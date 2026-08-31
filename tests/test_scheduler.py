import json
import shutil
import subprocess
from pathlib import Path

import pytest

from saffron.cell import runtime
from saffron.intake import load_spec
from saffron.ledger import Ledger
from saffron.scheduler import (
    DONE_STATES,
    REQUEUE_STATES,
    build_queue,
    retirement_refusal,
)
from tests.conftest import HostToolExecInTest


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


def _sha(path):
    """The spec_sha the scan would compute for a spec file on disk."""
    return load_spec(path)[1]


def _repo(ledger, origin="/o"):
    return ledger.upsert_repo("r", origin, "/m.git", policy_sha="p" * 64)


def _write_spec(
    directory,
    name,
    *,
    id,
    type="feature",
    priority=3,
    touches=None,
    depends_on=None,
    forbidden=None,
    body="",
):
    """A spec with the frontmatter the refusal-gate tests need — `_write`
    only carries id/type/priority, and these tests need `touches`,
    `forbidden`, `depends_on` and a body worth parsing acceptance criteria
    out of."""
    lines = ["---", f"id: {id}", "title: t", f"type: {type}", f"priority: {priority}"]
    if depends_on:
        lines.append("depends_on:")
        lines += [f"  - {d}" for d in depends_on]
    if touches:
        lines.append("touches:")
        lines += [f"  - {t}" for t in touches]
    if forbidden:
        lines.append("forbidden:")
        lines += [f"  - {f}" for f in forbidden]
    lines.append("---")
    lines.append("")
    lines.append(body)
    (directory / name).write_text("\n".join(lines) + "\n")


def _fake_gh(prs):
    """A `GhRunner` that never leaves the process — `prs` is the parsed JSON
    `gh pr list --json ...` would have printed."""
    payload = json.dumps(prs)

    def gh(argv):
        return subprocess.CompletedProcess(
            argv, returncode=0, stdout=payload, stderr=""
        )

    return gh


def _raw_gh(stdout, returncode=0):
    """A `GhRunner` returning bytes `gh` really can print — the failure and
    malformed shapes `_fake_gh` cannot express, since it always serialises
    well-formed JSON with a zero exit."""

    def gh(argv):
        return subprocess.CompletedProcess(
            argv, returncode=returncode, stdout=stdout, stderr=""
        )

    return gh


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


def test_tasks_by_spec_keeps_every_task_at_a_key_oldest_first(ledger):
    repo_id = _repo(ledger, "/o")
    first = _task_at(ledger, repo_id, spec_id="TE-1", spec_sha="s1", state="REJECTED")
    second = _task_at(
        ledger, repo_id, spec_id="TE-1", spec_sha="s1", state="CHANGES_REQUESTED"
    )
    assert second > first

    rows = ledger.tasks_by_spec(repo_id)[("TE-1", "s1")]

    # Both, in task_id order: the done-state check reads all of them, and the
    # live ledger really does hold ten at one key (SA-0013/ce08b1eb).
    assert [row["task_id"] for row in rows] == [first, second]
    assert [row["state"] for row in rows] == ["REJECTED", "CHANGES_REQUESTED"]


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


def test_a_done_task_wins_over_a_later_requeueing_one_at_the_same_sha(tmp_path, ledger):
    """The shape the live ledger actually has. A `READY_FOR_REVIEW` task with
    an open PR, then a later `saffron cell` on the same spec killed mid-flight
    and stamped `ORPHANED`: §4.2.1 asks whether *a* task is done with the spec,
    so the newer corpse must not re-queue work that is already up for review —
    gate 0 (`SA-0016`) would only refuse it again on its own PR.
    """
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1")
    repo_id = _repo(ledger)
    _, spec_sha = load_spec(directory / "a.md")
    done = _task_at(
        ledger, repo_id, spec_id="TE-1", spec_sha=spec_sha, state="READY_FOR_REVIEW"
    )
    corpse = _task_at(
        ledger, repo_id, spec_id="TE-1", spec_sha=spec_sha, state="ORPHANED"
    )
    assert corpse > done

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert candidates == []
    assert refusals == []


def test_the_newest_send_back_is_the_one_resumed(tmp_path, ledger):
    """Many re-queueing tasks and none done: the resumed row is the latest,
    not whichever the query happened to reach first."""
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1")
    repo_id = _repo(ledger)
    _, spec_sha = load_spec(directory / "a.md")
    _task_at(ledger, repo_id, spec_id="TE-1", spec_sha=spec_sha, state="GATE_ERROR")
    latest = _task_at(
        ledger, repo_id, spec_id="TE-1", spec_sha=spec_sha, state="CHANGES_REQUESTED"
    )

    candidates, _ = build_queue(directory, repo_id, ledger)

    assert [c.task_id for c in candidates] == [latest]


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
    """The scan is disk and ledger only. The guard is an exec tripwire, not a
    socket one — it covers the two ways this codebase leaves the host, and the
    second half of this test is what makes the first half's claim worth
    anything, since a guard that no longer fires reads exactly like a scan that
    never called out.
    """
    directory = _spec_dir(tmp_path)
    _write(directory, "a.md", id="TE-1")

    candidates, refusals = build_queue(directory, None, ledger)

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []

    with pytest.raises(HostToolExecInTest):
        subprocess.Popen(["gh", "pr", "list"])
    with pytest.raises(HostToolExecInTest):
        subprocess.Popen([runtime.RUNTIME, "run", "saffron/cell"])


# ---------------------------------------------------- refusal: open pull request


