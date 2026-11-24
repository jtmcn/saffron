"""`saffron/cell_name_lock.py`: one spec-id lock shared by every home of one
user (`DESIGN.md` §5.1's one name per spec id, backlog item b-d9ed45).

Never imports `saffron.cell_name_lock` at module scope. Every witness drives
it through `run_task`, or imports it from inside a test body. A reverted
source then fails an assertion here, rather than a collection error.
"""

from __future__ import annotations

import fcntl
import os
import queue
import re
import signal
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from saffron import task as task_module
from saffron.cell import runtime
from saffron.cell.session import CellOutcome
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.task import PinnedBase, ResolvedCeilings


class _SpyStop(KeyboardInterrupt):
    """Raised by the `runtime._call` spy below. A `KeyboardInterrupt`
    subclass, never a bare one. `run_task`'s own `isinstance(cell_exc,
    Exception)` check must see this as unrecoverable. A bare
    `KeyboardInterrupt` reaching pytest's own runner stops the whole
    session, rather than failing one test.
    """


def _call_spy(calls: list[list[str]]):
    """A `runtime._call` stand-in: records `argv` and stops the cell at
    once, before any real runtime call."""

    def _spy(argv, timeout_s=120):
        calls.append(list(argv))
        raise _SpyStop("stopped before any real runtime call")

    return _spy


def _spec(spec_id: str) -> Spec:
    return Spec(
        id=spec_id,
        title="A spec",
        type="feature",
        touches=["src/**"],
        acceptance_criteria=["it works"],
    )


def _ceilings() -> ResolvedCeilings:
    return ResolvedCeilings(
        budget_usd=12.0,
        max_attempts=4,
        max_turns=60,
        budget_source="default",
        attempts_source="default",
        turns_source="default",
    )


def _base(out_dir: Path) -> PinnedBase:
    return PinnedBase(
        mirror=out_dir / "mirror.git",
        url="https://github.com/o/r.git",
        base_sha="a" * 40,
    )


def _run_task_for(out_dir: Path, spec_id: str, *, repo_id: int = 1):
    """One `run_task` call for `spec_id`: no mutant, no `depends_on`, no
    `consumes`, no `removes`. The plain unstacked shape every witness here
    needs, with the real `run_one_cell` unless a caller replaces it.
    """
    (out_dir / spec_id).mkdir(parents=True, exist_ok=True)
    ledger = Ledger(out_dir / f"{spec_id}.db")
    return task_module.run_task(
        _spec(spec_id),
        "s" * 40,
        ceilings=_ceilings(),
        base=_base(out_dir),
        repo_id=repo_id,
        repo=out_dir / "target-repo",
        ledger=ledger,
        out_dir=out_dir,
        token=None,
    )


def _run_in_thread(fn, *, timeout_s: float = 30.0):
    """`fn()`, run in a thread joined with `timeout_s`. A wrong version that
    waits for the lock must not hang the whole test: this asserts the
    thread finished either way, then replays what `fn` returned or raised.
    """
    value: object = None
    error: BaseException | None = None

    def _target() -> None:
        nonlocal value, error
        try:
            value = fn()
        except BaseException as exc:
            error = exc

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join(timeout_s)
    assert not thread.is_alive(), "the contender's run_task never returned"
    if error is not None:
        raise error
    return value


def _read_marker(proc: subprocess.Popen, *, timeout_s: float = 30.0) -> str:
    """The holder's `root=...` line, read off `proc.stdout` with an overall
    deadline. `readline()` alone has no timeout, so this reads it on a
    daemon thread and polls a queue instead.
    """
    lines: queue.Queue[str] = queue.Queue()
    stdout = proc.stdout
    assert stdout is not None

    def _reader() -> None:
        for line in stdout:
            lines.put(line)
            if line.startswith("root="):
                return

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            line = lines.get(timeout=0.1)
        except queue.Empty:
            continue
        if line.startswith("root="):
            return line.strip()
    raise AssertionError("the holder never printed its root marker in time")


