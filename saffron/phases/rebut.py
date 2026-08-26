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

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from saffron.agents import context
from saffron.agents.artifacts import EXTRACTION_PROMPT, parse_output_block
from saffron.agents.findings import Finding
from saffron.phases import implement, review

VERDICT_PROMPT_FILE = "rebut-verdict.md"

REBUT_PROMPT = (
    "A critic reviewed your change and raised the blockers below. The host has "
    "already checked that each one points at a line your diff really changed, "
    "so none of them is about code you did not touch.\n\n"
    "{blockers}\n\n"
    "You get one attempt, and there is no second one. For each blocker, either "
    "fix it and commit, or argue that the finding is wrong. Arguing is a "
    "legitimate outcome and is recorded as one — a documented disagreement is "
    "more useful to the operator than agreement. Claiming a fix you did not "
    "commit is not an outcome at all: the host measures HEAD, not your report."
)

VERDICT_TURN_PROMPT = (
    "Confirm or withdraw each of your findings now, given the rebuttal. Read "
    "whatever you need to; you hold no tool that can change anything. "
    + EXTRACTION_PROMPT
)

EXTRACT_PROMPT = (
    "Record your rebuttal now. The block is a JSON object with one key, "
    "`rebuttals`, an array with one entry per blocker: `finding` (its number "
    'above), `action` ("fixed" if you committed a change for it, "argued" if '
    "you are arguing the finding is wrong) and `argument` (what you changed, or "
    "why the finding is wrong). " + EXTRACTION_PROMPT
)


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
    """The critic's confirm-or-withdraw — §4.1's `findings.verdict`, and never
    the operator's `adjudication`, which happens in GitHub against a PR."""

    finding: int
    verdict: Literal["confirmed", "withdrawn"]
    reason: str


class _Verdicts(BaseModel):
    verdicts: list[Verdict]


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
                    "verdicts": [d.model_dump() for d in v.verdicts],
                }
                for v in self.verdicts
            ],
        }


def blocker_lines(numbered: Sequence[tuple[int, Finding]]) -> str:
    """Blockers as prompt text, numbered so a rebuttal and a verdict can name
    one. The numbers are global across the phase: a lens is shown only its own
    blockers, but under the numbers the implementer answered."""
    return "\n".join(
        f"{n}. [{f.lens}] {f.file}:{f.line} — {f.claim}" for n, f in numbered
    )


