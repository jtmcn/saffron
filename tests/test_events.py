"""SA-0029/SA-0040: the host event vocabulary, its durable log, and
`describe()` — the renderer that proves the nine kinds are sufficient for the
64 `watch(...)` call sites. `SA-0030` is the first real producer — the tests
from "The seam" heading down drive `saffron.cell.session.run_one_cell` for
real (stubbed runtime, no network, no cell) and read back what it emitted.
"""

from __future__ import annotations

import ast
import json
import re
import typing
from dataclasses import fields as dc_fields
from pathlib import Path

import pytest

from saffron.cell import runtime as _runtime
from saffron.cell import session
from saffron.events import (
    _KINDS,
    FAMILIES,
    FINDINGS,
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
    _describe_agent_event,
    describe,
    read_log,
)
from saffron.gates.contract import Failure
from saffron.phases import implement, review
from tests.test_session import (
    _HIDDEN_DIFF,
    _INTEGRITY_POLICY,
    _PLAN,
    _block,
    _drive,
    _grow_the_diff_after_the_first_turn,
    _results,
    _spec,
    _stub_the_runtime,
    _turn,
)


def _read[E: Event](tmp_path, kind: type[E]) -> list[E]:
    """`read_log` returns the `Event` union; every test here knows the kind it
    wrote. Narrowing at the read is what lets the `types` gate see an
    attribute read off the wrong kind — the union is the whole point of the
    module, so a test that reads it untyped gives that up."""
    narrowed: list[E] = []
    for event in read_log(tmp_path):
        assert isinstance(event, kind), f"log holds a {type(event).__name__}"
        narrowed.append(event)
    return narrowed


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
    statuses = [e.status for e in _read(tmp_path, GateResult)]
    assert statuses == ["error", "fail"]


def test_gate_result_carries_all_four_statuses(tmp_path):
    log = EventLog(tmp_path)
    for status in ("pass", "fail", "skip", "error"):
        log.append(
            GateResult(
                timestamp=1.0, spec_id="SA", gate="g", status=status, against="attempt"
            )
        )
    assert [e.status for e in _read(tmp_path, GateResult)] == [
        "pass",
        "fail",
        "skip",
        "error",
    ]


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
    loaded = _read(tmp_path, Budget)
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
    loaded = _read(tmp_path, Terminal)
    assert loaded == events
    assert len({e.reason for e in loaded}) == 5


def test_agent_raw_line_round_trips_still_marked_as_raw(tmp_path):
    """The quarantine is the point: a line that was not an event must survive
    the log still flagged `raw=True`, not only on the terminal."""
    log = EventLog(tmp_path)
    event = Agent(timestamp=1.0, spec_id="SA", raw=True, line="not json at all")
    log.append(event)
    [loaded] = _read(tmp_path, Agent)
    assert loaded.raw is True
    assert loaded == event


