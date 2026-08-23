import json
import subprocess
import subprocess as sp
from types import SimpleNamespace

import pytest

from saffron.agents.findings import Finding
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.phases.package import (
    APPLY_CONFLICT,
    APPLY_OK,
    LeaseRejected,
    PackageError,
    apply_patch,
    assert_base_objects,
    commit_squash,
    default_branch,
    find_credentials,
    find_credentials_in_text,
    github_slug,
    needs_reverification,
    neutralize,
    open_draft_pr,
    package,
    push_with_lease,
    real_remote,
    remote_sha,
)
from saffron.phases.review import LensReview


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def bare_remote(tmp_path):
    """A bare repo standing in for GitHub. No network anywhere in these tests."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "trunk", str(remote))
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-q", "-b", "trunk")
    git(seed, "config", "user.email", "t@example.com")
    git(seed, "config", "user.name", "Test")
    (seed / "f.txt").write_text("a\nb\nc\nd\ne\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "base")
    git(seed, "push", "-q", str(remote), "trunk")
    return remote


@pytest.mark.parametrize(
    "url,slug",
    [
        ("git@github.com:jtmcn/saffron.git", "jtmcn/saffron"),
        ("https://github.com/jtmcn/saffron.git", "jtmcn/saffron"),
        ("https://github.com/jtmcn/saffron", "jtmcn/saffron"),
        ("ssh://git@github.com/jtmcn/saffron.git", "jtmcn/saffron"),
    ],
)
def test_both_url_shapes_yield_the_same_slug(url, slug):
    assert github_slug(url) == slug


def test_a_repo_with_no_origin_fails_clearly(tmp_path):
    """Every fresh `git init` and every test fixture is this case."""
    repo = tmp_path / "lonely"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    with pytest.raises(PackageError, match="no 'origin' remote"):
        real_remote(repo)


def test_the_default_branch_is_read_not_assumed(tmp_path, bare_remote):
    """Not hardcoded `main`: repo two need not resemble repo one (§9)."""
    assert default_branch(str(bare_remote), cwd=tmp_path) == "trunk"


DIFF_FLAGS = [
    "--src-prefix=a/",
    "--dst-prefix=b/",
    "--no-ext-diff",
    "--no-textconv",
    "--no-renames",
]


@pytest.fixture
def cell_patch(tmp_path):
    """A squashed diff shaped exactly like `worktree.export_patch`'s output."""
    repo = tmp_path / "cell"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "f.txt").write_text("a\nb\nc\nd\ne\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "f.txt").write_text("a\nb\nCELL\nd\ne\n")
    git(repo, "commit", "-qam", "the agent's work")
    patch = tmp_path / "patch.diff"
    patch.write_text(git(repo, "diff", *DIFF_FLAGS, f"{base}..HEAD") + "\n")
    return repo, base, patch


def test_a_patch_applies_onto_a_base_that_moved_elsewhere(tmp_path, cell_patch):
    repo, base, patch = cell_patch
    git(repo, "checkout", "-q", "-b", "pkg", base)
    (repo / "f.txt").write_text("a\nb\nc\nd\nMAIN\n")
    git(repo, "commit", "-qam", "main moved")
    assert apply_patch(repo, patch) == APPLY_OK
    assert (repo / "f.txt").read_text() == "a\nb\nCELL\nd\nMAIN\n"


def test_a_conflict_is_reported_even_though_git_wrote_the_file(tmp_path, cell_patch):
    """Measured, git 2.50.1: a conflicting --3way apply exits 1 AND writes
    conflict markers with a staged `U` entry. "Apply failed" and "nothing
    happened" are not the same state, and anything that committed here would
    push `<<<<<<<` to a real remote."""
    repo, base, patch = cell_patch
    git(repo, "checkout", "-q", "-b", "pkg", base)
    (repo / "f.txt").write_text("a\nb\nMAIN_TOOK_THIS_LINE\nd\ne\n")
    git(repo, "commit", "-qam", "main moved into the same line")
    assert apply_patch(repo, patch) == APPLY_CONFLICT
    assert "<<<<<<<" in (repo / "f.txt").read_text()  # git really did write it


def test_a_degraded_apply_is_an_error_not_a_success(tmp_path):
    """Measured, git 2.50.1: preimage blob absent + context matching ->
    `error: repository lacks the necessary blob` on stderr, and rc 0.
    Conflict detection silently becomes a context match, which is the whole
    reason --3way was chosen."""
    src = tmp_path / "src"
    src.mkdir()
    git(src, "init", "-q", "-b", "main")
    git(src, "config", "user.email", "t@example.com")
    git(src, "config", "user.name", "Test")
    (src / "f.txt").write_text("\n".join(str(n) for n in range(1, 21)) + "\n")
    git(src, "add", "-A")
    git(src, "commit", "-qm", "base")
    base = git(src, "rev-parse", "HEAD")
    (src / "f.txt").write_text(
        "\n".join("CELL" if n == 10 else str(n) for n in range(1, 21)) + "\n"
    )
    git(src, "commit", "-qam", "cell")
    patch = tmp_path / "p.diff"
    patch.write_text(git(src, "diff", *DIFF_FLAGS, f"{base}..HEAD") + "\n")

    # A different repo: line 1 differs, so the base blob is absent, but the
    # context around line 10 matches exactly.
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q", "-b", "main")
    git(other, "config", "user.email", "t@example.com")
    git(other, "config", "user.name", "Test")
    (other / "f.txt").write_text(
        "\n".join("DIFFERENT" if n == 1 else str(n) for n in range(1, 21)) + "\n"
    )
    git(other, "add", "-A")
    git(other, "commit", "-qm", "other")

    with pytest.raises(PackageError, match="three-way merge"):
        apply_patch(other, patch)


def test_a_binary_patch_is_an_error_not_a_conflict(tmp_path):
    """`worktree.DIFF_FLAGS` has no --binary/--full-index, so a binary change
    exports as `Binary files ... differ`. That is a patch that was never
    appliable — `error`, never "the branch moved underneath" (§5.4)."""
    repo = tmp_path / "bin"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "keep.txt").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "b.bin").write_bytes(b"\x00\x01\x02BIN")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "binary")
    patch = tmp_path / "p.diff"
    patch.write_text(git(repo, "diff", *DIFF_FLAGS, f"{base}..HEAD") + "\n")
    git(repo, "checkout", "-q", base)
    with pytest.raises(PackageError, match="binary"):
        apply_patch(repo, patch)


