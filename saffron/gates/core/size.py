"""The `size` gate: is the diff small enough to review? (DESIGN.md §5.4)

Core, for the same reason as `scope`: it reads the diff as text, counts lines,
and never executes repo code — no language knowledge anywhere (§2.1). Advisory
at `risk: standard` and blocking at `elevated` (§5.6); wiring that switch is a
separate spec, so this module only ever produces the judgment, never enforces
it.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult, split_lines

# bug / feature / refactor ceilings are DESIGN.md §5.4's table, verbatim.
_CEILINGS = {"bug": 300, "feature": 600, "refactor": 1000}

# `test`, `docs` and `chore` specs have no ceiling in §5.4 — an omission, not a
# signal that they are unbounded. Absence of a declared ceiling is not the gate
# breaking, so it must not become `error` (§5.4's own rule: `error` is reserved
# for the gate itself failing to run). `feature`'s ceiling is the middle of the
# three declared values, and stands in as the default until a spec pins one.
_DEFAULT_CEILING = _CEILINGS["feature"]

# The gate has no external tool to interrogate — it is Saffron's own line
# count — so `tool` names the gate itself rather than something obtained by
# running a subprocess (per the notes on this spec).
_TOOL = "saffron-size 1"


def _changed_lines(diff: str) -> int:
    """Added lines plus removed lines, from hunk content only.

    `split_lines`, not `splitlines()` — same reasoning as `scope`/`integrity`:
    a raw `\\r`/`\\x0c`/etc inside an added line must not be read as a second
    line.

    The `--- a/path` / `+++ b/path` file headers are excluded by *position*,
    not by matching their leading characters against hunk content: they only
    ever appear before a file block's first `@@` line, and a real added or
    removed line can itself start with `--`, `---`, `++` or `+++` — a SQL/Lua
    `-- comment`, a YAML/Markdown `---` delimiter, a git conflict marker, a
    bare `++i;` — none of which start a hunk. So every line up to and
    including a file block's first `@@` is header, not content, and every
    line after it is judged only by its single leading `+`/`-` marker, exactly
    as `integrity._parse_block` treats the same distinction (`saw_hunk`).
    """
    count = 0
    in_headers = True  # before the current file block's first "@@" line
    for line in split_lines(diff):
        if line.startswith("diff --git "):
            in_headers = True  # a new file block, with its own header lines
            continue
        if line.startswith("@@"):
            in_headers = False
            continue
        if in_headers:
            continue
        if line.startswith("+") or line.startswith("-"):
            count += 1
    return count


def size_gate(diff: str, spec_type: str) -> GateResult:
    """Diff lines (added + removed) against the ceiling `spec_type` sets.

    `pass`/`fail` only: a diff this gate can read never produces `error` — a
    large diff is the task's problem, not the gate's (§5.4). Ceiling lookup
    can't error either, since `_DEFAULT_CEILING` covers every spec type this
    function is not explicitly given a number for.
    """
    ceiling = _CEILINGS.get(spec_type, _DEFAULT_CEILING)
    lines = _changed_lines(diff)

    if lines <= ceiling:
        return GateResult(
            gate="size",
            status="pass",
            tool=_TOOL,
            summary=f"{lines} changed lines within the {spec_type} ceiling of {ceiling}",
        )

    return GateResult(
        gate="size",
        status="fail",
        tool=_TOOL,
        failures=[
            Failure(
                file="",
                code="diff-too-large",
                message=(
                    f"{lines} changed lines exceeds the {spec_type} ceiling of "
                    f"{ceiling}"
                ),
            )
        ],
        summary=f"{lines} changed lines exceeds the {spec_type} ceiling of {ceiling}",
    )
