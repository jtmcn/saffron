from __future__ import annotations

from saffron.gates.contract import Failure, GateResult
from saffron.gates.core.criteria import criteria_gate
from saffron.intake import Criterion


def _tests(*names: str, failed: tuple[str, ...] = ()) -> GateResult:
    """One enumerating gate result: what it collected, and which of those it
    keyed as failures — the two lists the host is already holding.

    `file` is a constant. The gate reads `failures[].code` and nothing else, and
    deriving a path from a node id here would be this module splitting a name
    that core is forbidden to split.
    """
    return GateResult(
        gate="tests",
        status="fail" if failed else "pass",
        tool="pytest 8.3.2",
        collected=list(names),
        failures=[Failure(file="t.py", code=n) for n in failed],
    )


def _c(witness: str, *, preserves: bool = False) -> Criterion:
    return Criterion(
        claim=f"a claim about {witness}", witness=witness, preserves=preserves
    )


def test_no_witnesses_skips():
    """`skip` is the common case and is not a failure: ten specs predate this
    key and must gate exactly as they did before."""
    result = criteria_gate(
        [], base=[_tests("t.py::test_a")], head=[_tests("t.py::test_a")]
    )
    assert result.status == "skip"
    assert result.failures == []


def test_a_new_witness_passing_at_head_is_the_ordinary_shape():
    """Absent from `collected(base)` because the diff adds it, green at head."""
    result = criteria_gate(
        [_c("t.py::test_new")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new")],
    )
    assert result.status == "pass"


def test_a_witness_green_at_base_fails():
    """The direction rule: a witness that already passed proves nothing about
    this change."""
    result = criteria_gate(
        [_c("t.py::test_a")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a")],
    )
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["witness-green-at-base"]
    assert result.failures[0].file == "t.py::test_a"


def test_a_witness_absent_from_collected_at_head_fails():
    """It names nothing the suite ran, and a criterion nothing ran is the
    defect this gate exists for."""
    result = criteria_gate(
        [_c("t.py::test_missing")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a")],
    )
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["witness-not-collected"]


def test_a_witness_that_failed_at_head_fails():
    result = criteria_gate(
        [_c("t.py::test_new")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new", failed=("t.py::test_new",))],
    )
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["witness-failed"]


def test_a_preserves_witness_green_at_both_sides_passes():
    result = criteria_gate(
        [_c("t.py::test_a", preserves=True)],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a")],
    )
    assert result.status == "pass"


def test_a_preserves_witness_not_green_at_base_fails():
    """A new test can never preserve: it did not pass at base."""
    result = criteria_gate(
        [_c("t.py::test_new", preserves=True)],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new")],
    )
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["witness-not-preserved"]


def test_a_preserves_witness_broken_at_head_fails():
    result = criteria_gate(
        [_c("t.py::test_a", preserves=True)],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", failed=("t.py::test_a",))],
    )
    assert result.status == "fail"


def test_no_collected_at_either_side_skips():
    """The baseline call hands `base=[]`, and a runner that does not enumerate
    looks the same. Neither is a gate with anything to compare."""
    head = [_tests("t.py::test_a")]
    assert criteria_gate([_c("t.py::test_a")], base=[], head=head).status == "skip"
    assert criteria_gate([_c("t.py::test_a")], base=head, head=[]).status == "skip"


def test_failures_all_absent_from_collected_skips():
    """The membership guard, reached without inspecting a name: a side is
    readable iff its failures are empty or at least one `code` appears in that
    side's `collected`. A runner keying failures on something else is not a
    repo doing something wrong."""
    keyed_elsewhere = GateResult(
        gate="tests",
        status="fail",
        tool="pytest 8.3.2",
        collected=["t.py::test_a", "t.py::test_b"],
        failures=[Failure(file="saffron/gates/runner.py", line=147, code="error")],
    )
    result = criteria_gate(
        [_c("t.py::test_b")], base=[_tests("t.py::test_a")], head=[keyed_elsewhere]
    )
    assert result.status == "skip"


def test_a_witness_that_failed_at_head_is_never_passed_because_the_runner_keyed_elsewhere():
    """The measured case, with the printing test pre-existing so the baseline
    subtracts it and `tests` blocks nothing. Without the membership guard the
    naive rule reads *`test_b` was collected and `test_b` not in {"error"}* and
    reports `pass` for a witness that failed — a ticked box over a red test,
    this spec's own defect reintroduced by the gate that closes it."""
    printing_test_swallows_the_node_ids = GateResult(
        gate="tests",
        status="fail",
        tool="pytest 8.3.2",
        collected=["t.py::test_prints", "t.py::test_b"],
        failures=[Failure(file="saffron/gates/runner.py", line=147, code="error")],
    )
    result = criteria_gate(
        [_c("t.py::test_b")],
        base=[_tests("t.py::test_prints", failed=("t.py::test_prints",))],
        head=[printing_test_swallows_the_node_ids],
    )
    assert result.status != "pass"
    assert result.status == "skip"


def test_an_empty_failures_list_is_readable():
    """A green side has no `code` to test membership on, and is readable — the
    guard is `failures empty OR some code collected`, not `some code collected`."""
    result = criteria_gate(
        [_c("t.py::test_new")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new")],
    )
    assert result.status == "pass"


def test_it_reads_whatever_gate_enumerated_and_names_no_role():
    """Core does not know which role enumerates; §2.1. Two gates splitting the
    suite are unioned, as in `census`."""
    result = criteria_gate(
        [_c("b::test_new")],
        base=[
            _tests("a::test_a"),
            GateResult(gate="spec-suite", status="pass", collected=["b::test_b"]),
        ],
        head=[
            _tests("a::test_a"),
            GateResult(
                gate="spec-suite", status="pass", collected=["b::test_b", "b::test_new"]
            ),
        ],
    )
    assert result.status == "pass"


def test_it_executes_nothing_so_it_claims_no_tool():
    """As `scope`, `integrity`, `size` and `census` all do — which is why
    `run_gate`'s tool requirement never applies to them."""
    for base, head in (([], []), ([_tests("t.py::test_a")], [_tests("t.py::test_a")])):
        assert criteria_gate([_c("t.py::test_a")], base=base, head=head).tool is None


def test_it_never_errors():
    """Reading lists cannot break. A `tests` gate that errored already aborted
    the attempt before this runs, so no task reaches `PREFLIGHT_FAILED`
    because of this gate and the baseline suite (§4.4) is unaffected."""
    broken = [GateResult(gate="tests", status="error", summary="toolchain missing")]
    for base, head in (([], []), (broken, broken), ([_tests()], [_tests()])):
        assert (
            criteria_gate([_c("t.py::test_a")], base=base, head=head).status != "error"
        )


def test_every_unmet_criterion_is_named_with_its_own_reason():
    result = criteria_gate(
        [_c("t.py::test_a"), _c("t.py::test_missing"), _c("t.py::test_new")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new")],
    )
    assert result.status == "fail"
    assert [(f.file, f.code) for f in result.failures] == [
        ("t.py::test_a", "witness-green-at-base"),
        ("t.py::test_missing", "witness-not-collected"),
    ]
    assert "a claim about t.py::test_a" in result.failures[0].message


_FIXTURE_SPEC = """---
id: TE-11
title: A spec that declares the key this spec introduces
type: feature
acceptance:
  - claim: "a witness that was already green at base_sha fails the gate"
    witness: tests/test_criteria.py::test_a_witness_green_at_base_fails
  - claim: "a spec with no acceptance block parses exactly as it does today"
    witness: tests/test_intake.py::test_extracts_the_acceptance_criteria_as_a_checklist
    preserves: true
---

The `acceptance:` block above is the one from SA-0011's own `## The format`
section. A string literal, not a file: `touches` names individual test paths.
"""


def test_the_fixture_spec_parses_and_passes_the_gate():
    """SA-0011 cannot declare `acceptance:` in its own frontmatter — `Spec` sets
    `extra="forbid"`, so a spec declaring the key it introduces is refused at
    intake as malformed (§3.2). This is the fixture that closes the recursion:
    the first witness is a test this change adds (absent at base, green at
    head), the second an existing one named because the criterion is *do not
    break this*."""
    from saffron.intake import parse_spec

    spec = parse_spec(_FIXTURE_SPEC)
    assert len(spec.acceptance) == 2
    assert spec.acceptance_criteria == []

    new, preserved = (c.witness for c in spec.acceptance)
    result = criteria_gate(
        spec.acceptance,
        base=[_tests(preserved)],
        head=[_tests(preserved, new)],
    )
    assert result.status == "pass", result.summary


def test_the_fixture_spec_names_witnesses_that_exist():
    """A witness naming a test nobody wrote is exactly what this gate fails
    tasks for. Asserted rather than trusted: both names are string literals no
    import checks, and a rename would leave the fixture pointing at nothing."""
    from saffron.intake import parse_spec
    from tests import test_intake

    assert {c.witness for c in parse_spec(_FIXTURE_SPEC).acceptance} == {
        "tests/test_criteria.py::test_a_witness_green_at_base_fails",
        "tests/test_intake.py::test_extracts_the_acceptance_criteria_as_a_checklist",
    }
    assert callable(test_a_witness_green_at_base_fails)
    assert callable(test_intake.test_extracts_the_acceptance_criteria_as_a_checklist)
