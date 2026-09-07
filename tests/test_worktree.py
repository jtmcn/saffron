from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from saffron.cell import proxy, runtime, worktree
from saffron.gates.runner import CellExecutor, run_gate
from saffron.intake import Mutant
from saffron.phases import package as package_phase
from saffron.repos import image
from saffron.repos import mirror as mirror_ops
from tests.test_proxy import reach

NETWORK = "saffron-test-wt-cells"


@pytest.fixture
def network():
    runtime.remove_network(NETWORK)
    runtime.create_network(NETWORK)
    yield NETWORK
    runtime.remove_network(NETWORK)


def _gates_dir(tmp_path):
    """A real export dir: the bind mount's source has to exist, and it holds a
    real gate so a refused write is distinguishable from a missing path."""
    dest = tmp_path / "gates-out"
    gates = dest / ".saffron" / "gates"
    gates.mkdir(parents=True, exist_ok=True)
    (gates / "tests").write_text("#!/bin/sh\nexit 0\n")
    (gates / "tests").chmod(0o755)
    return dest


def test_mounts_carry_the_gates_read_only():
    got = worktree.mounts("vol", "state-vol", Path("/host/gates-out"))
    gates = [m for m in got if m.target == worktree.GATES_MOUNT]
    assert len(gates) == 1
    assert gates[0].kind == "bind"
    assert gates[0].source == "/host/gates-out"
    # A writable gate mount is the hole this whole task closes.
    assert gates[0].readonly is True
    assert "readonly" in gates[0].to_flag()


def test_prepare_worktree_requires_a_gates_dir():
    """Required, not defaulted — the Appendix I lesson, in a third place."""
    # Through a deliberately untyped alias: omitting `gates_dir` is the subject
    # of this test, so `types` would otherwise report the test for
    # demonstrating the very thing it asserts.
    prepare: Any = worktree.prepare_worktree
    with pytest.raises(TypeError):
        prepare(
            mirror=Path("/m"),
            volume="v",
            base_sha="abc",
            branch="b",
            image="i",
            container="c",
            network="none",
            env={},
        )


def _seed_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(a, cwd=path, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    (path / "a.txt").write_text("one\n")
    run("git", "add", "a.txt")
    run("git", "commit", "-qm", "first")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True
    ).stdout.strip()


@pytest.mark.cell
def test_a_worktree_is_cloned_into_a_volume_and_the_cell_can_commit(tmp_path, network):
    origin = tmp_path / "origin"
    base = _seed_repo(origin)
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )

    volume = "saffron-test-wt"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    container = "saffron-test-cell"
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
            network=network,
            env={},
            gates_dir=_gates_dir(tmp_path),
        )
        assert worktree.commits_ahead(container, base) == 0

        runtime.exec_(container, ["sh", "-c", "echo two >> a.txt"], workdir="/work")
        runtime.exec_(container, ["git", "add", "a.txt"], workdir="/work")
        runtime.exec_(container, ["git", "commit", "-qm", "second"], workdir="/work")

        assert worktree.commits_ahead(container, base) == 1
        patch = worktree.export_patch(container, base)
        assert "two" in patch
        # The squash body's only record of what the agent actually committed.
        assert worktree.commit_subjects(container, base) == ["second"]

        # Probed from inside the cell, not read off the mount flag (Appendix I).
        # The gate the suite execs is at the second path; the baseline and every
        # head suite run in this one cell, so a mount that ignored `readonly`
        # would let the agent swap the judge between them.
        gate = f"{worktree.GATES_MOUNT}/.saffron/gates/tests"
        readable = runtime.exec_(container, ["cat", gate])
        # First, so the refusals below are refusals and not a missing path.
        assert readable.returncode == 0, readable.stderr
        for target in (f"{worktree.GATES_MOUNT}/x", gate):
            refused = runtime.exec_(container, ["sh", "-c", f"echo pwned > {target}"])
            assert refused.returncode != 0, f"{target} accepted a write"
            assert "read-only" in refused.stderr.lower(), refused.stderr
        assert runtime.exec_(container, ["cat", gate]).stdout == readable.stdout
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


@pytest.mark.cell
def test_a_gate_edited_inside_the_cell_never_runs(tmp_path, network):
    """The read-only mount (above) is only half the claim. The other half is
    that `run_gate` actually executes the host-exported gate rather than
    whatever the worktree now holds, even after the cell commits a lying one
    at the identical path (§5.4)."""
    origin = tmp_path / "origin"
    base = _seed_repo(origin)
    gates = origin / ".saffron" / "gates"
    gates.mkdir(parents=True)
    (gates / "demo").write_text(
        '#!/bin/sh\nprintf \'{"gate":"demo","status":"pass","tool":"honest 1.0"}\\n\'\n'
    )
    (gates / "demo").chmod(0o755)
    subprocess.run(["git", "add", "-A"], cwd=origin, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-qm", "add demo gate"],
        cwd=origin,
        check=True,
        capture_output=True,
    )
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=origin, capture_output=True, text=True
    ).stdout.strip()

    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    gates_dir = mirror_ops.export_saffron_dir(mirror, base, tmp_path / "gates-out")

    volume, container = "saffron-test-wt4", "saffron-test-cell4"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
            network=network,
            env={},
            gates_dir=gates_dir,
        )

        # The agent's move: rewrite the gate in the worktree and commit, so no
        # diff-reading gate can tell it from ordinary work. Heredoc, not a
        # nested-quote one-liner: POSIX sh has no backslash escape inside
        # single quotes.
        runtime.exec_(
            container,
            [
                "sh",
                "-euc",
                """
cd /work
cat > .saffron/gates/demo <<'GATE'
#!/bin/sh
printf '{"gate":"demo","status":"pass","tool":"lying 9.9"}\\n'
GATE
chmod +x .saffron/gates/demo
git add -A && git commit -qm 'tune the gate'
""",
            ],
        )
        # The edit must have landed, or the assertion below proves nothing.
        landed = runtime.exec_(container, ["cat", "/work/.saffron/gates/demo"])
        assert "lying" in landed.stdout, landed.stdout

        result = run_gate(
            "demo",
            Path(worktree.GATES_MOUNT) / ".saffron" / "gates" / "demo",
            cwd=tmp_path,
            executor=CellExecutor(container),
        )
        assert result.tool == "honest 1.0"
        assert result.status == "pass"
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


