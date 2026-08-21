"""The `scope` gate: changed files ⊆ touches.

Core, because it operates on the diff as text and paths — no language knowledge
anywhere (DESIGN.md §2.1).
"""

from __future__ import annotations

import re

from saffron.gates.contract import Failure, GateResult

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


def scope_gate(changed_files: list[str], touches: list[str]) -> GateResult:
    if not touches:
        return GateResult(
            gate="scope",
            status="skip",
            summary="no touches declared",
        )

    escaped = [
        path
        for path in changed_files
        if not any(matches(path, pattern) for pattern in touches)
    ]
    if not escaped:
        return GateResult(
            gate="scope",
            status="pass",
            summary=f"{len(changed_files)} changed files within touches",
        )

    # The failure line is the whole channel to the agent (§5.4), and `touches`
    # lives in frontmatter the spec body never carries — so it names them.
    declared = ", ".join(touches)
    return GateResult(
        gate="scope",
        status="fail",
        failures=[
            Failure(
                file=path, code="out-of-scope", message=f"outside touches: {declared}"
            )
            for path in escaped
        ],
        summary=f"{len(escaped)} of {len(changed_files)} changed files outside touches",
    )
