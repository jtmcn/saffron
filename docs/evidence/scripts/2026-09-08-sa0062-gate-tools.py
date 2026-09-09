"""Put the tools back into `SA-0062`'s frozen `gates.txt`.

`docs/BACKLOG.md` item 88. The fixture's gate summary was rebuilt from the
ledger's `gate_results` rows, which had no `tool` column, so all 14 lines read
`no tool reported` where the original named tools — the leading suspect for a
harness filing blockers 1, 2, 1 where production over the same range filed zero
(`docs/evidence/2026-09-07-lens-scoring-first-pass.md`).

The column now exists, but the rows do not carry it: they were written on
2026-09-07, and a nullable column added afterwards is null for every one. The
tools are recovered from the *other* record the same run left behind —
`baseline.json` in the batch tree, a serialized `GateResult` list with `tool`
populated, produced by the same container in the same run as the head suite. A
gate's tool is the version of a binary in that cell image; base and head ran it
from the same image, so the base suite's string is the head suite's string.

Two gates need more than a lookup. `revert` skipped at base and passed at head,
and it inherits the tool of the `tests` re-run it performs (`revert_gate`), so it
takes `tests`'s. `witness` inherits the same way (`witness_gate`) but *skipped*
here — the spec declares no mutants — so it reports none, and that is a status,
not a gate that executes nothing. The other six misses are: `scope`, `integrity`,
`size`, `committed`, `census` and `criteria` run no tool at all. Seven of the
fourteen lines say `no tool reported` in production too; only the other seven
were the deviation.

Statuses and summaries are unchanged: the ledger's rows are already faithful —
`green` in `session.py` is exactly the list that was recorded. The script
asserts that, refusing to write if regeneration moves anything but a tool.

    uv run python docs/evidence/scripts/2026-09-08-sa0062-gate-tools.py \
        --fixture docs/evidence/fixtures/SA-0062 --write

One-off, and idempotent: re-running it over the repaired fixture rewrites the
same bytes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from saffron.gates.contract import GateResult  # noqa: E402
from saffron.ledger import Ledger  # noqa: E402
from saffron.phases import review  # noqa: E402

# The parenthetical `gate_summary` writes, and the only thing this script may
# move. Anchored on the whole line so a changed status or summary cannot hide
# inside the part being replaced.
TOOL_PARENTHETICAL = re.compile(r"^(- \S+: \S+(?: \(advisory\))?) \([^)]*\)(.*)$")


def _strip_tools(text: str) -> str:
    """A summary with its tool parentheses removed, for comparing the rest."""
    lines = []
    for line in text.splitlines():
        matched = TOOL_PARENTHETICAL.match(line)
        lines.append(f"{matched[1]}{matched[2]}" if matched else line)
    return "\n".join(lines)


def _reviewed_results(ledger: Ledger, spec_id: str) -> list[GateResult]:
    """The suite REVIEW was shown: the last attempt that ran one.

    `session.py` keeps `green` from the gate call that decided the task was
    reviewable, and REVIEW's own attempts run no gates — so the last attempt
    holding results is that suite.
    """
    tasks = [row for row in ledger.queue_lines() if row["spec_id"] == spec_id]
    if len(tasks) != 1:
        raise SystemExit(f"{len(tasks)} tasks in the ledger for {spec_id}, want 1")
    for attempt in reversed(ledger.attempts(tasks[0]["task_id"])):
        results = ledger.attempt_results(attempt["attempt_id"])
        if results:
            return results
    raise SystemExit(f"{spec_id} has no attempt carrying gate results")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--home", type=Path, default=Path.home() / ".saffron")
    parser.add_argument("--spec-id", default="SA-0062")
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the fixture; without it the result is printed and nothing moves.",
    )
    args = parser.parse_args()

    batch_dir = args.home / "batches" / "v0" / args.spec_id
    baseline = json.loads((batch_dir / "baseline.json").read_text())
    tools = {row["gate"]: row["tool"] for row in baseline if row["tool"]}
    if not tools:
        raise SystemExit(f"{batch_dir / 'baseline.json'} names no tool — nothing to do")

    ledger = Ledger(args.home / "ledger.db")
    try:
        results = _reviewed_results(ledger, args.spec_id)
    finally:
        ledger.close()

    spliced = [
        result.model_copy(
            # `revert` executes the `tests` runner and reports its tool
            # (`revert_gate`); it skipped at base, so the lookup misses it.
            # `witness` inherits the same way but skipped here too, and every
            # other miss is a core gate that runs no tool — None is what
            # `gate_summary` renders as "no tool reported".
            update={
                "tool": tools.get(
                    result.gate, tools.get("tests") if result.gate == "revert" else None
                )
            }
        )
        for result in results
    ]
    # No advisory gate failed — every declared gate is `blocking: true` in the
    # policy at head, and `tests` is the only failure — so the advisory argument
    # cannot reach the rendered text and the empty set is not a simplification.
    failed = {r.gate for r in spliced if r.status == "fail"}
    if failed - {"tests"}:
        raise SystemExit(f"unexpected failing gates {sorted(failed)}; check advisory")
    # No trailing newline: `gate_summary` returns none, `session.py` hands the
    # lens what it returns, and `load_fixture` reads the file verbatim. Adding
    # one would be a second change to a frozen input.
    rendered = review.gate_summary(spliced)

    path = args.fixture / "gates.txt"
    before = path.read_text()
    if _strip_tools(before) != _strip_tools(rendered):
        raise SystemExit(
            "regeneration moved more than a tool — refusing to write.\n"
            f"before:\n{_strip_tools(before)}\nafter:\n{_strip_tools(rendered)}"
        )
    named = sum(1 for r in spliced if r.tool)
    if args.write:
        path.write_text(rendered)
        print(f"wrote {path}: {named} of {len(spliced)} lines name a tool")
    else:
        print(rendered)
        print(
            f"{named} of {len(spliced)} lines name a tool; "
            f"pass --write to update {path}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