def _raised(fn) -> BaseException | None:
    """What `fn` raised, `_SpyStop` included, or `None`. `pytest.raises`
    lets a `KeyboardInterrupt` subclass stop the whole session."""
    try:
        fn()
    except BaseException as exc:
        return exc
    return None


def holder_main(out_dir: str, spec_id: str, root: str | None = None) -> None:
    """Run in a bare subprocess, with no pytest and no conftest fixture: a
    real `run_task` for `spec_id` whose cell prints this process's own
    `CELL_NAME_LOCK_ROOT`, then waits on stdin before returning
    `NOT_IMPLEMENTED`. `root`, when given, replaces the per-uid default.
    """
    from unittest import mock

    if root is not None:
        task_module.CELL_NAME_LOCK_ROOT = Path(root)
    out = Path(out_dir)

    def _waiting_cell(*_a, **_k):
        print(f"root={task_module.CELL_NAME_LOCK_ROOT}", flush=True)
        sys.stdin.readline()
        return CellOutcome(
            state="NOT_IMPLEMENTED",
            task_id=1,
            run_id=1,
            task_dir=out / spec_id,
            spent_usd=0.0,
            attempts=0,
        )

    with mock.patch.object(task_module, "run_one_cell", _waiting_cell):
        _run_task_for(out, spec_id)


def contender_main(out_dir: str, spec_id: str) -> None:
    """Run in a bare subprocess: a real `run_task` for `spec_id`, printing
    `REFUSED <reason>` if it is refused, or `STARTED <argv>` if a real
    runtime call is ever reached.
    """

    from unittest import mock

    def _spy(argv, timeout_s=120):
        print("STARTED " + " ".join(argv), flush=True)
        raise SystemExit(1)

    mock.patch.object(runtime, "_call", _spy).start()
    result = _run_task_for(Path(out_dir), spec_id)
    if isinstance(result, task_module.Refused):
        print(f"REFUSED {result.reason}", flush=True)
    else:
        print(f"NOT_REFUSED {result}", flush=True)


def _popen_import(repo_root: Path, name: str, args: str, **kwargs) -> subprocess.Popen:
    """A bare subprocess that imports `name` from this file, then calls
    `name(args)`. Two statements, never one `import name(...)`."""
    script = f"from tests.test_cell_name_lock import {name}; {name}({args})"
    return subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=repo_root,
        **kwargs,
    )


