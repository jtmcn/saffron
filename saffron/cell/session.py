"""One cell, start to finish (DESIGN.md §5.1–§5.4).

v0.5 only: no scheduler, no budget pool, no PR. The operator watches this run.
`ponytail:` this is v0.5's supervisor. v1 replaces it with supervisor.py plus
scheduler.py, and this file goes the way replay.py went.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import time
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import partial, wraps
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from saffron.agents.findings import Finding, anchor
from saffron.cell import runtime
from saffron.events import (
    Attempt,
    Baseline,
    Budget,
    Event,
    EventLog,
    LineLabel,
    Phase,
    PhaseStart,
    Preflight,
    TaskOutcome,
    Teardown,
    Terminal,
    describe,
)

# Aliased: `GateResult` below is the gate contract's; this is `events.GateResult`.
from saffron.events import GateResult as GateResultEvent
from saffron.gates.baseline import NewFailure, is_no_progress
from saffron.gates.contract import GateResult
from saffron.intake import Criterion, Mutant
from saffron.phases import implement, rebut, review
from saffron.phases.implement import AttemptResult

if TYPE_CHECKING:
    from saffron.gates.suite import GateSuite, SuiteComparison, SuiteRun
    from saffron.ledger import Ledger

# Where this file lives inside the Saffron tree, used to locate CONTEXT.md —
# Saffron's own files, never the target repo's (§5.3). The prompt tree has its
# one locator in `context.PROMPTS_DIR`.
_SAFFRON_ROOT = Path(__file__).resolve().parents[2]

# §4.3's wall clock, per turn, set here rather than inherited: this is the bound
# the operator sits through, so it belongs where the task is driven. Fifteen
# minutes is long enough for a turn that runs a real gate suite between tool
# calls and short enough to watch; the idle bound (runtime.IDLE_TIMEOUT_S) is
# what catches a stall sooner, and this only catches a turn that never stops.
TURN_TIMEOUT_S = 900.0

# REVIEW is deliberately not gated on the spend ceiling — a green diff nobody
# reviewed is not a product — so its sessions are capped at what is left rather
# than at the whole task budget, which is how a $12 task bills $40 — one
# remainder per declared lens, never decremented between them, so `LENSES`
# growing moves that number rather than dividing it. The floor is
# what keeps "not gated" true when nothing is left: below it a lens would be
# refused for having no room, and the task would reach the operator unreviewed.
# REBUT *is* gated (`_over_budget` before the rebuttal turn): by then the
# findings are written and the operator has something to read either way.
REVIEW_FLOOR_USD = 2.0


def _default_emit(event: Event, *, log: EventLog) -> None:
    """What `run_one_cell` fans an event out to when the caller (every direct
    caller today, and `cli.py`, which is forbidden here and never passes
    `emit`) hands it none: the terminal an operator watches, and one durable
    `EventLog` at `task_dir`. `EventLog.append` never raises (§0's own rule),
    so a disk-full night still reaches its terminal state — it just stops
    growing `events.jsonl`, which `EventLog.failed` is the breadcrumb for.
    """
    line = describe(event)
    if line:
        print(line)
    log.append(event)


def spec_drift(gates_dir: Path, spec_id: str, spec_sha: str) -> str | None:
    """The spec the host is judging against, versus the one the cell can read.

    `saffron cell <path>` loads the file the operator names, on disk, now.
    The cell's worktree is built from the mirror, so it carries whatever
    `.saffron/specs/` held at that commit. Nothing compared them, and on
    `SA-0064`'s second run they differed: the host's copy had a criterion's
    mutant removed an hour earlier and the mirror's still carried it, so the
    implementer reasoned about a contract the host was not judging it against
    (item 85). It is also the measurement item 80 asked for — the prompt-level
    withholding of `mutant` is defeated by the worktree copy, demonstrably
    rather than in principle.

    Reported, never refused: an operator iterating on a spec is exactly what
    produced this, and refusing would stop the workflow that found it.

    Both bytes are already in hand — `spec_sha` is sha256 over the host file
    and `.saffron` is exported from the mirror regardless — so this reads one
    more file and hashes it the same way `load_spec` does.

    ponytail: compared at `base_sha`, the commit the export is taken at, while
    the worktree is built at `tree_base`. The two are the same for every
    unstacked run, which is every run that has happened; a stacked run could
    differ again in the worktree and this would not say so.
    """
    specs = gates_dir / ".saffron" / "specs"
    found = sorted(specs.rglob(f"{spec_id}*.md")) if specs.is_dir() else []
    if not found:
        # Silence, not a line. A spec written on the host and not yet pushed is
        # the ordinary shape of an attended run, and it is the *absence* of the
        # hazard: with no copy in the worktree there is no second contract for
        # the agent to read. Reporting it would print on almost every
        # `saffron cell`, and a line that prints when nothing is wrong is how an
        # operator learns to skip the one that matters.
        return None
    at_base = hashlib.sha256(found[0].read_bytes()).hexdigest()
    if at_base == spec_sha:
        return None
    return (
        f"{spec_id}: the host runs {spec_sha[:12]} and the cell's worktree "
        f"carries {at_base[:12]} ({found[0].name}) — the agent can read a "
        "contract this run is not judging it against"
    )


def critic_budget(budget_usd: float, spent: float) -> float:
    """The per-session cap for one critic turn: the remainder, never zero."""
    return max(budget_usd - spent, REVIEW_FLOOR_USD)


class RateLimited(RuntimeError):
    """The provider closed the window. Raised, never returned: every phase
    catches `AgentFailed`, so a state handed back would be swallowed."""

    def __init__(self, resets_at: int | None) -> None:
        super().__init__("rate limit: rejected")
        self.resets_at = resets_at


def _resets_at_fields(resets_at: object) -> tuple[int | None, bool]:
    """`RateLimited.resets_at`, shaped for `TaskOutcome`: `None`, a clean `int`, or unreadable."""
    if resets_at is None:
        return None, False
    if isinstance(resets_at, int) and not isinstance(resets_at, bool):
        return resets_at, False
    return None, True


def stop_on_rejected(
    agent: Callable[..., AttemptResult],
) -> Callable[..., AttemptResult]:
    """The one place every turn goes through, so no turn — plan, implement,
    repair, review or rebuttal — can run against a closed window (§4.3). A
    guard per call site is a guard the next turn type forgets to add.

    Committed work is not discarded: the patch export runs from `finally`."""

    @wraps(agent)
    def guarded(*args: object, **kwargs: object) -> AttemptResult:
        try:
            attempt = agent(*args, **kwargs)
        except implement.AgentFailed as failed:
            # A rejected window also comes back as a *failed* turn — `is_error`
            # with terminal_reason `api_error` — carrying the same field. That
            # path is how a provider wall was reported as NOT_IMPLEMENTED.
            _raise_if_rejected(failed.attempt)
            raise
        _raise_if_rejected(attempt)
        return attempt

    return guarded


def record_attempts(
    agent: Callable[..., AttemptResult], *, ledger: Ledger, task_id: int
) -> Callable[..., AttemptResult]:
    """One `attempts` row per agent turn (§4.1), opened here rather than at each
    call site: the lens sessions and the rebuttal turns run inside their phases,
    which take an `agent` and know nothing of the ledger.

    Wrapped *inside* `stop_on_rejected`, so a turn the provider walled has its
    cost recorded before the rate limit is raised. A turn that fails is still a
    turn that spent; a turn that raises something neither of them expects leaves
    its row open, which is what it is.
    """

    @wraps(agent)
    def recorded(*args: object, **kwargs: object) -> AttemptResult:
        attempt_id = ledger.open_attempt(task_id)
        try:
            attempt = agent(*args, **kwargs)
        except implement.AgentFailed as failed:
            _close_attempt(ledger, attempt_id, failed.attempt)
            raise
        _close_attempt(ledger, attempt_id, attempt)
        return attempt

    return recorded


def _close_attempt(
    ledger: Ledger, attempt_id: int, attempt: AttemptResult | None
) -> None:
    ledger.close_attempt(
        attempt_id,
        session_id=attempt.session_id if attempt else None,
        # Not yet available: AttemptResult carries no model, because the
        # runner's result event doesn't either (agent_runner.py) — only an
        # assistant message does, and nothing captures it from there yet.
        model=None,
        # A turn that produced no result at all is not a turn that succeeded,
        # and $0.00 here is measured absence, not a crash's zeroed fields.
        subtype=attempt.subtype if attempt else "error",
        terminal_reason=attempt.terminal_reason if attempt else None,
        num_turns=attempt.num_turns if attempt else 0,
        cost_usd_est=attempt.cost_usd_est if attempt else 0.0,
    )


def _raise_if_rejected(attempt: AttemptResult | None) -> None:
    if attempt and terminal_for_rate_limit(attempt.rate_limit_status):
        raise RateLimited(attempt.rate_limit_resets_at)


def terminal_for_rate_limit(status: str | None) -> str | None:
    """The provider said no. That is not the task failing its own gates, and
    reporting it as EXHAUSTED is how an operator retries a wall (§3.3)."""
    return "RATE_LIMITED" if status == "rejected" else None


class CellSessionError(RuntimeError):
    """The session cannot go on — not the agent's failure, the driver's."""


# A resolved commit, the only shape a second base may take.
_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


@dataclass
class CellSpec:
    spec_id: str
    spec_sha: str
    branch: str
    base_sha: str
    touches: list[str]
    spec_type: str
    body: str
    forbidden: list[str] = field(default_factory=list)
    # From the operator's host-side copy, parsed by `cli.load_spec` before the
    # cell exists — so what `criteria` checks was never in /work (§5.4).
    acceptance: list[Criterion] = field(default_factory=list)
    # The tier the spec declared, read by `_suite` as one half of the effective
    # one (`policy.effective_risk`); `elevate_on` matching the diff is the
    # other (§5.6). `cli` passes it, and `test_a_specs_declared_risk_reaches_
    # the_cell` is what says so — it went unpassed for a whole task once,
    # which made the declared half of §5.6 unreachable outside tests.
    risk: str = "standard"
    # Kept in step with `intake.Spec`, which is where a run's ceilings are
    # declared and defaulted; `cli` passes all three, so these are reached only
    # by tests. Two defaults for one ceiling is a drift vector — they disagreed
    # once already, and the 12.0/10.0 split is what hid it.
    budget_usd: float = 12.0
    max_attempts: int = 4
    max_turns: int = 60
    # A stacked task's parent branch head. `base_sha` stays the run's pin:
    # gates and policy are exported from it either way (§5.4, item 13).
    # `task._resolve_stacked_on` (`SA-0026`) puts the parent's fetched branch
    # head here, and `None` when there is no parent to stack on.
    stacked_on: str | None = None

    def __post_init__(self) -> None:
        # A resolver that could not find the parent must say `None`. An empty
        # string would make `tree_base` an empty git range — a silent
        # HEAD..HEAD — and a ref name is a moving target between the fetch and
        # the checkout, besides being interpolated into the seed script.
        if self.stacked_on is not None and not _SHA.fullmatch(self.stacked_on):
            raise ValueError(
                f"stacked_on is not a resolved sha: {self.stacked_on!r} — a "
                "parent that could not be resolved is None, never a ref or ''"
            )

    @property
    def tree_base(self) -> str:
        """What the worktree is built on and the patch is exported against.

        One name for the second base, so no consumer picks its own — the
        defect this field exists to remove is two things sharing one word,
        and a second word every caller resolves separately is the same bug.
        Equal to `base_sha` unstacked, which is every caller today.
        """
        return self.base_sha if self.stacked_on is None else self.stacked_on


@dataclass
class CellOutcome:
    """What one cell produced. Every field defaulted, because `session.py`'s
    early returns precede the bindings: `spent` is first bound by
    `plan_checkpoint` while PREFLIGHT_FAILED and PLAN_REJECTED return before it,
    and `reviews` is unbound on every path that skipped REVIEW.

    ponytail: this is the seam v1's supervisor.py inherits — a supervisor that
    returns a bare string cannot be given a caller.
    """

    state: str
    task_id: int
    run_id: int
    task_dir: Path
    spent_usd: float = 0.0
    attempts: int = 0
    cell_head_sha: str | None = None
    gates: list[GateResult] = field(default_factory=list)
    new_failures: list[NewFailure] = field(default_factory=list)
    reviews: list[review.LensReview] = field(default_factory=list)
    rebut_result: rebut.RebutResult | None = None
    agent_subjects: list[str] = field(default_factory=list)
    # The last suite's own answer to §5.6's two questions — computed inside
    # `_drive_cell`, from the same changed-file list every gate result here
    # was judged against, and carried out rather than re-derived: a consumer
    # re-computing it from `spec.risk` alone would silently drop the
    # `elevate_on` half (§5.6, this module's own notes on `_suite`).
    effective_risk: str = "standard"
    advisory_gates: list[str] = field(default_factory=list)
    # Only bound on `state == "SCOPE_REVIEW"` (SA-0018): the final touches a
    # future ratification would write back, spec path pattern included.
    # Empty on every other path.
    proposed_touches: list[str] = field(default_factory=list)
    # The implementer's own account of something it saw but was told not to
    # touch (backlog items 71/75/80, SA-0058/SA-0061/SA-0062) —
    # extracted and hashed the instant it was produced, never re-read from
    # `/work` (§5.3's own rule). Empty on every path that returns before the
    # notes turn runs, and on one that ran it but had nothing to say.
    notes: str = ""
    notes_sha256: str = ""


def repair_decision(
    *,
    attempt: int,
    max_attempts: int,
    new: Sequence[NewFailure],
    previous: Sequence[NewFailure],
) -> Literal["green", "no-progress", "exhausted", "repair"]:
    """What the loop does next: green | no-progress | exhausted | repair."""
    if not new:
        return "green"
    if previous and is_no_progress(new, previous):
        # baseline.py owns the counted-identity comparison — it must not
        # drift from subtract_baseline's own counting (§5.4).
        return "no-progress"
    if attempt >= max_attempts:
        return "exhausted"
    return "repair"


def cut_off_at_turn_ceiling(attempt: AttemptResult) -> bool:
    """Was this turn's own §4.3 turn bound what ended it, rather than the
    agent's own say-so? The fact `_drive_cell` trusts before spending a
    salvage turn on a zero-commit implement turn (SA-0028).

    Read off `terminal_reason`, the field `close_attempt` already persists
    for exactly this row: SA-0025's ledger carried `subtype: error_max_turns`
    and `terminal_reason: max_turns` on the attempt that burned 141 turns and
    $11.68 with nothing to export. A rate-limit wall or a crash carries some
    other reason, or none, and must not read as this — spending a turn on a
    provider ceiling or a crash is not what the salvage exists for.

    Both fields, because the ledger row carried both and `run_agent` keys on
    the subtype (`implement.py`'s failure predicate). A result event that
    arrived without `terminal_reason` would otherwise skip the salvage in
    silence — a control that does not fire looks identical to one that did.
    """
    return (
        attempt.terminal_reason == "max_turns" or attempt.subtype == "error_max_turns"
    )


def previous_cut_orphan(
    ledger: Ledger, repo_id: int, spec: CellSpec, task_id: int
) -> int | None:
    """The retry cap (SA-0126, backlog item b-36b551). Only the first
    zero-commit cut at one `spec_sha` earns `ORPHANED`, and the next settles
    as `NOT_IMPLEMENTED`. No fact says "orphaned by a cut" apart from the
    other three paths that write it, so this reads `ledger._db` directly, as
    `chain_walk._task_rows` does. A cut task's run finished `COMPLETE` while
    every attempt it holds stayed phase `IMPLEMENTING`, the state
    `_drive_cell` never leaves before this return fires. Scoped to this
    repo, spec id and `spec_sha`, excluding `task_id` itself. Call only when
    a bound cut this task and nothing survived the salvage.
    """
    row = ledger._db.execute(
        """
        SELECT t.task_id
          FROM tasks t
          JOIN runs rn ON rn.run_id = t.run_id
         WHERE rn.repo_id = ?
           AND t.spec_id = ?
           AND t.spec_sha = ?
           AND t.task_id != ?
           AND t.state = 'ORPHANED'
           AND rn.status = 'COMPLETE'
           AND NOT EXISTS (
               SELECT 1 FROM attempts a
                WHERE a.task_id = t.task_id AND a.phase != 'IMPLEMENTING'
           )
         ORDER BY t.task_id
         LIMIT 1
        """,
        (repo_id, spec.spec_id, spec.spec_sha, task_id),
    ).fetchone()
    return int(row["task_id"]) if row is not None else None


def require_session(session_id: str | None) -> str:
    """Every turn after the first resumes, so a missing session_id is fatal.

    `resume=None` starts a brand-new session with no memory of the plan or the
    code it wrote, and the repair loop would then read the flailing as the
    agent's fault (§5.3).
    """
    if not session_id:
        raise CellSessionError("the turn returned no session_id; nothing to resume")
    return session_id


def _spec_path(spec_id: str, repo: Path) -> str:
    """A `touches` entry for the task's own spec file (§5.2's rule, reached
    here from IMPLEMENT rather than DIAGNOSE — SA-0018).

    Read off the frontmatter, never guessed from the filename: nothing ties a
    spec file's name to its `id` (`discover_specs` globs `*.md` and reads `id`
    out of the frontmatter), so the `<id>-*.md` glob this used to return
    matched no file at all in a repo that names its specs any other way — and
    the writeback commit then failed the very `scope` gate the entry exists to
    satisfy. Every spec in this repo follows the convention, which is why no
    test caught it.

    The glob stays as the fallback for a spec the scan cannot find: a pattern
    that may match nothing still beats recording no spec path at all.

    That fallback covers a *missing* spec directory too, and states the
    precondition rather than asking: `discover_specs` refuses a path that is
    absent or not a directory (backlog item 26), which is right for a scan
    whose emptiness the scheduler reads, and wrong here — this is a best-effort
    `touches` entry, so it must not turn into the fault that stops a task.
    """
    from saffron.intake import discover_specs

    specs_dir = repo / ".saffron" / "specs"
    if not specs_dir.is_dir():
        return f".saffron/specs/{spec_id}-*.md"
    found, _unparseable = discover_specs(specs_dir)
    for discovered in found:
        if discovered.spec.id == spec_id:
            return discovered.path.relative_to(repo).as_posix()
    return f".saffron/specs/{spec_id}-*.md"


def plan_checkpoint(
    container: str,
    *,
    options: dict,
    spec: CellSpec,
    protected: list[str],
    elevate_on: list[str],
    agent: Callable[..., AttemptResult],
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> tuple[AttemptResult, str, float]:
    """Turn one: the plan, validated before an implementation token is spent.

    Returns the turn's result, the raw JSON of the accepted plan, and what the
    checkpoint spent in total — the re-prompted turn included, or a rejected
    turn is a budget that quietly stops counting (§4.1). Raises `PlanRejected`.
    A shape failure gets exactly one re-prompt carrying the validation error;
    anything else is a decision about content and is final.

    The same turn may instead propose scope (SA-0018, §5.2's door reached from
    IMPLEMENT): raises `ScopeProposed` when the proposal escapes `touches`. A
    proposal that does not is refused rather than recorded, and — unlike an
    ordinary content rejection — gets the same one bounded re-prompt a shape
    failure gets, so refusing it cannot itself become the plan's escape hatch.
    """
    from saffron.agents import artifacts

    # `agent` is `implement.run_agent`, wrapped with `spec.spec_id` already
    # bound (§0) — `emit` is handed straight through, with no adapter.
    spent = 0.0
    try:
        attempt = agent(
            container, prompt=implement.PLAN_PROMPT, options=options, emit=emit
        )
        spent = attempt.cost_usd_est
        # ponytail: the door is only here, at the plan checkpoint. A `touches`
        # insufficiency the implementer discovers mid-diff has no exit and
        # still burns to a ceiling — the case SA-0018 opened this door for,
        # one phase later. The prompt asks for it "before writing any code",
        # which shapes the behaviour without bounding it.
        for reprompted in (False, True):
            if artifacts.extraction_kind(attempt.text) == "scope_proposal":
                try:
                    proposal = artifacts.validate_scope_proposal(
                        attempt.text, touches=spec.touches
                    )
                except artifacts.PlanRejected as exc:
                    # Covers both `ScopeProposalNotSchema` (shape) and
                    # `ScopeProposalRefused` (content that did not escape
                    # touches) — both re-promptable exactly once, unlike an
                    # ordinary content `PlanRejected` from `validate_plan`.
                    if reprompted:
                        raise
                    emit(
                        PhaseStart(
                            timestamp=time.time(),
                            spec_id=spec.spec_id,
                            phase="IMPLEMENT",
                            label="SCOPE",
                            detail=f"proposal refused, re-prompting once — {exc}",
                        )
                    )
                    attempt = agent(
                        container,
                        prompt=f"{exc}\n\n{artifacts.EXTRACTION_PROMPT}",
                        options=options,
                        resume=require_session(attempt.session_id),
                        emit=emit,
                        last_cost_usd=attempt.cost_usd_est,
                    )
                    spent += attempt.cost_usd_est
                    continue
                raise artifacts.ScopeProposed(
                    proposal, artifacts.parse_output_block(attempt.text)
                )
            try:
                plan = artifacts.validate_plan(
                    attempt.text,
                    touches=spec.touches,
                    forbidden=spec.forbidden,
                    protected=protected,
                    spec_type=spec.spec_type,
                )
            except artifacts.PlanNotSchema as exc:
                if reprompted:
                    raise
                emit(
                    PhaseStart(
                        timestamp=time.time(),
                        spec_id=spec.spec_id,
                        phase="IMPLEMENT",
                        label="PLAN",
                        detail=f"not the schema, re-prompting once — {exc}",
                    )
                )
                attempt = agent(
                    container,
                    prompt=f"{exc}\n\n{artifacts.EXTRACTION_PROMPT}",
                    options=options,
                    resume=require_session(attempt.session_id),
                    emit=emit,
                    last_cost_usd=attempt.cost_usd_est,
                )
                spent += attempt.cost_usd_est
                continue
            advisory = artifacts.judge_estimate(
                plan, spec.spec_type, spec.risk, elevate_on
            )
            if advisory is not None:
                emit(
                    PhaseStart(
                        timestamp=time.time(),
                        spec_id=spec.spec_id,
                        phase="IMPLEMENT",
                        label="PLAN",
                        detail=advisory,
                    )
                )
            return attempt, artifacts.parse_output_block(attempt.text), spent
    except artifacts.ScopeProposed as proposed:
        # Same accounting `PlanRejected` gets, for the same reason (§4.1): the
        # checkpoint may have spent a re-prompted turn before the proposal
        # that ends it was accepted.
        proposed.spent_usd = spent
        raise
    except artifacts.PlanRejected as rejected:
        # The same accounting the crash path gets, for the same reason: two
        # turns can run before a shape rejection is final, and a checkpoint
        # that rejects is still a checkpoint that spent (§4.1).
        rejected.spent_usd = spent
        raise
    except implement.AgentFailed as failed:
        # A crashed plan turn is not a plan rejected on content, and the cell is
        # still alive, so it is not ORPHANED either (§4.5). The exception keeps
        # its own identity and carries what the checkpoint already spent, or a
        # re-prompted turn's first half stops counting (§4.1).
        prior = failed.attempt or _failed_turn(failed, "")
        failed.attempt = replace(prior, cost_usd_est=spent + prior.cost_usd_est)
        raise
    raise AssertionError("unreachable: the loop returns or raises")


def attempt_event(
    comparison: SuiteComparison,
    *,
    spec_id: str,
    phase: Phase,
    attempt: int,
    decision: Literal["green", "no-progress", "exhausted", "repair"] | None = None,
) -> Attempt:
    """One `Attempt` line for a suite comparison, in GATE and REBUT alike.

    `commits`/`spent_usd_est` are not the suite's to know — the implement turn
    holds them — so both are `None`, the log's word for "not computed", never a
    `0` a reader would take for a measurement (item 47).
    """
    if comparison.aborted:
        return Attempt(
            timestamp=time.time(),
            spec_id=spec_id,
            phase=phase,
            attempt=attempt,
            commits=None,
            spent_usd_est=None,
            aborted=comparison.aborted,
        )
    if comparison.drift:
        return Attempt(
            timestamp=time.time(),
            spec_id=spec_id,
            phase=phase,
            attempt=attempt,
            commits=None,
            spent_usd_est=None,
            drift=comparison.drift,
        )
    return Attempt(
        timestamp=time.time(),
        spec_id=spec_id,
        phase=phase,
        attempt=attempt,
        commits=None,
        spent_usd_est=None,
        new_failures=len(comparison.new_failures),
        decision=decision,
    )


def repair_loop(
    *,
    # The gate suite's attempt number, which only this loop holds; never the
    # ledger's attempt_id, a row id over every turn (item 47).
    judge: Callable[[int], SuiteComparison],
    max_attempts: int,
    repair: Callable[[Sequence[NewFailure]], str | None],
    # Required, not defaulted, for the reason `events.GateResult.against`
    # already states: a forgotten keyword files every attempt's events under
    # an empty id, indistinguishably from an observed one — and SA-0031's log
    # is shared across tasks. Measured: dropping it from the one production
    # call site passed all 1148 tests.
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> tuple[str, int, list[NewFailure]]:
    """GATE ⇄ REPAIR (§5.4), host-invoked. Returns the terminal state, the
    attempt count reached, and the last new-failure list.

    The agent never runs the gates: `repair` receives new failures and nothing
    else — no status, no verdict, no knowledge that it is being measured. It
    returns a terminal state to stop the loop early; the spend ceiling is the
    only thing in v0.5 that does.

    `judge` is one attempt's suite comparison. An advisory failure — `size` at
    `standard`, or a declared `blocking: false` gate — is never one of its new
    failures, so it decides nothing here and `repair` is never handed it (§5.6).
    """
    previous: list[NewFailure] = []
    for attempt in range(1, max_attempts + 1):
        comparison = judge(attempt)
        if comparison.aborted or comparison.drift:
            emit(
                attempt_event(
                    comparison, spec_id=spec_id, phase="GATE", attempt=attempt
                )
            )
            return "GATE_ERROR", attempt, []
        new = list(comparison.new_failures)
        decision = repair_decision(
            attempt=attempt, max_attempts=max_attempts, new=new, previous=previous
        )
        emit(
            attempt_event(
                comparison,
                spec_id=spec_id,
                phase="GATE",
                attempt=attempt,
                decision=decision,
            )
        )
        if decision == "green":
            return "READY_FOR_REVIEW", attempt, new
        if decision in ("no-progress", "exhausted"):
            # §3.3 has one state for both. Which one it was is on the emitted
            # event above; the task's outcome — it could not pass its own
            # gates — is the same either way.
            return "EXHAUSTED", attempt, new
        previous = new
        if stopped := repair(new):
            return stopped, attempt, new
    raise AssertionError("unreachable: repair_decision exhausts at max_attempts")


def _failed_turn(failed: implement.AgentFailed, session_id: str) -> AttemptResult:
    """What a failed turn is worth: its cost. A bound firing, or a crash, must
    never discard committed work (§4.3) — the caller measures the worktree."""
    return failed.attempt or AttemptResult(
        session_id=session_id,
        subtype="error",
        terminal_reason=None,
        num_turns=0,
        cost_usd_est=0.0,
        is_error=True,
    )


def cell_env(proxy_ip: str, thread_env: Mapping[str, str]) -> dict[str, str]:
    """Everything §5.1's per-task block puts in the cell's environment.

    The proxy is the cell's only route out, and `CLAUDE_CODE_OAUTH_TOKEN` is
    the one credential a cell ever holds — the agent runs inside it. A host
    `ANTHROPIC_API_KEY` is deliberately not forwarded: a subscription token
    from `claude setup-token` is separately revocable and its ceiling is
    provider-side, which a key's spend is not (§5.1).
    """
    from saffron.cell import proxy
    from saffron.cell.worktree import STATE_MOUNT

    env = proxy.proxy_env(proxy_ip) | dict(thread_env)
    env["CLAUDE_CONFIG_DIR"] = STATE_MOUNT
    if token := os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    return env


def export_patch(
    container: str,
    spec: CellSpec,
    task_dir: Path,
    emit: Callable[[Event], None],
) -> tuple[str | None, list[str]]:
    """The run's durable product (§0), plus the two facts PACKAGE needs about a
    cell that no longer exists. The commits live only on the worktree volume,
    so a patch not exported ceases to exist at teardown.

    Never raises: this runs from a `finally`. A cell that died, or never
    started, makes the exec fail — reported, not swallowed. The subjects are
    read in their own `try` because a missing subject list is not worth losing
    a package over, and vice versa.
    """
    from saffron.cell import worktree

    def _teardown(step: str, *, ok: bool, detail: str) -> None:
        emit(
            Teardown(
                timestamp=time.time(),
                spec_id=spec.spec_id,
                step=step,
                ok=ok,
                detail=detail,
            )
        )

    head_sha, subjects = None, []
    try:
        subjects = worktree.commit_subjects(container, spec.tree_base)
    except Exception as exc:
        _teardown(
            "commit_subjects",
            ok=False,
            detail=f"the agent's commit subjects are unreadable — {exc}",
        )
    try:
        patch = worktree.export_patch(container, spec.tree_base)
        if not patch:
            # Absence and emptiness must not look alike: no commits, no file.
            _teardown("no_commits", ok=True, detail="no commits, nothing to export")
            return head_sha, subjects
        # The only surviving name for the commit once the volume is gone — the
        # diff itself does not carry it.
        head_sha = worktree.head_sha(container)
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "patch.diff").write_text(patch)
        (task_dir / "patch.json").write_text(
            json.dumps(
                {
                    # The run's pin, unchanged. `tree_base` is what the
                    # diff below is relative to; equal unless stacked.
                    "base_sha": spec.base_sha,
                    "tree_base": spec.tree_base,
                    "head_sha": head_sha,
                    "files": worktree.changed_files(container, spec.tree_base),
                },
                indent=2,
            )
        )
        _teardown(
            "exported",
            ok=True,
            detail=f"exported {len(patch)} bytes to {task_dir / 'patch.diff'}",
        )
    except Exception as exc:
        _teardown("export_failed", ok=False, detail=f"patch export FAILED — {exc}")
    return head_sha, subjects


def run_one_cell(
    spec: CellSpec,
    *,
    repo: Path,
    mirror: Path,
    ledger: Ledger,
    out_dir: Path,
    emit: Callable[[Event], None] | None = None,
) -> CellOutcome:
    """Create a cell, drive one IMPLEMENT session in it, and gate the result.

    Returns what the cell produced, terminal state included. Every transition
    is printed, because v0.5's whole point is that the operator watches it.

    The default lives here, not in `cli.py` (forbidden to this spec) and not
    in `_drive_cell` (which does not yet know `task_dir` when this is called):
    a caller that hands no `emit` gets both consumers `_default_emit`
    describes — the terminal, and one `EventLog` at this run's own
    `task_dir` — built once, so the two agree on the object they are being
    handed rather than each constructing their own.

    Thin, because teardown learns two of the outcome's fields *after* every
    `return` inside `_drive_cell`: a `finally` cannot reach a value already
    returned, so the export hands them back through `exported` and they are
    stamped here.
    """
    if emit is None:
        log = EventLog(out_dir / spec.spec_id)
        emit = partial(_default_emit, log=log)
    exported: dict = {}
    outcome = _drive_cell(
        spec,
        repo=repo,
        mirror=mirror,
        ledger=ledger,
        out_dir=out_dir,
        emit=emit,
        exported=exported,
    )
    outcome.cell_head_sha = exported.get("head_sha")
    outcome.agent_subjects = exported.get("subjects", [])
    return outcome


def cell_up(
    *,
    repo: Path,
    mirror: Path,
    tree_base: str,
    branch: str,
    network: str,
    volume: str,
    state: str,
    container: str,
    gates_dir: Path,
    thread_env: Mapping[str, str],
    created: set[str],
    note: Callable[[str, str], None],
) -> None:
    """Bring a cell up: network, proxy, image, isolation asserts, worktree.

    Extracted from `_drive_cell` so a second caller cannot get a *nearly*
    isolated cell. The order is load-bearing and was found by spike rather than
    reasoned — the proxy before any container, the host-port probe before the
    worktree — so a paraphrase of it somewhere else is the shape Appendix I
    describes: every mechanism reports success and applies to a different
    container. One copy, and the callers differ only in what they do after it.

    `critic_cell` is the one sanctioned second path (SA-0087). It joins the
    network this call already built, so the host-port probe and the proxy
    reachability assert are properties it inherits rather than repeats; it
    starts, stops and removes neither the network nor the proxy.

    `created` is the caller's leak ledger, appended to in place, so a failure
    part-way leaves the caller holding exactly what may survive. `note` takes
    the progress lines: `_drive_cell` sends them to `Preflight` events, and a
    harness may simply print them.

    Nothing bound here outlives the call — the proxy address, the built image
    tag and the probed port list are all consumed before it returns.
    """
    from saffron import preflight
    from saffron.cell import proxy, runtime, worktree
    from saffron.repos import image

    # Inside the guarantee, not above it: a leftover network from a SIGKILLed
    # run makes `create_network` the first thing that raises on a re-run.
    runtime.remove_network(network)
    runtime.remove_volume(volume)
    runtime.remove_volume(state)
    created.add(network)
    runtime.create_network(network)

    # First of everything: on apple/container 1.3.0 a container on the
    # internal network before the proxy leaves it no route out (evidence
    # 2026-08-28), and a dead route found here costs one container start
    # rather than an image build and an attempt (§5.1.1).
    note("proxy_starting", "starting the proxy")
    proxy_ip = proxy.start_proxy(network)
    note("proxy_addr", f"proxy at {proxy_ip}")
    answered = preflight.assert_proxy_reaches_upstream(
        image.BASE_TAG, network, proxy_ip
    )
    note("egress", f"proxy reaches {proxy.UPSTREAM_HOST} ({answered})")

    # The cell runs the repo's own image, never the base: the base carries
    # no toolchain, so every gate would error before the agent is reached.
    note("image", f"building {image.cell_tag(repo)}")
    cell_image = image.build_cell_image(repo)

    # Probed from the base image, not the repo's. The probe runs `python`,
    # and core must not require an interpreter inside every target repo's
    # image — a Rust repo could then never start a cell (§2.1). What the
    # probe establishes is a property of the network, which both images
    # join identically.
    # The port count is the operator's evidence that enumeration ran: a
    # probe covering nothing is what a silent failure looks like. The
    # tolerated listeners print every run, including when there are none —
    # an exception that goes quiet is the invisibility it was granted around.
    ports, tolerated = preflight.host_probe_ports()
    note(
        "ports",
        f"probing {len(ports)} host ports at "
        + ", ".join(preflight.probe_addresses())
        + "; tolerating "
        + (", ".join(tolerated) or "nothing"),
    )
    # The list the operator was just shown, not a second one taken now. No
    # cell exists yet, and none will until this returns.
    preflight.assert_host_is_unreachable(image.BASE_TAG, network, ports)

    created.add(volume)
    runtime.create_volume(volume)
    # The state volume and the container are recorded inside, each against
    # its own create: an ephemeral seed container runs between them.
    worktree.prepare_worktree(
        created=created,
        mirror=mirror,
        volume=volume,
        # The tree's base, already resolved — `prepare_worktree` does
        # not re-derive it. `base_sha` still pins the gates and policy.
        base_sha=tree_base,
        branch=branch,
        image=cell_image,
        container=container,
        network=network,
        env=cell_env(proxy_ip, thread_env),
        gates_dir=gates_dir,
        state_volume=state,
    )
    note("cell_up", f"{container} up, worktree at {tree_base[:8]}")


def cell_down(
    *,
    network: str,
    volume: str,
    state: str,
    container: str,
    created: set[str],
    note: Callable[[str, bool, str], None],
) -> None:
    """Take a cell down: container, proxy log, proxy, network, volumes.

    `cell_up`'s pair, extracted for the same reason — a second caller cannot get
    a *nearly* complete teardown. The order is load-bearing: the proxy is a
    container on this network, so stopping it after `remove_network` leaves both
    behind, and `remove_network` reports that only through a return code. The
    harness paraphrased this block once and its first run died on "network
    saffron-cells already exists".

    `created` is the caller's leak ledger, read here rather than written: a
    non-zero exit is a leak only for something this caller made. `note` takes
    (step, ok, detail) — `_drive_cell` sends them to `Teardown` events, a
    harness may simply print them.

    A non-zero exit is reported, never raised — callers run this from a
    `finally`. `CellRuntimeError` still escapes if the runtime binary itself
    cannot be executed, as it did before this was extracted.
    """
    from saffron.cell import proxy, runtime

    removed = [("container", container, runtime.remove_container(container))]
    # Before the proxy goes: its log goes with it.
    for denied in proxy.denied_egress():
        note("proxy_denied", False, f"proxy DENIED {denied}")
    # Not a denial: an allowed CONNECT the proxy could not open. Reported apart
    # because the fix is the network, not the allowlist.
    for failed in proxy.failed_egress():
        note("proxy_failed", False, f"proxy FAILED {failed}")
    proxy.stop_proxy()
    removed.append(("network", network, runtime.remove_network(network)))
    # Volumes go too, or the same spec_id cannot be re-run.
    removed.append(("volume", volume, runtime.remove_volume(volume)))
    removed.append(("volume", state, runtime.remove_volume(state)))
    # Pre-cleaning tolerates absence; here a non-zero exit is a leak, and a
    # silent one is what let the state volume survive teardown unnoticed.
    for kind, name, done in removed:
        if done.returncode != 0 and name in created:
            note(
                "survived",
                False,
                f"{kind} {name} survived — {done.stderr.strip()[:160]}",
            )


class CriticPatchRejected(RuntimeError):
    """The exported patch does not apply against its own base in a fresh
    critic cell tree (CONTEXT.md §5, backlog item 118). The agent's problem,
    not the toolchain's — the export ran clean, `git apply` just refused it —
    so `EXHAUSTED` is the state that fits, the same one four red gate
    attempts would reach."""


class CriticPatchUnrepresentable(RuntimeError):
    """The patch could never have applied: `worktree.DIFF_FLAGS` carries no
    `--binary`/`--full-index`, so a binary change comes back as a
    `_NO_FULL_INDEX` stub no base can apply — the same marker PACKAGE's own
    `apply_patch` already reads as infrastructure. Saffron's ceiling, not the
    agent's: `GATE_ERROR`, charged to nobody."""


