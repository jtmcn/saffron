import json
import shutil
import subprocess
from pathlib import Path

import pytest

from saffron.cell import runtime
from saffron.intake import (
    DisclosedMutantError,
    SpecError,
    discover_specs,
    load_spec,
)
from saffron.ledger import Ledger
from saffron.scheduler import (
    DONE_STATES,
    REQUEUE_STATES,
    _unmatched_criterion_path,
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


REAL_SPECS = Path(__file__).resolve().parent.parent / ".saffron" / "specs"


def _real_corpus(tmp_path, *, promote=frozenset()):
    """This repo's own spec files, arranged as a scannable directory.

    Every spec Saffron has run is retired to `specs/done/`, so the live
    top-level directory is empty between batches and a test anchored to it
    measures nothing. The real files are still the corpus worth scanning —
    they carry real `depends_on` chains and real acceptance criteria, which
    is what the checks below are for — so a test names the ids it needs at
    top level and this puts them there, leaving the rest retired.

    `README.md` is dropped: `discover_specs` globs `*.md` and reports it as a
    failure, which is correct and is not what any caller here is measuring.
    """
    specs = tmp_path / "specs"
    specs.mkdir()
    done = specs / "done"
    shutil.copytree(REAL_SPECS / "done", done)
    (done / "README.md").unlink()
    for path in sorted(done.glob("*.md")):
        # A retired spec the loader refuses still has to be sorted, and the
        # two refusals differ exactly as they do in `_retired_ids`: one
        # refused on policy carries its parsed spec and so declares an id,
        # while one refused on shape declares none and cannot be named in
        # `promote` at all. `SA-0063` is the live case (item 82).
        try:
            spec = load_spec(path)[0]
        except DisclosedMutantError as exc:
            spec = exc.spec
        except SpecError:
            continue
        if spec.id in promote:
            shutil.move(str(path), specs / path.name)
    return specs


def _every_retired_spec_at_top_level(tmp_path):
    """`_real_corpus` with every retired spec promoted.

    `promote=` names ids and this caller wants all of them: a spec left in
    `done/` is never scanned. Retired specs only — `_real_corpus` copies
    `done/`, so the specs still live at the top of `.saffron/specs` are not
    here. `_every_live_spec_flattened` is the one that sees those.
    """
    directory = _real_corpus(tmp_path)
    for path in sorted((directory / "done").glob("*.md")):
        shutil.move(str(path), directory / path.name)
    return directory


def _every_live_spec_flattened(tmp_path):
    """Every spec file this repo has, retired or not, in one scannable
    directory.

    `_real_corpus` copies `done/` alone, which silently leaves out whichever
    specs are at the top of `.saffron/specs` right now — the most recent, and
    the likeliest to carry a defect nobody has met yet. A check claiming to
    hold over *every* spec cannot be built on a corpus that omits them.
    `README.md` is dropped for `_real_corpus`'s own reason: `discover_specs`
    globs `*.md` and reports it as a failure, correctly and irrelevantly.
    """
    directory = tmp_path / "specs"
    directory.mkdir()
    for path in list(REAL_SPECS.glob("*.md")) + list(
        (REAL_SPECS / "done").glob("*.md")
    ):
        if path.name != "README.md":
            shutil.copy(path, directory / path.name)
    return directory


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
    every spec in this repository touched the backlog file then (`SA-0026`)."""
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
    K=1, the same one `task._resolve_stacked_on` stacks on. Another task's
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


def test_a_grandparents_open_pull_request_does_not_refuse_its_grandchild(
    tmp_path, ledger
):
    """Backlog item 59: a stack is transitive, and the exemption above only
    ever walked one hop. `TE-2` depends on `TE-1`, which depends on `TE-0` —
    `TE-2` is cut from `TE-1`'s branch head, which is itself cut from `TE-0`'s,
    so `TE-0`'s changes are already in `TE-2`'s own tree by the time it runs.
    An open pull request from `TE-0` overlapping `TE-2`'s `touches` is nothing
    to conflict with, at two hops just as much as one."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory, "a.md", id="TE-2", touches=["shared.py"], depends_on=["TE-1"]
    )
    _write_spec(directory, "b.md", id="TE-1", touches=["mid.py"], depends_on=["TE-0"])
    _write_spec(directory, "c.md", id="TE-0", touches=["base.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-1",
        spec_sha=_sha(directory / "b.md"),
        state="READY_FOR_REVIEW",
    )
    gh = _fake_gh(
        [{"headRefName": "saffron/TE-0", "url": "g", "files": [{"path": "shared.py"}]}]
    )

    _candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="o/r", gh=gh
    )

    assert [r for r in refusals if r.path.name == "a.md"] == []


def test_an_unrelated_open_pull_request_still_refuses_on_overlap(tmp_path, ledger):
    """The gate `SA-0016` built and the ancestor walk must not widen past: two
    tasks with no dependency relationship at all, touching one file, are still
    refused, and the reason still names the pull request and the file.

    Pinned at both ends: `build_queue` end to end, and the walk itself —
    `_ancestor_branches` of a spec with no `depends_on` is `frozenset()`,
    which is the whole reason nothing here can be exempted. Imported inside
    the test, not at module level, so a source revert that removes the
    function fails only this test rather than the whole file's collection."""
    from saffron.scheduler import _ancestor_branches

    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"])
    gh = _fake_gh(
        [
            {
                "headRefName": "saffron/OTHER",
                "url": "https://example/pull/5",
                "files": [{"path": "a.py"}],
            }
        ]
    )

    candidates, refusals = build_queue(directory, None, ledger, repo_slug="o/r", gh=gh)

    assert candidates == []
    assert len(refusals) == 1
    assert "touches overlaps" in refusals[0].reason
    assert "a.py" in refusals[0].reason
    assert "https://example/pull/5" in refusals[0].reason
    assert _ancestor_branches("TE-1", {}) == frozenset()


def test_a_second_dependency_is_not_an_ancestor_and_still_refuses(tmp_path, ledger):
    """§4.2 fixes K=1: only `depends_on[0]` is ever a stacking candidate. A
    second entry is a dependency the candidate is not cut from, so its
    changes are not in the candidate's tree and an overlap with its pull
    request is a real conflict — the ancestor walk must not exempt it just
    because it happens to sit in the same `depends_on` list.

    `TE-0` (the first, exempted entry) is itself given a parent, `TE-A`, so
    this also exercises a real two-hop walk rather than one that happens to
    stop after a single link — a one-hop reading of K=1 would refuse `TE-A`'s
    own overlap too, which the assertions below rule out before ever reaching
    `TE-9`'s. `TE-A`'s pull request is listed first, so a walk that wrongly
    stopped at `TE-0` would return on it before ever inspecting `TE-9`'s."""
    from saffron.scheduler import _ancestor_branches

    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        touches=["shared.py", "sibling.py"],
        depends_on=["TE-0", "TE-9"],
    )
    _write_spec(directory, "b.md", id="TE-0", touches=["mid.py"], depends_on=["TE-A"])
    _write_spec(directory, "d.md", id="TE-A", touches=["base.py"])
    _write_spec(directory, "c.md", id="TE-9", touches=["other.py"])
    repo_id = _repo(ledger)
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-0",
        spec_sha=_sha(directory / "b.md"),
        state="READY_FOR_REVIEW",
    )
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-9",
        spec_sha=_sha(directory / "c.md"),
        state="READY_FOR_REVIEW",
    )
    gh = _fake_gh(
        [
            # The grandparent's own pull request, listed first: exempted by
            # the two-hop walk, so this must not be what the refusal names.
            {
                "headRefName": "saffron/TE-A",
                "url": "ga",
                "files": [{"path": "shared.py"}],
            },
            # The second `depends_on` entry's: not an ancestor, still refused.
            {
                "headRefName": "saffron/TE-9",
                "url": "u9",
                "files": [{"path": "sibling.py"}],
            },
        ]
    )

    _candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="o/r", gh=gh
    )

    mine = next(r for r in refusals if r.path.name == "a.md")
    assert "touches overlaps" in mine.reason
    assert "sibling.py" in mine.reason and "u9" in mine.reason
    assert "shared.py" not in mine.reason and "ga" not in mine.reason
    assert _ancestor_branches("TE-1", {"TE-1": "TE-0", "TE-0": "TE-A"}) == {
        "saffron/TE-0",
        "saffron/TE-A",
    }


