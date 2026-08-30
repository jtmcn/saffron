import json
import shutil
import subprocess
from pathlib import Path

import pytest

from saffron.cell import runtime
from saffron.intake import load_spec
from saffron.ledger import Ledger
from saffron.scheduler import DONE_STATES, REQUEUE_STATES, build_queue
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


# ------------------------------------------------------- refusal: depends_on


def test_a_non_empty_depends_on_refuses(tmp_path, ledger):
    directory = _spec_dir(tmp_path)
    _write_spec(directory, "a.md", id="TE-1", touches=["a.py"], depends_on=["TE-0"])

    candidates, refusals = build_queue(directory, None, ledger)

    assert candidates == []
    assert len(refusals) == 1
    assert "TE-0" in refusals[0].reason


# ---------------------------------------------------------------------- smoke


def test_saffron_queue_smoke_reproduces_this_repos_measured_queue(tmp_path, ledger):
    """Measured 2026-08-26 against `~/.saffron/ledger.db`: `SA-0001` and
    `SA-0008` queued, everything else filtered out with a `READY_FOR_REVIEW`
    task at the same `spec_sha`, and nothing refused. A smoke check, not proof
    the refusals work on their own — those are the fixtures above."""
    real_specs = Path(__file__).resolve().parent.parent / ".saffron" / "specs"
    directory = tmp_path / "specs"
    shutil.copytree(real_specs, directory)
    repo_id = _repo(ledger)

    still_open = {"SA-0001", "SA-0008"}
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

    assert [c.spec.id for c in candidates] == ["SA-0008", "SA-0001"]
    assert refusals == []

    # Again with no ledger, so nothing is filtered before `_refuse` runs. The
    # pass above reaches the refusals for two of eighteen specs — the other
    # sixteen are dropped as done first — so on its own it stays green while
    # every one of them is falsely refused, which is how the criterion-path
    # check shipped refusing SA-0011 and SA-0016 (this spec) on their own
    # criteria. `depends_on` refusals are expected here and are the shape the
    # Notes describe; a criterion-path refusal on a real spec is not.
    _, unfiltered = build_queue(
        directory, None, ledger, repo_slug="joel/saffron", gh=_fake_gh([])
    )

    assert [r for r in unfiltered if "acceptance criteria name" in r.reason] == []
    assert all("depends_on" in r.reason for r in unfiltered)
