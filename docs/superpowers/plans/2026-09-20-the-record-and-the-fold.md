# The record and the fold — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the append-only record on `refs/saffron/*` and the fold that
rebuilds `~/.saffron/ledger.db` from it, so that deleting the index and
rebuilding it produces the same rows.

**Architecture:** A `Record` is three operations over facts — `append`, `read`,
`compare_and_swap` — with two backends: an in-memory one for tests and a refs
one that commits to `refs/saffron/tasks/<task_key>` in a target's mirror. Every
`Ledger` write method also appends the fact that write represents, so for the
length of this plan both stores are written and the fold's output can be
compared against the ledger the old path produced. The fold reads the record and
writes a ledger; nothing reads the fold's output yet.

**Tech Stack:** Python 3.13, standard library only in `saffron/record/` (git via
`subprocess`, as `saffron/cell/worktree.py` already does), SQLite through the
existing `saffron.ledger.Ledger`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`

## Global Constraints

- **`saffron/` knows no languages, runners or package managers** (`DESIGN.md`
  §2.1). The record is repo-agnostic: it knows git, facts and hashes.
- **A comment is one or two lines naming the non-obvious why.** The `prose` gate
  counts them per file and a docstring stays within ten lines (`CLAUDE.md`).
- **The record holds facts and content hashes, never artifacts** (spec §2).
  A fact naming a file names its hash.
- **Vocabulary is enforced.** The record holds **facts**; `saffron/events.py`
  owns "event" for the `events.jsonl` stream, and spec §8 keeps the two
  distinct. Never call a record entry an event.
- **`error` ≠ `fail`** — never collapse them, including in a fact's payload.
- **A new test is not trusted until it has been run against the unfixed code**,
  or against a mutant that breaks the property (`CLAUDE.md`).
- **Commit subjects are lowercase `type(scope): what changed`**, written as a
  sentence about the defect rather than the file.
- Run `make check` before each commit. Run one test with
  `uv run pytest tests/test_record.py::test_name`.

## Two decisions the spec took late

Both follow from decisions the spec already made, and both were written into it
before this plan was saved. They are repeated here because every task depends on
them and a task's implementer reads only their own task.

**The record has its own task key.** `tasks.task_id` is a SQLite autoincrement.
The spec makes the ledger a deletable index rebuilt by the fold, so every
integer id in it is minted by the fold — which cannot then be the name of the
ref the fold reads. The record mints a `task_key`: 32 hex characters from
`secrets.token_hex(16)`, generated once at task creation, host-independent and
never reused. The index carries it as a new `tasks.record_key` column, which is
how the fold keys its upserts.

**A record entry is a fact, not an event.** `saffron/events.py` already owns
"event" for the stream `saffron watch` tails, and spec §8's whole purpose is to
keep the two apart. The spec's own words are "the record holds facts".

## File structure

- `saffron/record/__init__.py` — re-exports `Fact`, `Record`, `new_task_key`.
- `saffron/record/contract.py` — `Fact`, the `KINDS` closed set, `new_task_key`,
  and the `Record` protocol. The whole backend-agnostic surface, as
  `gates/contract.py` is for gates.
- `saffron/record/memory.py` — `MemoryRecord`, the in-memory backend. Tests use
  it wherever git is not what is under test.
- `saffron/record/refs.py` — `RefsRecord`, the git backend.
- `saffron/record/fold.py` — `fold(record, ledger, strict=True)`.
- `saffron/ledger.py` — modified: a `record` argument, a `record_key` column,
  and an append in every write method.
- `saffron/cli.py` — modified: the `saffron fold` command.
- `tests/test_record.py` — contract and memory backend.
- `tests/test_record_refs.py` — the git backend.
- `tests/test_fold.py` — the fold, including delete-and-rebuild.

---

### Task 1: The fact and the task key

**Files:**
- Create: `saffron/record/__init__.py`
- Create: `saffron/record/contract.py`
- Test: `tests/test_record.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Fact(kind: str, task_key: str, at: str, repo: str, batch_key: str | None, payload: dict[str, Any])`, frozen dataclass with `to_json() -> str` and `from_json(str) -> Fact`; `KINDS: tuple[str, ...]`; `new_task_key() -> str`; `Record` protocol with `append(task_key: str, fact: Fact) -> None`, `read(task_key: str) -> list[Fact]`, `task_keys() -> list[str]`, `compare_and_swap(key: str, expected: str | None, new: str) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_record.py
import json

import pytest

from saffron.record.contract import KINDS, Fact, new_task_key


def a_fact(**over):
    base = {
        "kind": "task_created",
        "task_key": "a" * 32,
        "at": "2026-09-20T00:00:00Z",
        "repo": "saffron",
        "batch_key": None,
        "payload": {"spec_id": "SA-0099"},
    }
    return Fact(**(base | over))


def test_a_task_key_is_32_hex_characters():
    key = new_task_key()
    assert len(key) == 32
    assert set(key) <= set("0123456789abcdef")


def test_two_task_keys_never_collide():
    assert len({new_task_key() for _ in range(1000)}) == 1000


def test_a_fact_round_trips_through_json():
    fact = a_fact()
    assert Fact.from_json(fact.to_json()) == fact


def test_a_fact_of_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="unknown fact kind"):
        a_fact(kind="wat")


