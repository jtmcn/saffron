"""Phase 4 — REVIEW, adversarial and host-driven (DESIGN.md §5.5).

Every lens is a fresh session the host invokes itself, never a subagent: the
model decides when to spawn a subagent, so a lens set requested in a prompt
varies by task, silently, with no error when a lens is skipped. A lens that runs
only when the model thinks it is relevant is not a lens.

A fresh session inherits nothing — that is the isolation the phase is for — so
the spec, the diff and the gate results are all passed explicitly.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ValidationError

from saffron.agents import context
from saffron.agents.artifacts import EXTRACTION_PROMPT, parse_output_block
from saffron.agents.findings import Finding, Severity, anchor
from saffron.events import Event, PhaseStart, describe
from saffron.gates.contract import GateResult
from saffron.phases import implement

# The implementer holds Write/Edit/Bash; a critic that can run a command can
# change the thing it is judging. Positive list for the reason `tools` exists at
# all (§5.3): a denylist still offers every built-in the runtime later adds.
REVIEW_TOOLS = ["Read", "Glob", "Grep"]

# Lens id -> its versioned prompt file. Prompts are source here, one file per
# lens, because a lens *is* its remit.
LENSES = {
    "correctness": "review-correctness.md",
    "contract": "review-contract.md",
    "adequacy": "review-adequacy.md",
}
# BACKLOG item 6, settled by #34: the third lens is not blast radius (that plan
# is retired) and it is not `revert`, which is unbuilt and asks a different
# question anyway (whether the new tests test *anything*, not *each thing*).
# It is a prompted lens that reads the diff and asks whether the tests would
# notice the code being wrong — no mutation tool, no coverage gate, both
# priced and both rejected in `docs/evidence/`.

REVIEW_PROMPT = (
    "Review this change now. Read whatever you need to; you hold no tool that "
    "can change anything. " + EXTRACTION_PROMPT
)


class _Reported(BaseModel):
    """One finding as the critic emits it.

    No `lens` field: the host stamps that. A lens that names its own lens can
    file under someone else's remit, and the drop rate would still read clean.
    """

    file: str
    line: int
    severity: Severity
    claim: str


class _Report(BaseModel):
    """The whole block. `findings: []` is the answer §5.5 asks for when there is
    no defect — distinguishable from a lens that emitted nothing at all."""

    findings: list[_Reported]


@dataclass
class LensReview:
    """What one lens produced, anchored findings and drops alike."""

    lens: str
    findings: list[Finding] = field(default_factory=list)
    cost_usd: float = 0.0
    error: str | None = None
    """Set when the lens did not deliver findings — a failed turn, or output
    that was not the schema. Never the same value as "found nothing" (§4.3)."""

    @property
    def drop_rate(self) -> float:
        """Unanchorable share. The signal a lens is badly prompted (§5.5)."""
        if not self.findings:
            return 0.0
        return sum(not f.anchored for f in self.findings) / len(self.findings)

    def as_dict(self) -> dict:
        return {
            "lens": self.lens,
            "cost_usd": self.cost_usd,
            "error": self.error,
            "drop_rate": self.drop_rate,
            "findings": [f.model_dump() for f in self.findings],
        }


def gate_summary(results: Sequence[GateResult], advisory: Sequence[str] = ()) -> str:
    """The gate results as prompt text — status and tool, never a verdict.

    `tool` is in it because "passed" and "never ran" are otherwise identical
    (§5.4), and a critic told a gate passed should be able to see which did.

    An advisory `fail` is marked, because an unmarked one reads as a defect the
    host missed: a lens files a blocker on it, the implementer spends a REBUT
    round arguing, and the budget goes on a failure the host already ruled is
    not the task's problem.
    """
    lines = []
    for r in results:
        mark = " (advisory)" if r.gate in advisory and r.status == "fail" else ""
        lines.append(
            f"- {r.gate}: {r.status}{mark} ({r.tool or 'no tool reported'})"
            + (f" — {r.summary}" if r.summary else "")
        )
    return "\n".join(lines)


def lens_prompt(
    lens: str,
    *,
    context_md: str,
    prompts_dir: Path,
    spec_body: str,
    diff: str,
    gates: str,
) -> str:
    """The lens's system prompt: its own file, plus what a fresh session lacks."""
    template = (prompts_dir / LENSES[lens]).read_text()
    return context.build_system_prompt(
        "REVIEW", context_md, template=template, spec=spec_body, diff=diff, gates=gates
    )