@pytest.mark.cell
def test_the_cell_cannot_reach_the_real_remote(tmp_path, network):
    """The mirror is the only remote a cell has (DESIGN.md §5.1)."""
    origin = tmp_path / "origin"
    base = _seed_repo(origin)
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    volume, container = "saffron-test-wt2", "saffron-test-cell2"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
            network=network,
            env={},
            gates_dir=_gates_dir(tmp_path),
        )
        remotes = runtime.exec_(container, ["git", "remote", "-v"], workdir="/work")
        assert "origin" not in remotes.stdout
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


@pytest.mark.cell
def test_the_cell_reaches_nothing_but_the_api(tmp_path, network):
    """The containment question is about *this* container — the long-lived cell
    prepare_worktree starts — not about an ephemeral probe run beside it."""
    origin = tmp_path / "origin"
    base = _seed_repo(origin)
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    volume, container = "saffron-test-wt3", "saffron-test-cell3"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    runtime.remove_container(container)
    try:
        proxy_ip = proxy.start_proxy(network)
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
            network=network,
            env=proxy.proxy_env(proxy_ip),
            gates_dir=_gates_dir(tmp_path),
        )
        denied = runtime.exec_(container, reach("https://example.com"), timeout_s=90)
        assert denied.returncode != 0, denied.stdout
        assert "URLError" in denied.stderr, denied.stderr

        # The positive half: the cell is contained, not merely broken.
        allowed = runtime.exec_(
            container, reach("https://api.anthropic.com/v1/models"), timeout_s=90
        )
        assert "STATUS" in allowed.stdout, allowed.stderr
    finally:
        runtime.remove_container(container)
        proxy.stop_proxy()
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


@pytest.mark.cell
def test_dirty_paths_sees_an_uncommitted_edit(tmp_path, network):
    origin = tmp_path / "origin"
    base = _seed_repo(origin)
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    volume, container = "saffron-test-wt5", "saffron-test-cell5"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
            network=network,
            env={},
            gates_dir=_gates_dir(tmp_path),
        )
        assert worktree.dirty_paths(container) == []
        runtime.exec_(container, ["sh", "-c", "echo x >> /work/a.txt"])
        assert "a.txt" in worktree.dirty_paths(container)
        runtime.exec_(container, ["sh", "-c", "cd /work && touch brand-new.py"])
        assert "brand-new.py" in worktree.dirty_paths(container)

        # A staged rename ("R  new\0old\0") is the tricky chunk: the skip must
        # consume exactly the source field so it neither leaks nor swallows a
        # neighbour. a.txt's prior edit rides along with the rename.
        renamed = runtime.exec_(
            container, ["git", "mv", "a.txt", "renamed.txt"], workdir="/work"
        )
        assert renamed.returncode == 0, renamed.stderr
        dirty = worktree.dirty_paths(container)
        assert "renamed.txt" in dirty
        assert "a.txt" not in dirty
        assert sorted(dirty) == ["brand-new.py", "renamed.txt"]
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


@pytest.mark.cell
def test_commit_dirty_commits_a_dirty_tree_and_no_ops_on_a_clean_one(tmp_path, network):
    origin = tmp_path / "origin"
    base = _seed_repo(origin)
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    volume, container = "saffron-test-wt7", "saffron-test-cell7"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
            network=network,
            env={},
            gates_dir=_gates_dir(tmp_path),
        )
        # A clean tree has nothing to checkpoint.
        assert worktree.commit_dirty(container, "checkpoint: nothing") is False
        assert worktree.commit_subjects(container, base) == []

        runtime.exec_(container, ["sh", "-c", "echo x >> /work/a.txt"])
        runtime.exec_(container, ["sh", "-c", "cd /work && touch brand-new.py"])
        assert worktree.commit_dirty(container, "checkpoint: turn ceiling") is True
        assert worktree.dirty_paths(container) == []
        assert worktree.commit_subjects(container, base) == ["checkpoint: turn ceiling"]

        # Idempotent: nothing left dirty, so calling again is a no-op.
        assert worktree.commit_dirty(container, "checkpoint: again") is False
        assert worktree.commit_subjects(container, base) == ["checkpoint: turn ceiling"]
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