def test_an_open_pr_from_another_task_refuses(tmp_path, ledger):
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"])
    gh = _fake_gh(
        [{"headRefName": "saffron/TE-1", "url": "https://example/pull/9", "files": []}]
    )

    candidates, refusals = build_queue(directory, None, ledger, repo_slug="o/r", gh=gh)

    assert candidates == []
    assert len(refusals) == 1
    assert refusals[0].path.name == "a.md"
    assert "another task" in refusals[0].reason
    assert "https://example/pull/9" in refusals[0].reason


def test_resuming_its_own_task_is_not_refused_by_its_own_open_pr(tmp_path, ledger):
    """DESIGN.md §4.2's footnote: refusal is keyed on `task_id`, not the spec,
    so a `CHANGES_REQUESTED` re-queue survives finding its own PR still open."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"])
    repo_id = _repo(ledger)
    _, spec_sha = load_spec(directory / "a.md")
    task_id = _task_at(
        ledger, repo_id, spec_id="TE-1", spec_sha=spec_sha, state="CHANGES_REQUESTED"
    )
    gh = _fake_gh(
        [{"headRefName": "saffron/TE-1", "url": "https://example/pull/9", "files": []}]
    )

    candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="o/r", gh=gh
    )

    assert refusals == []
    assert [c.task_id for c in candidates] == [task_id]


def test_no_repo_slug_skips_the_github_backed_refusals(tmp_path, ledger):
    """The default before `SA-0017` wires the CLI: no slug, no `gh` call, and
    the two GitHub-backed refusals are inert rather than erroring."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"])

    def exploding_gh(argv):
        raise AssertionError(f"gh should not have been called: {argv}")

    candidates, refusals = build_queue(directory, None, ledger, gh=exploding_gh)

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


@pytest.mark.parametrize(
    "stdout,returncode",
    [
        ("", 1),
        ("gh: not authenticated\n", 1),
        ("<html>rate limited</html>", 0),
        ("[1, 2]", 0),
        ('[{"headRefName":"other","files":null}]', 0),
        ('[{"headRefName":"other","files":["a.py"]}]', 0),
    ],
    ids=["exit-1", "auth-error", "not-json", "int-elements", "files-null", "files-str"],
)
def test_a_broken_gh_queues_rather_than_aborting_the_scan(
    tmp_path, ledger, stdout, returncode
):
    """`_open_prs` documents itself as best-effort, and these are the shapes
    that reach it on an unauthenticated host or a `gh` whose JSON moved. Each
    is valid enough to get past a top-level check and raise on `.get` instead
    — and §4.2.1 gives a refusal defined handling where an exception has none,
    so a scan that raises here loses the night rather than one candidate."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"])

    candidates, refusals = build_queue(
        directory, None, ledger, repo_slug="o/r", gh=_raw_gh(stdout, returncode)
    )

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


# ------------------------------------------------------ refusal: touches overlap


def test_a_touches_overlap_with_an_open_prs_files_refuses(tmp_path, ledger):
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"])
    gh = _fake_gh(
        [{"headRefName": "saffron/OTHER-1", "url": "u", "files": [{"path": "a.py"}]}]
    )

    candidates, refusals = build_queue(directory, None, ledger, repo_slug="o/r", gh=gh)

    assert candidates == []
    assert len(refusals) == 1
    assert "touches overlaps" in refusals[0].reason
    assert "a.py" in refusals[0].reason
    # The url, not the branch — the sibling refusal prints the url, and one
    # morning queue naming the same pull request two ways is a reread.
    assert "u" in refusals[0].reason
    assert "saffron/OTHER-1" not in refusals[0].reason


def test_the_stacking_parents_own_pull_request_is_not_an_overlap(tmp_path, ledger):
    """A stacked child starts from its parent's tree, so sharing files with
    the parent's open pull request is what stacking is for. Left refused,
    this check shadowed the dependency admission entirely: a parent at
    `READY_FOR_REVIEW` has an open pull request by definition, and almost
    every spec in this repository touches `docs/BACKLOG.md` (`SA-0026`)."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-0",
        spec_sha=_sha(directory / "b.md"),
        state="READY_FOR_REVIEW",
    )
    gh = _fake_gh(
        [{"headRefName": "saffron/TE-0", "url": "u", "files": [{"path": "a.py"}]}]
    )

    _candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="o/r", gh=gh
    )

    assert [r for r in refusals if r.path.name == "a.md"] == []


def test_a_third_partys_overlap_still_refuses_a_stacked_child(tmp_path, ledger):
    """The exemption above is `depends_on[0]`'s branch and nothing else —
    K=1, the same one `cli._resolve_stacked_on` stacks on. Another task's
    pull request over the same file is the collision the check exists for."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-0",
        spec_sha=_sha(directory / "b.md"),
        state="READY_FOR_REVIEW",
    )
    gh = _fake_gh(
        [
            {"headRefName": "saffron/TE-0", "url": "p", "files": [{"path": "a.py"}]},
            {"headRefName": "saffron/OTHER", "url": "o", "files": [{"path": "a.py"}]},
        ]
    )

    _candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="o/r", gh=gh
    )

    mine = [r for r in refusals if r.path.name == "a.md"]
    assert len(mine) == 1
    assert "touches overlaps" in mine[0].reason and "o" in mine[0].reason


def test_an_overlap_past_three_files_says_how_many_it_did_not_print(tmp_path, ledger):
    """`overlap[:3]` truncated silently, so a five-file overlap read as three
    — an operator sizing the conflict off the line got the wrong number."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=[f"f{n}.py" for n in range(5)])
    gh = _fake_gh(
        [
            {
                "headRefName": "saffron/OTHER-1",
                "url": "u",
                "files": [{"path": f"f{n}.py"} for n in range(5)],
            }
        ]
    )

    _, refusals = build_queue(directory, None, ledger, repo_slug="o/r", gh=gh)

    assert len(refusals) == 1
    assert "f0.py, f1.py, f2.py" in refusals[0].reason
    assert "(5 files)" in refusals[0].reason
    assert "f3.py" not in refusals[0].reason


