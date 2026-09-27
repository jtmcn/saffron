"""Reading a spec review's own findings block (ADR 7, `CONTEXT.md`).

A spec review is one host-invoked session, seeded at the tree a spec's own
cell would be cut from. It answers through one fenced ```json block, never
through prose. This module trusts nothing about that text beyond what it
can parse and validate itself.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, ValidationError

from saffron.agents import context
from saffron.agents.artifacts import hash_artifact
from saffron.agents.findings import Severity
from saffron.cell import session
from saffron.gates.core import size
from saffron.phases import implement
from saffron.repos.policy import Policy

# The tags a `concern` or `blocker` can name as its own fix. Looked up by
# name at call time, never bound to a local, so a patched tuple is honored.
SPEC_REVIEW_TAGS: tuple[str, ...] = ("scope", "build", "witness")

# One host-invoked session's tools (ADR 7): read-only plus `Bash`, with
# neither `Write` nor `Edit`, so `Bash` runs unprivileged (SA-0169).
SPEC_SESSION_TOOLS = ["Read", "Glob", "Grep", "Bash"]

SPEC_REVIEW_MAX_TURNS = 90

SPEC_REVIEW_BUDGET_USD = 6.0

# The extraction turn and its one re-ask, each a dozen times the spike's own
# extraction turn ($0.08, `docs/evidence/2026-09-23-structured-output-spike.md`).
SPEC_REVIEW_EXTRACT_BUDGET_USD = 1.0

# What one session records at most, best effort: the review turn plus both
# extraction turns.
SPEC_REVIEW_SESSION_USD = SPEC_REVIEW_BUDGET_USD + 2 * SPEC_REVIEW_EXTRACT_BUDGET_USD

# Twice `session.TURN_TIMEOUT_S`. The hand reviews of this chain, run with
# `Bash` on 2026-09-24, took 566 to 681 seconds.
SPEC_REVIEW_TIMEOUT_S = 1800.0

# `if review.resets_at:` reads 0 as unset, so a reset time that is missing,
# unreadable, or at or below 0 is shaped to this instead.
UNREADABLE_RESET = 1

# A file name, not a loaded template: `spec_review_system_prompt` reads it
# fresh from `prompts_dir` on every call.
SPEC_REVIEW_PROMPT = "spec-review.md"

# Loaded once at import, as `rebut.EXTRACT_PROMPT` is.
SPEC_REVIEW_EXTRACT_PROMPT = context.turn_prompt("spec-review-extract")


class _SpecReviewFinding(BaseModel):
    """One finding as the extraction turn's schema demands it.

    Every field is required. A `default` here would let the turn omit one
    rather than answer `null`. Four of the six take `null`. A spec review's
    finding can name no place at all. `fixes` is a tag or none, never a
    tag the model invents. `read_spec_review` checks `SPEC_REVIEW_TAGS` on
    read, not on write."""

    model_config = ConfigDict(extra="forbid")

    severity: Severity
    claim: str
    criterion: int | None
    file: str | None
    line: int | None
    fixes: str | None


class _SpecReviewFindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[_SpecReviewFinding]


# Sent as `output_format`: built once per process, as `rebut._REBUTTALS_FORMAT`
# is (§5.3, backlog b-4e0868).
SPEC_REVIEW_FORMAT = {
    "type": "json_schema",
    "schema": _SpecReviewFindings.model_json_schema(),
}


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
    return "\n".join(found).strip() if found is not None else None


def _error(session: SpecReviewSession, message: str) -> SpecReview:
    block = _last_json_block(session.text)
    block_sha256 = hash_artifact(block) if block is not None else None
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
        return _error(session, session.error)
    if block is None:
        return _error(session, "no fenced json block in spec review text")
    try:
        parsed = json.loads(block)
    except json.JSONDecodeError as exc:
        return _error(session, f"spec review json block did not parse: {exc}")
    if not isinstance(parsed, dict):
        return _error(session, "spec review json block is not an object")
    raw_findings = parsed.get("findings")
    if not isinstance(raw_findings, list):
        return _error(session, "spec review findings is not a list")

    findings: list[SpecReviewFinding] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            return _error(session, "spec review finding is not an object")
        severity = raw.get("severity")
        if severity not in get_args(Severity):
            return _error(
                session, f"spec review finding has an unknown severity: {severity!r}"
            )
        claim = raw.get("claim")
        if not isinstance(claim, str):
            return _error(session, "spec review finding has no claim")
        fixes = raw.get("fixes")
        if fixes is not None and fixes not in SPEC_REVIEW_TAGS:
            return _error(
                session, f"spec review finding has an unfixable tag: {fixes!r}"
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


def _reset(raw: object) -> int:
    """`resets_at`, shaped for a spec review: a clean, positive `int`, or
    `UNREADABLE_RESET`. `session._resets_at_fields` alone still passes 0
    and a negative number through unshaped. `if review.resets_at:` reads
    either as unset, so this floors them too."""
    value, unreadable = session._resets_at_fields(raw)
    if unreadable or value is None or value <= 0:
        return UNREADABLE_RESET
    return value


def _validate(value: object) -> tuple[_SpecReviewFindings | None, str | None]:
    """`value` against `_SpecReviewFindings`, or the `not the schema` error
    naming why. The same two messages `rebut._validate` gives, for the same
    two reasons: a turn that answered with nothing structured, and a turn
    whose answer was the wrong shape."""
    if value is None:
        return None, "not the schema: the turn returned no structured output"
    try:
        return _SpecReviewFindings.model_validate(value), None
    except ValidationError as exc:
        return None, f"not the schema: {exc}"


def _findings_text(report: _SpecReviewFindings) -> str:
    """The host's own serialization of `report`, fenced the way
    `read_spec_review` reads. `model_dump` fixes the key order to the
    model's own. The same findings always hash the same, whatever key
    order the turn's answer arrived in."""
    body = json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False)
    return f"```json\n{body}\n```\n"