def test_agent_carries_a_parsed_dict_verbatim(tmp_path):
    log = EventLog(tmp_path)
    cell_event = {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}
    event = Agent(timestamp=1.0, spec_id="SA", raw=False, event=cell_event)
    log.append(event)
    [loaded] = _read(tmp_path, Agent)
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
    skipped, failed = _read(tmp_path, GateResult)
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
    assert [e.against for e in _read(tmp_path, GateResult)] == [
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
    (loaded,) = _read(tmp_path, Attempt)
    assert (loaded.phase, loaded.attempt) == ("REPAIR", 3)


def test_the_enumerations_are_pinned(tmp_path):
    """What the `types` gate cannot see, and why this stays beside it.

    Measured against the gate: a member *removed* from one of these literals
    fails both. A member quietly *added* fails only this — the gate is happy,
    because a wider literal breaks no existing call. And widening the field
    itself (`ceiling: Ceiling` to `ceiling: str`) is invisible to both, in any
    checker, because nothing exercises the wider value (BACKLOG item 39)."""
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
    (loaded,) = _read(tmp_path, Teardown)
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


# --- SA-0040: `describe()` and the mapping table ---------------------------

# One event per render branch `describe()` has — the exact-line proof
# `AC1` asks for. `test_every_family_has_a_kind_and_renders` below checks
# every kind used in `FAMILIES` appears at least once here.
_CASES: list[tuple[Event, str]] = [
    (
        Preflight(timestamp=1.0, spec_id="x", step="proxy_start", detail="up"),
        "preflight: up",
    ),
    (
        Preflight(timestamp=1.0, spec_id="x", step="cell_up", detail="c up"),
        "cell: c up",
    ),
    (
        Preflight(timestamp=1.0, spec_id="x", step="unstacked", detail="gone"),
        "unstacked: gone",
    ),
    (
        Baseline(timestamp=1.0, spec_id="x", gates=("lint",), statuses=("pass",)),
        "baseline: lint=pass",
    ),
    (
        # Both fields set, as the real call site leaves them: the gate-status
        # line always prints, and the aborted-gate line joins it as a second
        # line from the *same* event — never one or the other.
        Baseline(
            timestamp=1.0,
            spec_id="x",
            gates=("lint", "tests"),
            statuses=("pass", "error"),
            aborted=("tests",),
        ),
        "baseline: lint=pass, tests=error\n"
        "baseline errored in ['tests'] — the toolchain is broken, not the code",
    ),
    (
        PhaseStart(
            timestamp=1.0,
            spec_id="x",
            phase="IMPLEMENT",
            label="PLAN",
            detail="accepted, sha256 abc",
        ),
        "PLAN: accepted, sha256 abc",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="GATE",
            attempt=1,
            commits=0,
            spent_usd_est=0.0,
            aborted=("tests",),
        ),
        "gates: ['tests'] errored — infrastructure, not the task",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="GATE",
            attempt=1,
            commits=0,
            spent_usd_est=0.0,
            drift=("tests: pass->skip",),
        ),
        "gates: ['tests: pass->skip'] — distrusting the subtraction",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="GATE",
            attempt=2,
            commits=0,
            spent_usd_est=1.0,
            new_failures=1,
            decision="repair",
        ),
        "gates: attempt 2, 1 new failures -> repair",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="REBUT",
            attempt=1,
            commits=0,
            spent_usd_est=1.0,
            new_failures=0,
        ),
        "gates: 0 new failures after the rebuttal",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="IMPLEMENT",
            attempt=1,
            commits=3,
            spent_usd_est=1.5,
        ),
        "IMPLEMENT: 3 commit(s), $1.50 spent",
    ),
    (
        GateResult(
            timestamp=1.0, spec_id="x", gate="lint", status="pass", against="attempt"
        ),
        "gates: lint=pass",
    ),
    (
        Budget(timestamp=1.0, spec_id="x", ceiling="budget_usd", value=9.0, limit=9.0),
        "budget: $9.00 of $9.00 — stopping",
    ),
    (Agent(timestamp=1.0, spec_id="x", raw=True, line="oops"), "agent: (raw) oops"),
    (
        Agent(
            timestamp=1.0,
            spec_id="x",
            raw=False,
            event={"type": "error", "error": "boom"},
        ),
        "agent: error boom",
    ),
    (
        Agent(
            timestamp=1.0,
            spec_id="x",
            raw=False,
            detail="reaped the cell after the kill",
        ),
        "agent: reaped the cell after the kill",
    ),
    (
        Terminal(
            timestamp=1.0,
            spec_id="x",
            reason="cut_off_no_salvage_room",
            spent_usd_est=9.0,
            detail="$9.00 of $9.00",
        ),
        "budget: $9.00 of $9.00 — cut off at the turn ceiling with nothing "
        "committed, no room left to salvage",
    ),
    (
        Terminal(
            timestamp=1.0,
            spec_id="x",
            reason="cut_off_salvage_failed",
            spent_usd_est=9.5,
        ),
        "SALVAGE: cut off and could not be salvaged, $9.50 spent",
    ),
    (
        Terminal(
            timestamp=1.0,
            spec_id="x",
            reason="ended_without_finishing",
            spent_usd_est=1.0,
            subtype="error",
            terminal_reason="api_error",
        ),
        "IMPLEMENT: the turn ended without finishing and produced nothing "
        "(error/api_error)",
    ),
    (
        Terminal(
            timestamp=1.0, spec_id="x", reason="finished_empty", spent_usd_est=0.2
        ),
        "IMPLEMENT: finished and produced nothing",
    ),
    (
        Terminal(
            timestamp=1.0,
            spec_id="x",
            reason="plan_rejected",
            spent_usd_est=0.1,
            detail="not the schema",
        ),
        "PLAN: rejected, $0.10 spent — not the schema",
    ),
    (Teardown(timestamp=1.0, spec_id="x", step="start", ok=True), "teardown"),
    (
        Teardown(
            timestamp=1.0,
            spec_id="x",
            step="export",
            ok=True,
            detail="exported 42 bytes to /x/patch.diff",
        ),
        "teardown: exported 42 bytes to /x/patch.diff",
    ),
]


@pytest.mark.parametrize(
    "event,expected",
    _CASES,
    ids=lambda v: (
        getattr(v, "__class__", type(v)).__name__ if not isinstance(v, str) else v[:24]
    ),
)
def test_describe_renders_every_kind_and_variant(event, expected):
    """AC1: `describe(event)` is the exact line the call site prints today,
    for every kind and every render branch — never a `type` string switch."""
    assert describe(event) == expected


def test_every_family_has_a_kind_and_renders():
    """AC2: every row in the module's own table names a real kind, and that
    kind is proven to render by `_CASES` above."""
    kinds_with_a_render_example = {type(event) for event, _ in _CASES}
    assert kinds_with_a_render_example == set(_KINDS.values())
    for family in FAMILIES:
        assert family.kind in _KINDS.values(), family.prefix


def test_every_row_cites_a_file_and_symbol_that_exist():
    """AC2, the half the assertion above cannot make. `family.kind in
    _KINDS.values()` is true of *any* row carrying any of the nine types, so
    the table could cite anything: a row reading
    `_Family("QQQQ", "no/such/file.py:nope", Teardown)` passed every check
    here. Resolve each citation instead — the file exists, and the symbol is
    defined in it."""
    root = Path(__file__).resolve().parents[1] / "saffron"
    cited = {(f.prefix, f.where) for f in FAMILIES}
    cited |= {(prefix, where) for prefix, where, _ in FINDINGS}
    for prefix, where in sorted(cited):
        rel, _, symbol = where.partition(":")
        path = root / rel
        assert path.exists(), f"{prefix!r} cites a file that does not exist: {rel}"
        defined = {
            node.name
            for node in ast.walk(ast.parse(path.read_text()))
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        }
        assert symbol in defined, f"{prefix!r} cites {rel}, which defines no {symbol}"


def test_the_table_did_not_quietly_lose_a_row():
    """AC2 again, and the mutation neither assertion above catches: deleting
    three rows — `unstacked:`, `baseline errored in`, `PACKAGE: (pr_url)` —
    left every test in this file passing. The table is the proof the nine
    kinds cover all 64 call sites and is what `SA-0030`/`SA-0031` read to find
    their work, so losing a row silently is the failure that matters.

    `SA-0030` and `SA-0031` migrate these call sites and will move this count.
    That is the point: moving it is a deliberate edit, not a silent one."""
    assert len(FAMILIES) == 57
    assert len({f.prefix for f in FAMILIES}) == 57