def test_a_dependency_cycle_does_not_hang_the_ancestor_walk(tmp_path, ledger):
    """Nothing validates `depends_on` for cycles at parse time, so a
    hand-written pair that depend on each other are reachable input, not a
    hypothetical — and the ancestor walk is computed for every candidate on
    every scan, whether or not any pull request ever overlaps. A `visited`
    set must stop it; unattended, a hang here costs the whole night rather
    than the one task the old one-hop refusal cost.

    The cycle sits one hop *above* the candidate (`TE-8` and `TE-9` depend
    on each other) rather than including the candidate itself, so the walk
    must pass through it and come out the other side with both branches
    collected — a one-hop reading of K=1 would never reach `TE-9` at all,
    and would refuse `TE-7` on `TE-9`'s pull request instead of exempting
    it, which is what the assertions below check for."""
    from saffron.scheduler import _ancestor_branches

    directory = _spec_dir(tmp_path)
    _write_spec(
        directory, "a.md", id="TE-7", touches=["shared.py"], depends_on=["TE-8"]
    )
    _write_spec(directory, "b.md", id="TE-8", touches=["p1.py"], depends_on=["TE-9"])
    _write_spec(directory, "c.md", id="TE-9", touches=["p2.py"], depends_on=["TE-8"])
    repo_id = _repo(ledger)
    _task_at(
        ledger,
        repo_id,
        spec_id="TE-8",
        spec_sha=_sha(directory / "b.md"),
        state="READY_FOR_REVIEW",
    )
    gh = _fake_gh(
        [
            {
                "headRefName": "saffron/TE-9",
                "url": "p2",
                "files": [{"path": "shared.py"}],
            }
        ]
    )

    _candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="o/r", gh=gh
    )

    # The point under test is reaching this line at all — a walk that hangs
    # on the cycle never gets here — and that the cycle is still correctly
    # read as an ancestor rather than a stranger's overlap.
    assert [
        r for r in refusals if r.path.name == "a.md" and "touches overlaps" in r.reason
    ] == []
    parent_of = {"TE-7": "TE-8", "TE-8": "TE-9", "TE-9": "TE-8"}
    assert _ancestor_branches("TE-7", parent_of) == {"saffron/TE-8", "saffron/TE-9"}


def test_an_unscanned_parent_ends_the_walk_without_raising(tmp_path, ledger):
    """A parent the scan cannot see ends the walk quietly rather than
    raising. `TE-0` (a real, scanned parent) itself depends on `TE-GONE`,
    which is retired to `specs/done/` — the operator's own assertion that its
    work already shipped, and not among the specs `parent_of` is built from.
    The walk still exempts `TE-0`'s immediate parent along the way, but must
    not raise trying to look `TE-GONE` up to go further."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory, "a.md", id="TE-1", touches=["shared.py"], depends_on=["TE-0"]
    )
    _write_spec(
        directory, "b.md", id="TE-0", touches=["mid.py"], depends_on=["TE-GONE"]
    )
    done = directory / "done"
    done.mkdir()
    _write_spec(done, "c.md", id="TE-GONE", touches=["base.py"])
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
            {
                "headRefName": "saffron/TE-GONE",
                "url": "g",
                "files": [{"path": "shared.py"}],
            }
        ]
    )

    _candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="o/r", gh=gh
    )

    assert [
        r for r in refusals if r.path.name == "a.md" and "touches overlaps" in r.reason
    ] == []


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
    `SimpleNamespace` standing in for one (backlog item 21's own
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

    reason = retirement_refusal(spec, [("docs/README.md", "TE-9")])

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
    `validate_plan` (backlog item 28)."""
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
    that is not literal (backlog item 28, `SA-0023`'s own criteria).
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
    exempts the same list."""
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


def test_a_spec_that_forbids_the_very_path_it_touches_is_still_refused(
    tmp_path, ledger
):
    """The exemption is for a broad `touches` narrowed by a specific
    `forbidden`. Naming the same path in both is a spec contradicting itself,
    and that is worth a line in the morning queue rather than a silent
    admission — the one route by which a protected path could otherwise reach
    a cell's `touches` unremarked."""
    directory = _spec_dir(tmp_path)
    _write_spec(
        directory,
        "a.md",
        id="TE-1",
        touches=["docs/DESIGN.md"],
        forbidden=["docs/DESIGN.md"],
    )

    candidates, refusals = build_queue(
        directory, None, ledger, protected=["docs/DESIGN.md"]
    )

    assert candidates == []
    assert "touches names 'docs/DESIGN.md'" in refusals[0].reason


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
    (`task._resolve_stacked_on`), so the gate that used to refuse them with
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
    """Criterion 5's live witness, re-anchored a fourth time — 2026-09-04,
    when the last active spec was retired and the top-level directory went
    empty. The shape survives each time, so it is the shape this pins: one
    parent merged and on disk, one parent retired off it, and both admitting
    their children.

    The four ids are promoted out of `specs/done/` rather than read where they
    happen to lie, which is the only thing that changed. Every previous
    anchoring picked whichever real specs were mid-flight at the time; there
    are none now, and waiting for the next batch would leave this dark for as
    long as the queue is empty. The files are the same real files, and the
    arrangement is the one that was measured.

    `SA-0017`'s parent `SA-0016` is promoted alongside it and carries a
    `MERGED` task — the first thing this gate ever scheduled. `SA-0022` and
    `SA-0023` depend on `SA-0020`, which stays in `specs/done/` and has no
    task at all, because it was implemented by hand: the case the ledger alone
    can never answer. A parent that is genuinely absent still refuses, which
    the synthetic tests hold.
    """
    directory = _real_corpus(
        tmp_path, promote={"SA-0016", "SA-0017", "SA-0022", "SA-0023"}
    )
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


def test_a_retired_parent_refused_on_policy_still_credits_its_child(tmp_path, ledger):
    """A spec refused for *disclosing its own mutant* read cleanly — it has an
    id, and `done/` says its work is in `main`.

    The two refusals are not the same fact. A file that does not parse declares
    no id, so it can credit nothing and the refusal has to stand. A spec item
    82 refuses parsed fine and is being kept out of the *queue*; withdrawing
    its `done/` credit as well would strand every child it already shipped for.
    `SA-0063` is the live case — merged, pending retirement, and the one spec
    in this repo that rule refuses.

    Without the distinction, adding any intake rule silently revokes the
    retirement credit of every spec already in `done/` that the new rule
    happens to refuse, and `done/` exists precisely for the dependency the
    ledger cannot state.
    """
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])
    (directory / "done").mkdir()
    (directory / "done" / "b.md").write_text(
        "---\nid: TE-0\ntitle: t\ntype: feature\npriority: 3\n"
        "depends_on: []\ntouches: [b.py]\nforbidden: []\n"
        "budget_usd: 5\nmax_attempts: 2\nrisk: standard\n"
        "acceptance:\n"
        "  - claim: the module declares CEILING = 60\n"
        "    witness: tests/test_b.py::test_declared\n"
        "    mutant:\n"
        "      file: b.py\n"
        "      find: 'CEILING = 60'\n"
        "      replace: 'CEILING = 0'\n"
        "---\n\nbody\n"
    )
    repo_id = _repo(ledger)

    candidates, refusals = build_queue(directory, repo_id, ledger)

    assert "TE-1" in [c.spec.id for c in candidates]
    assert [r for r in refusals if r.path.name == "a.md"] == []
    # And it is still not offered as a candidate itself: crediting the
    # dependency is not the same as admitting the spec.
    assert "TE-0" not in [c.spec.id for c in candidates]


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