def test_every_declared_kind_is_accepted():
    for kind in KINDS:
        assert a_fact(kind=kind).kind == kind


def test_a_fact_refuses_a_payload_json_cannot_carry():
    # A payload that fails to serialise must fail at append, not at fold time,
    # where the only record of the task is what could not be written.
    with pytest.raises(ValueError, match="payload"):
        a_fact(payload={"when": object()})


def test_a_fact_is_frozen():
    with pytest.raises(Exception):
        a_fact().kind = "task_state"


def test_from_json_refuses_a_missing_field():
    partial = json.dumps({"kind": "task_created", "task_key": "a" * 32})
    with pytest.raises(ValueError, match="missing"):
        Fact.from_json(partial)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_record.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'saffron.record'`

- [ ] **Step 3: Write the contract**

```python
# saffron/record/contract.py
"""The record's whole backend-agnostic surface: what a fact is, and what a
backend must do with one.

The record holds facts, never events — `saffron/events.py` owns that word for
the `events.jsonl` stream, and the two are deliberately separate (design §8).
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Protocol

# Closed, and one entry per thing the ledger's tables hold today. A kind that
# is not here cannot be appended, so the fold never meets one it cannot place.
KINDS = (
    "task_created",
    "task_state",
    "task_package",
    "task_push",
    "task_merged_head",
    "task_policy",
    "attempt_opened",
    "attempt_closed",
    "gate_result",
    "finding",
    "rebuttal",
    "decision",
    "run_created",
    "run_finished",
    "run_preflight",
    "batch_created",
    "batch_closed",
    "repo_upserted",
)


def new_task_key() -> str:
    """The record's own identity for a task, minted at creation. The ledger's
    `task_id` cannot serve: it is an autoincrement the fold mints, so it would
    name a ref by a number that only exists after the ref has been read."""
    return secrets.token_hex(16)


@dataclass(frozen=True)
class Fact:
    kind: str
    task_key: str
    at: str
    repo: str
    batch_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown fact kind: {self.kind!r}")
        # Refused here rather than at the backend, so a payload git cannot
        # carry fails while the caller still holds what it was trying to say.
        try:
            json.dumps(self.payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"payload is not JSON: {exc}") from exc

    def to_json(self) -> str:
        return json.dumps(
            {
                "kind": self.kind,
                "task_key": self.task_key,
                "at": self.at,
                "repo": self.repo,
                "batch_key": self.batch_key,
                "payload": self.payload,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, raw: str) -> Fact:
        data = json.loads(raw)
        missing = {"kind", "task_key", "at", "repo"} - set(data)
        if missing:
            raise ValueError(f"fact is missing {sorted(missing)}")
        return cls(
            kind=data["kind"],
            task_key=data["task_key"],
            at=data["at"],
            repo=data["repo"],
            batch_key=data.get("batch_key"),
            payload=data.get("payload", {}),
        )


class Record(Protocol):
    """Three operations and no git in any signature. `compare_and_swap` is
    unused on one host and is the seam a cross-host budget needs."""

    def append(self, task_key: str, fact: Fact) -> None: ...

    def read(self, task_key: str) -> list[Fact]: ...

    def task_keys(self) -> list[str]: ...

    def compare_and_swap(
        self, key: str, expected: str | None, new: str
    ) -> bool: ...
```

```python
# saffron/record/__init__.py
from saffron.record.contract import KINDS, Fact, Record, new_task_key

__all__ = ["KINDS", "Fact", "Record", "new_task_key"]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_record.py -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Check the spec still matches**

The spec already carries both decisions and calls a record entry a fact
throughout (§3's "Fact shape"). Confirm `KINDS` in `contract.py` and the
spec's §3 list the same kinds, and add any the spec names and the code does
not.

- [ ] **Step 6: Run the full check and commit**

```bash
make check
git add saffron/record tests/test_record.py
git commit -m "feat(record): the ledger's task_id is minted by the fold, so it cannot name the ref the fold reads"
```

---

### Task 2: The in-memory backend

**Files:**
- Create: `saffron/record/memory.py`
- Test: `tests/test_record.py` (append to it)

**Interfaces:**
- Consumes: `Fact`, `Record` from Task 1.
- Produces: `MemoryRecord()`, implementing `Record`. Used by every later test
  where git is not what is under test.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_record.py — append
from saffron.record.memory import MemoryRecord


def test_reading_a_task_with_no_facts_gives_an_empty_log():
    assert MemoryRecord().read("a" * 32) == []


def test_facts_read_back_in_append_order():
    record = MemoryRecord()
    first = a_fact(kind="task_created")
    second = a_fact(kind="task_state", payload={"state": "IMPLEMENTING"})
    record.append(first.task_key, first)
    record.append(second.task_key, second)
    assert record.read(first.task_key) == [first, second]


def test_appending_the_same_fact_twice_keeps_both():
    # Append-only means append-only: two identical gate results are two runs
    # of one gate, not one run recorded twice.
    record = MemoryRecord()
    fact = a_fact(kind="gate_result")
    record.append(fact.task_key, fact)
    record.append(fact.task_key, fact)
    assert len(record.read(fact.task_key)) == 2


def test_task_keys_lists_every_task_appended_to():
    record = MemoryRecord()
    for key in ("a" * 32, "b" * 32):
        record.append(key, a_fact(task_key=key))
    assert sorted(record.task_keys()) == ["a" * 32, "b" * 32]


def test_compare_and_swap_sets_an_absent_key():
    record = MemoryRecord()
    assert record.compare_and_swap("budget", None, "1.50") is True


def test_compare_and_swap_refuses_a_stale_writer():
    record = MemoryRecord()
    record.compare_and_swap("budget", None, "1.50")
    assert record.compare_and_swap("budget", "1.50", "2.00") is True
    assert record.compare_and_swap("budget", "1.50", "9.99") is False


def test_a_refused_swap_leaves_the_value_alone():
    record = MemoryRecord()
    record.compare_and_swap("budget", None, "1.50")
    record.compare_and_swap("budget", "wrong", "9.99")
    assert record.compare_and_swap("budget", "1.50", "2.00") is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_record.py -k memory -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'saffron.record.memory'`

- [ ] **Step 3: Write the backend**

```python
# saffron/record/memory.py
"""An in-memory `Record`. Tests use it wherever git is not what is under test,
so a fold test does not need a repository to prove the fold."""

from __future__ import annotations

from collections import defaultdict

from saffron.record.contract import Fact


class MemoryRecord:
    def __init__(self) -> None:
        self._facts: dict[str, list[Fact]] = defaultdict(list)
        self._values: dict[str, str] = {}

    def append(self, task_key: str, fact: Fact) -> None:
        self._facts[task_key].append(fact)

    def read(self, task_key: str) -> list[Fact]:
        return list(self._facts[task_key])

    def task_keys(self) -> list[str]:
        return list(self._facts)

    def compare_and_swap(
        self, key: str, expected: str | None, new: str
    ) -> bool:
        if self._values.get(key) != expected:
            return False
        self._values[key] = new
        return True
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_record.py -v`
Expected: PASS, 15 tests.

- [ ] **Step 5: Commit**

```bash
make check
git add saffron/record/memory.py tests/test_record.py
git commit -m "feat(record): a fold test needed a repository to prove the fold, so the backend gains an in-memory twin"
```

---

### Task 3: The refs backend

**Files:**
- Create: `saffron/record/refs.py`
- Test: `tests/test_record_refs.py`

**Interfaces:**
- Consumes: `Fact`, `Record` from Task 1.
- Produces: `RefsRecord(repo: Path, remote: str | None = None)`, implementing
  `Record`. `repo` is a git directory the host owns — the mirror, never a cell's
  worktree. `remote` is pushed to on each append when set, and left unset in
  tests.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_record_refs.py
import subprocess

import pytest

from saffron.record.contract import Fact
from saffron.record.refs import RefsRecord


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "mirror.git"
    subprocess.run(["git", "init", "-q", "--bare", str(path)], check=True)
    return path


def a_fact(**over):
    base = {
        "kind": "task_created",
        "task_key": "a" * 32,
        "at": "2026-09-20T00:00:00Z",
        "repo": "saffron",
        "batch_key": None,
        "payload": {"spec_id": "SA-0099"},
    }
    return Fact(**(base | over))


def test_the_first_append_creates_the_ref(repo):
    record = RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)
    out = subprocess.run(
        ["git", "-C", str(repo), "for-each-ref", "--format=%(refname)"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert f"refs/saffron/tasks/{fact.task_key}" in out


def test_facts_read_back_in_append_order(repo):
    record = RefsRecord(repo)
    first = a_fact(kind="task_created")
    second = a_fact(kind="task_state", payload={"state": "IMPLEMENTING"})
    record.append(first.task_key, first)
    record.append(second.task_key, second)
    assert record.read(first.task_key) == [first, second]


def test_each_append_adds_one_commit(repo):
    record = RefsRecord(repo)
    fact = a_fact()
    for _ in range(3):
        record.append(fact.task_key, fact)
    count = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--count",
         f"refs/saffron/tasks/{fact.task_key}"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert count == "3"


def test_an_earlier_fact_is_never_rewritten(repo):
    # Append-only is the whole interface. The first commit's sha must be
    # unchanged after later appends, or the record is a mutable store.
    record = RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)
    ref = f"refs/saffron/tasks/{fact.task_key}"
    first = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", ref],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    record.append(fact.task_key, a_fact(kind="task_state"))
    root = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", ref],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert root == first


def test_reading_an_absent_task_gives_an_empty_log(repo):
    assert RefsRecord(repo).read("f" * 32) == []


def test_task_keys_lists_every_task_ref(repo):
    record = RefsRecord(repo)
    for key in ("a" * 32, "b" * 32):
        record.append(key, a_fact(task_key=key))
    assert sorted(record.task_keys()) == ["a" * 32, "b" * 32]


def test_task_keys_ignores_branches_and_tags(repo):
    # The namespace is the record's alone: a repository's own refs must not
    # read back as tasks.
    record = RefsRecord(repo)
    record.append("a" * 32, a_fact(task_key="a" * 32))
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", f"refs/saffron/tasks/{'a' * 32}"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "refs/heads/main", head],
        check=True,
    )
    assert record.task_keys() == ["a" * 32]


def test_the_tree_carries_every_fact_so_far(repo):
    record = RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)
    record.append(fact.task_key, a_fact(kind="task_state"))
    listing = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only",
         f"refs/saffron/tasks/{fact.task_key}"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert listing == ["facts/0001.json", "facts/0002.json"]


def test_compare_and_swap_refuses_a_stale_writer(repo):
    record = RefsRecord(repo)
    assert record.compare_and_swap("budget", None, "1.50") is True
    assert record.compare_and_swap("budget", "1.50", "2.00") is True
    assert record.compare_and_swap("budget", "1.50", "9.99") is False


def test_a_corrupt_fact_blob_names_the_task_it_is_in(repo):
    # A record that cannot be read must say which task it could not read, or
    # the fold's failure names only the file it was parsing.
    record = RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)
    blob = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
        input="{not json", capture_output=True, text=True, check=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "-C", str(repo), "mktree"],
        input=f"100644 blob {blob}\tfacts/0001.json\n",
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(repo), "commit-tree", tree, "-m", "corrupt"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repo), "update-ref",
         f"refs/saffron/tasks/{fact.task_key}", commit],
        check=True,
    )
    with pytest.raises(ValueError, match=fact.task_key):
        record.read(fact.task_key)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_record_refs.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'saffron.record.refs'`

- [ ] **Step 3: Write the backend**

```python
# saffron/record/refs.py
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
        seq = len(self.read(task_key)) + 1
        blob = self._git("hash-object", "-w", "--stdin",
                         stdin=fact.to_json()).strip()
        entries = "".join(
            f"100644 blob {sha}\tfacts/{n:04d}.json\n"
            for n, sha in [*self._blobs(task_key), (seq, blob)]
        )
        tree = self._git("mktree", stdin=entries).strip()
        args = ["commit-tree", tree, "-m", f"{fact.kind} {task_key}"]
        if parent:
            args += ["-p", parent]
        commit = self._git(*args).strip()
        # `update-ref` with the old value is the local half of the same
        # compare-and-swap the push gets from fast-forward refusal.
        self._git("update-ref", ref, commit, parent or "")
        if self._remote:
            self._push(ref)

    def _push(self, ref: str) -> None:
        # No `--force`: a non-fast-forward refusal is how a stale writer
        # learns it is stale, and is the primitive the shared budget needs.
        self._git("push", self._remote or "", f"{ref}:{ref}")

    def _resolve(self, ref: str) -> str | None:
        try:
            return self._git("rev-parse", "--verify", "-q", ref).strip()
        except subprocess.CalledProcessError:
            return None

    def _blobs(self, task_key: str) -> list[tuple[int, str]]:
        ref = f"{TASKS}/{task_key}"
        if not self._resolve(ref):
            return []
        out = self._git("ls-tree", "-r", ref)
        found = []
        for line in out.splitlines():
            meta, name = line.split("\t", 1)
            if name.startswith("facts/"):
                found.append((int(name[6:10]), meta.split()[2]))
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
        return [line[len(TASKS) + 1:] for line in out.splitlines() if line]

    def compare_and_swap(
        self, key: str, expected: str | None, new: str
    ) -> bool:
        ref = f"{VALUES}/{key}"
        current = self._resolve(ref)
        held = self._git("cat-file", "blob", f"{current}:value").strip() \
            if current else None
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_record_refs.py -v`
Expected: PASS, 10 tests.

- [ ] **Step 5: Prove the append-only test can fail**

The property in `test_an_earlier_fact_is_never_rewritten` is already true, so
it needs a mutant (`CLAUDE.md`). In `append`, temporarily drop the parent:

```python
        args = ["commit-tree", tree, "-m", f"{fact.kind} {task_key}"]
        # MUTANT: no parent, so each append starts a new history
```

Run: `uv run pytest tests/test_record_refs.py::test_an_earlier_fact_is_never_rewritten -v`
Expected: FAIL. Then revert the mutant and confirm PASS.

- [ ] **Step 6: Commit**

```bash
make check
git add saffron/record/refs.py tests/test_record_refs.py
git commit -m "feat(record): the record had no backend a cell cannot reach, so it gains one on refs/saffron/tasks"
```

---

### Task 4: Every ledger write appends its fact

**Files:**
- Modify: `saffron/ledger.py` — constructor, `create_task`, `set_task_state`,
  `open_attempt`, `close_attempt`, `record_gate_result`, `record_findings`,
  `record_rebuttal`, `record_push`, `record_merged_head`, `record_policy`,
  `set_task_package`, `create_run`, `finish_run`, `set_run_preflight`,
  `create_batch`, `close_batch`, `upsert_repo`
- Test: `tests/test_ledger_appends.py`

**Interfaces:**
- Consumes: `Fact`, `new_task_key`, `Record` from Tasks 1–2.
- Produces: `Ledger(path, record=None)`. When `record` is given, every write
  method appends one fact. `tasks.record_key` holds the key. `Ledger.record_key(task_id) -> str` returns it.

**Why both are written:** spec §6's shape, applied one level down. The ledger's
old path keeps producing rows, so Task 5's fold has something to be compared
against that was not produced by the code under test. `record=None` keeps every
existing caller working unchanged, which is what keeps this task's diff a
addition rather than a migration.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ledger_appends.py
import pytest

from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.memory import MemoryRecord


@pytest.fixture
def record():
    return MemoryRecord()


@pytest.fixture
def ledger(tmp_path, record):
    made = Ledger(tmp_path / "ledger.db", record=record)
    yield made
    made.close()


@pytest.fixture
def task(ledger):
    repo_id = ledger.upsert_repo("saffron", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id, spec_id="SA-0099", spec_sha="s" * 64,
        branch="saffron/SA-0099", risk="elevated", budget_usd=12,
    )
    return run_id, task_id


def kinds(record, key):
    return [f.kind for f in record.read(key)]


def test_creating_a_task_mints_a_record_key(ledger, task):
    _, task_id = task
    key = ledger.record_key(task_id)
    assert len(key) == 32


def test_creating_a_task_appends_task_created(ledger, record, task):
    _, task_id = task
    key = ledger.record_key(task_id)
    assert kinds(record, key) == ["task_created"]
    fact = record.read(key)[0]
    assert fact.payload["spec_id"] == "SA-0099"
    assert fact.payload["risk"] == "elevated"


def test_a_declared_risk_and_an_absent_one_are_distinguishable(ledger, record):
    # The defect item 170 exists to kill: `standard` by default and `standard`
    # by declaration must not read the same in the record.
    repo_id = ledger.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    undeclared = ledger.create_task(
        run_id, spec_id="SA-0085", spec_sha="s" * 64, branch="b",
    )
    fact = record.read(ledger.record_key(undeclared))[0]
    assert fact.payload["risk"] is None


def test_a_state_change_appends_task_state(ledger, record, task):
    _, task_id = task
    ledger.set_task_state(task_id, "IMPLEMENTING")
    key = ledger.record_key(task_id)
    assert kinds(record, key) == ["task_created", "task_state"]
    assert record.read(key)[-1].payload["state"] == "IMPLEMENTING"


def test_an_attempt_appends_on_open_and_on_close(ledger, record, task):
    _, task_id = task
    attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENTING")
    ledger.close_attempt(
        attempt_id, session_id="s", subtype="success",
        terminal_reason=None, num_turns=4, cost_usd_est=1.25,
    )
    key = ledger.record_key(task_id)
    assert kinds(record, key)[-2:] == ["attempt_opened", "attempt_closed"]
    assert record.read(key)[-1].payload["cost_usd_est"] == 1.25


def test_a_gate_result_carries_its_failures(ledger, record, task):
    _, task_id = task
    attempt_id = ledger.open_attempt(task_id)
    ledger.record_gate_result(
        GateResult(
            gate="lint", status="fail", tool="ruff 0.6.0", duration_ms=12,
            summary="1 error",
            failures=[Failure(file="a.py", code="E501", message="long", line=3)],
        ),
        attempt_id=attempt_id,
    )
    fact = record.read(ledger.record_key(task_id))[-1]
    assert fact.kind == "gate_result"
    assert fact.payload["status"] == "fail"
    assert fact.payload["failures"][0]["code"] == "E501"


def test_a_gate_error_is_not_recorded_as_a_failure(ledger, record, task):
    # `error` means the gate broke and is charged to nobody; `fail` means the
    # repo's code is wrong. Collapsing them in the record loses the retry
    # taxonomy the fold has to reproduce.
    _, task_id = task
    attempt_id = ledger.open_attempt(task_id)
    ledger.record_gate_result(
        GateResult(gate="lint", status="error", tool="ruff 0.6.0",
                   duration_ms=12, summary="toolchain broken"),
        attempt_id=attempt_id,
    )
    assert record.read(ledger.record_key(task_id))[-1].payload["status"] == "error"


def test_a_ledger_with_no_record_still_writes_rows(tmp_path):
    # Every existing caller passes no record, and must be unaffected.
    plain = Ledger(tmp_path / "plain.db")
    repo_id = plain.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = plain.create_run(repo_id, base_sha="a" * 40)
    task_id = plain.create_task(
        run_id, spec_id="SA-0099", spec_sha="s" * 64, branch="b",
    )
    assert plain.record_key(task_id) is None
    plain.close()


def test_every_fact_carries_the_repo_it_belongs_to(ledger, record, task):
    _, task_id = task
    ledger.set_task_state(task_id, "REVIEWING")
    assert {f.repo for f in record.read(ledger.record_key(task_id))} == {"saffron"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_ledger_appends.py -v`
Expected: FAIL, `TypeError: Ledger.__init__() got an unexpected keyword argument 'record'`

- [ ] **Step 3: Modify the ledger**

Add to `saffron/ledger.py`:

```python
from saffron.record.contract import Fact, Record, new_task_key
```

In `__init__`, accept and store the record, and add the column beside the other
additive `ALTER`s at `saffron/ledger.py:190-200`:

```python
    def __init__(self, path: Path, record: Record | None = None) -> None:
        self._record = record
        ...
        for column in (
            "pushed_sha",
            "pr_url",
            "policy_sha",
            "prompt_sha",
            "merged_head_sha",
            "record_key",
        ):
```

Add the two helpers:

```python
    def record_key(self, task_id: int) -> str | None:
        row = self._db.execute(
            "SELECT record_key FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return row["record_key"] if row else None

    def _append(self, task_id: int, kind: str, **payload: Any) -> None:
        """Every ledger write appends the fact it represents. A `None` record
        is every caller that predates the record, which must be unaffected."""
        if self._record is None:
            return
        row = self._db.execute(
            """SELECT t.record_key AS key, r.name AS repo, b.batch_id AS batch
                 FROM tasks t
                 JOIN runs rn ON rn.run_id = t.run_id
                 JOIN repos r ON r.repo_id = rn.repo_id
                 LEFT JOIN batches b ON b.batch_id = rn.batch_id
                WHERE t.task_id = ?""",
            (task_id,),
        ).fetchone()
        fact = Fact(
            kind=kind,
            task_key=row["key"],
            at=datetime.now(UTC).isoformat(),
            repo=row["repo"],
            batch_key=str(row["batch"]) if row["batch"] else None,
            payload=payload,
        )
        self._record.append(row["key"], fact)
```

In `create_task`, mint the key before the insert and append after it:

```python
        key = new_task_key() if self._record else None
        cursor = self._db.execute(
            """INSERT INTO tasks
                   (run_id, spec_id, spec_sha, state, risk, branch, budget_usd,
                    policy_sha, prompt_sha, record_key)
               VALUES (?, ?, ?, 'QUEUED', ?, ?, ?, ?, ?, ?)""",
            (run_id, spec_id, spec_sha, risk, branch, budget_usd,
             policy_sha, prompt_sha, key),
        )
        self._db.commit()
        task_id = _inserted_id(cursor)
        self._append(
            task_id, "task_created", spec_id=spec_id, spec_sha=spec_sha,
            branch=branch, risk=declared_risk, budget_usd=budget_usd,
            policy_sha=policy_sha, prompt_sha=prompt_sha,
            **self._run_facts(run_id),
        )
        return task_id
```

`_run_facts` is **Ruling R1**: the fold has to insert `repos` and `runs` rows,
and `repos.origin`, `repos.mirror_path` and `runs.base_sha` are all `NOT NULL`.
A run is a fold over its task facts (spec §5), so the facts have to carry them:

```python
    def _run_facts(self, run_id: int) -> dict[str, Any]:
        """What the fold needs to rebuild the `repos` and `runs` rows this task
        hangs from. A run has no record of its own — it is a fold over the
        tasks that name it (design §5)."""
        row = self._db.execute(
            """SELECT rn.base_sha, r.origin, r.mirror_path
                 FROM runs rn JOIN repos r ON r.repo_id = rn.repo_id
                WHERE rn.run_id = ?""",
            (run_id,),
        ).fetchone()
        return {
            "base_sha": row["base_sha"],
            "origin": row["origin"],
            "mirror_path": row["mirror_path"],
        }
```

`declared_risk` is the change that closes item 170's own defect. Give
`create_task` a sentinel default so a declared `standard` and an absent one are
different values:

```python
    def create_task(
        self,
        run_id: int,
        spec_id: str,
        spec_sha: str,
        branch: str,
        risk: str | None = None,
        ...
    ) -> int:
        # `None` means the spec declared no tier; the column still defaults to
        # `standard` because the index's consumers read it (item 170).
        declared_risk = risk
        risk = risk or "standard"
```

Then add one `self._append(...)` call at the end of each remaining write
method, using the kind from `KINDS` and the method's own arguments as the
payload.

**Ruling R3, and it is exact:** `attempt_closed`'s payload is precisely
`close_attempt`'s keyword arguments — `session_id`, `model`, `subtype`,
`terminal_reason`, `num_turns`, `cost_usd_est` — and nothing else. Task 5's
fold calls `ledger.close_attempt(attempt_id, **fact.payload)`, so an extra or
renamed key is a `TypeError` at fold time. For the run-, batch- and repo-level methods, which have no `task_id`,
append nothing in this task — they are folded from the task facts they appear
in (spec §5), and Task 5's fold proves it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_ledger_appends.py tests/test_ledger.py -v`
Expected: PASS, 9 new tests and every existing ledger test unchanged.

- [ ] **Step 5: Run the whole suite**

Run: `make check`
Expected: 2,462 existing tests still pass. Any failure here is a caller the
`record=None` default did not cover, and is fixed rather than skipped.

- [ ] **Step 6: Commit**

```bash
git add saffron/ledger.py tests/test_ledger_appends.py
git commit -m "feat(ledger): a declared standard tier and an absent one were one value, so the record takes them as two"
```

---

### Task 5: The fold, and delete-and-rebuild against real nights

**Files:**
- Create: `saffron/record/fold.py`
- Modify: `saffron/cli.py` — add the `fold` command
- Test: `tests/test_fold.py`

**Interfaces:**
- Consumes: `Record`, `Fact` from Tasks 1–3; `Ledger` from Task 4.
- Produces: `fold(record: Record, ledger: Ledger) -> int`, returning the number
  of tasks folded. `saffron fold --repo <path> --into <ledger.db>`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_fold.py
import pytest

from saffron.gates.contract import GateResult
from saffron.ledger import Ledger
from saffron.record.fold import fold
from saffron.record.memory import MemoryRecord


@pytest.fixture
def record():
    return MemoryRecord()


def a_night(tmp_path, record):
    """One task through creation, an attempt, a gate result and a state."""
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p" * 64)
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id, spec_id="SA-0099", spec_sha="s" * 64,
        branch="saffron/SA-0099", risk="elevated", budget_usd=12,
    )
    attempt_id = source.open_attempt(task_id, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 0.6.0",
                   duration_ms=9, summary="clean"),
        attempt_id=attempt_id,
    )
    source.close_attempt(
        attempt_id, session_id="s", subtype="success", terminal_reason=None,
        num_turns=4, cost_usd_est=1.25,
    )
    source.set_task_state(task_id, "READY_FOR_REVIEW")
    return source


def rows(ledger):
    """Every row that describes the night, with the autoincrement ids left
    out — the fold mints those, so they are not what has to match."""
    tasks = [
        dict(r) for r in ledger._db.execute(
            "SELECT spec_id, spec_sha, state, risk, branch, budget_usd,"
            "       spent_usd_est, record_key FROM tasks ORDER BY record_key"
        )
    ]
    attempts = [
        dict(r) for r in ledger._db.execute(
            "SELECT phase, n, session_id, subtype, num_turns, cost_usd_est"
            "  FROM attempts ORDER BY phase, n"
        )
    ]
    gates = [
        dict(r) for r in ledger._db.execute(
            "SELECT gate, status, tool, summary FROM gate_results ORDER BY gate"
        )
    ]
    return tasks, attempts, gates


def test_folding_an_empty_record_makes_no_rows(tmp_path, record):
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into) == 0
    assert rows(into)[0] == []
    into.close()


def test_the_fold_reproduces_the_task(tmp_path, record):
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into) == 1
    assert rows(into)[0] == rows(source)[0]
    source.close()
    into.close()


def test_the_fold_reproduces_attempts_and_gate_results(tmp_path, record):
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    _, attempts, gates = rows(into)
    _, want_attempts, want_gates = rows(source)
    assert attempts == want_attempts
    assert gates == want_gates
    source.close()
    into.close()


def test_delete_the_index_rebuild_it_and_get_the_same_rows(tmp_path, record):
    # Spec §4's acceptance criterion, and the reason the ledger may be deleted
    # at any time.
    source = a_night(tmp_path, record)
    first = Ledger(tmp_path / "a.db")
    fold(record, first)
    want = rows(first)
    first.close()
    (tmp_path / "a.db").unlink()

    second = Ledger(tmp_path / "a.db")
    fold(record, second)
    assert rows(second) == want
    second.close()
    source.close()


def test_folding_twice_into_one_ledger_does_not_double_the_rows(tmp_path, record):
    # The fold is an upsert keyed on `record_key`, not an append: a rebuild
    # that runs twice must be indistinguishable from one that ran once.
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    once = rows(into)
    fold(record, into)
    assert rows(into) == once
    source.close()
    into.close()


def test_the_fold_keeps_error_and_fail_apart(tmp_path, record):
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id, spec_id="SA-0099", spec_sha="s" * 64, branch="b",
    )
    attempt_id = source.open_attempt(task_id)
    for status in ("error", "fail"):
        source.record_gate_result(
            GateResult(gate=f"g-{status}", status=status, tool="t",
                       duration_ms=1, summary=status),
            attempt_id=attempt_id,
        )
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    assert [g["status"] for g in rows(into)[2]] == ["error", "fail"]
    source.close()
    into.close()


def test_an_unreadable_task_names_itself_and_folds_the_rest(tmp_path, record):
    # A record one task cannot be read from must still produce an index of
    # the others, or one bad task costs a whole night's page.
    a_night(tmp_path, record)
    record.append("f" * 32, record.read(record.task_keys()[0])[0])
    record._facts["f" * 32] = ["not a fact"]
    into = Ledger(tmp_path / "into.db")
    with pytest.raises(ValueError, match="f" * 32):
        fold(record, into, strict=True)
    assert fold(record, into, strict=False) == 1
    into.close()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_fold.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'saffron.record.fold'`

- [ ] **Step 3: Write the fold**

```python
# saffron/record/fold.py
"""Record -> index. The ledger holds no fact of its own after this: every row
is replayed from the task facts, so deleting it costs nothing.

