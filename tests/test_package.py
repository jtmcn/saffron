import subprocess

import pytest

from saffron.phases.package import (
    APPLY_CONFLICT,
    APPLY_OK,
    PackageError,
    apply_patch,
    assert_base_objects,
    default_branch,
    find_credentials,
    github_slug,
    neutralize,
    real_remote,
)


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
