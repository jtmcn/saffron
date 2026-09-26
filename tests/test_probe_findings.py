"""`session.probe_findings` (backlog item b-792ab2, step 4): probing any
lens's findings, not `_probe_adequacy`'s adequacy findings alone.

No cell here. `critic_cell`, `runner.run_gate` and `worktree.source_mutated`
are stubbed, so the assertions are about which probes ran, in what order,
and what each finding ended at.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from saffron.agents.findings import Finding
from saffron.cell import session
from saffron.gates.contract import Failure, GateResult
from saffron.intake import Mutant
from saffron.phases import review

_SPEC = session.CellSpec(
    spec_id="SA-9999",
    spec_sha="0" * 40,
    branch="saffron/SA-9999",
    base_sha="0" * 40,
    touches=["src/x.py"],
    spec_type="bug",
    body="",
)


def _run_gate_stub(monkeypatch, results):
    """Patch `runner.run_gate` to return the next of `results`, whatever it
    is asked."""
    queue = list(results)

    def _fake(name, executable, cwd, *, timeout_s=900, subset=None, executor=None):
        return queue.pop(0)

    monkeypatch.setattr("saffron.gates.runner.run_gate", _fake)


def _critic_cell_stub(monkeypatch):
    """Patch `critic_cell` to a context manager that records its keywords and
    yields a fixed container name, and return the calls it recorded."""
    calls: list[dict] = []

    @contextlib.contextmanager
    def _fake(**kwargs):
        calls.append(kwargs)
        yield "saffron-gate-probe"

    monkeypatch.setattr("saffron.cell.session.critic_cell", _fake)
    return calls


def _mutated_stub(monkeypatch):
    """Patch `source_mutated` to a context manager that records the probe's
    `file` and yields no refusal, and return the mutants it recorded."""
    mutated: list[Mutant] = []

    @contextlib.contextmanager
    def _fake(container, mutant):
        mutated.append(mutant)
        yield None

    monkeypatch.setattr("saffron.cell.worktree.source_mutated", _fake)
    return mutated


def _tests_result(status, collected, failures=()):
    return GateResult(
        gate="tests",
        status=status,
        tool="pytest 8.0",
        collected=list(collected),
        failures=list(failures),
        summary="stub",
    )


def test_any_lenses_findings_are_probed_once_per_edit_and_decided_in_place(
    monkeypatch,
):
    calls = _critic_cell_stub(monkeypatch)
    mutated = _mutated_stub(monkeypatch)
    collected = ["t.py::test_old", "t.py::test_added"]
    _run_gate_stub(
        monkeypatch,
        [
            _tests_result("pass", collected),  # the probe cell's own baseline
            _tests_result("pass", collected),  # src/a.py
            _tests_result(
                "fail", collected, [Failure(file="t.py", code="t.py::test_added")]
            ),  # src/b.py
            _tests_result("pass", collected),  # src/c.py
        ],
    )
    base_results = [_tests_result("pass", ["t.py::test_old"])]
    probe_a = Mutant(file="src/a.py", find="a", replace="A")
    probe_b = Mutant(file="src/b.py", find="b", replace="B")
    probe_t = Mutant(file="tests/test_x.py", find="t", replace="T")
    probe_c = Mutant(file="src/c.py", find="c", replace="C")
    s1 = Finding(
        lens="spec",
        severity="concern",
        file="src/x.py",
        line=1,
        claim="s1",
        anchored=True,
        probe=probe_a,
    )
    s2 = Finding(
        lens="standards",
        severity="concern",
        file="src/x.py",
        line=1,
        claim="s2",
        anchored=True,
        probe=probe_a,
    )
    s3 = Finding(
        lens="spec",
        severity="blocker",
        file="src/x.py",
        line=1,
        claim="s3",
        anchored=False,
        probe=probe_b,
    )
    s4 = Finding(
        lens="adequacy",
        severity="concern",
        file="src/x.py",
        line=1,
        claim="s4",
        anchored=True,
        probe=probe_t,
    )
    s5 = Finding(
        lens="standards",
        severity="note",
        file="src/x.py",
        line=1,
        claim="s5",
        anchored=True,
        probe=probe_c,
    )
    targets = [s1, s2, s3, s4, s5]
    patch = "diff --git a/src/x.py b/src/x.py\n"
    thread_env = {"HOME": "/root"}

    entries = session.probe_findings(
        targets,
        spec=_SPEC,
        repo=Path("/repo"),
        mirror=Path("/mirror"),
        gates_dir=Path("/gates"),
        thread_env=thread_env,
        test_paths=["tests/**"],
        base_results=base_results,
        gates={"tests": Path("/gates/tests")},
        patch=patch,
        created=set(),
        note=lambda step, ok, detail: None,
    )

    assert [m.file for m in mutated] == ["src/a.py", "src/b.py", "src/c.py"]
    assert [e["probe"]["file"] for e in entries] == [
        "tests/test_x.py",
        "src/a.py",
        "src/b.py",
        "src/c.py",
    ]
    assert [e["probe_verdict"] for e in entries] == [
        "unproven",
        "survived",
        "killed",
        "survived",
    ]
    a_entry = entries[1]
    assert [f["lens"] for f in a_entry["findings"]] == ["spec", "standards"]
    assert [f.severity for f in targets] == [
        "blocker",
        "blocker",
        "note",
        "concern",
        "blocker",
    ]
    assert [f.probe_verdict for f in targets] == [
        "survived",
        "survived",
        "killed",
        "unproven",
        "survived",
    ]
    assert len(calls) == 1
    assert calls[0]["network"] is None
    assert calls[0]["patch"] == patch
    assert calls[0]["env"] == thread_env

    # `_probe_adequacy` keeps filtering through `review.adequacy_probes`
    # before it ever reaches `probe_findings`.
    calls = _critic_cell_stub(monkeypatch)
    mutated = _mutated_stub(monkeypatch)
    _run_gate_stub(
        monkeypatch,
        [
            _tests_result("pass", collected),  # the probe cell's own baseline
            _tests_result("pass", collected),  # src/d.py
        ],
    )
    probe_e = Mutant(file="src/e.py", find="e", replace="E")
    probe_d = Mutant(file="src/d.py", find="d", replace="D")
    x1 = Finding(
        lens="spec",
        severity="concern",
        file="src/x.py",
        line=1,
        claim="x1",
        anchored=True,
        probe=probe_e,
    )
    a1 = Finding(
        lens="adequacy",
        severity="concern",
        file="src/x.py",
        line=1,
        claim="a1",
        anchored=True,
        probe=probe_d,
    )
    a2 = Finding(
        lens="adequacy",
        severity="concern",
        file="src/x.py",
        line=1,
        claim="a2",
        anchored=False,
        probe=probe_e,
    )
    a3 = Finding(
        lens="adequacy",
        severity="concern",
        file="src/x.py",
        line=1,
        claim="a3",
        anchored=True,
        probe=None,
    )
    reviews = [
        review.LensReview(lens="spec", findings=[x1]),
        review.LensReview(lens="adequacy", findings=[a1, a2, a3]),
    ]

    entries = session._probe_adequacy(
        spec=_SPEC,
        repo=Path("/repo"),
        mirror=Path("/mirror"),
        gates_dir=Path("/gates"),
        thread_env=thread_env,
        test_paths=["tests/**"],
        base_results=base_results,
        gates={"tests": Path("/gates/tests")},
        patch=patch,
        reviews=reviews,
        created=set(),
        note=lambda step, ok, detail: None,
    )

    assert [m.file for m in mutated] == ["src/d.py"]
    (entry,) = entries
    assert entry["probe"]["file"] == "src/d.py"
    assert x1.probe_verdict is None
    assert a1.probe_verdict == "survived"
    assert a2.probe_verdict is None
    assert a3.probe_verdict is None
