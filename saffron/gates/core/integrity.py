"""The `integrity` gate: was a suppression added, or gate config edited? (§5.4)

Core, because both questions are about diff text and are identical in every
language — no execution of repo code, the same shape as `scope.py`. The
*vocabulary* is not universal, so `IntegrityPatterns` arrives from the repo's
`.saffron/policy.yaml` (§2.1) rather than being guessed here.

**Removal is not asked here.** "Was an existing test removed?" is a question
about which tests exist, and a diff is a lossy projection of that: three
diff-shaped versions of the check were written and all three were wrong, in
three different ways (Appendix M, principle 52). `census` answers it exactly,
by subtracting two sets of collected names.

The `touches` exemption binds both surviving checks. For a suppression or a
gate-config edit the signal is *this file changed at all*, and a spec whose
`touches` names the file has authorized exactly that. It is also the only
defence a substring scan has against prose: a docstring quoting a token is a
use of it to core.
"""

from __future__ import annotations

import re

from saffron.gates.contract import Failure, GateResult, split_lines
from saffron.gates.core.scope import matches
from saffron.repos.policy import IntegrityPatterns

# Same pinned-prefix contract as scope.py: the host runs `git diff` with
# `worktree.DIFF_FLAGS`, so every file header must be exactly this shape.
# Anything else means git did not honour the flags, and a gate that cannot
# recognise its own input reports `error` rather than a `pass` nobody checked.
_FILE_HEADER = re.compile(r'^diff --git (?:a/.+ b/.+|"a/.+" "b/.+")$')

# `--- a/path` / `--- /dev/null` and `+++ b/path` / `+++ /dev/null`, quoted or
# not. Only trusted before the first hunk of a block — after that an
# identical-looking line may be real content (a removed line whose own text
# starts with `--- `), not a path header.
_OLD_PATH = re.compile(r'^--- (?:"?a/(.+?)"?|/dev/null)$')
_NEW_PATH = re.compile(r'^\+\+\+ (?:"?b/(.+?)"?|/dev/null)$')

# `@@ -12,7 +12,9 @@ optional trailing context` — the only shape a hunk header
# is allowed to take. A `@@` line that does not match means the gate cannot
# trust where a hunk begins or ends.
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

# A `-diff` gitattribute renders a *text* file this way: content hidden, path
# not. `scope` reads paths and is unaffected; this gate reads added lines, and
# a file whose added lines cannot be read is a file whose suppressions cannot
# be counted (BACKLOG item 2).
#
# Measured: this line *replaces* the `--- `/`+++ ` headers rather than joining
# them, so the path has to come from here or it does not arrive at all — and
# without a path the `touches` exemption cannot be applied to it.
_BINARY = re.compile(
    r'^Binary files (?:"?a/(.+?)"?|/dev/null) and (?:"?b/(.+?)"?|/dev/null) differ$'
)


class _DiffError(Exception):
    """The diff isn't the shape this gate is entitled to trust. → `error`."""

    def __init__(self, summary: str) -> None:
        self.summary = summary


class _FileDiff:
    __slots__ = ("old_path", "new_path", "hunks", "unreadable")

    def __init__(self, old_path: str | None, new_path: str | None) -> None:
        self.old_path = old_path
        self.new_path = new_path
        # Content hidden as binary. Recorded rather than raised, so that a file
        # the spec declared in `touches` can be exempted before it is judged —
        # a committed PNG fixture must not abort the attempt.
        self.unreadable = False
        # Each hunk: a list of (kind, content, new_line) where kind is one of
        # "+"/"-"/" ", and new_line is the line's number in the post-image —
        # only meaningful (not None) for "+" and " " lines.
        self.hunks: list[list[tuple[str, str, int | None]]] = []

    @property
    def path(self) -> str:
        """The path an operator would recognise: new side, or old if deleted."""
        return self.new_path if self.new_path is not None else (self.old_path or "")

    def matches_any(self, patterns: list[str]) -> bool:
        candidates = [p for p in (self.old_path, self.new_path) if p is not None]
        return any(
            matches(candidate, pattern)
            for candidate in candidates
            for pattern in patterns
        )


def _split_blocks(diff: str) -> list[str]:
    """Split on `diff --git` header lines, validating each as we go."""
    lines = split_lines(diff)
    starts = []
    for index, line in enumerate(lines):
        if line.startswith("diff --git "):
            if not _FILE_HEADER.match(line):
                raise _DiffError(
                    f"diff prefixes are not a/ b/, so paths are unreadable: {line[:120]}"
                )
            starts.append(index)
    blocks = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        blocks.append("\n".join(lines[start:end]))
    return blocks


