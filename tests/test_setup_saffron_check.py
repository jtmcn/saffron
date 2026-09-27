"""The setup-saffron skill's check: a real git repo per case, real gate scripts."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "setup_saffron_check", REPO / ".claude" / "skills" / "setup-saffron" / "check.py"
)
assert _SPEC is not None and _SPEC.loader is not None
check = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = check
_SPEC.loader.exec_module(check)

TESTS_OK = """#!/bin/sh
tool="sh $(sh -c 'echo 1')"
printf '{"gate":"tests","status":"pass","tool":"%s","collected":["t::a"],"failures":[],"summary":"ok"}\\n' "$tool"
"""


@pytest.fixture(autouse=True)
def _isolated_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _target(tmp_path: Path, tests_gate: str = TESTS_OK) -> Path:
    repo = tmp_path / "target"
    gates = repo / ".saffron" / "gates"
    gates.mkdir(parents=True)
    (repo / ".saffron" / "specs").mkdir()
    (repo / ".saffron" / "specs" / ".gitkeep").touch()
    (repo / ".saffron" / "Dockerfile").write_text("FROM saffron/cell-base:python\n")
    (repo / ".saffron" / "policy.yaml").write_text("gates:\n  tests: {}\n")
    (gates / "tests").write_text(tests_gate)
    (gates / "tests").chmod(0o755)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run([*git, "add", "-A"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-qm", "init"], cwd=repo, check=True)
    return repo


def test_a_well_formed_target_has_no_problems(tmp_path: Path) -> None:
    assert check.check(_target(tmp_path)) == []


def test_a_gate_that_exits_nonzero_with_no_failures_is_an_error(tmp_path: Path) -> None:
    gate = TESTS_OK.replace(
        '"summary":"ok"}\\n\' "$tool"', '"summary":"ok"}\\n\' "$tool"; exit 1'
    )
    problems = check.check(_target(tmp_path, gate))
    assert any(p.startswith("tests: error:") for p in problems)


def test_a_tests_gate_with_no_collected_names_is_reported(tmp_path: Path) -> None:
    gate = TESTS_OK.replace('"collected":["t::a"],', "")
    assert check.check(_target(tmp_path, gate)) == [
        "tests: reports no `collected`, so `census` and `criteria` skip"
    ]


def test_a_gate_that_leaves_a_file_fails_committed(tmp_path: Path) -> None:
    gate = TESTS_OK.replace("#!/bin/sh\n", "#!/bin/sh\ntouch .coverage\n")
    assert check.check(_target(tmp_path, gate)) == [
        "committed: a gate left .coverage in the tree"
    ]


def test_a_dockerfile_off_cores_base_is_reported(tmp_path: Path) -> None:
    repo = _target(tmp_path)
    (repo / ".saffron" / "Dockerfile").write_text("FROM python:3.12\n")
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "x"],
        cwd=repo,
        check=True,
    )
    assert check.check(repo) == [
        f"{repo / '.saffron' / 'Dockerfile'} does not build FROM saffron/cell-base:<runtime>"
    ]


def test_an_undeclared_executable_fails_the_policy(tmp_path: Path) -> None:
    repo = _target(tmp_path)
    (repo / ".saffron" / "gates" / "tests").unlink()
    problems = check.check(repo)
    assert len(problems) == 1 and problems[0].startswith("policy: gate 'tests'")