def _apply_and_commit_patch(container: str, patch: str) -> None:
    """Apply the implementer's exported patch inside the critic cell's own
    git, then commit it — so what the lenses judge is the patch that ships,
    not a second read of the implementer's history (CONTEXT.md §5).

    The patch travels on stdin, never as an argument: Linux caps a single
    argv at `MAX_ARG_STRLEN` (measured against `saffron/cell-base:python` for
    `worktree._write_file`'s mutant), and a limit that is Saffron's own must
    not end a task the agent is charged for. `worktree._git` carries no stdin,
    so both calls take its pins from `worktree.git_argv` (backlog item 136).

    `--index`, PACKAGE's own spelling, rather than a following `git add -A`:
    staging re-runs the clean filters the patch's own `.gitattributes` just
    installed. Measured — a file committed before an attribute naming it
    `working-tree-encoding=UTF-16` leaves `git apply` at 0 and `git add` at
    128 — which ended the task as infrastructure, charged to nobody and with
    no lens run, and is the free way past a check `d3b9c51` names.
    """
    from saffron.cell import runtime, worktree
    from saffron.phases.package import _NO_FULL_INDEX

    def _ignore(_line: str) -> bool:
        return False

    applied = runtime.exec_stream(
        container,
        worktree.git_argv("apply", "--index"),
        stdin_data=patch,
        on_line=_ignore,
        workdir=worktree.WORKTREE_MOUNT,
    )
    if applied.timed_out:
        # Saffron's own wall or idle bound, not a refused apply — reading exit
        # 124 as a refusal would charge the agent for a bound that is ours
        # (error != fail, CLAUDE.md).
        raise runtime.CellRuntimeError(
            "applying the exported patch hit Saffron's own bound: "
            f"{applied.stderr.strip()[:200]}"
        )
    # Checked whatever the exit code, before the ordinary conflict check: the
    # stub this marker names is what a binary change becomes, whatever git
    # apply's own exit status reads as.
    # ponytail: an agent can reach this on purpose, by committing a file git
    # reads as binary, and end its task uncharged — the same ceiling `size`
    # and `integrity` already carry for a hidden binary (backlog item 103);
    # nothing ships from it either, since only READY_FOR_REVIEW is packaged.
    if _NO_FULL_INDEX in applied.stderr:
        raise CriticPatchUnrepresentable(applied.stderr.strip()[:400])
    if applied.returncode != 0:
        raise CriticPatchRejected(applied.stderr.strip()[:400])

    committed = runtime.exec_(
        container,
        worktree.git_argv(
            "commit", "-q", "-m", "critic: exported patch, applied and committed"
        ),
        workdir=worktree.WORKTREE_MOUNT,
    )
    if committed.returncode != 0:
        # The agent's content, so the agent's task: an exec that cannot launch
        # raises `CellRuntimeError` from `exec_` itself, and anything this
        # reaches is what the patch left in the index. Says which step it was,
        # since the caller's reason names the apply.
        raise CriticPatchRejected(
            f"applied, but could not be committed: {committed.stderr.strip()[:360]}"
        )