def test_the_duplicated_agent_renderer_still_matches_its_original():
    """`_describe_agent_event` was duplicated as `phases.implement._describe`,
    kept in step by nothing but a test. `SA-0041` deletes the copy, so this
    test's job changed: there is no longer a second renderer to compare
    against, and comparing `describe(Agent(event=e))` to
    `_describe_agent_event(e)` asserts nothing — `describe`'s Agent branch
    *is* `return _describe_agent_event(event.event)`, so that reads
    `f(e) == f(e)` and cannot fail. Measured: rewriting the `rate_limit` and
    `result` branches left 1156 tests passing.

    That matters more now than before. While `Agent.event` was always `None`
    this renderer was unreachable in production; it is now the sole renderer
    for every `agent:` line an operator sees and every one `events.jsonl`
    keeps, and the golden fixture excludes all of them by construction. So
    each branch is pinned to the literal line it must produce.
    """
    cases = [
        ({"type": "text", "text": "  a   b  "}, "agent: a b"),
        # The 160/120 bounds are the whole reason a cell's output is safe to
        # print: pin them, or shortening one is invisible. Measured — with
        # only the short case above, `text[:160]` -> `text[:80]` passed.
        ({"type": "text", "text": "x" * 400}, "agent: " + "x" * 160),
        (
            {"type": "tool_use", "name": "Bash", "input": {"command": "y" * 400}},
            "agent: Bash " + json.dumps({"command": "y" * 400})[:120],
        ),
        (
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
            'agent: Bash {"command": "ls"}',
        ),
        ({"type": "tool_result", "is_error": False}, "agent: tool ok"),
        ({"type": "tool_result", "is_error": True}, "agent: tool error"),
        (
            {
                "type": "result",
                "subtype": "success",
                "num_turns": 3,
                "total_cost_usd": 0.5,
                "terminal_reason": None,
            },
            "agent: success in 3 turns, $0.5 (None)",
        ),
        ({"type": "rate_limit", "status": "allowed"}, "agent: rate limit allowed"),
        (
            {"type": "rate_limit", "status": "rejected", "utilization": 0.5},
            "agent: rate limit rejected, 50% used",
        ),
        ({"type": "error", "error": "boom"}, "agent: error boom"),
        (
            {"type": "system", "subtype": "thinking_tokens"},
            "agent: system thinking_tokens",
        ),
        ({"type": "unknown_to_both"}, "agent: unknown_to_both"),
    ]
    for event, expected in cases:
        assert _describe_agent_event(event) == expected, event
        # And the wrapped form an operator actually meets renders identically.
        assert (
            describe(Agent(timestamp=1.0, spec_id="x", raw=False, event=event))
            == expected
        )

    # `resets_at` renders a local clock time, so only its stable half is
    # pinned; `_when`'s own formatting is covered by its call sites above.
    resets = _describe_agent_event(
        {"type": "rate_limit", "status": "rejected", "resets_at": 1_700_000_000}
    )
    assert resets.startswith("agent: rate limit rejected, resets ")
    assert resets != "agent: rate limit rejected, resets "


def test_findings_name_what_the_table_could_not_type():
    """The two call-site shapes `FAMILIES` refused to force into a
    `message: str` are named, not silently dropped."""
    assert len(FINDINGS) == 2
    for prefix, where, note in FINDINGS:
        assert prefix and where and note


# --- The fixture's normaliser -----------------------------------------------

_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_PATCH_PATH = re.compile(r"\S*/patch\.diff\b")
_PROMPT_CHARS = re.compile(r"system prompt \d+ chars")


def _normalise(line: str) -> str:
    """What the fixture's capture and its assertion both run every line
    through. Three things move between hosts and runs and nothing else does:
    the LAN address `preflight.probe_addresses()` reports (the stable gateway
    is left alone), pytest's absolute `tmp_path` ahead of `patch.diff`, and a
    system prompt's `CONTEXT.md`-dependent character count."""
    line = _IPV4.sub(
        lambda m: m.group(0) if m.group(0) == _runtime.GATEWAY else "<LAN-ADDR>", line
    )
    line = _PATCH_PATH.sub("<TASK_DIR>/patch.diff", line)
    return _PROMPT_CHARS.sub("system prompt <N> chars", line)


def test_normalise_replaces_exactly_the_three_volatile_substrings():
    port_line = (
        f"preflight: probing 1 host ports at {_runtime.GATEWAY}, 192.168.1.42; "
        "tolerating nothing"
    )
    assert _normalise(port_line) == (
        f"preflight: probing 1 host ports at {_runtime.GATEWAY}, <LAN-ADDR>; "
        "tolerating nothing"
    )
    path_line = "teardown: exported 12 bytes to /tmp/xyz/out/SY-1/patch.diff"
    assert (
        _normalise(path_line) == "teardown: exported 12 bytes to <TASK_DIR>/patch.diff"
    )
    prompt_line = "IMPLEMENT: system prompt 4821 chars"
    assert _normalise(prompt_line) == "IMPLEMENT: system prompt <N> chars"
    untouched = "REVIEW: no blockers, 0 concern(s)"
    assert _normalise(untouched) == untouched
    assert _normalise(_normalise(untouched)) == _normalise(untouched)