def test_assert_base_objects_passes_when_the_mirror_has_the_base(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "f.txt").write_text("a\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    assert assert_base_objects(repo, base) is None


def test_assert_base_objects_names_the_missing_base(tmp_path):
    """Disjoint repos, not a diverged branch — a diverged branch can still
    have the base reachable. Two separate `git init`s guarantee it is absent."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    git(elsewhere, "init", "-q", "-b", "main")
    git(elsewhere, "config", "user.email", "t@example.com")
    git(elsewhere, "config", "user.name", "Test")
    (elsewhere / "f.txt").write_text("a\n")
    git(elsewhere, "add", "-A")
    git(elsewhere, "commit", "-qm", "base")
    missing_base = git(elsewhere, "rev-parse", "HEAD")

    mirror = tmp_path / "mirror"
    mirror.mkdir()
    git(mirror, "init", "-q", "-b", "main")
    git(mirror, "config", "user.email", "t@example.com")
    git(mirror, "config", "user.name", "Test")
    (mirror / "g.txt").write_text("b\n")
    git(mirror, "add", "-A")
    git(mirror, "commit", "-qm", "unrelated")

    with pytest.raises(PackageError, match=missing_base[:12]):
        assert_base_objects(mirror, missing_base)


def test_the_cells_own_token_is_found_and_never_echoed():
    """The cell carries CLAUDE_CODE_OAUTH_TOKEN — the one sanctioned in-cell
    credential. Pushed to a real remote it is effectively undeletable."""
    token = "sk-ant-oat01-EXAMPLE-NOT-REAL-0000"
    patch = f'+++ b/config.py\n+TOKEN = "{token}"\n'
    found = find_credentials(patch, token=token)
    assert found
    assert token not in " ".join(found)  # naming it must not reprint it
    assert "config.py" in " ".join(found)


def test_a_clean_patch_finds_nothing():
    assert find_credentials("+++ b/a.py\n+x = 1\n", token="sk-ant-oat01-XYZ") == []


def test_no_token_in_the_environment_still_scans_known_shapes():
    patch = "+++ b/a.py\n+key = 'sk-ant-api03-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'\n"
    assert find_credentials(patch, token=None)


@pytest.mark.parametrize(
    "text",
    [
        "Fixes #12",
        "closes #45",
        "Resolved #7",
        "ping @someone",
        "Fixes GH-12",
        "Fixes owner/repo#12",
    ],
)
def test_github_acts_on_model_authored_text_so_it_is_defanged(text):
    """GitHub closes issues named in a commit body AND a PR body, and notifies
    @accounts. A cell causing that is a side effect on a real repository from
    inside the boundary, even though no code executes."""
    out = neutralize(text)
    assert "#" not in out or not any(
        w in out.lower() for w in ("fixes", "closes", "resolved")
    )
    assert "@someone" not in out


def test_neutralize_leaves_ordinary_prose_alone():
    assert neutralize("the tz default is wrong in parse()") == (
        "the tz default is wrong in parse()"
    )


def test_the_squash_body_carries_provenance_and_defanged_subjects(tmp_path, cell_patch):
    repo, base, patch = cell_patch
    git(repo, "checkout", "-q", "-b", "pkg", base)
    apply_patch(repo, patch)
    sha = commit_squash(
        repo,
        spec_id="SA-0005",
        title="package a green cell",
        base_sha=base,
        cell_head="deadbeefdeadbeef",
        attempts=2,
        spent_usd=6.4,
        agent_subjects=["fix the thing", "Fixes #12"],
    )
    body = git(repo, "log", "-1", "--format=%B", sha)
    assert body.splitlines()[0] == "saffron SA-0005: package a green cell"
    assert base[:12] in body and "deadbeefdead" in body
    assert "2 attempts" in body and "$6.40" in body
    assert "Fixes #12" not in body  # defanged; the digits survive, the trigger does not
    assert "#12" in body


def test_an_absent_branch_takes_an_empty_lease(tmp_path, bare_remote, cell_patch):
    """Measured, git 2.50.1: --force-with-lease=<ref>: with an empty expectation
    pushes a branch that does not exist. Not a special case to write around."""
    repo, base, patch = cell_patch
    git(repo, "checkout", "-q", "-b", "saffron/SA-0005", base)
    assert remote_sha(str(bare_remote), "saffron/SA-0005", cwd=tmp_path) == ""
    push_with_lease(repo, url=str(bare_remote), branch="saffron/SA-0005", expect="")
    assert remote_sha(str(bare_remote), "saffron/SA-0005", cwd=tmp_path) != ""


def test_a_branch_that_moved_underneath_is_rejected(tmp_path, bare_remote, cell_patch):
    """§5.7: turning a race into an error costs one flag. Measured: `stale info`."""
    repo, base, patch = cell_patch
    git(repo, "checkout", "-q", "-b", "saffron/SA-0005", base)
    push_with_lease(repo, url=str(bare_remote), branch="saffron/SA-0005", expect="")
    stale = remote_sha(str(bare_remote), "saffron/SA-0005", cwd=tmp_path)

    # somebody else pushes
    (repo / "other.txt").write_text("theirs\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "theirs")
    git(repo, "push", "-q", str(bare_remote), "HEAD:refs/heads/saffron/SA-0005")

    (repo / "ours.txt").write_text("ours\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "ours")
    with pytest.raises(LeaseRejected, match="moved underneath|stale"):
        push_with_lease(
            repo, url=str(bare_remote), branch="saffron/SA-0005", expect=stale
        )


def test_a_non_lease_push_failure_is_not_a_lease_rejection(tmp_path, cell_patch):
    """auth/host/refspec failures are infrastructure (error), not the task's
    problem (fail) — collapsing them would send an operator to read a diff
    that was never the cause. A bad local path is the no-network way to make
    git fail for a reason that is not `stale info`."""
    repo, base, patch = cell_patch
    git(repo, "checkout", "-q", "-b", "saffron/SA-0005", base)
    bad_url = str(tmp_path / "does-not-exist.git")
    with pytest.raises(PackageError) as excinfo:
        push_with_lease(repo, url=bad_url, branch="saffron/SA-0005", expect="")
    assert not isinstance(excinfo.value, LeaseRejected)


def test_remote_sha_raises_rather_than_reporting_absent(tmp_path):
    """An unreachable remote returning "" would be read as "branch absent" by
    push_with_lease's empty lease, and push over a branch that does exist."""
    bad_url = str(tmp_path / "does-not-exist.git")
    with pytest.raises(PackageError, match="cannot reach"):
        remote_sha(bad_url, "saffron/SA-0005", cwd=tmp_path)


def fake_gh(calls, *, create_rc=0, url="https://github.com/o/r/pull/7", view_url=""):
    def run(argv):
        calls.append(argv)
        if argv[1] == "pr" and argv[2] == "create":
            return sp.CompletedProcess(argv, create_rc, url + "\n", "already exists")
        return sp.CompletedProcess(argv, 0, view_url + "\n", "")

    return run


def test_the_pr_is_a_draft_and_always_carries_a_title(tmp_path):
    """Without --title and without --fill, `gh` prompts — unattended that hangs."""
    body = tmp_path / "body.md"
    body.write_text("## body\n")
    calls = []
    url = open_draft_pr(
        slug="o/r",
        branch="saffron/SA-0005",
        base="main",
        title="SA-0005 package",
        body_path=body,
        gh=fake_gh(calls),
    )
    assert url == "https://github.com/o/r/pull/7"
    argv = calls[0]
    assert "--draft" in argv
    assert "--title" in argv
    assert "--body-file" in argv


def test_a_second_package_reports_the_existing_pr(tmp_path):
    """§4.2's CHANGES_REQUESTED re-queue path: the push already updated it."""
    body = tmp_path / "body.md"
    body.write_text("## body\n")
    calls = []
    url = open_draft_pr(
        slug="o/r",
        branch="saffron/SA-0005",
        base="main",
        title="SA-0005 package",
        body_path=body,
        gh=fake_gh(calls, create_rc=1, view_url="https://github.com/o/r/pull/3"),
    )
    assert url == "https://github.com/o/r/pull/3"
    assert calls[1][2] == "view"


def test_a_missing_gh_is_infrastructure_and_says_the_branch_is_pushed(tmp_path):
    body = tmp_path / "body.md"
    body.write_text("## body\n")

    def missing(argv):
        raise FileNotFoundError("gh")

    with pytest.raises(PackageError, match="already pushed"):
        open_draft_pr(
            slug="o/r",
            branch="saffron/SA-0005",
            base="main",
            title="t",
            body_path=body,
            gh=missing,
        )


def test_a_silent_gh_is_infrastructure_and_says_the_branch_is_pushed(tmp_path):
    """Exit 0 with nothing on stdout: a bare IndexError at the one moment the
    branch is pushed and nothing about it is recorded."""
    body = tmp_path / "body.md"
    body.write_text("## body\n")

    with pytest.raises(PackageError, match="already pushed"):
        open_draft_pr(
            slug="o/r",
            branch="saffron/SA-0005",
            base="main",
            title="t",
            body_path=body,
            gh=lambda argv: sp.CompletedProcess(argv, 0, "  \n", ""),
        )


def test_an_unmoved_base_makes_reverification_provably_redundant():
    """If the default branch head still equals base_sha, the packaged tree is
    byte-identical to the one the suite already ran on. Skipping is not a
    shortcut — re-running could not produce a different answer."""
    assert not needs_reverification("a" * 40, "a" * 40)


def test_a_moved_base_requires_reverification():
    """Otherwise the gate table would publish `pass` for a suite that ran
    against base_sha's tree, on a commit whose tree is today's main plus the
    patch — the tool-field defect of §5.4 in a new costume."""
    assert needs_reverification("b" * 40, "a" * 40)


def _cell_outcome(task_dir, task_id, run_id):
    return SimpleNamespace(
        state="READY_FOR_REVIEW",
        task_id=task_id,
        run_id=run_id,
        task_dir=task_dir,
        spent_usd=6.4,
        attempts=1,
        cell_head_sha="c" * 40,
        gates=[],
        new_failures=[],
        reviews=[],
        rebut_result=None,
        agent_subjects=[],
    )


def test_a_conflict_persists_merge_failed_and_pushes_nothing(tmp_path):
    """Asserting the state alone would pass against an implementation that
    pushed conflict markers first, so this asserts the remote too."""
    # A "real remote", and a local repo whose origin points at it.
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "Test")
    (work / "f.txt").write_text("a\nb\nc\nd\ne\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    base = git(work, "rev-parse", "HEAD")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-q", "origin", "main")

    # The cell's patch touches line 3. Exported the way `worktree.export_patch`
    # does — a hand-written hunk carries no index line, and --3way then has no
    # blob to merge against.
    git(work, "checkout", "-q", "-b", "cell")
    (work / "f.txt").write_text("a\nb\nCELL\nd\ne\n")
    git(work, "commit", "-qam", "the agent's work")
    patch_text = git(work, "diff", *DIFF_FLAGS, f"{base}..HEAD") + "\n"
    git(work, "checkout", "-q", "main")

    # ... and main moves into the same line.
    (work / "f.txt").write_text("a\nb\nMAIN_TOOK_IT\nd\ne\n")
    git(work, "commit", "-qam", "main moved")
    git(work, "push", "-q", "origin", "main")

    mirror = tmp_path / "m.git"
    git(tmp_path, "clone", "-q", "--mirror", str(work), str(mirror))

    task_dir = tmp_path / "batch" / "SA-0005"
    task_dir.mkdir(parents=True)
    (task_dir / "patch.diff").write_text(patch_text)
    (task_dir / "patch.json").write_text(json.dumps({"base_sha": base}))

    ledger = Ledger(tmp_path / "l.db")
    repo_id = ledger.upsert_repo("work", str(remote), str(mirror), "sha")
    run_id = ledger.create_run(repo_id, base)
    task_id = ledger.create_task(run_id, "SA-0005", "s" * 40, branch="saffron/SA-0005")
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    ledger.finish_run(run_id, "COMPLETE")

    outcome = _cell_outcome(task_dir, task_id, run_id)
    spec = SimpleNamespace(
        id="SA-0005",
        title="package a green cell",
        risk="standard",
        touches=[],
        acceptance_criteria=[],
        type="feature",
    )
    policy = SimpleNamespace(integrity=SimpleNamespace(test_paths=["tests/**"]))

    def never_called(argv):
        raise AssertionError("gh must not be reached on a conflict")

    result = package(
        outcome,
        spec=spec,
        repo=work,
        mirror=mirror,
        policy=policy,
        image="unused",
        ledger=ledger,
        out_dir=tmp_path / "batch",
        token=None,
        gh=never_called,
        watch=lambda _: None,
    )

    assert result.state == "MERGE_FAILED"
    row = next(r for r in ledger.queue_lines() if r["task_id"] == task_id)
    assert row["state"] == "MERGE_FAILED"
    # The remote must be untouched — the assertion the state alone cannot make.
    assert remote_sha(str(remote), "saffron/SA-0005", cwd=tmp_path) == ""
    # And the scratch worktree is gone, on this path as on every other.
    assert not (tmp_path / "batch" / "package" / "SA-0005").exists()
    assert (tmp_path / "batch" / "index.html").is_file()
    ledger.close()


