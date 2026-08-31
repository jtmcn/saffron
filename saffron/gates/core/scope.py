"""The `scope` gate: changed files ⊆ touches, and ⊄ forbidden/protected.

Core, because it operates on the diff as text and paths — no language knowledge
anywhere (DESIGN.md §2.1).
"""

from __future__ import annotations

import re

from saffron.gates.contract import Failure, GateResult, split_lines

# A header from a diff whose prefixes were pinned (`worktree.DIFF_FLAGS`); git
# quotes both sides together when a path needs C-quoting.
_HEADER = re.compile(r'^diff --git (?:a/.+ b/.+|"a/.+" "b/.+")$')

_TOKENS = re.compile(r"\*\*/|\*\*|\*|\?")
_TRANSLATIONS = {"**/": r"(?:[^/]+/)*", "**": r".*", "*": r"[^/]*", "?": r"[^/]"}


def _to_regex(pattern: str) -> re.Pattern[str]:
    out, index = [], 0
    for token in _TOKENS.finditer(pattern):
        out.append(re.escape(pattern[index : token.start()]))
        out.append(_TRANSLATIONS[token.group()])
        index = token.end()
    out.append(re.escape(pattern[index:]))
    return re.compile("".join(out) + r"\Z")


def matches(path: str, pattern: str) -> bool:
    """Glob match where `*` stops at a slash and `**` does not.

    `fnmatch` lets `*` cross a `/`, and `PurePath.full_match` needs 3.13.
    """
    return _to_regex(pattern).match(path) is not None


def scope_gate(
    changed_files: list[str],
    touches: list[str],
    *,
    diff: str | None = None,
    forbidden: list[str] | None = None,
    protected: list[str] | None = None,
) -> GateResult:
    """Changed files ⊆ touches, and ⊄ forbidden/protected, judged against the
    diff those paths came from.

    `diff` is the export the reviewer reads. Its headers must carry the a/ b/
    the host pinned; anything else means git did not honour the flags, and a
    gate that cannot recognise its own input reports `error` — infrastructure,
    charged to nobody (§5.4) — rather than a `pass` nobody checked.

    `forbidden` (a spec's own deny list) and `protected` (the repo's global
    one) default to empty, so every caller that predates them is unchanged.
    Both are matched with the same `matches()` `touches` already uses — one
    function, one meaning of "declared" — and checked against every changed
    file independently of the `touches` check: a file can be both outside
    `touches` and denied by one of these lists, and the `out-of-scope` failure
    for it is never renamed or dropped just because it is also denied.
    """
    if diff is not None:
        # split_lines, not splitlines(): \r, \x0c and friends appear raw inside
        # a line git emits, and splitting on them could shatter one line into a
        # fragment that starts with "diff --git ".
        for line in split_lines(diff):
            if line.startswith("diff --git ") and not _HEADER.match(line):
                return GateResult(
                    gate="scope",
                    status="error",
                    summary=f"diff prefixes are not a/ b/, so paths are unreadable: {line[:120]}",
                )

    if not touches:
        # ponytail: a diff whose scope is unratified is checked against
        # neither deny list. Unreachable from a cell only because
        # `artifacts.validate_plan` rejects an empty `touches` first — a
        # plan-time guard, the class of control this gate exists to not be.
        return GateResult(
            gate="scope",
            status="skip",
            summary="no touches declared",
        )

    forbidden = forbidden or []
    protected = protected or []

    escaped = [
        path
        for path in changed_files
        if not any(matches(path, pattern) for pattern in touches)
    ]
    forbidden_hits = [
        path
        for path in changed_files
        if any(matches(path, pattern) for pattern in forbidden)
    ]
    protected_hits = [
        path
        for path in changed_files
        if any(matches(path, pattern) for pattern in protected)
    ]

    if not escaped and not forbidden_hits and not protected_hits:
        return GateResult(
            gate="scope",
            status="pass",
            summary=f"{len(changed_files)} changed files within touches",
        )

    # The failure line is the whole channel to the agent (§5.4), and none of
    # the three lists live in the spec body — so each failure names its own.
    declared_touches = ", ".join(touches)
    declared_forbidden = ", ".join(forbidden)
    declared_protected = ", ".join(protected)
    failures = (
        [
            Failure(
                file=path,
                code="out-of-scope",
                message=f"outside touches: {declared_touches}",
            )
            for path in escaped
        ]
        + [
            Failure(
                file=path,
                code="forbidden",
                message=f"denied by this spec's forbidden list: {declared_forbidden}",
            )
            for path in forbidden_hits
        ]
        + [
            Failure(
                file=path,
                code="protected",
                message=f"denied by the repo's protected list: {declared_protected}",
            )
            for path in protected_hits
        ]
    )

    if not forbidden_hits and not protected_hits:
        # Byte-identical to the gate's behaviour before forbidden/protected
        # existed, for every caller that never passes them.
        summary = (
            f"{len(escaped)} of {len(changed_files)} changed files outside touches"
        )
    else:
        summary = (
            f"{len(failures)} denial(s) across {len(changed_files)} changed files: "
            f"{len(escaped)} outside touches, {len(forbidden_hits)} forbidden, "
            f"{len(protected_hits)} protected"
        )

    return GateResult(
        gate="scope",
        status="fail",
        failures=failures,
        summary=summary,
    )
