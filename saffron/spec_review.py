"""Reading a spec review's own findings block (ADR 7, `CONTEXT.md`). It also
fills core's spec writer prompt and defines that writer's reply schema.

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

from pydantic import BaseModel, ConfigDict

from saffron import intake
from saffron.agents import context
from saffron.agents.artifacts import hash_artifact
from saffron.agents.findings import Severity
from saffron.cell import session
from saffron.gates.core import size
from saffron.phases import implement, rebut
from saffron.repos.policy import Policy

# The tags a `concern` or `blocker` can name as its own fix. Looked up by
# name at call time, never bound to a local, so a patched tuple is honored.
SPEC_REVIEW_TAGS: tuple[str, ...] = ("scope", "build", "witness")

# The two tags `spec_review_route` revises rather than escalates (ADR 7).
# Named once here, never derived from `SPEC_REVIEW_TAGS`.
SPEC_REVIEW_REVISABLE_TAGS: tuple[str, ...] = ("build", "witness")

# The phase a spec writer session's attempt is opened in (`run_stack_batch`,
# SA-0161's follow-up writer).
WRITING_PHASE = "SPEC_WRITING"

# One host-invoked session's tools (ADR 7): read-only plus `Bash`, with
# neither `Write` nor `Edit`, so `Bash` runs unprivileged (SA-0169).
SPEC_SESSION_TOOLS = ["Read", "Glob", "Grep", "Bash"]

# Measured: the last twelve reviews ran 64 to 102 turns, and SA-0338's was cut at 91.
SPEC_REVIEW_MAX_TURNS = 150

# Reasoned, unmeasured in a batch: SA-0155 records each review's cost.
SPEC_REVIEW_BUDGET_USD = 6.0

# Reasoned, unmeasured in a cell: each is a dozen times the spike's extraction
# turn ($0.08, `docs/evidence/2026-09-23-structured-output-spike.md`).
SPEC_REVIEW_EXTRACT_BUDGET_USD = 1.0

# What one session records at most, best effort: the review turn plus both
# extraction turns.
SPEC_REVIEW_SESSION_USD = SPEC_REVIEW_BUDGET_USD + 2 * SPEC_REVIEW_EXTRACT_BUDGET_USD

# The hand reviews of this chain, run with `Bash` on 2026-09-24, took 566
# to 681 seconds.
SPEC_REVIEW_TIMEOUT_S = 2 * session.TURN_TIMEOUT_S

# SA-0148's wait reads a reset at or before now as unreadable. So a
# missing, unreadable or non-positive reset is shaped to this.
UNREADABLE_RESET = 1


def _merge_models(current: str | None, addition: str | None) -> str | None:
    """`current` plus every name in `addition` not already present, in
    first-seen order, comma-joined or `None` (SA-0205). `addition` is one
    turn's own joined `AttemptResult.model`, split on `,` here. An empty
    segment, from an empty name or a trailing comma, names nothing."""
    names = [] if current is None else current.split(",")
    for name in [] if addition is None else addition.split(","):
        if name and name not in names:
            names.append(name)
    return ",".join(names) if names else None


# A file name, not a loaded template: `spec_review_system_prompt` reads it
# fresh from `prompts_dir` on every call.
SPEC_REVIEW_PROMPT = "spec-review.md"

# Loaded once at import, as `rebut.EXTRACT_PROMPT` is.
SPEC_REVIEW_EXTRACT_PROMPT = context.turn_prompt("spec-review-extract")


class _SpecReviewFinding(BaseModel):
    """One finding as the extraction turn's schema demands it.

    Every field is required. A `default` here would let the turn omit one
    rather than answer `null`. Four of the six take `null`. A spec review's
    finding can name no place at all. `fixes` is any string or null.
    `read_spec_review` alone checks it against `SPEC_REVIEW_TAGS`, when
    called."""

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
    around the review. `model` is every distinct model this session's own
    turns named, first-seen order, comma-joined (SA-0205)."""

    text: str
    cost_usd: float
    error: str | None
    resets_at: int | None = None
    session_id: str | None = None
    num_turns: int = 0
    model: str | None = None