# Drawn from the one declaration (runtime.SUBNETS, backlog item 143): neither
# `saffron-cells` (the task's, still up when this cell is created) nor
# `saffron-egress` (the proxy's) is torn down first, so this has to be a value
# nothing else holds — see runtime.py for every subnet Saffron allocates.
_GATE_CELL_SUBNET = runtime.SUBNETS["gate"]


@contextlib.contextmanager
def critic_cell(
    *,
    spec: CellSpec,
    repo: Path,
    mirror: Path,
    network: str | None,
    env: Mapping[str, str],
    gates_dir: Path,
    patch: str,
    created: set[str],
    note: Callable[[str, bool, str], None],
) -> Iterator[str]:
    """A fresh container from the repo's cell image, seeded at the task's tree
    base and carrying the implementer's exported patch, applied and committed
    by its own git (CONTEXT.md §5, backlog items 118 and 140). Never the
    implementer's own container: a fresh session there still re-execs a
    runner and an SDK that container's root could have rewritten.

    Serves every short-lived cell that needs exactly this — REVIEW's lens
    container, REBUT's verdict-lens container (`SA-0088`), and the gate suite
    REVIEW's lenses are shown (`SA-0087`, backlog item 118 part 4) — which is
    why the whole lifecycle lives in one function rather than three inlined
    copies of it (backlog item 140).

    `network` decides the names and who owns the network; the caller's `env`
    is what keeps a Gate-only cell off the proxy. Given a name, this joins it — the pieces `cell_up` already brought up for
    the task, the network and the proxy behind it — and neither starts, stops
    nor removes it; the container and its two volumes are named
    `saffron-critic-*`. Given `None`, this makes a network of its own, on
    `_GATE_CELL_SUBNET` rather than the task's own `saffron-cells`, and pre-
    cleans and tears it down itself, in the same `finally` as everything
    else it made; the container, its two volumes and this network are named
    `saffron-gate-*`. Keyword-only with no default either way — v0.5 shipped
    a cell with neither a declared network nor a declared env once, and every
    mechanism reported success while applying to a different container
    (Appendix I).

    `env` is the container's environment, exactly as given — a caller behind
    the proxy builds `cell_env(proxy_ip, thread_env)` itself and hands it in;
    a caller that wants only the repo's declared gate env passes
    `dict(thread_env)` and nothing more. This function reads no proxy address
    and injects nothing.

    `created` is the caller's leak ledger, exactly as `cell_up`/`cell_down`
    use it. `note` takes (step, ok, detail), the same shape `cell_down` gives
    its own — called only when a removal leaves something behind, so a green
    path prints nothing this spec did not already print.
    """
    from saffron.cell import runtime, worktree
    from saffron.repos import image

    own_network = network is None
    if own_network:
        container = f"saffron-gate-{spec.spec_id}"
        volume = f"saffron-gate-wt-{spec.spec_id}"
        state = f"saffron-gate-st-{spec.spec_id}"
        # Lowercased: apple/container refuses an uppercase network name
        # (measured 2026-09-16), and a spec id is uppercase.
        network = f"saffron-gate-net-{spec.spec_id.lower()}"
    else:
        container = f"saffron-critic-{spec.spec_id}"
        volume = f"saffron-critic-wt-{spec.spec_id}"
        state = f"saffron-critic-st-{spec.spec_id}"

    # Inside the guarantee, not above it — the same reason `cell_up` pre-cleans
    # before adding a name to `created`: a leftover from a SIGKILLed run must
    # not make this run's own create the first thing that fails. The network
    # is pre-cleaned on the branch that creates it, not only torn down.
    runtime.remove_container(container)
    if own_network:
        runtime.remove_network(network)
        # The collision is by subnet, and another spec's leftover holds it
        # under its own name: remove ours, never an operator's (item 143).
        for holder in runtime.networks_on_subnet(_GATE_CELL_SUBNET):
            if holder.startswith("saffron-"):
                runtime.remove_network(holder)
    runtime.remove_volume(volume)
    runtime.remove_volume(state)
    try:
        if own_network:
            created.add(network)
            runtime.create_network(network, subnet=_GATE_CELL_SUBNET)
        created.add(volume)
        runtime.create_volume(volume)
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=spec.tree_base,
            branch=spec.branch,
            image=image.cell_tag(repo),
            container=container,
            network=network,
            env=env,
            gates_dir=gates_dir,
            state_volume=state,
            created=created,
        )
        _apply_and_commit_patch(container, patch)
        yield container
    finally:
        removed = [
            ("container", container, runtime.remove_container(container)),
            ("volume", volume, runtime.remove_volume(volume)),
            ("volume", state, runtime.remove_volume(state)),
        ]
        if own_network:
            # Removed last: a network with a container still on it will not go.
            removed.append(("network", network, runtime.remove_network(network)))
        for kind, name, done in removed:
            if done.returncode != 0 and name in created:
                note(
                    "survived",
                    False,
                    f"{kind} {name} survived — {done.stderr.strip()[:160]}",
                )


