import os
import re

import pytest
import yaml

from saffron.repos.policy import PolicyError, effective_risk, load_policy

VALID = """
gates:
  format: { blocking: true }
  lint:   { blocking: true }
  types:  { blocking: true }
  tests:  { blocking: true }
  coverage: { blocking: false }
  shacl:  { blocking: true }
elevate_on:
  - alembic/versions/**
protected:
  - .github/**
integrity:
  test_paths: ["thermal_edge/tests/**"]
  suppressions: ["@pytest.mark.skip", "# type: ignore"]
  gate_config: ["pyproject.toml", "pytest.ini"]
thread_env:
  OMP_NUM_THREADS: "2"
"""


def write_repo(
    tmp_path,
    policy_text=VALID,
    gates=("format", "lint", "types", "tests", "coverage", "shacl"),
):
    saffron_dir = tmp_path / ".saffron"
    (saffron_dir / "gates").mkdir(parents=True)
    (saffron_dir / "policy.yaml").write_text(policy_text)
    for name in gates:
        executable = saffron_dir / "gates" / name
        executable.write_text("#!/bin/sh\necho '{}'\n")
        executable.chmod(0o755)
    return tmp_path


def test_reads_the_declared_gates(tmp_path):
    policy, _ = load_policy(write_repo(tmp_path))
    assert policy.gates["lint"].blocking is True
    assert policy.gates["coverage"].blocking is False


_FORM_POLICY = """
gates:
  prose:    { blocking: true, form: true }
  lint:     { blocking: true }
  types:    { blocking: true, form: false }
  coverage: { blocking: false, form: true }
"""


def test_a_gate_declares_itself_a_form_gate_and_defaults_to_none(tmp_path):
    """b-0bd346, criterion 1: a gate declaration takes a `form` key beside
    `blocking`. `form: true` loads as a form gate. `form: false`, or no
    `form` key at all, loads as no form gate. Neither key moves the other:
    `prose` is blocking and form, `coverage` is form and advisory."""
    policy, _ = load_policy(
        write_repo(
            tmp_path,
            policy_text=_FORM_POLICY,
            gates=("prose", "lint", "types", "coverage"),
        )
    )
    assert policy.gates["prose"].form is True
    assert policy.gates["prose"].blocking is True
    assert policy.gates["lint"].form is False
    assert policy.gates["lint"].blocking is True
    assert policy.gates["types"].form is False
    assert policy.gates["types"].blocking is True
    assert policy.gates["coverage"].form is True
    assert policy.gates["coverage"].blocking is False


def test_declaration_order_is_preserved(tmp_path):
    policy, _ = load_policy(write_repo(tmp_path))
    assert list(policy.gates) == [
        "format",
        "lint",
        "types",
        "tests",
        "coverage",
        "shacl",
    ]


def test_reads_the_integrity_vocabulary_even_though_v0_runs_no_integrity_gate(tmp_path):
    policy, _ = load_policy(write_repo(tmp_path))
    assert "@pytest.mark.skip" in policy.integrity.suppressions
    assert policy.integrity.test_paths == ["thermal_edge/tests/**"]


def test_gate_executables_resolve_to_real_paths(tmp_path):
    repo = write_repo(tmp_path)
    policy, _ = load_policy(repo)
    executables = policy.gate_executables(repo)
    assert executables["lint"] == repo / ".saffron" / "gates" / "lint"
    assert list(executables) == list(policy.gates)


def test_a_declared_gate_with_no_executable_is_a_policy_error(tmp_path):
    repo = write_repo(tmp_path, gates=("format", "lint", "types"))
    with pytest.raises(PolicyError, match="tests"):
        load_policy(repo)


def test_a_declared_gate_that_is_not_executable_is_a_policy_error(tmp_path):
    repo = write_repo(tmp_path)
    (repo / ".saffron" / "gates" / "lint").chmod(0o644)
    with pytest.raises(PolicyError, match="not executable"):
        load_policy(repo)


def test_a_gate_declaring_when_is_refused_at_load(tmp_path):
    policy_text = VALID.replace(
        "shacl:  { blocking: true }", 'shacl:  { blocking: true, when: "**/*.ttl" }'
    )
    with pytest.raises(PolicyError, match=r"(?s)shacl.*when"):
        load_policy(write_repo(tmp_path, policy_text))


def test_a_policy_declaring_envelope_default_is_refused_at_load(tmp_path):
    policy_text = VALID + "envelope_default: []\n"
    with pytest.raises(PolicyError, match="envelope_default"):
        load_policy(write_repo(tmp_path, policy_text))


def test_a_missing_policy_file_is_a_policy_error(tmp_path):
    (tmp_path / ".saffron").mkdir()
    with pytest.raises(PolicyError, match="policy.yaml"):
        load_policy(tmp_path)