def test_an_open_pr_with_a_null_url_names_the_branch_not_none(tmp_path, ledger):
    """`_open_prs` filters shapes, not fields, so a null `url` reaches the
    refusal. A `.get` default keeps the None; a line reading "already targets
    this spec: None" tells the operator nothing."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"])
    gh = _fake_gh([{"headRefName": "saffron/TE-1", "url": None, "files": []}])

    candidates, refusals = build_queue(directory, None, ledger, repo_slug="o/r", gh=gh)

    assert candidates == []
    assert len(refusals) == 1
    assert "None" not in refusals[0].reason
    assert "saffron/TE-1" in refusals[0].reason


def test_no_touches_overlap_with_an_open_prs_files_is_not_refused(tmp_path, ledger):
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"])
    gh = _fake_gh(
        [{"headRefName": "saffron/OTHER-1", "url": "u", "files": [{"path": "b.py"}]}]
    )

    candidates, refusals = build_queue(directory, None, ledger, repo_slug="o/r", gh=gh)

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


# ------------------------------------------- refusal: acceptance criteria path


def test_a_wrapped_criterion_naming_a_path_outside_touches_refuses(tmp_path, ledger):
    """Built on today's `spec.acceptance_criteria` — the fixture is `SA-0016`'s
    own third criterion, wrapped across two continuation lines, the same one
    `test_intake.py` uses for the truncation fix this refusal depends on. A
    fixture whose criterion is a single line would prove nothing about the
    bug `SA-0014` fixed, and this refusal would pass `SA-0005`-shaped input
    clean if it were still truncating.

    The fixture declares no `forbidden`, which is the whole difference between
    it and the real `SA-0016` it is copied from — see the next test."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        touches=["saffron/scheduler.py"],
        body=(
            "## Acceptance criteria\n"
            "- [ ] The two refusals needing GitHub take an injected runner in the\n"
            "      `GhRunner` shape `saffron/phases/package.py` already uses, and every\n"
            "      test in `tests/test_scheduler.py` runs with no network and no cell\n"
        ),
    )

    candidates, refusals = build_queue(directory, None, ledger)

    assert candidates == []
    assert len(refusals) == 1
    assert "saffron/phases/package.py" in refusals[0].reason


def test_a_criterion_citing_a_path_the_spec_forbids_itself_is_not_refused(
    tmp_path, ledger
):
    """`SA-0016` itself, frontmatter and all. Its third criterion names
    `saffron/phases/package.py` for the `GhRunner` shape to copy, and its own
    `forbidden` covers that directory — the spec's Notes say the file is "read
    for its signature only". Refusing it costs a night in which nothing ran;
    a spec that really does need a forbidden path is caught in the cell by
    `scope` on its first commit, for one attempt."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        touches=["saffron/scheduler.py", "tests/test_scheduler.py"],
        forbidden=["saffron/phases/**", "docs/**"],
        body=(
            "## Acceptance criteria\n"
            "- [ ] The two refusals needing GitHub take an injected runner in the\n"
            "      `GhRunner` shape `saffron/phases/package.py` already uses, and every\n"
            "      test in `tests/test_scheduler.py` runs with no network and no cell\n"
        ),
    )

    candidates, refusals = build_queue(directory, None, ledger)

    assert refusals == []
    assert [c.spec.id for c in candidates] == ["TE-1"]


def test_a_criterion_citing_a_path_with_a_line_number_is_not_refused(tmp_path, ledger):
    """This repo cites files as `path.py:123` throughout its prose. Because
    `scope.matches` compares whole strings, an unstripped citation never
    matches the `touches` entry that in fact covers it — refusing a spec for
    naming a file it is about to edit."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        touches=["saffron/scheduler.py"],
        body=(
            "## Acceptance criteria\n"
            "- [ ] the fold at `saffron/scheduler.py:98` reads every row, and\n"
            "      `saffron/scheduler.py:114-120` keeps the tie-break stable\n"
        ),
    )

    candidates, refusals = build_queue(directory, None, ledger)

    assert refusals == []
    assert [c.spec.id for c in candidates] == ["TE-1"]


def test_a_criterion_naming_a_glob_is_not_refused(tmp_path, ledger):
    """`SA-0011`'s shape: its criteria name `tests/fixtures/*.md` in the course
    of saying the fixture is *not* a file. A pattern is not a concrete path,
    and `scope.matches` takes one on the left — so there is nothing here it
    could answer."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        touches=["tests/test_criteria.py"],
        body=(
            "## Acceptance criteria\n"
            "- [ ] the fixture is a string literal in the test module, not a file:\n"
            "      a new `tests/fixtures/*.md` falls outside `touches` and `scope`\n"
            "      fails the diff that adds it\n"
        ),
    )

    candidates, refusals = build_queue(directory, None, ledger)

    assert refusals == []
    assert [c.spec.id for c in candidates] == ["TE-1"]


def test_a_wrapped_criterion_whose_paths_are_all_in_touches_is_not_refused(
    tmp_path, ledger
):
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        touches=[
            "saffron/scheduler.py",
            "saffron/phases/package.py",
            "tests/test_scheduler.py",
        ],
        body=(
            "## Acceptance criteria\n"
            "- [ ] The two refusals needing GitHub take an injected runner in the\n"
            "      `GhRunner` shape `saffron/phases/package.py` already uses, and every\n"
            "      test in `tests/test_scheduler.py` runs with no network and no cell\n"
        ),
    )

    candidates, refusals = build_queue(directory, None, ledger)

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


def test_criterion_path_check_is_skipped_when_touches_is_empty(tmp_path, ledger):
    """The documented shape for a bug awaiting DIAGNOSE (§5.2): every
    criterion names a path outside an empty list, so the unguarded form would
    refuse the entire bug class before DIAGNOSE could ever populate `touches`."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        type="bug",
        body="## Acceptance criteria\n- [ ] fixes `saffron/cli.py` for real\n",
    )

    candidates, refusals = build_queue(directory, None, ledger)

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


