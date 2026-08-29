from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron.cell import proxy, runtime, worktree
from saffron.gates.runner import CellExecutor, run_gate
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
    with pytest.raises(TypeError):
        worktree.prepare_worktree(
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
