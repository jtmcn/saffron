"""b-5df2a7: SIGTERM to `saffron cell` or `saffron batch` must unwind the way
Ctrl-C does. Then the existing abort teardown runs, instead of the process
dying with three containers still up and no row closed."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from saffron import cli, task
from saffron.cell import runtime
from saffron.ledger import Ledger
from tests.test_session import _PLAN, _block, _drive, _stub_the_runtime, _turn


def _spec_file(tmp_path: Path, spec_id: str = "SY-1") -> Path:
    path = tmp_path / f"{spec_id}.md"
    path.write_text(
        f"---\nid: {spec_id}\ntitle: One\ntype: feature\ntouches: ['src/**']\n"
        "---\n\n## Acceptance criteria\n- [ ] it works\n"
    )
    return path


@contextlib.contextmanager
def _sigterm_safety_net():
    """A record-only handler, installed outside `cli.main` itself: a build
    with no production handler leaves the raw signal's default action live,
    which ends this whole pytest process rather than failing one test.

    Yields `(installed, heard)`: the handler object installed before `cli.main`
    runs, and a list it appends to if it is ever actually invoked. `main`'s own
    handler overrides this one for its own span and must put this one back
    before returning — the caller asserts `signal.getsignal(signal.SIGTERM) is
    installed` and `heard == []` right after `cli.main` returns, which is the
    only way to tell "`main` restored what it found" from "the safety net's
    own `finally` quietly papered over a handler `main` never put back"."""
    previous = signal.getsignal(signal.SIGTERM)
    heard: list[int] = []

    def _record_only(signum: int, _frame: object) -> None:
        heard.append(signum)

    signal.signal(signal.SIGTERM, _record_only)
    try:
        yield _record_only, heard
    finally:
        signal.signal(signal.SIGTERM, previous)


def _patch_cell_prereqs(monkeypatch) -> None:
    """The same three doubles `test_the_exit_code_distinguishes_the_terminal_
    states` uses, so `_run_cell` reaches `run_task` with no real git or
    network. Also the token, since no conftest sets it for this module."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-test")
    monkeypatch.setattr("saffron.repos.mirror.ensure_mirror", lambda repo, at: at)
    monkeypatch.setattr(
        "saffron.phases.package.real_remote", lambda repo: "https://github.com/o/r.git"
    )
    monkeypatch.setattr(
        "saffron.phases.package.fetch_default_branch",
        lambda mirror, url: ("main", "a" * 40),
    )


def _turns_sending_sigterm_before(index: int):
    """The plan turn, the implement turn and REVIEW's first lens turn. A
    self-sent SIGTERM raises before the next statement (measured), so the
    production handler fires from inside this generator's own frame."""
    steps = [_turn(_block(_PLAN)), _turn(), _turn(_block({"findings": []}))]
    for position, step in enumerate(steps):
        if position == index:
            os.kill(os.getpid(), signal.SIGTERM)
        yield step


def _last_turn_tail(order: list[str]) -> list[str]:
    last = max(i for i, entry in enumerate(order) if entry.startswith("turn:"))
    return order[last:]


