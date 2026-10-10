"""Phase 4b — REBUT: one rebuttal, then the critic's verdict (DESIGN.md §5.6).

The order the design left ambiguous, settled here: anchored blockers → the
implementer rebuts → the critic verdicts each one. "Confirmed" in §5.6 is the
host's anchoring (§5.5), which already established the finding points at real
changed code; a critic that verdicts before it has seen the argument is
restating rather than disagreeing, and the recorded disagreement is the entire
product of this phase.

The implementer *resumes*: it already holds the plan, the diff it wrote and the
vocabulary, so REBUT injects none of its own (§5.3). Each verdict is a fresh
read-only session that sees the argument and never the transcript behind it.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from saffron.agents import context
from saffron.agents.findings import Finding
from saffron.cell.worktree import CriticPatchRejected, CriticPatchUnrepresentable
from saffron.events import Agent, Event, PhaseStart, describe
from saffron.intake import Criterion
from saffron.phases import implement, review

VERDICT_PROMPT_FILE = "rebut-verdict.md"

REBUT_PROMPT = context.turn_prompt("rebut")

VERDICT_TURN_PROMPT = context.turn_prompt("verdict")

EXTRACT_PROMPT = context.turn_prompt("rebut-extract")


class Rebuttal(BaseModel):
    """The implementer's answer to one blocker — §4.1's `findings.rebuttal`."""

    finding: int
    action: Literal["fixed", "argued"]
    # An empty argument is not an argument. `fixed` carries one too: the critic
    # verdicts on what the implementer says it changed, not on the diff alone.
    argument: str = Field(min_length=1)


class _Rebuttals(BaseModel):
    rebuttals: list[Rebuttal]


class Verdict(BaseModel):
    """The critic's confirmed, withdrawn or contradicted, as §4.1's `findings.verdict`.
    Never the operator's `adjudication`, which happens in GitHub against a PR."""

    finding: int
    verdict: Literal["confirmed", "withdrawn", "contradicted"]
    reason: str
    # Required only with `contradicted`, by the host's check below, not by
    # this schema: every verdict validates with or without them.
    rebuttal_quote: str | None = None
    finding_quote: str | None = None


class _Verdicts(BaseModel):
    verdicts: list[Verdict]


# Sent as `output_format`: the schema the host already validates against,
# generated once per process (§5.3, backlog b-4e0868).
_REBUTTALS_FORMAT = {"type": "json_schema", "schema": _Rebuttals.model_json_schema()}
_VERDICTS_FORMAT = {"type": "json_schema", "schema": _Verdicts.model_json_schema()}


def _validate[Model: BaseModel](
    model: type[Model], value: object
) -> tuple[Model | None, str | None]:
    """`value` against `model`, or the `not the schema` error naming why.

    A `None` value means the turn produced no structured reply at all. A
    shape `model_validate` rejects means the turn replied with the wrong
    schema instead.
    """
    if value is None:
        return None, "not the schema: the turn returned no structured output"
    try:
        return model.model_validate(value), None
    except ValidationError as exc:
        return None, f"not the schema: {exc}"


@dataclass
class RebuttalTurn:
    """What the implementer's one attempt produced."""

    rebuttals: list[Rebuttal] = field(default_factory=list)
    cost_usd: float = 0.0
    session_id: str | None = None
    error: str | None = None
    """Set when no rebuttal was recorded — a failed turn, or output that was not
    the schema. Never the same value as "argued nothing" (§4.3)."""


@dataclass
class LensVerdicts:
    """One lens's verdicts on its own blockers."""

    lens: str
    verdicts: list[Verdict] = field(default_factory=list)
    cost_usd: float = 0.0
    error: str | None = None
    # Set only when `error` is too: the runner reported that `query` yielded
    # no message before this session raised (backlog item b-8487de).
    never_started: bool = False
    # One entry per `contradicted` verdict the host's quote check rejected.
    quote_failures: list[dict] = field(default_factory=list)
    # One entry per `withdrawn` verdict the guard below refused, keyed by
    # finding number and carrying the lens's own reason (backlog b-cd5fd2).
    withdrawal_refusals: list[dict] = field(default_factory=list)