def test_criterion_path_matching_is_exact_not_a_directory_insensitive_suffix(
    tmp_path, ledger
):
    """`scope.matches("intake.py", "saffron/intake.py")` is `False` — the same
    directory-sensitivity holds for a shortened multi-segment path. A gate
    that quietly resolved a criterion's path token against `touches` by
    suffix would treat `gates/core/scope.py` as declared here, because
    `saffron/gates/core/scope.py` ends with it; `scope.matches` requires the
    whole string, so it does not, and this must still refuse."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        touches=["saffron/gates/core/scope.py"],
        body="## Acceptance criteria\n- [ ] fixes `gates/core/scope.py` for real\n",
    )

    candidates, refusals = build_queue(directory, None, ledger)

    assert candidates == []
    assert len(refusals) == 1
    assert "gates/core/scope.py" in refusals[0].reason


# ---------------------------------------------- refusal: retirement markers


def _spec_at(tmp_path, name, **kwargs):
    """A real `Spec`, parsed the way `build_queue` parses one — `_write_spec`
    writes the frontmatter, `load_spec` reads it back — so `retirement_refusal`
    is tested against the same object `_refuse` actually receives, not a
    `SimpleNamespace` standing in for one (docs/BACKLOG.md item 21's own
    lesson)."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, name, **kwargs)
    spec, _sha = load_spec(directory / name)
    return spec


def test_a_marker_inside_touches_is_not_refused(tmp_path):
    spec = _spec_at(tmp_path, "a.md", id="TE-9", touches=["saffron/x.py"])

    assert retirement_refusal(spec, [("saffron/x.py", "TE-9")]) is None


def test_reachability_is_scope_matches_and_not_string_equality(tmp_path):
    """Criterion 4: "declared" means one thing in every gate. Every other
    marker test uses a literal path equal to a literal pattern, so nothing
    there can tell `scope.matches` from `==` — measured, both substitutions
    passed all 163 tests. A glob and a nested path can.

    The argument order is load-bearing too: `matches(path, pattern)`, not the
    reverse. Swapped, `saffron/**` is asked whether it matches the pattern
    `saffron/deep/x.py`, which it does not."""
    spec = _spec_at(tmp_path, "a.md", id="TE-9", touches=["saffron/**"])

    assert retirement_refusal(spec, [("saffron/deep/x.py", "TE-9")]) is None


def test_a_forbidden_glob_reaches_a_nested_marker_too(tmp_path):
    """The same rule on the `forbidden` half, which has its own call to
    `matches` and so its own way to drift into equality."""
    spec = _spec_at(
        tmp_path, "a.md", id="TE-9", touches=["src/**"], forbidden=["docs/**"]
    )

    reason = retirement_refusal(spec, [("docs/BACKLOG.md", "TE-9")])

    assert reason is not None
    assert "forbidden" in reason


def test_a_marker_outside_touches_refuses_and_names_the_file_and_touches(
    tmp_path,
):
    """`SA-0026`'s own measured defect: a guard says `TE-9` will retire it,
    sitting in a file `TE-9`'s `touches` does not cover."""
    spec = _spec_at(tmp_path, "a.md", id="TE-9", touches=["saffron/x.py"])

    reason = retirement_refusal(spec, [("tests/test_package.py", "TE-9")])

    assert reason is not None
    assert "tests/test_package.py" in reason
    assert "saffron/x.py" in reason


def test_a_marker_in_the_specs_own_forbidden_list_refuses_differently(tmp_path):
    """A spec that may not touch the file at all cannot retire the guard
    either — a different mistake from `touches` merely not reaching it, and
    the acceptance criteria ask for it to read differently so an operator
    fixes the right thing."""
    spec = _spec_at(
        tmp_path,
        "a.md",
        id="TE-9",
        touches=["saffron/x.py"],
        forbidden=["saffron/phases/package.py"],
    )

    reason = retirement_refusal(spec, [("saffron/phases/package.py", "TE-9")])

    assert reason is not None
    assert "saffron/phases/package.py" in reason
    assert "forbidden" in reason
    assert reason != retirement_refusal(spec, [("tests/test_package.py", "TE-9")])


def test_a_marker_naming_a_different_spec_is_not_this_candidates_problem(
    tmp_path,
):
    spec = _spec_at(tmp_path, "a.md", id="TE-9", touches=["saffron/x.py"])

    assert retirement_refusal(spec, [("tests/test_package.py", "TE-10")]) is None


def test_a_bug_spec_with_no_touches_yet_is_not_refused_by_its_own_marker(tmp_path):
    """Empty `touches` is a bug awaiting DIAGNOSE (§5.2) — the one phase that
    could ever populate it must not be refused out from under itself."""
    spec = _spec_at(tmp_path, "a.md", id="TE-9", type="bug")
    assert spec.touches == []

    assert retirement_refusal(spec, [("saffron/x.py", "TE-9")]) is None