def _gate_cell_suite(
    *,
    spec: CellSpec,
    repo: Path,
    mirror: Path,
    gates_dir: Path,
    thread_env: Mapping[str, str],
    patch: str,
    suite: GateSuite,
    baseline: SuiteRun,
    created: set[str],
    note: Callable[[str, bool, str], None],
) -> SuiteComparison:
    """The gate suite REVIEW's lenses are shown, run in a cell of its own
    (CONTEXT.md §5, backlog item 118): never the implementer's own container,
    whose toolchain the agent had root over, and never the critic's either —
    a gate executes model-authored code (the tests the implementer wrote) as
    root, and running that in the container the lenses re-exec a moment later
    is the hole `SA-0087` closed.

    The whole lifecycle — pre-clean, `prepare_worktree`, patch apply, teardown
    in a `finally` — is `critic_cell`'s, entered here with `network=None` so
    it makes and tears down a network of its own rather than joining the
    task's, and `env=dict(thread_env)` so the container carries the repo's
    declared gate env and nothing else: no proxy, no credential, no route out
    (backlog item 140; item 134 is the same collapse for `reverify`'s own
    `_gate_cell` in `saffron/phases/package.py`, out of reach here).

    Judged against `baseline`, the run's own pre-turn suite: not a second,
    freshly-taken one, so `census`, `criteria` and `revert` still have a real
    prior to compare against rather than reporting `skip` across the board.

    Never touches `latest`: that stays the implementer's own last suite, for
    `CellOutcome.gates`/`effective_risk`/`advisory_gates` alike. This suite is
    the lens table only.
    """
    from saffron.gates.suite import CellTree

    with critic_cell(
        spec=spec,
        repo=repo,
        mirror=mirror,
        network=None,
        # The repo's declared gate env, and nothing else: no agent, no
        # credential and no route out — this cell only runs gates.
        env=dict(thread_env),
        gates_dir=gates_dir,
        patch=patch,
        created=created,
        note=note,
    ) as container:
        return suite.against(CellTree(container, cwd=repo), baseline)


def _probe_adequacy(
    *,
    spec: CellSpec,
    repo: Path,
    mirror: Path,
    gates_dir: Path,
    thread_env: Mapping[str, str],
    test_paths: Sequence[str],
    gates: dict[str, Path],
    patch: str,
    reviews: list[review.LensReview],
    created: set[str],
    note: Callable[[str, bool, str], None],
) -> list[dict]:
    """Every anchored adequacy finding's vacuity probe, asked once each
    (backlog item 117), in a Gate-only cell entered *after* REVIEW's own
    critic cell is torn down — never inside it, the hole `SA-0087` closed.

    Decides each finding's `severity`/`probe_verdict` in place before
    returning, so the caller's later `ledger.record_findings` sees the
    decided findings. Returns `probes.json`'s own list; writes nothing.
    """
    from saffron import probe as probe_check
    from saffron.cell import worktree
    from saffron.gates import runner

    targets = review.adequacy_probes(reviews)
    if not targets:
        return []
    # Captured before anything is decided, or a promotion loses it.
    filed = {id(f): f.severity for f in targets}
    by_probe: dict[tuple[str, str, str], list[Finding]] = {}
    for f in targets:
        assert f.probe is not None  # adequacy_probes already filtered this
        by_probe.setdefault(review.probe_key(f.probe), []).append(f)

    entries: list[dict] = []

    def decide(probe: Mutant, result) -> None:
        findings = by_probe[review.probe_key(probe)]
        for f in findings:
            review.apply_probe_verdict(f, result.verdict)
        entries.append(
            {
                **probe_check.record_fields(probe, result),
                "probe_verdict": result.verdict,
                "findings": [
                    {
                        "lens": f.lens,
                        "file": f.file,
                        "line": f.line,
                        "filed_severity": filed[id(f)],
                    }
                    for f in findings
                ],
            }
        )

    def unproven(pending: list[Mutant], reason: str, record=None) -> None:
        for p in pending:
            decide(p, probe_check.ProbeResult("unproven", reason, baseline=record))

    probes = review.distinct_probes(targets)
    refused = {
        review.probe_key(p): reason
        for p in probes
        if (reason := probe_check.probe_refusal(p.file, test_paths)) is not None
    }
    # The mutator is never entered for a refused probe (item 117, b-461729).
    for p in probes:
        if review.probe_key(p) in refused:
            decide(p, probe_check.ProbeResult("unproven", refused[review.probe_key(p)]))
    remaining = [p for p in probes if review.probe_key(p) not in refused]
    if not remaining:
        return entries
    if "tests" not in gates:
        # As the lens-corpus driver's own `_apply_probes` does: no cell.
        unproven(
            remaining,
            "this repo's head declares no `tests` gate, so nothing could "
            "answer the probe",
        )
        return entries

    def _run_tests(container: str, executable: Path, cwd: Path, subset: list[str]):
        return runner.run_gate(
            "tests",
            executable,
            cwd,
            subset=subset,
            executor=runner.CellExecutor(container),
        )

    # Entered through a stack so a cell that never comes up is one more
    # infrastructure failure, not an exception that discards a paid REVIEW.
    stack = contextlib.ExitStack()
    try:
        container = stack.enter_context(
            critic_cell(
                spec=spec,
                repo=repo,
                mirror=mirror,
                network=None,
                env=dict(thread_env),  # the repo's declared gate env, nothing more
                gates_dir=gates_dir,
                patch=patch,
                created=created,
                note=note,
            )
        )
    except runtime.CellRuntimeError as exc:
        unproven(remaining, f"the probe cell could not be entered: {exc}")
        return entries
    with stack:
        run_tests = partial(_run_tests, container, gates["tests"], repo)
        try:
            baseline = run_tests([])
        except runtime.CellRuntimeError as exc:
            unproven(remaining, f"the baseline tests gate could not run: {exc}")
            return entries
        # `check_probe` builds its own for each result it returns, so this
        # copy is only for the entries the host authors: the raise path's.
        record = probe_check.BaselineRecord.of(baseline)
        for index, p in enumerate(remaining):
            try:
                result = probe_check.check_probe(
                    p,
                    baseline=baseline,
                    mutate=partial(worktree.source_mutated, container),
                    run_tests=run_tests,
                    test_paths=test_paths,  # the same list every probe was asked about
                )
            except runtime.CellRuntimeError as exc:
                # A failed undo leaves the tree untrustworthy (item 117): no
                # later probe reaches the mutator either.
                decide(
                    p,
                    probe_check.ProbeResult(
                        "unproven",
                        f"the probe could not be applied or asked: {exc}",
                        baseline=record,
                    ),
                )
                unproven(
                    remaining[index + 1 :],
                    "an earlier probe left this cell's tree in an unknown "
                    "state, so nothing after it was asked",
                    record,
                )
                break
            decide(p, result)
    return entries