@dataclass
class RebutResult:
    state: str
    why: str
    rebuttal: RebuttalTurn
    verdicts: list[LensVerdicts]
    moved: bool
    cost_usd: float

    def as_dict(self, blockers: Sequence[Finding]) -> dict:
        """The phase's record. The ledger has no `findings` table, so `verdict`
        and `rebuttal` have nowhere to go but this artifact (§4.1)."""
        return {
            "state": self.state,
            "why": self.why,
            "head_moved": self.moved,
            "cost_usd": self.cost_usd,
            "blockers": [
                {"finding": n, **f.model_dump()} for n, f in enumerate(blockers, 1)
            ],
            "rebuttal": {
                "error": self.rebuttal.error,
                "rebuttals": [r.model_dump() for r in self.rebuttal.rebuttals],
            },
            "verdicts": [
                {
                    "lens": v.lens,
                    "error": v.error,
                    "cost_usd": v.cost_usd,
                    "never_started": v.never_started,
                    "verdicts": [d.model_dump() for d in v.verdicts],
                    "quote_failures": v.quote_failures,
                    "withdrawal_refusals": v.withdrawal_refusals,
                }
                for v in self.verdicts
            ],
        }


def _blocker_line(n: int, f: Finding) -> str:
    """One numbered blocker, plus its probe when the probe is why it is here
    (backlog item 117): a `survived` verdict is the tests not noticing the
    edit, and the implementer is shown that edit so it can see what was
    missed. A blocker whose probe was `unproven` — or that carries none —
    shows nothing the host does not actually know."""
    line = f"{n}. [{f.lens}] {f.file}:{f.line} — {f.claim}"
    if f.probe_verdict == "survived" and f.probe is not None:
        line += (
            f" (its probe survived: in {f.probe.file}, `{f.probe.find}` -> "
            f"`{f.probe.replace}`, and no test able to decide it failed)"
        )
    return line


def blocker_lines(numbered: Sequence[tuple[int, Finding]]) -> str:
    """Blockers as prompt text, numbered so a rebuttal and a verdict can name
    one. The numbers are global across the phase: a lens is shown only its own
    blockers, but under the numbers the implementer answered."""
    return "\n".join(_blocker_line(n, f) for n, f in numbered)


def run_rebuttal(
    container: str,
    *,
    blockers: Sequence[tuple[int, Finding]],
    options: dict,
    session_id: str,
    agent: Callable[..., implement.AttemptResult],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
    last_cost_usd: float = 0.0,
) -> RebuttalTurn:
    """The implementer's one attempt, plus the turn that records it.

    Two turns, because §5.3 allows exactly one way to produce a structured
    artifact: an extraction turn that forbids further action. Asking for the fix
    and the JSON in one breath produces neither reliably.
    """
    try:
        attempt = agent(
            container,
            prompt=REBUT_PROMPT.format(blockers=blocker_lines(blockers)),
            options=options,
            resume=session_id,
            emit=emit,
            last_cost_usd=last_cost_usd,
        )
    except implement.AgentFailed as failed:
        # No extraction turn is bought for a turn that already failed. The
        # caller still measures HEAD: a bound firing must not discard a commit
        # the attempt did make (§4.3).
        cost = failed.attempt.cost_usd_est if failed.attempt else 0.0
        return RebuttalTurn(cost_usd=cost, session_id=session_id, error=str(failed))

    session_id = attempt.session_id or session_id
    try:
        extracted = agent(
            container,
            prompt=EXTRACT_PROMPT,
            options=options | {"output_format": _REBUTTALS_FORMAT},
            resume=session_id,
            emit=emit,
            last_cost_usd=attempt.cost_usd_est,
        )
    except implement.AgentFailed as failed:
        cost = attempt.cost_usd_est + (
            failed.attempt.cost_usd_est if failed.attempt else 0.0
        )
        return RebuttalTurn(cost_usd=cost, session_id=session_id, error=str(failed))

    spent = attempt.cost_usd_est + extracted.cost_usd_est
    session_id = extracted.session_id or session_id
    # No re-prompt, as with REVIEW's extraction: the plan checkpoint retries
    # because a rejected plan costs an attempt that has not happened yet.
    # This attempt is already made, and HEAD already says what it did.
    report, error = _validate(_Rebuttals, extracted.structured_output)
    if error or report is None:
        return RebuttalTurn(
            cost_usd=spent, session_id=session_id, error=error or "not the schema"
        )
    return RebuttalTurn(
        rebuttals=report.rebuttals, cost_usd=spent, session_id=session_id
    )


