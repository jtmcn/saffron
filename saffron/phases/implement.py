"""Phase 2 — IMPLEMENT, with a plan checkpoint (DESIGN.md §5.3).

The planner and the implementer are the same session: they are not adversaries,
and splitting them pays full context cost twice for the same file reads.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from saffron.agents.artifacts import EXTRACTION_PROMPT
from saffron.cell import runtime
from saffron.cell.worktree import STATE_MOUNT, WORKTREE_MOUNT
from saffron.events import Agent, Event, describe
from saffron.gates.baseline import NewFailure

# The whole set an implementer is offered, not merely the set it may call
# unprompted. Measured: under `allowed_tools` alone the model still saw every
# built-in, Task and WebFetch and Cron* included — that list only
# auto-approves. `tools` is the one that withholds (§5.3).
# No TodoWrite: this runtime does not have it, and naming a tool that does not
# exist reads as a grant. An unknown name here is dropped, never granted.
IMPLEMENT_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]

# Installed by images/cell-base.python.Dockerfile. The agent runs inside the
# cell; the host drives it from outside (§5.1).
RUNNER = "/opt/saffron/agent_runner.py"
# The base image's own interpreter, never PATH's: a repo image can put a venv
# first, and the SDK is not installed in it (measured).
PYTHON = "/opt/saffron/python"

PLAN_PROMPT = (
    "Produce the plan for this task. Read whatever you need to; change no "
    "file and make no commit. If the declared touches cannot satisfy the "
    "acceptance criteria, propose scope instead of a plan. " + EXTRACTION_PROMPT
)

IMPLEMENT_PROMPT = (
    "The plan is accepted. Implement it now and commit your work. An attempt "
    "that produces no commits failed, whatever you say about it."
)

# session.py's one-turn salvage (SA-0028): spent only when the implement turn
# was cut off at its own turn ceiling with the worktree still at zero commits
# — the gap `committed` does not cover because a cell that never reaches GATE
# is never gated. Bounded far below an ordinary implement turn's own
# `max_turns`: this is a `git add`/`git commit` of what already exists, not a
# second attempt at the task. A run once spent 141 turns and $11.68 doing
# correct work it never committed; a salvage that could itself run that long
# would be the same defect one level down.
SALVAGE_MAX_TURNS = 5

SALVAGE_PROMPT = (
    "This turn was cut off before anything was committed. Do not keep "
    "implementing, do not re-read files, do not investigate further — commit "
    "exactly what already exists in the worktree, as-is, right now."
)


class AgentFailed(RuntimeError):
    """The turn did not finish cleanly: no result event, an error, a non-success
    subtype, a non-zero exit, or a kill by the idle or wall-clock bound.

    Not raised when the completion window closes: the runner emitted its result
    and only a child process was still holding stdout open (§4.3).

    An absent result and a clean result must never be the same value (§4.3) —
    this is the exception that keeps them apart. Whoever catches it still has
    to measure the worktree: a bound firing must not discard committed work.
    """

    def __init__(self, message: str, attempt: AttemptResult | None = None) -> None:
        super().__init__(message)
        # A failed turn still costs money. Dropping it here is how a budget
        # silently stops counting (§4.3).
        self.attempt = attempt


@dataclass
class AttemptResult:
    session_id: str | None
    subtype: str
    terminal_reason: str | None
    num_turns: int
    cost_usd_est: float
    # Every `text` event of the turn, in order. The <output> block is read from
    # here and never from /work, which the agent can rewrite (§5.3).
    text: str = ""
    is_error: bool = False
    # Which §4.3 bound ended the turn, verbatim from the runtime: "" for a
    # runner that exited on its own, "completion" for one whose child held the
    # pipe. An idle or wall-clock kill raises instead of returning.
    bound: str = ""
    # The last rate-limit status the turn reported, and when its window
    # reopens. Not a cost: a ceiling the provider enforces, not one the cell
    # reports and the host sums (§5.1).
    rate_limit_status: str | None = None
    rate_limit_resets_at: int | None = None


def agent_options(
    *,
    system_prompt: str,
    cwd: str = WORKTREE_MOUNT,
    max_turns: int,
    budget_usd: float,
    tools: Sequence[str] = IMPLEMENT_TOOLS,
) -> dict:
    """ClaudeAgentOptions as a plain dict, so it is assertable without the SDK.

    `permission_mode="dontAsk"` is load-bearing: unattended, a mode that asks on
    an unapproved tool is a hang, not a fallback (§5.3).
    """
    options = {
        "system_prompt": system_prompt,
        # `tools` withholds, `allowed_tools` auto-approves. Both, or the agent
        # either sees tools it cannot call or stalls on the ones it can.
        "tools": list(tools),
        "allowed_tools": list(tools),
        "permission_mode": "dontAsk",
        # /work is the target repo's checkout and the task can edit it, so its
        # .claude/ would configure the agent working on it (§2). Load nothing.
        "setting_sources": [],
        "cwd": cwd,
        "max_turns": max_turns,
        # In-cell and per *turn*, not per task: one options dict drives every
        # turn of the session. The per-task ceiling is the host's sum in
        # session.py; this one only cuts a runaway turn short (§4.3).
        "max_budget_usd": budget_usd,
        "env": {
            # The repair loop resumes the same session across a gate suite, and
            # a suite is minutes. At the five-minute default the cache has
            # expired on every attempt and the whole accumulated context is
            # re-billed as fresh input (§7.1).
            "ENABLE_PROMPT_CACHING_1H": "1",
            # Never under /work: the agent must not be able to read its own
            # session state, and the secret scan must not trip on it (§5.1).
            "CLAUDE_CONFIG_DIR": STATE_MOUNT,
            # The proxy allows api.anthropic.com and nothing else, so telemetry
            # becomes denied CONNECTs and per-turn latency that reads as a hang.
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
    }
    return options


def repair_prompt(new_failures: Sequence[NewFailure]) -> str:
    """The only way a gate result ever reaches the agent: as failures (§5.4).

    No status, no gate verdict, no counts of what passed — the agent never runs
    the gates and never learns whether it is green.
    """
    # A host-side gate can fail the diff as a whole rather than a path — `size`
    # is the first — and "- [size] :? diff-too-large" reads as a broken gate to
    # the one channel a gate result ever reaches the agent through.
    lines = [
        f"- [{n.gate}] "
        + (f"{n.failure.file}:{n.failure.line or '?'} " if n.failure.file else "")
        + f"{n.failure.code}: {n.failure.message}"
        for n in new_failures
    ]
    return (
        "These failures are new since the base commit. Failures already "
        "present on the base commit are excluded and are not yours to fix. "
        "Fix these and commit.\n\n" + "\n".join(lines)
    )


def when(stamp: int | None) -> str:
    """A unix timestamp is not something an operator watching a run can act on;
    the question it answers is "when can I retry" (§0). The day goes with it
    unless it is today: a seven-day window resets days out, and a bare clock
    time reads as an hour away."""
    local = time.localtime(stamp)
    today = time.localtime()
    same_day = (local.tm_year, local.tm_yday) == (today.tm_year, today.tm_yday)
    return time.strftime("%H:%M local" if same_day else "%a %d %b %H:%M local", local)


def _quarantined(spec_id: str, line: str) -> Agent:
    """A line that is not an event, bounded at the same 160 characters
    `describe` renders it at. `raw=True` is the quarantine and must survive
    every hop; the bound is what keeps an untrusted cell from choosing how
    much of the control plane's disk it writes."""
    return Agent(timestamp=time.time(), spec_id=spec_id, raw=True, line=line[:160])