def run_rebuttal(
    container: str,
    *,
    blockers: Sequence[tuple[int, Finding]],
    options: dict,
    session_id: str,
    agent: Callable[..., implement.AttemptResult],
    watch: Callable[[str], None] = print,
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
            watch=watch,
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
            options=options,
            resume=session_id,
            watch=watch,
            last_cost_usd=attempt.cost_usd_est,
        )
    except implement.AgentFailed as failed:
        cost = attempt.cost_usd_est + (
            failed.attempt.cost_usd_est if failed.attempt else 0.0
        )
        return RebuttalTurn(cost_usd=cost, session_id=session_id, error=str(failed))

    spent = attempt.cost_usd_est + extracted.cost_usd_est
    session_id = extracted.session_id or session_id
    try:
        report = _Rebuttals.model_validate(
            json.loads(parse_output_block(extracted.text))
        )
    except (ValueError, ValidationError) as exc:
        # No re-prompt, as with REVIEW's extraction: the plan checkpoint retries
        # because a rejected plan costs an attempt that has not happened yet.
        # This attempt is already made, and HEAD already says what it did.
        return RebuttalTurn(
            cost_usd=spent, session_id=session_id, error=f"not the schema: {exc}"
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
    prompts_dir: Path,
    spec_body: str,
    diff: str,
) -> str:
    """The verdict session's system prompt.

    It takes REVIEW's vocabulary sections: this is a fresh critic session, so
    §5.3's "REBUT injects nothing" — which is about the *resumed implementer* —
    does not reach it, and a session with no vocabulary would be verdicting
    against terms it was never given.
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
        blockers=blocker_lines(blockers),
        rebuttal=argued or "The implementer recorded no argument.",
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
    watch: Callable[[str], None] = print,
) -> LensVerdicts:
    """One lens, one fresh read-only session. `resume` is never passed, for the
    same reason as REVIEW: the critic must see the argument, not the session
    that wrote it."""
    options = implement.agent_options(
        system_prompt=system_prompt,
        max_turns=max_turns,
        budget_usd=budget_usd,
        tools=review.REVIEW_TOOLS,
    )
    try:
        attempt = agent(
            container, prompt=VERDICT_TURN_PROMPT, options=options, watch=watch
        )
    except implement.AgentFailed as failed:
        cost = failed.attempt.cost_usd_est if failed.attempt else 0.0
        return LensVerdicts(lens, cost_usd=cost, error=str(failed))
    try:
        report = _Verdicts.model_validate(json.loads(parse_output_block(attempt.text)))
    except (ValueError, ValidationError) as exc:
        return LensVerdicts(
            lens, cost_usd=attempt.cost_usd_est, error=f"not the schema: {exc}"
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
    if errored := [v.lens for v in verdicts if v.error]:
        return "REBUTTING", f"{errored} produced no verdict — the rebuttal is unjudged"
    confirmed = [
        v for lens in verdicts for v in lens.verdicts if v.verdict == "confirmed"
    ]
    unfixed = (
        " (a fix was claimed for some of them and no commit was made)"
        if (claimed and not moved)
        else ""
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


def sustained_blockers(rebut_result: RebutResult | None) -> int:
    """§6 level 3: how many blockers the rebuttal did **not** dispose of.

    A blocker is sustained when the same finding number carries both an
    `argued` rebuttal and a `confirmed` verdict. `confirmed` alone is not
    enough — it also covers a blocker the implementer *fixed and committed*,
    and counting that would rank a task by work already done, the mirror of
    the defect this level exists to fix (`anchored_concerns` stays the count
    below this one, not a component of it).

    Zero for every shape that is not a settled disagreement: no `RebutResult`
    (REBUT never ran), a rebuttal turn that errored (nothing to pair a
    verdict against), and a blocker that was verdicted but never rebutted —
    the last is not special-cased, it simply never enters the `argued` set
    below. An unanchored blocker never reaches REBUT at all (§5.5) and so
    never carries a finding number to collide with.
    """
    if rebut_result is None or rebut_result.rebuttal.error:
        return 0
    argued = {
        r.finding for r in rebut_result.rebuttal.rebuttals if r.action == "argued"
    }
    confirmed = {
        v.finding
        for lens in rebut_result.verdicts
        for v in lens.verdicts
        if v.verdict == "confirmed"
    }
    return len(argued & confirmed)


def run_rebut(
    container: str,
    *,
    blockers: Sequence[Finding],
    options: dict,
    session_id: str,
    spec_body: str,
    context_md: str,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    head_moved: Callable[[], bool],
    rerun_gates: Callable[[], str | None],
    diff: Callable[[], str],
    agent: Callable[..., implement.AttemptResult],
    watch: Callable[[str], None] = print,
    last_cost_usd: float = 0.0,
) -> RebutResult:
    """One rebuttal, the gate re-run, then one verdict session per lens.

    `rerun_gates` returns a terminal state when the re-run is not green and
    `None` when it is. It runs before the verdicts because it costs no tokens
    and because a red re-run ends the task either way (§5.6).
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
        watch=watch,
        last_cost_usd=last_cost_usd,
    )
    moved = head_moved()
    watch(
        f"REBUT: {len(turn.rebuttals)} rebuttal(s), HEAD "
        f"{'moved' if moved else 'did not move'}"
        + (f", {turn.error}" if turn.error else "")
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

    changed = diff()
    for lens in [
        lens for lens in review.LENSES if any(f.lens == lens for f in blockers)
    ]:
        mine = [(n, f) for n, f in numbered if f.lens == lens]
        result.verdicts.append(
            run_verdict(
                container,
                lens=lens,
                blockers=mine,
                system_prompt=verdict_prompt(
                    lens,
                    blockers=mine,
                    rebuttal=turn,
                    context_md=context_md,
                    prompts_dir=prompts_dir,
                    spec_body=spec_body,
                    diff=changed,
                ),
                max_turns=max_turns,
                budget_usd=budget_usd,
                agent=agent,
                watch=watch,
            )
        )
    result.cost_usd += sum(v.cost_usd for v in result.verdicts)
    result.state, result.why = rebut_state(
        moved=moved, rebuttal=turn, verdicts=result.verdicts
    )
    return result