def test_a_parent_whose_pushed_commit_reached_the_default_branch_satisfies_its_child(
    tmp_path,
):
    """`SA-0131`: a parent whose task never wrote `MERGED` still satisfies
    its child once `pushed_landed` says its recorded push reached the
    default branch. True whatever state that row carries, and whatever the
    ledger's other rows for the same parent say."""
    from saffron.scheduler import DEPENDENCY_WAITING_STATES

    def _recording(accept):
        seen = []

        def landed(sha):
            seen.append(sha)
            return sha == accept

        return seen, landed

    sha_a, sha_b = "1" * 40, "2" * 40
    # Parent A gets two rows below. B's push is rejected, C records none.
    parents = ["TE-1", "TE-3", "TE-5"]
    children = ["TE-2", "TE-4", "TE-6"]

    for state in sorted(DONE_STATES | REQUEUE_STATES):
        directory = tmp_path / f"specs-{state}"
        directory.mkdir()
        for parent, child in zip(parents, children, strict=True):
            _write_spec(directory, f"{parent}.md", id=parent, touches=[f"{parent}.py"])
            _write_spec(
                directory,
                f"{child}.md",
                id=child,
                touches=[f"{child}.py"],
                depends_on=[parent],
            )
        ledger = Ledger(tmp_path / f"ledger-{state}.db")
        repo_id = _repo(ledger)

        # A's older row carries the accepted push, at a sha this scan no
        # longer has on disk. Its newer row records no push at all.
        old_row = _task_at(
            ledger, repo_id, spec_id="TE-1", spec_sha="stale-sha-a", state="REJECTED"
        )
        ledger.record_push(old_row, sha_a)
        # B's older row records no push, so a scan reading only each spec's
        # oldest row never asks about B's push.
        _task_at(
            ledger, repo_id, spec_id="TE-3", spec_sha="stale-sha-b", state="REJECTED"
        )
        for parent in parents:
            row = _task_at(
                ledger,
                repo_id,
                spec_id=parent,
                spec_sha=_sha(directory / f"{parent}.md"),
                state=state,
            )
            if parent == "TE-3":  # B's own row: a push the callable rejects.
                ledger.record_push(row, sha_b)

        asked, pushed_landed = _recording(sha_a)
        candidates, refusals = build_queue(
            directory, repo_id, ledger, pushed_landed=pushed_landed
        )

        assert "TE-2" in [c.spec.id for c in candidates]
        assert not any(r.path.name == "TE-2.md" for r in refusals)
        # Only rows carrying a `pushed_sha` are ever asked, and none at all
        # once `MERGED` already credits every parent on its own.
        expected_asked = set() if state == "MERGED" else {sha_a, sha_b}
        assert set(asked) == expected_asked

        if state not in DEPENDENCY_WAITING_STATES and state != "MERGED":
            assert any(r.path.name == "TE-4.md" for r in refusals)
            assert any(r.path.name == "TE-6.md" for r in refusals)

        ledger.close()

    # A callable that cannot answer must not be read as "no": `build_queue`
    # propagates it rather than catching it and reporting a false refusal.
    from saffron.repos.mirror import GitError

    directory = tmp_path / "specs-raises"
    directory.mkdir()
    _write_spec(directory, "TE-1.md", id="TE-1", touches=["a.py"])
    _write_spec(directory, "TE-2.md", id="TE-2", touches=["b.py"], depends_on=["TE-1"])
    ledger = Ledger(tmp_path / "ledger-raises.db")
    repo_id = _repo(ledger)
    row = _task_at(
        ledger,
        repo_id,
        spec_id="TE-1",
        spec_sha=_sha(directory / "TE-1.md"),
        state="EXHAUSTED",
    )
    ledger.record_push(row, sha_a)

    def raising(_sha):
        raise GitError("mirror unreadable")

    with pytest.raises(GitError):
        build_queue(directory, repo_id, ledger, pushed_landed=raising)
    ledger.close()


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
    """Re-measured 2026-09-25, a hundredth time: `SA-0177` queued for
    backlog item b-792ab2, split from `SA-0167` on size. It builds the
    ledger's `stack_finishes` table and its two methods. It declares
    `depends_on: [SA-0174]`, so it is refused. `SA-0167` now declares
    `depends_on: [SA-0177]`. The candidates are unmoved.

    Re-measured 2026-09-25, a ninety-ninth time: `SA-0176` queued for
    backlog item b-792ab2, split from `SA-0160` on size. It builds core's
    spec writer prompt, its extraction turn prompt and their fill. It
    declares `depends_on: [SA-0150]`, so it is refused. `SA-0160` now
    declares `depends_on: [SA-0176]`. The candidates are unmoved.

    Re-measured 2026-09-25, a ninety-eighth time: `SA-0175` queued for
    backlog item b-792ab2, split from `SA-0156` when ADR 7 made the spec
    review's prompt core's. It builds the session, its extraction turn and
    core's prompt. It declares `depends_on: [SA-0169]`, so it is refused.
    `SA-0156` now declares `depends_on: [SA-0175]`. The candidates are
    unmoved.

    Re-measured 2026-09-25, a ninety-seventh time: the spec loop's run 16
    retired `SA-0133` to `SA-0139` to `done/`. `SA-0142`'s parent `SA-0136`
    is among them, so `SA-0142` is a candidate beside `SA-0141`. Every other
    spec of b-792ab2's chain is still refused on a parent that has not run.

    Re-measured 2026-09-25, a ninety-sixth time: fourteen specs queued
    for backlog item b-792ab2, the stack batch's build steps 6 to 9. They
    are `SA-0150`, `SA-0151`, `SA-0152`, `SA-0160`, `SA-0161`, `SA-0162`,
    `SA-0164`, `SA-0165`, `SA-0167`, `SA-0168`, `SA-0169`, `SA-0170`,
    `SA-0173` and `SA-0174`. They cover the spec writer and its revision
    rounds, the follow-ups and their layers, the finishing layer and the
    stack view. Each declares a parent in the same chain that has not run,
    so each is refused. `SA-0156` now declares `depends_on: [SA-0169]`.
    The candidates are unmoved.

    Re-measured 2026-09-23, a ninety-fifth time: `SA-0156` queued for
    backlog item b-792ab2, step 6's third spec. It builds the spec review
    session and the mint that `saffron batch --stack` passes, and runs each
    cell on the task its review is recorded on. It declares
    `depends_on: [SA-0155]`, so it is refused, since `SA-0155` has not run.
    The candidates are unmoved.

    Re-measured 2026-09-23, a ninety-fourth time: `SA-0159` queued for
    backlog item b-792ab2, split from `SA-0147`. It keeps the names each gate
    of a run's baseline collected. It declares `depends_on: [SA-0157]`, so it
    is refused, since `SA-0157` has not run. `SA-0147` now declares
    `depends_on: [SA-0159, SA-0138]`. The candidates are unmoved.

    Re-measured 2026-09-23, a ninety-third time: `SA-0157` queued for
    backlog item b-792ab2, split from `SA-0154` to keep its size under the
    margin. It wires the end review into `saffron batch --stack`, with a
    reserve of a quarter of `--budget`. It declares `depends_on: [SA-0154]`,
    so it is refused, since `SA-0154` has not run. The candidates are
    unmoved.

    Re-measured 2026-09-23, a ninety-second time: `SA-0155` queued for
    backlog item b-792ab2, step 6's second spec. It mints each reviewed
    spec's task before its review and records the review as facts on it. It
    declares `depends_on: [SA-0149]`, so it is refused, since `SA-0149` has
    not run. The candidates are unmoved.

    Re-measured 2026-09-23, a ninety-first time: `SA-0149` queued for
    backlog item b-792ab2, step 6 of its build order. It reads a spec
    review's findings block and routes each spec in a stack batch on it. It
    declares `depends_on: [SA-0148]`, so it is refused, since `SA-0148` has
    not run. The candidates are unmoved.

    Re-measured 2026-09-23, a ninetieth time: `SA-0148` queued for
    backlog item b-792ab2, step 5 of its build order. A rate limit in a
    stack batch waits for the window and runs the same spec again. It
    declares `depends_on: [SA-0147]`, so it is refused, since `SA-0147` has
    not run. The candidates are unmoved.

    Re-measured 2026-09-23, an eighty-ninth time: `SA-0147` queued for
    backlog item b-792ab2, step 4. It qualifies the end review's findings in
    host code. It declares `depends_on: [SA-0154]`, so it is refused, since
    `SA-0154` has not run. The candidates are unmoved.

    Re-measured 2026-09-23, an eighty-eighth time: `SA-0154` queued for
    backlog item b-792ab2, the third of three for step 3's end review. It
    adds the join lens and a layer's critic cell, and runs the whole end
    review in one call, which `SA-0157` wires into `saffron batch --stack`.
    It declares `depends_on: [SA-0153]`, so it
    is refused, since `SA-0153` has not run. The candidates are unmoved.

    Re-measured 2026-09-23, an eighty-seventh time: `SA-0153` queued for
    backlog item b-792ab2, the second of three for step 3's end review. It
    runs the end-review lenses over a stack, top down within a reserve, and
    records each layer's end review. It declares `depends_on: [SA-0146]`, so
    it is refused, since `SA-0146` has not run. The candidates are unmoved.

    Re-measured 2026-09-23, an eighty-sixth time: `SA-0146` queued for
    backlog item b-792ab2, the first of three for step 3's end review. It
    builds the Spec and Standards end-review lenses and fills their fields
    from the ledger. It declares `depends_on: [SA-0145]`, so it is refused,
    since `SA-0145` has not run. The candidates are unmoved.

    Re-measured 2026-09-23, an eighty-fifth time: `SA-0145` queued for
    backlog item b-792ab2, the last of four for a stack batch. It records
    each layer in a `stack_layers` table the fold rebuilds. It declares
    `depends_on: [SA-0144]`, so it is refused, since `SA-0144` has not run.
    The candidates are unmoved.

    Re-measured 2026-09-23, an eighty-fourth time: `SA-0143` and `SA-0144`
    queued for backlog item b-792ab2, the second and third of four for a
    stack batch. `SA-0143` hands each task its predecessor's branch, and
    `SA-0144` adds the `--stack` flags. `SA-0142` now declares
    `depends_on: [SA-0136]`, so `SA-0143`'s tree holds both chains. It moves
    from the candidates to the refusals, since `SA-0136` has not run.
    `SA-0143` depends on `SA-0142`, and `SA-0144` on `SA-0143`, so both are
    refused too.

    Re-measured 2026-09-23, an eighty-third time: `SA-0142` queued for
    backlog item b-792ab2, the first of three for a stack batch's order. It
    edits `saffron/scheduler.py` and `tests/test_scheduler.py`, which no
    queued spec touches, and declares no `depends_on`. At priority 1 it sorts
    after `SA-0140` by filename, so it is the second of six candidates. The
    refusals are unmoved.

    Re-measured 2026-09-25, an eighty-second time: the spec loop's run 16
    retired `SA-0133` to `SA-0139` to `done/`. `SA-0141` depends on
    `SA-0133`, `SA-0138`, `SA-0139` and `SA-0140`, which `done/` now
    satisfies, so it is the one candidate and nothing is refused.

    Re-measured 2026-09-23, an eighty-first time: the spec loop's run 16
    retired `SA-0140` (#501) and `SA-0129` (#502, taken by hand) to `done/`.
    `SA-0134` depends on `SA-0129`, which `done/` now satisfies, so it is a
    candidate.

    Re-measured 2026-09-23, an eightieth time: `SA-0141` queued for
    backlog item b-4e0868, which sends REBUT's two structured turns a schema
    through the SDK's `output_format`. It edits files `SA-0133`, `SA-0138`,
    `SA-0139` and `SA-0140` also touch, so it declares all four in
    `depends_on`. It is refused on that, since none has run. The candidates
    are unmoved.

    Re-measured 2026-09-23, a seventy-ninth time: the spec loop's run 16
    moved `SA-0133` onto `SA-0139`, since both edit
    `saffron/phases/implement.py`, `tests/test_implement.py` and
    `tests/test_session.py`. It is refused on that, since `SA-0139` has not
    run, and leaves the candidates.

    Re-measured 2026-09-23, a seventy-eighth time: `SA-0138` queued for
    backlog item b-19b255, which counts a vacuity probe killed only when a
    test the diff adds fails. It edits `saffron/cell/session.py` and
    `tests/test_session.py`, which `SA-0133` also touches, so it declares
    `depends_on: [SA-0133]`. It is refused on that, since `SA-0133` has not
    run. The candidates are unmoved.

    Re-measured 2026-09-23, a seventy-seventh time: `SA-0139` queued for
    backlog item b-6377cf, a `witness` survivor at base that the baseline no
    longer cancels. It also edits `saffron/phases/implement.py`,
    `tests/test_implement.py` and `tests/test_session.py`, which `SA-0133`
    touches too. Overlap refuses only against an open pull request, so both
    stay candidates, and it declares no `depends_on`. At priority 2 it is the
    fourth of five candidates. The refusals are unmoved.

    Re-measured 2026-09-23, a seventy-sixth time: `SA-0140` queued for
    backlog item b-8487de. The SDK gets the system prompt as a file, and a
    verdict session that never started ends REBUT `GATE_ERROR`. It edits
    `images/agent_runner.py`, `saffron/phases/rebut.py` and
    `tests/test_agent_runner.py`, which no queued spec touches, and declares
    no `depends_on`. At priority 1 it is the first of four candidates. The
    refusals are unmoved.

    Re-measured 2026-09-23, a seventy-fifth time: `SA-0137` queued for
    backlog item b-a9ee32, a pin on `attr.tree` in `git_argv`. It edits
    `saffron/cell/worktree.py` and `tests/test_worktree.py`, which no queued
    spec touches, and declares no `depends_on`. At priority 2 it is the
    second of three candidates. The refusals are unmoved.

    Re-measured 2026-09-23, a seventy-fourth time: `SA-0135` and `SA-0136`
    queued for backlog item b-602d00, the second and third of three.
    `SA-0135` adds the `consumes:` field and refuses a task whose entry does
    not resolve at its tree base. `SA-0136` refuses a malformed entry at
    load and an unreadable one before the cell. Each stacks on the one
    before, so `SA-0135` declares `depends_on: [SA-0134]` and `SA-0136`
    declares `depends_on: [SA-0135]`. Both are refused on that, since
    neither parent has run. The candidates are unmoved.

    Re-measured 2026-09-23, a seventy-third time: the spec loop's run 15
    retired `SA-0125`, `SA-0126`, `SA-0127`, `SA-0128`, `SA-0130` and
    `SA-0131` to `done/`. `SA-0129` and `SA-0133` depend on `SA-0128`, which
    `done/` now satisfies, so both are candidates. `SA-0134` is still refused
    on `SA-0129`.

    Re-measured 2026-09-22, a seventy-second time: `SA-0134` queued for
    backlog item b-602d00, a reader that says whether a tree base holds a
    path or a name. It is the first of two, and `SA-0135` wires it in. It
    edits `saffron/repos/mirror.py` and `tests/test_mirror.py`, which no
    queued spec touches. It declares `depends_on: [SA-0129]`, because its
    child edits `saffron/intake.py` after `SA-0129`. It is refused on that,
    since `SA-0129` has not run. The candidates are unmoved.

    Re-measured 2026-09-22, a seventy-first time: `SA-0133` queued for
    backlog item b-864a4d, a digest of each session's request and of the
    task's `CLAUDE.md` in the event log. It edits the cell session, the
    event table and `tests/test_session.py`, which `SA-0126` and `SA-0128`
    edit too, so it declares `depends_on: [SA-0128]`. It is refused on that,
    since `SA-0128` has not run. The candidates are unmoved.

    Re-measured 2026-09-22, a seventieth time: `SA-0131` queued for
    backlog item b-111c56, a parent merged by hand after `EXHAUSTED`. It
    edits the scheduler and the CLI, which no queued spec touches, so it
    declares no `depends_on`. It shares `SA-0130`'s priority and sorts after
    it on id, so it is candidate 4 of 4. The refusals are unmoved.

    Re-measured 2026-09-22, a sixty-ninth time: `SA-0130` queued for
    backlog item b-2dea1c, the IMPLEMENT prompt saying who runs wrong versions
    of the change. It edits `implement.md` and `tests/test_context.py`, which no
    queued spec touches, so it declares no `depends_on`. It sorts after
    `SA-0125` on priority and is candidate 3 of 3. The refusals are unmoved.

    Re-measured 2026-09-22, a sixty-eighth time: `SA-0123` (item
    b-fd1468) and `SA-0124` (item 171) merged and retire to `done/`. `SA-0123`
    was candidate 1, and `SA-0124` was refused on its `depends_on`. The
    candidates are `SA-0127` then `SA-0125`, and the refusals `SA-0126`,
    `SA-0128` and `SA-0129`.

    Re-measured 2026-09-22, a sixty-seventh time: `SA-0129` queued for
    backlog item b-db95e1, `driver.py check` refusing a spec whose declared
    estimate, priced in tokens, sits within 20% of its `size` ceiling. It
    reads `SA-0128`'s token ceilings and rate, so it declares
    `depends_on: [SA-0128]`. It is refused on that, since `SA-0128` has not
    run. The candidates are unmoved.

    Re-measured 2026-09-22, a sixty-sixth time: `SA-0128` queued for
    backlog item b-89ec93, `size` counting tokens rather than lines. It edits
    `tests/test_session.py`, which `SA-0126` edits too, so it declares
    `depends_on: [SA-0126]`. It is refused on that, since `SA-0126` has not
    run. The candidates are unmoved.

    Re-measured 2026-09-22, a sixty-fifth time: `SA-0126` queued for
    backlog item b-36b551, the salvage turn for a wall cut. It edits the cell
    session and the event table, which `SA-0125` edits too, so it declares
    `depends_on: [SA-0125]`. It is refused on that, since `SA-0125` has not
    run. The candidates are unmoved.

    Re-measured 2026-09-22, a sixty-fourth time: `SA-0125` queued for
    backlog item b-408cf5, the plan checkpoint refusing only where `size`
    blocks. It edits the checkpoint, the suite and the cell session, which
    no queued spec touches, so it declares no `depends_on`. It sorts after
    `SA-0127` on priority and is candidate 3 of 3.

    Re-measured 2026-09-22, a sixty-third time: `SA-0127` queued for
    backlog items 50 and 51, the `tests` gate reporting what became of each
    handed name. It edits the gate contract and `revert`, which no queued
    spec touches, so it declares no `depends_on` and is candidate 2 of 2.

    Re-measured 2026-09-22, a sixty-second time: `SA-0124` queued for
    backlog item 171, the diff stat in the ledger and the record. It edits
    `ledger.py` and two of its test files, which `SA-0123` edits too, so it
    declares `depends_on: [SA-0123]`. It is refused on that, since `SA-0123`
    has not run. The candidates are unmoved.

    Re-measured 2026-09-22, a sixty-first time: `SA-0123` queued for
    backlog item b-fd1468, the half that routes the write methods through
    `_apply`. Nothing else is queued, so it overlaps nothing, declares no
    `depends_on`, and is the one candidate. Nothing is refused.

    Re-measured 2026-09-22, a sixtieth time: the spec loop's run 13
    merged `SA-0119` (#431), `SA-0120` (#434), `SA-0122` (#436), `SA-0118`
    (#433) and `SA-0121` (#435), and all five retire to `done/`. Nothing is
    queued, so both lists are empty.

    Re-measured 2026-09-21, a fifty-ninth time: `SA-0121` and `SA-0122`
    queued together. `SA-0121` takes item 89's remainder, the two copies of
    `DIFF_FLAGS` in `harness/recovery.py` and `tests/test_package.py`. It
    overlaps nothing and declares no `depends_on`, so it is candidate 3 of 3.
    `SA-0122` takes item b-e403c1, the `probes.json` entry shape written twice.
    It declares `depends_on: [SA-0120]` and is refused on that.

    Re-measured 2026-09-21, a fifty-eighth time: `SA-0120` queued for
    backlog item b-2750d5, the half that applies each criterion probe and runs
    its criterion's witness over it. It edits `session.py` and its tests, which
    `SA-0119` edits too, so it declares `depends_on: [SA-0119]`. It is refused
    on that, since `SA-0119` has not run. The candidates are unmoved.

    Re-measured 2026-09-21, a fifty-seventh time: `SA-0118` queued for
    backlog item 103, the two attribute sources no override reaches. Its
    touches are `worktree.py` and its tests, which `SA-0119` forbids, so the
    two do not overlap. Neither declares `depends_on`, and both are candidates.
    Nothing is refused.

    Re-measured 2026-09-21, a fifty-sixth time: `SA-0119` queued for
    backlog item b-461729, the two rules that decide where a vacuity probe is
    applied, with item b-a70ec1 folded in. It edits `probe.py`, `session.py`,
    the lens-corpus driver and their tests, and nothing else is queued. So it
    has no `depends_on` and is the one candidate. Nothing is refused.

    Re-measured 2026-09-21, a fifty-fifth time: the spec loop's run 11
    merged `SA-0113` (#403), `SA-0114` (#404) and `SA-0115` (#406), and all
    three retire to `done/`. Nothing is queued, so both lists are empty.

    Re-measured 2026-09-21, a fifty-fourth time: the spec loop's run 12
    merged `SA-0117` (#418) and `SA-0116` (#416), and both retire to `done/`.
    `SA-0117` leaves the candidates. `SA-0116` leaves the refusals, where it
    waited on `SA-0115`. The three run 11 specs are unmoved.

    Re-measured 2026-09-20, a fifty-third time: `SA-0117` queued for
    backlog item b-fd1468, the fold that patches the rows the ledger's write
    methods make. It edits `ledger.py`, `record/fold.py` and their tests, which
    nothing else queued touches, so it has no `depends_on`. It joins the
    candidates at priority 1, after `SA-0113` by id and ahead of `SA-0114`.
    The refusals are unmoved.

    Re-measured 2026-09-20, a fifty-second time: `SA-0116` queued for
    backlog item b-7d3810, the four edits the commit that adds a spec owes to
    four other files. It edits the same two files as `SA-0114` and `SA-0115`,
    the spec loop's `driver.py` and `tests/test_spec_loop_driver.py`, so it
    declares `depends_on: [SA-0115]` — the later of the two — and is refused:
    that parent has no task at its current `spec_sha`. The candidates are
    unmoved, and the refusals are now two links of one chain.

    Re-measured 2026-09-20, a fifty-first time: `SA-0115` queued for the
    directory half of backlog item b-b69bb6, the tests that enumerate a
    directory a spec adds a file to. It edits the same two files as `SA-0114`,
    the spec loop's `driver.py` and `tests/test_spec_loop_driver.py`, so it
    declares `depends_on: [SA-0114]` and is refused: that parent has no task at
    its current `spec_sha`. The candidates are unmoved, and this is the
    seventeenth anchor's shape again, one link long.

    Re-measured 2026-09-20, a fiftieth time: `SA-0114` queued for the
    citation half of backlog item b-b69bb6, the `file:line` a spec review
    resolves by eye. It edits the spec loop's `driver.py` and
    `tests/test_spec_loop_driver.py`, which nothing else queued touches, so it
    has no `depends_on`. It joins `SA-0113` in the candidates, after it by
    priority. Nothing is refused. Its review cut the item's directory half out
    of it, which moves no `touches` entry and so no candidate.

    Re-measured 2026-09-20, a forty-ninth time: `SA-0113` queued for
    backlog item b-2750d5, the edit no session names for an acceptance claim.
    It edits `review.py`, `session.py`, two new prompt files and three test
    files, and nothing else is queued, so it has no `depends_on` and is the
    one candidate. Nothing is refused.

    Re-measured 2026-09-19, a forty-eighth time: the spec loop's run 10
    merged `SA-0111` (#381) and `SA-0112` (#382), and both retire to `done/`.
    Nothing is queued, so the candidate list is empty. The glob check below
    survives that: a glob that recursed into `done/` would offer the thirty-odd
    specs the precondition counts, and an empty list is the only thing they
    cannot produce.

    Re-measured 2026-09-19, a forty-seventh time: the spec loop's run 9
    merged `SA-0109` (#375) and `SA-0110` (#377), and both retire to `done/`.
    `SA-0111` and `SA-0112` are what is left, in that order.

    Re-measured 2026-09-19, a forty-sixth time: `SA-0112` queued for
    backlog item b-281f0a, the ceilings comparison no command judges. It edits
    the spec loop's `driver.py` and `tests/test_spec_loop_driver.py`, which
    nothing else queued touches, so it has no `depends_on` and joins the
    candidates last — priority 3, tied with `SA-0110` and after it by filename.

    Re-measured 2026-09-19, a forty-fifth time: `SA-0111` queued for
    backlog item 97's record half, the head a merging pull request is at. It
    edits `ledger.py` and `reconcile.py` and their tests, none of which
    anything else queued touches, so it has no `depends_on` and joins the
    candidates between `SA-0109` and `SA-0110` — priority 2, and ties run by
    filename.

    Re-measured 2026-09-19, a forty-fourth time: `SA-0110` queued for
    backlog item b-9ff0fd, the ADR record kind. It edits only `records/` and
    `tests/records/`, which nothing else queued touches, so it has no
    `depends_on` and joins the candidates after `SA-0109`.

    Re-measured 2026-09-19, a forty-third time: the spec loop's run 8 merged
    `SA-0101`, `SA-0102`, `SA-0107`, `SA-0108` and `SA-0106` (#351, #360, #355,
    #366, #353), and all five retire to `done/`. `SA-0109`'s parent `SA-0102` is
    merged, so it is the one candidate and nothing is refused.

    Re-measured 2026-09-18, a forty-second time: `SA-0109` queued for
    backlog item 117, the adequacy probe no task runs. It edits `session.py`
    and `test_session.py`, so it stacks on `SA-0102`, the tail of that chain,
    and is refused until `SA-0102` has a task. The candidates are unmoved.

    Re-measured 2026-09-18, a forty-first time: `SA-0107` and `SA-0108` queued
    for backlog item b-946f03 and Appendix T, the emitter reopened on
    the RATIONALE's own revisit clause. `SA-0107` creates two files and edits
    none, so it has no `depends_on` and joins the candidates at priority 2, after
    `SA-0101` by id. `SA-0108` is refused, and the refusal is correct: it stacks
    on `SA-0107`, which has no task at its current `spec_sha`. This is the
    seventeenth anchor's shape.

    Re-measured 2026-09-18, a fortieth time: the spec loop's run 7 merged
    `SA-0104`, `SA-0099`, `SA-0100`, `SA-0103` and `SA-0105` (#335, #338, #339,
    #342, #340), and all five retire to `done/`. `SA-0101`'s parent `SA-0099` is
    done, so it joins the candidates ahead of `SA-0106` by priority. `SA-0102`
    stays refused on `SA-0101`.

    Re-measured 2026-09-17, a thirty-ninth time: `SA-0106` queued for
    backlog item b-d6bff7, the batch's one scan. It edits `batch.py` and `cli.py`,
    which nothing else queued touches, so it has no `depends_on` and joins the
    candidates last, at priority 3 and after `SA-0105` by id.

    Re-measured 2026-09-17, a thirty-eighth time: `SA-0105` queued for
    backlog item 176, `mirror.diff_stat`'s bare read. Only it edits `mirror.py`,
    so it has no `depends_on` and joins the candidates last, at priority 3.

    Re-measured 2026-09-17, a thirty-seventh time: `SA-0104` queued for
    backlog item 154, the mutant write that cannot carry a file over 96 KiB. It
    edits `worktree.py`, which nothing else queued touches, so it has no
    `depends_on` and leads the candidates at priority 1.

    Re-measured 2026-09-17, a thirty-sixth time: `SA-0093`, `SA-0094`,
    `SA-0096` and `SA-0097` merged (PRs #303, #305, #320, #321) and retire to
    `done/`. `SA-0099` was refused on `SA-0094`, so it joins the candidates;
    `SA-0101` and `SA-0102` stay refused down its chain, `SA-0103` on `SA-0100`.

    Re-measured 2026-09-17, a thirty-fifth time: `SA-0098` merged as PR #323
    and is retired to `done/`, so it leaves the candidates. The refusals are
    unchanged: `SA-0101` named it as a second `depends_on`, and is still refused
    on its first, `SA-0099`.

    Re-measured 2026-09-17, a thirty-fourth time: five specs queued for
    backlog items 164 to 167 and 43, the observability gaps an inventory of what
    one execution can be seen through turned up. They form **two chains**, and
    only the head of one is a candidate.

    `SA-0100` (item 165, a task that never packaged reaching no index row) edits
    `saffron/task.py` and a `tests/test_task.py` that does not exist yet. Nothing
    else queued touches either, so it has `depends_on: []` and joins the
    candidates last — priority 2, and ties run by id. `SA-0103` (item 167, the
    unread `EventLog.failed`) stacks on it, because the reader belongs in the
    same closure at `task.py:251` and its witness goes in the file `SA-0100`
    creates.

    The other chain hangs off the existing `session.py` one. `SA-0099` (item 164,
    `runs.preflight`) is refused on `SA-0094`, then `SA-0101` (item 43's second
    half, the terminal announcement that reaches no log) on `SA-0099`, then
    `SA-0102` (item 166, the `GateResult` kind nothing constructs) on `SA-0101`.
    All four edit `saffron/cell/session.py`, so the chain is the thirty-first
    anchor's shape three links further down. `SA-0101` also carries a second
    `depends_on`, `SA-0098`, because both edit `saffron/events.py`: a second
    entry is a dependency rather than a base, and it refuses on the same terms.

    Every refusal here is the `depends_on` one and none is an overlap, because
    `_fake_gh([])` leaves `open_prs` empty. The chains are the operator's
    declaration, not the scheduler's inference.

    Re-measured 2026-09-17, a thirty-third time: `SA-0095` merged as PR #307
    and is retired to `done/`, so it leaves the queue and `SA-0094` is the only
    refusal left. The candidates are unmoved: `SA-0094` was refused on
    `SA-0093`, never on `SA-0095`, so retiring the child frees nothing.

    Re-measured 2026-09-16, a thirty-second time: `SA-0096`, `SA-0097` and
    `SA-0098` queued for backlog items 114, 115 and 63. No two queued specs
    share a `touches` file (`SA-0097` applies its mutants to `worktree.py`,
    which `SA-0096` edits, without listing it), so all three are independent
    and join the candidates behind `SA-0093`: every one is priority 2, and ties
    run by id. The refusals are unchanged.

    Re-measured 2026-09-16, a thirty-first time: `SA-0093`, `SA-0094` and
    `SA-0095` queued for backlog items 140, 143 and 141, the three cell-runnable
    items `SA-0089`'s review left open. `SA-0093` has `depends_on: []`, so it is
    the one candidate. The other two are refused, and both refusals are correct:
    all three edit `saffron/cell/session.py`, `SA-0094` stacks on `SA-0093` and
    `SA-0095` on `SA-0094`, and neither parent has a task at its current
    `spec_sha` yet.

    Re-measured 2026-09-16, a thirtieth time: the whole of item 118's chain
    and both harness-patterns specs merged in one spec loop (stack #285) and are
    retired to `done/`, so the live queue is **empty** — no candidate and no
    refusal. `SA-0088` (#277), `SA-0089` (#282), `SA-0091` (#284), `SA-0090`
    (#278) and `SA-0092` (#279) are all in `main`. An empty queue is the one
    shape that would also be produced by a glob that recursed into `done/` and
    then refused everything, so the `done/` population assertion below is what
    keeps this a check rather than a scan of nothing.

    Re-measured 2026-09-16, a twenty-ninth time: `SA-0087` merged as PR #274
    and is retired to `done/`, so item 118's chain advances by one. `SA-0088`
    becomes the candidate its parent was, because a parent in `done/` is the
    operator asserting that work is in `main` — the one thing a `spec_sha` task
    lookup cannot say on its own. `SA-0089` and `SA-0091` are still refused, now
    on `SA-0088` and `SA-0089`, and `SA-0090` and `SA-0092` are unmoved.

    Re-measured 2026-09-15, a twenty-eighth time: `SA-0092`, from backlog
    item 123. It edits the spec loop's driver and that file's tests, which
    nothing else queued touches, so it is refused by nothing and joins the
    candidates behind `SA-0087` and `SA-0090` — priority 3, and later by id.
    The refusals are unchanged.

    Re-measured 2026-09-15, a twenty-seventh time: `SA-0090` and `SA-0091`,
    from checking REVIEW and REBUT against a harness-patterns skill. `SA-0090`
    is independent and joins the candidates behind `SA-0087`, because it is
    priority 3. `SA-0091` is refused on `SA-0089`, which is correct: both edit
    `session.py`, and it also edits `rebut.py` after `SA-0088`.

    Re-measured 2026-09-14, a twenty-sixth time: `SA-0074` to `SA-0086`
    all merged to `main` and retired to `done/`, so the live queue holds only
    the tail of item 118's chain. `SA-0087` has `depends_on: []`, so it is the
    one candidate. `SA-0088` (`depends_on: [SA-0087]`) and `SA-0089`
    (`depends_on: [SA-0088]`) are both refused, and correctly: neither parent
    has a task at its current `spec_sha`, so nothing says it merged.

    Re-measured 2026-09-14, a twenty-fifth time: `SA-0086` to `SA-0089`
    queued for item 118. `SA-0086` and `SA-0087` are independent and join the
    candidates behind `SA-0074`, because candidates run in priority order and
    both are priority 1; refusals stay in file order. `SA-0088` stacks on
    `SA-0087` and `SA-0089` on `SA-0088`, because all three edit `session.py`.
    Neither parent has a task yet, so both are refused until the night after
    their parent packages.

    Re-measured 2026-09-13, a twenty-fourth time: four more specs. `SA-0082`
    (item 89) is independent and joins the candidates, ahead of `SA-0079` and
    `SA-0080` because it is priority 2 and they are 3. The other three are
    refused on a parent with no task yet, and each refusal is correct:
    `SA-0083` (item 110) stacks on `SA-0082` (both edit `worktree.py`),
    `SA-0084` (item 63) on `SA-0080` (both edit `events.py`), and `SA-0085`
    (item 23) on `SA-0084`.

    Re-measured 2026-09-13, a twenty-third time: `SA-0079` (item 111),
    `SA-0080` (item 62) and `SA-0081` (item 64) queued. The first two are
    independent and join the candidates. `SA-0081` is refused, which is
    correct: it stacks on `SA-0080`, both edit `saffron/watch.py`, and the
    parent has no task yet.

    Re-measured 2026-09-12, a twenty-second time: `SA-0078` (item 109)
    queued, independent of everything, so it joins the candidates. `SA-0075`
    is still refused on its parent.

    Re-measured 2026-09-12, a twenty-first time: `SA-0075` (item 103) and
    `SA-0076` (item 104) queued. `SA-0076` is independent, so it joins `SA-0074`
    as a candidate. `SA-0075` is refused, which is correct: it stacks on
    `SA-0074`, both edit `_git`, and the parent has no task yet, so it waits for
    the night after its parent packages. This is the seventeenth anchor's shape.

    Re-measured 2026-09-12, a twentieth time: `SA-0074` queued for backlog
    item 102, independent of everything, so it is the one candidate.

    Re-measured 2026-09-12, a nineteenth time: all eight specs below merged
    as stack #222 and were retired, so the live queue is empty again — the
    sixteenth anchor's shape, and the same non-recursive glob is what it checks.

    Re-measured 2026-09-10, an eighteenth time: three more specs, `SA-0071` to
    `SA-0073`, each independent of the rest, so all three are candidates.
    Nothing else moved.

    Re-measured 2026-09-10, a seventeenth time: five specs queued for a later
    night, `SA-0066` to `SA-0070`. Three are candidates. `SA-0067` and `SA-0070`
    are refused, and that is correct: each stacks on a parent (`SA-0066`,
    `SA-0068`) that has no task yet, and a night resolves its scan once, so a
    child waits for the night after its parent packages. `SA-0070` gained its
    parent in review, because both specs edit `saffron/events.py`.

    Re-measured 2026-09-10, a sixteenth time: every spec then in the tree
    had shipped and was retired, so the live queue was empty. The chain
    below merged as PRs #148, #150 and #154. What survives is the property the
    eleventh kept, the non-recursive glob.

    Re-measured 2026-09-06, a fifteenth time. `SA-0059` asked for item 71's
    whole seam in one spec, reached `EXHAUSTED` at $26.75, and is replaced by
    the sequence it named as its own contingency: `SA-0060` -> `SA-0061` ->
    `SA-0062`.

    So the shape is a chain three deep again, and the fourteenth anchor's
    "deliberately not a layer" is now wrong in a way worth leaving visible in
    the history rather than quietly overwriting. What changed is not the
    judgement that the seam is one thing — it is — but that one cell could not
    hold it. The order is what carries the lesson: the wiring lands second,
    against a stub, so the seam is exercised end to end before the expensive
    part exists.

    Retiring merged specs is not tidying either. `done/README.md` names the
    hazard: the ledger filter keys on `spec_sha`, so a merged spec left at the
    top level re-runs the moment anyone edits it, and nothing distinguishes a
    rewrite from a typo fix.

    Kept from the eleventh because it is the part that does not churn: the
    non-recursive glob. `done/` holds forty-odd shipped specs one directory
    down and the scan must see none of them — a real property with a real
    failure mode, and the reason `done/` retires a spec rather than deleting
    it.

    The dependency-chain assertion this carried through nine anchorings is gone
    with the chain that justified it, and the corpus-parses property it briefly
    carried belongs to `test_no_real_spec_is_refused_on_its_own_acceptance_
    criteria`, which moves `done/` up and scans all of it.

    Note what this does *not* exercise. `_fake_gh([])` means `open_prs` is
    empty, so the open-pull-request overlap refusal never runs here — which is
    why this test is untouched by backlog item 59's ancestor walk, and why the
    fixtures above are where that behaviour is pinned.
    """
    live = Path(__file__).resolve().parent.parent / ".saffron" / "specs"
    directory = tmp_path / "specs"
    shutil.copytree(live, directory)
    repo_id = _repo(ledger)

    candidates, refusals = build_queue(
        directory, repo_id, ledger, repo_slug="joel/saffron", gh=_fake_gh([])
    )

    # A fresh ledger filters nothing, so a glob that recursed would offer every
    # spec in `done/` here as well. That is what makes the exact list a check.
    assert [c.spec.id for c in candidates] == ["SA-0142", "SA-0141"]
    assert [r.path.name[:7] for r in refusals] == [
        "SA-0143",
        "SA-0144",
        "SA-0145",
        "SA-0146",
        "SA-0147",
        "SA-0148",
        "SA-0149",
        "SA-0150",
        "SA-0151",
        "SA-0152",
        "SA-0153",
        "SA-0154",
        "SA-0155",
        "SA-0156",
        "SA-0157",
        "SA-0159",
        "SA-0160",
        "SA-0161",
        "SA-0162",
        "SA-0164",
        "SA-0165",
        "SA-0167",
        "SA-0168",
        "SA-0169",
        "SA-0170",
        "SA-0173",
        "SA-0174",
        "SA-0175",
        "SA-0176",
        "SA-0177",
    ]
    # A precondition, not the glob check: `done/` holds far more specs than the
    # queue above, so that exact list is a check rather than a scan of nothing.
    assert len(list((directory / "done").glob("*.md"))) > 30


