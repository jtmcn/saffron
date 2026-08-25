"""The `size` gate: is the diff small enough to review? (DESIGN.md §5.4)

Core, for the same reason as `scope`: it reads the diff as text, counts lines,
and never executes repo code — no language knowledge anywhere (§2.1). Advisory
at `risk: standard` and blocking at `elevated` (§5.6); wiring that switch is a
separate spec, so this module only ever produces the judgment, never enforces
it.

**Host-side only.** `tool` is left unset, which is right for a gate that
executes nothing — but `runner.run_gate` turns a declared gate's `pass`/`fail`
with no `tool` into `error`. So the wiring spec calls this from
`session.py::_suite` beside `scope` and `integrity`; declaring it in a repo's
`policy.yaml` would error every task.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult, split_lines

# bug / feature / refactor ceilings are DESIGN.md §5.4's table, verbatim.
_CEILINGS = {"bug": 300, "feature": 600, "refactor": 1000}

# `test`, `docs` and `chore` specs have no ceiling in §5.4 — an omission, not a
# signal that they are unbounded. Absence of a declared ceiling is not the gate
# breaking, so it must not become `error` (§5.4's own rule: `error` is reserved
# for the gate itself failing to run). The stand-in is the widest declared
# ceiling, not the median: `chore` regenerating a lock file and `docs`
# rewriting a §-section are where the largest legitimate diffs live, so a
# median default is stricter than `refactor` for the types §5.4 never sized.
_DEFAULT_CEILING = _CEILINGS["refactor"]


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
    # ponytail: a file git renders as `Binary files ... differ` has no `@@`, so
    # it contributes 0 and a `-diff` gitattribute zeroes the gate on a rewrite
    # of any size — BACKLOG item 2's residual, arriving here. The upgrade path
    # is `git diff --numstat` as the cross-check (BACKLOG item 1); it is not
    # taken here because the honest response is `error` only when the
    # unreadable file is inside `touches`, as `integrity` already does, and
    # this gate is handed neither `touches` nor a numstat. The wiring spec has
    # both.
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
            summary=f"{lines} changed lines within the {spec_type} ceiling of {ceiling}",
        )

    return GateResult(
        gate="size",
        status="fail",
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