Replay, not snapshot: a task's state is what its facts add up to (design §3).
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.contract import Fact, Record


def fold(record: Record, ledger: Ledger, strict: bool = True) -> int:
    folded = 0
    for key in sorted(record.task_keys()):
        try:
            facts = record.read(key)
        except (ValueError, TypeError, AttributeError) as exc:
            if strict:
                raise ValueError(f"task {key} is unreadable: {exc}") from exc
            continue
        _fold_task(ledger, key, facts)
        folded += 1
    return folded


def _fold_task(ledger: Ledger, key: str, facts: list[Fact]) -> None:
    created = next(f for f in facts if f.kind == "task_created")
    run_id = _run_for(ledger, created)
    task_id = _upsert_task(ledger, key, run_id, created)
    attempt_id: int | None = None
    for fact in facts:
        if fact.kind == "attempt_opened":
            attempt_id = ledger.open_attempt(task_id, phase=fact.payload["phase"])
        elif fact.kind == "attempt_closed" and attempt_id is not None:
            ledger.close_attempt(attempt_id, **fact.payload)
        elif fact.kind == "gate_result":
            ledger.record_gate_result(
                _gate_result(fact), attempt_id=attempt_id
            )
        elif fact.kind == "task_state":
            ledger.set_task_state(task_id, fact.payload["state"])


