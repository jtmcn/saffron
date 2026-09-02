"""`saffron/reconcile.py`. No network, no cell: every `gh` here is a fake
`GhRunner`; `tests/conftest.py`'s `no_host_tool_exec` guard would raise on
a real one."""

from __future__ import annotations

import json
import subprocess

import pytest

from saffron.ledger import Ledger
from saffron.reconcile import IN_FLIGHT_STATES, reconcile


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


def _repo(ledger, origin="https://github.com/jtmcn/saffron.git"):
    return ledger.upsert_repo("saffron", origin, "/m.git", policy_sha="p" * 64)


def _task(ledger, repo_id, *, spec_id, state, pr_url=None):
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id, spec_id=spec_id, spec_sha="s" * 40, branch=f"saffron/{spec_id}"
    )
    ledger.set_task_state(task_id, state)
    if pr_url is not None:
        ledger._db.execute(
            "UPDATE tasks SET pr_url = ? WHERE task_id = ?", (pr_url, task_id)
        )
        ledger._db.commit()
    return task_id


def _state(ledger, task_id):
    return ledger._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()["state"]


class _FakeGh:
    """`answers[url]` is the JSON body `gh pr view` would print, or `None`
    for a `gh` call that fails outright (returncode != 0)."""

    def __init__(self, answers: dict[str, dict | None]) -> None:
        self.answers = answers
        self.calls: list[str] = []

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        assert argv[:3] == ["gh", "pr", "view"]
        self.calls.append(argv[3])
        answer = self.answers.get(argv[3])
        if answer is None:
            return subprocess.CompletedProcess(argv, 1, "", "not found")
        return subprocess.CompletedProcess(argv, 0, json.dumps(answer), "")


# This repo's own six recorded PR-carrying tasks, not invented: the ids and
# urls are the rows this machine's ledger held, and the five/one split is the
# spec's own `gh pr view` measurement of 2026-08-30. Not `git log --merges` —
# #51 was squash-merged, so that command does not list it.
_REAL_SIX = [
    ("SA-0013", "https://github.com/jtmcn/saffron/pull/51"),
    ("SA-0014", "https://github.com/jtmcn/saffron/pull/56"),
    ("SA-0015", "https://github.com/jtmcn/saffron/pull/59"),
    ("SA-0016", "https://github.com/jtmcn/saffron/pull/60"),
    ("SA-0017", "https://github.com/jtmcn/saffron/pull/64"),
    ("SA-0018", "https://github.com/jtmcn/saffron/pull/65"),
]


def test_the_real_six_tasks_reconcile_to_their_real_pull_request_states(ledger):
    """A fixture built to prove the happy path proves nothing about the
    caller — these are the repo's own tasks."""
    repo_id = _repo(ledger)
    task_ids = {
        spec_id: _task(
            ledger, repo_id, spec_id=spec_id, state="READY_FOR_REVIEW", pr_url=url
        )
        for spec_id, url in _REAL_SIX
    }
    answers: dict[str, dict | None] = {
        url: {"state": "MERGED", "reviewDecision": None}
        for spec_id, url in _REAL_SIX
        if spec_id != "SA-0018"
    }
    answers["https://github.com/jtmcn/saffron/pull/65"] = {
        "state": "OPEN",
        "reviewDecision": None,
    }

    result = reconcile(ledger, repo_id, gh=_FakeGh(answers))

    for spec_id in ("SA-0013", "SA-0014", "SA-0015", "SA-0016", "SA-0017"):
        assert task_ids[spec_id] in result.merged
    assert task_ids["SA-0018"] not in result.merged
    assert _state(ledger, task_ids["SA-0018"]) == "READY_FOR_REVIEW"
    assert result.unasked == []