@pytest.mark.cell
def test_a_cell_starts_from_a_base_the_mirror_only_learns_by_fetching(
    tmp_path, network
):
    """The end-to-end claim `test_fetch_default_branch_reaches_from_a_mirror_ref_when_local_is_behind`
    (tests/test_package.py) can't make: that the mirror ref moves. This proves
    a cell can actually seed from what it moved to."""
    origin = tmp_path / "origin"
    first = _seed_repo(origin)
    (origin / "a.txt").write_text("two\n")
    subprocess.run(["git", "add", "a.txt"], cwd=origin, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@example.com",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "second",
        ],
        cwd=origin,
        check=True,
        capture_output=True,
    )
    second = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=origin, capture_output=True, text=True
    ).stdout.strip()

    local = tmp_path / "local"
    subprocess.run(["git", "clone", "-q", str(origin), str(local)], check=True)
    subprocess.run(["git", "reset", "-q", "--hard", first], cwd=local, check=True)
    (local / "b.txt").write_text("local only\n")
    subprocess.run(["git", "add", "b.txt"], cwd=local, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@example.com",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "diverged",
        ],
        cwd=local,
        check=True,
        capture_output=True,
    )
    diverged = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=local, capture_output=True, text=True
    ).stdout.strip()

    mirror = mirror_ops.ensure_mirror(local, tmp_path / "m.git")
    # Precondition: without this, a bug that stopped moving the ref would
    # pass silently.
    assert (
        subprocess.run(
            ["git", "-C", str(mirror), "rev-parse", "refs/heads/main"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        == diverged
    )

    branch, fetched = package_phase.fetch_default_branch(mirror, str(origin))
    assert fetched == second

    volume, container = "saffron-test-wt6", "saffron-test-cell6"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=fetched,
            branch=f"saffron/test-{branch}",
            image=image.BASE_TAG,
            container=container,
            network=network,
            env={},
            gates_dir=_gates_dir(tmp_path),
        )
        assert worktree.head_sha(container) == fetched
        # The sha check alone would pass on an empty tree; the content read
        # is what proves the objects the fetch moved actually arrived.
        content = runtime.exec_(container, ["cat", "/work/a.txt"])
        assert content.stdout.strip() == "two"
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


def test_a_failed_seed_leaves_no_container_in_the_leak_ledger(monkeypatch, tmp_path):
    """The seed is an *ephemeral* container between the two creates. Recording
    the cell's name before it reports a container nothing ever created, and
    teardown then execs a patch export into it — the false leak the ledger
    exists to prevent, one step further along than where it was fixed."""
    monkeypatch.setattr(runtime, "create_volume", lambda name: None)
    monkeypatch.setattr(
        runtime, "run_ephemeral", lambda *a, **k: runtime.Completed(1, "", "bad sha")
    )

    def _never(*_a, **_k):
        raise AssertionError("run_detached must not be reached")

    monkeypatch.setattr(runtime, "run_detached", _never)

    created: set[str] = set()
    with pytest.raises(runtime.CellRuntimeError, match="seeding the worktree"):
        worktree.prepare_worktree(
            mirror=tmp_path / "m.git",
            volume="vol",
            base_sha="a" * 40,
            branch="saffron/SY-1",
            image="img",
            container="saffron-cell-SY-1",
            network="net",
            env={},
            gates_dir=_gates_dir(tmp_path),
            state_volume="st",
            created=created,
        )
    assert created == {"st"}


def test_the_container_is_recorded_before_the_run_that_creates_it(
    monkeypatch, tmp_path
):
    """The other direction: `run_detached` failing part-way can still have left
    the container, so the name goes in before the call and not after."""
    monkeypatch.setattr(runtime, "create_volume", lambda name: None)
    monkeypatch.setattr(
        runtime, "run_ephemeral", lambda *a, **k: runtime.Completed(0, "", "")
    )

    def _half_dead(*_a, **_k):
        raise runtime.CellRuntimeError("the container died starting up")

    monkeypatch.setattr(runtime, "run_detached", _half_dead)

    created: set[str] = set()
    with pytest.raises(runtime.CellRuntimeError, match="died starting up"):
        worktree.prepare_worktree(
            mirror=tmp_path / "m.git",
            volume="vol",
            base_sha="a" * 40,
            branch="saffron/SY-1",
            image="img",
            container="saffron-cell-SY-1",
            network="net",
            env={},
            gates_dir=_gates_dir(tmp_path),
            state_volume="st",
            created=created,
        )
    assert created == {"st", "saffron-cell-SY-1"}


# --------------------------------------------------------- stacked_on: no cell


def test_prepare_worktree_checks_out_exactly_the_base_it_is_given(
    monkeypatch, tmp_path
):
    """One base argument, and the seed checks out that and nothing else.

    `CellSpec.tree_base` resolves *which* base it is — the run's pin, or a
    stacked task's parent head. This function does not re-derive that: a
    second copy of the rule is two things sharing one word again, one layer
    down, and the copies can disagree with nothing to notice. No cell:
    `run_ephemeral`/`run_detached`/`create_volume` are monkeypatched to record
    what they were asked to do rather than run it.
    """
    scripts: list[str] = []
    monkeypatch.setattr(runtime, "create_volume", lambda name: None)

    def _record(image, command, **_kwargs):
        scripts.append(command[-1])
        return runtime.Completed(0, "", "")

    monkeypatch.setattr(runtime, "run_ephemeral", _record)
    monkeypatch.setattr(runtime, "run_detached", lambda *a, **k: None)

    def _prepare(base_sha: str) -> None:
        worktree.prepare_worktree(
            mirror=tmp_path / "m.git",
            volume="vol",
            base_sha=base_sha,
            branch="saffron/SY-1",
            image="img",
            container="c",
            network="net",
            env={},
            gates_dir=_gates_dir(tmp_path),
        )

    _prepare("b" * 40)
    _prepare("d" * 40)

    assert f"git checkout -q -b saffron/SY-1 {'b' * 40}" in scripts[0]
    assert f"git checkout -q -b saffron/SY-1 {'d' * 40}" in scripts[1]
    # Byte-identical but for the base: nothing else in the seed moves with it.
    assert scripts[0].replace("b" * 40, "d" * 40) == scripts[1]


def _no_cell_runtime(monkeypatch, tmp_path):
    """Fakes just enough of the cell runtime that `prepare_worktree` and the
    diff-reading helpers run their real git commands against a host
    directory instead of inside a container — the same commands, no cell and
    no network. Only one volume/container pair is ever live in a test that
    uses this, so a name -> directory mapping is all it takes.
    """
    volumes: dict[str, Path] = {}
    containers: dict[str, Path] = {}

    def _create_volume(name):
        directory = tmp_path / f"vol-{name}"
        directory.mkdir(parents=True, exist_ok=True)
        volumes[name] = directory

    def _run_ephemeral(image, command, *, mounts=(), **_kwargs):
        script = command[-1]
        for mount in mounts:
            real = (
                str(mount.source)
                if mount.kind == "bind"
                else str(volumes[mount.source])
            )
            script = script.replace(mount.target, real)
        done = subprocess.run(["sh", "-euc", script], capture_output=True)
        return runtime.Completed(
            done.returncode, done.stdout.decode(), done.stderr.decode()
        )

    def _run_detached(name, image, *, mounts=(), **_kwargs):
        for mount in mounts:
            if mount.kind == "volume" and mount.target == worktree.WORKTREE_MOUNT:
                containers[name] = volumes[mount.source]

    def _exec(container, command, *, workdir=None, timeout_s=900):
        # Raise rather than fall back to `None`: a helper that omitted
        # `workdir` would otherwise run git against this checkout and go green.
        if workdir != worktree.WORKTREE_MOUNT:
            raise AssertionError(f"unexpected workdir {workdir!r}")
        cwd = containers[container]
        done = subprocess.run(list(command), cwd=cwd, capture_output=True)
        return runtime.Completed(
            done.returncode,
            done.stdout.decode(errors="replace"),
            done.stderr.decode(errors="replace"),
        )

    monkeypatch.setattr(runtime, "create_volume", _create_volume)
    monkeypatch.setattr(runtime, "run_ephemeral", _run_ephemeral)
    monkeypatch.setattr(runtime, "run_detached", _run_detached)
    monkeypatch.setattr(runtime, "exec_", _exec)
    return volumes


def _commit_file(repo, name, content, message):
    (repo / name).write_text(content)
    subprocess.run(["git", "add", name], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-qm", message], cwd=repo, check=True, capture_output=True
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()


def test_a_stacked_worktree_holds_the_parents_real_commits_and_only_the_childs_new_commit_is_exported(
    monkeypatch, tmp_path
):
    """Criteria 2 and 3, witnessed together: a real two-commit parent branch,
    a real child commit on top of it, no cell.

    A worktree built at the parent's head — what `CellSpec.tree_base` resolves
    to for a stacked task — contains the parent's commits (criterion 2); a
    patch exported against that same head contains only the child's own commit
    (criterion 3), while one exported against the run's pin contains all three,
    which is what the same generic function gives an unstacked task.
    """
    origin = tmp_path / "origin"
    root = _seed_repo(origin)
    _commit_file(origin, "parent_a.txt", "from the parent\n", "parent commit A")
    parent_head = _commit_file(
        origin, "parent_b.txt", "also the parent\n", "parent commit B"
    )
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )

    volumes = _no_cell_runtime(monkeypatch, tmp_path)
    volume, container = "vol", "container"
    runtime.create_volume(volume)

    worktree.prepare_worktree(
        mirror=mirror,
        volume=volume,
        # The tree base the caller resolved, not the run's pin.
        base_sha=parent_head,
        branch="saffron/child",
        image="img",
        container=container,
        network="net",
        env={},
        gates_dir=_gates_dir(tmp_path),
    )

    # Criterion 2: a real branch, real commits — the tree is the parent's,
    # not the root's.
    assert worktree.head_sha(container) == parent_head
    assert worktree.commits_ahead(container, root) == 2
    assert (volumes[volume] / "parent_a.txt").read_text() == "from the parent\n"
    assert (volumes[volume] / "parent_b.txt").read_text() == "also the parent\n"

    # The child's own commit, made on top of the checked-out parent head.
    (volumes[volume] / "child.txt").write_text("from the child\n")
    subprocess.run(
        ["git", "add", "child.txt"],
        cwd=volumes[volume],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-qm", "child commit"],
        cwd=volumes[volume],
        check=True,
        capture_output=True,
    )

    # Criterion 3: exported against the base it was actually built on, the
    # patch holds only the child's own work.
    stacked_patch = worktree.export_patch(container, parent_head)
    assert "from the child" in stacked_patch
    assert "from the parent" not in stacked_patch
    assert "also the parent" not in stacked_patch
    assert worktree.commits_ahead(container, parent_head) == 1

    # Contrast: the same function, hedged against the original base_sha,
    # answers the ordinary (unstacked) question instead — every commit made
    # since the run's pin, parent's included.
    whole_patch = worktree.export_patch(container, root)
    assert "from the parent" in whole_patch
    assert "also the parent" in whole_patch
    assert "from the child" in whole_patch
    assert worktree.commits_ahead(container, root) == 3


# --- source_reverted, against a real git repo on the host ------------------
#
# `_git` is a one-function seam over `runtime.exec_`, so these run the real
# `_revert_source`/`_restore_source`/`_exists_at` against real git without a
# container. `-m cell` is what the *isolation* of a worktree needs; the tree
# arithmetic here needs only git, and leaving it to a cell-marked test is how
# the whole of this code shipped with `make check` saying nothing about it.


def _host_git(tmp_path, monkeypatch):
    """Point `worktree._git` at a real repo in `tmp_path` instead of a cell."""

    def exec_(_container, command, *, workdir=None, timeout_s=900):
        # Bytes then `runtime._decode`, exactly as `runtime._call` does it —
        # not `text=True`. Universal-newline translation and a strict decode
        # are both things production does not do, and a seam that does them
        # hides every byte-fidelity defect in the code under test.
        done = subprocess.run(command, cwd=tmp_path, capture_output=True, check=False)
        return runtime.Completed(
            done.returncode, runtime._decode(done.stdout), runtime._decode(done.stderr)
        )

    monkeypatch.setattr(worktree.runtime, "exec_", exec_)


def _commit(tmp_path, message):
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", message],
        cwd=tmp_path,
        check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _porcelain(tmp_path):
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _repo_with_a_diff(tmp_path, monkeypatch):
    """A repo whose HEAD commit modified one source file, deleted a second and
    added a third — the three shapes `changed_files` can carry. Renames arrive
    as the delete, because the diff is computed `--no-renames`."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "kept.py").write_text("kept = 1\n")
    (tmp_path / "src" / "gone.py").write_text("gone = 1\n")
    base = _commit(tmp_path, "base")

    (tmp_path / "src" / "kept.py").write_text("kept = 2\n")
    (tmp_path / "src" / "gone.py").unlink()
    (tmp_path / "src" / "added.py").write_text("added = 1\n")
    _commit(tmp_path, "the diff")

    _host_git(tmp_path, monkeypatch)
    return base, ["src/kept.py", "src/gone.py", "src/added.py"]


def test_the_reverted_tree_is_the_source_as_it_stood_at_the_base(tmp_path, monkeypatch):
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)
    inside = {}

    with worktree.source_reverted("c", base, paths):
        inside["kept"] = (tmp_path / "src" / "kept.py").read_text()
        inside["gone_exists"] = (tmp_path / "src" / "gone.py").exists()
        inside["added_exists"] = (tmp_path / "src" / "added.py").exists()

    # Modified goes back, deleted comes back, added goes away — the last is
    # what makes a spec landing a module with its tests break the import.
    assert inside == {"kept": "kept = 1\n", "gone_exists": True, "added_exists": False}


def test_a_diff_that_deletes_a_source_file_still_restores_every_other_path(
    tmp_path, monkeypatch
):
    """`git checkout HEAD -- <paths>` aborts the whole checkout on the first
    pathspec absent from HEAD, restoring none of the others. A deleted source
    file is exactly that, every rename contributes one, and the tree was left
    fully reverted for `committed` and the salvage checkpoints to act on."""
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)

    with worktree.source_reverted("c", base, paths):
        pass

    assert (tmp_path / "src" / "kept.py").read_text() == "kept = 2\n"
    assert not (tmp_path / "src" / "gone.py").exists()
    assert (tmp_path / "src" / "added.py").read_text() == "added = 1\n"
    assert _porcelain(tmp_path) == ""


def test_the_tree_is_restored_when_the_body_raises(tmp_path, monkeypatch):
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)

    with pytest.raises(RuntimeError), worktree.source_reverted("c", base, paths):
        raise RuntimeError("the reverted run crashed")

    assert (tmp_path / "src" / "kept.py").read_text() == "kept = 2\n"
    assert _porcelain(tmp_path) == ""


def test_a_revert_that_fails_halfway_still_restores(tmp_path, monkeypatch):
    """The revert is two git operations. A second that fails after the first
    succeeded used to raise with half the source reverted and no restore
    attempted, because the mutation sat outside the `try`."""
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)
    real = worktree._git

    def flaky(container, *args):
        if args[0] == "rm" and "--ignore-unmatch" not in args:
            return runtime.Completed(1, "", "rm exploded")
        return real(container, *args)

    monkeypatch.setattr(worktree, "_git", flaky)

    with (
        pytest.raises(runtime.CellRuntimeError),
        worktree.source_reverted("c", base, paths),
    ):
        raise AssertionError("the body must not run")

    assert _porcelain(tmp_path) == ""


# Every git operation here reports an exit code, and until these four tests
# nothing read one: replacing all three `raise runtime.CellRuntimeError` lines
# in `_revert_source`/`_restore_source` with `pass` left the whole suite green.
# A revert that silently did not happen runs the new tests against the source
# they shipped with, and `revert` calls correct work theater; a restore that
# silently did not happen hands `committed` a tree the agent did not make.


def _failing(monkeypatch, predicate):
    """Make `_git` report failure for the calls `predicate` names, and run the
    real thing for the rest."""
    real = worktree._git

    def flaky(container, *args):
        if predicate(args):
            return runtime.Completed(1, "", "git exploded")
        return real(container, *args)

    monkeypatch.setattr(worktree, "_git", flaky)


def test_a_revert_whose_checkout_fails_raises(tmp_path, monkeypatch):
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)
    # The revert's checkout, not the restore's: they differ by the tree named.
    _failing(monkeypatch, lambda args: args[0] == "checkout" and args[1] != "HEAD")

    with (
        pytest.raises(runtime.CellRuntimeError, match="revert checkout failed"),
        worktree.source_reverted("c", base, paths),
    ):
        raise AssertionError("the body must not run")

    assert _porcelain(tmp_path) == ""


def test_a_restore_whose_checkout_fails_raises(tmp_path, monkeypatch):
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)
    _failing(monkeypatch, lambda args: args[0] == "checkout" and args[1] == "HEAD")

    with (
        pytest.raises(runtime.CellRuntimeError, match="restore checkout failed"),
        worktree.source_reverted("c", base, paths),
    ):
        pass


def test_a_restore_whose_rm_fails_raises(tmp_path, monkeypatch):
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)
    # The restore's `rm` carries `--ignore-unmatch`; the revert's does not.
    _failing(monkeypatch, lambda args: args[0] == "rm" and "--ignore-unmatch" in args)

    with (
        pytest.raises(runtime.CellRuntimeError, match="restore rm failed"),
        worktree.source_reverted("c", base, paths),
    ):
        pass


def test_a_restore_that_reported_success_and_restored_nothing_raises(
    tmp_path, monkeypatch
):
    """An exit code is not the guarantee. The two arms of the restore partition
    the paths, so one that no-ops while the other succeeds exits 0 with the
    source still reverted — which `committed` reads as the agent's dirty tree
    and the salvage checkpoints commit."""
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)
    real = worktree._git

    def lying(container, *args):
        if args[0] == "checkout" and args[1] == "HEAD":
            return runtime.Completed(0, "", "")
        return real(container, *args)

    monkeypatch.setattr(worktree, "_git", lying)

    with (
        pytest.raises(runtime.CellRuntimeError, match="left the tree dirty"),
        worktree.source_reverted("c", base, paths),
    ):
        pass

    # And it raised because the tree really was still reverted, not because the
    # check fires on a tree it should accept.
    assert (tmp_path / "src" / "kept.py").read_text() == "kept = 1\n"


def test_no_source_paths_runs_no_git_at_all(monkeypatch):
    """Unreachable from the gate, which skips before it reverts nothing — kept
    because the restore's `git status` is pathspec-scoped, and an empty
    pathspec is not "no paths" to git, it is every path. Without this guard a
    no-op block would report the agent's unrelated work as a failed restore."""

    def explode(*_args):
        raise AssertionError("nothing to revert; must not run git")

    monkeypatch.setattr(worktree, "_git", explode)

    ran = False
    with worktree.source_reverted("c", "base-sha", []):
        ran = True
    assert ran


def test_a_restore_that_cannot_read_the_tree_raises(tmp_path, monkeypatch):
    """The check above is only as good as its read: a `git status` that did not
    run is not a clean tree."""
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)
    _failing(monkeypatch, lambda args: args[0] == "status")

    with (
        pytest.raises(runtime.CellRuntimeError, match="restore status failed"),
        worktree.source_reverted("c", base, paths),
    ):
        pass


