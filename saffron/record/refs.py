"""The record on `refs/saffron/*`. A cell reaches neither these refs nor their
objects, measured two ways in `docs/evidence/2026-09-17-state-on-git-refs.md`.

Standard library only, git by `subprocess`, as `saffron/cell/worktree.py` does.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from saffron.record.contract import Fact

TASKS = "refs/saffron/tasks"
VALUES = "refs/saffron/values"
_FACTS = "facts"


class RefsRecord:
    def __init__(self, repo: Path, remote: str | None = None) -> None:
        self._repo = repo
        self._remote = remote

    def _git(self, *args: str, stdin: str | None = None) -> str:
        done = subprocess.run(
            ["git", "-C", str(self._repo), *args],
            input=stdin,
            capture_output=True,
            text=True,
            check=True,
        )
        return done.stdout

    def append(self, task_key: str, fact: Fact) -> None:
        ref = f"{TASKS}/{task_key}"
        parent = self._resolve(ref)
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

    def _push(self, remote: str, ref: str) -> None:
        # No `--force`: a non-fast-forward refusal is how a stale writer
        # learns it is stale, the primitive a cross-host budget depends on.
        self._git("push", remote, f"{ref}:{ref}")

    def _resolve(self, ref: str) -> str | None:
        # Exit 1 is a genuinely absent ref; anything else is a broken repo, and
        # collapsing that into "no facts" is the `error` != `fail` mistake.
        try:
            return self._git("rev-parse", "--verify", "-q", ref).strip()
        except subprocess.CalledProcessError as exc:
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

    def read(self, task_key: str) -> list[Fact]:
        facts = []
        for seq, sha in self._blobs(task_key):
            raw = self._git("cat-file", "blob", sha)
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
        held = (
            self._git("cat-file", "blob", f"{current}:value").strip()
            if current
            else None
        )
        if held != expected:
            return False
        blob = self._git("hash-object", "-w", "--stdin", stdin=new).strip()
        tree = self._git("mktree", stdin=f"100644 blob {blob}\tvalue\n").strip()
        args = ["commit-tree", tree, "-m", f"{key} = {new}"]
        if current:
            args += ["-p", current]
        commit = self._git(*args).strip()
        self._git("update-ref", ref, commit, current or "")
        return True
