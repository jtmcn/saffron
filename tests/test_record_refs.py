import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from saffron.record.contract import KINDS, Fact, RecordError, StaleWriter
from saffron.record.refs import _IDENT as IDENT
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


def test_an_object_git_no_longer_has_is_not_a_shorter_log(repo):
    # `cat-file --batch` answers "<sha> missing" over exit 0, so a reader that
    # skips the line hands the fold a task missing its middle. `error` != `fail`.
    record = RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)
    sha = record._blobs(fact.task_key)[0][1]
    (repo / "objects" / sha[:2] / sha[2:]).unlink()
    with pytest.raises(RecordError, match="missing"):
        record.read(fact.task_key)


def test_a_host_with_no_git_identity_can_still_append(repo, tmp_path, monkeypatch):
    # Every append is a commit, and a host git cannot name an author on is a
    # real one: CI is that host, and it failed this whole file for it.
    config = tmp_path / "gitconfig"
    config.write_text("[user]\n\tuseConfigOnly = true\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    record = RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)
    assert record.read(fact.task_key) == [fact]


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
        # The identity is on the command because a bare repo has none, which
        # is what `RefsRecord` does and why CI could not run this file.
        ["git", "-C", str(repo), *IDENT, "commit-tree", tree, "-m", "corrupt"],
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


def test_a_ref_is_never_started_by_a_fact_other_than_task_created(tmp_path):
    # Every kind but `task_created` must refuse to start a ref this repo
    # lacks, with no remote and with a remote that lacks the ref too.
    for kind in KINDS:
        if kind == "task_created":
            continue
        fact = a_fact(kind=kind, task_key="b" * 32)

        no_origin = tmp_path / f"no-origin-{kind}.git"
        subprocess.run(["git", "init", "-q", "--bare", str(no_origin)], check=True)
        with pytest.raises(RecordError):
            RefsRecord(no_origin).append(fact.task_key, fact)
        assert RefsRecord(no_origin).task_keys() == []

        lacking = tmp_path / f"lacking-{kind}.git"
        subprocess.run(["git", "init", "-q", "--bare", str(lacking)], check=True)
        empty_remote = tmp_path / f"empty-remote-{kind}.git"
        subprocess.run(["git", "init", "-q", "--bare", str(empty_remote)], check=True)
        with pytest.raises(RecordError):
            RefsRecord(lacking, remote=str(empty_remote)).append(fact.task_key, fact)
        assert RefsRecord(lacking).task_keys() == []
        assert RefsRecord(empty_remote).task_keys() == []

    # A `remote` that holds the ref is fetched before the append, for
    # every one of those kinds, so each push is a fast-forward.
    for kind in KINDS:
        if kind == "task_created":
            continue
        fact = a_fact(kind=kind, task_key="c" * 32)

        origin = tmp_path / f"origin-{kind}.git"
        subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
        created = a_fact(kind="task_created", task_key=fact.task_key)
        RefsRecord(origin).append(created.task_key, created)
        before = subprocess.run(
            [
                "git",
                "-C",
                str(origin),
                "rev-list",
                "--count",
                f"{TASKS}/{fact.task_key}",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        empty = tmp_path / f"empty-{kind}.git"
        subprocess.run(["git", "init", "-q", "--bare", str(empty)], check=True)
        RefsRecord(empty, remote=str(origin)).append(fact.task_key, fact)

        after = subprocess.run(
            [
                "git",
                "-C",
                str(origin),
                "rev-list",
                "--count",
                f"{TASKS}/{fact.task_key}",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert int(after) == int(before) + 1
        assert RefsRecord(origin).read(fact.task_key) == RefsRecord(empty).read(
            fact.task_key
        )


def test_a_fact_cannot_be_filed_under_another_task(repo):
    # The same guard on the backend a night actually writes to.
    record = RefsRecord(repo)
    with pytest.raises(ValueError, match="filed under"):
        record.append("b" * 32, a_fact())
    assert record.task_keys() == []


def _stand_in_ssh(
    dir_: Path, log: Path, *, beat_s: float = 0.1, giveup_s: float = 20.0
) -> Path:
    """An `ssh` that appends one beat to `log` every `beat_s`. It gives up
    on its own after `giveup_s`, so a wrong version fails this witness
    instead of hanging it. Named literally `ssh`: git probes any other
    basename with `-G` first, starting it twice."""
    ssh = dir_ / "ssh"
    beats = max(1, int(giveup_s / beat_s))
    ssh.write_text(
        "#!/bin/sh\n"
        f"i=0\n"
        f"while [ $i -lt {beats} ]; do\n"
        f"  date +%s%N >> {log}\n"
        f"  sleep {beat_s}\n"
        f"  i=$((i + 1))\n"
        "done\n"
        "exit 1\n"
    )
    ssh.chmod(0o755)
    return ssh


def _logging_ssh(dir_: Path, log: Path) -> Path:
    """An `ssh` that logs its own argv and refuses at once, as a passphrase
    prompt would without one."""
    ssh = dir_ / "ssh"
    ssh.write_text(f'#!/bin/sh\necho "$*" >> {log}\nexit 255\n')
    ssh.chmod(0o755)
    return ssh


def _last_call(log: Path) -> list[str]:
    return log.read_text().splitlines()[-1].split() if log.exists() else []


def _has_keepalive(args: list[str]) -> bool:
    return "ServerAliveInterval=15" in args and "ServerAliveCountMax=4" in args


def _beats(log: Path) -> int:
    return len(log.read_text().splitlines()) if log.exists() else 0


def test_every_network_git_call_asks_for_no_credential(tmp_path, repo, monkeypatch):
    """Each fetch and push reaches an ssh origin through a stand-in ssh. It logs
    what it was handed and fails as an origin that wants a passphrase."""
    log = tmp_path / "ssh.log"
    ssh = tmp_path / "ssh"
    ssh.write_text(
        "#!/bin/sh\n"
        f'echo "prompt=$GIT_TERMINAL_PROMPT $*" >> {log}\n'
        'echo "would prompt for a passphrase" >&2\n'
        "exit 255\n"
    )
    ssh.chmod(0o755)
    monkeypatch.setenv("GIT_SSH_COMMAND", str(ssh))
    # conftest allows only `file`, and this origin must reach the stand-in ssh.
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file:ssh")
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)
    origin = "ssh://origin.invalid/saffron.git"
    created = a_fact()
    RefsRecord(repo).append(created.task_key, created)
    later = a_fact(kind="task_state", task_key="d" * 32, payload={"state": "MERGED"})

    with pytest.raises(RecordError):
        RefsRecord(repo).fetch(origin)
    with pytest.raises(RecordError):
        RefsRecord(repo).push(created.task_key, origin)
    with pytest.raises(RecordError) as refused:
        RefsRecord(repo, origin=origin).append(later.task_key, later)

    calls = log.read_text().splitlines()
    assert len(calls) == 3
    for call in calls:
        assert call.startswith("prompt=0 -o BatchMode=yes"), call
    # The refusal names git's reason rather than reading as a lacking origin.
    assert "would prompt for a passphrase" in str(refused.value)
    assert isinstance(refused.value.__cause__, RecordError)


def test_a_push_that_never_returns_is_refused_within_the_limit(
    tmp_path, repo, monkeypatch
):
    from saffron.record import refs

    monkeypatch.setattr(refs, "PUSH_TIMEOUT_S", 2, raising=False)
    log = tmp_path / "ssh.log"
    _stand_in_ssh(tmp_path, log)
    monkeypatch.setenv("GIT_SSH_COMMAND", str(tmp_path / "ssh"))
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file:ssh")
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)
    remote = "ssh://stall.invalid/mirror.git"

    record = refs.RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)
    ref = f"{TASKS}/{fact.task_key}"
    before = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", ref],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    for _ in range(2):
        start = time.monotonic()
        with pytest.raises(RecordError) as raised:
            record.push(fact.task_key, remote)
        elapsed = time.monotonic() - start
        assert 2 <= elapsed < 7
        assert not isinstance(raised.value, StaleWriter)
        assert "2s" in str(raised.value)
        after = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", ref],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert after == before

    later = a_fact(task_key="e" * 32)
    start = time.monotonic()
    with pytest.raises(RecordError) as raised_append:
        refs.RefsRecord(repo, remote=remote).append(later.task_key, later)
    elapsed = time.monotonic() - start
    assert 2 <= elapsed < 7
    assert not isinstance(raised_append.value, StaleWriter)
    assert "2s" in str(raised_append.value)
    # The local commit lands before the refused push, and stays.
    assert refs.RefsRecord(repo).read(later.task_key) == [later]


def test_a_timed_out_push_leaves_no_process_behind(tmp_path, repo, monkeypatch):
    from saffron.record import refs

    # Pinned, not read back: a batch pays for a stalled push up to this
    # limit, so a change to the real default must be a deliberate one.
    assert refs.PUSH_TIMEOUT_S == 120
    monkeypatch.setattr(refs, "PUSH_TIMEOUT_S", 2, raising=False)
    log = tmp_path / "ssh.log"
    _stand_in_ssh(tmp_path, log)
    monkeypatch.setenv("GIT_SSH_COMMAND", str(tmp_path / "ssh"))
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file:ssh")
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)
    remote = "ssh://stall.invalid/mirror.git"

    kept: list[subprocess.Popen] = []
    real_popen = subprocess.Popen

    def _spy_popen(argv: Any, *args: Any, **kwargs: Any) -> Any:
        proc = real_popen(argv, *args, **kwargs)
        if isinstance(argv, list) and "push" in argv:
            kept.append(proc)
        return proc

    monkeypatch.setattr(subprocess, "Popen", _spy_popen)

    record = refs.RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)

    def _check(do_call: Any) -> None:
        before = _beats(log)
        start = time.monotonic()
        with pytest.raises(RecordError):
            do_call()
        elapsed = time.monotonic() - start
        assert 2 <= elapsed < 7
        beats_at_refusal = _beats(log) - before
        assert beats_at_refusal >= 5
        # Read, never polled or waited on: production code's own wait set it.
        assert kept[-1].returncode is not None
        time.sleep(1)
        assert _beats(log) - before == beats_at_refusal

    _check(lambda: record.push(fact.task_key, remote))

    later = a_fact(task_key="e" * 32)
    _check(lambda: refs.RefsRecord(repo, remote=remote).append(later.task_key, later))