def test_no_real_spec_names_a_criterion_path_its_touches_do_not_cover(tmp_path):
    """BACKLOG item 81: the property asserted directly, over every spec, with
    no ledger and no refusal ordering in front of it.

    The item's own diagnosis does not reproduce and is corrected in the
    backlog. It claims `_refuse` decides an unsatisfied `depends_on` *before*
    the criterion-path check, blinding
    `test_no_real_spec_is_refused_on_its_own_acceptance_criteria` to every
    chained spec — "53 specs, 31 preempted, 22 examined". The order is the
    other way round: `scheduler.py:687` is the criterion-path check and the
    `depends_on` loop is at 697. Measured 2026-09-08 by planting
    `saffron/nowhere/invented.py` in each spec's first checklist box in turn
    and reading what the queue refuses it for: of the **30** specs whose
    criteria `_criteria_texts` reads from the markdown checklist, **28 report
    the criterion-path refusal**. `SA-0016`, named in that test as one of the
    two it memorialises, is among the 28. The other two are probe-dependent
    rather than a second class: `SA-0021` stops on an earlier `depends_on`
    refusal, and `SA-0001` is not refused at all because its own `forbidden:
    saffron/**` covers the planted token, which is this check's documented
    citation escape.

    What is left of the item is still worth this test. That check reaches the
    property only because of an ordering nothing pins, and it asserts something
    weaker — that no refusal is a criterion-path refusal — so it goes silently
    blind the day the order changes. This asserts the property itself. The
    queue-shaped test keeps its own job, which is that the queue refuses
    nothing unexpected.

    Over *every* spec, which is not what the first version of this test did:
    it was built on `_real_corpus`, which copies `done/` alone, so it scanned
    49 of 54 and never saw the specs still at the top of `.saffron/specs` —
    the five most recent, and the likeliest to carry a defect nobody has met.
    Measured: planting `saffron/nowhere/invented.py` in `SA-0060`'s first
    acceptance claim fails this test and passed the retired-only corpus.
    """
    directory = _every_live_spec_flattened(tmp_path)

    specs, _ = discover_specs(directory)
    # A loop that examined nothing would pass silently, which is the failure
    # mode this test exists to close rather than a stricter form of it. The
    # count is the guard, and it is also why the discovery failures are
    # dropped rather than asserted empty: a spec that does not parse cannot be
    # asked this question — unproven, not broken, the same distinction items
    # 83 and 84 turn on — while a corpus that stopped parsing *wholesale*
    # takes `len(specs)` down through this floor and fails here.
    assert len(specs) > 45, f"only {len(specs)} specs scanned"

    named = {
        found.spec.id: token
        for found in specs
        if (token := _unmatched_criterion_path(found.spec)) is not None
    }
    assert named == {}


