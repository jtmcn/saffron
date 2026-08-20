"""One cell, start to finish (DESIGN.md §5.1–§5.4).

v0.5 only: no scheduler, no budget pool, no PR. The operator watches this run.
`ponytail:` this is v0.5's supervisor. v1 replaces it with supervisor.py plus
scheduler.py, and this file goes the way replay.py went.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from saffron.gates.baseline import NewFailure, is_no_progress, subtract_baseline
from saffron.gates.contract import GateResult
from saffron.phases import implement
from saffron.phases.implement import AttemptResult

if TYPE_CHECKING:
    from saffron.ledger import Ledger

# Where this file lives inside the Saffron tree, used to locate CONTEXT.md and
# the prompt templates — Saffron's own files, never the target repo's (§5.3).
_SAFFRON_ROOT = Path(__file__).resolve().parents[2]
_SAFFRON_PKG = Path(__file__).resolve().parents[1]


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


def plan_checkpoint(
    container: str,
    *,
    options: dict,
    spec: CellSpec,
    protected: list[str],
    agent: Callable[..., AttemptResult],
    watch: Callable[[str], None] = print,
) -> tuple[AttemptResult, str]:
    """Turn one: the plan, validated before an implementation token is spent.

    Returns the turn's result and the raw JSON of the accepted plan, or raises
    `PlanRejected`. A shape failure gets exactly one re-prompt carrying the
    validation error; anything else is a decision about content and is final.
    """
    from saffron.agents import artifacts

    attempt = agent(
        container, prompt=implement.PLAN_PROMPT, options=options, watch=watch
    )
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
                resume=attempt.session_id,
                watch=watch,
                last_cost_usd=attempt.cost_usd_est,
            )
            continue
        return attempt, artifacts.parse_output_block(attempt.text)
    raise AssertionError("unreachable: the loop returns or raises")


def repair_loop(
    *,
    run_gates: Callable[[], list[GateResult]],
    baseline: list[GateResult],
    max_attempts: int,
    repair: Callable[[Sequence[NewFailure]], None],
    watch: Callable[[str], None] = print,
) -> str:
    """GATE ⇄ REPAIR (§5.4), host-invoked. Returns a terminal state.

    The agent never runs the gates: `repair` receives new failures and nothing
    else — no status, no verdict, no knowledge that it is being measured.
    """
    previous: list[NewFailure] = []
    for attempt in range(1, max_attempts + 1):
        results = run_gates()
        if aborted := aborted_gates(results):
            watch(f"gates: {aborted} errored — infrastructure, not the task")
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
        repair(new)
    raise AssertionError("unreachable: repair_decision exhausts at max_attempts")


def cell_env(proxy_ip: str, thread_env: Mapping[str, str]) -> dict[str, str]:
    """Everything §5.1's per-task block puts in the cell's environment.

    The proxy is the cell's only route out, and `ANTHROPIC_API_KEY` is the one
    credential a cell ever holds — the agent runs inside it.
    """
    from saffron.cell import proxy
    from saffron.cell.worktree import STATE_MOUNT

    env = proxy.proxy_env(proxy_ip) | dict(thread_env)
    env["CLAUDE_CONFIG_DIR"] = STATE_MOUNT
    if key := os.environ.get("ANTHROPIC_API_KEY"):
        env["ANTHROPIC_API_KEY"] = key
    return env


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

    network = "saffron-cells"
    volume = f"saffron-wt-{spec.spec_id}"
    state = f"saffron-st-{spec.spec_id}"
    container = f"saffron-cell-{spec.spec_id}"

    try:
        # Inside the guarantee, not above it: a leftover network from a SIGKILLed
        # run makes `create_network` the first thing that raises on a re-run.
        runtime.remove_container(container)
        runtime.remove_network(network)
        runtime.remove_volume(volume)
        runtime.remove_volume(state)
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
        watch(f"preflight: probing {', '.join(preflight.probe_addresses())}")
        preflight.assert_host_is_unreachable(image.BASE_TAG, network)

        watch("preflight: starting the proxy")
        proxy_ip = proxy.start_proxy(network)
        watch(f"preflight: proxy at {proxy_ip}")

        runtime.create_volume(volume)
        worktree.prepare_worktree(
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
        baseline = run_suite(gates, cwd=repo, executor=executor)
        watch("baseline: " + ", ".join(f"{r.gate}={r.status}" for r in baseline))
        for result in baseline:
            ledger.record_gate_result(result, run_id=run_id)

        task_dir = out_dir / spec.spec_id
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
            "IMPLEMENT", context_md, template=template, spec=spec.body
        )
        options = implement.agent_options(
            system_prompt=system_prompt,
            cwd=worktree.WORKTREE_MOUNT,
            max_turns=spec.max_turns,
            budget_usd=spec.budget_usd,
        )
        watch(f"IMPLEMENT: system prompt {len(system_prompt)} chars")
        ledger.set_task_state(task_id, "IMPLEMENTING")

        try:
            planned, raw_plan = plan_checkpoint(
                container,
                options=options,
                spec=spec,
                protected=policy.protected,
                agent=implement.run_agent,
                watch=watch,
            )
        except artifacts.PlanRejected as rejected:
            watch(f"PLAN: rejected — {rejected}")
            ledger.set_task_state(task_id, "PLAN_REJECTED")
            ledger.finish_run(run_id, "COMPLETE")
            return "PLAN_REJECTED"

        # Extracted and hashed the moment it is produced, and never read from
        # /work again: a plan the implementer can rewrite is a claim (§5.3).
        (task_dir / "plan.json").write_text(raw_plan)
        watch(f"PLAN: accepted, sha256 {artifacts.hash_artifact(raw_plan)[:12]}")

        session_id = planned.session_id
        spent = planned.cost_usd_est
        # The *previous turn's* cost, not the running total: what a crashed
        # turn reporting zero falls back to is one turn's figure (§4.1).
        last_cost = planned.cost_usd_est

        try:
            implemented = implement.run_agent(
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
            implemented = failed.attempt or AttemptResult(
                session_id=session_id,
                subtype="error",
                terminal_reason=None,
                num_turns=0,
                cost_usd_est=0.0,
                is_error=True,
            )
        session_id = implemented.session_id or session_id
        spent += implemented.cost_usd_est
        last_cost = implemented.cost_usd_est

        # Doneness is measured, never reported (§4.3): an attempt that produced
        # no commits failed, whatever the transcript says.
        commits = worktree.commits_ahead(container, spec.base_sha)
        watch(f"IMPLEMENT: {commits} commit(s), ${spent:.2f} spent")
        if commits == 0:
            ledger.set_task_state(task_id, "NOT_IMPLEMENTED")
            ledger.finish_run(run_id, "COMPLETE")
            return "NOT_IMPLEMENTED"

        def _run_gates() -> list[GateResult]:
            results = run_suite(gates, cwd=repo, executor=executor)
            for result in results:
                # No attempts table yet, so attempt_id carries the task_id —
                # the convention the schema already documents (§4.1).
                ledger.record_gate_result(result, attempt_id=task_id)
            return results

        def _repair(new: Sequence[NewFailure]) -> None:
            nonlocal session_id, spent, last_cost
            ledger.set_task_state(task_id, "REPAIRING")
            repaired = implement.run_agent(
                container,
                prompt=implement.repair_prompt(new),
                options=options,
                resume=session_id,
                watch=watch,
                last_cost_usd=last_cost,
            )
            session_id = repaired.session_id or session_id
            spent += repaired.cost_usd_est
            last_cost = repaired.cost_usd_est

        state = repair_loop(
            run_gates=_run_gates,
            baseline=baseline,
            max_attempts=spec.max_attempts,
            repair=_repair,
            watch=watch,
        )
        watch(f"{state}: ${spent:.2f} spent, session {session_id}")
        ledger.set_task_state(task_id, state)
        ledger.finish_run(run_id, "COMPLETE")
        return state
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
        runtime.remove_container(container)
        proxy.stop_proxy()
        runtime.remove_network(network)
        # Volumes go too, or the same spec_id cannot be re-run. Whoever adds
        # patch export must export before this line, not after.
        runtime.remove_volume(volume)
        runtime.remove_volume(state)
