"""One lock per spec id, shared by every home of one user.

A task's networks, proxy, container and volumes carry its spec id alone
(`DESIGN.md` §5.1), and each is removed before it is created
(`saffron/cell/session.py`). Two homes running the same spec id at once
share nothing but that: a live cell on one home is indistinguishable from
a dead process's leftover to the other's pre-clean. This lock closes that
gap without touching the cell runtime at all (`b-d9ed45`).

An exclusive, non-blocking `flock` on one file per spec id, named the way
the cell's own networks and proxy are (`saffron/cell/session.py`,
`saffron/cell/proxy.py`): the spec id lowercased. A holder already there
raises `LockHeld` at once, naming its pid and the text it wrote. This
module never waits. An `flock` belongs to the holder's open file
description. The kernel drops it once every descriptor there closes, so
a SIGKILLed holder frees the spec id with no cleanup needed.
"""

from __future__ import annotations

import fcntl
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class LockRootUnsafe(Exception):
    """`root`, or the lock file inside it, is not safe to use: not a
    directory, not owned by `os.getuid()`, or a symlink in either place.

    Raised before any lock is attempted, and never a `Refused`: there is no
    holder to name for a root that is wrong rather than taken.
    """


class LockHeld(Exception):
    """Another process already holds `spec_id`'s lock.

    `holder_pid` and `holder_text` are read from the lock file before this
    is raised, from the line the holder wrote after it took the lock.
    `str()` is the text `run_task` uses as its refusal reason.
    """

    def __init__(self, spec_id: str, holder_pid: int, holder_text: str) -> None:
        self.spec_id = spec_id
        self.holder_pid = holder_pid
        self.holder_text = holder_text
        super().__init__(
            f"{spec_id}'s cell is held by pid {holder_pid}'s {holder_text}"
        )


def _lock_path(root: Path, spec_id: str) -> Path:
    return root / f"{spec_id.lower()}.lock"


def _ensure_root_safe(root: Path) -> None:
    """Make `root` with mode `0700` if it is not there yet, then check it
    is this user's own directory. Raises `LockRootUnsafe` otherwise.
    `lstat`, never `stat`: a symlinked root fails this, rather than being
    followed.
    """
    root.mkdir(mode=0o700, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise LockRootUnsafe(f"{root} is not a directory")
    if info.st_uid != os.getuid():
        raise LockRootUnsafe(f"{root} is not owned by uid {os.getuid()}")


def _read_holder(handle) -> tuple[int, str]:
    handle.seek(0)
    line = handle.readline().rstrip("\n")
    pid_text, _, holder_text = line.partition(" ")
    try:
        pid = int(pid_text)
    except ValueError:
        pid = -1
    return pid, holder_text


@contextmanager
def lock(root: Path, spec_id: str, text: str) -> Iterator[None]:
    """Hold `spec_id`'s lock under `root` for as long as the block runs, by
    return or by raise. Never waits: a lock already held raises `LockHeld`
    at once, naming the holder the file names.

    Opened `O_RDWR | O_CREAT | O_NOFOLLOW`, never `O_TRUNC`: a contender
    this refuses still reads the holder's line out of the file, and a
    symlink in its place raises `OSError` rather than being followed. Only
    once the lock is taken does this truncate and write `text` beside this
    process's own pid.
    """
    _ensure_root_safe(root)
    path = _lock_path(root, spec_id)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    handle = os.fdopen(fd, "r+")
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pid, holder_text = _read_holder(handle)
            raise LockHeld(spec_id, pid, holder_text) from None
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()} {text}\n")
        handle.flush()
        yield