@pytest.fixture
def packageable(tmp_path):
    """A green cell's patch, a mirror, and a remote whose default branch has
    not moved — so PACKAGE runs its whole path and re-verification is provably
    redundant (no cell, no container, anywhere in these tests)."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "Test")
    (work / "f.txt").write_text("a\nb\nc\nd\ne\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    base = git(work, "rev-parse", "HEAD")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-q", "origin", "main")

    git(work, "checkout", "-q", "-b", "cell")
    # One line out, two in: +2/−1 tells a swapped pair of counts from a right one.
    (work / "f.txt").write_text("a\nb\nCELL\nMORE\nd\ne\n")
    git(work, "commit", "-qam", "the agent's work")
    patch_text = git(work, "diff", *DIFF_FLAGS, f"{base}..HEAD") + "\n"
    git(work, "checkout", "-q", "main")

    mirror = tmp_path / "m.git"
    git(tmp_path, "clone", "-q", "--mirror", str(work), str(mirror))
    # A mirror inherits no identity, and `commit_squash` runs in its worktree.
    git(mirror, "config", "user.email", "t@example.com")
    git(mirror, "config", "user.name", "Test")

    task_dir = tmp_path / "batch" / "SA-0005"
    task_dir.mkdir(parents=True)
    (task_dir / "patch.diff").write_text(patch_text)
    (task_dir / "patch.json").write_text(json.dumps({"base_sha": base}))

    ledger = Ledger(tmp_path / "l.db")
    repo_id = ledger.upsert_repo("work", str(remote), str(mirror), "sha")
    run_id = ledger.create_run(repo_id, base)
    task_id = ledger.create_task(run_id, "SA-0005", "s" * 40, branch="saffron/SA-0005")
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    ledger.finish_run(run_id, "COMPLETE")

    yield SimpleNamespace(
        work=work,
        remote=remote,
        mirror=mirror,
        base=base,
        ledger=ledger,
        task_id=task_id,
        out_dir=tmp_path / "batch",
        kwargs=dict(
            spec=SimpleNamespace(
                id="SA-0005",
                title="package a green cell",
                risk="standard",
                touches=["f.txt"],
                acceptance_criteria=["it works"],
                type="feature",
            ),
            repo=work,
            mirror=mirror,
            policy=SimpleNamespace(integrity=SimpleNamespace(test_paths=["tests/**"])),
            image="unused",
            ledger=ledger,
            out_dir=tmp_path / "batch",
            token=None,
            watch=lambda _: None,
        ),
        outcome=_cell_outcome(task_dir, task_id, run_id),
    )
    ledger.close()


def _state(ledger, task_id):
    return next(r for r in ledger.queue_lines() if r["task_id"] == task_id)


def test_a_green_cell_becomes_a_branch_a_draft_pr_and_a_queue_line(packageable):
    """§5.7 end to end, with the remote a bare repo and `gh` injected."""
    seen = []

    def fake_gh(argv):
        seen.append(argv)
        return sp.CompletedProcess(argv, 0, stdout="https://github.com/o/r/pull/1\n")

    result = package(packageable.outcome, gh=fake_gh, **packageable.kwargs)

    assert result.state == "READY_FOR_REVIEW"
    assert result.pr_url == "https://github.com/o/r/pull/1"
    pushed = remote_sha(
        str(packageable.remote), "saffron/SA-0005", cwd=packageable.work
    )
    assert pushed == result.pushed_sha
    assert "--draft" in seen[0]

    row = _state(packageable.ledger, packageable.task_id)
    assert (row["state"], row["pushed_sha"], row["pr_url"]) == (
        "READY_FOR_REVIEW",
        pushed,
        "https://github.com/o/r/pull/1",
    )
    # The counts are measured, not zero: the PR header and the queue line are
    # the two artifacts this phase exists to produce.
    assert (result.added, result.removed) == (2, 1)
    body = (packageable.outcome.task_dir / "pr_body.md").read_text()
    index = (packageable.out_dir / "index.html").read_text()
    assert "+2/−1" in body and "+2/−1" in index
    assert "SA-0005" in index


def test_the_bodys_diff_is_pinned_against_the_operators_gitconfig(packageable):
    """`diff.noprefix` is a global anyone may set, and it rewrites every path
    the host parses out of the diff. Without `DIFF_FLAGS`, §7's gate-gaming
    countermeasure renders an empty section and says nothing about why."""
    git(packageable.mirror, "config", "diff.noprefix", "true")
    # The one file this patch touches, declared as a test path, so the section
    # has something to render.
    packageable.kwargs["policy"] = SimpleNamespace(
        integrity=SimpleNamespace(test_paths=["f.txt"])
    )

    result = package(
        packageable.outcome,
        gh=lambda argv: sp.CompletedProcess(argv, 0, stdout="https://x/pull/1\n"),
        **packageable.kwargs,
    )

    assert result.state == "READY_FOR_REVIEW"
    body = (packageable.outcome.task_dir / "pr_body.md").read_text()
    assert "### Test files changed" in body
    assert "diff --git a/f.txt b/f.txt" in body


def test_a_branch_that_moved_is_the_tasks_failure(monkeypatch, packageable):
    """LeaseRejected only: the branch really did move, so MERGE_FAILED (1)."""
    git(
        packageable.work,
        "push",
        "-q",
        str(packageable.remote),
        "cell:refs/heads/saffron/SA-0005",
    )
    # An empty lease against a branch that exists is git's own `stale info`.
    monkeypatch.setattr("saffron.phases.package.remote_sha", lambda *a, **k: "")

    result = package(packageable.outcome, gh=_no_gh, **packageable.kwargs)

    assert result.state == "MERGE_FAILED" and result.pushed_sha == ""
    assert _state(packageable.ledger, packageable.task_id)["state"] == "MERGE_FAILED"


def test_a_push_that_broke_is_infrastructure_and_records_nothing(
    monkeypatch, packageable
):
    """An auth or transport failure is `error`, not `fail`. Recorded as
    MERGE_FAILED it would tell the operator their change conflicts with main
    when the real problem is their credentials."""

    def _broke(*_a, **_k):
        raise PackageError("Permission denied (publickey)")

    monkeypatch.setattr("saffron.phases.package.push_with_lease", _broke)

    with pytest.raises(PackageError, match="publickey"):
        package(packageable.outcome, gh=_no_gh, **packageable.kwargs)

    # Neither the state nor the queue moved: the run's own word still stands.
    assert (
        _state(packageable.ledger, packageable.task_id)["state"] == "READY_FOR_REVIEW"
    )
    assert not (packageable.out_dir / "index.html").exists()


def test_a_gate_that_errored_while_re_verifying_aborts_the_package(
    monkeypatch, packageable
):
    """`reverify` raises on an errored gate. A broken gate is not a merge
    conflict, and netting it to MERGE_FAILED would charge the task for the
    toolchain (§5.4)."""
    # Move the default branch, so re-verification is not redundant.
    (packageable.work / "other.txt").write_text("main moved\n")
    git(packageable.work, "add", "-A")
    git(packageable.work, "commit", "-qm", "main moved")
    git(packageable.work, "push", "-q", "origin", "main")

    def _errored(**_k):
        raise PackageError("baseline suite: types errored rather than ran")

    monkeypatch.setattr("saffron.phases.package.reverify", _errored)

    with pytest.raises(PackageError, match="errored rather than ran"):
        package(packageable.outcome, gh=_no_gh, **packageable.kwargs)

    assert (
        _state(packageable.ledger, packageable.task_id)["state"] == "READY_FOR_REVIEW"
    )
    assert (
        remote_sha(str(packageable.remote), "saffron/SA-0005", cwd=packageable.work)
        == ""
    )
    # The `finally` runs on a raise path too, not only on the conflict return.
    assert not (packageable.out_dir / "package" / "SA-0005").exists()


def test_new_failures_after_the_rebase_are_the_tasks_failure(monkeypatch, packageable):
    """The base moved and the packaged tree fails on it: MERGE_FAILED, and
    nothing reaches the remote — there is no `pushed_sha` to record."""
    (packageable.work / "other.txt").write_text("main moved\n")
    git(packageable.work, "add", "-A")
    git(packageable.work, "commit", "-qm", "main moved")
    git(packageable.work, "push", "-q", "origin", "main")

    monkeypatch.setattr(
        "saffron.phases.package.reverify",
        lambda **_k: (
            [NewFailure(gate="tests", failure=Failure(file="f.py", code="E"))],
            [],
        ),
    )

    result = package(packageable.outcome, gh=_no_gh, **packageable.kwargs)

    assert result.state == "MERGE_FAILED" and result.pushed_sha == ""
    assert "1 new failures after rebase" in result.note
    assert _state(packageable.ledger, packageable.task_id)["pushed_sha"] == ""
    assert (
        remote_sha(str(packageable.remote), "saffron/SA-0005", cwd=packageable.work)
        == ""
    )


def _no_gh(argv):
    raise AssertionError("gh must not be reached")


def test_the_squash_commits_with_no_git_identity_anywhere(tmp_path, monkeypatch):
    """A --mirror clone inherits no identity, so an unattended batch on a fresh
    host would fail every package after doing all the work. Proven with every
    config file git could read pointed at nothing."""
    empty = tmp_path / "empty-home"
    empty.mkdir()
    monkeypatch.setenv("HOME", str(empty))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(empty))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")

    repo = tmp_path / "no-identity"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "f.txt").write_text("x\n")
    git(repo, "add", "-A")
    # Even the seed commit has to bring its own; nothing is written to config.
    git(repo, "-c", "user.email=s@x", "-c", "user.name=S", "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "f.txt").write_text("y\n")
    git(repo, "add", "-A")

    sha = commit_squash(
        repo,
        spec_id="SA-0005",
        title="package a green cell",
        base_sha=base,
        cell_head=None,
        attempts=1,
        spent_usd=1.0,
        agent_subjects=[],
    )

    # The cell commits as this identity too (`worktree.prepare_worktree`), so
    # host-side and cell-side agree on who Saffron is.
    assert (
        git(repo, "log", "-1", "--format=%an <%ae>", sha)
        == "Saffron <saffron@localhost>"
    )
    # Still unset: the identity was passed, never written down.
    assert (
        subprocess.run(
            ["git", "-C", str(repo), "config", "--get", "user.email"],
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 1
    )


# Obviously fake, and never a real token: the shape is what the scan matches.
FAKE_KEY = "sk-ant-api03-" + "0123456789abcdef" * 2


def test_a_credential_in_the_patch_is_refused_before_anything_is_pushed(packageable):
    """The one guard between a model-authored patch and a secret on a public
    remote, where it is effectively undeletable. Every other e2e test passes
    `token=None` over a clean patch, so without this the block could be deleted
    and the suite would stay green."""
    work = packageable.work
    git(work, "checkout", "-q", "cell")
    (work / "config.py").write_text(f'ANTHROPIC_API_KEY = "{FAKE_KEY}"\n')
    git(work, "add", "-A")
    git(work, "commit", "-qm", "the agent hardcoded a key")
    patch = packageable.outcome.task_dir / "patch.diff"
    patch.write_text(git(work, "diff", *DIFF_FLAGS, f"{packageable.base}..HEAD") + "\n")
    git(work, "checkout", "-q", "main")

    result = package(packageable.outcome, gh=_no_gh, **packageable.kwargs)

    assert result.state == "MERGE_FAILED"
    assert "credential in the patch" in result.note
    assert "config.py" in result.note  # it says where, so it can be fixed
    # Load-bearing: the refusal is worth nothing if the push happened first.
    assert remote_sha(str(packageable.remote), "saffron/SA-0005", cwd=work) == ""

    # Naming a leak must never reprint it — not in the note, the ledger, or the
    # rendered queue.
    row = _state(packageable.ledger, packageable.task_id)
    assert row["state"] == "MERGE_FAILED"
    artifacts = [
        result.note,
        str(dict(row)),
        (packageable.out_dir / "index.html").read_text(),
        (packageable.out_dir / "queue.json").read_text(),
    ]
    assert not any(FAKE_KEY in text for text in artifacts)


def test_an_empty_diff_is_named_rather_than_a_traceback(packageable):
    """An agent that committed nothing exports neither file (§5.7). Reading
    `patch.json` first turned the named outcome into a FileNotFoundError."""
    (packageable.outcome.task_dir / "patch.diff").unlink()
    (packageable.outcome.task_dir / "patch.json").unlink()

    with pytest.raises(PackageError, match="nothing to package"):
        package(packageable.outcome, gh=_no_gh, **packageable.kwargs)


def test_a_credential_in_an_agent_commit_subject_is_refused(packageable):
    """The third channel: `commit_squash` renders the agent's own subjects into
    the squashed body, and no PR-body section shows them — so neither the patch
    scan nor the body scan sees one."""
    packageable.outcome.agent_subjects = [f"fix: use {FAKE_KEY}"]

    result = package(packageable.outcome, gh=_no_gh, **packageable.kwargs)

    assert result.state == "MERGE_FAILED"
    assert "credential in the commit subjects" in result.note
    assert (
        remote_sha(str(packageable.remote), "saffron/SA-0005", cwd=packageable.work)
        == ""
    )
    assert not any(
        FAKE_KEY in text
        for text in (
            result.note,
            str(dict(_state(packageable.ledger, packageable.task_id))),
            (packageable.out_dir / "index.html").read_text(),
        )
    )


def test_a_credential_in_a_finding_is_refused_before_anything_is_pushed(packageable):
    """The body is the cell's second channel to the remote: a claim, a rebuttal
    argument and a verdict reason all reach GitHub without ever being in the
    diff, and the diff is all `find_credentials` used to see."""
    packageable.outcome.reviews = [
        LensReview(
            lens="correctness",
            findings=[
                Finding(
                    lens="correctness",
                    severity="concern",
                    file="f.txt",
                    line=3,
                    claim=f"the key {FAKE_KEY} is hardcoded here",
                    anchored=True,
                )
            ],
        )
    ]

    result = package(packageable.outcome, gh=_no_gh, **packageable.kwargs)

    assert result.state == "MERGE_FAILED"
    assert "credential in the body" in result.note
    # The same refusal, so the push never happened.
    assert (
        remote_sha(str(packageable.remote), "saffron/SA-0005", cwd=packageable.work)
        == ""
    )
    assert not any(
        FAKE_KEY in text
        for text in (
            result.note,
            str(dict(_state(packageable.ledger, packageable.task_id))),
            (packageable.out_dir / "index.html").read_text(),
        )
    )


def test_an_added_line_that_starts_with_a_plus_is_still_scanned():
    """`+++` is a file header only outside a hunk. An added `++counter` reaches
    the scanner as `+++counter`, and a patch quoted in a test fixture makes
    every line it carries one — recognising the prefix alone hid all of them
    from §5.7's refusal, which is the only thing keeping the cell's token off
    the real remote."""
    token = "sk-ant-oat01-EXAMPLE-NOT-REAL-0000"
    patch = (
        "diff --git a/tests/fixtures.py b/tests/fixtures.py\n"
        "--- a/tests/fixtures.py\n"
        "+++ b/tests/fixtures.py\n"
        "@@ -1,1 +1,3 @@\n"
        " PATCH = '''\n"
        # Three `+`: the added-line marker, and content that is itself a
        # patch line. `+++counter` is the added line `++counter`.
        f'+++TOKEN = "{token}"\n'
        "+++counter\n"
    )
    found = find_credentials(patch, token=token)
    assert found
    assert token not in " ".join(found)
    assert "tests/fixtures.py" in " ".join(found)


def test_an_added_line_shaped_like_a_header_does_not_re_point_the_path():
    """An added `++ b/decoy.py` renders as `+++ b/decoy.py`. Read as a header it
    renamed the file every later hit was attributed to."""
    patch = (
        "diff --git a/real.py b/real.py\n"
        "+++ b/real.py\n"
        "@@ -1,1 +1,2 @@\n"
        # The added line `++ b/decoy.py`, not a file header.
        "+++ b/decoy.py\n"
        "+key = 'AKIAAAAAAAAAAAAAAAAA'\n"
    )
    found = find_credentials(patch, token=None)
    assert found and "real.py" in " ".join(found)
    assert "decoy.py" not in " ".join(found)


# Every character `str.splitlines()` breaks on and git does not. Any one of
# them inside an added line shatters it, and the fragment carrying the secret
# loses its `+` — dropping out of the scan that is the last check before a
# cell-authored patch reaches a real remote.
_NOT_A_LINE_TERMINATOR = [
    pytest.param("\x0b", id="VT"),
    pytest.param("\x0c", id="FF"),
    pytest.param("\x1c", id="FS"),
    pytest.param("\x1d", id="GS"),
    pytest.param("\x1e", id="RS"),
    pytest.param("\x85", id="NEL"),
    pytest.param("\u2028", id="LS"),
    pytest.param("\u2029", id="PS"),
    pytest.param("\r", id="CR"),
]


@pytest.mark.parametrize("separator", _NOT_A_LINE_TERMINATOR)
def test_a_byte_inside_an_added_line_cannot_hide_the_token_from_the_patch_scan(
    separator,
):
    """Measured: with `splitlines()` every one of these returned `leaked=[]`
    for a patch that pushes the cell's own OAuth token."""
    token = "sk-ant-oat01-EXAMPLE-NOT-REAL-0000"
    patch = (
        "diff --git a/cfg.py b/cfg.py\n"
        "--- a/cfg.py\n"
        "+++ b/cfg.py\n"
        "@@ -1,1 +1,2 @@\n"
        f'+TOKEN = "{separator}{token}"\n'
    )
    found = find_credentials(patch, token=token)
    assert found
    assert token not in " ".join(found)
    assert "cfg.py" in " ".join(found)


