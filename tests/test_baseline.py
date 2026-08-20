from saffron.gates.baseline import is_no_progress, subtract_baseline
from saffron.gates.contract import Failure, GateResult


def gate(name: str, *failures: Failure, status: str = "fail") -> GateResult:
    return GateResult(gate=name, status=status, failures=list(failures))


def test_a_failure_absent_from_the_baseline_is_new():
    base = [gate("types", Failure(file="a.py", line=1, code="arg-type", message="old"))]
    head = [
        gate(
            "types",
            Failure(file="a.py", line=1, code="arg-type", message="old"),
            Failure(file="b.py", line=4, code="return-value", message="fresh"),
        )
    ]
    new = subtract_baseline(head, base)
    assert [n.failure.file for n in new] == ["b.py"]
    assert new[0].gate == "types"


def test_a_pre_existing_failure_that_moved_thirty_lines_is_not_new():
    """The load-bearing test. A line-keyed implementation fails here.

    The head diff inserts thirty lines at the top of the file, so every
    pre-existing failure below shifts. None of them are this task's problem.
    """
    base = [
        gate(
            "types",
            Failure(file="a.py", line=40, code="arg-type", message="bad arg"),
            Failure(file="a.py", line=55, code="return-value", message="bad return"),
        ),
        gate(
            "lint", Failure(file="a.py", line=61, code="E501", message="line too long")
        ),
    ]
    head = [
        gate(
            "types",
            Failure(file="a.py", line=70, code="arg-type", message="bad arg"),
            Failure(file="a.py", line=85, code="return-value", message="bad return"),
        ),
        gate(
            "lint", Failure(file="a.py", line=91, code="E501", message="line too long")
        ),
    ]
    assert subtract_baseline(head, base) == []


def test_a_message_carrying_its_own_line_number_still_matches():
    base = [
        gate("types", Failure(file="a.py", line=40, code="X", message="see line 40"))
    ]
    head = [
        gate("types", Failure(file="a.py", line=70, code="X", message="see line 70"))
    ]
    assert subtract_baseline(head, base) == []


def test_the_same_code_twice_in_one_file_is_told_apart_by_message():
    base = [
        gate(
            "types",
            Failure(file="a.py", line=1, code="arg-type", message="expected str"),
        )
    ]
    head = [
        gate(
            "types",
            Failure(file="a.py", line=1, code="arg-type", message="expected str"),
            Failure(file="a.py", line=9, code="arg-type", message="expected int"),
        )
    ]
    new = subtract_baseline(head, base)
    assert [n.failure.message for n in new] == ["expected int"]


def test_the_same_code_twice_in_one_file_is_told_apart_by_its_numbers():
    """The numeric sibling of the test above.

    `normalize_message` collapses digit runs, so these two share an identity
    and only counting tells them apart.
    """
    base = [
        gate(
            "types",
            Failure(
                file="m.py",
                line=1,
                code="arg-type",
                message='Argument 1 to "f" has incompatible type "int"; expected "str"',
            ),
        )
    ]
    head = [
        gate(
            "types",
            Failure(
                file="m.py",
                line=1,
                code="arg-type",
                message='Argument 1 to "f" has incompatible type "int"; expected "str"',
            ),
            Failure(
                file="m.py",
                line=2,
                code="arg-type",
                message='Argument 2 to "f" has incompatible type "int"; expected "str"',
            ),
        )
    ]
    assert len(subtract_baseline(head, base)) == 1


def test_extra_failures_sharing_one_baseline_identity_are_new():
    """One pre-existing E501 cancels one E501, not every E501 in the file."""
    base = [
        gate(
            "lint",
            Failure(
                file="a.py", line=3, code="E501", message="Line too long (105 > 88)"
            ),
        )
    ]
    head = [
        gate(
            "lint",
            Failure(
                file="a.py", line=3, code="E501", message="Line too long (105 > 88)"
            ),
            Failure(
                file="a.py", line=8, code="E501", message="Line too long (140 > 88)"
            ),
            Failure(
                file="a.py", line=9, code="E501", message="Line too long (99 > 88)"
            ),
        )
    ]
    assert len(subtract_baseline(head, base)) == 2


def test_the_same_failure_in_two_gates_is_two_identities():
    base = [gate("lint", Failure(file="a.py", line=1, code="E501", message="long"))]
    head = [
        gate("lint", Failure(file="a.py", line=1, code="E501", message="long")),
        gate("format", Failure(file="a.py", line=1, code="E501", message="long")),
    ]
    new = subtract_baseline(head, base)
    assert [n.gate for n in new] == ["format"]


def test_a_gate_with_no_baseline_entry_reports_everything_as_new():
    head = [
        gate("shacl", Failure(file="s.ttl", line=2, code="shape", message="violated"))
    ]
    assert len(subtract_baseline(head, base=[])) == 1


def test_a_fixed_pre_existing_failure_is_not_reported_as_anything():
    base = [gate("lint", Failure(file="a.py", line=1, code="E501", message="long"))]
    head = [gate("lint", status="pass")]
    assert subtract_baseline(head, base) == []


def test_no_progress_ignores_the_lines_every_attempt_shifts():
    first = subtract_baseline(
        [gate("types", Failure(file="a.py", line=10, code="X", message="m"))], []
    )
    second = subtract_baseline(
        [gate("types", Failure(file="a.py", line=44, code="X", message="m"))], []
    )
    assert is_no_progress(second, first)


def test_progress_is_a_different_identity_set():
    first = subtract_baseline(
        [gate("types", Failure(file="a.py", line=10, code="X", message="m"))], []
    )
    second = subtract_baseline(
        [gate("types", Failure(file="b.py", line=10, code="X", message="m"))], []
    )
    assert not is_no_progress(second, first)


def test_fixing_some_of_several_identical_failures_is_progress():
    """A set-keyed is_no_progress calls three-of-four fixed "no progress"."""
    same = Failure(file="a.py", line=1, code="E501", message="Line too long (105 > 88)")
    previous = subtract_baseline([gate("lint", same, same, same, same)], [])
    current = subtract_baseline([gate("lint", same)], [])
    assert not is_no_progress(current, previous)
