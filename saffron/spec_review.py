"""Reading a spec review's own findings block (ADR 7, `CONTEXT.md`).

A spec review is one host-invoked session, seeded at the tree a spec's own
cell would be cut from. It answers through one fenced ```json block, never
through prose. This module trusts nothing about that text beyond what it
can parse and validate itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, get_args

from saffron.agents.artifacts import hash_artifact
from saffron.agents.findings import Severity

# The tags a `concern` or `blocker` can name as its own fix. Looked up by
# name at call time, never bound to a local, so a patched tuple is honored.
SPEC_REVIEW_TAGS: tuple[str, ...] = ("scope", "build", "witness")


@dataclass(frozen=True)
class SpecReviewSession:
    """What a `review` callable returns for one spec.

    `resets_at` is set only when the session met the account's own rate
    limit, and is the one field a `wait` route is driven by
    (`spec_review_route`). `session_id` and `num_turns` default for every
    caller that predates them, and feed the attempt row the batch opens
    around the review."""

    text: str
    cost_usd: float
    error: str | None
    resets_at: int | None = None
    session_id: str | None = None
    num_turns: int = 0


@dataclass(frozen=True)
class SpecReviewFinding:
    """One entry of a review's `findings` list, kept as read."""

    severity: Severity
    claim: str
    fixes: str | None
    criterion: str | None
    file: str | None
    line: int | None


@dataclass(frozen=True)
class SpecReview:
    """`read_spec_review`'s own reading of one session's last `json` block.

    `block` is the fenced text itself, kept whatever the route, and `None`
    only when no ```json fence was found at all. `block_sha256` is
    `hash_artifact` of it, or `None` beside it."""

    findings: list[SpecReviewFinding]
    cost_usd: float
    error: str | None
    resets_at: int | None
    block: str | None
    block_sha256: str | None


def _last_json_block(text: str) -> str | None:
    """The body of the last fenced ```json block in `text`, or `None`.

    A block opens at a line that is exactly ```` ```json ```` and closes at
    the next line that holds only ```` ``` ````. Backticks anywhere else on
    a line, mid-claim included, close nothing."""
    lines = text.splitlines()
    found: list[str] | None = None
    i = 0
    while i < len(lines):
        if lines[i] != "```json":
            i += 1
            continue
        start = i + 1
        end = start
        while end < len(lines) and lines[end] != "```":
            end += 1
        if end >= len(lines):
            break
        found = lines[start:end]
        i = end + 1
    return "\n".join(found) if found is not None else None


def _error(
    session: SpecReviewSession,
    message: str,
    *,
    block: str | None,
    block_sha256: str | None,
) -> SpecReview:
    return SpecReview(
        findings=[],
        cost_usd=session.cost_usd,
        error=message,
        resets_at=session.resets_at,
        block=block,
        block_sha256=block_sha256,
    )


def read_spec_review(session: SpecReviewSession) -> SpecReview:
    """Read `session`'s last ```json block into a `SpecReview`.

    Any text that is not one clean object with a `findings` list of valid
    findings routes `error` (`spec_review_route`), rather than being read as
    partly clean. `fixes` is kept on every finding, whatever its severity.
    The fenced text itself is kept as `block` on every path, including an
    unreadable one, so a caller can record what the session said."""
    block = _last_json_block(session.text)
    block_sha256 = hash_artifact(block) if block is not None else None
    if session.error is not None:
        return _error(session, session.error, block=block, block_sha256=block_sha256)
    if block is None:
        return _error(
            session,
            "no fenced json block in spec review text",
            block=block,
            block_sha256=block_sha256,
        )
    try:
        parsed = json.loads(block)
    except json.JSONDecodeError as exc:
        return _error(
            session,
            f"spec review json block did not parse: {exc}",
            block=block,
            block_sha256=block_sha256,
        )
    if not isinstance(parsed, dict):
        return _error(
            session,
            "spec review json block is not an object",
            block=block,
            block_sha256=block_sha256,
        )
    raw_findings = parsed.get("findings")
    if not isinstance(raw_findings, list):
        return _error(
            session,
            "spec review findings is not a list",
            block=block,
            block_sha256=block_sha256,
        )

    findings: list[SpecReviewFinding] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            return _error(
                session,
                "spec review finding is not an object",
                block=block,
                block_sha256=block_sha256,
            )
        severity = raw.get("severity")
        if severity not in get_args(Severity):
            return _error(
                session,
                f"spec review finding has an unknown severity: {severity!r}",
                block=block,
                block_sha256=block_sha256,
            )
        claim = raw.get("claim")
        if not isinstance(claim, str):
            return _error(
                session,
                "spec review finding has no claim",
                block=block,
                block_sha256=block_sha256,
            )
        fixes = raw.get("fixes")
        if fixes is not None and fixes not in SPEC_REVIEW_TAGS:
            return _error(
                session,
                f"spec review finding has an unfixable tag: {fixes!r}",
                block=block,
                block_sha256=block_sha256,
            )
        findings.append(
            SpecReviewFinding(
                severity=severity,
                claim=claim,
                fixes=fixes,
                criterion=raw.get("criterion"),
                file=raw.get("file"),
                line=raw.get("line"),
            )
        )
    return SpecReview(
        findings=findings,
        cost_usd=session.cost_usd,
        error=None,
        resets_at=session.resets_at,
        block=block,
        block_sha256=block_sha256,
    )


def spec_review_route(
    review: SpecReview,
) -> Literal["wait", "run", "escalate", "error"]:
    """Route one read: `wait` before any other check, then `error`, then
    `escalate` for any `blocker`, whatever its `fixes`, else `run`."""
    if review.resets_at is not None:
        return "wait"
    if review.error is not None:
        return "error"
    if any(finding.severity == "blocker" for finding in review.findings):
        return "escalate"
    return "run"
