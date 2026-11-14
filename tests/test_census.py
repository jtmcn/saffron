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


def test_census_accepts_exactly_the_declared_renames_the_head_carried_out():
    """Seven members, one rule each. A pair carried out. A pair whose new
    name is missing and whose old name is gone. A pair whose new name is
    missing but whose old name stays. A pair whose old name is gone, with
    its new name already at base. A pair whose old name stays, with its
    new name freshly added. A pair whose new name matches another file's
    name only after the last `::`. One disappearance with no rename
    entered at all."""
    renames = {
        "t.py::test_apple": "t.py::test_apple_new",
        "t.py::test_banana": "t.py::test_banana_new",
        "t.py::test_cherry": "t.py::test_cherry_new",
        "t.py::test_date": "t.py::test_date_new",
        "t.py::test_eggplant": "t.py::test_eggplant_new",
        "t.py::test_fig": "t.py::test_fig_new",
    }
    base = [
        _tests(
            "t.py::test_apple",
            "t.py::test_banana",
            "t.py::test_charlie",
            "t.py::test_date",
            "t.py::test_date_new",
            "t.py::test_eggplant",
            "t.py::test_fig",
            "t.py::test_grape",
        )
    ]
    head = [
        _tests(
            "t.py::test_apple_new",
            "t.py::test_charlie",
            "t.py::test_date_new",
            "t.py::test_eggplant",
            "t.py::test_eggplant_new",
            "other.py::test_fig_new",
        )
    ]

    result = census_gate(base=base, head=head, renames=renames)

    assert result.status == "fail"
    assert sorted((f.file, f.code) for f in result.failures) == [
        ("t.py::test_banana", "removed-test"),
        ("t.py::test_banana_new", "rename-not-collected"),
        ("t.py::test_cherry_new", "rename-not-collected"),
        ("t.py::test_date", "removed-test"),
        ("t.py::test_fig", "removed-test"),
        ("t.py::test_fig_new", "rename-not-collected"),
        ("t.py::test_grape", "removed-test"),
    ]
    by_file = {f.file: f for f in result.failures}
    assert "t.py::test_banana" in by_file["t.py::test_banana_new"].message
    assert "t.py::test_cherry" in by_file["t.py::test_cherry_new"].message
    assert "t.py::test_fig" in by_file["t.py::test_fig_new"].message

    carried_out = census_gate(
        base=[_tests("t.py::test_apple")],
        head=[_tests("t.py::test_apple_new")],
        renames={"t.py::test_apple": "t.py::test_apple_new"},
    )
    assert carried_out.status == "pass"
    assert carried_out.failures == []

    new_name_missing = census_gate(
        base=[_tests("t.py::test_charlie")],
        head=[_tests("t.py::test_charlie")],
        renames={"t.py::test_charlie": "t.py::test_cherry_new"},
    )
    assert new_name_missing.status == "fail"
    assert len(new_name_missing.failures) == 1
    assert new_name_missing.failures[0].code == "rename-not-collected"
    assert new_name_missing.failures[0].file == "t.py::test_cherry_new"
    assert "t.py::test_charlie" in new_name_missing.failures[0].message
