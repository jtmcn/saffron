from saffron.gates.core.scope import matches, scope_gate


def test_a_single_star_does_not_cross_a_slash():
    assert matches("src/a.py", "src/*.py")
    assert not matches("src/deep/a.py", "src/*.py")


def test_a_double_star_crosses_slashes():
    assert matches("src/deep/nested/a.py", "src/**")
    assert matches("src/a.py", "src/**")


def test_a_double_star_prefix_matches_at_any_depth():
    assert matches("a/b/c_test.go", "**/*_test.go")
    assert matches("c_test.go", "**/*_test.go")


def test_a_question_mark_matches_one_character_but_not_a_slash():
    assert matches("ab.py", "a?.py")
    assert not matches("a/b.py", "a?b.py")


def test_a_dot_in_a_pattern_is_literal():
    assert not matches("srcXa/py", "src.a/py")


def test_everything_inside_touches_passes():
    result = scope_gate(
        ["src/thermal_edge/weather/cli.py", "tests/test_cli.py"],
        touches=["src/thermal_edge/weather/**", "tests/**"],
    )
    assert result.gate == "scope"
    assert result.status == "pass"
    assert result.failures == []


def test_a_file_outside_touches_fails_and_names_itself():
    result = scope_gate(
        ["src/thermal_edge/weather/cli.py", "alembic/versions/0042_add.py"],
        touches=["src/thermal_edge/weather/**"],
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["alembic/versions/0042_add.py"]
    assert result.failures[0].code == "out-of-scope"
    assert result.failures[0].line is None
    # The failure line is all the agent gets, and `touches` is frontmatter it
    # never sees — "not matched by touches" alone is not actionable.
    assert result.failures[0].message == "outside touches: src/thermal_edge/weather/**"


def test_the_summary_counts_what_escaped():
    result = scope_gate(["a.py", "b.py", "c.py"], touches=["a.py"])
    assert result.summary == "2 of 3 changed files outside touches"


def test_an_empty_diff_passes():
    assert scope_gate([], touches=["src/**"]).status == "pass"


def test_no_declared_touches_skips_rather_than_failing_everything():
    """A bug spec has no `touches` until DIAGNOSE proposes one (DESIGN.md §5.2)."""
    result = scope_gate(["a.py"], touches=[])
    assert result.status == "skip"
    assert "no touches declared" in result.summary
