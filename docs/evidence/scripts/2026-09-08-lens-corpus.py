"""Score REVIEW's lenses across the whole fixture corpus, not one fixture at a time.

A prompt change cannot be read through one fixture's noise —
`harness/corpus.py`'s own docstring cites a pass where per-defect scores moved
by a third between two runs that changed nothing relevant, while the corpus
aggregate held. This is the driver that runs every fixture under one root and
reports the aggregate.

Run whole, over all eight fixtures: 2026-09-09, **$16.53** at the defaults below
(`docs/evidence/2026-09-09-lens-corpus-baseline.md`). That supersedes the ~$13
this docstring projected from a single fixture — see `--max-spend-usd`'s help,
which carries what the projection cost in headroom.

    env CLAUDE_CODE_OAUTH_TOKEN=... uv run python \\
        docs/evidence/scripts/2026-09-08-lens-corpus.py \\
        --fixtures docs/evidence/fixtures --out ~/.saffron/lens-corpus

`docs/evidence/scripts/2026-09-07-lens-scoring.py` stays exactly as it is —
both its recorded passes must stay reproducible by the file that produced
them — so this is a second file, not an edit to that one. It is modelled on
that script directly: same `_read_head_at`, same agent binding, same
`cell_up`/`cell_down` order. That order was found by spike, not reasoned, and
is copied here rather than paraphrased (Appendix I: every mechanism reports
success and applies to a different container).

**Do not run this while a batch is live**, for the same reason the
single-fixture driver's docstring gives: the container and volume names below
are this driver's own, but the proxy and the `saffron-cells` network are
shared, and `cell_up` removes the network on the way in while `cell_down`
stops the proxy on the way out. The exposure here is longer than the
single-fixture driver's — eight sequential cells over roughly the ~80 minutes
above, where that driver holds one cell up for as many runs as `--runs`
requests (its own docstring puts one run at ~8 minutes).

This module holds no scoring logic — `harness/corpus.py` is the predicate,
linted and tested; this file only spends money. It cannot be run against a
real cell in a test, but its wiring is not therefore unchecked:
`tests/test_corpus.py` drives `main` with `cell_up`, `cell_down`, `run_review`
and the gate runner replaced, which is what holds the probe path below to the
gate contract.

Four ways it differs from the single-fixture driver:

**It calibrates the whole corpus before the first cell.** One bad fixture
found after fixture six has already run is a bad fixture found expensively.

**It writes each fixture's run JSON the moment that fixture lands, and
`--skip-existing` resumes rather than restarts.** A failure at fixture six
must not cost the first five their money over again.

**Its spend ceiling is checked between fixtures, not between runs.** The
single-fixture driver's `if spent >= args.max_spend_usd and index < args.runs`
never fires at `--runs 1` — `1 < 1` is `False` — and `--runs 1` is exactly how
this driver is meant to be run, so copying that guard here would give a
ceiling that reads as active and is not. `--max-spend-usd` below is instead
checked once per fixture, after that fixture's cell is already down, so a trip
never leaves a cell running and never costs a fixture already on disk.

**It reports a second number.** Every adequacy finding carrying a vacuity
probe has that edit applied at the fixture's head, inside the cell that is
already up, and the repo's declared `tests` gate asked whether anything
notices. A probe that survives is the finding confirmed (`CONTEXT.md`), and
the table says so under the recall line. `--skip-probes` turns it off.

Every verdict lands in that fixture's `probes.json` as it is produced, for
the same reason each run's JSON is written the moment the fixture lands: a
raise inside a cell at fixture seven must not take the six before it with it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from harness import corpus, lens_scoring, probe_check  # noqa: E402
from saffron import events  # noqa: E402
from saffron.cell import runtime, session, worktree  # noqa: E402
from saffron.gates import runner  # noqa: E402
from saffron.gates.contract import GateResult  # noqa: E402
from saffron.intake import Mutant  # noqa: E402
from saffron.phases import implement, review  # noqa: E402
from saffron.repos import mirror as mirror_ops  # noqa: E402
from saffron.repos.policy import load_policy  # noqa: E402

TEST_PATHS = ("tests/",)
"""This repo's test root as a path prefix, which is not
`policy.integrity.test_paths` — those are globs (`tests/**`) where
`check_probe` compares normalised path prefixes. An edit to a test satisfies
the number by construction, so `check_probe` requires this argument."""


def _tests_gate_in_cell(
    container: str, executable: Path, cwd: Path, subset: list[str]
) -> GateResult:
    """The repo's *declared* `tests` gate, run inside the fixture's own cell.

    Never a tool: core invokes declared gates (§2.1), so a probe's suite is
    whatever `.saffron/policy.yaml` names at the fixture's head commit, read
    back through the JSON contract. `executable` is cell-side (`/gates/...`)
    and `cwd` a host path `CellExecutor` ignores — the same shape
    `phases/package.py` gives its re-verify suite, matched deliberately.

    Module level and bound with `partial`, not a closure over the fixture
    loop: a closure there captures the loop's `container` by name.
    """
    return runner.run_gate(
        "tests",
        executable,
        cwd,
        subset=subset,
        executor=runner.CellExecutor(container),
    )


def _distinct(probes: list[Mutant]) -> list[Mutant]:
    """The edits a pass will apply, first-seen order, one per distinct edit.

    `--runs 3` files the same probe three times. Applying it three times puts a
    raw total beside a recall line the run count normalises, and buys three
    identical suite runs — measured at ~14s each in-cell, and wasteful at any
    price.
    """
    return list({(p.file, p.find, p.replace): p for p in probes}.values())


def _write_probes(
    out: Path, applied: list[tuple[Mutant, probe_check.ProbeResult]]
) -> None:
    """The pass's second number, on disk rather than only in the terminal.

    Rewritten after every probe: recall survives a crash because the run JSON
    is already written and `--score-only` re-derives it, where a verdict that
    was only printed is gone with the process.
    """
    (out / "probes.json").write_text(
        json.dumps(
            [
                {
                    "probe": probe.model_dump(),
                    "verdict": result.verdict,
                    "reason": result.reason,
                    "failures": list(result.failures),
                    # What answered it: a `survived` over a suite that
                    # collected almost nothing is green too.
                    "tool": result.tool,
                    "collected": result.collected,
                    "summary": result.summary,
                }
                for probe, result in applied
            ],
            indent=2,
        )
    )


def _apply_probes(
    probes: list[Mutant],
    *,
    spec_id: str,
    out: Path,
    container: str,
    gates: dict[str, Path],
    cwd: Path,
) -> list[probe_check.ProbeResult]:
    """Every probe of one fixture, applied and asked, recorded as each lands.

    Inside the cell that is already up, and at `tree_base=head_sha` — `/work`
    is the fixture's head, which is the only tree `source_mutated` will apply
    an edit to (it refuses six cases by yielding a reason, and `check_probe`
    reads each as `unproven`).
    """
    applied: list[tuple[Mutant, probe_check.ProbeResult]] = []
    # Written before the first probe too, so a fixture that was probed and had
    # nothing to apply reads as `[]` rather than as a fixture nobody probed.
    _write_probes(out, applied)

    def landed(probe: Mutant, result: probe_check.ProbeResult) -> None:
        applied.append((probe, result))
        _write_probes(out, applied)
        print(f"  probe {result.verdict}: {result.reason}")

    def all_unproven(pending: list[Mutant], reason: str) -> None:
        for probe in pending:
            landed(probe, probe_check.ProbeResult("unproven", reason))

    if not probes:
        # Before the baseline, which is a whole suite run (~15.6s measured) to
        # answer nothing. The `[]` written above is still the coverage record.
        return []

    if "tests" not in gates:
        # Every shipped fixture's head declares a `tests` gate (pinned by a
        # test), so this is the fallback, not the path a pass takes.
        all_unproven(
            probes,
            f"{spec_id}'s head declares no `tests` gate, so nothing could "
            "answer the probe",
        )
        return [result for _probe, result in applied]

    run_tests = partial(_tests_gate_in_cell, container, gates["tests"], cwd)
    # A container exec fails routinely, so a raise at fixture seven of eight
    # must cost that fixture's probes, not the pass.
    try:
        baseline = run_tests([])
    except runtime.CellRuntimeError as exc:
        all_unproven(probes, f"the baseline tests gate could not run: {exc}")
        return [result for _probe, result in applied]

    for index, probe in enumerate(probes):
        try:
            result = probe_check.check_probe(
                probe,
                baseline=baseline,
                mutate=partial(worktree.source_mutated, container),
                run_tests=run_tests,
                test_paths=TEST_PATHS,
            )
        except runtime.CellRuntimeError as exc:
            # After a raise the tree may be mutated: a failed undo and a failed
            # apply (`SA-0062`) are told apart only by an exception's text, so
            # neither is trusted. The cell is per-fixture, so stop at this one.
            landed(
                probe,
                probe_check.ProbeResult(
                    "unproven", f"the probe could not be applied or asked: {exc}"
                ),
            )
            all_unproven(
                probes[index + 1 :],
                "an earlier probe left this cell's tree in an unknown state, "
                "so nothing after it in this fixture was asked",
            )
            break
        landed(probe, result)
    return [result for _probe, result in applied]


# Copied from the single-fixture driver rather than imported: importing across
# `docs/evidence/scripts/` would couple two independently reproducible files.
def _read_head_at(repo: Path, head_sha: str):
    def read_head(path: str) -> str | None:
        done = subprocess.run(
            ["git", "-C", str(repo), "show", f"{head_sha}:{path}"],
            capture_output=True,
            text=True,
        )
        return done.stdout if done.returncode == 0 else None

    return read_head


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="must be the same path across invocations for --skip-existing "
        "and a --max-spend-usd trip to resume correctly — unlike the "
        "single-fixture driver, this has no timestamped default.",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home() / ".saffron")
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="scored runs of the three lenses, per fixture (default 1 — a "
        "corpus pass already multiplies cost by fixture count, where the "
        "single-fixture driver multiplies by --runs instead).",
    )
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=4.0,
        help="per lens, per run, the way `run_review` spends it. Bounded for "
        "real by --max-spend-usd.",
    )
    parser.add_argument(
        "--max-spend-usd",
        type=float,
        default=20.0,
        help="the pass stops between fixtures once it has spent this in this "
        "invocation. At the defaults (8 fixtures, 3 lenses, --runs 1, "
        "--budget-usd 4.0) the theoretical ceiling is $96 with no abort. "
        "Measured, not extrapolated, since 2026-09-09: a whole pass over "
        "eight fixtures is $16.53 "
        "(docs/evidence/2026-09-09-lens-corpus-baseline.md), against the "
        "~$12.90 this help used to project from one fixture. So $20 leaves "
        "about 21%% headroom rather than the 50%% the projection implied, "
        "and the baseline's first invocation spent $17.31 of it — raise "
        "this before adding fixtures. On a trip: the pass stops, the "
        "fixtures already written stay written, and --skip-existing "
        "resumes it.",
    )
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="a fixture with an existing run-1.json under --out is left "
        "alone rather than re-run — how a --max-spend-usd trip is resumed.",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="skip cell_up entirely — no cell, no spend — and score "
        "whatever run-*.json already exists under --out for each fixture.",
    )
    parser.add_argument(
        "--skip-probes",
        action="store_true",
        help="do not apply the adequacy lens's vacuity probes, and report "
        "recall alone. They are the only part of a pass that runs the "
        "fixture's declared `tests` gate — once for a baseline, then once per "
        "probe — so a re-run interested only in recall should not wait on it.",
    )
    args = parser.parse_args()

    fixtures = corpus.load_corpus(args.fixtures)

    # Before any money: a predicate that no longer reproduces its fixture's
    # recorded answer is a bad fixture found for the price of a message.
    try:
        corpus.calibrate_corpus(fixtures)
    except lens_scoring.CalibrationError as exc:
        print(f"calibration failed, nothing was run:\n{exc}", file=sys.stderr)
        return 1
    print(f"calibration ok: {len(fixtures)} fixture(s)")

    args.out.mkdir(parents=True, exist_ok=True)

    mirror = None
    if not args.score_only:
        # Once for the whole pass; `cell_up` rebuilds the image per fixture,
        # expected to be a cache hit after the first — unmeasured.
        mirror = mirror_ops.ensure_mirror(args.repo, args.home / "mirrors" / "self")

    total_spent = 0.0
    # ponytail: this invocation's probes only, where recall below is re-derived
    # from every run JSON on disk. Nothing re-aggregates `probes.json` across
    # invocations; the summary names the fixture count so the two are distinct.
    probe_results: dict[str, list[probe_check.ProbeResult]] = {}
    for i, fixture in enumerate(fixtures):
        out = args.out / fixture.spec_id
        if args.score_only:
            print(f"{fixture.spec_id}: --score-only, not spending")
            continue
        if args.skip_existing and (out / "run-1.json").is_file():
            print(f"{fixture.spec_id}: already run, skipping")
            continue
        # Reachable only past the `score_only` continue above, where `mirror`
        # is always set — spelled out for the type checker, not the reader.
        assert mirror is not None
        out.mkdir(parents=True, exist_ok=True)

        # Hoisted out of `cell_up`: the probes need the same export, because
        # the policy must come from the commit its executables came from.
        gates_dir = mirror_ops.export_saffron_dir(
            mirror, fixture.head_sha, out / "gates"
        )
        # Off the read-only `/gates` mount, not `/work`: nothing REVIEW's cell
        # wrote can reach the gate a probe is judged by (§5.4).
        policy, _ = load_policy(gates_dir)
        gates = policy.gate_executables(Path(worktree.GATES_MOUNT))

        slug = f"lenscorpus-{fixture.spec_id.lower()}"
        network, volume = "saffron-cells", f"saffron-wt-{slug}"
        state, container = f"saffron-st-{slug}", f"saffron-cell-{slug}"
        created: set[str] = set()

        # Rebuilt per fixture so its `spec_id` follows the fixture, not the
        # first one bound before the loop started.
        agent = session.stop_on_rejected(
            partial(
                implement.run_agent,
                timeout_s=session.TURN_TIMEOUT_S,
                spec_id=f"{fixture.spec_id}-lenscorpus",
            )
        )

        try:
            session.cell_up(
                repo=args.repo,
                mirror=mirror,
                # The tree REVIEW read, not the merge commit: the fixture's
                # whole value is that the defects are still in it.
                tree_base=fixture.head_sha,
                branch=f"lens-corpus/{fixture.spec_id}",
                network=network,
                volume=volume,
                state=state,
                container=container,
                gates_dir=gates_dir,
                thread_env={},
                created=created,
                note=lambda step, detail: print(f"  {step}: {detail}"),
            )
            probes = []
            for index in range(1, args.runs + 1):
                print(f"{fixture.spec_id} run {index}/{args.runs}")
                reviews = review.run_review(
                    container,
                    diff=fixture.diff,
                    read_head=_read_head_at(args.repo, fixture.head_sha),
                    spec_body=fixture.spec_body,
                    gates=fixture.gates,
                    context_md=fixture.context_md,
                    # Off the script's own root, not the CWD: a relative
                    # resolve fails inside the loop, after a cell has started.
                    prompts_dir=ROOT / "saffron" / "agents" / "prompts",
                    max_turns=args.max_turns,
                    budget_usd=args.budget_usd,
                    agent=agent,
                    spec_id=f"{fixture.spec_id}-lenscorpus-{index}",
                    emit=lambda event: print(f"  {events.describe(event)}"),
                )
                (out / f"run-{index}.json").write_text(
                    json.dumps([r.as_dict() for r in reviews], indent=2)
                )
                total_spent += sum(r.cost_usd for r in reviews)
                probes += [
                    finding.probe
                    for review_ in reviews
                    for finding in review_.findings
                    if finding.probe is not None
                ]
                for review_ in reviews:
                    if review_.error:
                        # Not a miss: `score_run` drops the whole run.
                        print(
                            f"  ERRORED {review_.lens}: {review_.error}",
                            file=sys.stderr,
                        )

            # After every run, so `--runs 3` pays for one baseline and one
            # application per distinct edit. The key is set whenever this
            # fixture was probed, empty list included — that is `fixtures`.
            if not args.skip_probes:
                probes = _distinct(probes)
                print(f"  {len(probes)} vacuity probe(s) to apply")
                probe_results[fixture.spec_id] = _apply_probes(
                    probes,
                    spec_id=fixture.spec_id,
                    out=out,
                    container=container,
                    gates=gates,
                    cwd=mirror,
                )
        finally:
            # The shared teardown, not a paraphrase of it — see module
            # docstring and `session.cell_down`'s own.
            session.cell_down(
                network=network,
                volume=volume,
                state=state,
                container=container,
                created=created,
                note=lambda _s, _ok, d: print(f"  {d}", file=sys.stderr),
            )

        # Between fixtures, after this one's cell is down: a trip here never
        # leaves a cell running, and every fixture so far is on disk.
        if total_spent >= args.max_spend_usd and i < len(fixtures) - 1:
            print(
                f"stopping after {fixture.spec_id}: ${total_spent:.2f} "
                f"reaches --max-spend-usd ${args.max_spend_usd:.2f} — rerun "
                "with --skip-existing to resume",
                file=sys.stderr,
            )
            break

    runs = {
        fixture.spec_id: [
            lens_scoring.reviews_from_json(path.read_text())
            for path in sorted((args.out / fixture.spec_id).glob("run-*.json"))
        ]
        for fixture in fixtures
    }
    try:
        scored = corpus.score_corpus(fixtures, runs)
    except lens_scoring.LensErrored as exc:
        print(f"nothing to score:\n{exc}", file=sys.stderr)
        return 1
    table = corpus.render_corpus_table(
        fixtures,
        scored,
        corpus.anchored_blockers(runs),
        # `None`, not an empty score: a pass that applied no probe learned
        # nothing, and "0 of 0" under the table would read as though it had.
        probes=None
        if args.score_only or args.skip_probes or not probe_results
        else corpus.score_probes(probe_results, runs=args.runs),
    )
    (args.out / "table.md").write_text(table + "\n")
    print(
        f"\n{table}\n\n${total_spent:.2f} spent this invocation — raw JSON in {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