def _apply_criterion_probes(
    *,
    spec: CellSpec,
    repo: Path,
    mirror: Path,
    gates_dir: Path,
    thread_env: Mapping[str, str],
    test_paths: Sequence[str],
    gates: dict[str, Path],
    patch: str,
    entries: list[dict],
    diff: str,
    gate_comparison: SuiteComparison,
    reviews: list[review.LensReview],
    created: set[str],
    note: Callable[[str, bool, str], None],
) -> None:
    """Every criterion probe's own edit, applied and asked of its own witness
    (backlog item b-2750d5). It runs in a Gate-only cell entered after
    `_probe_adequacy`'s own is torn down, never inside the critic cell.

    Writes each edit's outcome and summary into `entries` in place. Appends a
    survivor's `Finding` to the `adequacy` review in `reviews`, the same
    in-place contract `_probe_adequacy` keeps with its caller.
    """
    from saffron import probe as probe_check
    from saffron.cell import worktree
    from saffron.gates import runner
    from saffron.gates.core.witness import witness_gate

    paired = list(zip(spec.acceptance, entries, strict=True))
    unknown_tree = (
        "an earlier edit left this cell's tree in an unknown state, so nothing "
        "after it was asked"
    )

    def _unproven(pending: list[tuple[Criterion, dict]], reason: str) -> None:
        for _criterion, entry in pending:
            entry["outcome"] = "unproven"
            entry["summary"] = reason

    # The mutator is never entered for an entry with no edit or a refused one.
    with_edit: list[tuple[Criterion, dict]] = []
    for criterion, entry in paired:
        if entry["edit"] is None:
            _unproven([(criterion, entry)], "this session named no edit")
            continue
        refusal = probe_check.probe_refusal(entry["edit"]["file"], test_paths)
        if refusal is not None:
            _unproven([(criterion, entry)], refusal)
            continue
        with_edit.append((criterion, entry))

    if not with_edit:
        return
    if "tests" not in gates:
        _unproven(
            with_edit,
            "this repo's head declares no `tests` gate, so nothing could "
            "answer the probe",
        )
        return

    collected = next(
        (r.collected for r in gate_comparison.run.results if r.gate == "tests"), None
    )
    adequacy = next(r for r in reviews if r.lens == "adequacy")

    stack = contextlib.ExitStack()
    try:
        container = stack.enter_context(
            critic_cell(
                spec=spec,
                repo=repo,
                mirror=mirror,
                network=None,
                env=dict(thread_env),  # the repo's declared gate env, nothing more
                gates_dir=gates_dir,
                patch=patch,
                created=created,
                note=note,
            )
        )
    except runtime.CellRuntimeError as exc:
        _unproven(with_edit, f"the probe cell could not be entered: {exc}")
        return

    with stack:
        # `witness_gate` reports a raise here and a gate `error` alike as
        # `error`. Only this note tells them apart.
        stopped: str | None = None

        @contextlib.contextmanager
        def _mutate(edit: Mutant):
            nonlocal stopped
            try:
                with worktree.source_mutated(container, edit) as reason:
                    yield reason
            except runtime.CellRuntimeError as exc:
                stopped = str(exc)
                raise

        def _run_tests(subset: list[str]) -> GateResult:
            nonlocal stopped
            try:
                return runner.run_gate(
                    "tests",
                    gates["tests"],
                    repo,
                    subset=subset,
                    executor=runner.CellExecutor(container),
                )
            except runtime.CellRuntimeError as exc:
                stopped = str(exc)
                raise

        for index, (criterion, entry) in enumerate(with_edit):
            edit = Mutant.model_validate(entry["edit"])
            result = witness_gate(
                acceptance=[criterion.model_copy(update={"mutant": edit})],
                mutate=_mutate,
                run_tests=_run_tests,
                collected=collected,
            )
            entry["outcome"] = review.criterion_probe_outcome(result.status)
            entry["summary"] = result.summary
            if stopped is not None:
                # `witness_gate` already reports this entry as `error`, with
                # the summary kept above. `stopped` only ends the loop.
                _unproven(with_edit[index + 1 :], unknown_tree)
                return
            if entry["outcome"] != "survived":
                continue
            try:
                content = worktree.read_at_head(container, edit.file)
                if content is None or edit.find not in content:
                    entry["outcome"] = "error"
                    entry["summary"] = "the survivor's line could not be read"
                    continue
                finding = review.survivor_finding(criterion, edit, content)
                (anchored,) = anchor(
                    [finding], diff, read_head=partial(worktree.read_at_head, container)
                )
            except runtime.CellRuntimeError as exc:
                entry["outcome"] = "error"
                entry["summary"] = f"the survivor's line could not be read: {exc}"
                _unproven(with_edit[index + 1 :], unknown_tree)
                return
            adequacy.findings.append(anchored)


