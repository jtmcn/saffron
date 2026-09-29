"""The setup-saffron skill: its check, and its templates held to Saffron's own schema.

A change to the policy model, the gate contract, the base tag or §5.4's roles
fails here until the skill follows it.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from saffron.gates.contract import Failure, GateResult
from saffron.repos.image import BASE_TAG
from saffron.repos.policy import IntegrityPatterns, Policy

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / ".claude" / "skills" / "setup-saffron"
TEMPLATES = SKILL / "templates"
_SPEC = importlib.util.spec_from_file_location(
    "setup_saffron_check", SKILL / "check.py"
)
assert _SPEC is not None and _SPEC.loader is not None
check = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = check
_SPEC.loader.exec_module(check)

TESTS_OK = """#!/bin/sh
tool="sh $(sh -c 'echo 1')"
printf '{"gate":"tests","status":"pass","tool":"%s","collected":["t::a"],"failures":[],"summary":"ok"}\\n' "$tool"
"""

# Stands in for every tool the templates wrap: `fake --version`, a clean
# `check`, a two-test `--list`, and a run that fails any name listed in FAIL.
FAKE_TOOL = """#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
if args == ["--version"]:
    print("fake 1.0")
elif args[:1] == ["--list"]:
    print("t.py::a\\nt.py::b\\n2 tests")
elif args[:1] == ["check"]:
    print("output in a shape no parser expects")
    sys.exit(2 if os.environ.get("BROKEN") else 0)
else:
    failed = [n for n in (args or ["t.py::a", "t.py::b"]) if n in os.environ.get("FAIL", "")]
    for name in failed:
        print(f"FAILED {name} - boom")
    sys.exit(1 if failed else 0)