def test_an_unknown_top_level_key_is_rejected(tmp_path):
    repo = write_repo(tmp_path, policy_text="gates: {}\nelevate_onn: []\n", gates=())
    with pytest.raises(PolicyError):
        load_policy(repo)


def test_the_policy_sha_moves_when_the_policy_does(tmp_path):
    repo = write_repo(tmp_path)
    _, before = load_policy(repo)
    (repo / ".saffron" / "policy.yaml").write_text(VALID + "\n# a comment\n")
    _, after = load_policy(repo)
    assert before != after


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file permission bits")
def test_an_unreadable_policy_file_is_a_policy_error(tmp_path):
    repo = write_repo(tmp_path)
    policy_path = repo / ".saffron" / "policy.yaml"
    policy_path.chmod(0o000)
    try:
        with pytest.raises(PolicyError, match="policy.yaml"):
            load_policy(repo)
    finally:
        policy_path.chmod(0o644)


def test_a_non_utf8_policy_file_is_a_policy_error(tmp_path):
    repo = write_repo(tmp_path)
    (repo / ".saffron" / "policy.yaml").write_bytes(b"gates: {}\n\xff\xfe bad bytes")
    with pytest.raises(PolicyError):
        load_policy(repo)


def test_a_gate_name_that_climbs_out_of_the_gates_dir_is_a_policy_error(tmp_path):
    """The name is joined to .saffron/gates and then executed."""
    repo = write_repo(
        tmp_path,
        policy_text='gates:\n  "../../../../bin/echo": { blocking: true }\n',
        gates=(),
    )
    with pytest.raises(PolicyError, match="invalid"):
        load_policy(repo)


@pytest.mark.parametrize("name", ["criteria", "census", "scope"])
def test_a_repo_gate_named_for_a_core_gate_is_a_policy_error(tmp_path, name):
    """Item 22: a repo gate named `criteria` reporting `pass` ticked every PR box
    on the re-verify path, and `{criteria: {blocking: false}}` made the core
    gate advisory. The name is core's, so the repo cannot declare it."""
    repo = write_repo(
        tmp_path,
        policy_text=f"gates:\n  {name}: {{ blocking: false }}\n",
        gates=(name,),
    )
    with pytest.raises(PolicyError, match="core gate"):
        load_policy(repo)


def test_a_policy_reads_as_version_1_and_refuses_any_other(tmp_path):
    for index, text in enumerate([VALID, VALID + "schema_version: 1\n"]):
        repo = tmp_path / f"ok-{index}"
        repo.mkdir()
        policy, _ = load_policy(write_repo(repo, policy_text=text))
        assert policy.schema_version == 1
        assert type(policy.schema_version) is int

    for index, (literal, value) in enumerate([("2", 2), ("true", True), ("1.0", 1.0)]):
        repo = tmp_path / f"bad-{index}"
        repo.mkdir()
        text = VALID + f"schema_version: {literal}\n"
        with pytest.raises(PolicyError) as excinfo:
            load_policy(write_repo(repo, policy_text=text))
        assert f"schema_version {value!r} " in str(excinfo.value)
        assert "[1]" in str(excinfo.value)


def test_a_spec_declared_elevated_risk_stays_elevated():
    """§5.6's first clause: the spec's own word is enough, with no diff at all."""
    assert effective_risk("elevated", [], []) == "elevated"


def test_an_elevate_on_match_elevates_a_standard_spec():
    """§5.6's second clause: a changed path crossing an `elevate_on` pattern
    elevates a spec that never asked for it (the wiring's whole point)."""
    assert (
        effective_risk("standard", ["saffron/cell/session.py"], ["saffron/cell/**"])
        == "elevated"
    )


def test_elevate_on_uses_scopes_own_glob_not_fnmatch():
    """`*` stops at a slash — `fnmatch` would wrongly match this."""
    assert effective_risk("standard", ["a/b/c.py"], ["a/*.py"]) == "standard"


def test_no_match_and_no_declaration_leaves_the_tier_alone():
    assert (
        effective_risk("standard", ["docs/readme.md"], ["saffron/cell/**"])
        == "standard"
    )


