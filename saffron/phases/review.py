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
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from saffron import probe
from saffron.agents import context
from saffron.agents.artifacts import EXTRACTION_PROMPT, parse_output_block
from saffron.agents.findings import Finding, Severity, anchor
from saffron.events import Event, PhaseStart, describe
from saffron.gates.contract import GateResult, GateStatus
from saffron.intake import Criterion, Mutant
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

# Marks a finding the host filed, never a lens (item b-2750d5): excluded
# from `drop_rate` and stripped by `_from_report` so a lens cannot forge one.
HOST_FILED = "[host-filed criterion probe] "

REVIEW_PROMPT = context.turn_prompt("review")


class _Reported(BaseModel):
    """One finding as a critic emits it.

    No `lens` field: the host stamps that. A lens that names its own lens can
    file under someone else's remit, and the drop rate would still read clean.
    """

    model_config = ConfigDict(extra="forbid")

    file: str
    line: int
    severity: Severity
    claim: str


class _ReportedWithProbe(_Reported):
    """Adequacy's variant. The probe is required because the number it feeds is
    only computable when every finding carries one — an optional field filled
    sometimes and not others makes the measurement a phrasing lottery, which is
    the failure the corpus exists to catch. Adequacy was once the only lens
    that asked for an edit here. The end review's Spec lens now asks for
    one too, through its own optional model below.
    """

    probe: Mutant


class _ReportedWithOptionalProbe(_Reported):
    """The end review's Spec lens keeps the probe optional. A criterion
    the diff satisfies cleanly names no wrong version at all. This field
    is not required the way adequacy's is."""

    probe: Mutant | None = None


_REPORTED: dict[str, type[_Reported]] = {
    "adequacy": _ReportedWithProbe,
    "spec": _ReportedWithOptionalProbe,
}


def reported_model(lens: str) -> type[_Reported]:
    """The schema this lens's findings are validated against.

    Per lens rather than one shape with an optional field: only adequacy's
    prompt asks for an edit and only its defect class is expressible as one.
    The end review's Spec lens asks for an edit too now, so it gets its
    own model here as well.
    """
    return _REPORTED.get(lens, _Reported)


class _Report(BaseModel):
    """The whole block, before a lens-specific model validates each finding.
    `findings: []` is the answer §5.5 asks for when there is no defect —
    distinguishable from a lens that emitted nothing at all."""

    findings: list[dict[str, object]]


def _parse_report(lens: str, raw: str) -> list[_Reported]:
    """The block plus each finding, validated against `reported_model(lens)`.

    One parse rather than `_Report.model_validate` alone, because the finding
    shape is per lens (Step 1): only adequacy's model demands `probe`, and only
    `run_lens` knows which lens produced this text.
    """
    report = _Report.model_validate(json.loads(raw))
    model = reported_model(lens)
    return [model.model_validate(item) for item in report.findings]


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
        """Unanchorable share. The signal a lens is badly prompted (§5.5).

        A `HOST_FILED` finding is excluded: the lens never filed it, so it
        cannot move the number that measures the lens's own prompting.
        """
        own = [f for f in self.findings if not f.claim.startswith(HOST_FILED)]
        if not own:
            return 0.0
        return sum(not f.anchored for f in own) / len(own)

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
    claude_md: str | None,
    prompts_dir: Path,
    spec_body: str,
    diff: str,
    gates: str,
) -> str:
    """The lens's system prompt: its own file, plus what a fresh session lacks."""
    template = (prompts_dir / LENSES[lens]).read_text()
    return context.build_system_prompt(
        "REVIEW",
        context_md,
        template=template,
        spec=spec_body,
        diff=diff,
        gates=gates,
        standing_instructions=context.standing_instructions(claude_md),
    )


def _strip_host_filed(claim: str) -> str:
    """Every leading `HOST_FILED` stripped, so a lens cannot buy its own
    finding an exemption from `drop_rate` by echoing the host's prefix."""
    while claim.startswith(HOST_FILED):
        claim = claim[len(HOST_FILED) :]
    return claim


def _from_report(lens: str, findings: list[_Reported], cost_usd: float) -> LensReview:
    built = []
    for reported in findings:
        data = reported.model_dump()
        data["claim"] = _strip_host_filed(data["claim"])
        built.append(Finding(lens=lens, **data))
    return LensReview(lens, findings=built, cost_usd=cost_usd)