def _gate_result(fact: Fact) -> GateResult:
    data = dict(fact.payload)
    failures = [Failure(**f) for f in data.pop("failures", [])]
    return GateResult(failures=failures, **data)
```

The implementer writes `_run_for` and `_upsert_task` to match: `_run_for`
upserts the repo and the run the fact names, and `_upsert_task` inserts the task
with its `record_key` or returns the existing `task_id` for that key. Keying on
`record_key` is what makes `test_folding_twice_into_one_ledger_does_not_double_the_rows`
pass.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_fold.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Add the CLI command**

In `saffron/cli.py`, beside the existing subcommands:

```python
def _fold(args: argparse.Namespace) -> int:
    """Rebuild the index from the record. The index is deletable, so this
    command is the whole of its recovery story (design §4)."""
    record = RefsRecord(Path(args.repo))
    ledger = Ledger(Path(args.into))
    try:
        count = fold(record, ledger, strict=not args.skip_unreadable)
    finally:
        ledger.close()
    print(f"folded {count} tasks into {args.into}")
    return 0
```

- [ ] **Step 6: Measure the rebuild, which is what decides the open question**

The spec leaves open whether the fold runs continuously or on demand, and says
the number that decides it is rebuild time. Produce it:

```bash
uv run python - <<'PY'
import time
from pathlib import Path
from saffron.ledger import Ledger
from saffron.record.fold import fold
from saffron.record.refs import RefsRecord

