"""`saffron.watch` — a second reader onto a task's `events.jsonl`.

Every fixture below is a real `Event`, appended through the real `EventLog`,
never hand-typed JSON: that is what makes each witness prove the round trip
through `read_log`/`describe` rather than a parser reading what the test
author imagined the writer emits.
"""

from __future__ import annotations

import json

import pytest

from saffron import watch
from saffron.events import Agent, EventLog, PhaseStart, Preflight, Teardown, describe


def _once(_seconds: float) -> bool:
    """A `follow` poll that renders whatever is already on disk exactly
    once, then stops — the deterministic, no-real-waiting stand-in for the
    real default's "keep going forever"."""
    return False


def test_a_log_renders_as_the_lines_its_terminal_printed(tmp_path):
    """The whole point: a watcher and the attended terminal agree, because
    both go through `describe` — never a second formatter."""
    task_dir = tmp_path / "SY-1"
    log = EventLog(task_dir)
    events = [
        Preflight(
            timestamp=1.0,
            spec_id="SY-1",
            step="cell_up",
            detail="saffron-cell-SY-1 up, worktree at bbbbbbbb",
        ),
        PhaseStart(
            timestamp=2.0,
            spec_id="SY-1",
            phase="IMPLEMENT",
            label="PLAN",
            detail="accepted, sha256 841501830587",
        ),
        Teardown(timestamp=3.0, spec_id="SY-1", step="start", ok=True),
    ]
    for event in events:
        log.append(event)

    lines = list(watch.follow(task_dir, sleep=_once))

    assert lines == [describe(event) for event in events]


def test_the_default_view_drops_the_token_counter_and_bare_acknowledgements(tmp_path):
    """Two agent payloads carry no operator signal — the periodic system
    event whose subtype is the running thinking-token estimate, and a bare
    tool result — and the default view drops both, keeping the agent's real
    work. Measured on one live task these two are 630 and 71 of 878 lines.

    Both are matched on the payload's own fields, never on the line they
    render to: a free-text message is rendered as `agent:` plus whatever the
    agent wrote, so a prefix match on the rendered string filters the agent's
    prose the moment it starts with the wrong words."""
    task_dir = tmp_path / "SY-2"
    log = EventLog(task_dir)
    real_work = Agent(
        timestamp=1.0,
        spec_id="SY-2",
        raw=False,
        event={"type": "text", "text": "reading the spec"},
    )
    token_counter = Agent(
        timestamp=2.0,
        spec_id="SY-2",
        raw=False,
        event={
            "type": "system",
            "subtype": "thinking_tokens",
            "data": {"estimated_tokens": 16300},
        },
    )
    bare_ack = Agent(
        timestamp=3.0,
        spec_id="SY-2",
        raw=False,
        event={"type": "tool_result", "is_error": False},
    )
    for event in (real_work, token_counter, bare_ack):
        log.append(event)

    lines = list(watch.follow(task_dir, verbose=False, sleep=_once))

    assert lines == [describe(real_work)]
    assert describe(token_counter) not in lines
    assert describe(bare_ack) not in lines


def test_the_rate_limit_line_is_signal_and_is_kept(tmp_path):
    """The one agent line least safe to hide. It renders with a leading
    `agent: rate limit` and reads like telemetry, which is exactly why an
    earlier attempt filtered it — but it is the provider ceiling announcing
    itself, six lines against the token counter's 630 in the same log, and
    hiding it is how a night dies `RATE_LIMITED` with nothing on screen.
    """
    task_dir = tmp_path / "SY-2b"
    log = EventLog(task_dir)
    warning = Agent(
        timestamp=1.0,
        spec_id="SY-2b",
        raw=False,
        event={"type": "rate_limit", "status": "allowed", "utilization": 0.5},
    )
    log.append(warning)

    assert list(watch.follow(task_dir, verbose=False, sleep=_once)) == [
        describe(warning)
    ]


def test_the_agents_own_words_are_never_filtered(tmp_path):
    """A free-text message renders as `agent:` plus the text, so it shares a
    prefix space with every telemetry shape. The agent remarking on a rate
    limit is the case that broke the first implementation: prose that reads
    like the telemetry line it is about.
    """
    task_dir = tmp_path / "SY-2c"
    log = EventLog(task_dir)
    prose = Agent(
        timestamp=1.0,
        spec_id="SY-2c",
        raw=False,
        event={"type": "text", "text": "rate limit handling looks wrong here"},
    )
    log.append(prose)

    assert list(watch.follow(task_dir, verbose=False, sleep=_once)) == [describe(prose)]


def test_the_unfiltered_view_keeps_every_line(tmp_path):
    """The filter is a default, never a deletion: `verbose=True` reaches
    everything the default view drops, because a diagnosis needs the record
    of what the agent actually did."""
    task_dir = tmp_path / "SY-3"
    log = EventLog(task_dir)
    events = [
        Agent(
            timestamp=1.0,
            spec_id="SY-3",
            raw=False,
            event={"type": "text", "text": "reading the spec"},
        ),
        Agent(
            timestamp=2.0,
            spec_id="SY-3",
            raw=False,
            event={
                "type": "system",
                "subtype": "thinking_tokens",
                "data": {"estimated_tokens": 16300},
            },
        ),
        Agent(
            timestamp=3.0,
            spec_id="SY-3",
            raw=False,
            event={"type": "tool_result", "is_error": False},
        ),
    ]
    for event in events:
        log.append(event)

    lines = list(watch.follow(task_dir, verbose=True, sleep=_once))

    assert lines == [describe(event) for event in events]


