import subprocess
from pathlib import Path

import pytest

from saffron.ledger import Ledger
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