# --- The golden fixture: driven, not typed ----------------------------------
#
# AC6. `SA-0030` and `SA-0031` are specified to trust this file, so what it
# does *not* prove is stated at the granularity that matters — the render
# branch, not the kind. A kind appearing here does not mean its branches do.
#
# Captured: `preflight:` (4 of 5 steps), `cell:`, `baseline:` (the joined
# line only), `PLAN: accepted`, `IMPLEMENT: system prompt`, `IMPLEMENT: N
# commit(s)`, `gates: attempt N …` (green, repair, no-progress), `REVIEW:`
# per-lens and summary, the outcome line, `teardown` and `teardown: exported
# N bytes`.
#
# Not captured, because the harness monkeypatches the agent and never touches
# a real cell: `agent:` in every form; `SCOPE:`/`SCOPE_REVIEW:`; `SALVAGE:`;
# `REPAIR:`; `REBUT:`; `unstacked:`; and every `PACKAGE:` line, which runs
# after `run_one_cell` returns.
#
# Not captured though the kind above it is — the gaps easiest to mistake for
# coverage:
#   * `GateResult` entirely. No call site prints one alone; it renders for a
#     future consumer (`SA-0036`) and this file proves nothing about it.
#   * `Baseline`'s `aborted` variant — both driven runs have every declared
#     gate report, so the second `baseline errored in [...]` line never
#     appears. Proven only by the `describe` case above.
#   * `Attempt`'s `aborted`, `drift` and `after the rebuttal` branches.
#   * every `PLAN:` branch except `accepted`, and both `IMPLEMENT:` session
#     failures (`the session failed`, `cut off … spending one turn`).
#   * `Budget`'s stopping line and all five `Terminal` reasons.
#   * every `teardown:` line except `exported N bytes` — no `no commits`, no
#     `patch export FAILED`, no `commit subjects unreadable`, no `proxy
#     DENIED`/`FAILED`, no `survived`.


def _golden_fixture_path() -> Path:
    return Path(__file__).parent / "fixtures" / "watch-golden.txt"


def test_watch_output_matches_the_golden_fixture(monkeypatch, tmp_path):
    cell_a = _stub_the_runtime(monkeypatch, suites=([], []))
    outcome_a, _ = _drive(
        monkeypatch, tmp_path / "a", cell=cell_a, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome_a.state == "READY_FOR_REVIEW"

    failing = Failure(file="a.py", code="E501", message="too long")
    cell_b = _stub_the_runtime(
        monkeypatch, suites=([], _results(failing), _results(failing))
    )
    outcome_b, _ = _drive(
        monkeypatch,
        tmp_path / "b",
        cell=cell_b,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
    )
    assert outcome_b.state == "EXHAUSTED"

    captured = "\n".join(
        [
            "# green: PLAN -> IMPLEMENT -> gates green -> REVIEW",
            *(_normalise(line) for line in cell_a.watched),
            "",
            "# failing gate, repaired once, then no-progress -> EXHAUSTED",
            *(_normalise(line) for line in cell_b.watched),
        ]
    )
    assert captured == _golden_fixture_path().read_text().rstrip("\n")


# --- The join: `describe` against lines the fixture actually captured -------
#
# `_CASES` above are literals, typed beside the code that produces them; the
# fixture is captured from real `watch(...)` call sites. Nothing compared the
# two, so `describe` could drift from `cell/session.py` and every test here
# stayed green — measured: rewriting the `gates: attempt …` branch and its
# `_CASES` literal together passed 67 tests. That is the one drift `SA-0030`
# cannot survive, because it replaces those call sites with
# `watch(describe(event))` and its only acceptance criterion is that the
# output does not change. Asserting the line is one the fixture *carries*, and
# that `describe` reproduces it, is what ties the two halves of this spec
# together.
#
# Not joinable, and deliberately absent: the normalised lines (`<LAN-ADDR>`,
# `<N>`, `<TASK_DIR>`), where `describe` renders the real value the normaliser
# replaced; and `{outcome}: $N spent, session …`, which `FINDINGS[0]` records
# as needing a tenth kind.
_JOINED: tuple[tuple[Event, str], ...] = (
    (
        Preflight(
            timestamp=1.0, spec_id="x", step="proxy", detail="starting the proxy"
        ),
        "preflight: starting the proxy",
    ),
    (
        Preflight(
            timestamp=1.0,
            spec_id="x",
            step="upstream",
            detail="proxy reaches api.anthropic.com (401)",
        ),
        "preflight: proxy reaches api.anthropic.com (401)",
    ),
    (
        Preflight(
            timestamp=1.0,
            spec_id="x",
            step="image",
            detail="building saffron/cell:repo",
        ),
        "preflight: building saffron/cell:repo",
    ),
    (
        Preflight(
            timestamp=1.0,
            spec_id="x",
            step="cell_up",
            detail="saffron-cell-SY-1 up, worktree at bbbbbbbb",
        ),
        "cell: saffron-cell-SY-1 up, worktree at bbbbbbbb",
    ),
    (
        Baseline(
            timestamp=1.0,
            spec_id="x",
            gates=("scope", "integrity", "size", "committed", "census", "criteria"),
            statuses=("pass", "skip", "pass", "pass", "skip", "skip"),
        ),
        "baseline: scope=pass, integrity=skip, size=pass, committed=pass, "
        "census=skip, criteria=skip",
    ),
    (
        PhaseStart(
            timestamp=1.0,
            spec_id="x",
            phase="IMPLEMENT",
            label="PLAN",
            detail="accepted, sha256 841501830587",
        ),
        "PLAN: accepted, sha256 841501830587",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="IMPLEMENT",
            attempt=1,
            commits=1,
            spent_usd_est=0.2,
        ),
        "IMPLEMENT: 1 commit(s), $0.20 spent",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="GATE",
            attempt=1,
            commits=0,
            spent_usd_est=0.0,
            new_failures=0,
            decision="green",
        ),
        "gates: attempt 1, 0 new failures -> green",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="GATE",
            attempt=1,
            commits=0,
            spent_usd_est=0.0,
            new_failures=1,
            decision="repair",
        ),
        "gates: attempt 1, 1 new failures -> repair",
    ),
    (
        Attempt(
            timestamp=1.0,
            spec_id="x",
            phase="GATE",
            attempt=2,
            commits=0,
            spent_usd_est=0.0,
            new_failures=1,
            decision="no-progress",
        ),
        "gates: attempt 2, 1 new failures -> no-progress",
    ),
    (
        PhaseStart(
            timestamp=1.0,
            spec_id="x",
            phase="REVIEW",
            label="REVIEW",
            detail="correctness: 0 blocker, 0 concern, 0 note, drop rate 0% of 0, $0.10",
        ),
        "REVIEW: correctness: 0 blocker, 0 concern, 0 note, drop rate 0% of 0, $0.10",
    ),
    (
        PhaseStart(
            timestamp=1.0,
            spec_id="x",
            phase="REVIEW",
            label="REVIEW",
            detail="contract: 0 blocker, 0 concern, 0 note, drop rate 0% of 0, $0.10",
        ),
        "REVIEW: contract: 0 blocker, 0 concern, 0 note, drop rate 0% of 0, $0.10",
    ),
    (
        PhaseStart(
            timestamp=1.0,
            spec_id="x",
            phase="REVIEW",
            label="REVIEW",
            detail="no blockers, 0 concern(s)",
        ),
        "REVIEW: no blockers, 0 concern(s)",
    ),
    (
        Teardown(timestamp=1.0, spec_id="x", step="start", ok=True),
        "teardown",
    ),
)


