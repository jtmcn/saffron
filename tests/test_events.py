"""SA-0029: the host event vocabulary and its durable log. No emission, no
renderer — that is `SA-0030`/`SA-0031` and `SA-0040`. No network, no cell.
"""

from __future__ import annotations

import json
import typing
from dataclasses import fields as dc_fields

import pytest

from saffron.events import (
    _KINDS,
    Agent,
    Attempt,
    Baseline,
    Budget,
    Ceiling,
    Event,
    EventLog,
    GateResult,
    GateStatus,
    Phase,
    PhaseStart,
    Preflight,
    Teardown,
    Terminal,
    TerminalReason,
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
        phase="GATE",
        attempt=1,
        commits=2,
        spent_usd_est=1.5,
        new_failures=0,
        decision="green",
    ),
    GateResult(
        timestamp=5.0, spec_id="SA-0029", gate="lint", status="fail", against="attempt"
    ),
    Budget(timestamp=6.0, spec_id="SA-0029", ceiling="max_turns", value=141, limit=120),
    Agent(timestamp=7.0, spec_id="SA-0029", raw=False, event={"type": "text"}),
    Terminal(
        timestamp=8.0, spec_id="SA-0029", reason="finished_empty", spent_usd_est=0.5
    ),
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
    log.append(
        GateResult(
            timestamp=1.0, spec_id="SA", gate="tests", status="error", against="attempt"
        )
    )
    log.append(
        GateResult(
            timestamp=2.0, spec_id="SA", gate="tests", status="fail", against="attempt"
        )
    )
    statuses = [e.status for e in read_log(tmp_path)]
    assert statuses == ["error", "fail"]


def test_gate_result_carries_all_four_statuses(tmp_path):
    log = EventLog(tmp_path)
    for status in ("pass", "fail", "skip", "error"):
        log.append(
            GateResult(
                timestamp=1.0, spec_id="SA", gate="g", status=status, against="attempt"
            )
        )
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
            timestamp=1.0,
            spec_id="SA",
            reason="cut_off_no_salvage_room",
            spent_usd_est=9.0,
        ),
        Terminal(
            timestamp=2.0,
            spec_id="SA",
            reason="cut_off_salvage_failed",
            spent_usd_est=9.5,
        ),
        Terminal(
            timestamp=3.0,
            spec_id="SA",
            reason="ended_without_finishing",
            spent_usd_est=1.0,
            subtype="error",
            terminal_reason="api_error",
        ),
        Terminal(
            timestamp=4.0, spec_id="SA", reason="finished_empty", spent_usd_est=0.2
        ),
        Terminal(
            timestamp=5.0, spec_id="SA", reason="plan_rejected", spent_usd_est=0.1
        ),
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
    """Pinned by a hand-written line, not by the writer's own output."""
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "kind": "Attempt",
                "timestamp": 1735689600.0,
                "spec_id": "SA-0029",
                "phase": "GATE",
                "attempt": 1,
                "commits": 2,
                "spent_usd_est": 1.5,
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
        phase="GATE",
        attempt=1,
        commits=2,
        spent_usd_est=1.5,
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


# --- The criteria an independent review found were held up by a comment, and
# --- the two whole-file-loss defects it found by fuzzing (PR #91 review).


def test_a_gate_that_never_ran_records_no_failure_count(tmp_path):
    """`skip`/`error` never had a count computed, and `0` would be a lie.

    Mutating this back to `int = 0` left the suite green before this existed.
    """
    log = EventLog(tmp_path)
    log.append(
        GateResult(
            timestamp=1.0,
            spec_id="SA-0029",
            gate="types",
            status="skip",
            against="attempt",
        )
    )
    log.append(
        GateResult(
            timestamp=2.0,
            spec_id="SA-0029",
            gate="tests",
            status="fail",
            against="attempt",
            new_failures=0,
        )
    )
    skipped, failed = read_log(tmp_path)
    assert skipped.new_failures is None, "a skipped gate must not report a counted zero"
    assert failed.new_failures == 0, "a counted zero must survive as zero"
    assert skipped.new_failures != failed.new_failures


def test_a_gate_result_says_which_tree_it_ran_against(tmp_path):
    """Three trees emit these lines and one log holds all three."""
    log = EventLog(tmp_path)
    for against in ("baseline", "attempt", "rebuttal"):
        log.append(
            GateResult(
                timestamp=1.0,
                spec_id="SA-0029",
                gate="tests",
                status="pass",
                against=against,
            )
        )
    assert [e.against for e in read_log(tmp_path)] == [
        "baseline",
        "attempt",
        "rebuttal",
    ]


def test_an_attempt_names_its_phase(tmp_path):
    """CONTEXT.md: "'Attempt 3' without a phase is ambiguous — name both.\""""
    log = EventLog(tmp_path)
    log.append(
        Attempt(
            timestamp=1.0,
            spec_id="SA-0029",
            phase="REPAIR",
            attempt=3,
            commits=1,
            spent_usd_est=1.0,
        )
    )
    (loaded,) = read_log(tmp_path)
    assert (loaded.phase, loaded.attempt) == ("REPAIR", 3)


