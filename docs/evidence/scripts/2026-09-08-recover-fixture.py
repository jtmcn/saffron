"""Rebuild a fixture directory from the ledger and the batch tree.

`docs/superpowers/specs/2026-09-08-lens-corpus-design.md`. Every `head_sha`
recorded in `patch.json` is gone from live history — the branch was deleted
after merge — so a fixture's range is recovered rather than read off:

    head  the ledger's `pushed_sha` for the task
    base  the first ancestor of that head where `git diff base..head` is
          byte-identical to the batch tree's recorded `patch.diff`

Byte-identity is the acceptance test, not a heuristic. Four of the eight
fixtures need the walk because their recorded `tree_base` is not an ancestor of
their head at all: they were stacked pull requests, and SA-0048's true base is
SA-0046's head (backlog item 33, visible in the archive).

The `[[defects]]` blocks are deliberately NOT generated. The backlog row is the
only place the mutation that proves a defect is written down, and a generated
guess would be a predicate nobody chose.

The recovery itself lives in `harness/recovery.py`, shared with
`2026-09-08-sa0062-gate-tools.py` — a module name cannot start with a digit,
so neither dated script can import the other.

    uv run python docs/evidence/scripts/2026-09-08-recover-fixture.py \
        --spec SA-0063 --write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from harness.recovery import (  # noqa: E402
    FIXTURE_FILES,
    RecoveryError,
    recover_fixture,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="e.g. SA-0063")
    parser.add_argument("--home", type=Path, default=Path.home() / ".saffron")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, default=Path("docs/evidence/fixtures"))
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the fixture directory; without it the recovered range is "
        "printed and nothing moves.",
    )
    args = parser.parse_args()

    try:
        files = recover_fixture(args.spec, args.home, args.repo)
    except RecoveryError as exc:
        raise SystemExit(str(exc))

    fixture_dir = args.out / args.spec
    if args.write:
        fixture_dir.mkdir(parents=True, exist_ok=True)
        for name in FIXTURE_FILES:
            (fixture_dir / name).write_text(files[name])
        print(f"wrote {fixture_dir}")
    else:
        print(files["fixture.toml"])
        print(f"would write {fixture_dir}; pass --write to do so", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