def test_an_interrupted_push_leaves_no_process_behind(tmp_path, repo, monkeypatch):
    from saffron.record import refs

    log = tmp_path / "ssh.log"
    _stand_in_ssh(tmp_path, log)
    monkeypatch.setenv("GIT_SSH_COMMAND", str(tmp_path / "ssh"))
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file:ssh")
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)
    remote = "ssh://stall.invalid/mirror.git"

    kept: list[subprocess.Popen] = []
    real_popen = subprocess.Popen

    def _spy_popen(argv: Any, *args: Any, **kwargs: Any) -> Any:
        proc = real_popen(argv, *args, **kwargs)
        if isinstance(argv, list) and "push" in argv:
            kept.append(proc)
        return proc

    monkeypatch.setattr(subprocess, "Popen", _spy_popen)

    def _raise_interrupt(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    record = refs.RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)

    def _check(do_call: Any) -> None:
        before = _beats(log)
        old = signal.signal(signal.SIGALRM, _raise_interrupt)
        start = time.monotonic()
        signal.setitimer(signal.ITIMER_REAL, 2.5)
        try:
            with pytest.raises(KeyboardInterrupt):
                do_call()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        # A wait on git with the group alive would hold the interrupt until ssh gives up.
        assert time.monotonic() - start < 2.5 + 5
        beats_at_interrupt = _beats(log) - before
        assert beats_at_interrupt >= 5
        assert kept[-1].returncode is not None
        time.sleep(1)
        assert _beats(log) - before == beats_at_interrupt

    _check(lambda: record.push(fact.task_key, remote))

    later = a_fact(task_key="f" * 32)
    _check(lambda: refs.RefsRecord(repo, remote=remote).append(later.task_key, later))