def _parse_block(block: str) -> _FileDiff:
    lines = split_lines(block)
    old_path: str | None = None
    new_path: str | None = None
    saw_hunk = False
    file_diff: _FileDiff | None = None
    current: list[tuple[str, str, int | None]] | None = None
    new_line = 0

    for line in lines:
        if not saw_hunk:
            if binary := _BINARY.match(line):
                # Measured: git emits this before any `@@`, and in place of the
                # path headers — so the paths come from the match itself.
                file_diff = _FileDiff(binary.group(1), binary.group(2))
                file_diff.unreadable = True
                return file_diff
            if line.startswith("--- ") and old_path is None:
                header = _OLD_PATH.match(line)
                if header is None:
                    raise _DiffError(f"unreadable old-file header: {line[:120]}")
                old_path = header.group(1)
                # git appends a TAB after a path containing whitespace; the
                # capture group swallows it, so strip the one it would add.
                if old_path is not None:
                    old_path = old_path.removesuffix("\t")
                continue
            if line.startswith("+++ ") and new_path is None:
                header = _NEW_PATH.match(line)
                if header is None:
                    raise _DiffError(f"unreadable new-file header: {line[:120]}")
                new_path = header.group(1)
                if new_path is not None:
                    new_path = new_path.removesuffix("\t")
                continue

        if line.startswith("@@"):
            if file_diff is None:
                file_diff = _FileDiff(old_path, new_path)
            header = _HUNK_HEADER.match(line)
            if header is None:
                raise _DiffError(f"unreadable hunk header: {line[:120]}")
            saw_hunk = True
            new_line = int(header.group(1))
            current = []
            file_diff.hunks.append(current)
            continue

        if not saw_hunk or current is None:
            continue  # mode lines, index lines, "rename from/to", etc.

        if line.startswith("+"):
            current.append(("+", line[1:], new_line))
            new_line += 1
        elif line.startswith("-"):
            current.append(("-", line[1:], None))
        elif line.startswith(" ") or line == "":
            # `diff.suppressBlankEmpty` drops the leading space from a blank
            # context line. `worktree` pins it off, but a diff read from
            # anywhere else must not abort the attempt over one.
            current.append((" ", line[1:], new_line))
            new_line += 1
        elif line.startswith("\\"):
            pass  # "\ No newline at end of file" — measured in all four positions
        else:
            raise _DiffError(f"unrecognised hunk content line: {line[:120]}")

    if file_diff is None:
        file_diff = _FileDiff(old_path, new_path)
    return file_diff


def integrity_gate(
    diff: str, patterns: IntegrityPatterns, touches: list[str]
) -> GateResult:
    """`pass`/`fail` over a unified diff, the repo's patterns, and the spec's
    `touches`.

    `diff` is the export the reviewer reads, produced with the pinned
    `worktree.DIFF_FLAGS` — the same contract `scope_gate` relies on. A diff
    this gate cannot parse is `error`, never a `pass` nobody checked (§5.4).
    """
    if not patterns.suppressions and not patterns.gate_config:
        return GateResult(
            gate="integrity",
            status="skip",
            summary="no integrity patterns declared",
        )

    try:
        files = [_parse_block(block) for block in _split_blocks(diff)]
    except _DiffError as exc:
        return GateResult(gate="integrity", status="error", summary=exc.summary)

    failures: list[Failure] = []

    for file_diff in files:
        declared = any(matches(file_diff.path, pattern) for pattern in touches)

        # Only reported for a file the spec authorized. A file outside `touches`
        # has already failed `scope`, which is a `fail` the agent can repair by
        # deleting it — and `repair_loop` checks `aborted_gates` before the
        # subtraction, so erroring here would replace that repairable failure
        # with an abandoned task.
        #
        # ponytail: two ceilings, one rule. A genuine binary fixture inside
        # `touches` aborts the attempt — the false positive. And an agent can
        # reach `error` *on purpose*: a committed `.gitattributes` with
        # `*.py -diff` renders every Python file this way, and `error` is
        # `GATE_ERROR`, charged to nobody. The upgrade path closes both: a
        # `--numstat` cross-check, since git still reports added lines for a
        # file it renders as binary. Not built here — it is a design change
        # (BACKLOG item 1, "Still open, deliberately").
        if file_diff.unreadable:
            if not declared:
                continue
            return GateResult(
                gate="integrity",
                status="error",
                summary=(
                    f"content hidden as binary, so added lines are unreadable: "
                    f"{file_diff.path}"
                ),
            )

        # The exemption binds this check and nothing else. It is file-level, and
        # so is the question — whereas exempting the line-level suppression scan
        # by the same key nullifies it, because `scope` already guarantees every
        # changed file is inside `touches` (§5.4).
        if (
            patterns.gate_config
            and not declared
            and file_diff.matches_any(patterns.gate_config)
        ):
            failures.append(
                Failure(
                    file=file_diff.path,
                    code="gate-config-changed",
                    message=f"changed gate configuration: {file_diff.path}",
                )
            )

        if patterns.suppressions:
            for hunk in file_diff.hunks:
                for kind, content, line_number in hunk:
                    if kind != "+":
                        continue
                    for token in patterns.suppressions:
                        if token in content:
                            failures.append(
                                Failure(
                                    file=file_diff.path,
                                    line=line_number,
                                    code="added-suppression",
                                    message=f"added suppression {token!r} in {file_diff.path}",
                                )
                            )

    if not failures:
        return GateResult(
            gate="integrity",
            status="pass",
            summary=f"{len(files)} changed files clean of suppression and gate-config edits",
        )

    return GateResult(
        gate="integrity",
        status="fail",
        failures=failures,
        summary=f"{len(failures)} integrity violation(s) across {len(files)} changed files",
    )