record = RefsRecord(Path.home() / ".saffron" / "mirrors" / "saffron.git")
out = Path("/tmp/fold-bench.db")
out.unlink(missing_ok=True)
ledger = Ledger(out)
start = time.monotonic()
n = fold(record, ledger)
print(f"{n} tasks in {time.monotonic() - start:.2f}s")
ledger.close()
PY
```

Write the number into a new evidence record,
`docs/evidence/2026-09-20-fold-rebuild-time.md`, naming the task count, the
fact count and the wall clock. That record is what the second plan's budget
fold argues from.

- [ ] **Step 7: Commit**

```bash
make check
git add saffron/record/fold.py saffron/cli.py tests/test_fold.py docs/evidence/2026-09-20-fold-rebuild-time.md
git commit -m "feat(record): the index had no way back from the record, so the fold rebuilds it and a test deletes it first"
```

---

## Where the shipped code diverged from Task 5

Recorded rather than rewritten: the snippets above are what was planned, and
these four are what a review of the branch changed after it. The code is
authoritative; read `saffron/record/fold.py` and `saffron/cli.py` first.

- **`fold` returns a `Fold`, not an `int`.** The plan's `fold(record, ledger)
  -> int` gives the CLI a count with the skipped tasks left out, and an exit
  code cannot be decided from it. The dataclass carries `folded` and a
  `(task_key, reason)` per skip, so the printing lives in the CLI.
- **An unreadable task is `UnreadableTask`, not `ValueError`.** The plan catches
  `(ValueError, TypeError, AttributeError)` around `record.read`, which reaches
  neither `RefsRecord`'s `RecordError` nor a replay failure. `_facts_of` checks
  the backend's contract at the seam, and everything past it aborts as itself.
- **`saffron fold` exits 1 when it skipped a task**, in both modes, where the
  plan's `_fold` returns 0 always. A rebuild short of tasks is not the ledger
  back, and exit 2 would call an unreadable record an infrastructure failure.
- **The plan's argparse block never adds `--skip-unreadable`** although its
  `_fold` reads `args.skip_unreadable`. The shipped parser adds it.

## What this plan does not do

Design steps 3 to 6, which need the rebuild-time measurement Task 5 produces:

- **Migration of the 99 stored tasks** (spec §7).
- **The batch and run folds, and `batch.py:194`** (spec §5). The open question
  in the spec — continuous or on-demand fold — changes whether the budget check
  reads the record or the index, so it is decided from Task 5's number first.
- **`queue.json` as a render, its equality check, and its removal** (spec §6).
- **The document amendments and the appendix** (spec §11). By hand; a cell can
  land none of it.

## Self-review

**Spec coverage.** §2's three operations are Task 1 and Task 2; the facts-not-
artifacts rule is Task 1's payload validation. §3's ref layout, cumulative tree,
no-force push and replay are Task 3. §4's fold and its delete-and-rebuild
criterion are Task 5. §7's `risk` separation is Task 4, taken early because the
fact shape has to carry it from the first append. §5, §6, §7's migration and
§11 are named above as the second plan's.

**Placeholders.** One deliberate gap: Task 5 step 3 names `_run_for` and
`_upsert_task` and describes their contracts rather than writing them, because
they are mechanical inserts against `saffron/ledger.py`'s existing methods and
the test that constrains them is written in full.

**Type consistency.** `task_key` is the record's identity in every task;
`record_key` is only ever the ledger column holding it. `batch_key` is a string
on a fact and `batch_id` an integer in the index, and `_append` converts at the
boundary. `Fact.payload` is `dict[str, Any]` throughout. `fold` takes `strict`
in its signature, its test and its CLI wiring.
