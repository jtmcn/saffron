import pytest

from saffron.intake import load_spec
from saffron.ledger import Ledger
from saffron.scheduler import DONE_STATES, REQUEUE_STATES, build_queue


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


def _spec_dir(tmp_path):
    d = tmp_path / "specs"
    d.mkdir()
    return d


def _write(directory, name, *, id, priority=3, sha_salt=""):
    """A minimal valid spec. `sha_salt` is folded into the body so two specs
    with the same id can be written at different `spec_sha`s (an edit)."""
    (directory / name).write_text(
        f"---\nid: {id}\ntitle: t\ntype: chore\npriority: {priority}\n---\n"
        f"body {sha_salt}\n"
    )


def _task_at(ledger, repo_id, *, spec_id, spec_sha, state):
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id, spec_id=spec_id, spec_sha=spec_sha, branch=f"saffron/{spec_id}"
    )
    ledger.set_task_state(task_id, state)
    return task_id


def _repo(ledger, origin="/o"):
    return ledger.upsert_repo("r", origin, "/m.git", policy_sha="p" * 64)


# ------------------------------------------------------------- resolve_repo_id


def test_resolve_repo_id_returns_none_without_inserting(ledger):
    assert ledger.resolve_repo_id("/never-seen") is None
    # Still nothing there — the read must not have created a row.
    assert ledger.resolve_repo_id("/never-seen") is None


def test_resolve_repo_id_finds_what_upsert_repo_made(ledger):
    repo_id = _repo(ledger, "/o")
    assert ledger.resolve_repo_id("/o") == repo_id


# ---------------------------------------------------------------- tasks_by_spec


def test_tasks_by_spec_is_scoped_to_one_repo(ledger):
    repo_a = _repo(ledger, "/a")
    repo_b = _repo(ledger, "/b")
    _task_at(ledger, repo_a, spec_id="TE-1", spec_sha="s1", state="MERGED")
    _task_at(ledger, repo_b, spec_id="TE-1", spec_sha="s1", state="MERGED")

    by_key = ledger.tasks_by_spec(repo_a)

    assert set(by_key) == {("TE-1", "s1")}


def test_tasks_by_spec_keeps_the_highest_task_id_per_key(ledger):
    repo_id = _repo(ledger, "/o")
    first = _task_at(ledger, repo_id, spec_id="TE-1", spec_sha="s1", state="REJECTED")
    second = _task_at(
        ledger, repo_id, spec_id="TE-1", spec_sha="s1", state="CHANGES_REQUESTED"
    )
    assert second > first

    row = ledger.tasks_by_spec(repo_id)[("TE-1", "s1")]

    assert row["task_id"] == second
    assert row["state"] == "CHANGES_REQUESTED"


# ---------------------------------------------------------------- build_queue


def test_a_never_run_repo_queues_every_parseable_spec(tmp_path, ledger):
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1")
    _write(directory, "b.md", id="TE-2")

    candidates, refusals = build_queue(directory, None, ledger)

    assert refusals == []
    assert [c.spec.id for c in candidates] == ["TE-1", "TE-2"]
    assert all(c.task_id is None for c in candidates)


@pytest.mark.parametrize("state", sorted(DONE_STATES))
def test_a_spec_done_at_this_sha_is_not_queued(tmp_path, ledger, state):
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1")
    repo_id = _repo(ledger)
    _, spec_sha = load_spec(directory / "a.md")
    _task_at(ledger, repo_id, spec_id="TE-1", spec_sha=spec_sha, state=state)

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert candidates == []
    assert refusals == []


@pytest.mark.parametrize("state", sorted(REQUEUE_STATES))
def test_a_spec_that_should_requeue_resumes_its_task_id(tmp_path, ledger, state):
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1")
    repo_id = _repo(ledger)
    _, spec_sha = load_spec(directory / "a.md")
    task_id = _task_at(ledger, repo_id, spec_id="TE-1", spec_sha=spec_sha, state=state)

    candidates, _ = build_queue(directory, repo_id, ledger)

    assert len(candidates) == 1
    assert candidates[0].task_id == task_id


def test_an_edited_spec_is_queued_fresh_despite_a_done_task_at_the_old_sha(
    tmp_path, ledger
):
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1", sha_salt="v2")
    repo_id = _repo(ledger)

    _task_at(ledger, repo_id, spec_id="TE-1", spec_sha="stale-sha", state="REJECTED")

    candidates, _ = build_queue(directory, repo_id, ledger)

    assert len(candidates) == 1
    assert candidates[0].task_id is None


def test_an_in_flight_task_is_neither_dropped_nor_resumed(tmp_path, ledger):
    """Not one of the two lists (§4.2.1) — this spec does not stamp ORPHANED,
    so it falls through to a fresh candidate rather than a resume."""
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1")
    repo_id = _repo(ledger)
    _, spec_sha = load_spec(directory / "a.md")
    _task_at(ledger, repo_id, spec_id="TE-1", spec_sha=spec_sha, state="IMPLEMENTING")

    candidates, _ = build_queue(directory, repo_id, ledger)

    assert len(candidates) == 1
    assert candidates[0].task_id is None


def test_a_parse_failure_is_refused_with_its_path_and_reason(tmp_path, ledger):
    directory = _spec_dir(tmp_path)
    _write(directory, "a-good.md", id="TE-1")
    (directory / "b-broken.md").write_text("no frontmatter here\n")

    candidates, refusals = build_queue(directory, None, ledger)

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert len(refusals) == 1
    assert refusals[0].path.name == "b-broken.md"
    assert "frontmatter" in refusals[0].reason


def test_candidates_are_ordered_by_priority_then_filename(tmp_path, ledger):
    directory = _spec_dir(tmp_path)
    _write(directory, "b-second.md", id="TE-2", priority=1)
    _write(directory, "a-first.md", id="TE-1", priority=9)
    _write(directory, "c-tied-first.md", id="TE-3", priority=1)

    candidates, _ = build_queue(directory, None, ledger)

    # Priority 1 before priority 9, and within priority 1 the filename order
    # (b before c) from discover_specs is preserved as the tie-break.
    assert [c.spec.id for c in candidates] == ["TE-2", "TE-3", "TE-1"]


def test_build_queue_touches_no_network_and_no_cell(tmp_path, ledger):
    """Sanity: nothing here reaches `gh` or a cell runtime — the autouse
    fixture in conftest.py would fail this test outright if it did."""
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1")

    build_queue(directory, None, ledger)