def run_lens(
    container: str,
    *,
    lens: str,
    system_prompt: str,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> LensReview:
    """One lens, one fresh session — never the implementer's and never another
    lens's, so the critic judges only the diff in front of it (§5.5).

    The single exception: output that is not the schema resumes that same
    session once, to repair the *shape* of the turn that just ran — mirroring
    `session.py`'s `PlanNotSchema` re-prompt. That turn still sees only its
    own prior output, over the same diff; it is not exposed to the
    implementer's transcript or to another lens's, so the isolation this
    docstring is otherwise about still holds.
    """
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
        findings = _parse_report(lens, parse_output_block(attempt.text))
    except (ValueError, ValidationError) as exc:
        remaining = budget_usd - attempt.cost_usd_est
        # A retry given less than the turn that just failed spent cannot
        # finish, so it is refused rather than started.
        if remaining < attempt.cost_usd_est or not attempt.session_id:
            return LensReview(
                lens, cost_usd=attempt.cost_usd_est, error=f"not the schema: {exc}"
            )
        emit(
            PhaseStart(
                timestamp=time.time(),
                spec_id=spec_id,
                phase="REVIEW",
                label="REVIEW",
                detail=f"{lens}: not the schema, re-prompting once — {exc}",
            )
        )
        retry_options = implement.agent_options(
            system_prompt=system_prompt,
            max_turns=max_turns,
            budget_usd=remaining,
            tools=REVIEW_TOOLS,
        )
        try:
            retry = agent(
                container,
                prompt=f"{exc}\n\n{EXTRACTION_PROMPT}",
                options=retry_options,
                resume=attempt.session_id,
                emit=emit,
                last_cost_usd=attempt.cost_usd_est,
            )
        except implement.AgentFailed as failed:
            cost = attempt.cost_usd_est + (
                failed.attempt.cost_usd_est if failed.attempt else 0.0
            )
            return LensReview(
                lens, cost_usd=cost, error=f"re-prompted once, then {failed}"
            )
        total_cost = attempt.cost_usd_est + retry.cost_usd_est
        try:
            findings = _parse_report(lens, parse_output_block(retry.text))
        except (ValueError, ValidationError) as exc2:
            return LensReview(
                lens,
                cost_usd=total_cost,
                error=f"not the schema, even after a re-prompt: {exc2}",
            )
        return _from_report(lens, findings, total_cost)
    return _from_report(lens, findings, attempt.cost_usd_est)


def run_review(
    container: str,
    *,
    diff: str,
    read_head: Callable[[str], str | None],
    spec_body: str,
    gates: str,
    context_md: str,
    claude_md: str | None,
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
                claude_md=claude_md,
                prompts_dir=prompts_dir,
                spec_body=spec_body,
                diff=diff,
                gates=gates,
            ),
            max_turns=max_turns,
            budget_usd=budget_usd,
            agent=agent,
            spec_id=spec_id,
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


class _ProbeAnswer(BaseModel):
    """One criterion-probe session's own answer (backlog item b-2750d5): the
    edit it names against the one claim it was shown, or none, and why."""

    model_config = ConfigDict(extra="forbid")

    edit: Mutant | None = None
    reason: str


CRITERION_PROBE_PROMPT = context.turn_prompt("criterion-probe")


def criterion_probe_prompt(
    *,
    claim: str,
    diff: str,
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
) -> str:
    """The system prompt for one criterion's own session: the claim substituted
    for `{spec}`, never the spec body and never a witness node id."""
    template = (prompts_dir / "criterion-probe.md").read_text()
    return context.build_system_prompt(
        "REVIEW",
        context_md,
        template=template,
        spec=claim,
        diff=diff,
        standing_instructions=context.standing_instructions(claude_md),
    )


def run_criterion_probe(
    container: str,
    *,
    system_prompt: str,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> tuple[Mutant | None, str, float, str | None]:
    """One fresh session, asked for the edit that falsifies one claim.

    No re-prompt on a bad shape, unlike `run_lens`: a criterion probe costs
    one claim, where a lens costs a whole remit.
    """
    options = implement.agent_options(
        system_prompt=system_prompt,
        max_turns=max_turns,
        budget_usd=budget_usd,
        tools=REVIEW_TOOLS,
    )
    try:
        attempt = agent(
            container, prompt=CRITERION_PROBE_PROMPT, options=options, emit=emit
        )
    except implement.AgentFailed as failed:
        cost = failed.attempt.cost_usd_est if failed.attempt else 0.0
        return None, "", cost, str(failed)
    try:
        answer = _ProbeAnswer.model_validate(
            json.loads(parse_output_block(attempt.text))
        )
    except (ValueError, ValidationError) as exc:
        return None, "", attempt.cost_usd_est, f"not the schema: {exc}"
    return answer.edit, answer.reason, attempt.cost_usd_est, None


def run_criterion_probes(
    container: str,
    *,
    acceptance: Sequence[Criterion],
    diff: str,
    context_md: str,
    claude_md: str | None,
    prompts_dir: Path,
    max_turns: int,
    budget_usd: float,
    agent: Callable[..., implement.AttemptResult],
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> list[dict]:
    """One fresh session per criterion, in the spec's own declared order
    (backlog item b-2750d5). Every entry is asked about, a `preserves` one
    included, and a spec declaring none buys no session at all."""
    entries = []
    for criterion in acceptance:
        system_prompt = criterion_probe_prompt(
            claim=criterion.claim,
            diff=diff,
            context_md=context_md,
            claude_md=claude_md,
            prompts_dir=prompts_dir,
        )
        edit, reason, cost, error = run_criterion_probe(
            container,
            system_prompt=system_prompt,
            max_turns=max_turns,
            budget_usd=budget_usd,
            agent=agent,
            spec_id=spec_id,
            emit=emit,
        )
        entries.append(
            {
                "witness": criterion.witness,
                "claim": criterion.claim,
                "edit": None if edit is None else edit.model_dump(),
                "reason": reason,
                "cost_usd": cost,
                "error": error,
            }
        )
    return entries


def describe_criterion_probes(entries: Sequence[Mapping[str, object]]) -> str:
    """The one REVIEW line criterion-probing adds, counted over
    `criterion-probes.json`'s own entries. `describe_probes` sets that
    precedent for a line counted over the record it summarises."""
    named = sum(1 for e in entries if e["edit"] is not None)
    return f"criterion probes: {named} named, {len(entries) - named} unnamed"


# `witness_gate`'s own status, over one criterion, in this record's words
# (item b-2750d5): `pass` killed, `fail` survived, `skip` unproven, `error` error.
_CRITERION_PROBE_OUTCOMES = {
    "pass": "killed",
    "fail": "survived",
    "error": "error",
    "skip": "unproven",
}


def criterion_probe_outcome(status: GateStatus) -> str:
    """`witness_gate`'s status for one criterion, read as an outcome. Its four
    statuses over one criterion probe are the only valid input."""
    return _CRITERION_PROBE_OUTCOMES[status]


def survivor_finding(criterion: Criterion, edit: Mutant, content: str) -> Finding:
    """The blocker filed when a criterion's own witness survives the edit its
    own session named for it (backlog item b-2750d5). `content` is the file at
    head in the cell that applied and restored the edit. The line is where
    `edit.find` begins there, never a hunk line.

    Unanchored: the caller still runs this through `findings.anchor`, exactly
    as every other finding in a `LensReview` is."""
    line = content.count("\n", 0, content.index(edit.find)) + 1
    return Finding(
        lens="adequacy",
        severity="blocker",
        file=edit.file,
        line=line,
        claim=(
            f"{HOST_FILED}{criterion.witness} stayed green with the criterion's "
            f"own edit applied to {edit.file}. The claim was "
            f"{criterion.claim!r}, and only that witness ran under the edit."
        ),
        probe=edit,
        probe_verdict="survived",
    )


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


def adequacy_probes(reviews: Sequence[LensReview]) -> list[Finding]:
    """Anchored adequacy findings that carry a probe — the set the Gate-only
    cell is asked about (backlog item 117). Unanchored ones are excluded: they
    never reach `anchored_blockers`/`anchored_concerns` either way, so
    promoting one would spend a suite run on a finding that decides nothing."""
    return [
        f
        for r in reviews
        for f in r.findings
        if f.lens == "adequacy" and f.anchored and f.probe is not None
    ]


def probe_key(probe: Mutant) -> tuple[str, str, str]:
    """The identity two probes share when they are the same edit. `Mutant` is
    not frozen, so this is what stands in for it as a dict key."""
    return (probe.file, probe.find, probe.replace)


def distinct_probes(findings: Sequence[Finding]) -> list[Mutant]:
    """The probes `findings` carry, first-seen order, one per distinct edit —
    matching the lens-corpus driver's own dedup (`_distinct`), so a probe two
    findings named is asked once."""
    seen: dict[tuple[str, str, str], Mutant] = {}
    for f in findings:
        assert f.probe is not None  # adequacy_probes already filtered this
        seen.setdefault(probe_key(f.probe), f.probe)
    return list(seen.values())


def apply_probe_verdict(finding: Finding, verdict: probe.Verdict) -> None:
    """Decide one finding from its probe's verdict (backlog item 117):
    `survived` promotes to `blocker`, `killed` demotes to `note`, `unproven`
    leaves the severity the lens filed. `Finding` is not frozen, so this
    mutates in place — `finding` keeps its `id()`, which is what lets REBUT's
    later `ledger.record_findings` lookup still find it."""
    finding.probe_verdict = verdict
    if verdict == "survived":
        finding.severity = "blocker"
    elif verdict == "killed":
        finding.severity = "note"


def describe_probes(entries: Sequence[Mapping[str, object]]) -> str:
    """The REVIEW line probing adds, counted over `probes.json`'s own entries
    — one per distinct edit, not per finding, so the line and the record it
    summarises cannot disagree when two findings name one probe."""
    counts = Counter(e["probe_verdict"] for e in entries)
    return (
        f"probes: {counts['survived']} survived, {counts['killed']} killed, "
        f"{counts['unproven']} unproven"
    )


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