def test_a_bug_specs_forbidden_marker_still_refuses_despite_empty_touches(
    tmp_path,
):
    """`forbidden` is not deferred alongside `touches` — a permanent fact
    DIAGNOSE cannot change."""
    spec = _spec_at(
        tmp_path, "a.md", id="TE-9", type="bug", forbidden=["saffron/phases/package.py"]
    )

    reason = retirement_refusal(spec, [("saffron/phases/package.py", "TE-9")])

    assert reason is not None
    assert "forbidden" in reason


def test_build_queue_still_admits_a_bug_spec_with_no_touches_despite_its_marker(
    tmp_path, ledger
):
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-9", type="bug")

    candidates, refusals = build_queue(
        directory, None, ledger, markers=[("saffron/x.py", "TE-9")]
    )

    assert [c.spec.id for c in candidates] == ["TE-9"]
    assert refusals == []


def test_a_marker_naming_an_unknown_spec_id_gets_its_own_dangling_line(
    tmp_path, ledger
):
    """`SA-0024`'s `done/` rule, applied to a marker instead of a
    `depends_on`: not silence, and not `TE-9`'s own refusal either — it has
    nothing to do with the dangling marker and is still queued."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-9", touches=["saffron/x.py"])

    candidates, refusals = build_queue(
        directory,
        None,
        ledger,
        markers=[("saffron/ghost.py", "TE-404")],
    )

    assert [c.spec.id for c in candidates] == ["TE-9"]
    assert len(refusals) == 1
    assert "saffron/ghost.py" in refusals[0].reason
    assert "TE-404" in refusals[0].reason
    assert refusals[0].path == Path("saffron/ghost.py")


def test_a_dangling_line_says_so_when_a_spec_file_could_not_be_read(tmp_path, ledger):
    """`known_ids` is built from the spec files that parsed, so an id declared
    only by one that did not reads as declared by nothing. Calling that
    dangling asserts something this scan never read — the same case
    `_dependency_refusal` qualifies rather than asserting past (§4.2.1)."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-9", touches=["saffron/x.py"])
    (directory / "b.md").write_text("no frontmatter here\n")

    _candidates, refusals = build_queue(
        directory,
        None,
        ledger,
        markers=[("saffron/ghost.py", "TE-404")],
    )

    dangling = next(r.reason for r in refusals if r.path.name == "ghost.py")
    assert "a dangling reference" in dangling
    assert "1 spec file here did not parse" in dangling


def test_a_dangling_line_is_unqualified_when_every_spec_file_parsed(tmp_path, ledger):
    """The other half: with nothing unread, the line must not hedge. A
    qualifier that is always present tells an operator nothing about which
    scan actually had a blind spot."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-9", touches=["saffron/x.py"])

    _candidates, refusals = build_queue(
        directory,
        None,
        ledger,
        markers=[("saffron/ghost.py", "TE-404")],
    )

    dangling = next(r.reason for r in refusals if r.path.name == "ghost.py")
    assert "did not parse" not in dangling


def test_a_marker_naming_a_retired_spec_is_not_dangling(tmp_path, ledger):
    """`specs/done/` declares an id exactly the way a live spec file does
    (`_retired_ids`) — a marker naming a retired spec is a real reference,
    not a dangling one."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-9", touches=["saffron/x.py"])
    done = directory / "done"
    done.mkdir()
    _write_spec(done, "TE-8.md", id="TE-8")

    candidates, refusals = build_queue(
        directory,
        None,
        ledger,
        markers=[("saffron/x.py", "TE-8")],
    )

    assert [c.spec.id for c in candidates] == ["TE-9"]
    assert refusals == []


# --------------------------------------------- refusal: touches vs protected


