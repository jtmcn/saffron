"""Score REVIEW's lenses against a fixture whose defects are already written down.

Track A of `docs/superpowers/plans/2026-09-07-trusting-the-queue.md`, closing the
evidence half of `docs/BACKLOG.md` item 79. Re-run this after every lens change
and put the table in a `docs/evidence/` record beside the prompt diff.

    env CLAUDE_CODE_OAUTH_TOKEN=... uv run python \\
        docs/evidence/scripts/2026-09-07-lens-scoring.py \\
        --fixture docs/evidence/fixtures/SA-0062 --runs 3

This is the half that spends money; the predicate it calls lives in
`harness/lens_scoring.py`, where it is linted and has tests. The split is not
tidiness: a scorer that can be wrong in silence is worth more tests than a
driver that fails loudly, and this file cannot be unit-tested without a cell.

Two things it refuses to do:

**It will not score a pass whose predicate cannot answer the run we already
know.** `calibrate` runs before the cell is built, so a loosened line range or a
dropped phrase costs nothing but a message. A harness that grades a lens by a
rule nobody checked is item 79 one level up.

**It will not build a cell any way but production's.** `session.cell_up` is the
same function `_drive_cell` calls — proxy first, host ports probed, egress
asserted — because a lens measured inside a weaker cell is measuring something
else (Appendix I).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from harness import lens_scoring  # noqa: E402
from saffron.cell import runtime, session  # noqa: E402
from saffron.phases import implement, review  # noqa: E402
from saffron.repos import mirror as mirror_ops  # noqa: E402

# The fixture pins the tree, so `git show <head>:<path>` is exactly what the
# cell's worktree holds — `anchor`'s own docstring names this as a satisfying
# `read_head`. Host-side keeps anchoring reproducible after teardown.
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
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home() / ".saffron")
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="lens passes over the same diff. A score without its n is the "
        "shape of claim item 69 charged the mutation-vs-lens record with.",
    )
    parser.add_argument("--budget-usd", type=float, default=4.0)
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    fixture = lens_scoring.load_fixture(args.fixture)

    # Before the cell, before the money: the predicate answers the one run whose
    # answer is written down, or nothing else it says is worth reading.
    try:
        lens_scoring.calibrate(fixture)
    except lens_scoring.CalibrationError as exc:
        print(f"calibration failed, nothing was run:\n{exc}", file=sys.stderr)
        return 1
    print(
        f"calibration ok: {fixture.spec_id} scores its own recorded findings "
        f"{fixture.recorded_seen} seen / {fixture.recorded_graded} graded"
    )

    stamp = time.strftime("%Y%m%dT%H%M%S")
    out_dir = args.out or (args.home / "lens-scoring" / f"{fixture.spec_id}-{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    mirror = mirror_ops.ensure_mirror(args.repo, args.home / "mirrors" / "self")
    gates_dir = mirror_ops.export_saffron_dir(
        mirror, fixture.head_sha, out_dir / "gates"
    )

    slug = f"lensscore-{fixture.spec_id.lower()}"
    network, volume = "saffron-cells", f"saffron-wt-{slug}"
    state, container = f"saffron-st-{slug}", f"saffron-cell-{slug}"
    created: set[str] = set()
    runs: list[list[review.LensReview]] = []

    try:
        session.cell_up(
            repo=args.repo,
            mirror=mirror,
            # The tree REVIEW read, not the merge commit: the fixture's whole
            # value is that the defects are still in it.
            tree_base=fixture.head_sha,
            branch=f"lens-scoring/{fixture.spec_id}",
            network=network,
            volume=volume,
            state=state,
            container=container,
            gates_dir=gates_dir,
            thread_env={},
            created=created,
            note=lambda step, detail: print(f"  {step}: {detail}"),
        )
        for index in range(1, args.runs + 1):
            print(f"run {index}/{args.runs}")
            reviews = review.run_review(
                container,
                diff=fixture.diff,
                read_head=_read_head_at(args.repo, fixture.head_sha),
                spec_body=fixture.spec_body,
                gates=fixture.gates,
                context_md=fixture.context_md,
                prompts_dir=Path("saffron/agents/prompts").resolve(),
                max_turns=args.max_turns,
                budget_usd=args.budget_usd,
                agent=implement.run_agent,
                spec_id=f"{fixture.spec_id}-lensscore-{index}",
                emit=lambda event: None,
            )
            (out_dir / f"run-{index}.json").write_text(
                json.dumps([r.as_dict() for r in reviews], indent=2)
            )
            runs.append(reviews)
    finally:
        # Narrower than `_drive_cell`'s teardown on purpose: no ledger row to
        # close and no outcome to stamp, so the only obligation is that nothing
        # this run created outlives it.
        for name in (container,):
            runtime.remove_container(name)
        for name in (volume, state):
            runtime.remove_volume(name)
        if network in created:
            runtime.remove_network(network)

    scores = lens_scoring.score_passes(fixture, runs)
    table = lens_scoring.render_table(fixture, scores)
    (out_dir / "table.md").write_text(table + "\n")
    spent = sum(r.cost_usd for run in runs for r in run)
    print(f"\n{table}\n\n${spent:.2f} over {args.runs} runs — raw JSON in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
