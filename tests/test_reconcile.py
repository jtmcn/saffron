"""`saffron/reconcile.py`. No network, no cell: every `gh` here is a fake
`GhRunner`; `tests/conftest.py`'s `no_host_tool_exec` guard would raise on
a real one."""

from __future__ import annotations

import json
import subprocess

import pytest

from saffron.intake import load_spec
from saffron.ledger import Ledger
from saffron.reconcile import (
    IN_FLIGHT_STATES,
    PR_PENDING_STATES,
    HeadMoved,
    reconcile,
)


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


def _repo(ledger, origin="https://github.com/jtmcn/saffron.git"):
    return ledger.upsert_repo("saffron", origin, "/m.git", policy_sha="p" * 64)


def _task(ledger, repo_id, *, spec_id, state, pr_url=None, pushed_sha=None):
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
    if pushed_sha is not None:
        ledger.record_push(task_id, pushed_sha)
    return task_id


def _state(ledger, task_id):
    return ledger._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()["state"]


class _FakeGh:
    """`answers[url]` is the JSON body `gh pr view` would print, or `None`
    for a `gh` call that fails outright (returncode != 0). Like real `gh`, it
    prints only the fields `--json` asked for, so code that forgets to ask for
    one reads it as absent.

    A `str` answer is returned verbatim as stdout with a zero exit, for a
    body `gh` printed that does not parse as JSON. A `list` answer is dumped
    as JSON with a zero exit, for a body that parses but is the wrong shape."""

    def __init__(self, answers: dict[str, dict | str | list | None]) -> None:
        self.answers = answers
        self.calls: list[str] = []

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        assert argv[:3] == ["gh", "pr", "view"]
        self.calls.append(argv[3])
        answer = self.answers.get(argv[3])
        if answer is None:
            return subprocess.CompletedProcess(argv, 1, "", "not found")
        if isinstance(answer, str):
            return subprocess.CompletedProcess(argv, 0, answer, "")
        if isinstance(answer, list):
            return subprocess.CompletedProcess(argv, 0, json.dumps(answer), "")
        asked = argv[argv.index("--json") + 1].split(",")
        shown = {key: value for key, value in answer.items() if key in asked}
        return subprocess.CompletedProcess(argv, 0, json.dumps(shown), "")


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
    answers: dict[str, dict | str | list | None] = {
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
        (
            {"state": "OPEN", "reviewDecision": None, "isDraft": False},
            "approved",
            "APPROVED",
        ),
        (
            {"state": "OPEN", "reviewDecision": None, "isDraft": True},
            None,
            "READY_FOR_REVIEW",
        ),
        ({"state": "OPEN", "reviewDecision": None}, None, "READY_FOR_REVIEW"),
        # The sixth mapping the module says it does not make: an unrecognised
        # `state` leaves the row exactly as it was, like an unanswerable `gh`.
        ({"state": "SOMETHING_NEW", "reviewDecision": None}, None, "READY_FOR_REVIEW"),
    ],
    ids=[
        "closed-unmerged",
        "open-changes-requested",
        "open-marked-ready",
        "open-draft",
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
        assert result.approved == []
    assert _state(ledger, task_id) == expect_state


@pytest.mark.parametrize(
    "pr, expect_state",
    [
        ({"state": "MERGED", "reviewDecision": None}, "MERGED"),
        ({"state": "CLOSED", "reviewDecision": None}, "REJECTED"),
        (
            {"state": "OPEN", "reviewDecision": "CHANGES_REQUESTED", "isDraft": False},
            "CHANGES_REQUESTED",
        ),
        ({"state": "OPEN", "reviewDecision": None, "isDraft": False}, "APPROVED"),
        ({"state": "OPEN", "reviewDecision": None, "isDraft": True}, "APPROVED"),
    ],
    ids=["merged", "closed", "changes-requested", "still-ready", "back-to-draft"],
)
def test_an_approved_task_moves_on_and_never_back(ledger, pr, expect_state):
    """Item 52. A pull request returned to draft leaves `APPROVED` as it was."""
    repo_id = _repo(ledger)
    url = "https://github.com/jtmcn/saffron/pull/101"
    task_id = _task(ledger, repo_id, spec_id="SA-9002", state="APPROVED", pr_url=url)

    reconcile(ledger, repo_id, gh=_FakeGh({url: pr}))

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


# --- A head past what PACKAGE pushed (backlog item 97) ---

_PUSHED = "a" * 40
_FIXED = "b" * 40


def test_a_head_other_than_what_package_pushed_is_reported_and_moves_no_state(
    ledger,
):
    """A review fix committed after PACKAGE reached no gate, critic or
    record. Reconcile is the one reader already asking GitHub about the pull
    request, so it names the gap — and writes nothing, because the row's
    state is still true."""
    repo_id = _repo(ledger)
    url = "https://github.com/jtmcn/saffron/pull/106"
    task_id = _task(
        ledger,
        repo_id,
        spec_id="SA-9301",
        state="READY_FOR_REVIEW",
        pr_url=url,
        pushed_sha=_PUSHED,
    )
    gh = _FakeGh({url: {"state": "OPEN", "reviewDecision": None, "headRefOid": _FIXED}})

    result = reconcile(ledger, repo_id, gh=gh)

    assert result.head_moved == [HeadMoved(task_id, _PUSHED, _FIXED)]
    assert _state(ledger, task_id) == "READY_FOR_REVIEW"


def test_a_merge_over_a_moved_head_is_reported_at_the_one_chance_there_is(ledger):
    """`MERGED` is never asked about again, so the run that sees the merge is
    the last that can say unjudged commits went in with it."""
    repo_id = _repo(ledger)
    url = "https://github.com/jtmcn/saffron/pull/107"
    task_id = _task(
        ledger,
        repo_id,
        spec_id="SA-9302",
        state="READY_FOR_REVIEW",
        pr_url=url,
        pushed_sha=_PUSHED,
    )
    gh = _FakeGh(
        {url: {"state": "MERGED", "reviewDecision": None, "headRefOid": _FIXED}}
    )

    result = reconcile(ledger, repo_id, gh=gh)

    assert result.merged == [task_id]
    assert result.head_moved == [HeadMoved(task_id, _PUSHED, _FIXED)]


@pytest.mark.parametrize(
    "pushed, answer",
    [
        (_PUSHED, {"headRefOid": _PUSHED}),
        (_PUSHED, {}),
        (_PUSHED, {"headRefOid": ""}),
        (_PUSHED, {"headRefOid": 123}),
        (None, {"headRefOid": _FIXED}),
    ],
    ids=[
        "head-is-what-was-pushed",
        "no-head-answered",
        "empty-head",
        "head-not-a-string",
        "no-push-recorded",
    ],
)
def test_a_head_that_cannot_be_compared_is_never_called_moved(ledger, pushed, answer):
    """Absence of an answer is not a claim, here as everywhere in this module:
    only two real shas that differ say the head moved."""
    repo_id = _repo(ledger)
    url = "https://github.com/jtmcn/saffron/pull/108"
    _task(
        ledger,
        repo_id,
        spec_id="SA-9303",
        state="READY_FOR_REVIEW",
        pr_url=url,
        pushed_sha=pushed,
    )
    gh = _FakeGh({url: {"state": "OPEN", "reviewDecision": None, **answer}})

    assert reconcile(ledger, repo_id, gh=gh).head_moved == []


def _merged_head(ledger, task_id):
    return ledger._db.execute(
        "SELECT merged_head_sha FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()["merged_head_sha"]


def test_a_merge_records_the_commit_its_pull_request_merged_at(ledger):
    """A `MERGED` row keeps the head GitHub reported for its pull request,
    whatever `pushed_sha` says: different, identical, or absent entirely
    (backlog item 97)."""
    repo_id = _repo(ledger)
    moved_url = "https://github.com/jtmcn/saffron/pull/201"
    moved = _task(
        ledger,
        repo_id,
        spec_id="SA-9401",
        state="READY_FOR_REVIEW",
        pr_url=moved_url,
        pushed_sha=_PUSHED,
    )
    same_url = "https://github.com/jtmcn/saffron/pull/202"
    same = _task(
        ledger,
        repo_id,
        spec_id="SA-9402",
        state="READY_FOR_REVIEW",
        pr_url=same_url,
        pushed_sha=_PUSHED,
    )
    unpushed_url = "https://github.com/jtmcn/saffron/pull/203"
    unpushed = _task(
        ledger,
        repo_id,
        spec_id="SA-9403",
        state="READY_FOR_REVIEW",
        pr_url=unpushed_url,
        pushed_sha=None,
    )
    gh = _FakeGh(
        {
            moved_url: {
                "state": "MERGED",
                "reviewDecision": None,
                "headRefOid": _FIXED,
            },
            same_url: {
                "state": "MERGED",
                "reviewDecision": None,
                "headRefOid": _PUSHED,
            },
            unpushed_url: {
                "state": "MERGED",
                "reviewDecision": None,
                "headRefOid": _FIXED,
            },
        }
    )

    result = reconcile(ledger, repo_id, gh=gh)

    assert set(result.merged) == {moved, same, unpushed}
    assert _merged_head(ledger, moved) == _FIXED
    assert _merged_head(ledger, same) == _PUSHED
    assert _merged_head(ledger, unpushed) == _FIXED


def test_a_head_is_recorded_only_for_an_observed_merge(ledger):
    """A merge GitHub answered with no usable head — absent, empty, or not a
    string — records nothing, and a real head over a non-merge move is left
    where `head_moved` alone already reports it (backlog item 97)."""
    repo_id = _repo(ledger)
    no_answer_url = "https://github.com/jtmcn/saffron/pull/204"
    no_answer = _task(
        ledger,
        repo_id,
        spec_id="SA-9404",
        state="READY_FOR_REVIEW",
        pr_url=no_answer_url,
        pushed_sha=_PUSHED,
    )
    empty_url = "https://github.com/jtmcn/saffron/pull/205"
    empty = _task(
        ledger,
        repo_id,
        spec_id="SA-9405",
        state="READY_FOR_REVIEW",
        pr_url=empty_url,
        pushed_sha=_PUSHED,
    )
    nonstring_url = "https://github.com/jtmcn/saffron/pull/206"
    nonstring = _task(
        ledger,
        repo_id,
        spec_id="SA-9406",
        state="READY_FOR_REVIEW",
        pr_url=nonstring_url,
        pushed_sha=_PUSHED,
    )
    changes_url = "https://github.com/jtmcn/saffron/pull/207"
    changes = _task(
        ledger,
        repo_id,
        spec_id="SA-9407",
        state="READY_FOR_REVIEW",
        pr_url=changes_url,
        pushed_sha=_PUSHED,
    )
    rejected_url = "https://github.com/jtmcn/saffron/pull/208"
    rejected = _task(
        ledger,
        repo_id,
        spec_id="SA-9408",
        state="READY_FOR_REVIEW",
        pr_url=rejected_url,
        pushed_sha=_PUSHED,
    )
    gh = _FakeGh(
        {
            no_answer_url: {"state": "MERGED", "reviewDecision": None},
            empty_url: {"state": "MERGED", "reviewDecision": None, "headRefOid": ""},
            nonstring_url: {
                "state": "MERGED",
                "reviewDecision": None,
                "headRefOid": 123,
            },
            changes_url: {
                "state": "OPEN",
                "reviewDecision": "CHANGES_REQUESTED",
                "headRefOid": _FIXED,
            },
            rejected_url: {
                "state": "CLOSED",
                "reviewDecision": None,
                "headRefOid": _FIXED,
            },
        }
    )

    result = reconcile(ledger, repo_id, gh=gh)

    assert set(result.merged) == {no_answer, empty, nonstring}
    assert result.changes_requested == [changes]
    assert result.rejected == [rejected]
    # The claim is about the row, not the bucket: a merge with no usable head
    # still moves, and the head alone is what goes unrecorded.
    for task_id in (no_answer, empty, nonstring):
        assert _state(ledger, task_id) == "MERGED"
    for task_id in (no_answer, empty, nonstring, changes, rejected):
        assert _merged_head(ledger, task_id) is None


def test_the_merged_head_is_written_before_the_state_moves(ledger, monkeypatch):
    """A `MERGED` row is never asked about again, so a crash between the two
    writes must be able to lose only the second one: the head has to land
    on the ledger before the state does (backlog item 97)."""
    repo_id = _repo(ledger)
    url = "https://github.com/jtmcn/saffron/pull/209"
    _task(
        ledger,
        repo_id,
        spec_id="SA-9409",
        state="READY_FOR_REVIEW",
        pr_url=url,
        pushed_sha=_PUSHED,
    )
    gh = _FakeGh(
        {url: {"state": "MERGED", "reviewDecision": None, "headRefOid": _FIXED}}
    )
    calls: list[str] = []
    real_record_head = ledger.record_merged_head
    real_set_state = ledger.set_task_state

    def spy_record_head(task_id, head):
        calls.append("head")
        return real_record_head(task_id, head)

    def spy_set_state(task_id, state):
        calls.append("state")
        return real_set_state(task_id, state)

    monkeypatch.setattr(ledger, "record_merged_head", spy_record_head)
    monkeypatch.setattr(ledger, "set_task_state", spy_set_state)

    reconcile(ledger, repo_id, gh=gh)

    assert calls == ["head", "state"]


def test_a_merge_a_crash_cut_short_completes_on_the_next_reconcile_without_asking(
    ledger, monkeypatch
):
    """A crash between `record_merged_head` and `set_task_state` leaves a
    merged head on a row still in a pending state. The next scan reads
    that head back and completes the row with no `gh` call, whatever
    pending state it was in (b-3e0dbe)."""
    repo_id = _repo(ledger)
    real_set_state = ledger.set_task_state

    def raising_set_state(task_id, state):
        raise RuntimeError("crash between the two writes")

    crashed = {}
    for i, state in enumerate(sorted(PR_PENDING_STATES)):
        spec_id = f"SA-95{10 + i}"
        url = f"https://github.com/jtmcn/saffron/pull/{310 + i}"
        task_id = _task(
            ledger,
            repo_id,
            spec_id=spec_id,
            state=state,
            pr_url=url,
            pushed_sha=_PUSHED,
        )
        crashed[spec_id] = (task_id, url, state)

        monkeypatch.setattr(ledger, "set_task_state", raising_set_state)
        gh = _FakeGh(
            {url: {"state": "MERGED", "reviewDecision": None, "headRefOid": _FIXED}}
        )
        with pytest.raises(RuntimeError):
            reconcile(ledger, repo_id, gh=gh, spec_id=spec_id)
        monkeypatch.setattr(ledger, "set_task_state", real_set_state)

    for _spec_id, (task_id, _url, state) in crashed.items():
        assert _merged_head(ledger, task_id) == _FIXED
        assert _state(ledger, task_id) == state

    plain_url = "https://github.com/jtmcn/saffron/pull/399"
    plain_id = _task(
        ledger,
        repo_id,
        spec_id="SA-9599",
        state="READY_FOR_REVIEW",
        pr_url=plain_url,
        pushed_sha=_PUSHED,
    )

    dead_gh = _FakeGh({})
    result = reconcile(ledger, repo_id, gh=dead_gh)

    assert set(result.merged) == {task_id for task_id, _url, _was in crashed.values()}
    for _spec_id, (task_id, url, _was) in crashed.items():
        assert url not in dead_gh.calls
        assert _state(ledger, task_id) == "MERGED"
        assert _merged_head(ledger, task_id) == _FIXED
    assert result.unasked == [plain_id]
    assert _state(ledger, plain_id) == "READY_FOR_REVIEW"

    third = reconcile(ledger, repo_id, gh=dead_gh)
    assert third.merged == []


# --- An `EXHAUSTED` draft that merges anyway (backlog item b-8e30bd) ---


def test_a_merged_draft_moves_its_exhausted_task_to_merged(ledger):
    """A draft PACKAGE opened for a task that ran out of budget can still
    merge. The merged answer applies through the writes a pending row's
    merge already uses. A crash-recovered row with its head on the
    ledger completes with no `gh` call."""
    repo_id = _repo(ledger)
    moved_url = "https://github.com/jtmcn/saffron/pull/301"
    moved = _task(ledger, repo_id, spec_id="SA-9601", state="REVIEWING")
    ledger.set_task_package(
        moved,
        "EXHAUSTED",
        branch="saffron/SA-9601",
        pushed_sha=_PUSHED,
        pr_url=moved_url,
    )
    crashed_url = "https://github.com/jtmcn/saffron/pull/302"
    crashed = _task(ledger, repo_id, spec_id="SA-9602", state="REBUTTING")
    ledger.set_task_package(
        crashed,
        "EXHAUSTED",
        branch="saffron/SA-9602",
        pushed_sha=_PUSHED,
        pr_url=crashed_url,
    )
    ledger.record_merged_head(crashed, _FIXED)
    gh = _FakeGh(
        {moved_url: {"state": "MERGED", "reviewDecision": None, "headRefOid": _FIXED}}
    )

    result = reconcile(ledger, repo_id, gh=gh)

    assert set(result.merged) == {moved, crashed}
    assert _state(ledger, moved) == "MERGED"
    assert _state(ledger, crashed) == "MERGED"
    assert _merged_head(ledger, moved) == _FIXED
    assert result.head_moved == [HeadMoved(moved, _PUSHED, _FIXED)]
    assert crashed_url not in gh.calls


def test_an_exhausted_task_moves_on_no_answer_but_a_merge(ledger):
    """Every other answer about an `EXHAUSTED` row's pull request leaves it
    `EXHAUSTED`. The nine rows with a pull request drive every answer
    `_pr_status` can give: the six it returns as an object, and the three
    it turns into `None`."""
    repo_id = _repo(ledger)

    def _exhausted(spec_id, url):
        task_id = _task(ledger, repo_id, spec_id=spec_id, state="REVIEWING")
        ledger.set_task_package(
            task_id,
            "EXHAUSTED",
            branch=f"saffron/{spec_id}",
            pushed_sha=_PUSHED,
            pr_url=url,
        )
        return task_id

    claimed = {
        "closed": ({"state": "CLOSED", "reviewDecision": None}, "SA-9701"),
        "changes-requested": (
            {"state": "OPEN", "reviewDecision": "CHANGES_REQUESTED"},
            "SA-9702",
        ),
        "marked-ready": (
            {"state": "OPEN", "reviewDecision": None, "isDraft": False},
            "SA-9703",
        ),
        "open-draft": (
            {"state": "OPEN", "reviewDecision": None, "isDraft": True},
            "SA-9704",
        ),
        "open-no-isdraft-field": ({"state": "OPEN", "reviewDecision": None}, "SA-9705"),
        "unrecognised-state": (
            {"state": "SOMETHING_NEW", "reviewDecision": None},
            "SA-9706",
        ),
    }
    answers: dict[str, dict | str | list | None] = {}
    task_ids: dict[str, int] = {}
    for i, (label, (pr, spec_id)) in enumerate(claimed.items()):
        url = f"https://github.com/jtmcn/saffron/pull/{700 + i}"
        task_ids[label] = _exhausted(spec_id, url)
        answers[url] = pr

    unanswerable = {
        "nonzero-exit": (None, "SA-9710"),
        "unparseable": ("not json", "SA-9711"),
        "wrong-shape": ([], "SA-9712"),
    }
    for i, (label, (answer, spec_id)) in enumerate(unanswerable.items()):
        url = f"https://github.com/jtmcn/saffron/pull/{710 + i}"
        task_ids[label] = _exhausted(spec_id, url)
        answers[url] = answer

    no_pr_null = _task(ledger, repo_id, spec_id="SA-9720", state="EXHAUSTED")
    no_pr_empty = _task(
        ledger, repo_id, spec_id="SA-9721", state="EXHAUSTED", pr_url=""
    )

    gh = _FakeGh(answers)
    result = reconcile(ledger, repo_id, gh=gh)

    for label in claimed:
        task_id = task_ids[label]
        assert _state(ledger, task_id) == "EXHAUSTED"
        assert task_id not in result.unasked
    for label in unanswerable:
        task_id = task_ids[label]
        assert _state(ledger, task_id) == "EXHAUSTED"
        assert task_id in result.unasked
    assert result.merged == result.rejected == result.changes_requested == []
    assert result.approved == []
    assert sorted(gh.calls) == sorted(answers)
    assert _state(ledger, no_pr_null) == "EXHAUSTED"
    assert _state(ledger, no_pr_empty) == "EXHAUSTED"


def test_a_merged_exhausted_parent_admits_its_child_to_the_queue(tmp_path, ledger):
    """`build_queue` refuses a child whose only parent row is a dead
    `EXHAUSTED` state. Once `reconcile` reads a merged answer for that
    parent's draft, the same scan admits the child and refuses nothing."""
    from saffron.scheduler import build_queue

    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    parent_id, child_id = "SA-9801", "SA-9802"
    (specs_dir / "parent.md").write_text(
        f"---\nid: {parent_id}\ntitle: Parent\ntype: chore\n---\n\nParent body.\n"
    )
    (specs_dir / "child.md").write_text(
        f"---\nid: {child_id}\ntitle: Child\ntype: chore\n"
        f"depends_on: [{parent_id}]\n---\n\nChild body.\n"
    )

    parent_spec, parent_sha = load_spec(specs_dir / "parent.md")
    repo_id = _repo(ledger)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    parent_task = ledger.create_task(
        run_id, spec_id=parent_spec.id, spec_sha=parent_sha, branch="saffron/SA-9801"
    )
    url = "https://github.com/jtmcn/saffron/pull/901"
    ledger.set_task_package(
        parent_task,
        "EXHAUSTED",
        branch="saffron/SA-9801",
        pushed_sha=_PUSHED,
        pr_url=url,
    )

    before_candidates, before_refusals = build_queue(specs_dir, repo_id, ledger)
    assert [c.spec.id for c in before_candidates] == []
    assert len(before_refusals) == 1
    assert before_refusals[0].path == specs_dir / "child.md"
    assert "EXHAUSTED" in before_refusals[0].reason

    gh = _FakeGh({url: {"state": "MERGED", "reviewDecision": None}})
    reconcile(ledger, repo_id, gh=gh)

    assert _state(ledger, parent_task) == "MERGED"
    after_candidates, after_refusals = build_queue(specs_dir, repo_id, ledger)
    assert [c.spec.id for c in after_candidates] == [child_id]
    assert after_refusals == []


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