@pytest.mark.parametrize("event,line", _JOINED)
def test_describe_reproduces_a_line_the_fixture_captured(event, line):
    """AC1 + AC3, joined. The expected string must be a line the capture
    really produced — not one typed here — and `describe` must reproduce it
    exactly."""
    captured = _golden_fixture_path().read_text().splitlines()
    assert line in captured, f"not a captured line: {line!r}"
    assert describe(event) == line


def test_the_join_covers_every_captured_line_a_kind_renders():
    """A join that silently shrinks proves less each time it is edited. Every
    fixture line is either joined above, normalised, or named in `FINDINGS`;
    nothing else is allowed to go unchecked."""
    captured = [
        line
        for line in _golden_fixture_path().read_text().splitlines()
        if line and not line.startswith("#")
    ]
    joined = {line for _, line in _JOINED}
    unchecked = [
        line
        for line in captured
        if line not in joined
        and "<" not in line
        and not re.match(r"^(READY_FOR_REVIEW|EXHAUSTED):", line)
    ]
    assert unchecked == [], f"captured but joined to no kind: {unchecked}"


# --- The seam: SA-0030 drives run_one_cell for real ------------------------
#
# Everything above proves `describe()` is sufficient once an `Event` exists.
# These five drive `saffron.cell.session.run_one_cell` — the same stubbed
# runtime `tests/test_session.py` uses everywhere, no network, no cell — to
# prove something actually constructs one now.


def test_run_one_cell_with_no_emit_argument_still_prints(monkeypatch, tmp_path, capsys):
    """AC3: `cli.py` is forbidden to this spec and never passes `emit` — every
    direct caller today gets `run_one_cell`'s default, which must still print
    for the operator watching, exactly as the golden fixture's own run does."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        use_default_emit=True,
    )
    assert outcome.state == "READY_FOR_REVIEW"
    printed = capsys.readouterr().out
    assert "preflight: starting the proxy" in printed
    assert "READY_FOR_REVIEW: $0.40 spent, session sess-1" in printed


def test_events_jsonl_reproduces_what_the_terminal_printed(
    monkeypatch, tmp_path, capsys
):
    """AC4: the default `emit` fans out to both consumers, and `read_log` +
    `describe` must reproduce the same sequence `capsys` captured — except
    the two lines `events.FINDINGS[0]` names, which `session._drive_cell`
    prints directly rather than forcing into a tenth kind, and which the join
    test above already excludes from every other kind-level check the same
    way (`re.match(r"^(READY_FOR_REVIEW|EXHAUSTED):", line)`)."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        use_default_emit=True,
    )
    assert outcome.state == "READY_FOR_REVIEW"
    printed = [line for line in capsys.readouterr().out.split("\n") if line]
    without_outcome = [
        line
        for line in printed
        if not re.match(r"^(READY_FOR_REVIEW|EXHAUSTED):", line)
    ]
    logged = [
        line
        for event in read_log(tmp_path / "out" / "SY-1")
        for line in describe(event).split("\n")
        if line
    ]
    assert without_outcome == logged

    # `spec_id` is written at 21 sites in `session.py` and read by no test:
    # measured, replacing every one with a wrong literal passed all 1149.
    # `describe` never renders it, so the golden fixture cannot cover it
    # either, and today the log's own path makes it redundant. `SA-0042`
    # gives `cli.py` one fan-out across a task's phases, at which point this
    # field is the only thing saying which task a row belongs to.
    assert {event.spec_id for event in read_log(tmp_path / "out" / "SY-1")} == {"SY-1"}