def test_the_enumerations_are_pinned(tmp_path):
    """`.saffron/gates/types` always skips, so a `Literal` is documentation
    unless something asserts its members."""
    assert typing.get_args(Ceiling) == ("budget_usd", "max_attempts", "max_turns")
    assert typing.get_args(GateStatus) == ("pass", "fail", "skip", "error")
    assert set(typing.get_args(Phase)) == {
        "DIAGNOSE",
        "IMPLEMENT",
        "GATE",
        "REPAIR",
        "REVIEW",
        "REBUT",
        "PACKAGE",
    }
    assert "PLAN" not in typing.get_args(Phase), (
        "CONTEXT.md's plan-checkpoint entry lists 'PLAN' on its own _Avoid_ line "
        "and says the checkpoint is deliberately not a phase"
    )
    assert len(typing.get_args(TerminalReason)) == 5


@pytest.mark.parametrize("event", _ONE_OF_EACH, ids=lambda e: type(e).__name__)
def test_the_wire_keys_are_pinned_for_every_kind(tmp_path, event):
    """`test_round_trips_every_kind` writes and reads with the same code, so a
    coordinated rename survives it. This reads the keys off the line."""
    EventLog(tmp_path).append(event)
    written = json.loads((tmp_path / "events.jsonl").read_text())
    assert set(written) == {"kind"} | {f.name for f in dc_fields(type(event))}
    assert "spent_usd" not in written, "DESIGN.md §4.1: a stored figure keeps _est"


def test_the_union_and_the_wire_table_cannot_drift(tmp_path):
    """Both are hand-maintained lists of the same nine kinds."""
    assert set(typing.get_args(Event)) == set(_KINDS.values())
    assert len(_KINDS) == 9
    for cls in _KINDS.values():
        assert "kind" not in {f.name for f in dc_fields(cls)}, "would clobber the tag"


def test_every_kind_is_frozen():
    for cls in _KINDS.values():
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} is not frozen"


def test_an_unhashable_kind_does_not_take_the_file_down(tmp_path):
    """`dict.get` raises TypeError on an unhashable key, losing the file."""
    good = json.dumps(
        {
            "kind": "Teardown",
            "timestamp": 1.0,
            "spec_id": "X",
            "step": "s",
            "ok": True,
            "detail": "",
        }
    )
    for bad in (
        '{"kind": ["a"]}',
        '{"kind": {"a": 1}}',
        '{"kind": 7}',
        '{"kind": null}',
    ):
        (tmp_path / "events.jsonl").write_text(f"{good}\n{bad}\n{good}\n")
        assert len(read_log(tmp_path)) == 2, f"{bad} cost the file its good events"


def test_a_field_a_newer_saffron_added_does_not_delete_the_event(tmp_path):
    """An added field must not delete every event of its kind."""
    v2 = json.dumps(
        {
            "kind": "Teardown",
            "timestamp": 2.0,
            "spec_id": "X",
            "step": "s",
            "ok": True,
            "detail": "",
            "added_by_a_later_saffron": 1,
        }
    )
    (tmp_path / "events.jsonl").write_text(v2 + "\n")
    (loaded,) = read_log(tmp_path)
    assert (loaded.step, loaded.ok) == ("s", True)


def test_a_line_missing_a_required_field_is_still_dropped(tmp_path):
    """The tolerance above must not become "accept anything"."""
    (tmp_path / "events.jsonl").write_text('{"kind": "Teardown", "timestamp": 1.0}\n')
    assert read_log(tmp_path) == []


def test_append_never_raises_on_a_dict_a_cell_authored(tmp_path):
    """`asdict` deep-copies before `json.dumps` is reached, and `Agent.event`
    comes from an untrusted cell."""
    # The shape a cell can actually emit, at a measured depth: `json.loads`
    # accepts it and `asdict`'s deepcopy cannot walk it. 500 is fine, 1000
    # raises — the recursion limit. `json.dumps` alone handles 5000, so
    # `asdict` is the only statement here that raises, which is why it moved
    # inside the try. A hand-built cycle is unreachable by contrast.
    deep = json.loads("[" * 1000 + "]" * 1000)
    log = EventLog(tmp_path)
    log.append(
        Agent(timestamp=1.0, spec_id="X", raw=False, event={"d": deep}, line=None)
    )
    assert log.failed, "a swallowed write must leave a breadcrumb"
    log.append(
        Agent(timestamp=2.0, spec_id="X", raw=False, event={"s": {1, 2}}, line=None)
    )
    log.append(Teardown(timestamp=3.0, spec_id="X", step="done", ok=True))
    assert [type(e).__name__ for e in read_log(tmp_path)] == ["Teardown"]