def test_a_cell_sent_sigterm_tears_down_and_closes_its_task(monkeypatch, tmp_path):
    """Criteria 1 to 3: a real SIGTERM mid-IMPLEMENT, and again mid-REVIEW,
    exits 143 and tears down in the documented order. It also exports the
    patch and closes the run and task. A bare `KeyboardInterrupt` still
    escapes `main`, rather than reading as one."""
    spec = _spec_file(tmp_path)

    # Mid-IMPLEMENT: index 1.
    _patch_cell_prereqs(monkeypatch)
    cell = _stub_the_runtime(monkeypatch)
    drive_dir = tmp_path / "mid-implement"

    def _stub_run_one_cell_implement(
        cell_spec, *, repo, mirror, ledger, out_dir, emit, on_state
    ):
        outcome, _ledger = _drive(
            monkeypatch,
            drive_dir,
            cell=cell,
            turns=_turns_sending_sigterm_before(1),
            on_state=on_state,
        )
        return outcome

    monkeypatch.setattr(task, "run_one_cell", _stub_run_one_cell_implement)
    argv = ["--home", str(tmp_path / "home-implement"), "cell", str(spec)]
    try:
        with _sigterm_safety_net() as (installed_before, heard):
            exit_code = cli.main(argv)
            # The handler `main` found is the one restored, and it heard
            # neither signal: both were consumed by `main`'s own handler.
            assert signal.getsignal(signal.SIGTERM) is installed_before
            assert heard == []
    # Broad on purpose: a leak here fails the test, not the whole session.
    except BaseException as exc:
        pytest.fail(f"cli.main leaked {exc!r} instead of returning 143")

    assert exit_code == 143
    assert len(cell.turns) == 2
    assert _last_turn_tail(cell.order) == [
        "turn:saffron-cell-SY-1",
        "removed:container:saffron-cell-SY-1",
        "removed:network:saffron-cells",
        "removed:network:saffron-critic-net",
        "removed:volume:saffron-wt-SY-1",
        "removed:volume:saffron-st-SY-1",
    ]
    assert "stop" in cell.preflight
    assert (drive_dir / "out" / "SY-1" / "patch.diff").is_file()
    ledger = Ledger(drive_dir / "ledger.db")
    (run_row,) = ledger._db.execute("SELECT status FROM runs").fetchall()
    assert run_row["status"] == "ABORTED"
    (queued,) = ledger.queue_lines()
    assert queued["state"] == "ORPHANED"
    ledger.close()

    # Mid-REVIEW: index 2.
    cell2 = _stub_the_runtime(monkeypatch)
    drive_dir2 = tmp_path / "mid-review"

    def _stub_run_one_cell_review(
        cell_spec, *, repo, mirror, ledger, out_dir, emit, on_state
    ):
        outcome, _ledger = _drive(
            monkeypatch,
            drive_dir2,
            cell=cell2,
            turns=_turns_sending_sigterm_before(2),
            on_state=on_state,
        )
        return outcome

    monkeypatch.setattr(task, "run_one_cell", _stub_run_one_cell_review)
    argv2 = ["--home", str(tmp_path / "home-review"), "cell", str(spec)]
    try:
        with _sigterm_safety_net() as (installed_before2, heard2):
            exit_code2 = cli.main(argv2)
            assert signal.getsignal(signal.SIGTERM) is installed_before2
            assert heard2 == []
    # Broad on purpose: a leak here fails the test, not the whole session.
    except BaseException as exc:
        pytest.fail(f"cli.main leaked {exc!r} instead of returning 143")

    assert exit_code2 == 143
    assert len(cell2.turns) == 3
    assert _last_turn_tail(cell2.order) == [
        "turn:saffron-critic-SY-1",
        "removed:container:saffron-critic-SY-1",
        "removed:volume:saffron-critic-wt-SY-1",
        "removed:volume:saffron-critic-st-SY-1",
        "removed:container:saffron-cell-SY-1",
        "removed:network:saffron-cells",
        "removed:network:saffron-critic-net",
        "removed:volume:saffron-wt-SY-1",
        "removed:volume:saffron-st-SY-1",
    ]
    assert "stop" in cell2.preflight
    assert (drive_dir2 / "out" / "SY-1" / "patch.diff").is_file()
    ledger2 = Ledger(drive_dir2 / "ledger.db")
    (run_row2,) = ledger2._db.execute("SELECT status FROM runs").fetchall()
    assert run_row2["status"] == "ABORTED"
    (queued2,) = ledger2.queue_lines()
    assert queued2["state"] == "ORPHANED"
    ledger2.close()

    # A bare KeyboardInterrupt, with no signal involved, still escapes `main`.
    # The handler's own mark is what tells the two apart, and this sets none.
    cell3 = _stub_the_runtime(monkeypatch)
    drive_dir3 = tmp_path / "bare"

    def _stub_run_one_cell_bare(
        cell_spec, *, repo, mirror, ledger, out_dir, emit, on_state
    ):
        outcome, _ledger = _drive(
            monkeypatch,
            drive_dir3,
            cell=cell3,
            turns=[KeyboardInterrupt()],
            on_state=on_state,
        )
        return outcome

    monkeypatch.setattr(task, "run_one_cell", _stub_run_one_cell_bare)
    argv3 = ["--home", str(tmp_path / "home-bare"), "cell", str(spec)]
    with pytest.raises(KeyboardInterrupt):
        cli.main(argv3)