def test_a_gate_error_is_recorded_distinctly_from_a_gate_failure(monkeypatch, tmp_path):
    """AC6: `error` — the gate itself broke — must never blur into `fail`,
    the repo's code being wrong. `Attempt.aborted` (an errored gate) and
    `Attempt.new_failures`/`decision` (a real failure, repaired or not) are
    the two shapes `repair_loop` never lets collide on one event; this is
    what proves the *events* carry the distinction, not just the line."""
    errored: list[Event] = []
    cell = _stub_the_runtime(monkeypatch)
    _grow_the_diff_after_the_first_turn(monkeypatch, cell, big=_HIDDEN_DIFF)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(spec_type="bug"),
        policy=_INTEGRITY_POLICY,
        capture=errored,
    )
    assert outcome.state == "GATE_ERROR"
    (error_attempt,) = [e for e in errored if isinstance(e, Attempt) and e.aborted]
    assert error_attempt.aborted == ("integrity",)
    assert error_attempt.new_failures is None
    assert error_attempt.decision is None

    failing = Failure(file="a.py", code="E501", message="too long")
    failed: list[Event] = []
    cell_b = _stub_the_runtime(
        monkeypatch, suites=([], _results(failing), _results(failing))
    )
    outcome_b, _ledger_b = _drive(
        monkeypatch,
        tmp_path / "b",
        cell=cell_b,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
        capture=failed,
    )
    assert outcome_b.state == "EXHAUSTED"
    (fail_attempt,) = [
        e for e in failed if isinstance(e, Attempt) and e.decision == "no-progress"
    ]
    assert fail_attempt.aborted == ()
    assert fail_attempt.new_failures == 1


def test_an_unwritable_event_log_does_not_abort_the_run(monkeypatch, tmp_path):
    """AC7: `EventLog.append` never raises, and neither does a disk-full
    night take the run down with it. `events.jsonl` pre-created as a
    directory breaks only the log's own write — `open(path, "a")` raises
    `IsADirectoryError`, caught by `EventLog.append`'s own `except (OSError,
    ...)` — while every other `task_dir` file the run writes is untouched."""
    cell = _stub_the_runtime(monkeypatch)
    task_dir = tmp_path / "out" / "SY-1"
    task_dir.mkdir(parents=True)
    (task_dir / "events.jsonl").mkdir()
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        use_default_emit=True,
    )
    assert outcome.state == "READY_FOR_REVIEW"
    assert (task_dir / "baseline.json").is_file()
    assert (task_dir / "plan.json").is_file()
    assert (task_dir / "events.jsonl").is_dir()


def test_the_supervisor_binds_every_required_argument_of_run_agent():
    """`implement.run_agent` is monkeypatched in every `_drive` test, so the
    seam between the supervisor and its real signature is invisible to the
    whole suite. Measured: deleting `spec_id=spec.spec_id` from the
    `partial(implement.run_agent, ...)` leaves 1156 tests **and** `ty check`
    green, and in production raises `TypeError: missing 1 required
    keyword-only argument` on the PLAN turn of every run — after the proxy,
    the image build and the worktree have already been paid for.

    Read statically, because the only way to exercise it dynamically is to
    stop stubbing the function the tests exist to stub."""
    import ast
    import inspect

    required = {
        name
        for name, param in inspect.signature(implement.run_agent).parameters.items()
        if param.kind is param.KEYWORD_ONLY and param.default is param.empty
    }
    # `record_attempts` supplies these per call; the partial supplies the rest.
    per_call = {"prompt", "options"}
    tree = ast.parse(Path(session.__file__).read_text())
    partials = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and node.args
        and ast.unparse(node.args[0]) == "implement.run_agent"
    ]
    assert partials, "no partial(implement.run_agent, ...) in session.py"
    for call in partials:
        bound = {kw.arg for kw in call.keywords if kw.arg}
        missing = required - per_call - bound
        assert not missing, f"partial does not bind {sorted(missing)}"


def test_every_spec_id_the_supervisor_passes_comes_from_the_spec():
    """Third instance of one defect tonight: `repair_loop`'s `spec_id` was
    defaultable, the `run_agent` partial's was droppable, and `run_rebut`'s can
    be set to `""` with 1156 tests still green. Each was found by a different
    reviewer and patched separately.

    They share a shape — a required argument whose *value* nothing reads —
    and the events it labels are how `SA-0042`'s single fan-out will tell one
    task's rows from another's in a shared log. Checked structurally because
    the dynamic version needs a test per call site, which is what let the
    third one through."""
    import ast

    tree = ast.parse(Path(session.__file__).read_text())
    literals = [
        ast.unparse(kw.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "spec_id" and not isinstance(kw.value, ast.Name | ast.Attribute)
    ]
    assert literals == [], f"spec_id passed as a literal: {literals}"


def test_the_supervisor_hands_the_adapter_to_the_agent_it_calls(monkeypatch, tmp_path):
    """AC8's other half, which the isolated test below cannot reach: it proves
    `_phase_watch` renders correctly, not that `session.py` threads it into
    anything. Measured — replacing `watch=` with a live no-op at all six
    `agent(...)` call sites, so every `agent:` line during PLAN, IMPLEMENT,
    SALVAGE and REPAIR vanishes from the terminal *and* `events.jsonl`, left
    218 tests passing. The golden fixture cannot catch it either: its harness
    stubs the agent and captures no `agent:` line, which its own header
    records.

    Four *calls*, not four of the six `agent(...)` sites. A green run reaches
    two of those — `plan_checkpoint`'s turn and `_drive_cell`'s IMPLEMENT turn
    — and the other two calls arrive through `review.run_review`, one per
    lens, which is a `watch=` site rather than an `agent(...)` one. SALVAGE and
    REPAIR are reached only by a failing run: `test_the_repair_seam_is_also_
    threaded` below drives one. The `REVIEW:`/`REBUT:` *lines* are covered by
    the golden fixture instead.
    """
    spoken = 'agent: Bash {"command": "ls"}'
    cell = _stub_the_runtime(monkeypatch, suites=([], []))
    outcome, _ = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        agent_says=spoken,
    )
    assert outcome.state == "READY_FOR_REVIEW"
    # Exact, not `>= 1`: the count is the number of seams exercised, and a
    # migration that drops one should fail here rather than pass quietly.
    # Derived, not hard-coded: two turns plus one session per lens. `4` reads
    # as a constant and is not one — `review.LENSES` has two entries beside a
    # `ponytail:` saying a third is an open question, and adding it would fail
    # this test for a change that has nothing to do with the seam.
    assert cell.watched.count(spoken) == 2 + len(review.LENSES), cell.watched


