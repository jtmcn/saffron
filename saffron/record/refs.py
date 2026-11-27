"""The record on `refs/saffron/*`. A cell reaches neither these refs nor their
objects, measured two ways in `docs/evidence/2026-09-17-state-on-git-refs.md`.

Standard library only, git by `subprocess`, as `saffron/cell/worktree.py` does.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
from pathlib import Path

from saffron.record.contract import (
    Fact,
    RecordError,
    StaleWriter,
    check_filed_under,
)

# On the command, as `phases/package.py` does and for its reason: a mirror
# inherits no identity, so `commit-tree` fell to whatever the host had.
_IDENT = ("-c", "user.email=saffron@localhost", "-c", "user.name=Saffron")


# ponytail: this overrides a host's `core.sshCommand` and `GIT_SSH`, keeping only `GIT_SSH_COMMAND`.
def _no_prompt() -> dict[str, str]:
    """The host's environment, with neither git nor ssh able to ask for a credential."""
    out = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    ssh = out.get("GIT_SSH_COMMAND") or "ssh"
    out["GIT_SSH_COMMAND"] = f"{ssh} -o BatchMode=yes"
    return out


TASKS = "refs/saffron/tasks"
VALUES = "refs/saffron/values"
_FACTS = "facts"

# Measured: a dry-run push takes 1.3-1.4s. Chosen: 120s clears keepalive's 60s
# give-up. Read at call time, so a witness can patch it (b-65eb8f).
PUSH_TIMEOUT_S = 120

# Reasoned, as `_REAP_S` is in `saffron/cell/runtime.py`: a killed group
# closes its pipes at once, so this bounds only a child that left the group.
_PUSH_REAP_S = 5.0

_KEEPALIVE = ("-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4")


def _kill_group(proc: subprocess.Popen) -> None:
    # Measured on macOS: a group left holding only a zombie answers EPERM,
    # not ESRCH, the same shape `saffron/cell/runtime.py`'s `_kill_group` guards.
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(proc.pid, signal.SIGKILL)