def test_following_emits_only_events_that_arrived_since_the_last_poll(tmp_path):
    """A watcher that re-rendered the file each time would repeat every line
    it had already printed. The poll interval and the poll itself are both
    injected, so this test neither waits nor sleeps."""
    task_dir = tmp_path / "SY-4"
    log = EventLog(task_dir)
    first = Teardown(timestamp=1.0, spec_id="SY-4", step="start", ok=True)
    second = Teardown(
        timestamp=2.0, spec_id="SY-4", step="proxy", ok=False, detail="denied"
    )
    log.append(first)

    calls: list[float] = []

    def sleep(seconds: float) -> bool:
        calls.append(seconds)
        if len(calls) == 1:
            # Arrives between the first and second poll — the follower must
            # not have already rendered it, and must not re-render `first`.
            log.append(second)
            return True
        return False

    lines = list(watch.follow(task_dir, interval=5, sleep=sleep))

    assert lines == [describe(first), describe(second)]
    assert calls == [5, 5]


def test_a_partial_final_line_is_dropped_and_the_whole_ones_survive(tmp_path):
    """A log caught mid-write loses the partial line and keeps every whole
    one — `read_log`'s own distinction, inherited here rather than
    reimplemented."""
    task_dir = tmp_path / "SY-5"
    task_dir.mkdir()
    log = EventLog(task_dir)
    whole_a = Teardown(timestamp=1.0, spec_id="SY-5", step="start", ok=True)
    whole_b = Teardown(timestamp=2.0, spec_id="SY-5", step="network", ok=True)
    log.append(whole_a)
    log.append(whole_b)
    # A live file being appended by another process, caught between the
    # write and its flush — never through `EventLog.append`, which always
    # writes a whole line.
    events_path = task_dir / "events.jsonl"
    with events_path.open("a") as handle:
        handle.write('{"kind": "Teardown", "spec_id": "SY-5", "step": "tr')

    lines = list(watch.follow(task_dir, sleep=_once))

    assert lines == [describe(whole_a), describe(whole_b)]


def test_an_unknown_task_names_the_directory_it_looked_in(tmp_path):
    """A mistyped spec id must not read as a task that has genuinely
    produced nothing yet — it names the directory `follow` looked in."""
    missing = tmp_path / "batches" / "v0" / "SY-404"

    with pytest.raises(watch.UnknownTask) as excinfo:
        list(watch.follow(missing))

    assert str(missing) in str(excinfo.value)


def test_a_payload_that_is_not_an_object_is_dropped_and_the_rest_survive(tmp_path):
    """`read_log` type-checks nothing, so a corrupt line can hand `describe`
    a `str` where it expects a mapping — and `describe` raises
    `AttributeError` on it. One such line must cost its own line and no
    more: raised, it ends the whole follow, and `main`'s catch-all reports
    the per-line corruption `read_log` exists to tolerate as exit `2`,
    infrastructure failed.

    Written straight to the file rather than built as an `Agent` and
    appended, following the partial-line witness above and for the same
    reason: `Agent.event` is annotated `dict | None`, so the constructor is
    the one path this shape cannot arrive by. `read_log` is where it gets in,
    because `cls(**obj)` checks no types at all.
    """
    task_dir = tmp_path / "SY-6"
    log = EventLog(task_dir)
    whole = Teardown(timestamp=1.0, spec_id="SY-6", step="start", ok=True)
    after = Teardown(timestamp=3.0, spec_id="SY-6", step="network", ok=True)
    log.append(whole)
    events_path = task_dir / "events.jsonl"
    with events_path.open("a") as handle:
        handle.write(
            json.dumps(
                {
                    "kind": "Agent",
                    "timestamp": 2.0,
                    "spec_id": "SY-6",
                    "raw": False,
                    "event": "not an object",
                }
            )
            + "\n"
        )
    log.append(after)

    lines = list(watch.follow(task_dir, sleep=_once))

    assert lines == [describe(whole), describe(after)]


def test_a_malformed_payload_is_dropped_by_the_unfiltered_view_too(tmp_path):
    """`--all` reaches every line `_is_noise` hides, but not one `describe`
    cannot render at all. The asymmetry is the point: a filtered line is
    still a line, and this one is a crash."""
    task_dir = tmp_path / "SY-7"
    log = EventLog(task_dir)
    kept = Teardown(timestamp=2.0, spec_id="SY-7", step="start", ok=True)
    task_dir.mkdir(parents=True, exist_ok=True)
    with (task_dir / "events.jsonl").open("a") as handle:
        handle.write(
            json.dumps(
                {
                    "kind": "Agent",
                    "timestamp": 1.0,
                    "spec_id": "SY-7",
                    "raw": False,
                    "event": ["also", "not"],
                }
            )
            + "\n"
        )
    log.append(kept)

    lines = list(watch.follow(task_dir, verbose=True, sleep=_once))

    assert lines == [describe(kept)]


def test_the_no_follow_poll_stops_after_one_pass(tmp_path):
    """`watch.once` is what `--no-follow` hands `follow`: it renders what is
    on disk and stops, without waiting for a line that may never come. Not
    finish detection — it never asks whether the task ended, which is why it
    needs no teardown event to be reliable."""
    task_dir = tmp_path / "SY-8"
    log = EventLog(task_dir)
    events = [
        Teardown(timestamp=1.0, spec_id="SY-8", step="start", ok=True),
        Teardown(timestamp=2.0, spec_id="SY-8", step="network", ok=True),
    ]
    for event in events:
        log.append(event)

    lines = list(watch.follow(task_dir, sleep=watch.once))

    assert lines == [describe(event) for event in events]