def test_the_repair_seam_is_also_threaded(monkeypatch, tmp_path):
    """The sibling above drives a green run, which never reaches the SALVAGE or
    REPAIR `agent(...)` sites. Measured: severing `watch=` at only those two
    left 1129 tests passing, so every `agent:` line during REPAIR — the phase
    an operator most needs to watch — could vanish from the terminal and the
    log unnoticed. A failing run reaches REPAIR, so it is witnessed here."""
    spoken = 'agent: Bash {"command": "pytest"}'
    failing = Failure(file="a.py", code="E501", message="too long")
    cell = _stub_the_runtime(
        monkeypatch, suites=([], _results(failing), _results(failing))
    )
    outcome, _ = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
        agent_says=spoken,
    )
    assert outcome.state == "EXHAUSTED"
    # The plan turn, IMPLEMENT, and one REPAIR turn per failed attempt. No
    # lens runs: REVIEW is never reached on a red loop.
    assert cell.watched.count(spoken) == 3, cell.watched


def _lines_from_cell(*raw_lines: str):
    """A minimal `exec_stream` double: hands each line to `on_line`, in order,
    then reports a clean exit — enough to drive `implement.run_agent` without
    a real cell."""

    def _exec(container, command, *, stdin_data, on_line, **kwargs):
        for line in raw_lines:
            on_line(line)
        return _runtime.Completed(0, "", "")

    return _exec


def _scripted_agent(*texts: str):
    """`Callable[..., implement.AttemptResult]`: one canned turn per text, for
    driving `review.run_review`/`rebut.run_rebut` without a real agent."""
    scripted = iter(texts)

    def run(container, *, prompt, options, **kwargs):
        return _turn(next(scripted))

    return run


def test_the_watch_shaped_callable_phases_still_receive_does_not_raise():
    """`_phase_watch` used to recover a typed event from a line
    `phases/implement.py`, `phases/review.py` and `phases/rebut.py` had
    already rendered to prose, by matching its prefix. There is no adapter
    left to test — those three files construct `Agent`/`PhaseStart` events
    directly now, at the point the dict or the fact is still available, and
    `describe()` of what they construct is what used to be asserted here
    byte for byte. Each of the four lines below is a real call site, driven
    directly, not decoded from a hand-written string — the same "receives an
    event-shaped callable and does not raise" property this test's name
    promises, proven the other way around now that there is no longer a
    watch-shaped one to feed it (SA-0041)."""
    from saffron.agents.findings import Finding
    from saffron.phases import implement, rebut

    prompts_dir = Path(review.__file__).resolve().parents[1] / "agents" / "prompts"
    context_md = (Path(review.__file__).resolve().parents[2] / "CONTEXT.md").read_text()
    diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n"

    # "agent: (raw) ..." and "agent: Bash ..." — implement.run_agent's own
    # _consume, fed a non-JSON line and a real cell event.
    implement_captured: list[Event] = []
    implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="s",
        emit=implement_captured.append,
        exec_stream=_lines_from_cell(
            "some stray stdout",
            json.dumps(
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}
            ),
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "num_turns": 1,
                    "total_cost_usd": 0.1,
                    "session_id": "s1",
                    "terminal_reason": "completed",
                    "is_error": False,
                }
            ),
        ),
    )
    implement_lines = [describe(e) for e in implement_captured]
    assert "agent: (raw) some stray stdout" in implement_lines
    assert 'agent: Bash {"command": "ls"}' in implement_lines

    # "REVIEW: ..." — review.run_review's own PhaseStart, one clean lens.
    review_captured: list[Event] = []
    review.run_review(
        "cell",
        diff=diff,
        read_head=lambda _p: None,
        spec_body="fix it",
        gates="",
        context_md=context_md,
        prompts_dir=prompts_dir,
        max_turns=5,
        budget_usd=1.0,
        agent=_scripted_agent(_block({"findings": []}), _block({"findings": []})),
        spec_id="s",
        emit=review_captured.append,
    )
    review_lines = [describe(e) for e in review_captured]
    assert (
        "REVIEW: correctness: 0 blocker, 0 concern, 0 note, drop rate 0% of 0, $0.10"
        in review_lines
    )

    # "REBUT: ..." — rebut.run_rebut's own PhaseStart, one fixed blocker.
    rebut_captured: list[Event] = []
    blocker = Finding(
        lens="correctness",
        severity="blocker",
        file="x.py",
        line=1,
        claim="c",
        anchored=True,
    )
    options = implement.agent_options(system_prompt="s", max_turns=5, budget_usd=1.0)
    rebut.run_rebut(
        "cell",
        blockers=[blocker],
        options=options,
        session_id="sess-1",
        spec_body="fix it",
        context_md=context_md,
        prompts_dir=prompts_dir,
        max_turns=5,
        budget_usd=1.0,
        head_moved=lambda: True,
        rerun_gates=lambda: None,
        diff=lambda: diff,
        agent=_scripted_agent(
            "ok",
            _block(
                {"rebuttals": [{"finding": 1, "action": "fixed", "argument": "done"}]}
            ),
            _block(
                {"verdicts": [{"finding": 1, "verdict": "withdrawn", "reason": "ok"}]}
            ),
        ),
        spec_id="s",
        emit=rebut_captured.append,
    )
    rebut_lines = [describe(e) for e in rebut_captured]
    assert "REBUT: 1 rebuttal(s), HEAD moved" in rebut_lines


