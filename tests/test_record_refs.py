import subprocess
from pathlib import Path
from typing import Any

import pytest

from saffron.record.contract import Fact, RecordError, StaleWriter
from saffron.record.refs import TASKS, RefsRecord


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "mirror.git"
    subprocess.run(["git", "init", "-q", "--bare", str(path)], check=True)
    return path


def a_fact(**over: Any) -> Fact:
    base: dict[str, Any] = {
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
        capture_output=True,
        text=True,
        check=True,
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
        [
            "git",
            "-C",
            str(repo),
            "rev-list",
            "--count",
            f"refs/saffron/tasks/{fact.task_key}",
        ],
        capture_output=True,
        text=True,
        check=True,
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
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    record.append(fact.task_key, a_fact(kind="task_state"))
    root = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", ref],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert root == first


def test_reading_an_absent_task_gives_an_empty_log(repo):
    assert RefsRecord(repo).read("f" * 32) == []


def test_a_broken_repository_is_not_an_empty_log(tmp_path):
    # A repo that cannot be read is `error`, never a task with no facts.
    broken = tmp_path / "not-a-repo"
    with pytest.raises(RecordError):
        RefsRecord(broken).read("a" * 32)


def test_a_failure_carries_the_reason_git_gave(tmp_path):
    # `CalledProcessError` names the argv and the exit code and drops stderr,
    # so a refused push read exactly like a repository that is not there.
    broken = tmp_path / "not-a-repo"
    broken.mkdir()
    with pytest.raises(RecordError) as raised:
        RefsRecord(broken).read("a" * 32)
    assert "not a git repository" in raised.value.stderr.lower()
    assert "not a git repository" in str(raised.value).lower()


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
        capture_output=True,
        text=True,
        check=True,
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
        [
            "git",
            "-C",
            str(repo),
            "ls-tree",
            "-r",
            "--name-only",
            f"refs/saffron/tasks/{fact.task_key}",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert listing == ["facts/0001.json", "facts/0002.json"]


def test_compare_and_swap_refuses_a_stale_writer(repo):
    record = RefsRecord(repo)
    assert record.compare_and_swap("budget", None, "1.50") is True
    assert record.compare_and_swap("budget", "1.50", "2.00") is True
    assert record.compare_and_swap("budget", "1.50", "9.99") is False
    # The refused swap above must not have written "9.99" over "2.00".
    assert record.compare_and_swap("budget", "2.00", "3.00") is True


def test_a_swap_that_loses_the_race_returns_false(repo):
    # The one case a swap exists for: the value moves between the read and
    # the write. Raising there left the caller only the mismatch it read.

    class Raced(RefsRecord):
        def _git(self, *args: str, stdin: str | None = None) -> str:
            out = super()._git(*args, stdin=stdin)
            if args[0] == "commit-tree":
                # A second writer lands between this swap's read and its write.
                RefsRecord(repo).compare_and_swap("budget", "1.50", "7.77")
            return out

    RefsRecord(repo).compare_and_swap("budget", None, "1.50")
    assert Raced(repo).compare_and_swap("budget", "1.50", "2.00") is False
    # The lost race must not have written "2.00" over the winner's "7.77".
    assert RefsRecord(repo).compare_and_swap("budget", "7.77", "3.00") is True


def test_a_swap_stores_the_value_it_was_given(repo):
    # A read-back that strips makes a value with surrounding whitespace
    # unmatchable by its own text, so no caller can swap on what it read.
    record = RefsRecord(repo)
    assert record.compare_and_swap("budget", None, " 1.50\n") is True
    assert record.compare_and_swap("budget", "1.50", "2.00") is False
    assert record.compare_and_swap("budget", " 1.50\n", "2.00") is True


def test_a_corrupt_fact_blob_names_the_task_it_is_in(repo):
    # Nested mktree calls, matching `append`'s tree shape: `git mktree` refuses
    # a flat "facts/0001.json" entry as a path containing a slash.
    record = RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)
    blob = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
        input="{not json",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    facts_tree = subprocess.run(
        ["git", "-C", str(repo), "mktree"],
        input=f"100644 blob {blob}\t0001.json\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "-C", str(repo), "mktree"],
        input=f"040000 tree {facts_tree}\tfacts\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(repo), "commit-tree", tree, "-m", "corrupt"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "update-ref",
            f"refs/saffron/tasks/{fact.task_key}",
            commit,
        ],
        check=True,
    )
    with pytest.raises(ValueError, match=fact.task_key):
        record.read(fact.task_key)


def test_append_pushes_the_ref_to_the_remote(tmp_path, repo):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    record = RefsRecord(repo, remote=str(remote))
    fact = a_fact()
    record.append(fact.task_key, fact)
    local = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", f"{TASKS}/{fact.task_key}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    on_remote = subprocess.run(
        ["git", "-C", str(remote), "rev-parse", f"{TASKS}/{fact.task_key}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert on_remote == local


def test_a_diverged_push_is_refused_not_forced(tmp_path, repo):
    # No `--force` anywhere in `_push`: a stale writer must see the refusal
    # rather than overwrite what it never read (design §3).
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    fact = a_fact()
    RefsRecord(repo, remote=str(remote)).append(fact.task_key, fact)
    on_remote = subprocess.run(
        ["git", "-C", str(remote), "rev-parse", f"{TASKS}/{fact.task_key}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # A second writer that never read `repo`'s append: same task, unrelated
    # local history, so its commit is not a descendant of what is on `remote`.
    stale = tmp_path / "stale.git"
    subprocess.run(["git", "init", "-q", "--bare", str(stale)], check=True)
    diverged = a_fact(task_key=fact.task_key, payload={"spec_id": "SA-0100"})
    # `StaleWriter`, not `RecordError`: the refusal is the cross-host
    # detection §3 rests on, and a retry needs it apart from a dead remote.
    with pytest.raises(StaleWriter):
        RefsRecord(stale, remote=str(remote)).append(diverged.task_key, diverged)

    unchanged = subprocess.run(
        ["git", "-C", str(remote), "rev-parse", f"{TASKS}/{fact.task_key}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert unchanged == on_remote
