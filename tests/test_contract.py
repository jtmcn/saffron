import pytest
from pydantic import ValidationError

from saffron.gates.contract import (
    Failure,
    GateResult,
    identity,
    normalize_message,
    parse_gate_json,
)


def test_parses_a_well_formed_gate_result():
    raw = """
    {"gate": "types", "status": "fail",
     "failures": [{"file": "src/ingest.py", "line": 88, "code": "arg-type",
                   "message": "Argument 1 has incompatible type"}],
     "summary": "4 errors in 2 files"}
    """
    result = parse_gate_json(raw, expected_gate="types")
    assert result.gate == "types"
    assert result.status == "fail"
    assert result.summary == "4 errors in 2 files"
    assert result.failures[0].file == "src/ingest.py"
    assert result.failures[0].line == 88
    assert result.failures[0].code == "arg-type"


def test_a_passing_gate_needs_no_failures_key():
    result = parse_gate_json('{"gate": "lint", "status": "pass"}', expected_gate="lint")
    assert result.status == "pass"
    assert result.failures == []


def test_skip_is_a_first_class_status():
    result = parse_gate_json('{"gate": "types", "status": "skip"}', expected_gate="types")
    assert result.status == "skip"


def test_an_unknown_status_is_rejected():
    with pytest.raises(ValidationError):
        parse_gate_json('{"gate": "lint", "status": "warning"}', expected_gate="lint")


def test_a_gate_naming_the_wrong_role_is_rejected():
    with pytest.raises(ValueError, match="declared as 'lint'"):
        parse_gate_json('{"gate": "types", "status": "pass"}', expected_gate="lint")


def test_line_is_optional_because_not_every_gate_has_one():
    result = parse_gate_json(
        '{"gate": "format", "status": "fail",'
        ' "failures": [{"file": "a.py", "code": "format", "message": "would reformat"}]}',
        expected_gate="format",
    )
    assert result.failures[0].line is None


def test_identity_excludes_line_because_the_diff_moves_it():
    before = Failure(file="a.py", line=12, code="arg-type", message="bad arg")
    after = Failure(file="a.py", line=412, code="arg-type", message="bad arg")
    assert identity("types", before) == identity("types", after)


def test_identity_separates_two_failures_of_the_same_code_in_one_file():
    first = Failure(file="a.py", line=1, code="arg-type", message="expected str")
    second = Failure(file="a.py", line=9, code="arg-type", message="expected int")
    assert identity("types", first) != identity("types", second)


def test_normalize_message_collapses_the_numbers_a_diff_shifts():
    assert normalize_message("line 88 of 120") == normalize_message("line 412 of 900")


def test_normalize_message_collapses_whitespace():
    assert normalize_message("two   words\n here") == "two words here"


def test_gate_result_rejects_a_negative_duration():
    with pytest.raises(ValidationError):
        GateResult(gate="lint", status="pass", duration_ms=-1)