@pytest.mark.parametrize(
    "pr, bucket, expect_state",
    [
        ({"state": "CLOSED", "reviewDecision": None}, "rejected", "REJECTED"),
        (
            {"state": "OPEN", "reviewDecision": "CHANGES_REQUESTED"},
            "changes_requested",
            "CHANGES_REQUESTED",
        ),
        ({"state": "OPEN", "reviewDecision": None}, None, "READY_FOR_REVIEW"),
        # The fifth mapping the module says it does not make: an unrecognised
        # `state` leaves the row exactly as it was, like an unanswerable `gh`.
        ({"state": "SOMETHING_NEW", "reviewDecision": None}, None, "READY_FOR_REVIEW"),
    ],
    ids=[
        "closed-unmerged",
        "open-changes-requested",
        "open-undecided",
        "unrecognised-state",
    ],
)
def test_one_pull_request_outcome_maps_to_one_ledger_state(
    ledger, pr, bucket, expect_state
):
    repo_id = _repo(ledger)
    url = "https://github.com/jtmcn/saffron/pull/100"
    task_id = _task(
        ledger, repo_id, spec_id="SA-9001", state="READY_FOR_REVIEW", pr_url=url
    )

    result = reconcile(ledger, repo_id, gh=_FakeGh({url: pr}))

    if bucket:
        assert getattr(result, bucket) == [task_id]
    else:
        assert result.merged == result.rejected == result.changes_requested == []
    assert _state(ledger, task_id) == expect_state


@pytest.mark.parametrize(
    "broken_gh",
    [
        lambda argv: subprocess.CompletedProcess(argv, 1, "", "gh: not authenticated"),
        lambda argv: subprocess.CompletedProcess(argv, 0, "not json", ""),
        lambda argv: subprocess.CompletedProcess(argv, 0, "[]", ""),
    ],
    ids=["nonzero-exit", "unparseable", "wrong-shape"],
)
def test_a_gh_that_cannot_be_trusted_leaves_the_state_exactly_as_it_found_it(
    ledger, broken_gh
):
    """Absence of an answer is never "not merged"."""
    repo_id = _repo(ledger)
    url = "https://github.com/jtmcn/saffron/pull/103"
    task_id = _task(
        ledger, repo_id, spec_id="SA-9004", state="READY_FOR_REVIEW", pr_url=url
    )

    result = reconcile(ledger, repo_id, gh=broken_gh)

    assert result.unasked == [task_id]
    assert result.merged == result.rejected == result.changes_requested == []
    assert _state(ledger, task_id) == "READY_FOR_REVIEW"


def test_a_merged_task_never_moves_again(ledger):
    """`MERGED` is never asked about again, on this run or the next."""
    repo_id = _repo(ledger)
    url = "https://github.com/jtmcn/saffron/pull/104"
    task_id = _task(ledger, repo_id, spec_id="SA-9005", state="MERGED", pr_url=url)
    gh = _FakeGh({url: {"state": "CLOSED", "reviewDecision": None}})

    reconcile(ledger, repo_id, gh=gh)
    reconcile(ledger, repo_id, gh=gh)

    assert gh.calls == []
    assert _state(ledger, task_id) == "MERGED"


def test_stamp_orphaned_only_fires_when_the_caller_asserts_the_premise(ledger):
    """Default `False` leaves in-flight rows untouched even while the
    pull-request half runs; `stamp_orphaned=True` stamps them all."""
    repo_id = _repo(ledger)
    in_flight_ids = [
        _task(ledger, repo_id, spec_id=f"SA-{9100 + i}", state=state)
        for i, state in enumerate(sorted(IN_FLIGHT_STATES))
    ]
    url = "https://github.com/jtmcn/saffron/pull/105"
    pr_task = _task(
        ledger, repo_id, spec_id="SA-9200", state="READY_FOR_REVIEW", pr_url=url
    )
    gh = _FakeGh({url: {"state": "MERGED", "reviewDecision": None}})

    default = reconcile(ledger, repo_id, gh=gh)
    assert default.orphaned == []
    assert default.merged == [pr_task]
    for task_id in in_flight_ids:
        assert _state(ledger, task_id) in IN_FLIGHT_STATES

    asserted = reconcile(ledger, repo_id, gh=gh, stamp_orphaned=True)
    assert sorted(asserted.orphaned) == sorted(in_flight_ids)
    for task_id in in_flight_ids:
        assert _state(ledger, task_id) == "ORPHANED"
