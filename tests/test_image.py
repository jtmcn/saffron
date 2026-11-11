from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron.cell import runtime
from saffron.phases import implement
from saffron.repos import image


def test_build_argv_names_the_dockerfile_and_tag(tmp_path):
    argv = image._build_argv(tmp_path / "D", "saffron/cell-base:python", tmp_path)
    assert argv[:2] == ["container", "build"]
    assert "-t" in argv and "saffron/cell-base:python" in argv
    assert "-f" in argv and str(tmp_path / "D") in argv
    assert argv[-1] == str(tmp_path)


@pytest.mark.cell
def test_base_image_has_git_and_the_agent_runtime():
    done = runtime.run_ephemeral(image.BASE_TAG, ["git", "--version"])
    assert done.returncode == 0, done.stderr
    done = runtime.run_ephemeral(
        image.BASE_TAG, ["python", "-c", "import claude_agent_sdk"]
    )
    assert done.returncode == 0, done.stderr


@pytest.mark.cell
def test_the_runner_has_an_interpreter_with_the_sdk_inside_a_repos_own_image():
    """The trap the base image alone cannot show: a repo's image puts its venv
    first on PATH, and `python` there has no claude_agent_sdk."""
    tag = image.build_cell_image(Path(__file__).resolve().parents[1])
    done = runtime.run_ephemeral(
        tag, [implement.PYTHON, "-c", "import claude_agent_sdk"]
    )
    assert done.returncode == 0, done.stderr


def _visible_cpus(tag: str, cpus: int) -> int:
    """What `nproc` reports inside a cell allocated `cpus`."""
    done = runtime.run_ephemeral(tag, ["nproc"], cpus=cpus, timeout_s=120)
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"nproc failed in {tag}: {done.stderr.strip()}")
    return int(done.stdout.strip().splitlines()[-1])


@pytest.mark.cell
def test_the_cell_sees_only_the_cpus_it_has():
    """The requirement §5.1 states, with the offset Appendix G measured."""
    assert _visible_cpus(image.BASE_TAG, 1) == 1 + runtime.CPU_OFFSET


def test_the_cell_image_is_named_for_the_repo(tmp_path):
    """A cell runs `saffron/cell:<repo>` (§5.1), never the toolchain-free base."""
    assert image.cell_tag(tmp_path / "thermal-edge") == "saffron/cell:thermal-edge"
    # A worktree directory name is not a legal tag.
    assert image.cell_tag(tmp_path / "joel+v0.5") == "saffron/cell:joel-v0.5"


def test_building_a_cell_image_without_a_dockerfile_is_an_error(tmp_path):
    with pytest.raises(runtime.CellRuntimeError):
        image.build_cell_image(tmp_path)


