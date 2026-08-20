import os
import subprocess
import sys
import time
from pathlib import Path

from saffron.gates.runner import run_gate, run_suite

FIXTURES = Path(__file__).parent / "fixtures" / "gates"


def _running(pattern: str) -> bool:
    return (
        subprocess.run(
            ["pgrep", "-f", pattern], capture_output=True, check=False
        ).returncode
        == 0
    )


def test_a_well_behaved_gate_is_parsed(tmp_path):
    result = run_gate("lint", FIXTURES / "good", cwd=tmp_path)
    assert result.status == "fail"
    assert result.failures[0].code == "E501"
    assert result.duration_ms is not None


def test_unparseable_stdout_is_error_not_fail(tmp_path):
    result = run_gate("lint", FIXTURES / "malformed", cwd=tmp_path)
    assert result.status == "error"
    assert result.failures == []
    assert "ModuleNotFoundError" in result.summary


def test_a_timeout_is_error(tmp_path):
    result = run_gate("slow", FIXTURES / "hangs", cwd=tmp_path, timeout_s=0.5)
    assert result.status == "error"
    assert "timed out" in result.summary
    # And nothing the gate launched outlives it — in production the survivor is
    # pytest, still running inside a worktree the caller is about to delete.
    for _ in range(40):
        if not _running("sleep 31337"):
            break
        time.sleep(0.05)
    assert not _running("sleep 31337")


def test_a_missing_executable_is_error(tmp_path):
    result = run_gate("types", FIXTURES / "does-not-exist", cwd=tmp_path)
    assert result.status == "error"


def test_valid_json_is_believed_regardless_of_exit_code(tmp_path):
    result = run_gate("tests", FIXTURES / "nonzero-but-valid", cwd=tmp_path)
    assert result.status == "fail"
    assert result.failures[0].message == "boom"


def test_a_crash_after_valid_output_is_still_believed(tmp_path):
    result = run_gate("types", FIXTURES / "crashes", cwd=tmp_path)
    assert result.status == "pass"


def test_the_subset_argument_reaches_the_gate(tmp_path):
    result = run_gate(
        "tests", FIXTURES / "echoes-args", cwd=tmp_path, subset=["t/a.py", "t/b.py"]
    )
    assert result.summary == "args: t/a.py t/b.py"


def test_run_suite_returns_one_result_per_declared_gate(tmp_path):
    results = run_suite(
        {"lint": FIXTURES / "good", "types": FIXTURES / "malformed"}, cwd=tmp_path
    )
    assert [r.gate for r in results] == ["lint", "types"]
    assert [r.status for r in results] == ["fail", "error"]


def test_run_suite_preserves_declaration_order(tmp_path):
    results = run_suite(
        {"types": FIXTURES / "malformed", "lint": FIXTURES / "good"}, cwd=tmp_path
    )
    assert [r.gate for r in results] == ["types", "lint"]


def test_saffrons_own_interpreter_activation_does_not_reach_the_gate(
    tmp_path, monkeypatch
):
    """The false-green of the first live run: `uv run saffron` exported
    VIRTUAL_ENV and Saffron's .venv/bin, so gates resolved Saffron's toolchain
    instead of the repo's and reported `pass` for tools that were absent."""
    monkeypatch.setattr(sys, "prefix", "/fake/venv")
    monkeypatch.setenv("VIRTUAL_ENV", "/fake/venv")
    monkeypatch.setenv("PYTHONPATH", "/fake/lib")
    monkeypatch.setenv("PYTHONHOME", "/fake")
    monkeypatch.setenv("PYTHONSTARTUP", "/fake/startup.py")
    monkeypatch.setenv("PATH", os.pathsep.join(["/fake/venv/bin", "/usr/bin", "/bin"]))

    summary = run_gate("env", FIXTURES / "echoes-env", cwd=tmp_path).summary

    for name in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
        assert f"{name}=[]" in summary
    assert "/fake/venv/bin" not in summary
    assert "/usr/bin" in summary