def test_a_task_whose_spec_id_another_process_holds_is_refused_before_any_runtime_call(
    tmp_path, monkeypatch, capsys
):
    repo_root = Path(__file__).resolve().parents[1]
    home_a = tmp_path / "home-a"
    home_b = tmp_path / "home-b"
    home_a.mkdir()
    home_b.mkdir()

    # A root of this test's own: the host's default holds other runs' live locks.
    lock_root = tmp_path / "locks"

    holder = _popen_import(
        repo_root,
        "holder_main",
        f"{str(home_a)!r}, 'SY-1', {str(lock_root)!r}",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert Path(_read_marker(holder)[len("root=") :]) == lock_root
        # Home B meets the subprocess holder at the same root.
        monkeypatch.setattr(task_module, "CELL_NAME_LOCK_ROOT", lock_root)
        # The claim names a single `sy-1.lock`, lowercased: not `SY-1.lock`,
        # not a `.pid` file, and no second file for any other spelling.
        assert [p.name for p in lock_root.iterdir()] == ["sy-1.lock"]

        calls: list[list[str]] = []
        monkeypatch.setattr(runtime, "_call", _call_spy(calls))

        capsys.readouterr()
        result: object = None

        def _contend() -> None:
            nonlocal result
            result = _run_in_thread(lambda: _run_task_for(home_b, "SY-1"))

        raised = _raised(_contend)
        assert raised is None, repr(raised)
        assert isinstance(result, task_module.Refused)
        # Exact, not a substring match: `repo` in place of `out_dir` would
        # still contain `str(home_a)` as a path prefix.
        expected_reason = f"SY-1's cell is held by pid {holder.pid}'s {home_a}"
        assert result.reason == expected_reason
        assert f"SY-1       refused  {expected_reason}" in capsys.readouterr().out
        assert calls == []

        # The lowercase spelling meets the same lock.
        lower: object = None

        def _contend_lower() -> None:
            nonlocal lower
            lower = _run_in_thread(lambda: _run_task_for(home_b, "sy-1"))

        raised = _raised(_contend_lower)
        assert raised is None, repr(raised)
        assert isinstance(lower, task_module.Refused), lower
        assert calls == []

        try:
            _run_in_thread(lambda: _run_task_for(home_b, "SY-2"))
        except BaseException as exc:
            assert isinstance(exc, _SpyStop), repr(exc)
        else:
            pytest.fail("SY-2 beside the same holder should reach the spy")
        assert calls and calls[0][-1] == "saffron-cell-SY-2"
        calls.clear()

        os.kill(holder.pid, signal.SIGKILL)
        holder.wait(timeout=10)

        try:
            _run_in_thread(lambda: _run_task_for(home_b, "SY-1"))
        except BaseException as exc:
            assert isinstance(exc, _SpyStop), repr(exc)
        else:
            pytest.fail("SY-1 should reach the spy once the holder is dead")
        assert calls and calls[0][-1] == "saffron-cell-SY-1"
    finally:
        if holder.poll() is None:
            holder.kill()
        holder.wait()


def test_run_task_holds_the_spec_ids_lock_until_its_cell_returns_or_raises(
    tmp_path, monkeypatch
):
    from saffron import cell_name_lock

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    this_pid = os.getpid()

    def _assert_locked_from_inside() -> None:
        with (
            pytest.raises(cell_name_lock.LockHeld) as exc_info,
            cell_name_lock.lock(task_module.CELL_NAME_LOCK_ROOT, "SY-1", "irrelevant"),
        ):
            pass
        reason = str(exc_info.value)
        assert re.search(rf"\b{this_pid}\b", reason)
        assert str(out_dir) in reason

    def _assert_free() -> None:
        with cell_name_lock.lock(task_module.CELL_NAME_LOCK_ROOT, "SY-1", "after"):
            pass

    not_implemented = CellOutcome(
        state="NOT_IMPLEMENTED",
        task_id=1,
        run_id=1,
        task_dir=out_dir / "SY-1",
        spent_usd=0.0,
        attempts=0,
    )

    def _stub_not_implemented(*_a, **_k):
        _assert_locked_from_inside()
        return not_implemented

    monkeypatch.setattr(task_module, "run_one_cell", _stub_not_implemented)
    monkeypatch.setattr(
        package_phase,
        "push_unpackaged_work",
        lambda *a, **k: package_phase.PushResult(pushed=False, note="nothing"),
    )
    result = _run_task_for(out_dir, "SY-1")
    assert isinstance(result, CellOutcome)
    _assert_free()

    def _stub_raises(*_a, **_k):
        _assert_locked_from_inside()
        raise RuntimeError("the cell raised")

    monkeypatch.setattr(task_module, "run_one_cell", _stub_raises)
    with pytest.raises(RuntimeError):
        _run_task_for(out_dir, "SY-1")
    _assert_free()

    ready = CellOutcome(
        state="READY_FOR_REVIEW",
        task_id=1,
        run_id=1,
        task_dir=out_dir / "SY-1",
        spent_usd=0.0,
        attempts=0,
    )

    def _probe_package(outcome, **_k):
        # Reached only after `run_one_cell` returned: the lock must
        # already be free by the time PACKAGE runs.
        _assert_free()
        return SimpleNamespace(
            state="READY_FOR_REVIEW", pr_url="https://example/pr/1", note=None
        )

    monkeypatch.setattr(task_module, "run_one_cell", lambda *a, **k: ready)
    monkeypatch.setattr(package_phase, "package", _probe_package)
    result = _run_task_for(out_dir, "SY-1")
    assert isinstance(result, CellOutcome)


def test_the_lock_is_one_file_whatever_home_or_tmpdir_says(tmp_path):
    import random

    repo_root = Path(__file__).resolve().parents[1]
    spec_id = f"SY-{random.randint(10**6, 10**7 - 1)}"
    home_a, home_b = tmp_path / "home-a", tmp_path / "home-b"
    tmp_a, tmp_b = tmp_path / "tmp-a", tmp_path / "tmp-b"
    out_a, out_b = tmp_path / "out-a", tmp_path / "out-b"
    for directory in (home_a, home_b, tmp_a, tmp_b, out_a, out_b):
        directory.mkdir()

    env_a = {**os.environ, "HOME": str(home_a), "TMPDIR": str(tmp_a)}
    env_b = {**os.environ, "HOME": str(home_b), "TMPDIR": str(tmp_b)}

    holder = _popen_import(
        repo_root,
        "holder_main",
        f"{str(out_a)!r}, {spec_id!r}",
        env=env_a,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    real_root: Path | None = None
    try:
        real_root = Path(_read_marker(holder)[len("root=") :])

        contender = subprocess.run(
            [
                sys.executable,
                "-c",
                f"from tests.test_cell_name_lock import contender_main as c; "
                f"c({str(out_b)!r}, {spec_id!r})",
            ],
            cwd=repo_root,
            env=env_b,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert "REFUSED" in contender.stdout, contender.stdout
        assert str(holder.pid) in contender.stdout
        assert "STARTED" not in contender.stdout
    finally:
        if holder.poll() is None:
            holder.kill()
        holder.wait()
        if real_root is not None:
            (real_root / f"{spec_id.lower()}.lock").unlink(missing_ok=True)


def test_a_lock_root_that_is_unsafe_raises_before_any_runtime_call(
    tmp_path, monkeypatch
):
    from saffron import cell_name_lock

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    calls: list[list[str]] = []
    monkeypatch.setattr(runtime, "_call", _call_spy(calls))

    # 1. A fresh path: reaches the spy, and is made with mode 0700 even
    # under a permissive umask.
    old_umask = os.umask(0o022)
    try:
        fresh_root = tmp_path / "fresh-root"
        monkeypatch.setattr(task_module, "CELL_NAME_LOCK_ROOT", fresh_root)
        try:
            _run_task_for(out_dir, "SY-1")
        except _SpyStop:
            pass
        else:
            pytest.fail("the fresh root should reach the spy")
        assert calls
        assert stat.S_IMODE(fresh_root.stat().st_mode) == 0o700
    finally:
        os.umask(old_umask)
    calls.clear()

    # 2. A symlink to a directory.
    real_dir = tmp_path / "real-dir"
    real_dir.mkdir()
    symlinked_root = tmp_path / "symlinked-root"
    symlinked_root.symlink_to(real_dir, target_is_directory=True)
    monkeypatch.setattr(task_module, "CELL_NAME_LOCK_ROOT", symlinked_root)
    raised = _raised(lambda: _run_task_for(out_dir, "SY-1"))
    assert isinstance(raised, cell_name_lock.LockRootUnsafe), repr(raised)
    assert list(real_dir.iterdir()) == []
    assert calls == []

    # 3. A directory whose owner differs from `os.getuid()`, both with and
    # without this process already holding `SY-1`'s lock there.
    real_uid = os.getuid()
    owned_dir = tmp_path / "owned-dir"
    owned_dir.mkdir()
    monkeypatch.setattr(task_module, "CELL_NAME_LOCK_ROOT", owned_dir)

    with monkeypatch.context() as mp:
        mp.setattr(os, "getuid", lambda: real_uid + 1)
        raised = _raised(lambda: _run_task_for(out_dir, "SY-1"))
    assert isinstance(raised, cell_name_lock.LockRootUnsafe), repr(raised)
    assert calls == []

    held = cell_name_lock.lock(owned_dir, "SY-1", str(out_dir))
    held.__enter__()
    try:
        with monkeypatch.context() as mp:
            mp.setattr(os, "getuid", lambda: real_uid + 1)
            raised = _raised(lambda: _run_task_for(out_dir, "SY-1"))
    finally:
        held.__exit__(None, None, None)
    assert isinstance(raised, cell_name_lock.LockRootUnsafe), repr(raised)
    assert calls == []

    # 4. A symlink in place of `sy-1.lock`.
    lock_file = owned_dir / "sy-1.lock"
    if lock_file.is_symlink() or lock_file.exists():
        lock_file.unlink()
    target_file = tmp_path / "symlink-target.txt"
    target_file.write_text("not a lock")
    lock_file.symlink_to(target_file)
    raised = _raised(lambda: _run_task_for(out_dir, "SY-1"))
    assert isinstance(raised, OSError), repr(raised)
    assert target_file.read_text() == "not a lock"
    assert calls == []


def _fd_identity(fd: int) -> tuple[int, int]:
    info = os.fstat(fd)
    return (info.st_dev, info.st_ino)


class _ReleaseProbe:
    """Watches one lock file across a `pytest.MonkeyPatch.context()`, and
    marks the instant its holder's `flock` first lets go: by an explicit
    `LOCK_UN` or by the handle's own `close`, whichever fires first. The
    first such signal reads `path`, then runs `on_release`, a successor
    that retakes the file. Shared by `tests/test_home_lock.py`, imported
    the way that file imports from `tests/test_cli.py`.
    """

    def __init__(self, path: Path, on_release) -> None:
        self._path = path
        fd = os.open(path, os.O_RDONLY)
        try:
            self._identity = _fd_identity(fd)
        finally:
            os.close(fd)
        self._on_release = on_release
        self.released = False
        self.content_at_release: str | None = None

    def _mark(self) -> None:
        if self.released:
            return
        self.released = True
        self.content_at_release = self._path.read_text()
        self._on_release()

    def patch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real_fdopen = os.fdopen
        real_flock = fcntl.flock

        def _fdopen(fd, *args, **kwargs):
            handle = real_fdopen(fd, *args, **kwargs)
            if _fd_identity(handle.fileno()) == self._identity:
                real_close = handle.close

                def _close():
                    real_close()
                    self._mark()

                handle.close = _close
            return handle

        def _flock(fd_or_handle, operation):
            real_flock(fd_or_handle, operation)
            if operation == fcntl.LOCK_UN:
                fd = (
                    fd_or_handle
                    if isinstance(fd_or_handle, int)
                    else fd_or_handle.fileno()
                )
                if _fd_identity(fd) == self._identity:
                    self._mark()

        monkeypatch.setattr(os, "fdopen", _fdopen)
        monkeypatch.setattr(fcntl, "flock", _flock)


def test_both_locks_read_their_holder_with_one_parser(tmp_path, monkeypatch):
    from saffron import cell_name_lock, home_lock

    assert cell_name_lock._read_holder is home_lock._read_holder

    real_read_holder = home_lock._read_holder
    calls: list[str] = []

    def _spy(name: str):
        def _wrapped(handle):
            calls.append(name)
            return real_read_holder(handle)

        return _wrapped

    monkeypatch.setattr(cell_name_lock, "_read_holder", _spy("cell_name_lock"))
    monkeypatch.setattr(home_lock, "_read_holder", _spy("home_lock"))

    lock_root = tmp_path / "locks"
    lock_root.mkdir()
    cell_path = cell_name_lock._lock_path(lock_root, "SY-1")
    fd = os.open(cell_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(fd, b"4242 holder-a\n")
        os.fsync(fd)
        with (
            pytest.raises(cell_name_lock.LockHeld) as exc_info,
            cell_name_lock.lock(lock_root, "SY-1", "contender"),
        ):
            pass
        reason = str(exc_info.value)
        assert "4242" in reason
        assert "holder-a" in reason
    finally:
        os.close(fd)

    home = tmp_path / "home"
    home.mkdir()
    home_path = home / home_lock._LOCK_NAME
    fd2 = os.open(home_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(fd2, b"4343 saffron batch\n")
        os.fsync(fd2)
        with (
            pytest.raises(home_lock.HomeLocked) as exc_info2,
            home_lock.lock(home, "saffron cell"),
        ):
            pass
        reason2 = str(exc_info2.value)
        assert "4343" in reason2
        assert "saffron batch" in reason2
    finally:
        os.close(fd2)

    assert calls == ["cell_name_lock", "home_lock"]


def test_a_contender_in_a_holders_write_window_names_no_stale_holder(tmp_path):
    from saffron import cell_name_lock

    root = tmp_path / "locks"
    this_pid = os.getpid()

    def _in_block_refusal() -> None:
        with (
            pytest.raises(cell_name_lock.LockHeld) as exc_info,
            cell_name_lock.lock(root, "SY-1", "irrelevant"),
        ):
            pass
        reason = str(exc_info.value)
        assert re.search(rf"\b{this_pid}\b", reason)
        assert "the-holder" in reason

    def _stale_window_refusal() -> None:
        path = cell_name_lock._lock_path(root, "SY-1")
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            def _contend() -> None:
                with cell_name_lock.lock(root, "SY-1", "irrelevant"):
                    pass

            raised = _raised(_contend)
            assert isinstance(raised, cell_name_lock.LockHeld), repr(raised)
            assert str(raised) == "SY-1's cell is held by pid unknown's unknown"
        finally:
            os.close(fd)

    def _ending(mode: str) -> None:
        with cell_name_lock.lock(root, "SY-1", "the-holder"):
            _in_block_refusal()
            _in_block_refusal()
            if mode == "return":
                return
            if mode == "raise":
                raise RuntimeError("the holder raised")
            raise _SpyStop("the holder was interrupted")

    for mode in ("return", "raise", "interrupt"):
        raised = _raised(lambda mode=mode: _ending(mode))
        if mode == "return":
            assert raised is None, repr(raised)
        elif mode == "raise":
            assert isinstance(raised, RuntimeError), repr(raised)
        else:
            assert isinstance(raised, _SpyStop), repr(raised)
        assert cell_name_lock._lock_path(root, "SY-1").read_text() == ""
        _stale_window_refusal()


def test_the_spec_id_lock_empties_its_file_before_it_lets_go(tmp_path):
    from saffron import cell_name_lock

    root = tmp_path / "locks"
    with cell_name_lock.lock(root, "SY-1", "warmup"):
        pass
    lock_path = cell_name_lock._lock_path(root, "SY-1")

    def _relock_as_successor() -> None:
        fd = os.open(lock_path, os.O_RDWR | os.O_TRUNC)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(fd, b"4242 next\n")
            os.fsync(fd)
        finally:
            os.close(fd)

    def _ending(mode: str) -> None:
        with cell_name_lock.lock(root, "SY-1", "the-holder"):
            if mode == "return":
                return
            if mode == "raise":
                raise RuntimeError("the holder raised")
            raise _SpyStop("the holder was interrupted")

    for mode in ("return", "raise", "interrupt"):
        probe = _ReleaseProbe(lock_path, _relock_as_successor)
        with pytest.MonkeyPatch.context() as mp:
            probe.patch(mp)
            raised = _raised(lambda mode=mode: _ending(mode))

        if mode == "return":
            assert raised is None, repr(raised)
        elif mode == "raise":
            assert isinstance(raised, RuntimeError), repr(raised)
        else:
            assert isinstance(raised, _SpyStop), repr(raised)

        assert probe.released, "the probe never saw a release"
        assert probe.content_at_release == ""
        assert lock_path.read_text() == "4242 next\n"