def test_no_real_spec_is_refused_on_its_own_acceptance_criteria(tmp_path, ledger):
    """The half of the smoke check that catches a defect, pointed at the whole
    retired corpus — 36 specs rather than the 9 that happened to be in flight.

    No ledger, so nothing is filtered before `_refuse` runs and every spec
    reaches it. The criterion-path check shipped refusing `SA-0011` and
    `SA-0016` on their own criteria, and this is the assertion that catches
    that class: a `depends_on` refusal is the expected shape here, because the
    corpus is one long dependency chain with no tasks behind it; a refusal on
    anything else is the bug.
    """
    directory = _every_retired_spec_at_top_level(tmp_path)

    _, refusals = build_queue(
        directory, None, ledger, repo_slug="joel/saffron", gh=_fake_gh([])
    )

    assert refusals, "the corpus refuses nothing, so this asserts nothing"
    assert [r for r in refusals if "acceptance criteria name" in r.reason] == []
    # One legitimate non-`depends_on` refusal, named rather than waved through
    # by a loose predicate: `SA-0063` discloses its own mutant (item 82). This
    # helper promotes it *out* of `done/`, where production keeps it, so the
    # refusal is an artifact of the arrangement — naming the single spec it may
    # apply to keeps a second one from slipping in behind it.
    disclosed = [r for r in refusals if "mutant names text" in r.reason]
    assert [r.path.name[:7] for r in disclosed] == ["SA-0063"]
    assert all("depends_on" in r.reason for r in refusals if r not in disclosed)