def _identifier_watch_appears(source: str) -> bool:
    """Structural, not textual: a docstring saying `watch=` for history's
    sake (this file has several) must not make the check below pass by
    accident. `watch` as a parameter name, a call keyword, or a bare name
    reference are the only three shapes the old seam could have left behind;
    a string literal is none of them."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.arg) and node.arg == "watch":
            return True
        if isinstance(node, ast.keyword) and node.arg == "watch":
            return True
        if isinstance(node, ast.Name) and node.id == "watch":
            return True
    return False


def test_no_phase_this_spec_owns_still_takes_a_watch():
    """Every `watch(...)` in these three files is an `emit(<Event>)` now, and
    none of the three carries a `watch` parameter — checked structurally so a
    prose mention of the old name cannot pass this by accident."""
    root = Path(__file__).resolve().parents[1] / "saffron" / "phases"
    for name in ("implement.py", "review.py", "rebut.py"):
        source = (root / name).read_text()
        assert not _identifier_watch_appears(source), name


def test_the_supervisor_no_longer_adapts_events_to_prose():
    """`_phase_watch` existed only to adapt `emit` to the `watch(str)` these
    three phases used to expect. Both constructions — `plan_checkpoint`'s and
    `_drive_cell`'s — are gone along with the function itself: checked by
    attribute absence, and by a source scan so a reintroduction under the
    same name anywhere in the module still fails this, not only a call site
    this test happened to look at."""
    assert not hasattr(session, "_phase_watch")
    source = Path(session.__file__).read_text()
    assert "_phase_watch" not in source


def test_a_driven_agent_turn_logs_the_event_not_its_rendering():
    """`Agent.event` carries the parsed cell event dict verbatim again.
    `SA-0030`'s adapter was handed a string `_consume` had already rendered,
    so every per-turn line landed in `Agent.detail` as prose and `Agent.event`
    was permanently `None` — the inverse of what `events.Agent` documents.
    Driven through the real call site, not constructed by hand, so this
    fails if `_consume` ever goes back to rendering before it emits."""
    from saffron.phases import implement

    captured: list[Event] = []
    implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="s",
        emit=captured.append,
        exec_stream=_lines_from_cell(
            json.dumps(
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}
            ),
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "num_turns": 1,
                    "total_cost_usd": 0.1,
                    "session_id": "s1",
                    "terminal_reason": "completed",
                    "is_error": False,
                }
            ),
        ),
    )
    (tool_use,) = [
        e
        for e in captured
        if isinstance(e, Agent) and e.event and e.event.get("type") == "tool_use"
    ]
    assert tool_use.event == {
        "type": "tool_use",
        "name": "Bash",
        "input": {"command": "ls"},
    }
    assert tool_use.raw is False
    assert tool_use.detail == ""


def test_an_unknown_cell_event_kind_does_not_raise(tmp_path):
    """The runner degrades to a `passthrough`-shaped dict for a message shape
    it has never seen, rather than asserting (`test_an_unknown_message_
    passes_through_rather_than_crashing` in `test_agent_runner.py`). The host
    side has to match: an unknown `type` must still reach `describe()` and
    `EventLog.append` without raising."""
    from saffron.phases import implement

    captured: list[Event] = []
    implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="s",
        emit=captured.append,
        exec_stream=_lines_from_cell(
            json.dumps({"type": "something_nobody_has_seen_before"}),
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "num_turns": 1,
                    "total_cost_usd": 0.1,
                    "session_id": "s1",
                    "terminal_reason": "completed",
                    "is_error": False,
                }
            ),
        ),
    )
    (unknown,) = [
        e
        for e in captured
        if isinstance(e, Agent)
        and e.event
        and e.event.get("type") == "something_nobody_has_seen_before"
    ]
    # Reaches the terminal without raising.
    assert "something_nobody_has_seen_before" in describe(unknown)
    # Reaches the log without raising.
    log = EventLog(tmp_path)
    log.append(unknown)
    assert not log.failed
    [loaded] = _read(tmp_path, Agent)
    assert loaded.event == unknown.event


def test_no_test_this_spec_owns_still_passes_a_watch():
    """No `watch=` remains in any test file this spec owns — the five the
    `criteria`/`tests` gate actually collects. `test_agent_runner.py` is
    cell-marked and excluded from both (`SA-0041`'s own notes), so it is
    migrated by hand rather than named here; `SA-0042` claims the other
    three the parent required this of."""
    root = Path(__file__).resolve().parent
    for name in (
        "test_implement.py",
        "test_review.py",
        "test_rebut.py",
        "test_session.py",
        "test_events.py",
    ):
        source = (root / name).read_text()
        assert not _identifier_watch_appears(source), name