def run_agent(
    container: str,
    *,
    prompt: str,
    options: dict,
    resume: str | None = None,
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
    last_cost_usd: float = 0.0,
    timeout_s: float = 3600,
    exec_stream: Callable[..., runtime.Completed] = runtime.exec_stream,
    reap_cell: Callable[..., runtime.Completed] = runtime.reap_cell,
) -> AttemptResult:
    """Drive one turn of the in-cell agent and return what it did.

    The host reads Saffron's event schema, never the SDK's — `agent_runner.py`
    inside the cell is the only place the SDK's types exist.

    `spec_id` is required, not defaulted: a forgotten keyword would file every
    line of this turn's stream under an empty id, indistinguishably from an
    observed one — the same rule `session.repair_loop` states for its own
    `spec_id` (§4.1).

    Every event this turn produces is emitted as `events.Agent` — the parsed
    cell dict verbatim under `event`, a raw non-JSON line under `line`, or a
    host-authored fact with neither — the moment it is known, and never
    reduced to a string first: the dict is only ever available here, not
    downstream of it (SA-0041).
    """
    request = json.dumps({"prompt": prompt, "options": options, "resume": resume})
    text: list[str] = []
    errors: list[str] = []
    result: dict = {}
    rate_limit: dict = {}

    def _on_line(line: str) -> bool:
        """True once the result event has been seen — §4.3's completion signal,
        and the only thing that opens the completion window. Reading it here
        keeps Saffron's event schema out of the runtime seam."""
        if line.strip():
            _consume(line)
        return bool(result)

    def _consume(line: str) -> None:
        try:
            event = json.loads(line)
        except ValueError:
            # Anything not an event came from a process sharing the runner's
            # stdout. Show it to the operator; never try to read it as one —
            # `raw=True` is the quarantine, and it must survive every hop.
            # Truncated at capture, not at render: `describe` already cuts at
            # 160, but the untruncated line reached `events.jsonl`. Measured on
            # one 5 MB stdout line — 715 bytes written before this spec, 10 MB
            # after. The cell is untrusted and this is a control-plane file.
            emit(_quarantined(spec_id, line))
            return
        if not isinstance(event, dict):
            # JSON that is not an object: `_describe_agent_event` calls `.get`,
            # so a bare list or string would raise inside the renderer. Same
            # quarantine, and it has its own branch because `json.loads` does
            # not raise for it.
            emit(_quarantined(spec_id, line))
            return
        if event.get("type") == "text":
            text.append(str(event.get("text", "")))
        elif event.get("type") == "error":
            errors.append(str(event.get("error", "")))
        elif event.get("type") == "result":
            result.update(event)
        elif event.get("type") == "rate_limit":
            # Last one wins: the CLI emits on transition, so the final state is
            # the one the next turn would start under.
            rate_limit.update(event)
        # The dict, verbatim, under `event` — never re-rendered to a string
        # here. `describe()` is the one place it becomes prose, and it is
        # called downstream of this line, not inside it.
        emit(Agent(timestamp=time.time(), spec_id=spec_id, raw=False, event=event))

    done = exec_stream(
        container,
        [PYTHON, RUNNER],
        stdin_data=request,
        on_line=_on_line,
        workdir=WORKTREE_MOUNT,
        timeout_s=timeout_s,
    )

    if done.timed_out:
        # `exec_stream` killed the host-side client; measured, that leaves the
        # runner alive inside the cell. The driver goes on to measure commits,
        # run the suite and resume the session in this same container, so an
        # abandoned agent would still be editing /work underneath all three.
        reaped = reap_cell(container)
        emit(
            Agent(
                timestamp=time.time(),
                spec_id=spec_id,
                raw=False,
                detail=(
                    "reaped the cell after the kill"
                    if reaped.returncode == 0
                    else f"the cell would not reap — {reaped.stderr.strip()[:200]}"
                ),
            )
        )

    detail = "; ".join(errors) or done.stderr.strip()[-800:] or "no output"
    # One phrasing for both failure paths, so "why did this turn end" reads the
    # same whether or not a result event arrived first.
    how = (
        f"was cut by the {done.bound} bound"
        if done.bound
        else "timed out"
        if done.timed_out
        else f"exited {done.returncode}"
        if done.returncode
        else "errored"
    )
    if not result:
        # An idle or wall kill takes the runner mid-stream, so no result event
        # ever carries the cost fields. The turn still spent what the last good
        # figure saw, and dropping it is how the ceiling stops counting (§4.1).
        raise AgentFailed(
            f"the agent produced no result event, {how}: {detail}",
            AttemptResult(
                session_id=None,
                subtype="error",
                terminal_reason=None,
                num_turns=0,
                cost_usd_est=last_cost_usd,
                text="".join(text),
                is_error=True,
                bound=done.bound,
                rate_limit_status=rate_limit.get("status"),
                rate_limit_resets_at=rate_limit.get("resets_at"),
            ),
        )

    subtype = str(result.get("subtype", "unknown"))
    is_error = bool(result.get("is_error"))
    if done.bound == "completion":
        # Not a failure and not silent: the operator should know a child of the
        # runner outlived it rather than wonder why the turn ended early.
        emit(
            Agent(
                timestamp=time.time(),
                spec_id=spec_id,
                raw=False,
                detail="result seen, then a child held stdout open — pipe closed",
            )
        )
    # One predicate for the accounting and the control flow both: a turn the
    # cost fallback treats as crashed must not also read as a clean return.
    # `timed_out` covers the idle and wall-clock kills only — a completion
    # window closing is a finished turn, and §4.3 is explicit that treating it
    # as a failure is the mistake splitting the two bounds exists to prevent.
    failed = is_error or subtype != "success" or done.timed_out or done.returncode != 0
    attempt = AttemptResult(
        session_id=result.get("session_id"),
        subtype=subtype,
        terminal_reason=result.get("terminal_reason"),
        num_turns=int(result.get("num_turns") or 0),
        cost_usd_est=_reconcile_cost(
            reported=float(result.get("total_cost_usd") or 0.0),
            last_good=last_cost_usd,
            failed=failed,
        ),
        text="".join(text),
        is_error=is_error,
        bound=done.bound,
        rate_limit_status=rate_limit.get("status"),
        rate_limit_resets_at=rate_limit.get("resets_at"),
    )
    if failed:
        # `is_error`, measured and not assumed: a cell with no credential
        # returns `subtype="success"` with `is_error=true` and terminal_reason
        # `api_error`. Keying on the subtype alone would call a session that
        # did nothing at all a clean success.
        # A turn ceiling is a bound like the other three, and it is the one the
        # exit code cannot show: "exited 1" was the whole account of a session
        # that did correct work for 61 turns and was cut mid-edit.
        ended = (
            f"reached its ceiling of {options.get('max_turns')} turns "
            f"after {attempt.num_turns}"
            if subtype == "error_max_turns"
            else how
        )
        raise AgentFailed(
            f"the agent {ended} ({subtype}/{attempt.terminal_reason}): {detail}",
            attempt,
        )
    return attempt


def _reconcile_cost(*, reported: float, last_good: float, failed: bool) -> float:
    """A crashed session may report every cost field as zero (§4.1).

    An attempt that burned $4 and then crashed records $0 unless the supervisor
    falls back to the last good figure it saw. Unattended, this is the
    difference between a budget that holds and one that silently stops counting.

    `failed` is the caller's single predicate, so the figure charged and the
    control flow can never disagree about whether the turn worked.
    """
    if failed and reported == 0.0 and last_good > 0.0:
        return last_good
    return reported
