"""Tests for the `witness` gate (§5.4.1, `docs/BACKLOG.md` item 69).

This spec's own acceptance criteria deliberately declare no mutants — a gate
whose own tests depend on the gate is a circle — so everything here drives
`witness_gate` directly with fabricated `Criterion`/`Mutant` objects and a
fake `run_tests` callable, against real files on disk so `apply_mutant` and
`restore_mutant` do genuine byte-level work.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult, GateStatus
from saffron.gates.core.witness import witness_gate
from saffron.intake import Criterion, Mutant


def _tests(
    *, status: GateStatus, collected: tuple[str, ...] = (), tool: str = "pytest 8.3.2"
) -> GateResult:
    """A canned `tests`-gate result for exactly the one-node subset this gate
    invokes it with."""
    return GateResult(gate="tests", status=status, tool=tool, collected=list(collected))


def _criterion(
    *,
    claim: str = "the total is clamped at zero",
    witness: str = "tests/test_billing.py::test_clamped",
    file: str = "a.py",
    find: str = "max(x, 0)",
    replace: str = "x",
) -> Criterion:
    return Criterion(
        claim=claim,
        witness=witness,
        mutant=Mutant(file=file, find=find, replace=replace),
    )


def _write(tmp_path, name: str, text: str) -> None:
    (tmp_path / name).write_text(text)


def test_a_witness_that_dies_under_its_mutant_passes(tmp_path):
    """The gate applies the edit, invokes the repo's declared `tests` gate
    over exactly that one node id, and reads a `fail` as the answer it
    wanted — the only gate in the system for which a failing test is the
    passing result."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        assert subset == [criterion.witness]
        return _tests(status="fail", collected=(criterion.witness,))

    result = witness_gate(acceptance=[criterion], tree=tmp_path, run_tests=run_tests)

    assert result.status == "pass"
    assert result.gate == "witness"


def test_a_witness_that_survives_its_mutant_fails(tmp_path):
    """A witness that survives its mutant fails, and the failure names the
    criterion, the witness and the edit."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion(claim="the total is clamped at zero")

    def run_tests(subset):
        return _tests(status="pass", collected=(criterion.witness,))

    result = witness_gate(acceptance=[criterion], tree=tmp_path, run_tests=run_tests)

    assert result.status == "fail"
    assert len(result.failures) == 1
    failure = result.failures[0]
    assert isinstance(failure, Failure)
    assert failure.file == criterion.witness  # the witness
    assert "the total is clamped at zero" in failure.message  # the criterion's claim
    assert "max(x, 0)" in failure.message and "x" in failure.message  # the edit


def test_the_tree_is_unchanged_however_the_gate_ends(tmp_path):
    """Byte-identical once the gate is done, whether the witness died,
    survived, or the mutant never applied. It executes inside the worktree
    the task is packaged from, so a mutant left behind would ship in the
    diff."""
    original = "def total(x):\n    return max(x, 0)\n"
    _write(tmp_path, "a.py", original)
    target = tmp_path / "a.py"

    for status in ("fail", "pass", "error"):
        result = witness_gate(
            acceptance=[_criterion()],
            tree=tmp_path,
            run_tests=lambda subset, s=status: _tests(status=s),
        )
        assert result.status in ("pass", "fail", "error")
        assert target.read_bytes() == original.encode()

    # And when the mutant does not apply at all, the file was never touched.
    _write(tmp_path, "a.py", "def total(x):\n    return x\n")
    unchanged = target.read_bytes()
    witness_gate(
        acceptance=[_criterion()],
        tree=tmp_path,
        run_tests=lambda subset: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    assert target.read_bytes() == unchanged


def test_a_mutant_that_did_not_apply_is_named_not_counted(tmp_path):
    """A mutant that does not apply is `skip` for that criterion and is named
    in the summary — never `pass`, and never counted as a witness that did
    its job."""
    _write(tmp_path, "a.py", "def total(x):\n    return x\n")  # `find` absent
    criterion = _criterion()

    def run_tests(subset):
        raise AssertionError("the tests gate must not run for an unapplied mutant")

    result = witness_gate(acceptance=[criterion], tree=tmp_path, run_tests=run_tests)

    assert result.status == "skip"
    assert criterion.witness in result.summary
    assert not result.failures


def test_a_runner_that_broke_under_the_mutant_is_an_error(tmp_path):
    """A `tests` gate that reports `error` under the mutant is `error` here
    too, not `fail`. A test runner that could not start says nothing about
    whether the witness guards its claim, and charging that to the task is
    the collapse `DESIGN.md` refuses everywhere else."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        return GateResult(
            gate="tests", status="error", summary="pytest could not collect"
        )

    result = witness_gate(acceptance=[criterion], tree=tmp_path, run_tests=run_tests)

    assert result.status == "error"