def test_a_push_asks_ssh_for_keepalive_only_where_the_host_names_no_ssh_command(
    tmp_path, repo, monkeypatch
):
    from saffron.record import refs

    # A stall must outlast keepalive's own give-up, so ssh's error arrives first.
    assert getattr(refs, "PUSH_TIMEOUT_S", 0) > 15 * 4
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)
    monkeypatch.delenv("GIT_SSH", raising=False)
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file:ssh")
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)

    home = tmp_path / "home"
    xdg = tmp_path / "xdg"
    home.mkdir()
    xdg.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    bare_dir = tmp_path / "bare-bin"
    bare_dir.mkdir()
    bare_log = tmp_path / "bare.log"
    _logging_ssh(bare_dir, bare_log)
    monkeypatch.setenv("PATH", f"{bare_dir}{os.pathsep}{os.environ['PATH']}")

    named_dir = tmp_path / "named-bin"
    named_dir.mkdir()
    named_log = tmp_path / "named.log"
    named_ssh = _logging_ssh(named_dir, named_log)

    pushes: list[Any] = []
    real_popen = subprocess.Popen

    def _spy_popen(argv: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(argv, list) and "push" in argv:
            pushes.append(argv)
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", _spy_popen)

    remote = "ssh://stall.invalid/mirror.git"
    record = refs.RefsRecord(repo)
    fact = a_fact()
    record.append(fact.task_key, fact)

    def _bare_push_has_keepalive(do_call: Any) -> bool:
        before = _beats(bare_log)
        with pytest.raises(RecordError):
            do_call()
        assert _beats(bare_log) == before + 1
        return _has_keepalive(_last_call(bare_log))

    def _set_core_ssh_command(value: str | None) -> None:
        if value is None:
            subprocess.run(
                ["git", "-C", str(repo), "config", "--unset", "core.sshCommand"],
                check=True,
            )
        else:
            subprocess.run(
                ["git", "-C", str(repo), "config", "core.sshCommand", value],
                check=True,
            )

    # Neither set: keepalive goes on the bare `ssh` resolved from `PATH`,
    # for every push of the ref and for `append` with a `remote`.
    assert _bare_push_has_keepalive(lambda: record.push(fact.task_key, remote))
    assert _bare_push_has_keepalive(lambda: record.push(fact.task_key, remote))
    appended = a_fact(task_key="d" * 32)
    assert _bare_push_has_keepalive(
        lambda: refs.RefsRecord(repo, remote=remote).append(appended.task_key, appended)
    )

    # `GIT_SSH_COMMAND` alone: no keepalive, and the named stand-in runs.
    monkeypatch.setenv("GIT_SSH_COMMAND", str(named_ssh))
    with pytest.raises(RecordError):
        record.push(fact.task_key, remote)
    assert not _has_keepalive(_last_call(named_log))
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)

    # `core.sshCommand` alone, from each source git itself reads.
    _set_core_ssh_command("true")
    with pytest.raises(RecordError):
        record.push(fact.task_key, remote)
    assert not _has_keepalive(_last_call(bare_log))
    _set_core_ssh_command(None)

    (home / ".gitconfig").write_text("[core]\n\tsshCommand = true\n")
    with pytest.raises(RecordError):
        record.push(fact.task_key, remote)
    assert not _has_keepalive(_last_call(bare_log))
    (home / ".gitconfig").unlink()

    xdg_git_dir = xdg / "git"
    xdg_git_dir.mkdir()
    (xdg_git_dir / "config").write_text("[core]\n\tsshCommand = true\n")
    with pytest.raises(RecordError):
        record.push(fact.task_key, remote)
    assert not _has_keepalive(_last_call(bare_log))
    (xdg_git_dir / "config").unlink()

    system_file = tmp_path / "gitconfig-system"
    system_file.write_text("[core]\n\tsshCommand = true\n")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(system_file))
    monkeypatch.delenv("GIT_CONFIG_NOSYSTEM", raising=False)
    with pytest.raises(RecordError):
        record.push(fact.task_key, remote)
    assert not _has_keepalive(_last_call(bare_log))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("GIT_CONFIG_SYSTEM", raising=False)

    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.sshCommand")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    with pytest.raises(RecordError):
        record.push(fact.task_key, remote)
    assert not _has_keepalive(_last_call(bare_log))
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    monkeypatch.delenv("GIT_CONFIG_KEY_0", raising=False)
    monkeypatch.delenv("GIT_CONFIG_VALUE_0", raising=False)

    # Both set: still no keepalive, and still the named stand-in.
    _set_core_ssh_command("true")
    monkeypatch.setenv("GIT_SSH_COMMAND", str(named_ssh))
    with pytest.raises(RecordError):
        record.push(fact.task_key, remote)
    assert not _has_keepalive(_last_call(named_log))
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)
    _set_core_ssh_command(None)

    # Every place unset again: the same stand-in logs keepalive once more.
    pushes_before = len(pushes)
    assert _bare_push_has_keepalive(lambda: record.push(fact.task_key, remote))
    assert len(pushes) == pushes_before + 1

    # Any other exit from that read is `RecordError`, before any push starts.
    pushes_before = len(pushes)
    before_bare = _beats(bare_log)
    before_named = _beats(named_log)
    (repo / "config").write_text("not a valid git config [[[\n")
    with pytest.raises(RecordError) as broken:
        record.push(fact.task_key, remote)
    assert broken.value.returncode == 128
    assert len(pushes) == pushes_before
    assert _beats(bare_log) == before_bare
    assert _beats(named_log) == before_named