def run_spec_review(
    container: str,
    *,
    system_prompt: str,
    prompt: str,
    agent: Callable[..., implement.AttemptResult],
) -> SpecReviewSession:
    """One host-invoked, tool-using session that reads a spec before any
    cell is cut for it (ADR 7). A second turn then extracts its findings
    through `output_format`, never a fenced block this module would have
    to trust.

    Calls `agent` directly, never through `session.stop_on_rejected`.
    That wrapper raises on a rejected window before its caller sees the
    turn's own cost. A rejected review must still be charged for what it
    spent (§4.1).
    """
    options = implement.agent_options(
        system_prompt=system_prompt,
        max_turns=SPEC_REVIEW_MAX_TURNS,
        budget_usd=SPEC_REVIEW_BUDGET_USD,
        tools=SPEC_SESSION_TOOLS,
    )
    cost = 0.0
    turns = 0
    sid: str | None = None

    def _measure(attempt: implement.AttemptResult | None) -> None:
        nonlocal cost, turns, sid
        if attempt is None:
            return
        cost += attempt.cost_usd_est
        turns += attempt.num_turns
        sid = attempt.session_id or sid

    def _rejected(attempt: implement.AttemptResult) -> SpecReviewSession:
        return SpecReviewSession(
            text="",
            cost_usd=cost,
            error=None,
            resets_at=_reset(attempt.rate_limit_resets_at),
            session_id=sid,
            num_turns=turns,
        )

    try:
        first = agent(container, prompt=prompt, options=options)
    except implement.AgentFailed as failed:
        _measure(failed.attempt)
        if failed.attempt and session.terminal_for_rate_limit(
            failed.attempt.rate_limit_status
        ):
            return _rejected(failed.attempt)
        return SpecReviewSession(
            text="",
            cost_usd=cost,
            error=str(failed),
            resets_at=None,
            session_id=sid,
            num_turns=turns,
        )

    if session.terminal_for_rate_limit(first.rate_limit_status):
        _measure(first)
        return _rejected(first)
    _measure(first)
    if first.session_id is None:
        return SpecReviewSession(
            text="",
            cost_usd=cost,
            error="no session to extract from",
            resets_at=None,
            session_id=None,
            num_turns=turns,
        )

    extract_options = options | {
        "max_budget_usd": SPEC_REVIEW_EXTRACT_BUDGET_USD,
        "output_format": SPEC_REVIEW_FORMAT,
    }

    def _extraction_turn(
        *, turn_prompt: str, resume: str | None, last_cost_usd: float
    ) -> SpecReviewSession | implement.AttemptResult:
        """One extraction attempt: a rejected or failed `SpecReviewSession`,
        or the clean `AttemptResult` for the caller to validate."""
        try:
            got = agent(
                container,
                prompt=turn_prompt,
                options=extract_options,
                resume=resume,
                last_cost_usd=last_cost_usd,
            )
        except implement.AgentFailed as failed:
            _measure(failed.attempt)
            if failed.attempt and session.terminal_for_rate_limit(
                failed.attempt.rate_limit_status
            ):
                return _rejected(failed.attempt)
            return SpecReviewSession(
                text="",
                cost_usd=cost,
                error=str(failed),
                resets_at=None,
                session_id=sid,
                num_turns=turns,
            )
        if session.terminal_for_rate_limit(got.rate_limit_status):
            _measure(got)
            return _rejected(got)
        _measure(got)
        return got

    extracted = _extraction_turn(
        turn_prompt=SPEC_REVIEW_EXTRACT_PROMPT,
        resume=first.session_id,
        last_cost_usd=min(first.cost_usd_est, SPEC_REVIEW_EXTRACT_BUDGET_USD),
    )
    if isinstance(extracted, SpecReviewSession):
        return extracted
    report, error = _validate(extracted.structured_output)
    if report is not None:
        return SpecReviewSession(
            text=_findings_text(report),
            cost_usd=cost,
            error=None,
            resets_at=None,
            session_id=sid,
            num_turns=turns,
        )

    # The CLI already retries the shape inside a turn, so this one re-ask is
    # a backstop. No second re-ask: HEAD already holds this attempt's cost.
    reasked = _extraction_turn(
        turn_prompt=f"{error}\n\n{SPEC_REVIEW_EXTRACT_PROMPT}",
        resume=sid,
        last_cost_usd=min(extracted.cost_usd_est, SPEC_REVIEW_EXTRACT_BUDGET_USD),
    )
    if isinstance(reasked, SpecReviewSession):
        return reasked
    report, error = _validate(reasked.structured_output)
    if report is not None:
        return SpecReviewSession(
            text=_findings_text(report),
            cost_usd=cost,
            error=None,
            resets_at=None,
            session_id=sid,
            num_turns=turns,
        )
    return SpecReviewSession(
        text="",
        cost_usd=cost,
        error=error,
        resets_at=None,
        session_id=sid,
        num_turns=turns,
    )


