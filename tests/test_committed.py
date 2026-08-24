from saffron.gates.core.committed import committed_gate


def test_a_clean_worktree_passes():
    result = committed_gate([])
    assert result.status == "pass"
    assert result.failures == []


def test_every_uncommitted_path_is_its_own_failure():
    """One per path, so the no-progress rule can tell two dirty attempts apart."""
    result = committed_gate(["saffron/a.py", "tests/test_a.py"])
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["saffron/a.py", "tests/test_a.py"]
    assert {f.code for f in result.failures} == {"uncommitted-change"}


def test_it_never_reports_error():
    """`fail` and `error` are not interchangeable: a dirty tree is the attempt's
    problem, not the gate breaking, and `error` is charged to nobody (§5.4)."""
    assert committed_gate(["x.py"]).status == "fail"