def run_lens(
    container: str,
    *,
    lens: str,
    system_prompt: str,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> LensReview:
    """One lens, one fresh session. `resume` is never passed, deliberately: the
    critic must not see the implementer's transcript or its own earlier runs."""
    options = implement.agent_options(
        system_prompt=system_prompt,
        max_turns=max_turns,
        budget_usd=budget_usd,
        tools=REVIEW_TOOLS,
    )
    try:
        attempt = agent(container, prompt=REVIEW_PROMPT, options=options, emit=emit)
    except implement.AgentFailed as failed:
        # A lens that crashed still cost money, and a lens that did not run must
        # never read as a lens that found nothing.
        cost = failed.attempt.cost_usd_est if failed.attempt else 0.0
        return LensReview(lens, cost_usd=cost, error=str(failed))
    try:
        report = _Report.model_validate(json.loads(parse_output_block(attempt.text)))
    except (ValueError, ValidationError) as exc:
        return LensReview(
            lens, cost_usd=attempt.cost_usd_est, error=f"not the schema: {exc}"
        )
    return LensReview(
        lens,
        findings=[
            Finding(lens=lens, **reported.model_dump()) for reported in report.findings
        ],
        cost_usd=attempt.cost_usd_est,
    )


def run_review(
    container: str,
    *,
    diff: str,
    read_head: Callable[[str], str | None],
    spec_body: str,
    gates: str,
    context_md: str,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    # Passed, never defaulted — the same shape `plan_checkpoint` uses, and a
    # module-level default would bind `run_agent` at import time.
    agent: Callable[..., implement.AttemptResult],
    # Required, not defaulted, for the reason `implement.run_agent`'s own
    # `spec_id` states: this phase authors its own `PhaseStart` line below, and
    # a forgotten keyword would file it under an empty id (§4.1).
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> list[LensReview]:
    """Every declared lens, in order, on this diff. The host drives the loop."""
    reviews = []
    for lens in LENSES:
        review = run_lens(
            container,
            lens=lens,
            system_prompt=lens_prompt(
                lens,
                context_md=context_md,
                prompts_dir=prompts_dir,
                spec_body=spec_body,
                diff=diff,
                gates=gates,
            ),
            max_turns=max_turns,
            budget_usd=budget_usd,
            agent=agent,
            emit=emit,
        )
        review.findings = anchor(review.findings, diff, read_head=read_head)
        emit(
            PhaseStart(
                timestamp=time.time(),
                spec_id=spec_id,
                phase="REVIEW",
                label="REVIEW",
                detail=_describe(review),
            )
        )
        reviews.append(review)
    return reviews


def _describe(review: LensReview) -> str:
    if review.error:
        return f"{review.lens} produced nothing — {review.error}"
    counted = [f for f in review.findings if f.anchored]
    by_severity = ", ".join(
        f"{sum(f.severity == s for f in counted)} {s}"
        for s in ("blocker", "concern", "note")
    )
    return (
        f"{review.lens}: {by_severity}, "
        f"drop rate {review.drop_rate:.0%} of {len(review.findings)}, "
        f"${review.cost_usd:.2f}"
    )


def anchored_blockers(reviews: Sequence[LensReview]) -> list[Finding]:
    """Anchored blockers, in order. ORDER IS LOAD-BEARING: `rebut.py` numbers
    this result from 1, and the pull-request body renders `_disagreements`
    against those same numbers — the single selection rule every caller of
    REBUT's blocker list must share."""
    return [
        f for r in reviews for f in r.findings if f.anchored and f.severity == "blocker"
    ]


def anchored_concerns(reviews: Sequence[LensReview]) -> int:
    """How many anchored concerns the review left. One rule, two callers:
    `review_state` and the queue line the operator sorts on (§6) — a second
    hand-written copy silently reorders the morning page."""
    return sum(
        f.anchored and f.severity == "concern" for r in reviews for f in r.findings
    )


def review_state(reviews: Sequence[LensReview]) -> tuple[str, str]:
    """The task's state after REVIEW, and the one line that says why.

    Any single anchored blocker routes to REBUT (§5.5), so `REBUTTING` here is
    a phase to run, not a stop. A lens that errored *is* a stop, at `REVIEWING`:
    an unrun lens must not read as a clean review, and there is no finding set
    to rebut against.
    """
    if errored := [r.lens for r in reviews if r.error]:
        return "REVIEWING", f"{errored} produced no findings — the review is incomplete"
    blockers = anchored_blockers(reviews)
    if blockers:
        return "REBUTTING", f"{len(blockers)} blocker(s) — the implementer rebuts"
    concerns = anchored_concerns(reviews)
    return "READY_FOR_REVIEW", f"no blockers, {concerns} concern(s)"