@dataclass(frozen=True)
class SpecReviewFinding:
    """One entry of a review's `findings` list, kept as read."""

    severity: Severity
    claim: str
    fixes: str | None
    criterion: int | None
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
) -> Literal["wait", "run", "escalate", "revise", "error"]:
    """Route one read: `wait` before any other check, then `error`. A
    `blocker` escalates unless every one of them names a tag in
    `SPEC_REVIEW_REVISABLE_TAGS`, in which case the read revises. With no
    blocker, any `concern` tagged `witness` also revises. Anything else
    runs. The tag check runs over the blockers alone, so a concern or a
    note beside a revisable blocker never turns it into an escalation."""
    if review.resets_at is not None:
        return "wait"
    if review.error is not None:
        return "error"
    blockers = [f for f in review.findings if f.severity == "blocker"]
    if blockers:
        if all(b.fixes in SPEC_REVIEW_REVISABLE_TAGS for b in blockers):
            return "revise"
        return "escalate"
    if any(f.severity == "concern" and f.fixes == "witness" for f in review.findings):
        return "revise"
    return "run"


def _reset(raw: object) -> int:
    """`resets_at`, shaped for a spec review: a clean, positive `int`, or
    `UNREADABLE_RESET`. `session._resets_at_fields` alone still passes 0
    and a negative number through unshaped. SA-0148's wait reads either
    as unreadable, so this floors them too."""
    value, unreadable = session._resets_at_fields(raw)
    if unreadable or value is None or value <= 0:
        return UNREADABLE_RESET
    return value


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
    model: str | None = None

    def _measure(attempt: implement.AttemptResult | None) -> None:
        nonlocal cost, turns, sid, model
        if attempt is None:
            return
        cost += attempt.cost_usd_est
        turns += attempt.num_turns
        sid = attempt.session_id or sid
        model = _merge_models(model, attempt.model)

    def _rejected(attempt: implement.AttemptResult) -> SpecReviewSession:
        return SpecReviewSession(
            text="",
            cost_usd=cost,
            error=None,
            resets_at=_reset(attempt.rate_limit_resets_at),
            session_id=sid,
            num_turns=turns,
            model=model,
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
            model=model,
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
            model=model,
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
                model=model,
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
    report, error = rebut._validate(_SpecReviewFindings, extracted.structured_output)
    if report is not None:
        return SpecReviewSession(
            text=_findings_text(report),
            cost_usd=cost,
            error=None,
            resets_at=None,
            session_id=sid,
            num_turns=turns,
            model=model,
        )

    # One re-ask, as run_lens makes (§5.3 says two). The CLI already retries
    # the shape inside a turn.
    reasked = _extraction_turn(
        turn_prompt=f"{error}\n\n{SPEC_REVIEW_EXTRACT_PROMPT}",
        resume=sid,
        last_cost_usd=min(extracted.cost_usd_est, SPEC_REVIEW_EXTRACT_BUDGET_USD),
    )
    if isinstance(reasked, SpecReviewSession):
        return reasked
    report, error = rebut._validate(_SpecReviewFindings, reasked.structured_output)
    if report is not None:
        return SpecReviewSession(
            text=_findings_text(report),
            cost_usd=cost,
            error=None,
            resets_at=None,
            session_id=sid,
            num_turns=turns,
            model=model,
        )
    return SpecReviewSession(
        text="",
        cost_usd=cost,
        error=error,
        resets_at=None,
        session_id=sid,
        num_turns=turns,
        model=model,
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


# A file name, not a loaded template: `spec_writer_system_prompt` reads it
# fresh from `prompts_dir` on every call, as `spec_review_system_prompt` does.
SPEC_WRITER_PROMPT = "spec-writer.md"

# Loaded once at import, as `rebut.EXTRACT_PROMPT` is.
SPEC_WRITER_EXTRACT_PROMPT = context.turn_prompt("spec-writer-extract")

# Loaded once at import, as the other turn prompts are. Sent before a
# send-back's own fault lines (SA-0353).
SPEC_WRITER_SEND_BACK_PROMPT = context.turn_prompt("spec-writer-send-back")


class _SpecWriterReply(BaseModel):
    """The spec writer's whole answer, one required field (ADR 7).

    `extra="forbid"` keeps a stray key out. No default on `spec` refuses a
    reply with no `spec` key. An empty string still validates."""

    model_config = ConfigDict(extra="forbid")

    spec: str


# The spec writer session sends it as `output_format`. Built once per process,
# as `rebut._REBUTTALS_FORMAT` is (§5.3).
SPEC_WRITER_FORMAT = {
    "type": "json_schema",
    "schema": _SpecWriterReply.model_json_schema(),
}


def spec_writer_system_prompt(policy: Policy, *, prompts_dir: Path) -> str:
    """Core's own spec-writer prompt, filled the way `spec_review_system_prompt`
    fills its own template (ADR 7).

    The template is read fresh on every call, not cached at import, for the
    same reason as the review's.
    """
    template = (prompts_dir / SPEC_WRITER_PROMPT).read_text()
    return template.format(
        gates=_gate_lines(policy),
        protected=_path_lines(policy.protected),
        elevate_on=_path_lines(policy.elevate_on),
        ceilings=_ceiling_lines(),
    )


# The p90 of 74 hand `spec-writer` sessions, $16.92, rounded up (SA-0161).
SPEC_WRITER_BUDGET_USD = 17.0

# Reasoned from the spike's own extraction turns, $0.40 and $0.41, with
# room: a real spec writer session resumes a longer context than the spike's did.
SPEC_WRITER_EXTRACT_BUDGET_USD = 1.5

# The operator's bound on how many send-backs one draft gets, read at
# call time so a patched value holds (SA-0353).
SPEC_WRITER_SEND_BACKS = 1

# Reasoned, unmeasured: twice the extraction turn's own budget. A
# send-back's own work turn spends up to this much (SA-0353).
SPEC_WRITER_SEND_BACK_BUDGET_USD = 3.0

# What one session records at most, best effort: the writer's first turn,
# one extraction turn, and each send-back's own work and extraction turns.
SPEC_WRITER_SESSION_USD = (
    SPEC_WRITER_BUDGET_USD
    + SPEC_WRITER_EXTRACT_BUDGET_USD
    + SPEC_WRITER_SEND_BACKS
    * (SPEC_WRITER_SEND_BACK_BUDGET_USD + SPEC_WRITER_EXTRACT_BUDGET_USD)
)

# Reasoned, unmeasured: a third above SPEC_REVIEW_MAX_TURNS, since a spec
# writer session can run longer.
SPEC_WRITER_MAX_TURNS = 200

# Measured: 79 hand `spec-writer` transcripts had a median of 1396 s, and 21 ran
# past 2700 s.
SPEC_WRITER_TIMEOUT_S = 3600.0


@dataclass(frozen=True)
class DraftFaults:
    """One judgement of a draft `run_spec_writer` is about to settle on
    (SA-0353). `parsed` is whether `intake.parse_spec` and
    `intake.refuse_inline_mutants` could read it at all. `lines` is every
    fault line found, in order: the one line an unparseable draft gets, or
    a `judge`'s own rendering of each new failure. Empty `lines` means
    nothing is wrong."""

    parsed: bool
    lines: tuple[str, ...]


def draft_faults(
    text: str,
    *,
    path: str | None,
    judge: Callable[[str, str], Sequence[str]] | None,
    emit: Callable[[str], None],
) -> DraftFaults:
    """Whether `text` is a draft `run_spec_writer` can hand back as is.

    `intake.parse_spec` then `intake.refuse_inline_mutants` read it first
    (SA-0338). A `SpecError` from either ends here: `parsed` is `False`
    and the one line is that error's own message, with nothing judged.
    With no `judge`, a parsing draft gets no fault line. Otherwise
    `judge` runs at `path`, or the spec's own `.saffron/specs/<id>.md`,
    and its lines come back in order. A raise from `judge` reaches no
    writer: `emit` names it once, and no fault line comes back."""
    try:
        spec = intake.parse_spec(text)
        intake.refuse_inline_mutants(spec)
    except intake.SpecError as exc:
        return DraftFaults(parsed=False, lines=(str(exc),))
    if judge is None:
        return DraftFaults(parsed=True, lines=())
    judged_path = path if path is not None else f".saffron/specs/{spec.id}.md"
    try:
        lines = judge(judged_path, text)
    except Exception as exc:
        emit(f"spec writer draft judge raised {type(exc).__name__}: {exc}")
        return DraftFaults(parsed=True, lines=())
    return DraftFaults(parsed=True, lines=tuple(lines))


@dataclass(frozen=True)
class SpecWriterSession:
    """What `run_spec_writer` returns for one draft or revision.

    `text` is the newest text `faults` found parsed, or the newest text
    when none parsed (SA-0353). Neither turn's own `text` feeds it.
    `spec_sha` is `hash_artifact` of it, or `None` beside empty text.
    `model` is every distinct model this session's own turns named,
    first-seen order, comma-joined (SA-0205). `fault_lines` is the lines
    `faults` last found for `text`, once the send-backs ran out or the
    session gave up."""

    text: str
    cost_usd: float
    error: str | None
    resets_at: int | None
    session_id: str | None
    num_turns: int
    spec_sha: str | None
    model: str | None = None
    fault_lines: tuple[str, ...] = ()


def _writer_session(
    *,
    text: str,
    cost: float,
    error: str | None,
    resets_at: int | None,
    session_id: str | None,
    turns: int,
    model: str | None = None,
    fault_lines: tuple[str, ...] = (),
) -> SpecWriterSession:
    return SpecWriterSession(
        text=text,
        cost_usd=cost,
        error=error,
        resets_at=resets_at,
        session_id=session_id,
        num_turns=turns,
        spec_sha=hash_artifact(text) if text else None,
        model=model,
        fault_lines=fault_lines,
    )


def run_spec_writer(
    container: str,
    *,
    system_prompt: str,
    prompt: str,
    agent: Callable[..., implement.AttemptResult],
    faults: Callable[[str], DraftFaults],
    emit: Callable[[str], None],
) -> SpecWriterSession:
    """One host-invoked, tool-using session that drafts or revises a whole
    spec file (ADR 7). A second turn then extracts the file through
    `output_format`, resumed on the same session, never read from either
    turn's own text. `faults` can send a validated text back for a bounded
    number of send-backs before it settles (SA-0353).

    Calls `agent` directly, never through `session.stop_on_rejected`: a
    rejected session must still be charged for what it spent (§4.1)."""
    options = implement.agent_options(
        system_prompt=system_prompt,
        max_turns=SPEC_WRITER_MAX_TURNS,
        budget_usd=SPEC_WRITER_BUDGET_USD,
        tools=SPEC_SESSION_TOOLS,
    )
    cost = 0.0
    turns = 0
    sid: str | None = None
    model: str | None = None

    def _measure(attempt: implement.AttemptResult | None) -> None:
        nonlocal cost, turns, sid, model
        if attempt is None:
            return
        cost += attempt.cost_usd_est
        turns += attempt.num_turns
        sid = attempt.session_id or sid
        model = _merge_models(model, attempt.model)

    def _rejected(attempt: implement.AttemptResult) -> SpecWriterSession:
        return _writer_session(
            text="",
            cost=cost,
            error=None,
            resets_at=_reset(attempt.rate_limit_resets_at),
            session_id=sid,
            turns=turns,
            model=model,
        )

    try:
        first = agent(container, prompt=prompt, options=options)
    except implement.AgentFailed as failed:
        _measure(failed.attempt)
        if failed.attempt and session.terminal_for_rate_limit(
            failed.attempt.rate_limit_status
        ):
            return _rejected(failed.attempt)
        return _writer_session(
            text="",
            cost=cost,
            error=str(failed),
            resets_at=None,
            session_id=sid,
            turns=turns,
            model=model,
        )

    if session.terminal_for_rate_limit(first.rate_limit_status):
        _measure(first)
        return _rejected(first)
    _measure(first)
    if first.session_id is None:
        return _writer_session(
            text="",
            cost=cost,
            error="no session to extract from",
            resets_at=None,
            session_id=None,
            turns=turns,
            model=model,
        )

    extract_options = options | {
        "max_budget_usd": SPEC_WRITER_EXTRACT_BUDGET_USD,
        "output_format": SPEC_WRITER_FORMAT,
    }

    def _extraction_turn(
        *, turn_prompt: str, resume: str | None, last_cost_usd: float
    ) -> SpecWriterSession | implement.AttemptResult:
        """One extraction attempt: a rejected or failed `SpecWriterSession`,
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
            return _writer_session(
                text="",
                cost=cost,
                error=str(failed),
                resets_at=None,
                session_id=sid,
                turns=turns,
                model=model,
            )
        if session.terminal_for_rate_limit(got.rate_limit_status):
            _measure(got)
            return _rejected(got)
        _measure(got)
        return got

    def _read(attempt: implement.AttemptResult) -> tuple[str | None, str | None]:
        report, error = rebut._validate(_SpecWriterReply, attempt.structured_output)
        if report is None:
            return None, error
        return report.spec.strip() + "\n", None

    def _send_back_turn(
        *,
        turn_prompt: str,
        resume: str | None,
        turn_options: dict,
        last_cost_usd: float,
    ) -> implement.AttemptResult | str:
        """One send-back's call: the clean `AttemptResult`, or a `str`
        naming the failure. A send-back's own rate limit is a failure here,
        never a wait (SA-0353). `_rejected` is for the turns before any
        send-back alone."""
        try:
            got = agent(
                container,
                prompt=turn_prompt,
                options=turn_options,
                resume=resume,
                last_cost_usd=last_cost_usd,
            )
        except implement.AgentFailed as failed:
            _measure(failed.attempt)
            return str(failed)
        _measure(got)
        if session.terminal_for_rate_limit(got.rate_limit_status):
            return "rate limited"
        return got

    def _settle(text: str, last_cost_usd: float) -> SpecWriterSession:
        """`text`, or a send-back's own replacement, judged by `faults`
        until one is clean or `SPEC_WRITER_SEND_BACKS` is spent (SA-0353).
        The session's own text is then the newest one `faults` found
        parsed, or the newest of all when none did."""
        newest_parsed: str | None = None
        newest_any = text
        newest_parsed_lines: tuple[str, ...] = ()
        newest_any_lines: tuple[str, ...] = ()

        def _record(candidate: str, outcome: DraftFaults) -> None:
            nonlocal newest_parsed, newest_any, newest_parsed_lines, newest_any_lines
            newest_any = candidate
            newest_any_lines = tuple(outcome.lines)
            if outcome.parsed:
                newest_parsed = candidate
                newest_parsed_lines = tuple(outcome.lines)

        def _finish() -> SpecWriterSession:
            return _writer_session(
                text=newest_parsed if newest_parsed is not None else newest_any,
                cost=cost,
                error=None,
                resets_at=None,
                session_id=sid,
                turns=turns,
                model=model,
                fault_lines=(
                    newest_parsed_lines
                    if newest_parsed is not None
                    else newest_any_lines
                ),
            )

        def _give_up(message: str, lines: Sequence[str]) -> SpecWriterSession:
            emit(message)
            for line in lines:
                emit(line)
            return _finish()

        outcome = faults(text)
        _record(text, outcome)
        send_backs = 0
        while outcome.lines and send_backs < SPEC_WRITER_SEND_BACKS:
            send_backs += 1
            lines = outcome.lines
            work = _send_back_turn(
                turn_prompt=SPEC_WRITER_SEND_BACK_PROMPT + "\n" + "\n".join(lines),
                resume=sid,
                turn_options=options
                | {"max_budget_usd": SPEC_WRITER_SEND_BACK_BUDGET_USD},
                last_cost_usd=min(last_cost_usd, SPEC_WRITER_SEND_BACK_BUDGET_USD),
            )
            if isinstance(work, str):
                return _give_up(f"spec writer send-back's work turn {work}", lines)

            extracted_again = _send_back_turn(
                turn_prompt=SPEC_WRITER_EXTRACT_PROMPT,
                resume=work.session_id,
                turn_options=extract_options,
                last_cost_usd=min(work.cost_usd_est, SPEC_WRITER_EXTRACT_BUDGET_USD),
            )
            if isinstance(extracted_again, str):
                return _give_up(
                    f"spec writer send-back's extraction turn {extracted_again}", lines
                )

            new_text, read_error = _read(extracted_again)
            if new_text is None:
                return _give_up(
                    f"spec writer send-back's extraction {read_error}", lines
                )

            last_cost_usd = extracted_again.cost_usd_est
            outcome = faults(new_text)
            _record(new_text, outcome)
        return _finish()

    extracted = _extraction_turn(
        turn_prompt=SPEC_WRITER_EXTRACT_PROMPT,
        resume=first.session_id,
        last_cost_usd=min(first.cost_usd_est, SPEC_WRITER_EXTRACT_BUDGET_USD),
    )
    if isinstance(extracted, SpecWriterSession):
        return extracted
    text, error = _read(extracted)
    if text is not None:
        return _settle(text, extracted.cost_usd_est)

    # One re-ask, as run_spec_review makes (§5.3 says two). The CLI already
    # retries the shape inside a turn.
    reasked = _extraction_turn(
        turn_prompt=f"{error}\n\n{SPEC_WRITER_EXTRACT_PROMPT}",
        resume=sid,
        last_cost_usd=min(extracted.cost_usd_est, SPEC_WRITER_EXTRACT_BUDGET_USD),
    )
    if isinstance(reasked, SpecWriterSession):
        return reasked
    text, error = _read(reasked)
    if text is not None:
        return _settle(text, reasked.cost_usd_est)
    return _writer_session(
        text="",
        cost=cost,
        error=error,
        resets_at=None,
        session_id=sid,
        turns=turns,
        model=model,
    )