def verdict_prompt(
    lens: str,
    *,
    blockers: Sequence[tuple[int, Finding]],
    rebuttal: RebuttalTurn,
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
    spec_body: str,
    reviewed_diff: str,
    diff: str,
) -> str:
    """The verdict session's system prompt.

    It takes REVIEW's vocabulary sections: this is a fresh critic session, so
    §5.3's "REBUT injects nothing" — which is about the *resumed implementer* —
    does not reach it, and a session with no vocabulary would be verdicting
    against terms it was never given.

    Two diffs, never one: `reviewed_diff` is the tree the blockers' line
    numbers were filed against — REVIEW's own, exported once and handed
    through, never re-exported — and `diff` is the tree as it now stands,
    after the rebuttal. The template names both by heading so the critic
    reads a blocker's line number against the tree it was actually filed on.
    """
    # Filtered to this lens's own blockers: `run_verdict` requires the verdict
    # set to match `blockers` exactly, so showing arguments it may not verdict
    # on fails the phase on prompt shape rather than on disagreement.
    mine = {n for n, _ in blockers}
    argued = "\n\n".join(
        f"On finding {r.finding}, the implementer {r.action}: {r.argument}"
        for r in rebuttal.rebuttals
        if r.finding in mine
    )
    template = (prompts_dir / VERDICT_PROMPT_FILE).read_text()
    return context.build_system_prompt(
        "REVIEW",
        context_md,
        template=template,
        spec=spec_body,
        diff=diff,
        reviewed_diff=reviewed_diff,
        blockers=blocker_lines(blockers),
        rebuttal=argued or "The implementer recorded no argument.",
        standing_instructions=context.standing_instructions(claude_md),
    )


def _never_started(event: Event) -> bool:
    """The runner reported that `query` yielded no message before this
    session raised (backlog item b-8487de). `event.event` is `None` for a reap
    line, a quarantined raw line or a host-authored fact. None of those
    say whether `query` ran, so they pass over rather than reset this."""
    return (
        isinstance(event, Agent)
        and event.event is not None
        and event.event.get("type") == "error"
        and event.event.get("query_yielded") is False
    )


