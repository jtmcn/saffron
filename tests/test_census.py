from __future__ import annotations

from saffron.gates.contract import GateResult
from saffron.gates.core.census import census_gate


def _tests(*names: str) -> GateResult:
    return GateResult(
        gate="tests", status="pass", tool="pytest 8.3.2", collected=list(names)
    )


def test_a_name_that_disappeared_fails_and_names_itself():
    result = census_gate(
        base=[_tests("t.py::test_a", "t.py::test_b")], head=[_tests("t.py::test_a")]
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["t.py::test_b"]
    assert result.failures[0].code == "removed-test"


def test_a_test_renamed_out_of_collection_is_a_removal():
    """The case no diff-reading version could see: the body survives, nothing
    is deleted, and the test never runs again (Appendix M)."""
    result = census_gate(base=[_tests("t.py::test_b")], head=[_tests("t.py::check_b")])
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["t.py::test_b"]


def test_a_parametrize_consolidation_that_keeps_the_names_passes():
    result = census_gate(
        base=[_tests("t.py::test_a", "t.py::test_b")],
        head=[
            _tests(
                "t.py::test_ab[1]",
                "t.py::test_ab[2]",
                "t.py::test_a",
                "t.py::test_b",
            )
        ],
    )
    assert result.status == "pass"


def test_added_tests_alone_pass():
    result = census_gate(
        base=[_tests("t.py::test_a")], head=[_tests("t.py::test_a", "t.py::test_new")]
    )
    assert result.status == "pass"


def test_no_names_at_base_skips():
    """The baseline call, and a runner that does not enumerate. Both are a
    gate with nothing to compare, not a gate with nothing to report."""
    assert census_gate(base=[], head=[_tests("t.py::test_a")]).status == "skip"


def test_names_at_base_and_none_at_head_errors():
    """A suite that enumerated before the task and stopped after it. Reporting
    every test removed would charge the task for the toolchain (§5.4)."""
    result = census_gate(
        base=[_tests("t.py::test_a")],
        head=[GateResult(gate="tests", status="pass", tool="pytest 8.3.2")],
    )
    assert result.status == "error"
    assert result.failures == []


def test_an_empty_collection_at_head_is_a_removal_not_an_error():
    """`[]` and `None` are different facts: the runner ran and found nothing."""
    result = census_gate(
        base=[_tests("t.py::test_a")],
        head=[
            GateResult(gate="tests", status="pass", tool="pytest 8.3.2", collected=[])
        ],
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["t.py::test_a"]


def test_the_gate_names_no_role_it_reads_whatever_reported():
    """Core does not know which role enumerates; §2.1. A repo reporting from
    a gate called anything else is read the same way."""
    other = GateResult(gate="spec-suite", status="pass", collected=["a::b"])
    assert census_gate(base=[other], head=[]).status == "error"


def test_it_executes_nothing_so_it_claims_no_tool():
    assert census_gate(base=[], head=[]).tool is None


def test_removed_names_are_reported_in_a_stable_order():
    result = census_gate(
        base=[_tests("t.py::test_c", "t.py::test_a", "t.py::test_b")], head=[_tests()]
    )
    assert [f.file for f in result.failures] == [
        "t.py::test_a",
        "t.py::test_b",
        "t.py::test_c",
    ]
