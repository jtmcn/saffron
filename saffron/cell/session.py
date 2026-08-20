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

from saffron.gates.baseline import NewFailure, is_no_progress
from saffron.gates.contract import GateResult

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
    """Create a cell, run the baseline suite, and stop at the SDK seam.

    Returns a terminal state. Every transition is printed, because v0.5's
    whole point is that the operator watches it.

    Scope boundary (this task): this function does not drive the agent SDK —
    no `query()`, no `ClaudeSDKClient`, no message stream. It builds the system
    prompt and the agent options and stops there. A later task adds the actual
    session drive and the GATE/REPAIR loop around `repair_decision` above.
    """
    from saffron import preflight
    from saffron.agents import context
    from saffron.cell import proxy, runtime, worktree
    from saffron.gates.runner import CellExecutor, run_suite
    from saffron.phases import implement
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
        watch(
            f"IMPLEMENT: agent options built ({len(options['allowed_tools'])} "
            "tools, dontAsk) — ready to drive the session"
        )
        # SEAM: this is where a later task drives the SDK — open a
        # ClaudeSDKClient with `options`, stream the IMPLEMENT turn, extract
        # and validate plan.json (saffron.agents.artifacts.validate_plan),
        # then loop GATE (run_suite again) -> repair_decision -> REPAIR,
        # resuming the same session, until green/no-progress/exhausted. Left
        # unimplemented on purpose (task scope): the loop's shape depends on
        # what the message stream actually yields.
        ledger.finish_run(run_id, "COMPLETE")
        return "NOT_IMPLEMENTED"
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