def _gate_lines(policy: Policy) -> str:
    lines = [
        f"- `{name}`" + ("" if decl.blocking else " (advisory)")
        for name, decl in policy.gates.items()
    ]
    return "\n".join(lines) if lines else "none"


def _path_lines(paths: Sequence[str]) -> str:
    return "\n".join(f"- `{path}`" for path in paths) if paths else "none"


def _ceiling_lines() -> str:
    lines = [
        f"- `{spec_type}`: {ceiling} changed tokens"
        for spec_type, ceiling in size._CEILINGS.items()
    ]
    lines.append(f"- any other type: {size._DEFAULT_CEILING} changed tokens")
    return "\n".join(lines)


def _tag_lines() -> str:
    return "\n".join(f"- `{tag}`" for tag in SPEC_REVIEW_TAGS)


def spec_review_system_prompt(policy: Policy, *, prompts_dir: Path) -> str:
    """Core's own spec-review prompt, with the repo's declarations filled
    in as `format` arguments. Never by substituting text and formatting
    the result, which a path like `docs/{a,b}.md` in `protected` would
    break.

    The template is read fresh on every call, not cached at import: a
    ceiling or a tag list can change within one process.
    """
    template = (prompts_dir / SPEC_REVIEW_PROMPT).read_text()
    return template.format(
        gates=_gate_lines(policy),
        protected=_path_lines(policy.protected),
        elevate_on=_path_lines(policy.elevate_on),
        ceilings=_ceiling_lines(),
        tags=_tag_lines(),
    )