def test_a_second_sigterm_does_not_cut_the_teardown_short(monkeypatch, tmp_path):
    """A second SIGTERM, sent while the first one's teardown removes the
    cell's own container, cuts nothing short: every removal still runs, in
    the same order, and `main` still exits 143."""
    spec = _spec_file(tmp_path)
    _patch_cell_prereqs(monkeypatch)
    cell = _stub_the_runtime(monkeypatch)

    first_signal_sent = False
    second_sent = False
    # Bound after `_stub_the_runtime`, so this chains to its recording stub
    # rather than replacing it outright.
    stashed_remove_container = runtime.remove_container

    def _wrapped_remove_container(name):
        nonlocal second_sent
        if name == "saffron-cell-SY-1" and first_signal_sent and not second_sent:
            # A build that restored the default disposition instead of
            # SIG_IGN would let this second signal end pytest itself.
            assert signal.getsignal(signal.SIGTERM) is signal.SIG_IGN
            second_sent = True
            os.kill(os.getpid(), signal.SIGTERM)
        return stashed_remove_container(name)

    monkeypatch.setattr(
        "saffron.cell.runtime.remove_container", _wrapped_remove_container
    )

    def _turns():
        nonlocal first_signal_sent
        steps = [_turn(_block(_PLAN)), _turn()]
        for position, step in enumerate(steps):
            if position == 1:
                first_signal_sent = True
                os.kill(os.getpid(), signal.SIGTERM)
            yield step

    drive_dir = tmp_path / "drive"

    def _stub_run_one_cell(cell_spec, *, repo, mirror, ledger, out_dir, emit, on_state):
        outcome, _ledger = _drive(
            monkeypatch, drive_dir, cell=cell, turns=_turns(), on_state=on_state
        )
        return outcome

    monkeypatch.setattr(task, "run_one_cell", _stub_run_one_cell)
    argv = ["--home", str(tmp_path / "home"), "cell", str(spec)]
    try:
        with _sigterm_safety_net() as (installed_before, heard):
            exit_code = cli.main(argv)
            # Both signals were consumed by `main`'s own handler (the first
            # raised, the second ignored), and it put the same one back.
            assert signal.getsignal(signal.SIGTERM) is installed_before
            assert heard == []
    # Broad on purpose: a leak here fails the test, not the whole session.
    except BaseException as exc:
        pytest.fail(f"cli.main leaked {exc!r} instead of returning 143")

    assert exit_code == 143
    assert second_sent, "the wrapped remove_container was never reached"
    assert _last_turn_tail(cell.order) == [
        "turn:saffron-cell-SY-1",
        "removed:container:saffron-cell-SY-1",
        "removed:network:saffron-cells",
        "removed:network:saffron-critic-net",
        "removed:volume:saffron-wt-SY-1",
        "removed:volume:saffron-st-SY-1",
    ]


_CHILD_TEMPLATE = "import pathlib, time\npathlib.Path(__MARKER__).write_text('ready')\ntime.sleep(60)\n"

_BATCH_SCRIPT = """
import pathlib
import subprocess
import sys

from saffron import cli, preflight
from saffron.intake import parse_spec

CHILD = __CHILD__

def _fake_check_readiness(repo, mirror_path, *, scratch, home, token):
    return preflight.Readiness(
        ok=True,
        mirror=pathlib.Path("/tmp/does-not-exist.git"),
        url="https://github.com/o/r.git",
        base_sha="a" * 40,
    )


preflight.check_readiness = _fake_check_readiness

_SY1 = (
    "---\\nid: SY-1\\ntitle: One\\ntype: feature\\ntouches: ['src/**']\\n---\\n\\n"
    "## Acceptance criteria\\n- [ ] it works\\n"
)
_SY2 = (
    "---\\nid: SY-2\\ntitle: Two\\ntype: feature\\ntouches: ['src/**']\\n---\\n\\n"
    "## Acceptance criteria\\n- [ ] it works\\n"
)


def _candidate(text):
    spec = parse_spec(text)
    return cli.Candidate(path=pathlib.Path(spec.id), spec=spec, spec_sha="a" * 64, task_id=None)


def _fake_resolve_queue(repo, home, ledger, *, stamp_orphaned, pinned=None, stack=False):
    return cli.QueueResolution(
        repo_id=None,
        mirror=pathlib.Path("/tmp/does-not-exist.git"),
        base_sha="a" * 40,
        repo_slug=None,
        exported=pathlib.Path("/tmp/does-not-exist"),
        candidates=[_candidate(_SY1), _candidate(_SY2)],
        refusals=[],
        reconciled=cli.ReconcileResult(),
        gh_failures=[],
        policy_unread=[],
    )


cli._resolve_queue = _fake_resolve_queue
cli._protected_paths_at = lambda mirror, base_sha, scratch, unread=None: []
cli._retirement_markers_at = lambda mirror, base_sha: []


def _fake_run_task(spec, *a, **k):
    print("running " + spec.id)
    # The pipe stays open and silent while the child sleeps, so the blocking
    # read sits inside this `with` body rather than in its implicit
    # `__exit__` alone, which is what makes `Popen.__exit__`'s own exact-class
    # check on its way out actually apply (measured, b-5df2a7).
    with subprocess.Popen(
        [sys.executable, "-c", CHILD],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as child:
        child.stdout.read()
    raise RuntimeError("unreachable: the child outlives this call")


cli.run_task = _fake_run_task

sys.exit(cli.main(["--home", "__HOME__", "batch", "--repo", "__REPO__", "--budget", "50"]))
"""

