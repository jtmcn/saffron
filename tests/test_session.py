from __future__ import annotations

import pytest

from saffron.cell import session
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure
from saffron.ledger import Ledger


def _failure(gate, file, code, message="m"):
    return NewFailure(gate, Failure(file=file, code=code, message=message))


def test_the_loop_stops_when_there_are_no_new_failures():
    decision = session.repair_decision(attempt=1, max_attempts=4, new=[], previous=[])
    assert decision == "green"


def test_the_loop_stops_on_no_progress():
    same = [_failure("lint", "a.py", "E501")]
    decision = session.repair_decision(
        attempt=2, max_attempts=4, new=same, previous=same
    )
    assert decision == "no-progress"


def test_fixing_three_of_four_colliding_failures_is_progress():
    """Counted, not set-compared — §5.4."""
    previous = [_failure("lint", "a.py", "E501") for _ in range(4)]
    current = [_failure("lint", "a.py", "E501")]
    decision = session.repair_decision(
        attempt=2, max_attempts=4, new=current, previous=previous
    )
    assert decision == "repair"


def test_the_loop_exhausts_at_max_attempts():
    new = [_failure("lint", "a.py", "E501")]
    decision = session.repair_decision(attempt=4, max_attempts=4, new=new, previous=[])
    assert decision == "exhausted"


def test_an_errored_gate_aborts_rather_than_counting_against_the_task():
    from saffron.gates.contract import GateResult

    results = [
        GateResult(gate="lint", status="pass", tool="ruff 1.0"),
        GateResult(gate="tests", status="error", summary="toolchain missing"),
    ]
    assert session.aborted_gates(results) == ["tests"]


def test_no_errored_gate_means_no_abort():
    from saffron.gates.contract import GateResult

    results = [GateResult(gate="lint", status="fail", tool="ruff 1.0")]
    assert session.aborted_gates(results) == []


def test_the_task_row_carries_the_specs_own_sha_not_the_policys(tmp_path, monkeypatch):
    """§4.1: a spec edited mid-batch must invalidate the task, on its own
    hash — not the policy's, which the two distinguishable shas here catch."""
    repo = tmp_path / "repo"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    (repo / ".saffron" / "policy.yaml").write_text("gates: {}\n")

    spec = session.CellSpec(
        spec_id="SY-1",
        spec_sha="spec" + "0" * 60,
        branch="saffron/SY-1",
        base_sha="a" * 40,
        touches=["src/**"],
        spec_type="bug",
        body="do the thing",
    )

    # Stop right after the ledger writes, before anything touches a real
    # cell runtime — this test asserts the ledger row, nothing past it.
    class _StopHere(Exception):
        pass

    def _stop(*_a, **_k):
        raise _StopHere

    monkeypatch.setattr("saffron.preflight.assert_host_is_unreachable", _stop)
    for name in ("remove_container", "remove_network", "create_network"):
        monkeypatch.setattr(f"saffron.cell.runtime.{name}", lambda *a, **k: None)
    monkeypatch.setattr("saffron.cell.proxy.stop_proxy", lambda *a, **k: None)

    ledger = Ledger(tmp_path / "ledger.db")
    try:
        with pytest.raises(_StopHere):
            session.run_one_cell(
                spec,
                repo=repo,
                mirror=tmp_path / "m.git",
                ledger=ledger,
                out_dir=tmp_path / "out",
            )
        row = ledger._db.execute(
            "SELECT spec_sha FROM tasks WHERE spec_id = 'SY-1'"
        ).fetchone()
        (repo_row,) = ledger._db.execute("SELECT policy_sha FROM repos").fetchall()

        assert row["spec_sha"] == spec.spec_sha
        assert row["spec_sha"] != repo_row["policy_sha"]
    finally:
        ledger.close()