class RefsRecord:
    def __init__(
        self, repo: Path, remote: str | None = None, origin: str | None = None
    ) -> None:
        self._repo = repo
        self._remote = remote
        # Only `_recover` reads this. The auto-push in `append` stays keyed
        # on `remote` alone, so a `RoutedRecord`'s appends stay local.
        self._origin = origin

    def _git(self, *args: str, stdin: str | None = None) -> str:
        return self._git_bytes(
            *args, stdin=stdin.encode() if stdin is not None else None
        ).decode()

    def _git_bytes(
        self,
        *args: str,
        stdin: bytes | None = None,
    ) -> bytes:
        done = subprocess.run(
            ["git", "-C", str(self._repo), *_IDENT, *args],
            input=stdin,
            capture_output=True,
            env=_no_prompt(),
        )
        if done.returncode != 0:
            # `check=True` would raise a `CalledProcessError` that names the
            # argv and drops the reason, which is the one thing a caller needs.
            stderr = done.stderr.decode(errors="replace")
            raise RecordError(
                f"git {args[0]} failed ({done.returncode}): {stderr.strip()}",
                returncode=done.returncode,
                stderr=stderr,
            )
        return done.stdout

    def append(self, task_key: str, fact: Fact) -> None:
        """Append one fact onto `task_key`'s own ref.

        Only `task_created` starts a ref this repo lacks. Any other kind
        first calls `_recover`, recovering the ref from `remote` or `origin`
        before the append proceeds.
        """
        check_filed_under(task_key, fact)
        ref = f"{TASKS}/{task_key}"
        parent = self._resolve(ref)
        if parent is None and fact.kind != "task_created":
            parent = self._recover(ref)
        blobs = self._blobs(task_key)
        seq = len(blobs) + 1
        blob = self._git("hash-object", "-w", "--stdin", stdin=fact.to_json()).strip()
        tree = self._tree_with(blobs + [(seq, blob)])
        args = ["commit-tree", tree, "-m", f"{fact.kind} {task_key}"]
        if parent:
            args += ["-p", parent]
        commit = self._git(*args).strip()
        # `update-ref` with the old value is the local half of the same
        # compare-and-swap a push gets from git's fast-forward refusal.
        self._git("update-ref", ref, commit, parent or "")
        # ponytail: the local ref lands before the push below, so a refused push
        # stalls it on history the remote will never take without a rollback or a re-derive.
        remote = self._remote
        if remote:
            self._push(remote, ref)

    def _recover(self, ref: str) -> str:
        """The parent a later fact needs when this repo lacks `ref`.

        Fetches `ref` once, from `remote` or `origin`, whichever is set.
        Raises `RecordError` where neither is set, or where the one tried
        lacks `ref` too: a later fact needs a ref that already opens on
        `task_created`.
        """
        source = self._remote or self._origin
        fetched: RecordError | None = None
        if source:
            try:
                self._fetch_one(source, ref)
            except RecordError as exc:
                fetched = exc
            parent = self._resolve(ref)
            if parent is not None:
                return parent
        reason = f". The fetch from {source} said: {fetched}" if fetched else ""
        raise RecordError(
            f"{ref} is absent here, and the fact is not task_created: "
            f"a later fact needs a ref that already opens on task_created{reason}"
        ) from fetched

    def _fetch_one(self, remote: str, ref: str) -> None:
        """Fetch exactly `ref` from `remote` into the same name."""
        self._git_bytes("fetch", remote, f"{ref}:{ref}")

    def _tree_with(self, blobs: list[tuple[int, str]]) -> str:
        # `git mktree` refuses a slash in an entry's name, so the "facts/NNNN.json"
        # layout is two trees: a `facts` subtree, wrapped by the root.
        facts_entries = "".join(
            f"100644 blob {sha}\t{n:04d}.json\n" for n, sha in blobs
        )
        facts_tree = self._git("mktree", stdin=facts_entries).strip()
        return self._git(
            "mktree", stdin=f"040000 tree {facts_tree}\t{_FACTS}\n"
        ).strip()

    def push(self, task_key: str, remote: str) -> None:
        """Push one task's own ref to `remote`, nothing else. A non-fast-forward
        keeps raising `StaleWriter` through `_push`. A hook decline or a dead
        remote surfaces as the plain `RecordError` `_push` already raises for
        anything that is not `[rejected]`."""
        self._push(remote, f"{TASKS}/{task_key}")

    def fetch(self, remote: str) -> None:
        """Pull every task ref from `remote`, pruning one this repo holds that
        `remote` no longer does. Scoped to `refs/saffron/tasks/*` alone, so a
        mirror's branches and its `refs/saffron/values/*` are left as they were."""
        self._git("fetch", "--prune", remote, f"+{TASKS}/*:{TASKS}/*")

    def _keepalive_args(self) -> tuple[str, ...]:
        """`ServerAliveInterval`/`CountMax`, where this host names no
        `GIT_SSH_COMMAND` and this mirror resolves no `core.sshCommand`.
        An exit from that read other than 0 (set) or 1 (unset) is a mirror
        git cannot read, and raises before any push starts."""
        if "GIT_SSH_COMMAND" in os.environ:
            return ()
        try:
            self._git("config", "--get", "core.sshCommand")
        except RecordError as exc:
            if exc.returncode != 1:
                raise
            return _KEEPALIVE
        return ()

    def _push_env(self) -> dict[str, str]:
        env = _no_prompt()
        keepalive = self._keepalive_args()
        if keepalive:
            env["GIT_SSH_COMMAND"] += " " + " ".join(keepalive)
        return env

    def _push(self, remote: str, ref: str) -> None:
        # No `--force`: a stale writer must see the refusal, not an overwrite.
        # Run by hand, in its own process group, so a stall can be killed alone.
        argv = ["git", "-C", str(self._repo), *_IDENT, "push", remote, f"{ref}:{ref}"]
        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self._push_env(),
                process_group=0,
            )
        except OSError as exc:
            raise RecordError(f"git push could not be executed: {exc}") from exc
        try:
            _, stderr = proc.communicate(timeout=PUSH_TIMEOUT_S)
        except subprocess.TimeoutExpired as expired:
            _kill_group(proc)
            try:
                _, stderr = proc.communicate(timeout=_PUSH_REAP_S)
            except subprocess.TimeoutExpired as late:
                # A child outside the group can still hold a pipe open.
                # Keep what was read. The kill ended git, so this wait returns at once.
                stderr = late.stderr
                proc.wait()
            raise RecordError(
                f"git push did not finish within {PUSH_TIMEOUT_S}s",
                returncode=124,
                stderr=(stderr or b"").decode(errors="replace"),
            ) from expired
        except BaseException:
            # Ctrl-C and SIGTERM reach here as `KeyboardInterrupt`.
            # Let it go on unchanged, once git itself is gone.
            _kill_group(proc)
            proc.wait()
            raise
        if proc.returncode == 0:
            return
        text = (stderr or b"").decode(errors="replace")
        if "[rejected]" not in text:
            # git writes "! [rejected]" for the refusal and nothing else.
            # A full disk or a dead remote stays the error it already is.
            raise RecordError(
                f"git push failed ({proc.returncode}): {text.strip()}",
                returncode=proc.returncode,
                stderr=text,
            )
        raise StaleWriter(
            f"{remote} refused {ref}: {text.strip()}",
            returncode=proc.returncode,
            stderr=text,
        )

    def _resolve(self, ref: str) -> str | None:
        # Exit 1 is a genuinely absent ref; anything else is a broken repo, and
        # collapsing that into "no facts" is the `error` != `fail` mistake.
        try:
            return self._git("rev-parse", "--verify", "-q", ref).strip()
        except RecordError as exc:
            if exc.returncode != 1:
                raise
            return None

    def _blobs(self, task_key: str) -> list[tuple[int, str]]:
        ref = f"{TASKS}/{task_key}"
        if not self._resolve(ref):
            return []
        found = []
        for line in self._git("ls-tree", "-r", ref).splitlines():
            mode_type_sha, name = line.split("\t", 1)
            prefix = f"{_FACTS}/"
            if not name.startswith(prefix):
                continue
            seq = int(name.removeprefix(prefix).removesuffix(".json"))
            found.append((seq, mode_type_sha.split()[2]))
        return sorted(found)

    def _cat_blobs(self, shas: list[str]) -> list[str]:
        """One `cat-file --batch` for a whole task, never one process a fact.
        The fold measured 24 ms a fact when each was its own spawn, and packing
        the record saved 1%, so the cost was the spawns
        (`docs/evidence/2026-09-20-fold-rebuild-time.md`)."""
        if not shas:
            return []
        out = self._git_bytes(
            "cat-file", "--batch", stdin=("\n".join(shas) + "\n").encode()
        )
        blobs = []
        at = 0
        for sha in shas:
            # `<sha> blob <size>\n<contents>\n`, or `<sha> missing\n` over
            # exit 0, which must not read as an empty log. `error` != `fail`.
            end = out.find(b"\n", at)
            header = out[at : end if end != -1 else len(out)].decode(errors="replace")
            fields = header.split()
            if end == -1 or len(fields) != 3 or fields[1] != "blob":
                raise RecordError(f"git cat-file gave no blob for {sha}: {header}")
            size = int(fields[2])
            start = end + 1
            if start + size > len(out):
                raise RecordError(f"git cat-file truncated {sha} at {size} bytes")
            blobs.append(out[start : start + size].decode())
            at = start + size + 1
        return blobs

    def read(self, task_key: str) -> list[Fact]:
        blobs = self._blobs(task_key)
        facts = []
        raws = self._cat_blobs([sha for _, sha in blobs])
        for (seq, _), raw in zip(blobs, raws, strict=True):
            try:
                facts.append(Fact.from_json(raw))
            except ValueError as exc:
                raise ValueError(
                    f"task {task_key} fact {seq:04d} is unreadable: {exc}"
                ) from exc
        return facts

    def task_keys(self) -> list[str]:
        out = self._git("for-each-ref", "--format=%(refname)", TASKS)
        return [line[len(TASKS) + 1 :] for line in out.splitlines() if line]

    def compare_and_swap(self, key: str, expected: str | None, new: str) -> bool:
        ref = f"{VALUES}/{key}"
        current = self._resolve(ref)
        # No `.strip()`: stripping made a value with surrounding whitespace
        # unmatchable by its own text, so no caller could swap on what it read.
        held = self._git("cat-file", "blob", f"{current}:value") if current else None
        if held != expected:
            return False
        blob = self._git("hash-object", "-w", "--stdin", stdin=new).strip()
        tree = self._git("mktree", stdin=f"100644 blob {blob}\tvalue\n").strip()
        args = ["commit-tree", tree, "-m", f"{key} = {new}"]
        if current:
            args += ["-p", current]
        commit = self._git(*args).strip()
        try:
            self._git("update-ref", ref, commit, current or "")
        except RecordError as exc:
            # The value moved between the read above and this write, which is
            # the race the swap exists to report rather than raise on.
            if "but expected" not in exc.stderr:
                raise
            return False
        return True
