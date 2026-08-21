import os
import subprocess
import sys
import time
from pathlib import Path

from saffron.cell import runtime as cell_runtime
from saffron.gates.runner import CellExecutor, run_gate, run_suite

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


def test_a_crash_after_a_clean_pass_is_now_an_error(tmp_path):
    """Pre-Task-5 this was believed as `pass`. A crash (nonzero exit) paired
    with zero reported failures is now indistinguishable from the exact
    false-green this contract exists to catch, so it is `error` instead."""
    result = run_gate("types", FIXTURES / "crashes", cwd=tmp_path)
    assert result.status == "error"


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


def _gate_script(tmp_path, name, body):
    path = tmp_path / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


def test_a_gate_that_cannot_name_its_tool_is_an_error(tmp_path):
    """A green result and an absent result are the same bytes (principle 34)."""
    gate = _gate_script(
        tmp_path,
        "lint",
        'echo \'{"gate":"lint","status":"pass","failures":[],"summary":"clean"}\'\n',
    )
    result = run_gate("lint", gate, tmp_path)
    assert result.status == "error"
    assert "tool" in result.summary


def test_nonzero_exit_with_no_parsed_failures_is_an_error(tmp_path):
    """A reworded tool output line makes every match vanish; the exit code is
    the only thing that still disagrees."""
    gate = _gate_script(
        tmp_path,
        "format",
        'echo \'{"gate":"format","status":"pass","tool":"ruff 0.14.2",'
        '"failures":[],"summary":"0 files"}\'\nexit 1\n',
    )
    result = run_gate("format", gate, tmp_path)
    assert result.status == "error"
    assert "exit" in result.summary


def test_a_real_failure_with_a_nonzero_exit_is_still_fail(tmp_path):
    gate = _gate_script(
        tmp_path,
        "lint",
        'echo \'{"gate":"lint","status":"fail","tool":"ruff 0.14.2",'
        '"failures":[{"file":"a.py","code":"E501","message":"long"}],'
        '"summary":"1"}\'\nexit 1\n',
    )
    assert run_gate("lint", gate, tmp_path).status == "fail"


def test_skip_needs_no_tool(tmp_path):
    """A repo that declares no such gate has no tool to name."""
    gate = _gate_script(
        tmp_path,
        "types",
        'echo \'{"gate":"types","status":"skip","summary":"no type system"}\'\n',
    )
    assert run_gate("types", gate, tmp_path).status == "skip"


class _FakeExecutor:
    def __init__(self, completed):
        self.completed = completed
        self.calls = []

    def run(self, argv, cwd, timeout_s):
        self.calls.append((list(argv), str(cwd), timeout_s))
        return self.completed


def test_run_gate_delegates_to_the_executor(tmp_path):
    executor = _FakeExecutor(
        cell_runtime.Completed(
            0,
            '{"gate":"lint","status":"pass","tool":"ruff 1.0","failures":[],'
            '"summary":"clean"}',
            "",
        )
    )
    result = run_gate("lint", tmp_path / "lint", tmp_path, executor=executor)
    assert result.status == "pass"
    assert executor.calls[0][0] == [str(tmp_path / "lint")]


def test_a_subset_argument_reaches_the_executor(tmp_path):
    executor = _FakeExecutor(
        cell_runtime.Completed(
            0,
            '{"gate":"tests","status":"pass","tool":"pytest 8","failures":[],'
            '"summary":"1 passed"}',
            "",
        )
    )
    run_gate(
        "tests",
        tmp_path / "tests",
        tmp_path,
        executor=executor,
        subset=["tests/test_a.py"],
    )
    assert executor.calls[0][0][-1] == "tests/test_a.py"


def test_an_executor_timeout_is_an_error(tmp_path):
    executor = _FakeExecutor(cell_runtime.Completed(124, "", "", timed_out=True))
    result = run_gate("tests", tmp_path / "tests", tmp_path, executor=executor)
    assert result.status == "error"
    assert "timed out" in result.summary


def test_cell_executor_passes_the_gate_path_through_unchanged(tmp_path, monkeypatch):
    """R2: a CellExecutor ignores the host cwd (a cell-side path does not exist
    on the host) and always runs at its own workdir. Fakes the runtime — this
    is a unit test about argv construction, not a container."""
    calls = []

    def fake_exec(container, command, *, workdir=None, timeout_s=900):
        calls.append((container, list(command), workdir, timeout_s))
        return cell_runtime.Completed(0, "", "")

    monkeypatch.setattr(cell_runtime, "exec_", fake_exec)

    executor = CellExecutor("cell-1")
    gate_path = "/work/.saffron/gates/lint"
    executor.run([gate_path], tmp_path, 900)

    container, command, workdir, timeout_s = calls[0]
    assert container == "cell-1"
    assert command == [gate_path]
    assert workdir == "/work"
    assert timeout_s == 900
