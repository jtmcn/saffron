import shutil
import subprocess
from pathlib import Path

import pytest

from saffron.ledger import Ledger
from saffron.record.contract import KINDS, Fact, RecordError, StaleWriter
from saffron.record.memory import MemoryRecord
from saffron.record.refs import TASKS, RefsRecord


def _bare(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--bare", str(path)], check=True)
    return path


def _refs(repo: Path, pattern: str = "refs/saffron/") -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "for-each-ref", "--format=%(refname)", pattern],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


@pytest.fixture(autouse=True)
def _isolated_git(tmp_path, monkeypatch):
    """No user or system config reaches a push: an empty `HOME` and
    `XDG_CONFIG_HOME`, and `GIT_CONFIG_NOSYSTEM` set."""
    config_home = tmp_path / "home"
    config_home.mkdir()
    monkeypatch.setenv("HOME", str(config_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def test_each_fact_lands_in_the_mirror_of_the_repo_its_task_ran_against(tmp_path):
    """Two repo rows share one `repos.name` and differ in origin and
    mirror. A `Ledger` built with a `RoutedRecord` routes each task's own
    facts to its own mirror, and to no other one."""
    from saffron.record.routed import RoutedRecord

    mirror_a = _bare(tmp_path / "a" / "mirror.git")
    mirror_b = _bare(tmp_path / "b" / "mirror.git")

    ledger = Ledger(
        tmp_path / "l.db", record=RoutedRecord(lambda key: ledger.record_home(key))
    )

    repo_a = ledger.upsert_repo("repo", "https://example/a.git", str(mirror_a), None)
    repo_b = ledger.upsert_repo("repo", "https://example/b.git", str(mirror_b), None)
    run_a = ledger.create_run(repo_a, base_sha="a" * 40)
    run_b = ledger.create_run(repo_b, base_sha="b" * 40)
    task_a = ledger.create_task(run_a, spec_id="SY-A", spec_sha="s" * 40, branch="x")
    task_b = ledger.create_task(run_b, spec_id="SY-B", spec_sha="s" * 40, branch="y")
    ledger.set_task_state(task_a, "DIAGNOSING")
    ledger.set_task_state(task_b, "DIAGNOSING")

    key_a = ledger.record_key(task_a)
    key_b = ledger.record_key(task_b)
    assert key_a is not None
    assert key_b is not None

    facts_a = RefsRecord(mirror_a).read(key_a)
    facts_b = RefsRecord(mirror_b).read(key_b)
    assert [f.kind for f in facts_a] == ["task_created", "task_state"]
    assert [f.kind for f in facts_b] == ["task_created", "task_state"]

    # Neither mirror holds the other task's ref at all.
    assert RefsRecord(mirror_a).read(key_b) == []
    assert RefsRecord(mirror_b).read(key_a) == []


def test_a_push_carries_the_whole_ref_to_the_tasks_origin_and_an_append_pushes_nothing(
    tmp_path,
):
    """`push_record` pushes a task's ref to its own repo's origin. An
    append pushes nothing, and another repo's origin stays untouched."""
    from saffron.record.routed import RoutedRecord

    origin = _bare(tmp_path / "origin.git")
    mirror = _bare(tmp_path / "mirror.git")
    other_origin = _bare(tmp_path / "other-origin.git")

    ledger = Ledger(
        tmp_path / "l.db", record=RoutedRecord(lambda key: ledger.record_home(key))
    )

    # Upserted first: a version that pushes to the most recently upserted
    # origin would reach `other_origin` instead, and this witness catches it.
    repo_id = ledger.upsert_repo("repo", str(origin), str(mirror), None)
    ledger.upsert_repo("other", str(other_origin), str(tmp_path / "unused.git"), None)

    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(run_id, spec_id="SY-1", spec_sha="s" * 40, branch="x")
    ledger.set_task_state(task_id, "DIAGNOSING")

    key = ledger.record_key(task_id)
    assert key is not None
    assert _refs(origin, f"{TASKS}/{key}") == []

    ledger.push_record(task_id)

    local_head = RefsRecord(mirror).read(key)
    on_origin = RefsRecord(origin).read(key)
    assert [f.kind for f in on_origin] == [f.kind for f in local_head]
    assert _refs(other_origin) == []


def test_a_later_fact_for_a_ref_the_mirror_lacks_lands_on_the_origins_history(
    tmp_path,
):
    """A `task_state` fact for a task whose ref its mirror lacks first fetches
    that one ref from the task's own origin, then appends on it. Driven over
    a pruned mirror that lost the ref, and a fresh one `upsert_repo` points
    the repo row at."""
    from saffron.record.routed import RoutedRecord

    origin = _bare(tmp_path / "origin.git")
    mirror = _bare(tmp_path / "mirror.git")

    ledger = Ledger(
        tmp_path / "l.db", record=RoutedRecord(lambda key: ledger.record_home(key))
    )
    repo_id = ledger.upsert_repo("repo", str(origin), str(mirror), None)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(run_id, spec_id="SY-1", spec_sha="s" * 40, branch="x")
    ledger.set_task_state(task_id, "DIAGNOSING")
    key = ledger.record_key(task_id)
    assert key is not None
    ledger.push_record(task_id)
    origin_head_before = _refs(origin, f"{TASKS}/{key}")

    # A ref only the mirror holds, and one only the origin holds: neither
    # is this task's, and neither must move.
    mirror_only = "d" * 32
    origin_only = "e" * 32
    stray = Fact(
        kind="task_created",
        task_key=mirror_only,
        at="2026-01-01T00:00:00Z",
        repo="repo",
        batch_key=None,
        payload={},
    )
    RefsRecord(mirror).append(mirror_only, stray)
    RefsRecord(origin).append(
        origin_only,
        Fact(
            kind="task_created",
            task_key=origin_only,
            at="2026-01-01T00:00:00Z",
            repo="repo",
            batch_key=None,
            payload={},
        ),
    )

    # Prune the task's own ref from the mirror, simulating a mirror that
    # lost it.
    subprocess.run(
        ["git", "-C", str(mirror), "update-ref", "-d", f"{TASKS}/{key}"], check=True
    )
    assert _refs(mirror, f"{TASKS}/{key}") == []

    ledger.set_task_state(task_id, "IMPLEMENTING")
    assert len(_refs(mirror, f"{TASKS}/{key}")) == 1
    parent = subprocess.run(
        ["git", "-C", str(mirror), "rev-parse", f"{TASKS}/{key}^"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert (
        parent
        == subprocess.run(
            ["git", "-C", str(origin), "rev-parse", f"{TASKS}/{key}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    assert origin_head_before  # a ref existed on origin to recover from

    ledger.push_record(task_id)
    assert RefsRecord(mirror).read(key) == RefsRecord(origin).read(key)

    # The fetch took no other ref, and pruned none.
    assert RefsRecord(mirror).read(mirror_only) == [stray]
    assert RefsRecord(mirror).read(origin_only) == []

    # A fresh mirror `upsert_repo` points the repo row at: the production
    # path for a repeated run from another checkout (item 170).
    fresh_mirror = _bare(tmp_path / "fresh-mirror.git")
    ledger.upsert_repo("repo", str(origin), str(fresh_mirror), None)
    ledger.set_task_state(task_id, "GATING")
    ledger.push_record(task_id)
    assert RefsRecord(fresh_mirror).read(key) == RefsRecord(origin).read(key)


def test_a_later_fact_neither_the_mirror_nor_the_origin_holds_writes_no_ref(
    tmp_path, monkeypatch
):
    """Where the origin lacks the ref too, an append through the
    `RoutedRecord` raises `RecordError`, and neither the mirror nor the
    origin gains a ref."""
    from saffron.record.routed import RoutedRecord

    origin = _bare(tmp_path / "origin.git")
    mirror = _bare(tmp_path / "mirror.git")

    plain = Ledger(tmp_path / "l.db")
    repo_id = plain.upsert_repo("repo", str(origin), str(mirror), None)
    run_id = plain.create_run(repo_id, base_sha="a" * 40)
    task_id = plain.create_task(run_id, spec_id="SY-1", spec_sha="s" * 40, branch="x")
    key = plain.record_key(task_id)
    assert key is not None
    plain.close()

    calls: list[list[str]] = []
    real_run = subprocess.run

    def _spy(argv, *args, **kwargs):
        if isinstance(argv, list) and argv and argv[0] == "git":
            calls.append(list(argv))
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)

    routed = Ledger(
        tmp_path / "l.db", record=RoutedRecord(lambda k: routed.record_home(k))
    )

    with pytest.raises(RecordError):
        routed.set_task_state(task_id, "DIAGNOSING")

    fetches = [call for call in calls if "fetch" in call]
    assert len(fetches) == 1
    assert str(origin) in fetches[0]
    assert any(f"{TASKS}/{key}:{TASKS}/{key}" in item for item in fetches[0])

    assert _refs(mirror) == []
    assert _refs(origin) == []

    # A routed `task_created`, and a later fact on the ref it starts,
    # record no fetch at all.
    calls.clear()
    new_task_id = routed.create_task(
        run_id, spec_id="SY-2", spec_sha="s" * 40, branch="y"
    )
    assert not any("fetch" in call for call in calls)
    assert not any(str(origin) in item for call in calls for item in call)

    calls.clear()
    routed.set_task_state(new_task_id, "DIAGNOSING")
    assert not any("fetch" in call for call in calls)
    assert not any(str(origin) in item for call in calls for item in call)


def test_two_origins_sharing_a_mirror_each_fetch_from_their_own(tmp_path):
    """Two repo rows share one mirror and differ in origin. The second row's
    later fact recovers its ref from its own origin. This holds after the
    same command touched the first row's task."""
    from saffron.record.routed import RoutedRecord

    a = _bare(tmp_path / "a.git")
    b = _bare(tmp_path / "b.git")
    mirror = _bare(tmp_path / "mirror.git")
    seed = Ledger(tmp_path / "l.db", record=RoutedRecord(lambda k: seed.record_home(k)))
    repo_a = seed.upsert_repo("repo", str(a), str(mirror), None)
    repo_b = seed.upsert_repo("repo", str(b), str(mirror), None)
    task_a = seed.create_task(
        seed.create_run(repo_a, base_sha="a" * 40),
        spec_id="SY-1",
        spec_sha="s" * 40,
        branch="x",
    )
    task_b = seed.create_task(
        seed.create_run(repo_b, base_sha="a" * 40),
        spec_id="SY-2",
        spec_sha="s" * 40,
        branch="y",
    )
    seed.push_record(task_a)
    seed.push_record(task_b)
    key_b = seed.record_key(task_b)
    assert key_b is not None
    subprocess.run(
        ["git", "-C", str(mirror), "update-ref", "-d", f"{TASKS}/{key_b}"],
        check=True,
    )
    assert f"{TASKS}/{key_b}" in _refs(b)

    command = Ledger(
        tmp_path / "l.db", record=RoutedRecord(lambda k: command.record_home(k))
    )
    command.set_task_state(task_a, "DIAGNOSING")
    command.set_task_state(task_b, "DIAGNOSING")

    kinds = [fact.kind for fact in RefsRecord(mirror).read(key_b)]
    assert kinds == ["task_created", "task_state"]


def test_a_ledger_without_a_routed_record_pushes_nothing(tmp_path):
    """`push_record` on a plain or a `MemoryRecord`-backed ledger returns
    without pushing or raising, even over a mirror and origin that do not
    exist. On a `RoutedRecord` ledger, a task id with no row is the same."""
    from saffron.record.routed import RoutedRecord

    bogus_mirror = str(tmp_path / "no" / "mirror.git")
    bogus_origin = str(tmp_path / "no" / "origin.git")

    plain = Ledger(tmp_path / "plain.db")
    repo_id = plain.upsert_repo("repo", bogus_origin, bogus_mirror, None)
    run_id = plain.create_run(repo_id, base_sha="a" * 40)
    task_id = plain.create_task(run_id, spec_id="SY-1", spec_sha="s" * 40, branch="x")
    plain.push_record(task_id)

    memory_record = MemoryRecord()
    memoried = Ledger(tmp_path / "memory.db", record=memory_record)
    repo_id = memoried.upsert_repo("repo", bogus_origin, bogus_mirror, None)
    run_id = memoried.create_run(repo_id, base_sha="a" * 40)
    task_id = memoried.create_task(
        run_id, spec_id="SY-1", spec_sha="s" * 40, branch="x"
    )
    memoried.push_record(task_id)

    mirror = _bare(tmp_path / "mirror.git")
    origin = _bare(tmp_path / "origin.git")
    routed = Ledger(
        tmp_path / "routed.db",
        record=RoutedRecord(lambda key: routed.record_home(key)),
    )
    routed.upsert_repo("repo", str(origin), str(mirror), None)

    routed.push_record(999999)

    assert _refs(mirror) == []
    assert _refs(origin) == []


def _direct_fact(key: str, kind: str, repo: str = "repo") -> Fact:
    return Fact(
        kind=kind,
        task_key=key,
        at="2026-01-01T00:00:00Z",
        repo=repo,
        batch_key=None,
        payload={},
    )


def test_the_exit_push_carries_each_appended_key_once_to_its_own_origin(
    tmp_path, monkeypatch
):
    """`push_unpushed` pushes each kept key once, through `push`, in
    append order, and returns `[]`. Driven across two repos and five keys.
    One is appended three times. One already carries its own `push`,
    with no later fact. One carries, then gains one more fact. One
    carries a commit an earlier `RoutedRecord` already pushed. One
    drives every kind in `KINDS`. A second call pushes nothing more."""
    from saffron.record.routed import RoutedRecord

    origin_a = _bare(tmp_path / "a" / "origin.git")
    mirror_a = _bare(tmp_path / "a" / "mirror.git")
    origin_b = _bare(tmp_path / "b" / "origin.git")
    mirror_b = _bare(tmp_path / "b" / "mirror.git")

    record = RoutedRecord(lambda key: ledger.record_home(key))
    ledger = Ledger(tmp_path / "l.db", record=record)
    repo_a = ledger.upsert_repo("a", str(origin_a), str(mirror_a), None)
    repo_b = ledger.upsert_repo("b", str(origin_b), str(mirror_b), None)
    run_a = ledger.create_run(repo_a, base_sha="a" * 40)
    run_b = ledger.create_run(repo_b, base_sha="b" * 40)

    # Appended three times, no push in between.
    task_three = ledger.create_task(
        run_a, spec_id="SY-1", spec_sha="s" * 40, branch="x1"
    )
    key_three = ledger.record_key(task_three)
    assert key_three is not None
    ledger.set_task_state(task_three, "DIAGNOSING")
    ledger.set_task_state(task_three, "IMPLEMENTING")

    # `push` carries it, and no later fact lands.
    task_carried = ledger.create_task(
        run_a, spec_id="SY-2", spec_sha="s" * 40, branch="x2"
    )
    key_carried = ledger.record_key(task_carried)
    assert key_carried is not None
    record.push(key_carried)

    # `push` carries it, then one more fact lands, of a kind neither
    # `task_created` nor `task_state` names.
    task_reappended = ledger.create_task(
        run_b, spec_id="SY-3", spec_sha="s" * 40, branch="x3"
    )
    key_reappended = ledger.record_key(task_reappended)
    assert key_reappended is not None
    record.push(key_reappended)
    record.append(key_reappended, _direct_fact(key_reappended, "finding", "b"))

    # Its ref already carries a commit a second `RoutedRecord` pushed, and
    # this one's own exit push still lands the fact that follows.
    task_earlier = ledger.create_task(
        run_a, spec_id="SY-4", spec_sha="s" * 40, branch="x4"
    )
    key_earlier = ledger.record_key(task_earlier)
    assert key_earlier is not None
    RoutedRecord(lambda key: ledger.record_home(key)).push(key_earlier)
    ledger.set_task_state(task_earlier, "GATING")

    # Drives every kind `KINDS` names, appended directly rather than
    # through a `Ledger` write method.
    task_kinds = ledger.create_task(
        run_b, spec_id="SY-5", spec_sha="s" * 40, branch="x5"
    )
    key_kinds = ledger.record_key(task_kinds)
    assert key_kinds is not None
    for kind in KINDS:
        if kind == "task_created":
            continue  # `create_task` above already wrote this one.
        record.append(key_kinds, _direct_fact(key_kinds, kind, "b"))

    calls: list[list[str]] = []
    real_run = subprocess.run

    def _spy(argv, *args, **kwargs):
        if isinstance(argv, list) and argv and argv[0] == "git":
            calls.append(list(argv))
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)

    def _pushes(key: str) -> int:
        return sum(
            1 for call in calls if "push" in call and any(key in item for item in call)
        )

    assert _refs(origin_a, f"{TASKS}/{key_three}") == []

    refused = record.push_unpushed()

    assert refused == []
    assert _pushes(key_three) == 1
    assert _refs(origin_a, f"{TASKS}/{key_three}") != []
    assert RefsRecord(origin_a).read(key_three) == RefsRecord(mirror_a).read(key_three)

    assert _pushes(key_carried) == 0
    assert _pushes(key_reappended) == 1
    assert _pushes(key_earlier) == 1
    assert _pushes(key_kinds) == 1

    assert RefsRecord(origin_b).read(key_reappended) == RefsRecord(mirror_b).read(
        key_reappended
    )
    assert RefsRecord(origin_a).read(key_earlier) == RefsRecord(mirror_a).read(
        key_earlier
    )
    assert RefsRecord(origin_b).read(key_kinds) == RefsRecord(mirror_b).read(key_kinds)
    assert [fact.kind for fact in RefsRecord(mirror_b).read(key_kinds)] == list(KINDS)

    calls.clear()
    second = record.push_unpushed()
    assert second == []
    assert calls == []


def test_a_refused_exit_push_is_returned_with_its_key_and_never_pushed_again(tmp_path):
    """A refused push is returned beside its key, never raised. A
    diverged origin comes back as `StaleWriter`. An origin that is not a
    repository comes back as a plain `RecordError`. A key kept after
    both refusals is still pushed. Neither refused key is retried by a
    second call. A refused key is pushed again only once a later fact
    lands on it."""
    from saffron.record.routed import RoutedRecord

    origin_stale = _bare(tmp_path / "origin-stale.git")
    mirror_stale = _bare(tmp_path / "mirror-stale.git")
    seed = _bare(tmp_path / "seed.git")

    origin_dead = _bare(tmp_path / "origin-dead.git")
    mirror_dead = _bare(tmp_path / "mirror-dead.git")

    origin_ok = _bare(tmp_path / "origin-ok.git")
    mirror_ok = _bare(tmp_path / "mirror-ok.git")

    record = RoutedRecord(lambda key: ledger.record_home(key))
    ledger = Ledger(tmp_path / "l.db", record=record)
    repo_stale = ledger.upsert_repo("stale", str(origin_stale), str(mirror_stale), None)
    repo_dead = ledger.upsert_repo("dead", str(origin_dead), str(mirror_dead), None)
    repo_ok = ledger.upsert_repo("ok", str(origin_ok), str(mirror_ok), None)

    run_stale = ledger.create_run(repo_stale, base_sha="a" * 40)
    task_stale = ledger.create_task(
        run_stale, spec_id="SY-1", spec_sha="s" * 40, branch="x1"
    )
    key_stale = ledger.record_key(task_stale)
    assert key_stale is not None
    # A second writer, sharing no history with `mirror_stale`, pushes its
    # own commit for this key to `origin_stale` first.
    RefsRecord(seed, remote=str(origin_stale)).append(
        key_stale, _direct_fact(key_stale, "task_created", "stale")
    )

    run_dead = ledger.create_run(repo_dead, base_sha="a" * 40)
    task_dead = ledger.create_task(
        run_dead, spec_id="SY-2", spec_sha="s" * 40, branch="x2"
    )
    key_dead = ledger.record_key(task_dead)
    assert key_dead is not None
    shutil.rmtree(origin_dead)

    run_ok = ledger.create_run(repo_ok, base_sha="a" * 40)
    task_ok = ledger.create_task(run_ok, spec_id="SY-3", spec_sha="s" * 40, branch="x3")
    key_ok = ledger.record_key(task_ok)
    assert key_ok is not None

    refused = record.push_unpushed()
    by_key = dict(refused)
    assert set(by_key) == {key_stale, key_dead}
    assert isinstance(by_key[key_stale], StaleWriter)
    assert isinstance(by_key[key_dead], RecordError)
    assert not isinstance(by_key[key_dead], StaleWriter)

    assert RefsRecord(origin_ok).read(key_ok) == RefsRecord(mirror_ok).read(key_ok)

    assert key_stale not in record._kept
    assert key_dead not in record._kept

    second = record.push_unpushed()
    assert second == []

    ledger.set_task_state(task_stale, "DIAGNOSING")
    assert key_stale in record._kept