def test_a_touches_entry_matching_a_protected_literal_path_is_refused(tmp_path, ledger):
    """`SA-0021`'s own shape: `DESIGN.md` declared in `touches` is exactly
    the collision that cost a cell, a turn and $0.82 before it reached
    `validate_plan` (docs/BACKLOG.md item 28)."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["DESIGN.md", "saffron/x.py"])

    candidates, refusals = build_queue(
        directory,
        None,
        ledger,
        protected=["DESIGN.md", "CONTEXT.md", ".saffron/**", "uv.lock"],
    )

    assert candidates == []
    assert len(refusals) == 1
    reason = refusals[0].reason
    assert "DESIGN.md" in reason
    assert "protected" in reason
    assert "forbidden" in reason


def test_protected_matching_uses_the_glob_matcher_not_a_string_compare(
    tmp_path, ledger
):
    """Same mistake `SA-0016`'s fifth refusal already records
    (`_path_tokens`'s own docstring): a nested path string-compares to no
    match against a `**` pattern that plainly covers it. `docs/nested/x.md`
    never appears verbatim in `touches` — only `docs/**` does."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["docs/**"])

    candidates, refusals = build_queue(
        directory, None, ledger, protected=["docs/nested/x.md"]
    )

    assert candidates == []
    assert "docs/nested/x.md" in refusals[0].reason


def test_a_glob_protected_entry_is_not_decided_here(tmp_path, ledger):
    """`.saffron/**` is this repo's own fourth `protected` entry, and the one
    that is not literal (docs/BACKLOG.md item 28, `SA-0023`'s own criteria).
    Deciding whether it can ever intersect a `touches` glob needs the file
    list at `base_sha`, which the scan does not have — `protected_touch_
    refusal`'s own `ponytail:` — so this is left to `validate_plan`'s
    backstop once a plan reaches a concrete file, not refused here."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=[".saffron/gates/lint"])

    candidates, refusals = build_queue(
        directory, None, ledger, protected=[".saffron/**"]
    )

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


def test_the_glob_guard_is_what_stops_a_false_refusal(tmp_path, ledger):
    """The ceiling test above holds with or without the guard — `matches`
    says False either way — so it does not witness the guard. This pair
    does: without it, `matches("docs/*", "docs/**")` is True and a spec whose
    `touches` cannot be shown to reach anything protected is refused for the
    night. §4.2.1: a false refusal costs a whole spec overnight with nothing
    to notice until morning."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["docs/**"])

    candidates, refusals = build_queue(directory, None, ledger, protected=["docs/*"])

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


def test_a_path_the_specs_own_forbidden_bars_is_not_a_collision(tmp_path, ledger):
    """`validate_plan` rejects on `forbidden` before it ever consults
    `protected`, so a spec that has denied itself the path cannot reach it
    whatever `touches` covers. Refusing here would cost a night for a
    collision that cannot happen — which is why `_unmatched_criterion_path`
    exempts the same list twenty lines above."""
    directory = _spec_dir(tmp_path)
    # `docs/**` rather than a leading-`*` pattern: `_write_spec` emits touches
    # unquoted and YAML reads a leading `*` as an alias.
    _write_spec(
        directory, "a.md", id="TE-1", touches=["docs/**"], forbidden=["docs/DESIGN.md"]
    )
    _write_spec(directory, "b.md", id="TE-2", touches=["docs/**"])

    candidates, refusals = build_queue(
        directory, None, ledger, protected=["docs/DESIGN.md"]
    )

    assert [c.spec.id for c in candidates] == ["TE-1"]
    reason = next(r.reason for r in refusals if r.path.name == "b.md")
    # And the one that is refused is told what actually matched: a pattern
    # covering the path, not `touches` naming it.
    assert "covers 'docs/DESIGN.md'" in reason
    assert "touches names" not in reason


def test_no_protected_declared_changes_nothing(tmp_path, ledger):
    """`protected`'s default is `()`, so every caller before `SA-0023`
    (every existing test in this file included) gets exactly the queue it
    already had."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["DESIGN.md"])

    candidates, refusals = build_queue(directory, None, ledger)

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


# ------------------------------------------------------- refusal: depends_on


def test_a_depends_on_refuses_when_the_scan_has_no_ledger_to_look_it_up_in(
    tmp_path, ledger
):
    """Was `test_a_non_empty_depends_on_refuses`, which named the old rule:
    any `depends_on` refused, unlooked-up. It still refuses here, but for a
    read reason — with no `repo_id` there are no rows, so nothing says the
    parent merged."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])

    candidates, refusals = build_queue(directory, None, ledger)

    assert candidates == []
    assert len(refusals) == 1
    assert "TE-0" in refusals[0].reason
    assert "no task" in refusals[0].reason


def test_a_dependency_that_merged_is_a_candidate(tmp_path, ledger):
    """§4.2's rule, narrowed to what needs no stacking: a merged parent is in
    the default branch the child is cut from."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-0",
        spec_sha=_sha(directory / "b.md"),
        state="MERGED",
    )

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert "TE-1" in [c.spec.id for c in candidates]
    assert [r for r in refusals if "TE-1" in str(r.path)] == []


def test_a_merged_parent_satisfies_whatever_sha_it_ran_at(tmp_path, ledger):
    """Merging is permanent and sha-independent — the parent's code is in the
    default branch however its spec text has moved since."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)
    _task_at(ledger, repo_id, spec_id="TE-0", spec_sha="0" * 64, state="MERGED")

    candidates, _ = build_queue(directory, repo_id, ledger)

    assert "TE-1" in [c.spec.id for c in candidates]


@pytest.mark.parametrize("state", ["READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN"])
def test_a_parent_waiting_to_merge_is_admitted_for_stacking(tmp_path, ledger, state):
    """Renamed with the widening: the old name asserted the opposite of what
    this now proves, and `census`'s remove-plus-add is a cheaper price than a
    name that lies to the next reader — a rename landed on the default branch
    is in the next cell's baseline before it ever runs. §4.2's own rule admits
    these, and now the code does too. A dependent
    branches off the parent's branch instead of `base_sha`
    (`cli._resolve_stacked_on`), so the gate that used to refuse them with
    "stacking is SA-0022" — a sentence describing machinery that did not
    exist yet — has nothing left to refuse."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger, repo_id, spec_id="TE-0", spec_sha=_sha(directory / "b.md"), state=state
    )

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert "TE-1" in [c.spec.id for c in candidates]
    assert [r for r in refusals if r.path.name == "a.md"] == []
    # The deleted sentence, not just the state list: a forward reference to
    # machinery that now exists must not survive anywhere in the refusal text.
    assert not any("SA-0022" in r.reason for r in refusals)


@pytest.mark.parametrize("state", ["REJECTED", "EXHAUSTED"])
def test_a_parent_that_will_not_merge_reads_differently_from_one_unrun(
    tmp_path, ledger, state
):
    """A parent that will not merge and a parent not yet run are different
    facts about the night."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger, repo_id, spec_id="TE-0", spec_sha=_sha(directory / "b.md"), state=state
    )

    _, refusals = build_queue(directory, repo_id, ledger)
    reason = next(r.reason for r in refusals if r.path.name == "a.md")

    assert state in reason
    # Not "no task": that is the unrun message, and criterion 3 asks for a
    # reason distinct from it. Asserted on the distinctive phrase rather than
    # on "not run", which the dead message itself ends with ("not yet run").
    assert "no task" not in reason


def test_a_parent_with_no_task_names_that_rather_than_a_state(tmp_path, ledger):
    """No reason claims a check it did not perform."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)

    _, refusals = build_queue(directory, repo_id, ledger)
    reason = next(r.reason for r in refusals if r.path.name == "a.md")

    assert "TE-0" in reason
    assert "no task" in reason


def test_a_dead_state_under_a_superseded_sha_does_not_speak_for_the_parent(
    tmp_path, ledger
):
    """Measured on this spec's own first attempt (2026-08-30): `any(state in
    DEAD)` across every sha reports a parent dead when its spec has been
    edited since, and the disposition of the text on disk is simply unknown.
    """
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)
    # The parent ran, was rejected, and its spec text has moved since.
    _task_at(ledger, repo_id, spec_id="TE-0", spec_sha="f" * 64, state="REJECTED")

    _, refusals = build_queue(directory, repo_id, ledger)
    reason = next(r.reason for r in refusals if r.path.name == "a.md")

    assert "REJECTED" not in reason
    assert "no task" in reason


def test_this_repos_own_specs_admit_a_merged_parent_and_name_a_retired_one(
    tmp_path, ledger
):
    """Criterion 5's live witness, re-anchored a third time — 2026-08-31,
    when retirement began satisfying a dependency. The shape survives each
    time, so it is the shape this pins: one parent merged and on disk, one
    parent retired off it, and both admitting their children.

    `SA-0017`'s parent `SA-0016` is top-level and merged — the first thing
    this gate ever scheduled. `SA-0022` and `SA-0023` depend on `SA-0020`,
    which is in `specs/done/` and has no task at all, because it was
    implemented by hand: the case the ledger alone can never answer. A parent
    that is genuinely absent still refuses, which the synthetic tests hold.
    """
    real_specs = Path(__file__).resolve().parent.parent / ".saffron" / "specs"
    directory = tmp_path / "specs"
    shutil.copytree(real_specs, directory)
    repo_id = _repo(ledger)

    under_test = {"SA-0017", "SA-0022", "SA-0023"}
    for path in sorted(directory.glob("*.md")):
        spec, spec_sha = load_spec(path)
        if spec.id in under_test:
            continue
        _task_at(ledger, repo_id, spec_id=spec.id, spec_sha=spec_sha, state="MERGED")

    candidates, refusals = build_queue(directory, repo_id, ledger)

    scheduled = [c.spec.id for c in candidates]
    assert "SA-0017" in scheduled
    for dependent in ("SA-0022", "SA-0023"):
        assert dependent in scheduled
    # Not merely unrefused-for-some-other-reason: no line anywhere names the
    # retired parent, which is the whole of what changed.
    assert [r for r in refusals if "SA-0020" in r.reason] == []


def test_a_waiting_parent_is_admitted_where_a_dead_one_is_still_refused(
    tmp_path, ledger
):
    """Renamed with the widening, for the reason above. A waiting parent used
    to be refused with its own reason, distinct from a dead parent's; now it
    is not refused at all, and only the dead parent still is — proving the
    widening landed on exactly the three waiting states and left
    `DEPENDENCY_DEAD_STATES` alone.
    """
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-8"])
    _write_spec(directory, "b.md", id="TE-2", touches=["b.py"], depends_on=["TE-9"])
    _write_spec(directory, "p8.md", id="TE-8", touches=["p8.py"])
    _write_spec(directory, "p9.md", id="TE-9", touches=["p9.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-8",
        spec_sha=_sha(directory / "p8.md"),
        state="READY_FOR_REVIEW",
    )
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-9",
        spec_sha=_sha(directory / "p9.md"),
        state="REJECTED",
    )

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert "TE-1" in [c.spec.id for c in candidates]
    assert [r for r in refusals if r.path.name == "a.md"] == []
    dead = next(r.reason for r in refusals if r.path.name == "b.md")
    assert "will not merge as it stands" in dead


@pytest.mark.parametrize("state", ["CHANGES_REQUESTED", "IMPLEMENTING"])
def test_a_parent_in_any_other_state_is_named_by_that_state(tmp_path, ledger, state):
    """The fallthrough handles most of the state space — every in-flight state
    and five terminal ones — and nothing exercised it: replacing it with a
    raise left the whole suite green."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    _write_spec(directory, "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger, repo_id, spec_id="TE-0", spec_sha=_sha(directory / "b.md"), state=state
    )

    _, refusals = build_queue(directory, repo_id, ledger)
    reason = next(r.reason for r in refusals if r.path.name == "a.md")

    assert state in reason
    # It names what it read and nothing it did not: no bucket's wording.
    assert "waits for the parent" not in reason
    assert "will not merge as it stands" not in reason


def test_a_parent_absent_from_the_scan_is_not_called_unrun(tmp_path, ledger):
    """A parent that is nowhere — not on disk, not in `done/`, no task — has
    no current `spec_sha` to have no task at, so saying it had not run names a
    check this scan cannot perform, which is the defect this gate removed.
    Retirement is the other case and is now admitted, not refused."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-GONE"])
    repo_id = _repo(ledger)

    _, refusals = build_queue(directory, repo_id, ledger)
    reason = next(r.reason for r in refusals if r.path.name == "a.md")

    assert "TE-GONE" in reason
    assert "not among the specs in this directory" in reason
    assert "spec_sha" not in reason
    assert "has not run" not in reason


def test_a_parent_retired_as_shipped_satisfies_the_dependency(tmp_path, ledger):
    """`specs/done/` is the operator asserting the parent's work is in `main`
    — the same fact `MERGED` establishes, and the only one this gate needs,
    because the child is cut from the default branch. Work done by hand
    writes no task at all, so without this the ledger can never say it."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    (directory / "done").mkdir()
    _write_spec(directory / "done", "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert "TE-1" in [c.spec.id for c in candidates]
    assert [r for r in refusals if r.path.name == "a.md"] == []


def test_a_retired_parent_is_never_itself_offered_as_a_candidate(tmp_path, ledger):
    """Reading `done/` for ids must not turn it into a second scan directory:
    the whole point of the move is that the spec stops being offered."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    (directory / "done").mkdir()
    _write_spec(directory / "done", "b.md", id="TE-0", touches=["b.py"])
    repo_id = _repo(ledger)

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert "TE-0" not in [c.spec.id for c in candidates]
    assert [r for r in refusals if r.path.name == "b.md"] == []


def test_an_unreadable_retired_spec_is_refused_by_path_not_only_by_silence(
    tmp_path, ledger
):
    """A file in `done/` that stops parsing declares no id, so it credits
    nothing — and without its own line the only trace is a child refused for
    a parent the operator can see sitting in `done/`. Discarding those
    failures made the refusal contradict the filesystem."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    (directory / "done").mkdir()
    (directory / "done" / "b.md").write_text("no frontmatter here\n")
    repo_id = _repo(ledger)

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert "TE-1" not in [c.spec.id for c in candidates]
    retired = next(r for r in refusals if r.path.name == "b.md")
    assert retired.path.parent.name == "done"
    assert "credits no dependency" in retired.reason
    assert "frontmatter" in retired.reason
    # And the child's own line stops asserting a `done/` it could only partly
    # read: it names what was unreadable there.
    child = next(r.reason for r in refusals if r.path.name == "a.md")
    assert "1 file in done/ could not be read as a spec" in child


def test_a_retired_parent_admits_its_child_with_no_ledger_row_at_all(tmp_path, ledger):
    """`repo_id is None` is a repo the ledger has never seen — which is
    exactly the repo whose parent shipped by hand, so retirement has to be
    read there too. The docstring that said a `depends_on` is refused
    outright in this case described the gate before `SA-0020`."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    (directory / "done").mkdir()
    _write_spec(directory / "done", "b.md", id="TE-0", touches=["b.py"])

    candidates, refusals = build_queue(directory, None, ledger)

    assert [c.spec.id for c in candidates] == ["TE-1"]
    assert refusals == []


def test_a_parent_that_is_neither_retired_nor_merged_names_both_checks(
    tmp_path, ledger
):
    """The refusal names every check it performed and no check it did not —
    an operator who reads it must know that `done/` was consulted too."""
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-GONE"])
    (directory / "done").mkdir()
    repo_id = _repo(ledger)

    _, refusals = build_queue(directory, repo_id, ledger)
    reason = next(r.reason for r in refusals if r.path.name == "a.md")

    assert "TE-GONE" in reason
    assert "done/" in reason
    assert "no task in the ledger says it merged" in reason


def test_every_unmet_dependency_is_counted_not_just_the_first(tmp_path, ledger):
    """One line in a morning queue: an operator who clears the first and meets
    the second tomorrow has lost a night the line could have saved."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-8", "TE-9"]
    )
    repo_id = _repo(ledger)

    _, refusals = build_queue(directory, repo_id, ledger)
    reason = next(r.reason for r in refusals if r.path.name == "a.md")

    assert "TE-8" in reason
    assert "+1 more unmet" in reason


# ---------------------------------------------------------------------- smoke


def test_saffron_queue_smoke_reproduces_this_repos_measured_queue(tmp_path, ledger):
    """Re-measured 2026-08-31, after twelve shipped specs moved to
    `specs/done/` (`intake.discover_specs` globs `*.md`, not `**/*.md`):
    `SA-0009` and `SA-0019` queued, everything else filtered out with a
    `READY_FOR_REVIEW` task at the same `spec_sha`, and nothing refused. The
    two ids are not arbitrary — they are the only top-level specs with an
    empty `depends_on`, and every other one would be refused by the dependency
    gate rather than queued, which would test the refusal instead of the
    filter. Re-anchored 2026-08-31, when `SA-0009` was retired to `specs/done/`
    as shipped and `SA-0024` took its place as the second such spec. A smoke
    check, not proof the refusals work on their own — those are the fixtures
    above."""
    real_specs = Path(__file__).resolve().parent.parent / ".saffron" / "specs"
    directory = tmp_path / "specs"
    shutil.copytree(real_specs, directory)
    repo_id = _repo(ledger)

    still_open = {"SA-0019", "SA-0024"}
    for path in sorted(directory.glob("*.md")):
        spec, spec_sha = load_spec(path)
        if spec.id in still_open:
            continue
        _task_at(
            ledger,
            repo_id,
            spec_id=spec.id,
            spec_sha=spec_sha,
            state="READY_FOR_REVIEW",
        )

    candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="joel/saffron", gh=_fake_gh([])
    )

    assert [c.spec.id for c in candidates] == ["SA-0019", "SA-0024"]
    assert refusals == []

    # Again with no ledger, so nothing is filtered before `_refuse` runs. The
    # pass above reaches the refusals for two of nine specs — the other seven
    # are dropped as done first — so on its own it stays green while
    # every one of them is falsely refused, which is how the criterion-path
    # check shipped refusing SA-0011 and SA-0016 (this spec) on their own
    # criteria. `depends_on` refusals are expected here and are the shape the
    # Notes describe; a criterion-path refusal on a real spec is not.
    _, unfiltered = build_queue(
        directory, None, ledger, repo_slug="joel/saffron", gh=_fake_gh([])
    )

    assert [r for r in unfiltered if "acceptance criteria name" in r.reason] == []
    assert all("depends_on" in r.reason for r in unfiltered)