def _drive_cell(
    spec: CellSpec,
    *,
    repo: Path,
    mirror: Path,
    ledger: Ledger,
    out_dir: Path,
    emit: Callable[[Event], None],
    exported: dict,
) -> CellOutcome:
    """`run_one_cell`'s whole body. `exported` is teardown's way out."""
    from saffron.agents import artifacts, context
    from saffron.cell import proxy, runtime, worktree
    from saffron.gates.core.criteria import witnesses_green_at_base
    from saffron.gates.suite import CellTree, GateSuite
    from saffron.repos import mirror as mirror_ops
    from saffron.repos.policy import PolicyError, load_policy

    def _preflight(step: str, detail: str) -> None:
        emit(
            Preflight(
                timestamp=time.time(), spec_id=spec.spec_id, step=step, detail=detail
            )
        )

    def _phase_start(phase: Phase, label: LineLabel, detail: str) -> None:
        emit(
            PhaseStart(
                timestamp=time.time(),
                spec_id=spec.spec_id,
                phase=phase,
                label=label,
                detail=detail,
            )
        )

    network = "saffron-cells"
    volume = f"saffron-wt-{spec.spec_id}"
    state = f"saffron-st-{spec.spec_id}"
    container = f"saffron-cell-{spec.spec_id}"

    # Hoisted above the try: teardown exports here too, including on paths that
    # never reached the baseline write below.
    task_dir = out_dir / spec.spec_id
    # Ahead of its three siblings in the pre-clean below, because the export
    # clears the bind-mount source and a SIGKILLed run of this spec can still
    # have it live at /gates.
    runtime.remove_container(container)
    # Before the cell exists — the mount source has to be there when the
    # container is created — and before the policy, which is read back out of
    # it. Reading the policy from the operator's checkout while the gates it
    # declares come from `base_sha` diverges the two on any branch that
    # touches `.saffron/` (§5.4).
    task_dir.mkdir(parents=True, exist_ok=True)
    gates_dir = mirror_ops.export_saffron_dir(mirror, spec.base_sha, task_dir / "gates")
    # Beside gates_dir, not at the prompt-build site: every base-sha input is
    # read before a cell exists, so a GitError fails before one is created.
    # ponytail: Claude Code's own `@path` imports inside CLAUDE.md still reach
    # the model as literal text, and file_at follows only one symlink hop.
    claude_md = mirror_ops.file_at(mirror, spec.base_sha, "CLAUDE.md")

    # R2: the on-host validation stays — a declared gate exists and is
    # executable — but it now runs against the exported tree the cell mounts.
    # The paths run_suite is given must be cell-side: CellExecutor always
    # execs at /work (Task 6) and a host path there resolves to nothing.
    try:
        policy, policy_sha = load_policy(gates_dir)
    except PolicyError as exc:
        # The path it reports is a batch-tree directory the operator has never
        # opened. Unnamed, the base sends them to their own policy.yaml, which
        # is correct — the wrong diagnosis this read exists to stop.
        raise PolicyError(f"at base {spec.base_sha[:12]}: {exc}") from exc
    # Cell-side, and from the read-only mount rather than /work: an in-cell
    # edit to a gate — committed or not — never reaches the runner (§5.4).
    gates = policy.gate_executables(Path(worktree.GATES_MOUNT))

    if drift := spec_drift(gates_dir, spec.spec_id, spec.spec_sha):
        _preflight("spec_drift", drift)

    # §4.1: `origin` is the real remote, `mirror_path` the local mirror. v0
    # stored the mirror's source in both, so nothing downstream knew where a
    # pull request would go. `cli._run_cell` now calls `real_remote` itself to
    # get `base_sha`, before a `CellSpec` exists, so a repo with no origin
    # exits 2 there rather than reaching this cell. The fallback stays for a
    # caller of `run_one_cell` that skips that path — it should still get a
    # runnable, unpackageable cell rather than a crash.
    from saffron.phases import package

    try:
        origin_url = package.real_remote(repo)
    except package.PackageError:
        origin_url = str(repo)
    repo_id = ledger.upsert_repo(repo.name, origin_url, str(mirror), policy_sha)
    run_id = ledger.create_run(repo_id, spec.base_sha)
    task_id = ledger.create_task(
        run_id,
        spec.spec_id,
        spec.spec_sha,
        branch=spec.branch,
        budget_usd=spec.budget_usd,
        # The spec-declared tier only: no diff exists yet for an `elevate_on`
        # path to have matched, and there is no later write to correct it
        # against (§5.6). `_suite` below computes the real, per-attempt
        # effective tier from the diff it already has.
        risk=spec.risk,
        # The declaration these gates actually ran under, read above from the
        # export at base_sha — never the working copy (§5.4, backlog item 16).
        policy_sha=policy_sha,
        # The prompt tree the cell was given, digested as authored — the
        # third input beside spec_sha and policy_sha (§4.1).
        prompt_sha=context.prompt_sha(),
    )

    # Only what this run reached the creation of can leak. `volume rm` on a
    # name that never existed also exits non-zero, so reporting every failure
    # prints survivors for a run that aborted in preflight — absent reading as
    # leaked, which trains the operator to ignore the line. Each name is
    # recorded immediately before its own create, never a batch before the
    # first: a create that fails part-way can still have left its resource, but
    # the two that were never attempted are not survivors of anything.
    created: set[str] = set()

    # Bound before the try, not by plan_checkpoint's assignment: RateLimited can
    # unwind from anywhere in the body, and the accumulated total must survive
    # even when it fires before that assignment runs.
    spent = 0.0

    try:
        cell_up(
            repo=repo,
            mirror=mirror,
            tree_base=spec.tree_base,
            branch=spec.branch,
            network=network,
            volume=volume,
            state=state,
            container=container,
            gates_dir=gates_dir,
            thread_env=policy.thread_env,
            created=created,
            note=_preflight,
        )

        tree = CellTree(container, cwd=repo)
        # Measured from `tree_base`, unlike doneness: `scope` judges the whole
        # task diff a reviewer reads, the plan turn's commits included.
        suite = GateSuite(
            gates=gates, spec=spec, policy=policy, diff_base=spec.tree_base
        )
        baseline = suite.baseline(tree)
        # The last suite run: every outcome reports its tier and advisory set,
        # so an outcome never reads a stale attempt's (§5.6).
        latest = baseline
        green_at_base = witnesses_green_at_base(spec.acceptance, baseline.results)
        # One event, one line per fact present; `describe()` joins them with
        # "\n" (§5.4, `events.Baseline`'s own docstring).
        emit(
            Baseline(
                timestamp=time.time(),
                spec_id=spec.spec_id,
                aborted=tuple(baseline.aborted),
                gates=tuple(r.gate for r in baseline.results),
                statuses=tuple(r.status for r in baseline.results),
                green_at_base=tuple(green_at_base),
            )
        )
        for result in baseline.results:
            ledger.record_gate_result(result, run_id=run_id)
            # Beside the joined `Baseline` line, not replacing it. No count:
            # a baseline is measured against, never a subject of one.
            emit(
                GateResultEvent(
                    timestamp=time.time(),
                    spec_id=spec.spec_id,
                    gate=result.gate,
                    status=result.status,
                    against="baseline",
                )
            )

        (task_dir / "baseline.json").write_text(
            json.dumps([r.model_dump() for r in baseline.results], indent=2)
        )

        if baseline.aborted:
            # Written where it is known, never derived from `tasks.state`.
            ledger.set_run_preflight(run_id, "FAILED")
            ledger.set_task_state(task_id, "PREFLIGHT_FAILED")
            ledger.finish_run(run_id, "COMPLETE")
            return CellOutcome(
                state="PREFLIGHT_FAILED",
                task_id=task_id,
                run_id=run_id,
                task_dir=task_dir,
                effective_risk=latest.effective_risk,
                advisory_gates=sorted(latest.advisory_gates),
            )

        # Once, here: a later abort says nothing about fitness to start.
        ledger.set_run_preflight(run_id, "PASSED")

        # The agent runs inside the cell, at /work, on the cell's own key (§5.1).
        context_md = (_SAFFRON_ROOT / "CONTEXT.md").read_text()
        template = (context.PROMPTS_DIR / "implement.md").read_text()
        system_prompt = context.build_system_prompt(
            "IMPLEMENT",
            context_md,
            template=template,
            spec=spec.body,
            # The body is prose; the paths the plan and the diff are judged
            # against live in frontmatter and policy.yaml, so they are injected.
            constraints=context.constraints_block(
                spec.touches, spec.forbidden, policy.protected
            ),
            witnesses=context.witnesses_block(spec.acceptance),
            standing_instructions=context.standing_instructions(claude_md),
        )
        options = implement.agent_options(
            system_prompt=system_prompt,
            cwd=worktree.WORKTREE_MOUNT,
            max_turns=spec.max_turns,
            budget_usd=spec.budget_usd,
        )
        _phase_start(
            "IMPLEMENT", "IMPLEMENT", f"system prompt {len(system_prompt)} chars"
        )
        ledger.set_task_state(task_id, "IMPLEMENTING")

        # Bound once, here, so no turn — plan, implement, repair, review or
        # rebuttal — can quietly inherit the library's hour (§4.3), or run on
        # against a window the provider already closed. `spec_id` is bound
        # here too: every call site below hands this `agent` an `emit`
        # straight through, with no adapter to carry the id instead (§0).
        agent = stop_on_rejected(
            record_attempts(
                partial(
                    implement.run_agent,
                    timeout_s=TURN_TIMEOUT_S,
                    spec_id=spec.spec_id,
                ),
                ledger=ledger,
                task_id=task_id,
            )
        )

        try:
            planned, raw_plan, spent = plan_checkpoint(
                container,
                options=options,
                spec=spec,
                protected=policy.protected,
                elevate_on=policy.elevate_on,
                agent=agent,
                emit=emit,
            )
        except artifacts.ScopeProposed as proposed:
            # The attempt ends here: no IMPLEMENT turn, no gate suite, no
            # REVIEW — a proposal is the end of the attempt, not a note it
            # carries while continuing (SA-0018).
            proposal = proposed.proposal
            # Host-added, never the model's: the writeback this touches set
            # feeds is a commit to the spec file itself, and that commit would
            # otherwise fail its own `scope` gate (§5.2, DESIGN.md:618).
            # ponytail: since SA-0024 this is no longer sufficient where the
            # spec directory is `protected` — the deny lists do not consult
            # `touches`, so widening it no longer clears the writeback
            # (BACKLOG item 31). Latent: nothing writes it back yet.
            # A superset of the declared `touches`, never a replacement: the
            # prompt asks for paths "inside or outside" them, and a prompt is
            # not the boundary (SA-0018 review).
            final_touches = sorted(
                {
                    *spec.touches,
                    *proposal.proposed_touches,
                    _spec_path(spec.spec_id, repo),
                }
            )
            (task_dir / "scope_proposal.json").write_text(
                json.dumps(
                    {
                        "proposed_touches": final_touches,
                        "root_cause": proposal.root_cause,
                        "raw": proposed.raw,
                        # `plan.json` is the raw block verbatim, so its watch
                        # line's sha256 is re-derivable with `sha256sum`. This
                        # is an envelope, so it has to carry the hash itself.
                        "sha256": artifacts.hash_artifact(proposed.raw),
                    },
                    indent=2,
                )
            )
            _phase_start(
                "IMPLEMENT",
                "SCOPE_REVIEW",
                f"proposed {final_touches}, "
                f"sha256 {artifacts.hash_artifact(proposed.raw)[:12]}, "
                f"${proposed.spent_usd:.2f} spent",
            )
            ledger.set_task_state(task_id, "SCOPE_REVIEW")
            ledger.finish_run(run_id, "COMPLETE")
            return CellOutcome(
                state="SCOPE_REVIEW",
                task_id=task_id,
                run_id=run_id,
                task_dir=task_dir,
                spent_usd=proposed.spent_usd,
                effective_risk=latest.effective_risk,
                advisory_gates=sorted(latest.advisory_gates),
                proposed_touches=final_touches,
            )
        except artifacts.PlanRejected as rejected:
            emit(
                Terminal(
                    timestamp=time.time(),
                    spec_id=spec.spec_id,
                    reason="plan_rejected",
                    spent_usd_est=rejected.spent_usd,
                    detail=str(rejected),
                )
            )
            ledger.set_task_state(task_id, "PLAN_REJECTED")
            ledger.finish_run(run_id, "COMPLETE")
            return CellOutcome(
                state="PLAN_REJECTED",
                task_id=task_id,
                run_id=run_id,
                task_dir=task_dir,
                spent_usd=rejected.spent_usd,
                # The plan's own forecast tier when `judge_estimate` rejected
                # it, the baseline's tier for every other rejection.
                effective_risk=(
                    rejected.risk_tier
                    if rejected.risk_tier is not None
                    else latest.effective_risk
                ),
                advisory_gates=sorted(latest.advisory_gates),
            )
        except implement.AgentFailed as failed:
            # No plan and no commits, but a live cell: the earned state, not the
            # ORPHANED that a crash out of `run_one_cell` would stamp (§4.5).
            plan_cost = failed.attempt.cost_usd_est if failed.attempt else 0.0
            _phase_start(
                "IMPLEMENT",
                "PLAN",
                f"the session failed, ${plan_cost:.2f} spent — {failed}",
            )
            ledger.set_task_state(task_id, "NOT_IMPLEMENTED")
            ledger.finish_run(run_id, "COMPLETE")
            return CellOutcome(
                state="NOT_IMPLEMENTED",
                task_id=task_id,
                run_id=run_id,
                task_dir=task_dir,
                # Measured, so it is reported: a supervisor summing `spent_usd`
                # across tasks otherwise books every plan failure at zero.
                spent_usd=plan_cost,
                effective_risk=latest.effective_risk,
                advisory_gates=sorted(latest.advisory_gates),
            )

        # Extracted and hashed the moment it is produced, and never read from
        # /work again: a plan the implementer can rewrite is a claim (§5.3).
        (task_dir / "plan.json").write_text(raw_plan)
        _phase_start(
            "IMPLEMENT",
            "PLAN",
            f"accepted, sha256 {artifacts.hash_artifact(raw_plan)[:12]}",
        )

        # Doneness is measured from here, not from base_sha: the plan turn holds
        # Write/Edit/Bash and only a prompt telling it not to commit, so a plan
        # turn that commits would otherwise satisfy the implement turn (§4.3).
        planned_sha = worktree.head_sha(container)

        session_id = require_session(planned.session_id)
        # The *previous turn's* cost, not the running total: what a crashed
        # turn reporting zero falls back to is one turn's figure (§4.1).
        # Summing is correct — measured, not assumed: a resumed turn reports its
        # own cost, not the session's ($0.00396 fresh, then $0.00199 on resume
        # of the same session_id; cumulative would never fall).
        last_cost = planned.cost_usd_est

        def _over_budget() -> bool:
            """The host-side ceiling. `max_budget_usd` is per turn and is
            evaluated inside the cell; this is the sum the supervisor holds
            against the task's own budget (§4.3)."""
            if spent < spec.budget_usd:
                return False
            emit(
                Budget(
                    timestamp=time.time(),
                    spec_id=spec.spec_id,
                    ceiling="budget_usd",
                    value=spent,
                    limit=spec.budget_usd,
                )
            )
            return True

        if _over_budget():
            # Same state as four red attempts, and only the watch line above
            # tells them apart — acceptable while v0.5 is attended (§3.3).
            ledger.set_task_state(task_id, "EXHAUSTED")
            ledger.finish_run(run_id, "COMPLETE")
            return CellOutcome(
                state="EXHAUSTED",
                task_id=task_id,
                run_id=run_id,
                task_dir=task_dir,
                spent_usd=spent,
                effective_risk=latest.effective_risk,
                advisory_gates=sorted(latest.advisory_gates),
            )

        implement_failed = False
        try:
            implemented = agent(
                container,
                prompt=implement.IMPLEMENT_PROMPT,
                options=options,
                resume=session_id,
                emit=emit,
                last_cost_usd=last_cost,
            )
        except implement.AgentFailed as failed:
            # A bound firing, or a crash, must never discard committed work
            # (§4.3) — so the failure is recorded and the worktree is measured
            # below rather than the attempt being thrown away here.
            _phase_start("IMPLEMENT", "IMPLEMENT", f"the session failed — {failed}")
            implemented = _failed_turn(failed, session_id)
            # `run_agent`'s own predicate, kept rather than re-derived from the
            # result: `is_error` is only one of the four things it ORs, so a
            # turn that crashed after emitting a clean result reads as success.
            implement_failed = True
        session_id = require_session(implemented.session_id or session_id)
        spent += implemented.cost_usd_est
        last_cost = implemented.cost_usd_est

        # Doneness is measured, never reported (§4.3): an attempt that produced
        # no commits failed, whatever the transcript says.
        commits = worktree.commits_ahead(container, planned_sha)
        emit(
            Attempt(
                timestamp=time.time(),
                spec_id=spec.spec_id,
                phase="IMPLEMENT",
                attempt=1,
                commits=commits,
                spent_usd_est=spent,
            )
        )

        # Decided once, from the implement turn's own attempt: SA-0028's turn
        # ceiling, or, since SA-0126, the wall clock.
        turn_ceiling_cut = cut_off_at_turn_ceiling(implemented)
        wall_cut = implemented.bound == "wall"
        cut_by_bound = turn_ceiling_cut or wall_cut
        bound_word = "the turn ceiling" if turn_ceiling_cut else "the wall clock"

        if commits == 0 and cut_by_bound:
            # The agent did not decide it was finished — a bound cut it off
            # with the work still in /work, uncommitted, about to die with
            # the volume at teardown (SA-0025: $14.61, 141 turns, zero
            # commits, $5.39 unspent). One more turn, resumed on the same
            # session, asking only for a commit. The budget ceiling is
            # checked *before* it is spent, never after (§4.3).
            if _over_budget():
                emit(
                    Terminal(
                        timestamp=time.time(),
                        spec_id=spec.spec_id,
                        reason="cut_off_no_salvage_room",
                        spent_usd_est=spent,
                        detail=(
                            f"${spent:.2f} of ${spec.budget_usd:.2f} — "
                            f"cut off at {bound_word}"
                        ),
                    )
                )
            else:
                _phase_start(
                    "IMPLEMENT",
                    "IMPLEMENT",
                    f"cut off at {bound_word} with nothing committed — "
                    "spending one turn to salvage it",
                )
                # Clamped: a spec with a `max_turns` below the salvage
                # constant would otherwise get a salvage turn with a *higher*
                # ceiling than the implement turn it is salvaging.
                salvage_turns = min(implement.SALVAGE_MAX_TURNS, spec.max_turns)
                salvage_options = implement.agent_options(
                    system_prompt=system_prompt,
                    cwd=worktree.WORKTREE_MOUNT,
                    max_turns=salvage_turns,
                    budget_usd=spec.budget_usd,
                )
                salvage_note = "the salvage turn committed nothing"
                try:
                    salvaged = agent(
                        container,
                        prompt=implement.SALVAGE_PROMPT,
                        options=salvage_options,
                        resume=session_id,
                        emit=emit,
                        # Scaled, not carried over: the fallback charges a
                        # crashed turn the previous turn's figure, and these
                        # two ceilings differ by construction. Unscaled, a
                        # crashed 5-turn salvage is billed a 120-turn
                        # implement turn — $11.68 for a `git commit`, enough
                        # to book EXHAUSTED on a task the salvage just saved.
                        last_cost_usd=last_cost * salvage_turns / spec.max_turns,
                    )
                except implement.AgentFailed as failed:
                    # The same rule as the implement turn itself (§4.3): a
                    # bound firing on the salvage turn must not discard
                    # whatever it managed to commit before it was cut.
                    _phase_start(
                        "IMPLEMENT", "SALVAGE", f"the session failed — {failed}"
                    )
                    salvaged = _failed_turn(failed, session_id)
                    # Truncated: this reaches the PR body through
                    # `commit_subjects`, and `str(failed)` carries in-cell stderr.
                    salvage_note = str(failed)[:120]
                session_id = require_session(salvaged.session_id or session_id)
                spent += salvaged.cost_usd_est
                # `last_cost` deliberately keeps the *implement* turn's figure.
                # It anchors the crash fallback of the next turn, which runs on
                # the full ceiling; the salvage turn's own cost is small by
                # construction. Carrying it forward would undo the scaling above
                # in the other direction — billing a crashed 120-turn repair
                # turn the price of a `git commit`, which is §4.1's budget that
                # silently stops counting, one hop downstream.
                # Unconditional, not only on the failure branch: a salvage turn
                # that ends cleanly having committed nothing — a hook rejected
                # the commit, say — loses exactly the work it was spent to
                # save. Doneness is measured, never reported (§4.3), so its
                # clean exit buys it no more trust than a bound firing. Same
                # host checkpoint the repair loop takes below.
                try:
                    if worktree.dirty_paths(container):
                        worktree.commit_dirty(
                            container, f"checkpoint: host-committed — {salvage_note}"
                        )
                        _phase_start(
                            "IMPLEMENT",
                            "SALVAGE",
                            "uncommitted work checkpointed by the host",
                        )
                except runtime.CellRuntimeError as broke:
                    # `commit_dirty` raises on any non-zero git exit, so a hook
                    # refusing the commit arrives here as a runtime error. It is
                    # the repo's code being wrong, not the runtime breaking:
                    # letting it out books exit 2, charged to nobody, on a task
                    # that earned `ORPHANED` or `NOT_IMPLEMENTED` (error ≠
                    # fail). The `commits_ahead` re-measure below still decides.
                    _phase_start(
                        "IMPLEMENT", "SALVAGE", f"the host checkpoint failed — {broke}"
                    )
                # Same measurement point as before: the plan turn's head, not
                # base_sha and not where the salvage turn itself started.
                commits = worktree.commits_ahead(container, planned_sha)
                if commits:
                    _phase_start(
                        "IMPLEMENT",
                        "SALVAGE",
                        f"recovered {commits} commit(s), ${spent:.2f} spent",
                    )
                else:
                    emit(
                        Terminal(
                            timestamp=time.time(),
                            spec_id=spec.spec_id,
                            reason="cut_off_salvage_failed",
                            spent_usd_est=spent,
                        )
                    )
        elif commits == 0 and implement_failed:
            # Neither cut off nor finished: an idle bound, a provider wall, a
            # crash. Saying "finished" here would collapse a third fact into
            # the two this spec exists to separate, and a retry is warranted
            # for this one.
            emit(
                Terminal(
                    timestamp=time.time(),
                    spec_id=spec.spec_id,
                    reason="ended_without_finishing",
                    spent_usd_est=spent,
                    subtype=implemented.subtype,
                    terminal_reason=implemented.terminal_reason,
                )
            )
        elif commits == 0:
            # The agent finished the turn on its own and produced nothing —
            # a different fact from being cut off, and not one more turn
            # answers (§4.3: doneness is measured, never reported, and never
            # argued with).
            emit(
                Terminal(
                    timestamp=time.time(),
                    spec_id=spec.spec_id,
                    reason="finished_empty",
                    spent_usd_est=spent,
                )
            )

        if commits == 0:
            # SA-0126: a bound's first cut at a `spec_sha` re-queues as
            # `ORPHANED`. An earlier such task settles this one instead.
            state = "NOT_IMPLEMENTED"
            if cut_by_bound:
                earlier = previous_cut_orphan(ledger, repo_id, spec, task_id)
                if earlier is not None:
                    _phase_start(
                        "IMPLEMENT",
                        "IMPLEMENT",
                        f"cut again at this spec_sha — task {earlier}",
                    )
                else:
                    state = "ORPHANED"
            ledger.set_task_state(task_id, state)
            ledger.finish_run(run_id, "COMPLETE")
            return CellOutcome(
                state=state,
                task_id=task_id,
                run_id=run_id,
                task_dir=task_dir,
                spent_usd=spent,
                effective_risk=latest.effective_risk,
                advisory_gates=sorted(latest.advisory_gates),
            )

        def _judge(attempt: int | None = None) -> SuiteComparison:
            nonlocal latest
            comparison = suite.against(tree, baseline)
            # Kept for the `CellOutcome`'s own gates, effective_risk and
            # advisory_gates. Not for the critic: its table comes from the
            # gate-only cell now, never the implementer's own run.
            latest = comparison.run
            # The turn that just closed, which is the repair turn under §5.4's
            # loop — the join the no-progress rule and §8 need, and the whole
            # point of not collapsing every attempt onto the task. Under §5.6
            # it is the rebuttal's *extraction* turn rather than the turn that
            # moved HEAD, because `run_rebuttal` buys two; that re-run decides
            # EXHAUSTED-or-not and is not a term in either query.
            attempt_id = ledger.attempts(task_id)[-1]["attempt_id"]
            for result in latest.results:
                ledger.record_gate_result(result, attempt_id=attempt_id)
            # `None` unless `repair_loop` is calling: `_rebut_gates` calls
            # `_judge()` bare, since `against: "rebuttal"` has no owner yet (item 160).
            if attempt is not None:
                # `None`, not a measured `0`, for an aborted/drifted suite or
                # a skipped/errored/advisory gate: none of those ran a count.
                counted = (
                    None
                    if comparison.aborted or comparison.drift
                    else Counter(nf.gate for nf in comparison.new_failures)
                )
                for result in latest.results:
                    count = None
                    if (
                        counted is not None
                        and result.status not in ("skip", "error")
                        and result.gate not in latest.advisory_gates
                    ):
                        count = counted.get(result.gate, 0)
                    emit(
                        GateResultEvent(
                            timestamp=time.time(),
                            spec_id=spec.spec_id,
                            gate=result.gate,
                            status=result.status,
                            against="attempt",
                            attempt=attempt,
                            new_failures=count,
                        )
                    )
            return comparison

        def _repair(new: Sequence[NewFailure]) -> str | None:
            nonlocal session_id, spent, last_cost
            if _over_budget():
                return "EXHAUSTED"
            ledger.set_task_state(task_id, "REPAIRING")
            try:
                repaired = agent(
                    container,
                    prompt=implement.repair_prompt(new),
                    options=options,
                    resume=session_id,
                    emit=emit,
                    last_cost_usd=last_cost,
                )
            except implement.AgentFailed as failed:
                # The same rule as the implement turn (§4.3): a bound firing
                # mid-loop must not discard work that is already committed and
                # a suite that may be nearly green. The next gate suite measures.
                _phase_start("REPAIR", "REPAIR", f"the session failed — {failed}")
                repaired = _failed_turn(failed, session_id)
                # "Commit as you go" is a prompt, and a prompt is never the
                # boundary (§0). Real edits the turn never got to commit do not
                # survive teardown otherwise — checkpointed here so the next
                # attempt builds on them instead of redoing the same ground.
                try:
                    if worktree.dirty_paths(container):
                        worktree.commit_dirty(
                            container, f"checkpoint: host-committed — {failed}"
                        )
                        _phase_start(
                            "REPAIR",
                            "REPAIR",
                            "uncommitted work checkpointed by the host",
                        )
                except runtime.CellRuntimeError as broke:
                    # A hook refusing the commit is the repo's code, not the
                    # runtime (error ≠ fail) — the salvage checkpoint's rule.
                    _phase_start(
                        "REPAIR", "REPAIR", f"the host checkpoint failed — {broke}"
                    )
            session_id = require_session(repaired.session_id or session_id)
            spent += repaired.cost_usd_est
            last_cost = repaired.cost_usd_est
            return None

        outcome, attempts, new_failures = repair_loop(
            judge=_judge,
            max_attempts=spec.max_attempts,
            repair=_repair,
            spec_id=spec.spec_id,
            emit=emit,
        )

        # Extraction turn, the way `plan.json` already is one (§5.3): the
        # implementer's own account of something it saw but was told not to
        # touch, taken at the cheapest moment there will ever be — right after
        # its last repair attempt, on its own session, before REVIEW forks a
        # critic's (backlog items 71/75/80, SA-0058/SA-0061/
        # SA-0062). Runs whatever `outcome` repair_loop handed back — READY_
        # FOR_REVIEW, EXHAUSTED or GATE_ERROR alike, since "implementation
        # just stopped" is the fact this is timed against, not which gate
        # result followed.
        #
        # Asked only when this attempt actually had something it could have
        # been denied against — a declared `forbidden` list or a repo-wide
        # `protected` one (exactly the two lists SA-0058/61/62 kept asking an
        # agent to "file a finding" about with nowhere to put it). A spec with
        # neither has nothing this channel was built to catch, and a turn
        # asked of every task regardless would spend real money narrating
        # "nothing to report" on the common case. Skipped once the task is
        # already over budget either way: cheap is not free (§4.3).
        notes = ""
        notes_sha256 = ""
        notes_worth_asking = bool(spec.forbidden) or bool(policy.protected)
        if notes_worth_asking and not _over_budget():
            try:
                noted = agent(
                    container,
                    prompt=artifacts.NOTES_PROMPT,
                    options=options,
                    resume=session_id,
                    emit=emit,
                    last_cost_usd=last_cost,
                )
            except implement.AgentFailed as failed:
                _phase_start(
                    "IMPLEMENT", "IMPLEMENT", f"the notes turn failed — {failed}"
                )
                noted = _failed_turn(failed, session_id)
            session_id = require_session(noted.session_id or session_id)
            spent += noted.cost_usd_est
            last_cost = noted.cost_usd_est
            notes = artifacts.extract_notes(noted.text)
            if notes:
                notes_sha256 = artifacts.hash_artifact(notes)
                (task_dir / "notes.json").write_text(
                    json.dumps({"raw": notes, "sha256": notes_sha256}, indent=2)
                )
                _phase_start(
                    "IMPLEMENT",
                    "IMPLEMENT",
                    f"notes recorded, sha256 {notes_sha256[:12]}",
                )

        # Pre-bound, not left to the branch below: repair_loop can hand back
        # EXHAUSTED or GATE_ERROR directly, skipping REVIEW entirely, and the
        # outcome at the bottom of this function must still be constructible.
        reviews: list[review.LensReview] = []
        # Same reason: REBUT reads this to attach a verdict to the row REVIEW
        # wrote, and the branch that fills it is the branch above.
        recorded: dict[int, int] = {}
        # Bound here, not in the branch below: REVIEW fills it and REBUT reads
        # it, and neither should depend on the other's control flow.
        reviewed_diff = ""
        # REVIEW binds it and REBUT reads it, like the three above.
        critic_env: dict[str, str] = {}
        # One entry per criterion (backlog item b-2750d5), empty for a spec
        # declaring none. Bound early for the same reason as `reviews`.
        criterion_probes: list[dict] = []

        if outcome == "READY_FOR_REVIEW":
            ledger.set_task_state(task_id, "REVIEWING")

            # Read once: REVIEW's and REBUT's critic cells share this env.
            proxy_ip = runtime.container_ip(proxy.PROXY_NAME)
            if proxy_ip is None:
                # Infrastructure, not a task outcome: the proxy this task
                # already started is unreadable, which `cell_env` cannot turn
                # into a `str`.
                raise runtime.CellRuntimeError(
                    "the critic cell could not read the proxy's address"
                )
            critic_env = cell_env(proxy_ip, policy.thread_env)

            def _critic_teardown(step: str, ok: bool, detail: str) -> None:
                emit(
                    Teardown(
                        timestamp=time.time(),
                        spec_id=spec.spec_id,
                        step=step,
                        ok=ok,
                        detail=detail,
                    )
                )

            # The bytes the patch export leaves behind for the operator — fed
            # to the Gate-only cell's own git and the critic cell's, never re-read
            # from `/work` again.
            patch_to_review = worktree.export_patch(container, spec.tree_base)

            # The table every lens is shown, computed in a cell of its own
            # (CONTEXT.md §5, backlog item 118): the implementer had root over
            # its own toolchain, so a table built from `latest` is a claim the
            # agent could have forged, and a lens told the gates are green
            # reads the diff differently. Judged against this run's own
            # pre-turn baseline — taken before the agent had a single turn —
            # never a second, freshly-taken one: that baseline is not a
            # forged-toolchain input in the sense this cell exists to close.
            try:
                gate_comparison = _gate_cell_suite(
                    spec=spec,
                    repo=repo,
                    mirror=mirror,
                    gates_dir=gates_dir,
                    thread_env=policy.thread_env,
                    patch=patch_to_review,
                    suite=suite,
                    baseline=baseline,
                    created=created,
                    note=_critic_teardown,
                )
            except CriticPatchRejected as rejected:
                # The same patch the critic cell would otherwise have been the
                # first to refuse — applying it here first only moves which
                # cell notices. The agent's problem either way: `EXHAUSTED`.
                gate_comparison = None
                outcome = "EXHAUSTED"
                _phase_start(
                    "REVIEW",
                    "REVIEW",
                    f"the exported patch did not apply in the Gate-only cell — {rejected}",
                )
            except CriticPatchUnrepresentable as binary:
                gate_comparison = None
                outcome = "GATE_ERROR"
                _phase_start(
                    "REVIEW",
                    "REVIEW",
                    "the exported patch carries a binary change the export "
                    f"cannot carry — {binary}",
                )

            # The Gate-only cell's results, before any lens and before the
            # `GATE_ERROR` branch; bare, like `baseline.json`'s write.
            if gate_comparison is not None:
                (task_dir / "lens-gates.json").write_text(
                    json.dumps(
                        [r.model_dump() for r in gate_comparison.run.results],
                        indent=2,
                    )
                )

            if gate_comparison is not None and (
                gate_comparison.aborted or gate_comparison.drift
            ):
                # error != fail (§5.4): the gate itself broke, or the two
                # suites disagree on shape — never a task's own new failure,
                # and never READY_FOR_REVIEW. The same read `_judge`'s own
                # callers give an aborted or drifted comparison. No lens runs.
                outcome = "GATE_ERROR"
                what = "errored" if gate_comparison.aborted else "drifted"
                _phase_start(
                    "REVIEW",
                    "REVIEW",
                    f"the suite at the exported patch {what} — "
                    + "; ".join(gate_comparison.aborted or gate_comparison.drift),
                )
            elif gate_comparison is not None:
                # One ceiling for every lens and every criterion-probe
                # session alike (backlog item b-2750d5), computed once.
                probe_budget = critic_budget(spec.budget_usd, spent)
                try:
                    with critic_cell(
                        spec=spec,
                        repo=repo,
                        mirror=mirror,
                        network=network,
                        env=critic_env,
                        gates_dir=gates_dir,
                        patch=patch_to_review,
                        created=created,
                        note=_critic_teardown,
                    ) as critic_container:
                        # Read from the critic cell's own tree, not the
                        # implementer's — the diff it judges is the patch that
                        # ships, applied by a git the implementer never
                        # touched (CONTEXT.md §5, backlog item 118). Bound to
                        # a name so REBUT is handed this one, not a second
                        # export of it (`SA-0091`).
                        reviewed_diff = worktree.export_patch(
                            critic_container, spec.tree_base
                        )
                        reviews = review.run_review(
                            critic_container,
                            diff=reviewed_diff,
                            read_head=lambda path: worktree.read_at_head(
                                critic_container, path
                            ),
                            # A witnessed spec's claims live only in frontmatter
                            # (§3.2); append them so the critic sees what a
                            # markdown spec already gives.
                            spec_body=spec.body
                            + context.criteria_section(spec.acceptance),
                            # The Gate-only cell's own comparison, never `latest` —
                            # the implementer's last suite is exactly the input
                            # this cell exists to stop feeding the critic.
                            gates=review.gate_summary(
                                gate_comparison.run.results,
                                sorted(gate_comparison.run.advisory_gates),
                            ),
                            context_md=context_md,
                            claude_md=claude_md,
                            prompts_dir=context.PROMPTS_DIR,
                            max_turns=spec.max_turns,
                            budget_usd=probe_budget,
                            agent=agent,
                            spec_id=spec.spec_id,
                            emit=emit,
                        )
                        # One fresh session per criterion, asked before this
                        # cell is torn down and never after (item b-2750d5).
                        criterion_probes = review.run_criterion_probes(
                            critic_container,
                            acceptance=spec.acceptance,
                            diff=reviewed_diff,
                            context_md=context_md,
                            claude_md=claude_md,
                            prompts_dir=context.PROMPTS_DIR,
                            max_turns=spec.max_turns,
                            budget_usd=probe_budget,
                            agent=agent,
                            spec_id=spec.spec_id,
                            emit=emit,
                        )
                except CriticPatchRejected as rejected:
                    outcome = "EXHAUSTED"
                    _phase_start(
                        "REVIEW",
                        "REVIEW",
                        "the exported patch did not apply in the critic cell — "
                        f"{rejected}",
                    )
                except CriticPatchUnrepresentable as binary:
                    outcome = "GATE_ERROR"
                    _phase_start(
                        "REVIEW",
                        "REVIEW",
                        "the exported patch carries a binary change the export "
                        f"cannot carry — {binary}",
                    )
                else:
                    # Backlog item 117: every probed adequacy finding's own
                    # verdict, decided before the ledger write below.
                    probed = _probe_adequacy(
                        spec=spec,
                        repo=repo,
                        mirror=mirror,
                        gates_dir=gates_dir,
                        thread_env=policy.thread_env,
                        test_paths=policy.integrity.test_paths,
                        gates=gates,
                        patch=patch_to_review,
                        reviews=reviews,
                        created=created,
                        note=_critic_teardown,
                    )
                    if probed:
                        (task_dir / "probes.json").write_text(
                            json.dumps(probed, indent=2)
                        )
                        _phase_start(
                            "REVIEW",
                            "REVIEW",
                            review.describe_probes(probed),
                        )

                    # Every named edit, applied and asked (item b-2750d5),
                    # before the record below is written.
                    _apply_criterion_probes(
                        spec=spec,
                        repo=repo,
                        mirror=mirror,
                        gates_dir=gates_dir,
                        thread_env=policy.thread_env,
                        test_paths=policy.integrity.test_paths,
                        gates=gates,
                        patch=patch_to_review,
                        entries=criterion_probes,
                        diff=reviewed_diff,
                        gate_comparison=gate_comparison,
                        reviews=reviews,
                        created=created,
                        note=_critic_teardown,
                    )

                    # A spec declaring no criterion bought no session above
                    # and writes no record here (backlog item b-2750d5).
                    if criterion_probes:
                        (task_dir / "criterion-probes.json").write_text(
                            json.dumps(criterion_probes, indent=2)
                        )
                        _phase_start(
                            "REVIEW",
                            "REVIEW",
                            review.describe_criterion_probes(criterion_probes),
                        )

                    # Deliberately not gated on the host ceiling: a green diff
                    # nobody reviewed is exactly the product Appendix K says
                    # means nothing.
                    spent += sum(r.cost_usd for r in reviews) + sum(
                        e["cost_usd"] for e in criterion_probes
                    )
                    (task_dir / "findings.json").write_text(
                        json.dumps([r.as_dict() for r in reviews], indent=2)
                    )
                    # Keyed by identity rather than re-filtered:
                    # `anchored_blockers` is the single selection rule REBUT's
                    # callers share, and a second copy of it here would
                    # silently renumber the blockers (§5.5).
                    reported = [f for r in reviews for f in r.findings]
                    recorded = dict(
                        zip(
                            map(id, reported),
                            ledger.record_findings(task_id, reported),
                            strict=True,
                        )
                    )
                    outcome, why = review.review_state(reviews)
                    _phase_start("REVIEW", "REVIEW", why)

        # Same reasoning as `reviews` above: bound only inside the REBUTTING
        # branch below, and READY_FOR_REVIEW's own outcomes skip it entirely.
        rebut_result: rebut.RebutResult | None = None

        if outcome == "REBUTTING":
            ledger.set_task_state(task_id, "REBUTTING")
            blockers = review.anchored_blockers(reviews)
            if _over_budget():
                outcome = "EXHAUSTED"
            else:
                before = worktree.head_sha(container)

                def _rebut_gates() -> str | None:
                    """§5.6: red after the rebuttal is EXHAUSTED, and REBUT does
                    not re-enter the repair loop. An errored gate is still
                    infrastructure and still not charged to the task (§5.4)."""
                    comparison = _judge()
                    # The suite after the loop's last, so the gate count
                    # continues rather than restarting at 1 (item 47).
                    emit(
                        attempt_event(
                            comparison,
                            spec_id=spec.spec_id,
                            phase="REBUT",
                            attempt=attempts + 1,
                        )
                    )
                    if comparison.aborted or comparison.drift:
                        return "GATE_ERROR"
                    return "EXHAUSTED" if comparison.new_failures else None

                with contextlib.ExitStack() as critic_stack:

                    def _rebut_critic_container() -> str:
                        """Called only once `run_rebut` has a green re-run to
                        show a lens, never on an early return. Seeded from
                        the implementer's *current* HEAD, so a rebuttal fix
                        reaches the critic's tree (CONTEXT.md §5, item 118).
                        `critic_stack` closes when `run_rebut` returns below,
                        tearing the cell down the way REVIEW's is.
                        """
                        rebuttal_patch = worktree.export_patch(
                            container, spec.tree_base
                        )
                        return critic_stack.enter_context(
                            critic_cell(
                                spec=spec,
                                repo=repo,
                                mirror=mirror,
                                network=network,
                                env=critic_env,
                                gates_dir=gates_dir,
                                patch=rebuttal_patch,
                                created=created,
                                note=_critic_teardown,
                            )
                        )

                    result = rebut.run_rebut(
                        container,
                        blockers=blockers,
                        options=options,
                        session_id=session_id,
                        spec_body=spec.body + context.criteria_section(spec.acceptance),
                        context_md=context_md,
                        claude_md=claude_md,
                        prompts_dir=context.PROMPTS_DIR,
                        max_turns=spec.max_turns,
                        budget_usd=critic_budget(spec.budget_usd, spent),
                        # Measured, never reported (§4.3): from the head the
                        # rebuttal started at, so the implement turn's own
                        # commits cannot satisfy it.
                        head_moved=lambda: (
                            worktree.commits_ahead(container, before) > 0
                        ),
                        rerun_gates=_rebut_gates,
                        critic_container=_rebut_critic_container,
                        # Read from the critic cell's own tree, never the
                        # implementer's own `.git` (CONTEXT.md §5).
                        diff=lambda critic: worktree.export_patch(
                            critic, spec.tree_base
                        ),
                        agent=agent,
                        spec_id=spec.spec_id,
                        # The exact diff REVIEW's lenses were shown.
                        reviewed_diff=reviewed_diff,
                        emit=emit,
                        last_cost_usd=last_cost,
                    )
                rebut_result = result
                spent += result.cost_usd
                session_id = result.rebuttal.session_id or session_id
                (task_dir / "rebuttal.json").write_text(
                    json.dumps(result.as_dict(blockers), indent=2)
                )
                # The critic's verdict and the implementer's argument, onto the
                # rows REVIEW wrote. Both are keyed by the blocker's number,
                # which is its position in `blockers` counted from 1 (§5.6).
                # Nothing validates the rebuttal turn's numbering the way
                # `run_verdict` validates a verdict set, so it is validated
                # here: a number nobody asked about is dropped, and
                # `first_answers` keeps the one that stands. Silently letting
                # a duplicate win leaves another blocker reading as unanswered.
                # `action` rides along because "fixed" and "argued" are the
                # difference the critic-ROI query is asking about (§4.6).
                argued = {
                    n: f"{r.action}: {r.argument}"
                    for n, r in rebut.first_answers(result.rebuttal).items()
                    if 1 <= n <= len(blockers)
                }
                judged = {
                    v.finding: v.verdict
                    for lens in result.verdicts
                    for v in lens.verdicts
                }
                for n, finding in enumerate(blockers, 1):
                    ledger.record_rebuttal(
                        recorded[id(finding)],
                        verdict=judged.get(n),
                        rebuttal=argued.get(n),
                    )
                outcome, why = result.state, result.why
                _phase_start("REBUT", "REBUT", why)

        # The task's own outcome — `events.FAMILIES`' two `TaskOutcome` rows.
        emit(
            TaskOutcome(
                timestamp=time.time(),
                spec_id=spec.spec_id,
                outcome=outcome,
                spent_usd_est=spent,
                session_id=session_id,
            )
        )
        ledger.set_task_state(task_id, outcome)
        ledger.finish_run(run_id, "COMPLETE")
        return CellOutcome(
            state=outcome,
            task_id=task_id,
            run_id=run_id,
            task_dir=task_dir,
            spent_usd=spent,
            attempts=attempts,
            gates=latest.results,
            new_failures=new_failures,
            reviews=reviews,
            rebut_result=rebut_result,
            effective_risk=latest.effective_risk,
            advisory_gates=sorted(latest.advisory_gates),
            notes=notes,
            notes_sha256=notes_sha256,
        )
    except RateLimited as stopped:
        # Read back, not reported: `spent` loses the walled turn — the raise
        # comes from outside it, past the `spent +=` — and loses the whole
        # tally when the window closed inside plan_checkpoint's frame. Every
        # turn recorded its own attempt before the rate limit was raised, so
        # the roll-up here is the figure that survived both.
        spent_read_back = ledger.task_spend(task_id)
        resets_at, resets_at_unreadable = _resets_at_fields(stopped.resets_at)
        emit(
            TaskOutcome(
                timestamp=time.time(),
                spec_id=spec.spec_id,
                outcome="RATE_LIMITED",
                spent_usd_est=spent_read_back,
                resets_at=resets_at,
                resets_at_unreadable=resets_at_unreadable,
            )
        )
        ledger.set_task_state(task_id, "RATE_LIMITED")
        ledger.finish_run(run_id, "COMPLETE")
        return CellOutcome(
            state="RATE_LIMITED",
            task_id=task_id,
            run_id=run_id,
            task_dir=task_dir,
            spent_usd=spent_read_back,
            effective_risk=latest.effective_risk,
            advisory_gates=sorted(latest.advisory_gates),
        )
    except BaseException:
        # A run row left open is a run that reads as still going. Preflight
        # raising is the path an operator hits first, so it is the one most
        # worth closing honestly — ABORTED, not COMPLETE. BaseException, not
        # Exception: this is the attended driver, and Ctrl-C is the likeliest
        # abort of all. The exception is re-raised untouched.
        ledger.finish_run(run_id, "ABORTED")
        # The cell died, so the task is ORPHANED (§4.5) — left QUEUED it reads
        # in `queue_lines` as never started, which is the founding defect.
        ledger.set_task_state(task_id, "ORPHANED")
        raise
    finally:

        def _teardown(step: str, ok: bool = True, detail: str = "") -> None:
            emit(
                Teardown(
                    timestamp=time.time(),
                    spec_id=spec.spec_id,
                    step=step,
                    ok=ok,
                    detail=detail,
                )
            )

        _teardown("start")
        # Before `cell_down`, on every path the exception one included: the
        # export execs inside the cell, so it must precede the container's
        # removal as well as the volume's. An EXHAUSTED run with commits is
        # worth reading too.
        if container in created:
            exported["head_sha"], exported["subjects"] = export_patch(
                container, spec, task_dir, emit
            )
        cell_down(
            network=network,
            volume=volume,
            state=state,
            container=container,
            created=created,
            note=_teardown,
        )