def _record_builds(monkeypatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def _call(argv, timeout_s):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(runtime, "call", _call)
    return calls


def test_a_cell_image_build_rebuilds_the_base_first(monkeypatch, tmp_path):
    """A base built by hand once went stale: SA-0090's token fields in
    `agent_runner.py` reached no cell for three weeks (backlog b-5e443c)."""
    (tmp_path / ".saffron").mkdir()
    (tmp_path / ".saffron" / "Dockerfile").write_text("FROM saffron/cell-base:python\n")
    monkeypatch.delenv("SAFFRON_BASE_IMAGE", raising=False)
    calls = _record_builds(monkeypatch)
    image.build_cell_image(tmp_path)
    tags = [argv[argv.index("-t") + 1] for argv in calls]
    assert tags == [image.BASE_TAG, image.cell_tag(tmp_path)]
    base = calls[0]
    dockerfile = Path(base[base.index("-f") + 1])
    assert dockerfile.name == "cell-base.python.Dockerfile" and dockerfile.is_file()
    assert not any(a.startswith("--build-arg") for a in base)


def test_a_declared_base_image_reaches_the_base_build(monkeypatch, tmp_path):
    """A host with no registry names its own base (§5.1.2)."""
    (tmp_path / ".saffron").mkdir()
    (tmp_path / ".saffron" / "Dockerfile").write_text("FROM saffron/cell-base:python\n")
    monkeypatch.setenv(image.BASE_IMAGE_ENV, "local/debootstrap:24.04")
    calls = _record_builds(monkeypatch)
    image.build_cell_image(tmp_path)
    assert "--build-arg=BASE_IMAGE=local/debootstrap:24.04" in calls[0]
    assert not any(a.startswith("--build-arg") for a in calls[1])


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@pytest.fixture
def isolated_git(monkeypatch):
    """No host git config reaches these repos, as SA-0255's witnesses do."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _repo(path: Path, origin: str | None) -> Path:
    """A committed repo at `path` with a `.saffron/Dockerfile`, and `origin`."""
    (path / ".saffron").mkdir(parents=True)
    (path / ".saffron" / "Dockerfile").write_text("FROM saffron/cell-base:python\n")
    _git(path, "init", "-q")
    _git(path, "add", "-A")
    _git(path, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "seed")
    if origin is not None:
        _git(path, "remote", "add", "origin", origin)
    return path


def test_two_git_worktrees_of_one_repo_build_one_cell_image(
    monkeypatch, tmp_path, isolated_git
):
    """Two worktrees and their checkout build one cell image, and a second
    repo builds its own (b-2bc0d5)."""
    store: set[str] = set()

    def _call(argv, timeout_s):
        store.add(argv[argv.index("-t") + 1])
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(runtime, "call", _call)
    main = _repo(tmp_path / "saffron", "https://github.com/o/thermal-edge.git")
    for name in ("joel+one", "wt-two"):
        _git(main, "worktree", "add", "-q", str(tmp_path / name))
        image.build_cell_image(tmp_path / name)
    image.build_cell_image(main)
    assert {t for t in store if t.startswith("saffron/cell:")} == {
        "saffron/cell:thermal-edge"
    }

    other = _repo(tmp_path / "other", "https://github.com/o/lattice.git")
    image.build_cell_image(other)
    assert {t for t in store if t.startswith("saffron/cell:")} == {
        "saffron/cell:thermal-edge",
        "saffron/cell:lattice",
    }


def test_the_cell_tag_reads_the_repo_name_from_every_origin_form(
    tmp_path, isolated_git
):
    """Each URL shape git writes names the same image. A name a tag cannot
    carry is made legal, and a checkout with no origin keeps its own name."""
    forms = [
        "https://github.com/o/thermal-edge.git",
        "https://github.com/o/thermal-edge",
        "https://github.com/o/thermal-edge/",
        "git@github.com:o/thermal-edge.git",
        "git@host:thermal-edge.git",
        "ssh://git@github.com/o/thermal-edge.git",
        "/srv/git/thermal-edge.git",
        "/srv/git/thermal-edge.git/",
        "file:///srv/git/thermal-edge",
    ]
    for n, origin in enumerate(forms):
        repo = _repo(tmp_path / f"checkout-{n}", origin)
        assert image.cell_tag(repo) == "saffron/cell:thermal-edge", origin
    audit = _repo(tmp_path / "plain-audit", "https://github.com/o/audit.git")
    assert image.cell_tag(audit) == "saffron/cell:audit"
    pages = _repo(tmp_path / "plain-pages", "https://github.com/o/o.github.io.git")
    assert image.cell_tag(pages) == "saffron/cell:o.github.io"
    for n, origin in enumerate(["/srv/git/repo/.git", "https://host/o/.git"]):
        empty = _repo(tmp_path / f"empty-{n}" / "checkout", origin)
        assert image.cell_tag(empty) == "saffron/cell:checkout", origin
    odd = _repo(tmp_path / "plain", "/srv/git/joel+v0.5.git")
    assert image.cell_tag(odd) == "saffron/cell:joel-v0.5"
    lone = _repo(tmp_path / "lone", None)
    assert image.cell_tag(lone) == "saffron/cell:lone"
