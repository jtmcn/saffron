"""`saffron watch` — read one task's `events.jsonl` back, for an operator who
is not the terminal that started it.

Almost everything this needs shipped in `saffron/events.py` already:
`EventLog` writes one flushed JSON line per event, `read_log_since` reads
only what was appended past a byte offset (sharing `read_log`'s own per-line
tolerance for a truncated final line), and `describe` turns any event into
the exact line the attended terminal printed. This module adds no second
formatter and no second parser — it only adds a follower: something that
polls for what is new since the last poll and renders it through `describe`,
plus a filter over the two agent payloads that carry no operator signal.

Deliberately narrow, per the spec this ships under (`SA-0053`): no detection
of a task having finished (a follower here runs until interrupted, the way
`tail -f` does — the teardown event is not a reliable end marker, since a
killed cell never reaches it), and no rendering of a night's worth of tasks
(that is the batch index, `saffron/report/**`, forbidden to this spec).

backlog item 64 named a second way one task's log reads as
another's: a spec driven twice writes both tasks into one `events.jsonl`,
in order, with nothing between them, so the default view used to open on
whichever task's lines happened to be oldest — a rejected plan from last
week above today's live repair turn. `_since_newest_task` is the fix, and it
needs no new event kind: `Ceilings` is already the first event `run_task`
writes for every task, so the newest task starts at the last `Ceilings` the
log holds.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from pathlib import Path

from saffron.events import Agent, Ceilings, Event, describe, read_log_since

# The token counter, by the subtype the runtime gives it. Measured on one live
# task: 630 of 878 lines, the single largest shape in any log.
_TOKEN_COUNTER = "thinking_tokens"

# The bare tool acknowledgement — the second shape, 71 lines in that same log.
# `describe` renders it as "agent: tool ok"/"agent: tool error", carrying
# nothing the preceding tool_use line did not already say.
_BARE_ACK = "tool_result"


def _is_noise(event: Event) -> bool:
    """Whether an event is one of the two shapes the default view drops.

    Keyed on the agent payload's own `type`/`subtype`, never on the rendered
    line, and the distinction is the whole correctness of this function.
    `_describe_agent_event` renders a free-text message as `agent:` followed
    by the text itself, so *any* prefix match on the rendered string collides
    with whatever the agent happens to write — an agent remarking on being
    throttled would be filtered as telemetry. These two are exact matches on
    fields the agent does not author.

    Not `isinstance(event, Agent)` alone: both shapes live inside that one
    kind alongside the agent's real text and tool calls, so a kind-level
    filter would drop the work with the noise.

    The rate-limit event is deliberately *not* here. It renders with a
    leading "agent: rate limit" and reads like telemetry; it is the provider
    ceiling announcing itself, six lines against the token counter's 630, and
    hiding it is how a night dies `RATE_LIMITED` with nothing on screen to
    say so.
    """
    if not isinstance(event, Agent) or event.raw or not isinstance(event.event, dict):
        return False
    payload = event.event
    if payload.get("type") == _BARE_ACK:
        return True
    return payload.get("subtype") == _TOKEN_COUNTER


def _is_malformed(event: Event) -> bool:
    """An `Agent` whose payload survived `read_log` without being an object.

    `read_log` type-checks nothing — it is `cls(**obj)` onto a plain
    dataclass — so a corrupt or hand-edited line puts a `str` where
    `describe` expects a mapping, and `describe` raises `AttributeError` on
    it. Dropped here rather than allowed to reach it: one such line would
    otherwise end the whole follow through `main`'s catch-all as exit `2`,
    "infrastructure failed", for exactly the per-line corruption `read_log`
    exists to tolerate. `saffron/events.py` is forbidden to this spec, so
    `describe` still carries the hole for every other caller — item 61.
    """
    return (
        isinstance(event, Agent)
        and not event.raw
        and event.event is not None
        and not isinstance(event.event, dict)
    )


def render_line(event: Event, *, verbose: bool = False) -> str | None:
    """One event, rendered through `describe` and nothing else.

    `None` for an event `describe` itself renders as an empty string (the
    `Baseline` case with nothing to say yet), and — unless `verbose` — for one
    of the two noisy shapes `_is_noise` names. The filter is a default, never
    a deletion: `verbose=True` is how every dropped line stays reachable,
    because it is still the record of what the agent actually did.

    A malformed payload is dropped under `verbose` too, and that asymmetry is
    deliberate: `_is_noise` hides a line that renders fine, while
    `_is_malformed` names one `describe` cannot render at all.
    """
    if _is_malformed(event):
        return None
    if not verbose and _is_noise(event):
        return None
    return describe(event) or None


def _since_newest_task(events: list[Event]) -> list[Event]:
    """`events`, cut to the suffix that starts at the last `Ceilings` among
    them — the newest task's own boundary, since `run_task` writes one
    `Ceilings` first, for every task, before anything else in the log.

    Unchanged when `events` holds no `Ceilings` at all: a log written before
    tasks recorded their own ceilings on the way in has no boundary to cut
    at, and renders in full — the fact
    `test_a_log_renders_as_the_lines_its_terminal_printed` already pins.
    """
    newest: int | None = None
    for index, event in enumerate(events):
        if isinstance(event, Ceilings):
            newest = index
    if newest is None:
        return events
    return events[newest:]


def _sleep_and_continue(seconds: float) -> bool:
    """The real poll: sleep, then say "keep going" — the one thing this
    default never says is "stop". A test's own `sleep` is the only way a
    `follow` loop ends without pretending the production loop does; counting
    iterations inside the loop body would be exactly that pretense."""
    time.sleep(seconds)
    return True


def once(_seconds: float) -> bool:
    """The `--no-follow` poll: render what is on disk, then stop.

    Not finish *detection*, which is out of scope and unbuildable as asked —
    a killed cell emits no teardown event to detect. This needs none, because
    it never waits for a next line: it answers the spec's third problem (a
    finished task's log readable as something other than raw JSON) rather
    than the first.
    """
    return False


class UnknownTask(LookupError):
    """No task directory at the path `follow` looked in.

    Named apart from the silent `[]` `read_log` returns for a missing file:
    an operator who mistyped a spec id must not get the same output as a task
    that has genuinely produced nothing yet. Carries the directory it looked
    in, because that is the one fact a mistyped id needs said back to it.
    """

    def __init__(self, task_dir: Path) -> None:
        self.task_dir = Path(task_dir)
        super().__init__(f"no task directory at {self.task_dir}")


def follow(
    task_dir: Path,
    *,
    verbose: bool = False,
    whole_log: bool = False,
    interval: float = 1.0,
    sleep: Callable[[float], bool] = _sleep_and_continue,
) -> Iterator[str]:
    """Yield rendered lines from one task's `events.jsonl`, forever — the
    way `tail -f` follows a growing file — until `sleep` says stop.

    Raises `UnknownTask` if `task_dir` is not a directory at all: a mistyped
    spec id, not a task that has not started yet (out of scope here — the
    directory appears when the supervisor first writes to it, and waiting for
    that to happen is a different feature from reading it).

    Each poll reads only the bytes appended since the poll before it, via
    `read_log_since`, so nothing already read is read or parsed again (item
    62: a whole-file re-read every poll cost O(n²) over a night, measured at
    5.7s per re-read on a 37 MB / 160k-line log). `sleep`/`interval` are
    injected rather than reaching `time.sleep` directly, so a test can drive
    this loop to a deterministic end without waiting on a real clock; the
    real default (`_sleep_and_continue`) never returns `False`, which is what
    makes "runs until interrupted" true in production and finite in a test.

    By default (`whole_log=False`) the very first poll — the one that starts
    from offset `0` and so is the one whole-file read this ever does — is cut
    to `_since_newest_task`: a spec driven twice writes both tasks into one
    file, and an operator diagnosing the newer one must not open on the
    older one's outcome (backlog item 64). Only that first read is
    cut: a `Ceilings` a spec driven again writes while this follower is
    already running arrives on a later poll like anything else appended
    since the poll before it, and following continues past it rather than
    clearing the screen. `whole_log=True` skips the cut entirely — every
    task in the file renders, in order, behind `--whole-log`.
    """
    task_dir = Path(task_dir)
    if not task_dir.is_dir():
        raise UnknownTask(task_dir)
    offset = 0
    first_poll = True
    while True:
        events, offset = read_log_since(task_dir, offset)
        if first_poll and not whole_log:
            events = _since_newest_task(events)
        first_poll = False
        for event in events:
            line = render_line(event, verbose=verbose)
            if line is not None:
                yield line
        if not sleep(interval):
            return
