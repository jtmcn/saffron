"""SA-0029: the host event vocabulary and its durable log. No emission, no
renderer — that is `SA-0030`/`SA-0031` and `SA-0040`. No network, no cell.
"""

from __future__ import annotations

import json

import pytest

from saffron.events import (
    Agent,
    Attempt,
    Baseline,
    Budget,
    EventLog,
    GateResult,
    PhaseStart,
    Preflight,
    Teardown,
    Terminal,
    read_log,
)

_ONE_OF_EACH = [
    Preflight(timestamp=1.0, spec_id="SA-0029", step="proxy_start", detail="up"),
    Baseline(timestamp=2.0, spec_id="SA-0029", aborted=("tests",)),
    PhaseStart(
        timestamp=3.0,
        spec_id="SA-0029",
        phase="IMPLEMENT",
        label="SALVAGE",
        detail="3 commits",
    ),
    Attempt(
        timestamp=4.0,
        spec_id="SA-0029",
        attempt=1,
        commits=2,
        spent_usd=1.5,
        new_failures=0,
        decision="green",
    ),
    GateResult(timestamp=5.0, spec_id="SA-0029", gate="lint", status="fail"),
    Budget(timestamp=6.0, spec_id="SA-0029", ceiling="max_turns", value=141, limit=120),
    Agent(timestamp=7.0, spec_id="SA-0029", raw=False, event={"type": "text"}),
    Terminal(timestamp=8.0, spec_id="SA-0029", reason="finished_empty", spent_usd=0.5),
    Teardown(timestamp=9.0, spec_id="SA-0029", step="container", ok=True),
]


@pytest.mark.parametrize("event", _ONE_OF_EACH, ids=lambda e: type(e).__name__)
def test_round_trips_every_kind(tmp_path, event):
    log = EventLog(tmp_path)
    log.append(event)
    assert read_log(tmp_path) == [event]


def test_gate_result_error_and_fail_are_distinguishable(tmp_path):
    """`error` means the gate broke and is charged to nobody; `fail` means the
    repo's code is wrong. They must never collapse into one another."""
    log = EventLog(tmp_path)
    log.append(GateResult(timestamp=1.0, spec_id="SA", gate="tests", status="error"))
    log.append(GateResult(timestamp=2.0, spec_id="SA", gate="tests", status="fail"))
    statuses = [e.status for e in read_log(tmp_path)]
    assert statuses == ["error", "fail"]


def test_gate_result_carries_all_four_statuses(tmp_path):
    log = EventLog(tmp_path)
    for status in ("pass", "fail", "skip", "error"):
        log.append(GateResult(timestamp=1.0, spec_id="SA", gate="g", status=status))
    assert [e.status for e in read_log(tmp_path)] == ["pass", "fail", "skip", "error"]


def test_budget_ceilings_round_trip_distinctly(tmp_path):
    """SA-0005 died at the turn ceiling with 56% of budget unspent, and
    nothing said which of the three ceilings had fired. All three must
    survive the log as distinct, reconstructible facts."""
    log = EventLog(tmp_path)
    events = [
        Budget(timestamp=1.0, spec_id="SA", ceiling="budget_usd", value=9.0, limit=9.0),
        Budget(timestamp=2.0, spec_id="SA", ceiling="max_attempts", value=4, limit=4),
        Budget(timestamp=3.0, spec_id="SA", ceiling="max_turns", value=141, limit=120),
    ]
    for event in events:
        log.append(event)
    loaded = read_log(tmp_path)
    assert loaded == events
    assert [e.ceiling for e in loaded] == ["budget_usd", "max_attempts", "max_turns"]
    assert len({e.ceiling for e in loaded}) == 3


def test_terminal_distinguishes_all_five_zero_commit_endings(tmp_path):
    """The supervisor separates five ways an implement turn ends with no
    commits; a boolean would re-collapse them. 'Cut off and recovered' is
    deliberately absent — that branch has commits and belongs to `Attempt`."""
    log = EventLog(tmp_path)
    events = [
        Terminal(
            timestamp=1.0, spec_id="SA", reason="cut_off_no_salvage_room", spent_usd=9.0
        ),
        Terminal(
            timestamp=2.0, spec_id="SA", reason="cut_off_salvage_failed", spent_usd=9.5
        ),
        Terminal(
            timestamp=3.0,
            spec_id="SA",
            reason="ended_without_finishing",
            spent_usd=1.0,
            subtype="error",
            terminal_reason="api_error",
        ),
        Terminal(timestamp=4.0, spec_id="SA", reason="finished_empty", spent_usd=0.2),
        Terminal(timestamp=5.0, spec_id="SA", reason="plan_rejected", spent_usd=0.1),
    ]
    for event in events:
        log.append(event)
    loaded = read_log(tmp_path)
    assert loaded == events
    assert len({e.reason for e in loaded}) == 5