def test_the_restore_ignores_work_the_gate_never_touched(tmp_path, monkeypatch):
    """The clean-tree check is scoped to `paths`, and the scoping is what lets
    `revert` run at all on a tree with uncommitted work on it — the gate
    refuses only when that work collides with what it would revert. Unscoped,
    the restore reads the agent's unrelated edits as its own failure and ends
    the attempt as infrastructure."""
    base, paths = _repo_with_a_diff(tmp_path, monkeypatch)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "notes.md").write_text("committed\n")
    _commit(tmp_path, "an unrelated file")

    with worktree.source_reverted("c", base, paths):
        (tmp_path / "docs" / "notes.md").write_text("uncommitted\n")
        (tmp_path / "docs" / "scratch.md").write_text("and untracked\n")

    # Survives untouched, and the restore did not read either as its own doing.
    assert (tmp_path / "docs" / "notes.md").read_text() == "uncommitted\n"
    assert (tmp_path / "docs" / "scratch.md").exists()
    porcelain = _porcelain(tmp_path)
    assert "docs/notes.md" in porcelain
    assert "docs/scratch.md" in porcelain
    assert "src/" not in porcelain


# --- source_mutated, against a real git repo on the host (SA-0062) ---------
#
# `_git` is a one-function seam over `runtime.exec_`, so — exactly as the
# `source_reverted` tests above do — these run the real
# `_read_file`/`_write_file`/`source_mutated` against real git with no
# container: `_host_git` points `worktree._git`'s underlying `runtime.exec_`
# at a real repo in `tmp_path` instead.