def run_verdict(
    container: str,
    *,
    lens: str,
    blockers: Sequence[tuple[int, Finding]],
    system_prompt: str,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> LensVerdicts:
    """One lens, one fresh read-only session. `resume` is never passed, for the
    same reason as REVIEW: the critic must see the argument, not the session
    that wrote it."""
    options = implement.agent_options(
        system_prompt=system_prompt,
        max_turns=max_turns,
        budget_usd=budget_usd,
        tools=review.REVIEW_TOOLS,
    ) | {"output_format": _VERDICTS_FORMAT}
    never_started = False

    def _watch(event: Event) -> None:
        nonlocal never_started
        never_started = never_started or _never_started(event)
        emit(event)

    try:
        attempt = agent(
            container, prompt=VERDICT_TURN_PROMPT, options=options, emit=_watch
        )
    except implement.AgentFailed as failed:
        cost = failed.attempt.cost_usd_est if failed.attempt else 0.0
        return LensVerdicts(
            lens, cost_usd=cost, error=str(failed), never_started=never_started
        )
    report, error = _validate(_Verdicts, attempt.structured_output)
    if error or report is None:
        return LensVerdicts(
            lens, cost_usd=attempt.cost_usd_est, error=error or "not the schema"
        )
    asked = {n for n, _ in blockers}
    given = {v.finding for v in report.verdicts}
    if given != asked:
        # A blocker left unverdicted must not read as withdrawn — that is the
        # one direction this phase must never guess in.
        return LensVerdicts(
            lens,
            cost_usd=attempt.cost_usd_est,
            error=f"verdicted {sorted(given)}, asked about {sorted(asked)}",
        )
    return LensVerdicts(lens, verdicts=report.verdicts, cost_usd=attempt.cost_usd_est)


def _normalized(text: str | None) -> str:
    """`text` with every run of whitespace collapsed to one space and both
    ends stripped, or the empty string for `None`."""
    return " ".join((text or "").split())


def _contradiction_failure(
    rebuttal_quote: str | None, finding_quote: str | None, spec_body: str
) -> str | None:
    """Why a `contradicted` verdict's quotes fail the host's check, or `None`
    when both hold. Checked in order: the rebuttal's quote, the finding's
    quote, then whether the two are equal. A pair that is both absent and
    equal still names the missing quote first."""
    spec_text = _normalized(spec_body)
    rebuttal = _normalized(rebuttal_quote)
    if not rebuttal or rebuttal not in spec_text:
        return "the rebuttal's quote is not in the spec text"
    finding = _normalized(finding_quote)
    if not finding or finding not in spec_text:
        return "the finding's quote is not in the spec text"
    if rebuttal == finding:
        return "the two quotes are the same spec text"
    return None


def _check_contradictions(lens_verdicts: LensVerdicts, spec_body: str) -> None:
    """Every `contradicted` verdict in `lens_verdicts`, checked against
    `spec_body` and mutated in place. A verdict that fails the check becomes
    a `confirmed` one carrying the lens's own reason and no quotes. The
    failure is recorded in `lens_verdicts.quote_failures` under this lens."""
    kept: list[Verdict] = []
    failures: list[dict] = []
    for verdict in lens_verdicts.verdicts:
        if verdict.verdict != "contradicted":
            kept.append(verdict)
            continue
        reason = _contradiction_failure(
            verdict.rebuttal_quote, verdict.finding_quote, spec_body
        )
        if reason is None:
            kept.append(verdict)
            continue
        failures.append(
            {
                "finding": verdict.finding,
                "reason": reason,
                "rebuttal_quote": verdict.rebuttal_quote,
                "finding_quote": verdict.finding_quote,
            }
        )
        kept.append(
            Verdict(finding=verdict.finding, verdict="confirmed", reason=verdict.reason)
        )
    lens_verdicts.verdicts = kept
    lens_verdicts.quote_failures = failures


# The host's own sentence ahead of a refused withdrawal's reason: a
# `preserves` criterion holds over the whole file (backlog b-cd5fd2).
_WITHDRAWAL_REFUSED_REASON = (
    "The host kept this blocker: its criterion is `preserves`, so it holds "
    "over the whole file, and no committed fix answered it. The lens withdrew it:"
)


def _guarded_blockers(
    numbered: Sequence[tuple[int, Finding]], acceptance: Sequence[Criterion]
) -> set[int]:
    """Blocker numbers whose claim opens with a `preserves` criterion's own
    guard text: `review.HOST_FILED`, that criterion's witness, then
    `' stayed green with '`. `survivor_finding` writes that exact prefix for
    the criterion's own edit and for a wrong version alike. A shared witness
    still guards a survivor of the other criterion. Nothing here tells the
    two apart, and keeping a blocker is the safe direction.
    """
    prefixes = tuple(
        f"{review.HOST_FILED}{criterion.witness} stayed green with "
        for criterion in acceptance
        if criterion.preserves
    )
    return {
        n
        for n, finding in numbered
        if any(finding.claim.startswith(prefix) for prefix in prefixes)
    }


def _check_withdrawal_refusals(
    lens_verdicts: LensVerdicts,
    *,
    guarded: set[int],
    answers: Mapping[int, Rebuttal],
    moved: bool,
) -> None:
    """Every `withdrawn` verdict in `lens_verdicts` on a guarded blocker,
    checked and mutated in place. It stands only when the blocker's first
    answer was `fixed` and HEAD moved. Every other one becomes `confirmed`,
    the host's sentence ahead of the lens's own reason and no quotes. The
    refusal is recorded in `lens_verdicts.withdrawal_refusals` under this
    lens (backlog b-cd5fd2)."""
    kept: list[Verdict] = []
    refusals: list[dict] = []
    for verdict in lens_verdicts.verdicts:
        if verdict.verdict != "withdrawn" or verdict.finding not in guarded:
            kept.append(verdict)
            continue
        answer = answers.get(verdict.finding)
        if moved and answer is not None and answer.action == "fixed":
            kept.append(verdict)
            continue
        refusals.append(
            {"finding": verdict.finding, "withdrawn_reason": verdict.reason}
        )
        kept.append(
            Verdict(
                finding=verdict.finding,
                verdict="confirmed",
                reason=f"{_WITHDRAWAL_REFUSED_REASON} {verdict.reason}",
            )
        )
    lens_verdicts.verdicts = kept
    lens_verdicts.withdrawal_refusals = refusals


def rebut_state(
    *, moved: bool, rebuttal: RebuttalTurn, verdicts: Sequence[LensVerdicts]
) -> tuple[str, str]:
    """The task's state after REBUT, and the line that says why.

    Doneness is measured, never reported (§4.3): HEAD moved, or an explicit
    recorded argument. A turn that claims a fix it did not commit produced
    neither, and §3.3 has no state for it — `NOT_IMPLEMENTED` is IMPLEMENT's
    measurement and would name the wrong phase — so the task halts at
    `REBUTTING`, which is where it actually stopped.
    """
    argued = [r for r in rebuttal.rebuttals if r.action == "argued"]
    claimed = [r for r in rebuttal.rebuttals if r.action == "fixed"]
    if not moved and not argued:
        detail = (
            f"claimed a fix for {len(claimed)} blocker(s) and committed nothing"
            if claimed
            else rebuttal.error or "recorded nothing"
        )
        return (
            "REBUTTING",
            f"the rebuttal moved no commit and made no argument: {detail}",
        )
    if never_started := [v for v in verdicts if v.error and v.never_started]:
        # Infrastructure, not the critic's output (§3.3). No other lens is
        # named, whatever else in `verdicts` also carries an error.
        names = [v.lens for v in never_started]
        detail = "; ".join(v.error or "" for v in never_started)
        return "GATE_ERROR", f"{names} never started: {detail}"
    if errored := [v.lens for v in verdicts if v.error]:
        return "REBUTTING", f"{errored} produced no verdict — the rebuttal is unjudged"
    confirmed = [
        v for lens in verdicts for v in lens.verdicts if v.verdict == "confirmed"
    ]
    contradicted = [
        v for lens in verdicts for v in lens.verdicts if v.verdict == "contradicted"
    ]
    unfixed = (
        " (a fix was claimed for some of them and no commit was made)"
        if (claimed and not moved)
        else ""
    )
    if contradicted:
        # The check demoted a failing quote pair to `confirmed`. What remains
        # here is a real disagreement between two lines of the same spec.
        return "READY_FOR_REVIEW", (
            f"{len(confirmed)} blocker(s) confirmed after the rebuttal, "
            f"{len(contradicted)} on spec lines that contradict each other, "
            f"{len(argued)} argued — recorded disagreement, yours to adjudicate"
            + unfixed
        )
    if confirmed:
        # No state for "the critic was right": adjudication is the operator's,
        # in GitHub (§5.6). What the phase owes them is the disagreement.
        return "READY_FOR_REVIEW", (
            f"{len(confirmed)} blocker(s) confirmed after the rebuttal, "
            f"{len(argued)} argued — recorded disagreement, yours to adjudicate"
            + unfixed
        )
    return "READY_FOR_REVIEW", f"every blocker withdrawn by its own lens{unfixed}"


def first_answers(rebuttal: RebuttalTurn) -> dict[int, Rebuttal]:
    """The rebuttal keyed by blocker number, first answer winning.

    Nothing in `_Rebuttals` constrains the model to one entry per `finding`,
    and three places read this field: the ledger, the queue's counts, and the
    pull request's Disagreements table. They disagreed — two took the first
    answer, one took the last — so the same duplicate rendered as `fixed` in
    the record and `argued` to the operator reading the PR. The rule lives
    here now; a caller that wants a different one is a caller with a bug.
    """
    answered: dict[int, Rebuttal] = {}
    for r in rebuttal.rebuttals:
        answered.setdefault(r.finding, r)
    return answered


def _confirmed_with(rebut_result: RebutResult, action: str) -> int:
    """Blockers whose first answer was `action` and whose verdict kept it standing.

    One body for both counts below, which differ only in the action they pair.
    Copied, they would be two rules for one queue row the first time somebody
    tightened either — the divergence `first_answers` exists to end.
    """
    answered = {
        finding
        for finding, r in first_answers(rebut_result.rebuttal).items()
        if r.action == action
    }
    # A `contradicted` verdict counts here too. The host's check already
    # turned a failing one into `confirmed`.
    confirmed = {
        v.finding
        for lens in rebut_result.verdicts
        for v in lens.verdicts
        if v.verdict in ("confirmed", "contradicted")
    }
    return len(answered & confirmed)


def sustained_blockers(rebut_result: RebutResult | None) -> int:
    """§6 level 3: how many blockers the rebuttal did **not** dispose of.

    A blocker is sustained when one finding number carries an `argued` rebuttal
    and a `confirmed` or `contradicted` verdict. The verdict alone would count a
    blocker fixed and committed, and rank a task by work already done.

    Zero with no `RebutResult`, with a rebuttal turn that errored, and for a
    blocker verdicted but never rebutted, which never enters `_confirmed_with`'s
    answered set. An unanchored blocker never reaches REBUT at all (§5.5).
    """
    if rebut_result is None or rebut_result.rebuttal.error:
        return 0
    return _confirmed_with(rebut_result, "argued")


def unkept_fixes(rebut_result: RebutResult | None) -> int:
    """§6: a confirmed blocker whose only answer was a fix that never reached
    HEAD — a promise nobody kept, ranked *with* `sustained_blockers` but
    counted apart from it (`fixed & confirmed`, not `argued & confirmed`).

    Zero for every shape `sustained_blockers` is zero for, plus two more.
    ponytail: `moved` is one bit for the whole rebuttal, not per blocker, so
    it cannot say which claimed fix a landed commit was for. §6 names this a
    floor — `moved` True returns `0` even if a claimed fix never landed.

    The second is not this function's to fix: a rebuttal that answered every
    blocker `fixed` and moved nothing returns at `run_rebut`'s early exit
    below, so no verdict pass runs and there is nothing to confirm against —
    the purest instance of §6's failure counts zero here. It still reaches the
    queue, as state `REBUTTING`; note that ranks `_ELEVATED`, *below* the
    level-3 bucket this count feeds, so the purest case sorts under the
    mixed ones until that task lands.
    """
    if rebut_result is None or rebut_result.rebuttal.error or rebut_result.moved:
        return 0
    return _confirmed_with(rebut_result, "fixed")


def run_rebut(
    container: str,
    *,
    blockers: Sequence[Finding],
    # Required, not defaulted: a default would hide that `preserves` never
    # reached the guard below (backlog b-cd5fd2).
    acceptance: Sequence[Criterion],
    options: dict,
    session_id: str,
    spec_body: str,
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    head_moved: Callable[[], bool],
    rerun_gates: Callable[[], str | None],
    # Zero-argument and called at most once, lazily — after `rerun_gates`
    # answers — so the two early returns below never pay for a critic cell a
    # plain argument would have made the caller build regardless.
    critic_container: Callable[[], str],
    # Takes the container `critic_container()` just produced: the
    # diff a verdict session is shown must come from that tree, never the
    # implementer's own (CONTEXT.md §5, backlog item 118).
    diff: Callable[[str], str],
    agent: Callable[..., implement.AttemptResult],
    # Required, not defaulted — the same rule `review.run_review`'s own
    # `spec_id` states: this phase authors its own `PhaseStart` line below.
    spec_id: str,
    # Required, not defaulted: a default would let a caller keep today's
    # behaviour — one diff, the post-rebuttal one — without noticing it had
    # not threaded REVIEW's own diff through.
    reviewed_diff: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
    last_cost_usd: float = 0.0,
) -> RebutResult:
    """One rebuttal in the implementer's own container, the gate re-run there
    too, then one verdict session per lens in a fresh critic cell the
    rebutting implementer never ran in (CONTEXT.md §5, backlog item 118).

    `rerun_gates` returns a terminal state when the re-run is not green and
    `None` when it is; it runs first because a red re-run ends the task
    either way (§5.6), and `critic_container` is only ever called after.
    """
    # Numbered from 1: answering "1." for the first of one blocker is the
    # conventional reading, and `run_verdict` requires the verdict set to match
    # exactly — a renumbering model would cost the whole phase's spend.
    numbered = list(enumerate(blockers, 1))
    turn = run_rebuttal(
        container,
        blockers=numbered,
        # The implementer's own options, but never its budget: these two turns
        # resume the IMPLEMENT session, whose `max_budget_usd` is the whole task
        # budget. Uncapped here, REBUT re-spends it after REVIEW already has.
        options=options | {"max_budget_usd": budget_usd},
        session_id=session_id,
        agent=agent,
        emit=emit,
        last_cost_usd=last_cost_usd,
    )
    moved = head_moved()
    emit(
        PhaseStart(
            timestamp=time.time(),
            spec_id=spec_id,
            phase="REBUT",
            label="REBUT",
            detail=(
                f"{len(turn.rebuttals)} rebuttal(s), HEAD "
                f"{'moved' if moved else 'did not move'}"
                + (f", {turn.error}" if turn.error else "")
            ),
        )
    )
    result = RebutResult(
        state="",
        why="",
        rebuttal=turn,
        verdicts=[],
        moved=moved,
        cost_usd=turn.cost_usd,
    )

    if not moved and not any(r.action == "argued" for r in turn.rebuttals):
        # Nothing was fixed and nothing argued, so HEAD is where the gates last
        # measured it: re-running the suite would buy the same answer.
        result.state, result.why = rebut_state(moved=moved, rebuttal=turn, verdicts=[])
        return result

    if stopped := rerun_gates():
        result.state = stopped
        result.why = (
            "the gates are red after the rebuttal — REBUT does not re-enter the "
            "repair loop, and the rebuttal diff is kept"
            if stopped == "EXHAUSTED"
            else f"the gate re-run ended {stopped}"
        )
        return result

    try:
        critic = critic_container()
    except CriticPatchRejected as rejected:
        # §5.5, unchanged at REBUT: a bad patch is the agent's problem, and
        # the rebuttal turn plus the gate re-run are already paid for either
        # way — produced here, not left to escape uncharged.
        result.state = "EXHAUSTED"
        result.why = rejected.reason("a critic cell", "the post-rebuttal patch")
        return result
    except CriticPatchUnrepresentable as binary:
        # §5.5's one carve-out: a binary change the export cannot carry is
        # Saffron's own ceiling, charged to nobody.
        result.state = "GATE_ERROR"
        result.why = f"the post-rebuttal patch carries a binary change — {binary}"
        return result

    changed = diff(critic)
    for lens in [
        lens for lens in review.LENSES if any(f.lens == lens for f in blockers)
    ]:
        mine = [(n, f) for n, f in numbered if f.lens == lens]
        result.verdicts.append(
            run_verdict(
                critic,
                lens=lens,
                blockers=mine,
                system_prompt=verdict_prompt(
                    lens,
                    blockers=mine,
                    rebuttal=turn,
                    context_md=context_md,
                    claude_md=claude_md,
                    prompts_dir=prompts_dir,
                    spec_body=spec_body,
                    reviewed_diff=reviewed_diff,
                    diff=changed,
                ),
                max_turns=max_turns,
                budget_usd=budget_usd,
                agent=agent,
                emit=emit,
            )
        )
    # Every lens is checked on its own, not only the first or the last one
    # built. The failing verdict can come from either side of a rebuttal.
    guarded = _guarded_blockers(numbered, acceptance)
    answers = first_answers(turn)
    for lens_verdicts in result.verdicts:
        _check_contradictions(lens_verdicts, spec_body)
        _check_withdrawal_refusals(
            lens_verdicts, guarded=guarded, answers=answers, moved=moved
        )
    result.cost_usd += sum(v.cost_usd for v in result.verdicts)
    result.state, result.why = rebut_state(
        moved=moved, rebuttal=turn, verdicts=result.verdicts
    )
    return result
