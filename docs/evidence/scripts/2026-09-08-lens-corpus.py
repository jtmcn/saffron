"""Score REVIEW's lenses across the whole fixture corpus, not one fixture at a time.

`docs/superpowers/plans/2026-09-08-lens-corpus.md` (~$13, ~80 minutes at the
defaults below): a prompt change cannot be read through one fixture's noise —
`harness/corpus.py`'s own docstring cites a pass where per-defect scores moved
by a third between two runs that changed nothing relevant, while the corpus
aggregate held. This is the driver that runs every fixture under one root and
reports the aggregate.

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

This module holds no scoring logic — `harness/corpus.py` is the predicate,
linted and tested; this file only spends money and cannot be unit-tested
without a cell.

Three ways it differs from the single-fixture driver:

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

from harness import corpus, lens_scoring  # noqa: E402
from saffron import events  # noqa: E402
from saffron.cell import session  # noqa: E402
from saffron.phases import implement, review  # noqa: E402
from saffron.repos import mirror as mirror_ops  # noqa: E402


# Same function as the single-fixture driver, copied rather than imported: it
# is three lines, and importing across `docs/evidence/scripts/` files would
# couple two things meant to stay independently reproducible.
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
        "--budget-usd 4.0) the theoretical ceiling is $96 with no abort; "
        "the plan that specced this driver measured a full pass at ~$13 "
        "(docs/superpowers/plans/2026-09-08-lens-corpus.md). $20 leaves "
        "about 50%% headroom over that measurement while stopping well "
        "short of the theoretical max. On a trip: the pass stops, the "
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
    args = parser.parse_args()

    fixtures = corpus.load_corpus(args.fixtures)

    # Before the first cell, before any money: one predicate that no longer
    # reproduces its fixture's recorded answer is a bad fixture found for the
    # price of a message, not a cell.
    try:
        corpus.calibrate_corpus(fixtures)
    except lens_scoring.CalibrationError as exc:
        print(f"calibration failed, nothing was run:\n{exc}", file=sys.stderr)
        return 1
    print(f"calibration ok: {len(fixtures)} fixture(s)")

    args.out.mkdir(parents=True, exist_ok=True)

    mirror = None
    if not args.score_only:
        # One mirror and one image build for the whole pass — `image.cell_tag`
        # keys off the repo path, not the tree, so only the worktree changes
        # per fixture (session.cell_up's own docstring).
        mirror = mirror_ops.ensure_mirror(args.repo, args.home / "mirrors" / "self")

    total_spent = 0.0
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
                gates_dir=mirror_ops.export_saffron_dir(
                    mirror, fixture.head_sha, out / "gates"
                ),
                thread_env={},
                created=created,
                note=lambda step, detail: print(f"  {step}: {detail}"),
            )
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
                    # resolve puts the failure inside the loop, after a cell
                    # has already started.
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
                for review_ in reviews:
                    if review_.error:
                        # Not a miss: `score_run` drops the whole run. Said
                        # here too, because by the table it is one line of
                        # arithmetic.
                        print(
                            f"  ERRORED {review_.lens}: {review_.error}",
                            file=sys.stderr,
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

        # Between fixtures, after the cell for this one is already down: a
        # trip here never leaves a cell running, and every fixture up to and
        # including this one is already written to disk.
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
    table = corpus.render_corpus_table(fixtures, scored, corpus.anchored_blockers(runs))
    (args.out / "table.md").write_text(table + "\n")
    print(
        f"\n{table}\n\n${total_spent:.2f} spent this invocation — raw JSON in {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
