import os

import pytest

from saffron.repos.policy import PolicyError, load_policy

VALID = """
gates:
  format: { blocking: true }
  lint:   { blocking: true }
  types:  { blocking: true }
  tests:  { blocking: true }
  coverage: { blocking: false }
  shacl:  { blocking: true, when: "**/*.ttl" }
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
    assert policy.gates["shacl"].when == "**/*.ttl"


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