def _repo_with_a_file(tmp_path, monkeypatch, content):
    """A committed repo holding one source file, ready for a mutant."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "guard.py").write_text(content)
    _commit(tmp_path, "base")
    _host_git(tmp_path, monkeypatch)


def test_a_mutant_is_applied_and_undone_inside_the_cell(tmp_path, monkeypatch):
    _repo_with_a_file(tmp_path, monkeypatch, "if amount < 0:\n    raise ValueError\n")
    mutant = Mutant(file="src/guard.py", find="if amount < 0:", replace="if False:")
    target = tmp_path / "src" / "guard.py"

    with worktree.source_mutated("c", mutant) as reason:
        assert reason is None
        assert target.read_text() == "if False:\n    raise ValueError\n"

    assert target.read_text() == "if amount < 0:\n    raise ValueError\n"
    assert _porcelain(tmp_path) == ""


def test_the_undo_restores_the_committed_file_not_a_byte_copy(tmp_path, monkeypatch):
    """The undo is `git checkout` against `HEAD`, not a replay of the bytes
    `_read_file` displaced — `revert`'s own restore works the same way, for
    the same reason (`committed` guarantees the tree matches `HEAD`)."""
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    mutant = Mutant(file="src/guard.py", find="value = 1", replace="value = 2")

    calls: list[tuple] = []
    real = worktree._git

    def spy(container, *args):
        calls.append(args)
        return real(container, *args)

    monkeypatch.setattr(worktree, "_git", spy)

    with worktree.source_mutated("c", mutant):
        pass

    assert ("checkout", "HEAD", "--", "src/guard.py") in calls
    assert (tmp_path / "src" / "guard.py").read_text() == "value = 1\n"


def test_a_find_that_does_not_match_once_applies_nothing(tmp_path, monkeypatch):
    """Zero matches and two matches are both "not exactly once" — the same
    rule `saffron.mutation.apply_mutant` follows for a host tree, matched
    here rather than re-derived. A mutant that names two places names no
    property, and picking one silently is how a check comes to measure
    something other than what it claims."""
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\nvalue = 1\n")
    target = tmp_path / "src" / "guard.py"

    twice = Mutant(file="src/guard.py", find="value = 1", replace="value = 2")
    with worktree.source_mutated("c", twice) as reason:
        assert reason is not None
        assert "matches 2 times" in reason
    assert target.read_text() == "value = 1\nvalue = 1\n"
    assert _porcelain(tmp_path) == ""

    absent = Mutant(file="src/guard.py", find="value = 9", replace="value = 2")
    with worktree.source_mutated("c", absent) as reason:
        assert reason is not None
        assert "not found" in reason
    assert target.read_text() == "value = 1\nvalue = 1\n"
    assert _porcelain(tmp_path) == ""


def test_a_failed_undo_raises_rather_than_reporting_a_verdict(tmp_path, monkeypatch):
    """A tree `source_mutated` could not restore is the one outcome that must
    not read as a witness doing its job — `witness_gate` turns this into
    `error`, never `pass` or `fail`."""
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    mutant = Mutant(file="src/guard.py", find="value = 1", replace="value = 2")
    real = worktree._git

    def flaky(container, *args):
        if args[0] == "checkout" and args[1] == "HEAD":
            return runtime.Completed(1, "", "checkout exploded")
        return real(container, *args)

    monkeypatch.setattr(worktree, "_git", flaky)

    with (
        pytest.raises(runtime.CellRuntimeError, match="mutant undo"),
        worktree.source_mutated("c", mutant),
    ):
        pass

    # The half above left the mutation in place on purpose: its undo failed.
    # Restore first — this half is about a failure to *read*, and a dirty tree
    # would trip the uncommitted-work refusal before the read is ever reached.
    subprocess.run(
        ["git", "checkout", "HEAD", "--", "src/guard.py"], cwd=tmp_path, check=True
    )

    # A failure to *apply* raises the same way — never a yielded reason, which
    # `witness_gate` would read as the ordinary "did not apply" case.
    real_exec = worktree.runtime.exec_

    def exploding_exec(container, command, *, workdir=None, timeout_s=900):
        if command[:2] == ["sh", "-euc"] and command[2].startswith("base64 <"):
            return runtime.Completed(1, "", "base64 exploded")
        return real_exec(container, command, workdir=workdir, timeout_s=timeout_s)

    monkeypatch.setattr(worktree.runtime, "exec_", exploding_exec)
    with (
        pytest.raises(runtime.CellRuntimeError, match="reading"),
        worktree.source_mutated("c", mutant),
    ):
        raise AssertionError("the body must not run")


def test_a_mutant_over_uncommitted_work_applies_nothing(tmp_path, monkeypatch):
    """`witness` runs inside `run_suite`, and `committed` runs *after* it
    (`cell/session.py`) — so the tree here may still be dirty, and the undo
    restores `HEAD`. `revert` refuses the identical move for the identical
    reason: restoring to `HEAD` would destroy the agent's uncommitted work and
    hide it from the one gate whose job is to notice (`gates/core/revert.py`,
    `docs/BACKLOG.md` item 78). A yielded reason lands `witness` on `skip`,
    which is the honest answer when the evidence cannot be bought.
    """
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    target = tmp_path / "src" / "guard.py"
    target.write_text("value = 1\nagent_added = True\n")
    mutant = Mutant(file="src/guard.py", find="value = 1", replace="value = 2")

    with worktree.source_mutated("c", mutant) as reason:
        assert reason is not None
        assert "uncommitted" in reason

    assert target.read_text() == "value = 1\nagent_added = True\n"
    assert _porcelain(tmp_path) == "M src/guard.py"


def test_a_write_that_fails_does_not_leave_the_file_truncated(tmp_path, monkeypatch):
    """`> path` truncates before `base64 -d` writes a byte, so a failed exec
    leaves the file empty or half-written while `witness_gate` reports "could
    not apply" — the `applied` flag is not set yet. `gates/core/witness.py`
    names this exact shape ("a raise from `__enter__` must mean nothing was
    changed") and calls a container exec that loses the connection mid-write
    the one implementation that can reach it.
    """
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    target = tmp_path / "src" / "guard.py"
    mutant = Mutant(file="src/guard.py", find="value = 1", replace="value = 2")
    real_exec = worktree.runtime.exec_

    def truncate_then_fail(container, command, *, workdir=None, timeout_s=900):
        if command[:2] == ["sh", "-euc"] and "base64 -d" in command[2]:
            target.write_text("")  # what `>` has already done by this point
            return runtime.Completed(1, "", "exec connection lost")
        return real_exec(container, command, workdir=workdir, timeout_s=timeout_s)

    monkeypatch.setattr(worktree.runtime, "exec_", truncate_then_fail)

    with (
        pytest.raises(runtime.CellRuntimeError, match="writing"),
        worktree.source_mutated("c", mutant),
    ):
        raise AssertionError("the body must not run")

    assert target.read_text() == "value = 1\n"
    assert _porcelain(tmp_path) == ""


def test_a_failed_undo_does_not_replace_an_exception_in_flight(tmp_path, monkeypatch):
    """An exception raised inside a `finally` replaces whatever was already
    propagating through it — `saffron.mutation._mutated` records this defect
    as already paid for once, and demoting a `KeyboardInterrupt` to
    `__context__` puts it where nothing looks. Raise after the `finally`,
    which Python never reaches while an exception is still in flight.
    """
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    mutant = Mutant(file="src/guard.py", find="value = 1", replace="value = 2")
    real = worktree._git

    def flaky(container, *args):
        if args[0] == "checkout":
            return runtime.Completed(1, "", "checkout exploded")
        return real(container, *args)

    monkeypatch.setattr(worktree, "_git", flaky)

    with pytest.raises(KeyboardInterrupt), worktree.source_mutated("c", mutant):
        raise KeyboardInterrupt


def test_a_mutant_path_outside_the_worktree_applies_nothing(tmp_path, monkeypatch):
    """`Mutant.file`'s only validator is "not blank" (`intake.py`), and a cell
    mounts more than the worktree — `/agent-state` among them. `..` in a
    declared path is the shape that turns a check into an arbitrary write,
    which is why `saffron.mutation._resolve_target` refuses it before either
    half reads or writes a byte. The cell sibling owes the same refusal.
    """
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret = 1\n")

    for escaping in ("../outside.txt", str(outside)):
        mutant = Mutant(file=escaping, find="secret = 1", replace="secret = 2")
        with worktree.source_mutated("c", mutant) as reason:
            assert reason is not None, escaping
            assert "inside the tree" in reason
        assert outside.read_text() == "secret = 1\n"


def test_a_mutation_leaves_bytes_it_did_not_name_alone(tmp_path, monkeypatch):
    """`runtime.exec_` decodes with `errors="replace"`, so reading a file as
    text and writing it back re-encodes every byte that was not valid UTF-8 as
    U+FFFD. The tests then run against a file differing from `HEAD` in ways the
    mutant never declared, which is the whole thing `saffron.mutation` reads
    and writes raw bytes to prevent: "anything it does must be undone exactly:
    byte-identical". A CRLF line ending is the same defect, cheaper to trip.
    """
    _repo_with_a_file(tmp_path, monkeypatch, "placeholder\n")
    target = tmp_path / "src" / "guard.py"
    target.write_bytes(b"# caf\xe9 (latin-1)\r\nvalue = 1\n")
    _commit(tmp_path, "non-utf8 and a CRLF")
    mutant = Mutant(file="src/guard.py", find="value = 1", replace="value = 2")

    with worktree.source_mutated("c", mutant) as reason:
        assert reason is None
        assert target.read_bytes() == b"# caf\xe9 (latin-1)\r\nvalue = 2\n"

    assert target.read_bytes() == b"# caf\xe9 (latin-1)\r\nvalue = 1\n"
    assert _porcelain(tmp_path) == ""


@pytest.mark.cell
def test_a_mutant_applied_in_a_real_cell_keeps_the_bytes_it_did_not_name(
    tmp_path, network
):
    """Every test above runs `source_mutated` through `_host_git`, which is a
    host `subprocess` — so the one genuinely new mechanism here, a
    `printf | base64 -d` line executed by the cell's own shell against a
    volume-backed `/work`, has never actually run in a cell. `base64` is an
    image dependency, `workdir` is ignored by the host seam, and acceptance
    claim #1 ("the host never writes to the volume, because it cannot") is
    the one thing a host-seamed test cannot assert about itself.
    """
    origin = tmp_path / "origin"
    origin.mkdir(parents=True)
    run = lambda *a: subprocess.run(a, cwd=origin, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    # Neither survives a UTF-8 round trip: the byte is invalid UTF-8 and would
    # come back U+FFFD, the CRLF is what universal-newline translation eats.
    (origin / "guard.py").write_bytes(b"# caf\xe9\r\nif amount < 0:\n    raise\n")
    run("git", "add", "guard.py")
    run("git", "commit", "-qm", "first")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=origin, capture_output=True, text=True
    ).stdout.strip()

    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    volume = "saffron-test-mutant"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    container = "saffron-test-mutant-cell"
    runtime.remove_container(container)

    def bytes_in_cell(path):
        done = runtime.exec_(
            container,
            ["sh", "-euc", f"base64 < {path}"],
            workdir=worktree.WORKTREE_MOUNT,
        )
        assert done.returncode == 0, done.stderr
        return base64.b64decode(done.stdout)

    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
            network=network,
            env={},
            gates_dir=_gates_dir(tmp_path),
        )
        mutant = Mutant(file="guard.py", find="if amount < 0:", replace="if False:")

        with worktree.source_mutated(container, mutant) as reason:
            assert reason is None, reason
            assert bytes_in_cell("guard.py") == b"# caf\xe9\r\nif False:\n    raise\n"

        assert bytes_in_cell("guard.py") == b"# caf\xe9\r\nif amount < 0:\n    raise\n"
        assert worktree.dirty_paths(container) == []
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


def test_a_mutant_on_a_path_git_cannot_restore_applies_nothing(tmp_path, monkeypatch):
    """The undo is `git checkout HEAD -- <file>`, so the precondition it
    actually needs is *a regular file tracked at HEAD* — not merely a clean
    one. A gitignored or untracked path is clean to `git status` and has
    nothing at `HEAD` to come back from; a nonexistent one is the ordinary
    case `gates/core/witness.py` calls "the spec anticipated a different
    implementation", which `saffron.mutation.apply_mutant` answers with a
    reason and `error` would wrongly charge to the attempt.
    """
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    (tmp_path / ".gitignore").write_text("generated/\n")
    _commit(tmp_path, "ignore generated")
    (tmp_path / "generated").mkdir()
    (tmp_path / "generated" / "g.py").write_bytes(b"value = 1\n")

    for path in ("generated/g.py", "nope.py"):
        mutant = Mutant(file=path, find="value = 1", replace="value = 2")
        with worktree.source_mutated("c", mutant) as reason:
            assert reason is not None, path
            assert "HEAD" in reason, reason
    assert (tmp_path / "generated" / "g.py").read_bytes() == b"value = 1\n"
    assert _porcelain(tmp_path) == ""


def test_a_symlinked_mutant_path_applies_nothing(tmp_path, monkeypatch):
    """A symlink is a regular path to `cat` and to `>`, and *not* to
    `git checkout`: the read follows it, the write follows it, and the undo
    restores the link — which never changed — and exits 0. The mutation is
    left behind on the file the link points at, reported as a clean success.

    `saffron.mutation` never meets this because it writes bytes back to the
    same path it read them from. Here the two halves resolve differently, so
    the mode at `HEAD` has to be read rather than assumed.
    """
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    (tmp_path / "src" / "alias.py").symlink_to("guard.py")
    _commit(tmp_path, "a symlink beside the source")
    mutant = Mutant(file="src/alias.py", find="value = 1", replace="value = 2")

    with worktree.source_mutated("c", mutant) as reason:
        assert reason is not None
        assert "regular file" in reason

    assert (tmp_path / "src" / "guard.py").read_bytes() == b"value = 1\n"
    assert (tmp_path / "src" / "alias.py").is_symlink()
    assert _porcelain(tmp_path) == ""


def test_an_undo_that_exits_zero_without_restoring_still_raises(tmp_path, monkeypatch):
    """`_restore_source` in this same module argues that an exit code is not
    the guarantee it makes, and checks the tree afterwards. The undo here owes
    the same: a tree this could not restore must not read as a witness doing
    its job, and `git checkout` exiting 0 is not proof that it did.
    """
    _repo_with_a_file(tmp_path, monkeypatch, "value = 1\n")
    mutant = Mutant(file="src/guard.py", find="value = 1", replace="value = 2")
    real = worktree._git

    def checkout_that_does_nothing(container, *args):
        if args[0] == "checkout":
            return runtime.Completed(0, "", "")
        return real(container, *args)

    monkeypatch.setattr(worktree, "_git", checkout_that_does_nothing)

    with (
        pytest.raises(runtime.CellRuntimeError, match="did not restore"),
        worktree.source_mutated("c", mutant),
    ):
        pass