"""


@pytest.fixture(autouse=True)
def _isolated_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
    )


def _target(tmp_path: Path, tests_gate: str = TESTS_OK, commit: bool = True) -> Path:
    repo = tmp_path / "target"
    gates = repo / ".saffron" / "gates"
    gates.mkdir(parents=True)
    (repo / ".saffron" / "specs").mkdir()
    (repo / ".saffron" / "specs" / ".gitkeep").touch()
    (repo / ".saffron" / "Dockerfile").write_text("FROM saffron/cell-base:python\n")
    (repo / ".saffron" / "policy.yaml").write_text("gates:\n  tests: {}\n")
    (gates / "tests").write_text(tests_gate)
    (gates / "tests").chmod(0o755)
    _git(repo, "init", "-q")
    if commit:
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "init")
    return repo


def test_a_well_formed_target_has_no_problems(tmp_path: Path) -> None:
    assert check.check(_target(tmp_path)) == []


def test_an_uncommitted_onboarding_is_not_a_gate_leftover(tmp_path: Path) -> None:
    assert check.check(_target(tmp_path, commit=False)) == []


def test_a_gate_that_exits_nonzero_with_no_failures_is_an_error(tmp_path: Path) -> None:
    gate = TESTS_OK.replace(
        '"summary":"ok"}\\n\' "$tool"', '"summary":"ok"}\\n\' "$tool"; exit 1'
    )
    problems = check.check(_target(tmp_path, gate))
    assert any(p.startswith("tests: error:") for p in problems)


def test_a_tests_gate_with_no_collected_names_is_reported(tmp_path: Path) -> None:
    gate = TESTS_OK.replace('"collected":["t::a"],', "")
    assert check.check(_target(tmp_path, gate)) == [
        "tests: reports no `collected`, so `census`, `criteria`, `revert` "
        "and `witness` skip"
    ]


def test_failures_not_keyed_on_collected_names_are_reported(tmp_path: Path) -> None:
    gate = TESTS_OK.replace('"status":"pass"', '"status":"fail"').replace(
        '"failures":[]', '"failures":[{"file":"t","code":"assert","message":"x"}]'
    )
    assert check.check(_target(tmp_path, gate)) == [
        "tests: no failure `code` is a collected name, so `criteria` skips"
    ]


def test_a_tests_gate_that_ignores_its_subset_is_reported(tmp_path: Path) -> None:
    gate = TESTS_OK.replace('["t::a"]', '["t::a","t::b"]')
    assert check.check(_target(tmp_path, gate)) == [
        "tests: handed 't::a', it collected more than that name"
    ]


def test_a_gate_that_leaves_a_file_fails_committed(tmp_path: Path) -> None:
    gate = TESTS_OK.replace("#!/bin/sh\n", "#!/bin/sh\ntouch .coverage\n")
    assert check.check(_target(tmp_path, gate)) == [
        "committed: a gate left .coverage, which .gitignore does not cover"
    ]


def test_a_dockerfile_off_cores_base_is_reported(tmp_path: Path) -> None:
    repo = _target(tmp_path)
    (repo / ".saffron" / "Dockerfile").write_text("FROM python:3.12\n")
    assert check.check(repo) == [
        f"{repo / '.saffron' / 'Dockerfile'} does not start "
        "FROM saffron/cell-base:<runtime>"
    ]


def test_a_declared_gate_with_no_executable_fails_the_policy(tmp_path: Path) -> None:
    repo = _target(tmp_path)
    (repo / ".saffron" / "gates" / "tests").unlink()
    problems = check.check(repo)
    assert len(problems) == 1 and problems[0].startswith("policy: gate 'tests'")


def _template_policy() -> dict:
    return yaml.safe_load((TEMPLATES / "policy.yaml").read_text())


def test_the_policy_template_names_every_policy_field() -> None:
    policy = _template_policy()
    Policy.model_validate(policy)
    assert set(policy) == set(Policy.model_fields)
    assert set(policy["integrity"]) == set(IntegrityPatterns.model_fields)


def test_the_policy_template_declares_every_repo_owned_role() -> None:
    design = (REPO / "DESIGN.md").read_text()
    table = design.split("#### Gate roles", 1)[1].split("\n\n", 2)[2]
    roles = set(re.findall(r"^\| `([a-z-]+)` \| repo \|", table, re.MULTILINE))
    assert roles == {"format", "lint", "types", "tests", "no-network", "coverage"}
    assert roles <= set(_template_policy()["gates"])


@pytest.mark.parametrize("field", ["envelope_default", "when"])
def test_a_field_the_skill_calls_unread_is_still_unread(field: str) -> None:
    readers = [
        str(path.relative_to(REPO))
        for path in (REPO / "saffron").rglob("*.py")
        if path.name != "policy.py" and f".{field}" in path.read_text()
    ]
    assert readers == [], f"templates/policy.yaml and SKILL.md call `{field}` unread"


def test_the_dockerfile_template_starts_from_cores_base() -> None:
    lines = (TEMPLATES / "Dockerfile").read_text().splitlines()
    assert (
        next(line for line in lines if line.startswith("FROM ")) == f"FROM {BASE_TAG}"
    )


@pytest.mark.parametrize("name", sorted(p.name for p in TEMPLATES.iterdir()))
def test_a_template_cites_no_saffron_design_section(name: str) -> None:
    # A target repo has no DESIGN.md, so a citation copied into it dangles.
    assert not re.search(r"DESIGN\.md|§", (TEMPLATES / name).read_text())


def test_gates_md_names_every_contract_field() -> None:
    text = (SKILL / "GATES.md").read_text()
    fields = (set(GateResult.model_fields) - {"duration_ms"}) | set(
        Failure.model_fields
    )
    assert {f for f in fields if f"`{f}`" not in text and f'"{f}"' not in text} == set()


def _onboarded_from_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "fake").write_text(FAKE_TOOL)
    (bin_dir / "fake").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{Path(sys.executable).parent}:/usr/bin:/bin")
    repo = _target(tmp_path)
    shutil.copy(TEMPLATES / "policy.yaml", repo / ".saffron" / "policy.yaml")
    shutil.copy(TEMPLATES / "Dockerfile", repo / ".saffron" / "Dockerfile")
    for name in _template_policy()["gates"]:
        source = TEMPLATES / ("tests" if name == "tests" else "gate")
        text = (
            source.read_text()
            .replace("FILL-tool", "fake")
            .replace("FILL-runner", "fake")
        )
        (repo / ".saffron" / "gates" / name).write_text(text)
        (repo / ".saffron" / "gates" / name).chmod(0o755)
    return repo


def test_the_templates_filled_in_pass_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert check.check(_onboarded_from_templates(tmp_path, monkeypatch)) == []


def test_the_gate_template_reads_an_unparsed_nonzero_exit_as_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _onboarded_from_templates(tmp_path, monkeypatch)
    monkeypatch.setenv("BROKEN", "1")
    result = check.run_gate("lint", repo / ".saffron" / "gates" / "lint", repo)
    assert (result.status, result.tool) == ("error", "fake 1.0")


def test_the_tests_template_keys_a_failure_on_its_collected_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _onboarded_from_templates(tmp_path, monkeypatch)
    monkeypatch.setenv("FAIL", "t.py::b")
    assert check.check(repo) == []
    result = check.run_gate("tests", repo / ".saffron" / "gates" / "tests", repo)
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["t.py::b"]
    assert result.collected == ["t.py::a", "t.py::b"]


def test_the_tests_template_reports_a_name_it_cannot_find(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _onboarded_from_templates(tmp_path, monkeypatch)
    gate = repo / ".saffron" / "gates" / "tests"
    result = check.run_gate("tests", gate, repo, subset=["t.py::a", "t.py::gone"])
    assert (result.status, result.collected, result.uncollected) == (
        "pass",
        ["t.py::a"],
        ["t.py::gone"],
    )
