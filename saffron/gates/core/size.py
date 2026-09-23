"""The `size` gate: is the diff small enough to review? (DESIGN.md §5.4)

Core, for the same reason as `scope`: it reads the diff as text, counts
tokens, and never executes repo code — no language knowledge anywhere
(§2.1). Advisory at `risk: standard` and blocking at `elevated` (§5.6). The
host decides which of those a given attempt is and says so with `blocking`;
whether a *failure* then stops anything is `advisory_gates`' question
downstream, not this module's. The one thing `blocking` changes here is
whether an unmeasurable diff is refused — see `size_gate`.

**Host-side only.** `tool` is left unset, which is right for a gate that
executes nothing — but `runner.run_gate` turns a declared gate's `pass`/`fail`
with no `tool` into `error`. So the wiring spec calls this from
`session.py::_suite` beside `scope` and `integrity`; declaring it in a repo's
`policy.yaml` would error every task.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult, split_lines
from saffron.gates.core.integrity import _BINARY, _FILE_HEADER
from saffron.gates.core.scope import matches

# bug / feature / refactor ceilings, re-measured in tokens against 97 past
# diffs. Each value disagrees with the fewest past rows on pass or block.
_CEILINGS = {"bug": 1300, "feature": 3000, "refactor": 4200}

# `test`, `docs` and `chore` specs have no ceiling in §5.4 — an omission, not a
# signal that they are unbounded. Absence of a declared ceiling is not the gate
# breaking, so it must not become `error` (§5.4's own rule: `error` is reserved
# for the gate itself failing to run). The stand-in is the widest declared
# ceiling, not the median: `chore` regenerating a lock file and `docs`
# rewriting a §-section are where the largest legitimate diffs live, so a
# median default is stricter than `refactor` for the types §5.4 never sized.
_DEFAULT_CEILING = _CEILINGS["refactor"]

# Tokens per changed line, from 97 past diffs: aggregate 4.19, rounded down
# so a plan's own estimate errs toward acceptance. `artifacts.py` imports it.
_TOKENS_PER_LINE = 4

# A file whose two trimmed token streams multiply past this many pairs is
# not diffed exactly. The worst case under it measured 0.10s and 108MB.
_TOKEN_DIFF_BOUND = 10**9


def _file_blocks(diff: str) -> list[tuple[str, list[str], list[str], int]]:
    """Every file block that carries a hunk, as its path, its two token
    streams, and its physical changed-line count.

    The old stream holds context and removed tokens, the new one context
    and added tokens, in order. Neither resets at a `@@` line, so a block
    moved between hunks of one file counts as one edit. Header lines are
    skipped by position, before a block's first `@@`.
    """
    blocks: list[tuple[str, list[str], list[str], int]] = []
    path = ""
    old: list[str] = []
    new: list[str] = []
    physical = 0
    in_headers = True  # before the current file block's first "@@" line
    saw_hunk = False

    def flush() -> None:
        if saw_hunk:
            blocks.append((path, old, new, physical))

    for line in split_lines(diff):
        if line.startswith("diff --git "):
            flush()
            header = _FILE_HEADER.match(line)
            path = "" if header is None else (header.group(1) or header.group(2) or "")
            old, new, physical = [], [], 0
            in_headers = True  # a new file block, with its own header lines
            saw_hunk = False
            continue
        if line.startswith("@@"):
            in_headers = False
            saw_hunk = True
            continue
        if in_headers:
            continue
        if line.startswith("+"):
            new.extend(line[1:].split())
            physical += 1
        elif line.startswith("-"):
            old.extend(line[1:].split())
            physical += 1
        elif line.startswith(" ") or line == "":
            # `diff.suppressBlankEmpty` drops the leading space from a
            # blank context line, and a bare empty line reads the same way.
            tokens = line[1:].split()
            old.extend(tokens)
            new.extend(tokens)
        # anything else ("\ No newline at end of file", a rename line) adds
        # to neither stream.
    flush()
    return blocks


def _trim_shared_ends(old: list[str], new: list[str]) -> tuple[list[str], list[str]]:
    """`old` and `new`, with the tokens they share at the start and at the
    end removed. A pure move or rewrap shares its whole content this way,
    and trims to nothing. A one-token edit inside a long shared block
    trims down to that token and its immediate neighbours."""
    limit = min(len(old), len(new))
    start = 0
    while start < limit and old[start] == new[start]:
        start += 1
    limit -= start
    end = 0
    while end < limit and old[len(old) - 1 - end] == new[len(new) - 1 - end]:
        end += 1
    return old[start : len(old) - end], new[start : len(new) - end]


def _lcs_length(a: list[str], b: list[str]) -> int:
    """LCS length by bit-parallel LCS (Hyyrö, 2004) over Python ints.
    Cost grows with `len(a) * len(b)`, which `_TOKEN_DIFF_BOUND` caps."""
    if len(a) > len(b):
        a, b = b, a
    width = len(a)
    if width == 0:
        return 0
    shared = set(a) & set(b)
    masks: dict[str, int] = {}
    for index, token in enumerate(a):
        if token in shared:
            masks[token] = masks.get(token, 0) | (1 << index)
    all_ones = (1 << width) - 1
    vector = all_ones
    for token in b:
        matched = vector & masks.get(token, 0)
        vector = (vector + matched) | (vector - matched)
    return width - bin(vector & all_ones).count("1")


def _token_counts(diff: str) -> list[tuple[str, int, bool]]:
    """Every file's `(path, changed tokens, estimated)`, in diff order.

    `estimated` is set when the file's trimmed streams multiply past
    `_TOKEN_DIFF_BOUND`: the file is not diffed exactly, and its count is
    its changed physical lines times `_TOKENS_PER_LINE` instead.
    """
    counts: list[tuple[str, int, bool]] = []
    for path, old, new, physical in _file_blocks(diff):
        trimmed_old, trimmed_new = _trim_shared_ends(old, new)
        if len(trimmed_old) * len(trimmed_new) > _TOKEN_DIFF_BOUND:
            counts.append((path, physical * _TOKENS_PER_LINE, True))
            continue
        lcs = _lcs_length(trimmed_old, trimmed_new)
        counts.append((path, len(trimmed_old) + len(trimmed_new) - 2 * lcs, False))
    return counts


def _changed_lines(diff: str) -> int:
    """Changed tokens summed over files (see `_token_counts`). The name
    predates the unit."""
    return sum(count for _path, count, _estimated in _token_counts(diff))


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
    """The diff's changed tokens (added + removed, by the shortest per-file
    edit) against the ceiling `spec_type` sets.

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
    readable tokens are counted and the unreadable file is named in the summary.

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
    file it renders as binary, so an estimate is recoverable without the content.

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
                f"content hidden as binary, so changed tokens are unreadable: "
                f"{unreadable}"
            ),
        )

    ceiling = _CEILINGS.get(spec_type, _DEFAULT_CEILING)
    tokens = _changed_lines(diff)
    # Named, never silent. A count over a diff with a hidden or estimated
    # file has a hole in it, and the reader must be told which one.
    hidden = _unreadable_paths(diff)
    estimated = [path for path, _count, past_bound in _token_counts(diff) if past_bound]
    notes = []
    if hidden:
        notes.append(f"{', '.join(hidden)} unreadable, not counted")
    if estimated:
        notes.append(
            f"{', '.join(estimated)} past the token-diff bound, estimated at "
            f"{_TOKENS_PER_LINE} tokens a changed line"
        )
    caveat = f" ({'; '.join(notes)})" if notes else ""

    if tokens <= ceiling:
        return GateResult(
            gate="size",
            status="pass",
            summary=(
                f"{tokens} changed tokens within the {spec_type} ceiling "
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
                    f"{tokens} changed tokens exceeds the {spec_type} ceiling of "
                    f"{ceiling}"
                ),
            )
        ],
        summary=(
            f"{tokens} changed tokens exceeds the {spec_type} ceiling "
            f"of {ceiling}{caveat}"
        ),
    )