def test_a_spec_with_no_mutants_skips(tmp_path):
    """A spec whose criteria declare no mutants reports `skip` with a summary
    saying so. Every spec that exists today is in that state, and this gate
    must not fail a task for a field its own spec predates."""
    criterion = Criterion(claim="unrelated", witness="tests/test_x.py::test_a")

    result = witness_gate(
        acceptance=[criterion],
        tree=tmp_path,
        run_tests=lambda subset: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert result.status == "skip"
    assert "no" in result.summary.lower() and "mutant" in result.summary.lower()


def test_two_criteria_do_not_see_each_others_mutants(tmp_path):
    """The gate restores the tree before invoking anything else, so two
    criteria cannot interact. Each mutant is applied to a clean tree and
    undone before the next, which is what makes a survivor attributable to
    one claim rather than to the pair."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    _write(tmp_path, "b.py", "def other(y):\n    return min(y, 10)\n")

    first = _criterion(
        witness="tests/test_a.py::test_a",
        file="a.py",
        find="max(x, 0)",
        replace="x",
    )
    second = _criterion(
        witness="tests/test_b.py::test_b",
        file="b.py",
        find="min(y, 10)",
        replace="y",
    )

    seen_content: dict[str, tuple[bytes, bytes]] = {}

    def run_tests(subset):
        # Record exactly what the tree looks like for each invocation, so a
        # leaked mutant from the other criterion would show up here.
        seen_content[subset[0]] = (
            (tmp_path / "a.py").read_bytes(),
            (tmp_path / "b.py").read_bytes(),
        )
        return _tests(status="fail", collected=tuple(subset))

    result = witness_gate(
        acceptance=[first, second], tree=tmp_path, run_tests=run_tests
    )

    assert result.status == "pass"
    a_during_first, b_during_first = seen_content[first.witness]
    assert a_during_first == b"def total(x):\n    return x\n"  # first's mutant applied
    assert (
        b_during_first == b"def other(y):\n    return min(y, 10)\n"
    )  # second untouched

    a_during_second, b_during_second = seen_content[second.witness]
    assert a_during_second == b"def total(x):\n    return max(x, 0)\n"  # first restored
    assert (
        b_during_second == b"def other(y):\n    return y\n"
    )  # second's mutant applied

    # And by the time the gate returns, both are back to their originals.
    assert (tmp_path / "a.py").read_bytes() == b"def total(x):\n    return max(x, 0)\n"
    assert (tmp_path / "b.py").read_bytes() == b"def other(y):\n    return min(y, 10)\n"


def test_the_tool_is_the_one_the_tests_gate_reported(tmp_path):
    """The `tool` field is obtained by executing the `tests` gate, never
    written as a literal. This is the invariant that separates a gate that
    ran from one that never did, and it is the whole reason this gate
    re-invokes a declared gate rather than shelling out to a runner."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        return _tests(status="fail", collected=tuple(subset), tool="pytest 9.9.9")

    result = witness_gate(acceptance=[criterion], tree=tmp_path, run_tests=run_tests)

    assert result.tool == "pytest 9.9.9"