@pytest.mark.parametrize("separator", _NOT_A_LINE_TERMINATOR)
def test_prose_is_split_the_way_git_wrote_it_so_the_token_stays_whole(separator):
    """A claim, a rebuttal and a verdict reason are cell-authored, and the PR
    body carries them to the remote.

    The shaped-credential regexes cannot match across a separator either way,
    so the difference here is narrower than `_added_lines`': the literal-token
    check is a *substring* test, and a splitter that shatters the line first
    hands it two halves of the one secret the host knows is in the cell.
    """
    token = f"sk-ant-oat01-EXAMPLE{separator}NOT-REAL-0000"
    text = f"I set the header to {token} and it worked."
    found = find_credentials_in_text(text, token=token, where="claim")
    assert found == ["claim: the cell's own CLAUDE_CODE_OAUTH_TOKEN"]


def test_a_branch_that_cannot_be_created_is_infrastructure(packageable):
    """The one git call here that went unchecked. A `refs/heads/saffron` blocks
    the `saffron/SA-0005` path; unchecked, the squash lands on a detached HEAD
    that no `refs/heads/*` reaches — and `reverify`'s fetch cannot check out."""
    git(packageable.mirror, "branch", "saffron", "main")

    with pytest.raises(PackageError, match="cannot create saffron/SA-0005"):
        package(packageable.outcome, gh=_no_gh, **packageable.kwargs)

    assert (
        remote_sha(str(packageable.remote), "saffron/SA-0005", cwd=packageable.work)
        == ""
    )


def test_a_re_verified_body_shows_the_gates_that_re_ran(monkeypatch, packageable):
    """`_verification` says the gates ran on the packaged commit, so the table
    below it must be that run — not the cell's results at `base_sha`."""
    (packageable.work / "other.txt").write_text("main moved\n")
    git(packageable.work, "add", "-A")
    git(packageable.work, "commit", "-qm", "main moved")
    git(packageable.work, "push", "-q", "origin", "main")

    packageable.outcome.gates = [
        GateResult(
            gate="tests", status="pass", tool="pytest 1.0", summary="ran at base"
        )
    ]
    repackaged = GateResult(
        gate="tests", status="pass", tool="pytest 9.9.9", summary="ran on the package"
    )
    monkeypatch.setattr(
        "saffron.phases.package.reverify", lambda **_k: ([], [repackaged])
    )

    package(
        packageable.outcome,
        gh=lambda argv: sp.CompletedProcess(argv, 0, stdout="https://x/pull/1\n"),
        **packageable.kwargs,
    )

    body = (packageable.outcome.task_dir / "pr_body.md").read_text()
    assert "packaged commit" in body
    assert "ran on the package" in body
    # The cell's run at `base_sha` must not be the one shown.
    assert "ran at base" not in body