def test_a_witness_block_is_checked_when_the_policy_loads(tmp_path):
    """`load_policy` refuses a bad `witness:` block with `PolicyError`.
    A constant pattern missing `name` or `value`, or not a regular
    expression. A `replace` naming a group its pattern lacks. A bad
    `witness_name`. A `witness_body` missing `{name}`, or invalid once
    filled in. It also loads a full block and reads it back.

    Each message matches the validator's own wording. A bare
    `extra_forbidden` error for an undeclared `witness:` key embeds
    the whole mapping, which can repeat the same text (item b-5b1f8a).
    """
    good_pattern = r"(?P<name>[A-Z]+) = (?P<value>\d+)"
    cases = []

    no_name = r"(?P<value>\d+)"
    cases.append(
        (
            {"constants": [{"pattern": no_name, "replace": ""}]},
            f"witness constant pattern {no_name!r} has no `name` group",
        )
    )

    no_value = r"(?P<name>[A-Z]+)"
    cases.append(
        (
            {"constants": [{"pattern": no_value, "replace": ""}]},
            f"witness constant pattern {no_value!r} has no `value` group",
        )
    )

    not_a_regex = r"(?P<name>[A-Z]+"
    cases.append(
        (
            {"constants": [{"pattern": not_a_regex, "replace": ""}]},
            f"witness constant pattern {not_a_regex!r} is not a valid regular expression",
        )
    )

    bad_replace = r"\g<nope>"
    cases.append(
        (
            {"constants": [{"pattern": good_pattern, "replace": bad_replace}]},
            f"witness constant replace {bad_replace!r} for pattern {good_pattern!r}",
        )
    )

    bad_witness_name = r"::\w+$"
    cases.append(
        (
            {"witness_name": bad_witness_name},
            f"witness_name {bad_witness_name!r} has no `name` group",
        )
    )

    no_placeholder = "def foo(("
    cases.append(
        (
            {"witness_body": no_placeholder},
            f"witness_body {no_placeholder!r} has no {{name}} in it",
        )
    )

    invalid_once_filled = "def {name}(("
    cases.append(
        (
            {"witness_body": invalid_once_filled},
            f"witness_body {invalid_once_filled!r} is not a valid regular "
            "expression once {name} is filled in",
        )
    )

    for index, (witness_block, expected) in enumerate(cases):
        text = yaml.dump({"gates": {}, "witness": witness_block})
        case_dir = tmp_path / str(index)
        case_dir.mkdir()
        repo = write_repo(case_dir, policy_text=text, gates=())
        with pytest.raises(PolicyError, match=re.escape(expected)):
            load_policy(repo)

    full_block = {
        "witness_name": r"::(?P<name>\w+)$",
        "witness_body": r"def {name}\(",
        "constants": [{"pattern": good_pattern, "replace": r"(\g<value> + 1)"}],
    }
    full_dir = tmp_path / "full"
    full_dir.mkdir()
    text = yaml.dump({"gates": {}, "witness": full_block})
    policy, _ = load_policy(write_repo(full_dir, policy_text=text, gates=()))
    assert policy.witness.witness_name == full_block["witness_name"]
    assert policy.witness.witness_body == full_block["witness_body"]
    assert len(policy.witness.constants) == 1
    assert policy.witness.constants[0].pattern == good_pattern

    # A quantifier's braces in the body are regex, not a format field.
    quantified = {"witness_body": r"def {name}\(\w{2}.{0,3}"}
    quantified_dir = tmp_path / "quantified"
    quantified_dir.mkdir()
    text = yaml.dump({"gates": {}, "witness": quantified})
    policy, _ = load_policy(write_repo(quantified_dir, policy_text=text, gates=()))
    assert policy.witness.witness_body == quantified["witness_body"]


def test_a_citations_block_is_checked_when_the_policy_loads(tmp_path):
    """`load_policy` reads `citations:` and refuses a bad definition with
    `PolicyError`. One missing `{name}`, and one that is no regular
    expression once `{name}` is filled in. An absent block reads empty,
    and `parse_policy` reads the same bytes with no gate on disk.
    """
    from saffron.repos.policy import parse_policy

    good = [r"\s*(?:async\s+)?def\s+{name}\b", r"\s*class\s+{name}\b"]
    text = yaml.dump({"gates": {}, "citations": {"definitions": good}})
    good_dir = tmp_path / "good"
    good_dir.mkdir()
    policy, _ = load_policy(write_repo(good_dir, policy_text=text, gates=()))
    assert policy.citations.definitions == good
    assert parse_policy(text.encode()).citations.definitions == good

    absent_dir = tmp_path / "absent"
    absent_dir.mkdir()
    policy, _ = load_policy(write_repo(absent_dir, policy_text="gates: {}\n", gates=()))
    assert policy.citations.definitions == []

    cases = [
        ("def foo", "definition 'def foo' has no {name} in it"),
        (
            "def {name}((",
            "definition 'def {name}((' is not a valid regular expression once "
            "{name} is filled in",
        ),
    ]
    for index, (entry, expected) in enumerate(cases):
        text = yaml.dump({"gates": {}, "citations": {"definitions": [entry]}})
        case_dir = tmp_path / str(index)
        case_dir.mkdir()
        repo = write_repo(case_dir, policy_text=text, gates=())
        with pytest.raises(PolicyError, match=re.escape(expected)):
            load_policy(repo)
        with pytest.raises(PolicyError, match=re.escape(expected)):
            parse_policy(text.encode())
