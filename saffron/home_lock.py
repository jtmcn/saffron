"""One exclusive lock per `--home`.

It keeps a batch scan from running beside a live `cell`, `batch` or
`draft` on the same home. Without it, that scan can mistake a live task's
row for the corpse `DESIGN.md` §4.2.1 lets it assume (backlog item
b-a714d2, b-615466).

`cli.main` holds the lock for the whole of each such command. No other
command takes it.

The lock file sits beside `ledger.db`, never truncated before the lock is
taken. A contender the lock refuses still reads the holder's pid and
command from that file.
"""

from __future__ import annotations

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

_LOCK_NAME = "ledger.lock"


class HomeLocked(Exception):
    """Another command already holds `home`'s lock.

    `pid` and `command` come from the lock file the holder wrote, read
    before this exception is raised. Either is `None` when the file is
    read between the holder's truncate and its write.
    """

    def __init__(self, pid: int | None, command: str | None) -> None:
        self.pid = pid
        self.command = command
        super().__init__(
            f"held by pid {pid if pid is not None else 'unknown'} "
            f"running {command if command is not None else 'unknown'}"
        )


def _read_holder(handle: TextIO) -> tuple[int | None, str | None]:
    handle.seek(0)
    line = handle.readline().rstrip("\n")
    pid_text, _, command = line.partition(" ")
    try:
        pid: int | None = int(pid_text)
    except ValueError:
        pid = None
    return pid, (command or None)


@contextmanager
def lock(home: Path, command: str) -> Iterator[None]:
    """Hold `home`'s lock for `command`, for as long as the block runs, by
    return or by raise. Never waits: a lock already held raises
    `HomeLocked` at once, naming the holder the file names.

    Opened `O_RDWR | O_CREAT`, never `O_TRUNC`: a contender this refuses
    reads the holder's line out of the file it was refused on. The
    descriptor is non-inheritable by Python's own default (PEP 446), so a
    child this command starts never keeps the lock once this process ends.
    """
    home.mkdir(parents=True, exist_ok=True)
    fd = os.open(home / _LOCK_NAME, os.O_RDWR | os.O_CREAT, 0o644)
    handle = os.fdopen(fd, "r+")
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pid, holder_command = _read_holder(handle)
            raise HomeLocked(pid, holder_command) from None
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()} {command}\n")
        handle.flush()
        yield
