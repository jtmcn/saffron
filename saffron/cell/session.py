"""One cell, start to finish (DESIGN.md §5.1–§5.4).

v0.5 only: no scheduler, no budget pool, no PR. The operator watches this run.
`ponytail:` this is v0.5's supervisor. v1 replaces it with supervisor.py plus
scheduler.py, and this file goes the way replay.py went.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from saffron.gates.baseline import (
    NewFailure,
    is_no_progress,
    subtract_baseline,
    suite_drift,
)
from saffron.gates.contract import GateResult
from saffron.phases import implement, rebut, review
from saffron.phases.implement import AttemptResult

if TYPE_CHECKING:
    from saffron.ledger import Ledger

# Where this file lives inside the Saffron tree, used to locate CONTEXT.md and
# the prompt templates — Saffron's own files, never the target repo's (§5.3).
_SAFFRON_ROOT = Path(__file__).resolve().parents[2]
_SAFFRON_PKG = Path(__file__).resolve().parents[1]

# §4.3's wall clock, per turn, set here rather than inherited: this is the bound
# the operator sits through, so it belongs where the task is driven. Fifteen
# minutes is long enough for a turn that runs a real gate suite between tool
# calls and short enough to watch; the idle bound (runtime.IDLE_TIMEOUT_S) is
# what catches a stall sooner, and this only catches a turn that never stops.
TURN_TIMEOUT_S = 900.0

# REVIEW is deliberately not gated on the spend ceiling — a green diff nobody
# reviewed is not a product — so its sessions are capped at what is left rather
# than at the whole task budget, which is how a $12 task bills $40. The floor is
# what keeps "not gated" true when nothing is left: below it a lens would be
# refused for having no room, and the task would reach the operator unreviewed.
# REBUT *is* gated (`_over_budget` before the rebuttal turn): by then the
# findings are written and the operator has something to read either way.
REVIEW_FLOOR_USD = 2.0


def critic_budget(budget_usd: float, spent: float) -> float:
    """The per-session cap for one critic turn: the remainder, never zero."""
    return max(budget_usd - spent, REVIEW_FLOOR_USD)


class CellSessionError(RuntimeError):
    """The session cannot go on — not the agent's failure, the driver's."""


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
    budget_usd: float = 12.0
    max_attempts: int = 4
    max_turns: int = 60


def aborted_gates(results: Sequence[GateResult]) -> list[str]:
    """Gates that errored. The gate itself broke — the attempt aborts and
    nothing here is charged to the task (§5.4)."""
    return [r.gate for r in results if r.status == "error"]


def repair_decision(
    *,
    attempt: int,
    max_attempts: int,
    new: Sequence[NewFailure],
    previous: Sequence[NewFailure],
) -> str:
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


def require_session(session_id: str | None) -> str:
    """Every turn after the first resumes, so a missing session_id is fatal.

    `resume=None` starts a brand-new session with no memory of the plan or the
    code it wrote, and the repair loop would then read the flailing as the
    agent's fault (§5.3).
    """
    if not session_id:
        raise CellSessionError("the turn returned no session_id; nothing to resume")
    return session_id


def plan_checkpoint(
    container: str,
    *,
    options: dict,
    spec: CellSpec,
    protected: list[str],
    agent: Callable[..., AttemptResult],
    watch: Callable[[str], None] = print,
) -> tuple[AttemptResult, str, float]:
    """Turn one: the plan, validated before an implementation token is spent.

    Returns the turn's result, the raw JSON of the accepted plan, and what the
    checkpoint spent in total — the re-prompted turn included, or a rejected
    turn is a budget that quietly stops counting (§4.1). Raises `PlanRejected`.
    A shape failure gets exactly one re-prompt carrying the validation error;
    anything else is a decision about content and is final.
    """
    from saffron.agents import artifacts

    spent = 0.0
    try:
        attempt = agent(
            container, prompt=implement.PLAN_PROMPT, options=options, watch=watch
        )
        spent = attempt.cost_usd_est
        for reprompted in (False, True):
            try:
                artifacts.validate_plan(
                    attempt.text,
                    touches=spec.touches,
                    forbidden=spec.forbidden,
                    protected=protected,
                    spec_type=spec.spec_type,
                )
            except artifacts.PlanNotSchema as exc:
                if reprompted:
                    raise
                watch(f"PLAN: not the schema, re-prompting once — {exc}")
                attempt = agent(
                    container,
                    prompt=f"{exc}\n\n{artifacts.EXTRACTION_PROMPT}",
                    options=options,
                    resume=require_session(attempt.session_id),
                    watch=watch,
                    last_cost_usd=attempt.cost_usd_est,
                )
                spent += attempt.cost_usd_est
                continue
            return attempt, artifacts.parse_output_block(attempt.text), spent
    except implement.AgentFailed as failed:
        # A crashed plan turn is not a plan rejected on content, and the cell is
        # still alive, so it is not ORPHANED either (§4.5). The exception keeps
        # its own identity and carries what the checkpoint already spent, or a
        # re-prompted turn's first half stops counting (§4.1).
        prior = failed.attempt or _failed_turn(failed, "")
        failed.attempt = replace(prior, cost_usd_est=spent + prior.cost_usd_est)
        raise
    raise AssertionError("unreachable: the loop returns or raises")


def repair_loop(
    *,
    run_gates: Callable[[], list[GateResult]],
    baseline: list[GateResult],
    max_attempts: int,
    repair: Callable[[Sequence[NewFailure]], str | None],
    watch: Callable[[str], None] = print,
) -> str:
    """GATE ⇄ REPAIR (§5.4), host-invoked. Returns a terminal state.

    The agent never runs the gates: `repair` receives new failures and nothing
    else — no status, no verdict, no knowledge that it is being measured. It
    returns a terminal state to stop the loop early; the spend ceiling is the
    only thing in v0.5 that does.
    """
    previous: list[NewFailure] = []
    for attempt in range(1, max_attempts + 1):
        results = run_gates()
        if aborted := aborted_gates(results):
            watch(f"gates: {aborted} errored — infrastructure, not the task")
            return "GATE_ERROR"
        if drift := suite_drift(results, baseline):
            # The suites differ in a way no failure can express, so the
            # subtraction is not to be trusted — let alone reported (§5.4).
            watch(f"gates: {drift} — distrusting the subtraction")
            return "GATE_ERROR"
        new = subtract_baseline(results, baseline)
        decision = repair_decision(
            attempt=attempt, max_attempts=max_attempts, new=new, previous=previous
        )
        watch(f"gates: attempt {attempt}, {len(new)} new failures -> {decision}")
        if decision == "green":
            return "READY_FOR_REVIEW"
        if decision in ("no-progress", "exhausted"):
            # §3.3 has one state for both. Which one it was is on the watch line
            # above; the task's outcome — it could not pass its own gates — is
            # the same either way.
            return "EXHAUSTED"
        previous = new
        if stopped := repair(new):
            return stopped
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
    watch: Callable[[str], None],
) -> None:
    """The run's durable product (§0). The commits live only on the worktree
    volume, so a patch not exported ceases to exist at teardown.

    Never raises: this runs from a `finally`. A cell that died, or never
    started, makes the exec fail — reported, not swallowed.
    """
    from saffron.cell import worktree

    try:
        patch = worktree.export_patch(container, spec.base_sha)
        if not patch:
            # Absence and emptiness must not look alike: no commits, no file.
            watch("teardown: no commits, nothing to export")
            return
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "patch.diff").write_text(patch)
        (task_dir / "patch.json").write_text(
            json.dumps(
                {
                    "base_sha": spec.base_sha,
                    # The only surviving name for the commit once the volume is
                    # gone — the diff itself does not carry it.
                    "head_sha": worktree.head_sha(container),
                    "files": worktree.changed_files(container, spec.base_sha),
                },
                indent=2,
            )
        )
        watch(f"teardown: exported {len(patch)} bytes to {task_dir / 'patch.diff'}")
    except Exception as exc:
        watch(f"teardown: patch export FAILED — {exc}")


def run_one_cell(
    spec: CellSpec,
    *,
    repo: Path,
    mirror: Path,
    ledger: Ledger,
    out_dir: Path,
    watch: Callable[[str], None] = print,
) -> str:
    """Create a cell, drive one IMPLEMENT session in it, and gate the result.

    Returns a terminal state. Every transition is printed, because v0.5's
    whole point is that the operator watches it.
    """
    from saffron import preflight
    from saffron.agents import artifacts, context
    from saffron.cell import proxy, runtime, worktree
    from saffron.gates.core.scope import scope_gate
    from saffron.gates.runner import CellExecutor, run_suite
    from saffron.repos import image
    from saffron.repos.policy import load_policy

    # R2: policy is read from the host repo to learn gate *names* and to keep
    # the existing on-host validation (declared gate exists, is executable).
    # The paths run_suite is given must be cell-side — CellExecutor always
    # execs at /work (Task 6) and a host path there resolves to nothing.
    policy, policy_sha = load_policy(repo)
    gates = policy.gate_executables(Path(worktree.WORKTREE_MOUNT))

    repo_id = ledger.upsert_repo(repo.name, str(repo), str(mirror), policy_sha)
    run_id = ledger.create_run(repo_id, spec.base_sha)
    task_id = ledger.create_task(
        run_id,
        spec.spec_id,
        spec.spec_sha,
        branch=spec.branch,
        budget_usd=spec.budget_usd,
    )

    # Hoisted above the try: teardown exports here too, including on paths that
    # never reached the baseline write below.
    task_dir = out_dir / spec.spec_id

    network = "saffron-cells"
    volume = f"saffron-wt-{spec.spec_id}"
    state = f"saffron-st-{spec.spec_id}"
    container = f"saffron-cell-{spec.spec_id}"

    # Only what this run reached the creation of can leak. `volume rm` on a
    # name that never existed also exits non-zero, so reporting every failure
    # prints survivors for a run that aborted in preflight — absent reading as
    # leaked, which trains the operator to ignore the line. Each name is
    # recorded immediately before its own create, never a batch before the
    # first: a create that fails part-way can still have left its resource, but
    # the two that were never attempted are not survivors of anything.
    created: set[str] = set()

    try:
        # Inside the guarantee, not above it: a leftover network from a SIGKILLed
        # run makes `create_network` the first thing that raises on a re-run.
        runtime.remove_container(container)
        runtime.remove_network(network)
        runtime.remove_volume(volume)
        runtime.remove_volume(state)
        created.add(network)
        runtime.create_network(network)

        # The cell runs the repo's own image, never the base: the base carries
        # no toolchain, so every gate would error before the agent is reached.
        watch(f"preflight: building {image.cell_tag(repo)}")
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
        watch(
            f"preflight: probing {len(ports)} host ports at "
            + ", ".join(preflight.probe_addresses())
            + "; tolerating "
            + (", ".join(tolerated) or "nothing")
        )
        # The list the operator was just shown, not a second one taken now.
        preflight.assert_host_is_unreachable(image.BASE_TAG, network, ports)

        watch("preflight: starting the proxy")
        proxy_ip = proxy.start_proxy(network)
        watch(f"preflight: proxy at {proxy_ip}")

        created.add(volume)
        runtime.create_volume(volume)
        # The state volume and the container are recorded inside, each against
        # its own create: an ephemeral seed container runs between them.
        worktree.prepare_worktree(
            created=created,
            mirror=mirror,
            volume=volume,
            base_sha=spec.base_sha,
            branch=spec.branch,
            image=cell_image,
            container=container,
            network=network,
            env=cell_env(proxy_ip, policy.thread_env),
            state_volume=state,
        )
        watch(f"cell: {container} up, worktree at {spec.base_sha[:8]}")

        executor = CellExecutor(container)

        def _suite() -> list[GateResult]:
            """The repo's declared gates plus the one core gate v0.5 runs.

            `scope` reads the diff on the host, so it is prepended here rather
            than declared in `.saffron/gates` — first because it is the only
            gate that cannot break on the repo's toolchain (§5.4). Measured
            from `base_sha`, unlike doneness: what it judges is the whole task
            diff a reviewer reads, the plan turn's commits included.
            """
            changed = worktree.changed_files(container, spec.base_sha)
            return [
                # The diff goes with the paths: it is what proves the export the
                # reviewer will read still has the shape the host pinned.
                scope_gate(
                    changed,
                    spec.touches,
                    diff=worktree.export_patch(container, spec.base_sha),
                ),
                *run_suite(gates, cwd=repo, executor=executor),
            ]

        # At base_sha the diff is empty, so `scope` passes with no failures —
        # nothing for the subtraction to cancel a real escape against.
        baseline = _suite()
        watch("baseline: " + ", ".join(f"{r.gate}={r.status}" for r in baseline))
        for result in baseline:
            ledger.record_gate_result(result, run_id=run_id)

        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "baseline.json").write_text(
            json.dumps([r.model_dump() for r in baseline], indent=2)
        )

        if aborted := aborted_gates(baseline):
            watch(
                f"baseline errored in {aborted} — the toolchain is broken, not the code"
            )
            ledger.set_task_state(task_id, "PREFLIGHT_FAILED")
            ledger.finish_run(run_id, "COMPLETE")
            return "PREFLIGHT_FAILED"

        # The agent runs inside the cell, at /work, on the cell's own key (§5.1).
        context_md = (_SAFFRON_ROOT / "CONTEXT.md").read_text()
        template = (_SAFFRON_PKG / "agents" / "prompts" / "implement.md").read_text()
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
        )
        options = implement.agent_options(
            system_prompt=system_prompt,
            cwd=worktree.WORKTREE_MOUNT,
            max_turns=spec.max_turns,
            budget_usd=spec.budget_usd,
        )
        watch(f"IMPLEMENT: system prompt {len(system_prompt)} chars")
        ledger.set_task_state(task_id, "IMPLEMENTING")

        # Bound once, here, so no turn — plan, implement, repair, review or
        # rebuttal — can quietly inherit the library's hour (§4.3).
        agent = partial(implement.run_agent, timeout_s=TURN_TIMEOUT_S)

        try:
            planned, raw_plan, spent = plan_checkpoint(
                container,
                options=options,
                spec=spec,
                protected=policy.protected,
                agent=agent,
                watch=watch,
            )
        except artifacts.PlanRejected as rejected:
            watch(f"PLAN: rejected — {rejected}")
            ledger.set_task_state(task_id, "PLAN_REJECTED")
            ledger.finish_run(run_id, "COMPLETE")
            return "PLAN_REJECTED"
        except implement.AgentFailed as failed:
            # No plan and no commits, but a live cell: the earned state, not the
            # ORPHANED that a crash out of `run_one_cell` would stamp (§4.5).
            plan_cost = failed.attempt.cost_usd_est if failed.attempt else 0.0
            watch(f"PLAN: the session failed, ${plan_cost:.2f} spent — {failed}")
            ledger.set_task_state(task_id, "NOT_IMPLEMENTED")
            ledger.finish_run(run_id, "COMPLETE")
            return "NOT_IMPLEMENTED"

        # Extracted and hashed the moment it is produced, and never read from
        # /work again: a plan the implementer can rewrite is a claim (§5.3).
        (task_dir / "plan.json").write_text(raw_plan)
        watch(f"PLAN: accepted, sha256 {artifacts.hash_artifact(raw_plan)[:12]}")

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
            watch(f"budget: ${spent:.2f} of ${spec.budget_usd:.2f} — stopping")
            return True

        if _over_budget():
            # Same state as four red attempts, and only the watch line above
            # tells them apart — acceptable while v0.5 is attended (§3.3).
            ledger.set_task_state(task_id, "EXHAUSTED")
            ledger.finish_run(run_id, "COMPLETE")
            return "EXHAUSTED"

        try:
            implemented = agent(
                container,
                prompt=implement.IMPLEMENT_PROMPT,
                options=options,
                resume=session_id,
                watch=watch,
                last_cost_usd=last_cost,
            )
        except implement.AgentFailed as failed:
            # A bound firing, or a crash, must never discard committed work
            # (§4.3) — so the failure is recorded and the worktree is measured
            # below rather than the attempt being thrown away here.
            watch(f"IMPLEMENT: the session failed — {failed}")
            implemented = _failed_turn(failed, session_id)
        session_id = require_session(implemented.session_id or session_id)
        spent += implemented.cost_usd_est
        last_cost = implemented.cost_usd_est

        # Doneness is measured, never reported (§4.3): an attempt that produced
        # no commits failed, whatever the transcript says.
        commits = worktree.commits_ahead(container, planned_sha)
        watch(f"IMPLEMENT: {commits} commit(s), ${spent:.2f} spent")
        if commits == 0:
            ledger.set_task_state(task_id, "NOT_IMPLEMENTED")
            ledger.finish_run(run_id, "COMPLETE")
            return "NOT_IMPLEMENTED"

        # The suite that went green, kept for REVIEW: the critic is shown the
        # gate results, and re-running the suite to fetch them costs a suite.
        green: list[GateResult] = []

        def _run_gates() -> list[GateResult]:
            results = _suite()
            green[:] = results
            for result in results:
                # No attempts table yet, so attempt_id carries the task_id —
                # the convention the schema already documents (§4.1).
                ledger.record_gate_result(result, attempt_id=task_id)
            return results

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
                    watch=watch,
                    last_cost_usd=last_cost,
                )
            except implement.AgentFailed as failed:
                # The same rule as the implement turn (§4.3): a bound firing
                # mid-loop must not discard work that is already committed and
                # a suite that may be nearly green. The next gate run measures.
                watch(f"REPAIR: the session failed — {failed}")
                repaired = _failed_turn(failed, session_id)
            session_id = require_session(repaired.session_id or session_id)
            spent += repaired.cost_usd_est
            last_cost = repaired.cost_usd_est
            return None

        outcome = repair_loop(
            run_gates=_run_gates,
            baseline=baseline,
            max_attempts=spec.max_attempts,
            repair=_repair,
            watch=watch,
        )

        if outcome == "READY_FOR_REVIEW":
            ledger.set_task_state(task_id, "REVIEWING")
            reviews = review.run_review(
                container,
                # The critic sees the diff, not the cell's history: the same
                # bytes the patch export leaves behind for the operator.
                diff=worktree.export_patch(container, spec.base_sha),
                read_head=lambda path: worktree.read_at_head(container, path),
                spec_body=spec.body,
                gates=review.gate_summary(green),
                context_md=context_md,
                prompts_dir=_SAFFRON_PKG / "agents" / "prompts",
                max_turns=spec.max_turns,
                budget_usd=critic_budget(spec.budget_usd, spent),
                agent=agent,
                watch=watch,
            )
            # Deliberately not gated on the host ceiling: a green diff nobody
            # reviewed is exactly the product Appendix K says means nothing.
            spent += sum(r.cost_usd for r in reviews)
            (task_dir / "findings.json").write_text(
                json.dumps([r.as_dict() for r in reviews], indent=2)
            )
            outcome, why = review.review_state(reviews)
            watch(f"REVIEW: {why}")

        if outcome == "REBUTTING":
            ledger.set_task_state(task_id, "REBUTTING")
            blockers = [
                f
                for r in reviews
                for f in r.findings
                if f.anchored and f.severity == "blocker"
            ]
            if _over_budget():
                outcome = "EXHAUSTED"
            else:
                before = worktree.head_sha(container)

                def _rebut_gates() -> str | None:
                    """§5.6: red after the rebuttal is EXHAUSTED, and REBUT does
                    not re-enter the repair loop. An errored gate is still
                    infrastructure and still not charged to the task (§5.4)."""
                    results = _run_gates()
                    if aborted := aborted_gates(results):
                        watch(
                            f"gates: {aborted} errored — infrastructure, not the task"
                        )
                        return "GATE_ERROR"
                    if drift := suite_drift(results, baseline):
                        watch(f"gates: {drift} — distrusting the subtraction")
                        return "GATE_ERROR"
                    new = subtract_baseline(results, baseline)
                    watch(f"gates: {len(new)} new failures after the rebuttal")
                    return "EXHAUSTED" if new else None

                result = rebut.run_rebut(
                    container,
                    blockers=blockers,
                    options=options,
                    session_id=session_id,
                    spec_body=spec.body,
                    context_md=context_md,
                    prompts_dir=_SAFFRON_PKG / "agents" / "prompts",
                    max_turns=spec.max_turns,
                    budget_usd=critic_budget(spec.budget_usd, spent),
                    # Measured, never reported (§4.3): from the head the
                    # rebuttal started at, so the implement turn's own commits
                    # cannot satisfy it.
                    head_moved=lambda: worktree.commits_ahead(container, before) > 0,
                    rerun_gates=_rebut_gates,
                    diff=lambda: worktree.export_patch(container, spec.base_sha),
                    agent=agent,
                    watch=watch,
                    last_cost_usd=last_cost,
                )
                spent += result.cost_usd
                session_id = result.rebuttal.session_id or session_id
                (task_dir / "rebuttal.json").write_text(
                    json.dumps(result.as_dict(blockers), indent=2)
                )
                outcome, why = result.state, result.why
                watch(f"REBUT: {why}")

        watch(f"{outcome}: ${spent:.2f} spent, session {session_id}")
        ledger.set_task_state(task_id, outcome)
        ledger.finish_run(run_id, "COMPLETE")
        return outcome
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
        watch("teardown")
        # First, and on every path the exception one included: the export execs
        # inside the cell, so it must precede the container's removal as well as
        # the volume's. An EXHAUSTED run with commits is worth reading too.
        if container in created:
            export_patch(container, spec, task_dir, watch)
        removed = [("container", container, runtime.remove_container(container))]
        proxy.stop_proxy()
        removed.append(("network", network, runtime.remove_network(network)))
        # Volumes go too, or the same spec_id cannot be re-run.
        removed.append(("volume", volume, runtime.remove_volume(volume)))
        removed.append(("volume", state, runtime.remove_volume(state)))
        # Pre-cleaning tolerates absence; here a non-zero exit is a leak, and
        # a silent one is what let the state volume survive teardown unnoticed.
        # Reported, never raised: this is a `finally`.
        for kind, name, done in removed:
            if done.returncode != 0 and name in created:
                watch(f"teardown: {kind} {name} survived — {done.stderr.strip()[:160]}")
