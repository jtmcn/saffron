"""The `size` gate: is the diff small enough to review? (DESIGN.md §5.4)

Core, for the same reason as `scope`: it reads the diff as text, counts lines,
and never executes repo code — no language knowledge anywhere (§2.1). Advisory
at `risk: standard` and blocking at `elevated` (§5.6). The host decides which
of those a given attempt is and says so with `blocking`; whether a *failure*
then stops anything is `advisory_gates`' question downstream, not this
module's. The one thing `blocking` changes here is whether an unmeasurable
diff is refused — see `size_gate`.

**Host-side only.** `tool` is left unset, which is right for a gate that
executes nothing — but `runner.run_gate` turns a declared gate's `pass`/`fail`
with no `tool` into `error`. So the wiring spec calls this from
`session.py::_suite` beside `scope` and `integrity`; declaring it in a repo's
`policy.yaml` would error every task.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult, split_lines
from saffron.gates.core.integrity import _BINARY
from saffron.gates.core.scope import matches

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
    # A file git renders as `Binary files ... differ` has no `@@`, so it
    # contributes 0 here — deliberately: `size_gate` screens for a declared-
    # unreadable block *before* calling this, the same split `integrity` makes
    # between "unreadable and inside touches" (`error`, handled there) and
    # "unreadable and outside touches" (`scope`'s problem, left at 0 here).
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


def _unreadable_paths(diff: str) -> list[str]:
    """Every `Binary files ... differ` path in the diff, in order.

    Same regex `integrity._BINARY` matches, imported rather than re-derived:
    a second, independently written pattern for the identical shape is how the
    two gates drift apart.
    """
    found = []
    for line in split_lines(diff):
        binary = _BINARY.match(line)
        if binary is None:
            continue
        # New side if renamed/added, old side if deleted — same preference as
        # `integrity._FileDiff.path`.
        found.append(binary.group(2) or binary.group(1) or "")
    return found


def _declared(path: str, touches: list[str]) -> bool:
    """Inside the task's declared paths. An empty `touches` declares nothing
    and constrains nothing — `scope` skips outright — so every path is in
    scope rather than none: a spec with no `touches` must not be the one place
    a hidden rewrite is unmeasurable *and* unremarked."""
    return not touches or any(matches(path, pattern) for pattern in touches)


def _unreadable_declared_path(diff: str, touches: list[str]) -> str | None:
    """The path of the first `Binary files ... differ` block whose path is
    inside `touches`, or `None` if every such block (if any) is outside it.

    Same regex `integrity._BINARY` matches, imported rather than re-derived:
    a second, independently written pattern for the identical shape is how
    the two gates drift apart (`integrity._parse_block`'s own note on this).
    Reuses `scope.matches` for the same glob semantics `integrity` applies to
    its `touches` exemption, so "declared" means the same thing in both gates.
    """
    return next(
        (path for path in _unreadable_paths(diff) if _declared(path, touches)), None
    )


def size_gate(
    diff: str, spec_type: str, touches: list[str], *, blocking: bool = True
) -> GateResult:
    """Diff lines (added + removed) against the ceiling `spec_type` sets.

    `error` before anything else is measured: a file git renders as
    `Binary files ... differ` (a `-diff` gitattribute, say) hides its content,
    so a hunk-counting gate cannot tell a genuine binary asset from 2000
    rewritten lines routed past the ceiling. `integrity` answers the identical
    shape by checking the file against the task's `touches`: unreadable and
    declared is `error` — the gate saying it cannot measure, never a verdict
    on the task, charged to nobody (§5.4). Unreadable and *not* declared is
    left alone, because `scope` already fails a diff touching an undeclared
    file, and erroring here too would make a genuine binary asset outside
    `touches` abort every task that happens to carry one.

    **Only when this gate blocks.** `error` reaches `aborted_gates` before
    `advisory_gates` is consulted, so it ends the attempt whatever the tier —
    and at `standard`, where §5.6 says this gate stops nothing, aborting is the
    opposite of nothing. It is also indistinguishable from the honest case: a
    task legitimately adding a PNG inside `touches` renders the same way as the
    `-diff` trick, and no diff can tell them apart. So the refusal is spent
    where the verdict is load-bearing — at `elevated` — and below it the
    readable lines are counted and the unreadable file is named in the summary.

    ponytail: this guarantee is *this gate's* alone. `integrity` refuses the
    identical shape — unreadable and inside `touches` — at every tier, so a
    repo declaring integrity patterns still aborts a standard-tier attempt over
    a genuine binary asset; only a repo that declares none sees the difference.
    Making the two agree means giving `integrity` a tier it does not otherwise
    need, or the `--numstat` cross-check its own `ponytail:` comment names as
    the upgrade path for exactly this. Neither is this gate's to decide.

    ponytail: an agent that cannot pass its gates can commit any real binary
    inside `touches` at `elevated` and reach `GATE_ERROR` on purpose — charged
    to nobody, no repair turn, exit 2. Same ceiling `integrity` already carries
    and the same upgrade path: git reports added lines in `--numstat` for a
    file it renders as binary, so the count is recoverable without the content.

    Past that check, `pass`/`fail` only: a diff this gate can read never
    produces `error` for size reasons — a large diff is the task's problem,
    not the gate's (§5.4). Ceiling lookup can't error either, since
    `_DEFAULT_CEILING` covers every spec type this function is not explicitly
    given a number for.
    """
    unreadable = _unreadable_declared_path(diff, touches)
    if unreadable is not None and blocking:
        return GateResult(
            gate="size",
            status="error",
            summary=(
                f"content hidden as binary, so changed lines are unreadable: "
                f"{unreadable}"
            ),
        )

    ceiling = _CEILINGS.get(spec_type, _DEFAULT_CEILING)
    lines = _changed_lines(diff)
    # Named, never silent: an advisory count over a diff with a hidden file is
    # a number with a hole in it, and the reader has to be told which.
    hidden = _unreadable_paths(diff)
    caveat = f" ({', '.join(hidden)} unreadable, not counted)" if hidden else ""

    if lines <= ceiling:
        return GateResult(
            gate="size",
            status="pass",
            summary=(
                f"{lines} changed lines within the {spec_type} ceiling "
                f"of {ceiling}{caveat}"
            ),
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
        summary=(
            f"{lines} changed lines exceeds the {spec_type} ceiling "
            f"of {ceiling}{caveat}"
        ),
    )