def test_agent_raw_line_round_trips_still_marked_as_raw(tmp_path):
    """The quarantine is the point: a line that was not an event must survive
    the log still flagged `raw=True`, not only on the terminal."""
    log = EventLog(tmp_path)
    event = Agent(timestamp=1.0, spec_id="SA", raw=True, line="not json at all")
    log.append(event)
    [loaded] = read_log(tmp_path)
    assert loaded.raw is True
    assert loaded == event


def test_agent_carries_a_parsed_dict_verbatim(tmp_path):
    log = EventLog(tmp_path)
    cell_event = {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}
    event = Agent(timestamp=1.0, spec_id="SA", raw=False, event=cell_event)
    log.append(event)
    [loaded] = read_log(tmp_path)
    assert loaded.event == cell_event
    assert loaded.raw is False


def test_on_disk_shape_is_pinned_by_a_hand_written_line(tmp_path):
    """Four later specs read this format. Pinned by a hand-written line, not
    by round-tripping the writer's own output back through itself."""
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "kind": "Attempt",
                "timestamp": 1735689600.0,
                "spec_id": "SA-0029",
                "attempt": 1,
                "commits": 2,
                "spent_usd": 1.5,
                "new_failures": 0,
                "decision": "green",
            }
        )
        + "\n"
    )
    [loaded] = read_log(tmp_path)
    assert loaded == Attempt(
        timestamp=1735689600.0,
        spec_id="SA-0029",
        attempt=1,
        commits=2,
        spent_usd=1.5,
        new_failures=0,
        decision="green",
    )


def test_read_log_drops_a_truncated_final_line(tmp_path):
    events_path = tmp_path / "events.jsonl"
    good = json.dumps(
        {
            "kind": "Teardown",
            "timestamp": 1.0,
            "spec_id": "SA",
            "step": "container",
            "ok": True,
        }
    )
    events_path.write_text(good + "\n" + good + "\n" + '{"kind": "Teardown", "time')
    loaded = read_log(tmp_path)
    assert loaded == [
        Teardown(timestamp=1.0, spec_id="SA", step="container", ok=True),
        Teardown(timestamp=1.0, spec_id="SA", step="container", ok=True),
    ]


def test_read_log_tolerates_an_unknown_kind(tmp_path):
    events_path = tmp_path / "events.jsonl"
    known = json.dumps(
        {
            "kind": "Teardown",
            "timestamp": 1.0,
            "spec_id": "SA",
            "step": "network",
            "ok": False,
        }
    )
    unknown = json.dumps({"kind": "FromTheFuture", "timestamp": 2.0, "spec_id": "SA"})
    events_path.write_text(unknown + "\n" + known + "\n")
    assert read_log(tmp_path) == [
        Teardown(timestamp=1.0, spec_id="SA", step="network", ok=False)
    ]


def test_read_log_on_a_missing_file_returns_no_events(tmp_path):
    assert read_log(tmp_path / "nowhere") == []


def test_event_log_write_failure_raises_nothing(tmp_path):
    """A cell that cannot write its own log must not lose the caller to it."""
    unwritable = tmp_path / "not-a-directory"
    unwritable.write_text("occupied by a file, not a directory")
    log = EventLog(unwritable)  # events.jsonl would live *inside* a file
    log.append(
        Teardown(timestamp=1.0, spec_id="SA", step="container", ok=True)
    )  # does not raise


def test_event_log_appends_one_line_per_event(tmp_path):
    log = EventLog(tmp_path)
    log.append(Teardown(timestamp=1.0, spec_id="SA", step="container", ok=True))
    log.append(Teardown(timestamp=2.0, spec_id="SA", step="network", ok=True))
    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert all(json.loads(line)["kind"] == "Teardown" for line in lines)