_CELL_SCRIPT = """
import pathlib
import subprocess
import sys

from saffron import cli, preflight

CHILD = __CHILD__


def _fake_prepare_mirror(repo, mirror_path):
    return pathlib.Path("/tmp/does-not-exist.git"), "https://github.com/o/r.git", "a" * 40


preflight.prepare_mirror = _fake_prepare_mirror
cli._protected_paths_at = lambda mirror, base_sha, scratch, unread=None: []
cli._retirement_markers_at = lambda mirror, base_sha: []


def _fake_run_task(spec, *a, **k):
    print("running " + spec.id)
    # The pipe stays open and silent while the child sleeps, so the blocking
    # read sits inside this `with` body rather than in its implicit
    # `__exit__` alone, which is what makes `Popen.__exit__`'s own exact-class
    # check on its way out actually apply (measured, b-5df2a7).
    with subprocess.Popen(
        [sys.executable, "-c", CHILD],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as child:
        child.stdout.read()
    raise RuntimeError("unreachable: the child outlives this call")


cli.run_task = _fake_run_task

sys.exit(cli.main(["--home", "__HOME__", "cell", "__SPEC__"]))
"""


def _run_signaled(script: str, *, marker: Path, repo_root: Path) -> tuple[int, str]:
    """Spawn `script`, wait for `marker`, SIGTERM it, and reap it either way."""
    env = dict(os.environ)
    env.pop("PYTHONUNBUFFERED", None)
    env.pop("SAFFRON_CELL_RUNTIME", None)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = "sk-test"

    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        cwd=repo_root,
        env=env,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while not marker.exists():
            if proc.poll() is not None:
                pytest.fail(f"the process exited early with {proc.returncode}")
            if time.monotonic() > deadline:
                pytest.fail("the marker never appeared")
            time.sleep(0.05)

        proc.send_signal(signal.SIGTERM)
        try:
            stdout, _stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pytest.fail("the process did not exit within ten seconds of SIGTERM")
        return proc.returncode, stdout
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()


def test_a_process_sent_sigterm_exits_143_with_its_log_flushed(tmp_path):
    """A `saffron cell` process and a `saffron batch` process, each with
    stdout piped and a child process of its own still running, are sent
    SIGTERM from outside. Each exits 143 within ten seconds, with its
    pre-signal stdout intact, buffered or not."""
    repo_root = Path(cli.__file__).resolve().parent.parent

    # cell
    cell_marker = tmp_path / "cell-marker"
    cell_child = _CHILD_TEMPLATE.replace("__MARKER__", repr(str(cell_marker)))
    spec_path = tmp_path / "SY-1.md"
    spec_path.write_text(
        "---\nid: SY-1\ntitle: One\ntype: feature\ntouches: ['src/**']\n"
        "---\n\n## Acceptance criteria\n- [ ] it works\n"
    )
    cell_script = (
        _CELL_SCRIPT.replace("__CHILD__", repr(cell_child))
        .replace("__HOME__", str(tmp_path / "home-cell"))
        .replace("__SPEC__", str(spec_path))
    )
    cell_code, cell_out = _run_signaled(
        cell_script, marker=cell_marker, repo_root=repo_root
    )
    assert cell_code == 143
    assert "running SY-1" in cell_out

    # batch
    batch_marker = tmp_path / "batch-marker"
    batch_child = _CHILD_TEMPLATE.replace("__MARKER__", repr(str(batch_marker)))
    batch_home = tmp_path / "home-batch"
    batch_script = (
        _BATCH_SCRIPT.replace("__CHILD__", repr(batch_child))
        .replace("__HOME__", str(batch_home))
        .replace("__REPO__", str(repo_root))
    )
    batch_code, batch_out = _run_signaled(
        batch_script, marker=batch_marker, repo_root=repo_root
    )
    assert batch_code == 143
    assert "running SY-1" in batch_out
    assert "running SY-2" not in batch_out

    ledger = Ledger(batch_home / "ledger.db")
    (batch_row,) = ledger._db.execute("SELECT status, ended_at FROM batches").fetchall()
    assert batch_row["status"] == "INFRASTRUCTURE"
    assert batch_row["ended_at"] is not None
    ledger.close()
