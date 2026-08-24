# The Two Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A task is cut from the remote's default-branch head, and its gate results come from executables the cell could not have written.

**Architecture:** Three changes to where the host gets things. `base_sha` comes from a fetch of the remote's default branch at cell construction instead of `git rev-parse HEAD` in the invoking checkout. Gate executables come from a read-only bind mount extracted out of the mirror at `base_sha`, not from `/work`. And a new core gate, `committed`, fails an attempt whose worktree is dirty — because the gates measure `/work` while the patch is `base_sha..HEAD`, so an uncommitted change is live for the suite and invisible to every reviewing gate.

**Tech Stack:** Python 3.12+, pydantic, pytest, `uv`, `apple/container` (via `saffron.cell.runtime` only).

**Spec:** `docs/superpowers/specs/2026-08-23-two-boundaries-design.md`

## Global Constraints

- `DESIGN.md` section numbers are an API. Add subsections; **never renumber**.
- Vocabulary is enforced (`CONTEXT.md`, including its `_Avoid_` lists): "cell" not "sandbox", "cell runtime" not "Docker", "gate result" not "gate run". States in backticked caps, phases in bare caps, gate names and statuses lowercase in backticks.
- `error` ≠ `fail`. `fail` means the repo's code is wrong; `error` means the gate broke, aborts the attempt, and is charged to nobody.
- `saffron/cell/runtime.py` is the **only** module that may name `apple/container`.
- Core knows nothing about languages, test runners, or package managers (§2.1). Core invokes declared gates, never tools.
- Commit subjects are lowercase `type(scope): what changed`, written as a sentence about the defect rather than the file.
- Inline comments are terse — 1–2 lines, the non-obvious "why" only. Rationale goes in the commit message or `DESIGN.md`.
- `make check` (lint + test) must pass before every commit. Cell-marked tests are excluded by default and are run explicitly with `uv run pytest -m cell`.
- Never run `git push`.

---

### Task 1: `fetch_default_branch` — one source for both ends

**Files:**
- Modify: `saffron/phases/package.py:92-101` (after `default_branch`), `saffron/phases/package.py:485-491`
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: `default_branch(url, *, cwd) -> str`, `_run(cwd, *args)`, `PackageError` — all already in `package.py`.
- Produces: `fetch_default_branch(mirror: Path, url: str) -> tuple[str, str]` returning `(branch_name, head_sha)`. Task 2 calls it from `cli.py`.

Pure refactor — `package()` must behave identically. Item 11 is an asymmetry, not a missing feature: this is the function both ends will read.

- [ ] **Step 1: Write the failing test**

```python
def test_fetch_default_branch_reports_the_remote_head(tmp_path):
    """The head the mirror now holds, not the one the caller happened to have."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git_init_with_commit(origin, "first")
    head = subprocess.run(
        ["git", "-C", str(origin), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    mirror = ensure_mirror(origin, tmp_path / "mirror.git")
    branch, fetched = fetch_default_branch(mirror, str(origin))

    assert fetched == head
    assert branch in ("main", "master")
    # The object is in the mirror, which is what prepare_worktree needs.
    assert subprocess.run(
        ["git", "-C", str(mirror), "cat-file", "-e", f"{fetched}^{{tree}}"]
    ).returncode == 0


def test_fetch_default_branch_refuses_an_unreachable_remote(tmp_path):
    mirror = ensure_mirror(_repo_with_commit(tmp_path), tmp_path / "mirror.git")
    with pytest.raises(PackageError):
        fetch_default_branch(mirror, str(tmp_path / "nowhere"))
```

Add `fetch_default_branch` to the `saffron.phases.package` import block at the top of `tests/test_package.py:23`, and `from saffron.repos.mirror import ensure_mirror`. If `_git_init_with_commit` / `_repo_with_commit` helpers do not already exist in this file, write one that runs `git init -q`, writes a file, `git add -A`, and `git -c user.email=t@t -c user.name=T commit -qm first`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package.py -k fetch_default_branch -v`
Expected: FAIL with `ImportError: cannot import name 'fetch_default_branch'`

- [ ] **Step 3: Write minimal implementation**

Insert after `default_branch` in `saffron/phases/package.py`:

```python
def fetch_default_branch(mirror: Path, url: str) -> tuple[str, str]:
    """The remote's default branch and its head, fetched into the mirror.

    Both ends of §5.7 read this. They read two different sources until backlog
    item 11 — the invoking checkout's HEAD at task start and the remote at
    package time — and the asymmetry was the whole defect.
    """
    default = default_branch(url, cwd=mirror)
    fetched = _run(mirror, "fetch", url, f"refs/heads/{default}")
    if fetched.returncode != 0:
        raise PackageError(f"cannot fetch {default} from {url}: {fetched.stderr[:200]}")
    head = _run(mirror, "rev-parse", "FETCH_HEAD").stdout.strip()
    if not head:
        raise PackageError(f"{url} reported no head for {default}")
    return default, head
```

Then replace `package.py:485-491`. Before:

```python
    default = default_branch(url, cwd=mirror)

    assert_base_objects(mirror, base_sha)
    fetched = _run(mirror, "fetch", url, f"refs/heads/{default}")
    if fetched.returncode != 0:
        raise PackageError(f"cannot fetch {default} from {url}: {fetched.stderr[:200]}")
    fetch_head = _run(mirror, "rev-parse", "FETCH_HEAD").stdout.strip()
```

After:

```python
    default, fetch_head = fetch_default_branch(mirror, url)
    assert_base_objects(mirror, base_sha)
```

The fetch now happens one line before `assert_base_objects` instead of one line after. Nothing reads the mirror in between, so the order does not matter — noted because a reviewer will see the move.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS, including every pre-existing `package()` test — this task changes no behaviour.

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py
git commit -m "refactor(package): the two ends of the base comparison read one source"
```

---

### Task 2: the base is the remote's default-branch head

**Files:**
- Modify: `saffron/cli.py:114-119`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `fetch_default_branch(mirror, url) -> tuple[str, str]` (Task 1), `package_phase.real_remote(repo) -> str`.
- Produces: nothing new. `CellSpec.base_sha` now holds the remote's default-branch head.

- [ ] **Step 1: Write the failing test**

```python
def test_the_base_is_the_remote_default_branch_not_the_checkout(tmp_path, monkeypatch):
    """A task started from a feature branch is still cut from the default branch.

    The property §4.2 needs: a task's base must not depend on where the
    operator was standing.
    """
    repo = _repo_with_commit(tmp_path)
    default_head = _rev_parse(repo, "HEAD")
    _run_git(repo, "checkout", "-q", "-b", "joel/feature")
    (repo / "extra.txt").write_text("uncommitted-and-local\n")
    _run_git(repo, "add", "-A")
    _run_git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "local only")
    assert _rev_parse(repo, "HEAD") != default_head

    captured: dict[str, str] = {}

    def _fake_run_one_cell(cell_spec, **kwargs):
        captured["base_sha"] = cell_spec.base_sha
        raise SystemExit(0)

    monkeypatch.setattr("saffron.cli.run_one_cell", _fake_run_one_cell)
    with pytest.raises(SystemExit):
        _invoke_run_cell(repo, tmp_path)

    assert captured["base_sha"] == default_head
```

`_invoke_run_cell` builds the `argparse.Namespace` that `_run_cell` takes (`repo`, `spec`, `home`, `budget`, `max_attempts`) and calls `saffron.cli._run_cell` with a `Ledger` on a `tmp_path` database and an `out_dir` under `tmp_path`. Follow whatever construction `tests/test_cli.py` already uses for its existing cases; if it has no `_run_cell` case yet, build the namespace inline. The repo needs an `origin` remote pointing at a second bare clone for `real_remote` to succeed — create it with `git clone --bare` and `git remote add origin`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -k default_branch -v`
Expected: FAIL — `base_sha` equals the feature branch tip, not `default_head`.

- [ ] **Step 3: Write minimal implementation**

In `saffron/cli.py:_run_cell`, replace:

```python
    base_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
```

with:

```python
    # The remote's default-branch head, not the invoking checkout's: a task's
    # base must not depend on where the operator was standing (§5.7).
    _, base_sha = package_phase.fetch_default_branch(
        mirror, package_phase.real_remote(repo)
    )
```

`package_phase` is already imported at `cli.py:15`. Run `uv run ruff check saffron/cli.py` afterwards — if `subprocess` is now unused, ruff reports `F401` and the import comes out.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_cli.py -v && uv run ruff check saffron/`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add saffron/cli.py tests/test_cli.py
git commit -m "fix(cli): a task's base was whatever branch the operator was standing on"
```

---

### Task 3: `export_gates` — the base tree's gates, on the host

**Files:**
- Modify: `saffron/repos/mirror.py` (add at end)
- Test: `tests/test_mirror.py`

**Interfaces:**
- Consumes: `GitError`, `_run` — already in `mirror.py`.
- Produces: `export_gates(mirror: Path, sha: str, dest: Path) -> Path`. Returns `dest`, whose only content is `.saffron/gates/`. Task 4 mounts `dest` at `/gates`, so `policy.gate_executables(Path("/gates"))` resolves to `/gates/.saffron/gates/<name>` with no change to `policy.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_export_gates_takes_the_tree_at_the_sha(tmp_path):
    repo = _repo_with_commit(tmp_path)
    gates = repo / ".saffron" / "gates"
    gates.mkdir(parents=True)
    (gates / "tests").write_text("#!/bin/sh\necho honest\n")
    (gates / "tests").chmod(0o755)
    _commit_all(repo, "gates")
    base = _rev_parse(repo, "HEAD")

    (gates / "tests").write_text("#!/bin/sh\necho lying\n")
    _commit_all(repo, "a gate that lies")

    mirror = ensure_mirror(repo, tmp_path / "mirror.git")
    dest = export_gates(mirror, base, tmp_path / "gates-out")

    exported = dest / ".saffron" / "gates" / "tests"
    assert "honest" in exported.read_text()
    assert "lying" not in exported.read_text()
    # A gate that is not executable reads identically to one that is missing.
    assert os.access(exported, os.X_OK)


def test_export_gates_refuses_a_tree_with_no_gates(tmp_path):
    repo = _repo_with_commit(tmp_path)
    mirror = ensure_mirror(repo, tmp_path / "mirror.git")
    with pytest.raises(GitError):
        export_gates(mirror, _rev_parse(repo, "HEAD"), tmp_path / "gates-out")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mirror.py -k export_gates -v`
Expected: FAIL with `ImportError: cannot import name 'export_gates'`

- [ ] **Step 3: Write minimal implementation**

Add `import shutil` (already present) and `import tarfile` to `saffron/repos/mirror.py`, then:

```python
def export_gates(mirror: Path, sha: str, dest: Path) -> Path:
    """`.saffron/gates/` as it stood at `sha`, on the host.

    The cell reads its gates from here rather than from `/work`, so an in-cell
    edit — committed or not — cannot reach the runner (§5.4). `git archive`
    carries the mode bits, and a gate that is not executable reads identically
    to one that was never declared.
    """
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    archive = dest / "gates.tar"
    with archive.open("wb") as sink:
        done = subprocess.run(
            ["git", "-C", str(mirror), "archive", "--format=tar", sha, ".saffron/gates"],
            stdout=sink,
            stderr=subprocess.PIPE,
            check=False,
        )
    if done.returncode != 0:
        detail = done.stderr.decode(errors="replace").strip()
        raise GitError(f"git archive {sha[:12]} .saffron/gates: {detail}")
    with tarfile.open(archive) as tar:
        # filter="data" clears setuid/setgid/sticky and group-and-other write,
        # and keeps the execute bit the gate needs.
        tar.extractall(dest, filter="data")
    archive.unlink()

    if not (dest / ".saffron" / "gates").is_dir():
        raise GitError(f"{sha[:12]} has no .saffron/gates for the cell to run")
    return dest
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_mirror.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add saffron/repos/mirror.py tests/test_mirror.py
git commit -m "feat(mirror): the gates that judge a task came from the tree the task can edit"
```

---

### Task 4: mount the gates read-only, and run them from there

**Files:**
- Modify: `saffron/cell/worktree.py:17-31` (`GATES_MOUNT`, `mounts`), `saffron/cell/worktree.py:33-50` (`prepare_worktree` signature), `saffron/cell/worktree.py:96-105` (the `mounts(...)` call)
- Modify: `saffron/cell/session.py:478`, and the `prepare_worktree(...)` call at `saffron/cell/session.py:563-575`
- Test: `tests/test_worktree.py`

**Interfaces:**
- Consumes: `export_gates(mirror, sha, dest) -> Path` (Task 3), `runtime.Mount(kind, source, target, readonly)`.
- Produces: `worktree.GATES_MOUNT = "/gates"`; `mounts(volume, state_volume, gates_dir)`; `prepare_worktree(..., gates_dir: Path)`.

`gates_dir` is a **required** argument, like `network` and `env` before it. v0.5 shipped a cell where an omitted argument meant every containment control applied to a different container (Appendix I); a defaulted `gates_dir` would mean a cell silently falling back to `/work`'s gates with nothing to notice it.

- [ ] **Step 1: Write the failing test**

```python
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
            mirror=Path("/m"), volume="v", base_sha="abc", branch="b",
            image="i", container="c", network="none", env={},
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_worktree.py -k "gates" -v`
Expected: FAIL — `AttributeError: module 'saffron.cell.worktree' has no attribute 'GATES_MOUNT'`

- [ ] **Step 3: Write minimal implementation**

In `saffron/cell/worktree.py`, beside `WORKTREE_MOUNT`:

```python
GATES_MOUNT = "/gates"
```

Then `mounts`:

```python
def mounts(volume: str, state_volume: str, gates_dir: Path) -> list[runtime.Mount]:
    """The mounts every cell gets, and why they are separate.

    Session state and any credential file must not live in the tree the agent
    can write, that the scope gate walks, and that gets patch-exported. The
    gates are read-only and come from `base_sha`: the executables that judge a
    task are not the ones the task can edit (§5.4).
    """
    return [
        runtime.Mount("volume", volume, WORKTREE_MOUNT),
        runtime.Mount("volume", state_volume, STATE_MOUNT),
        runtime.Mount("bind", str(gates_dir), GATES_MOUNT, readonly=True),
    ]
```

Add `gates_dir: Path` to `prepare_worktree`'s keyword-only parameters (no default, placed beside `network` and `env`), and pass it through at the `run_detached` call: `mounts=mounts(volume, state, gates_dir)`.

In `saffron/cell/session.py:478`, replace:

```python
    gates = policy.gate_executables(Path(worktree.WORKTREE_MOUNT))
```

with:

```python
    # Cell-side, and from the read-only mount rather than /work: an in-cell
    # edit to a gate — committed or not — never reaches the runner (§5.4).
    gates = policy.gate_executables(Path(worktree.GATES_MOUNT))
```

Then, before the `prepare_worktree` call in `run_one_cell`, extract the gates and pass the directory:

```python
        task_dir.mkdir(parents=True, exist_ok=True)
        gates_dir = mirror_ops.export_gates(mirror, spec.base_sha, task_dir / "gates")
```

and add `gates_dir=gates_dir,` to the `prepare_worktree(...)` keyword arguments.

`task_dir.mkdir` currently happens *after* the baseline suite. Move that one line up to here and delete the later one — the gates must exist before the container is created. Import `export_gates` the way `session.py` already reaches `saffron.repos.mirror`; if it has no alias yet, add `from saffron.repos import mirror as mirror_ops` beside the other imports.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_worktree.py tests/test_session.py -v`
Expected: PASS. Any `prepare_worktree` or `mounts` call in an existing test now needs `gates_dir` — that is the required argument doing its job; fix each call site rather than restoring a default.

- [ ] **Step 5: Commit**

```bash
git add saffron/cell/worktree.py saffron/cell/session.py tests/test_worktree.py tests/test_session.py
git commit -m "fix(cell): the gate runner lived in the tree the cell could rewrite"
```

---

### Task 5: prove it from inside a cell

**Files:**
- Test: `tests/test_package_cell.py` (or a new `tests/test_gates_cell.py` — put it beside the other `@pytest.mark.cell` cases)

**Interfaces:**
- Consumes: everything from Tasks 3 and 4.
- Produces: nothing.

Appendix I's rule binds here: **start the cell the way production does and probe from inside it.** A test that asserts the mount list is a test of a list. This one commits a lying gate inside the cell and asserts the honest one ran anyway.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.cell
def test_a_gate_edited_inside_the_cell_never_runs(tmp_path):
    """The in-cell edit is committed, and still does not reach the runner."""
    repo = _repo_with_gate(tmp_path, body='#!/bin/sh\necho \'{"gate":"demo","status":"pass","tool":"honest 1.0"}\'\n')
    mirror = ensure_mirror(repo, tmp_path / "mirror.git")
    base = _rev_parse(repo, "HEAD")
    gates_dir = export_gates(mirror, base, tmp_path / "gates-out")

    volume, state, container = _unique_names()
    try:
        worktree.prepare_worktree(
            mirror=mirror, volume=volume, base_sha=base, branch="saffron/T-0001",
            image=CELL_IMAGE, container=container, network="none", env={},
            state_volume=state, gates_dir=gates_dir,
        )
        # The agent's move: rewrite the gate and commit, so no diff-reading
        # gate can tell it from ordinary work.
        runtime.exec_(container, [
            "sh", "-euc",
            "cd /work && printf '#!/bin/sh\\necho \\'{\"gate\":\"demo\",\"status\":\"pass\",\"tool\":\"lying 9.9\"}\\'\\n' "
            "> .saffron/gates/demo && chmod +x .saffron/gates/demo && "
            "git add -A && git commit -qm 'tune the gate'",
        ])

        result = run_gate(
            "demo",
            Path(worktree.GATES_MOUNT) / ".saffron" / "gates" / "demo",
            cwd=repo,
            executor=CellExecutor(container),
        )
        assert result.tool == "honest 1.0"
        assert result.status == "pass"

        # And the mount is read-only, so the direct route fails too.
        written = runtime.exec_(container, ["sh", "-c", "echo x > /gates/.saffron/gates/demo"])
        assert written.returncode != 0
    finally:
        _teardown(container, volume, state)
```

Reuse whatever `_unique_names` / `_teardown` / `CELL_IMAGE` helpers `tests/test_package_cell.py` and `tests/test_worktree.py` already use for their cell-marked cases rather than writing new ones.

- [ ] **Step 2: Run test to verify it fails**

Build the images first if they are not present:

```bash
container build -t saffron/cell-base:python -f images/cell-base.python.Dockerfile .
```

Run: `uv run pytest -m cell -k gate_edited_inside -v`
Expected: FAIL before Task 4's change is in place; with it, PASS. If it passes for the wrong reason — the cell never wrote the gate at all — assert the in-cell commit landed before asserting the tool.

- [ ] **Step 3: Run the whole cell suite**

Run: `uv run pytest -m cell -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_package_cell.py
git commit -m "test(cell): the gate-source claim had no test that could go red"
```

---

### Task 6: `committed` — the tree the gates measure is the tree the patch contains

**Files:**
- Create: `saffron/gates/core/committed.py`
- Modify: `saffron/cell/worktree.py` (add `dirty_paths`), `saffron/cell/session.py:591-603` (`_suite`)
- Test: `tests/test_committed.py` (new), `tests/test_worktree.py`

**Interfaces:**
- Consumes: `GateResult`, `Failure` from `saffron.gates.contract`; `runtime.exec_`.
- Produces: `worktree.dirty_paths(container: str) -> list[str]`; `committed.committed_gate(dirty: list[str]) -> GateResult`.

Shaped like `scope`: `session.py` reads the cell, the gate itself is a pure function that executes nothing. No `tool` field — core gates are constructed directly and never claim to have run one.

The "one repair turn, then abort" behaviour needs **no new control flow**. A dirty tree produces a `fail` with one failure per path; `subtract_baseline` cancels nothing (the baseline tree is freshly cloned and clean); `repair_decision` returns `repair` on attempt 1 and, on identical failures at attempt 2, `no-progress` → `EXHAUSTED` (`session.py:195-211`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_committed.py
from saffron.gates.core.committed import committed_gate


def test_a_clean_worktree_passes():
    result = committed_gate([])
    assert result.status == "pass"
    assert result.failures == []


def test_every_uncommitted_path_is_its_own_failure():
    """One per path, so the no-progress rule can tell two dirty attempts apart."""
    result = committed_gate(["saffron/a.py", "tests/test_a.py"])
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["saffron/a.py", "tests/test_a.py"]
    assert {f.code for f in result.failures} == {"uncommitted-change"}


def test_it_never_reports_error():
    """`fail` and `error` are not interchangeable: a dirty tree is the attempt's
    problem, not the gate breaking, and `error` is charged to nobody (§5.4)."""
    assert committed_gate(["x.py"]).status == "fail"
```

And in `tests/test_worktree.py`, a cell-marked case:

```python
@pytest.mark.cell
def test_dirty_paths_sees_an_uncommitted_edit(tmp_path):
    ...  # prepare_worktree as in Task 5, then:
    assert worktree.dirty_paths(container) == []
    runtime.exec_(container, ["sh", "-c", "echo x >> /work/README.md"])
    assert "README.md" in worktree.dirty_paths(container)
    runtime.exec_(container, ["sh", "-c", "cd /work && touch brand-new.py"])
    assert "brand-new.py" in worktree.dirty_paths(container)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_committed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'saffron.gates.core.committed'`

- [ ] **Step 3: Write minimal implementation**

`saffron/gates/core/committed.py`:

```python
"""The `committed` gate: is the tree the gates measure the tree the patch
contains? (DESIGN.md §5.4)

Core, and it executes nothing — `session.py` reads the worktree's status the
way it reads the diff for `scope`. The gates run against `/work` while
`export_patch` diffs `base_sha..HEAD`, so an uncommitted change is live for
every gate and absent from the diff `scope`, `integrity` and the reviewer all
read.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult

_MESSAGE = (
    "changed but not committed; the gates measure the committed tree, and the "
    "patch a reviewer reads is base_sha..HEAD"
)


def committed_gate(dirty: list[str]) -> GateResult:
    """`fail`, never `error`: a dirty tree is the attempt's problem, and an
    `error` would abort it and be charged to nobody (§5.4)."""
    if not dirty:
        return GateResult(gate="committed", status="pass", summary="worktree clean")
    return GateResult(
        gate="committed",
        status="fail",
        # One failure per path: identity is what the no-progress rule counts,
        # so a second dirty attempt over the same paths must look identical.
        failures=[
            Failure(file=path, code="uncommitted-change", message=_MESSAGE)
            for path in dirty
        ],
        summary=f"{len(dirty)} path(s) changed but not committed",
    )
```

In `saffron/cell/worktree.py`:

```python
def dirty_paths(container: str) -> list[str]:
    """Paths with uncommitted changes, verbatim, untracked files included."""
    done = _git(container, "status", "--porcelain", "-z", "--untracked-files=all")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"status failed: {done.stderr.strip()}")
    chunks = [chunk for chunk in done.stdout.split("\0") if chunk]
    paths: list[str] = []
    index = 0
    while index < len(chunks):
        entry = chunks[index]
        index += 1
        # A rename or copy emits a second NUL-terminated field — the source
        # path — which is not itself an entry.
        if "R" in entry[:2] or "C" in entry[:2]:
            index += 1
        paths.append(entry[3:])
    return sorted(paths)
```

In `session.py`'s `_suite`, beside the other host-side core gates:

```python
            results = [
                scope_gate(changed, spec.touches, diff=diff),
                integrity_gate(diff, policy.integrity, spec.touches),
                committed_gate(worktree.dirty_paths(container)),
                *run_suite(gates, cwd=repo, executor=executor),
            ]
```

Import `committed_gate` beside the other core-gate imports at the top of `session.py`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_committed.py tests/test_session.py -v`
Expected: PASS. Existing `session.py` tests that assert on the gate list will need `committed` added — check that each expects `pass` at baseline, which is what a freshly cloned worktree gives.

- [ ] **Step 5: Commit**

```bash
git add saffron/gates/core/committed.py saffron/cell/worktree.py saffron/cell/session.py tests/test_committed.py tests/test_worktree.py
git commit -m "fix(gates): an uncommitted edit was live for the suite and absent from the patch"
```

---

### Task 7: one repair turn, then the loop's own rule

**Files:**
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `repair_loop`, `repair_decision` (`session.py:292`, `session.py:195`), `committed_gate` (Task 6).
- Produces: nothing.

Task 6 claims the existing loop already gives "one repair turn, then abort". A claim with no test that can go red is exactly what this repo keeps finding, so this task tests the claim rather than the code.

- [ ] **Step 1: Write the failing test**

```python
def _dirty_suite(paths):
    return [committed_gate(paths)]


def test_a_dirty_tree_buys_one_repair_turn(monkeypatch):
    """Attempt 1 repairs, attempt 2 with the same paths is no-progress."""
    calls: list[str] = []
    trees = iter([["a.py"], []])

    def _run_gates():
        return _dirty_suite(next(trees))

    def _repair(new):
        calls.append("repair")
        return None

    state, attempts, _ = repair_loop(
        run_gates=_run_gates,
        baseline=_dirty_suite([]),
        max_attempts=4,
        repair=_repair,
        watch=lambda _: None,
    )
    assert calls == ["repair"]
    assert state == "READY_FOR_REVIEW"
    assert attempts == 2


def test_a_tree_still_dirty_after_the_repair_turn_ends_the_attempt():
    calls: list[str] = []

    state, attempts, new = repair_loop(
        run_gates=lambda: _dirty_suite(["a.py"]),
        baseline=_dirty_suite([]),
        max_attempts=4,
        repair=lambda _: calls.append("repair"),
        watch=lambda _: None,
    )
    assert calls == ["repair"]          # exactly one, not four
    assert state == "EXHAUSTED"
    assert attempts == 2
    assert [n.failure.file for n in new] == ["a.py"]
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/test_session.py -k dirty -v`
Expected: PASS if Task 6's reasoning holds. **If it does not** — if `repair` is called more than once, or the state is not `EXHAUSTED` — stop and say so rather than changing the test to match: the design chose one repair turn, and a loop that gives four is a finding about `repair_decision`, not about this plan.

- [ ] **Step 3: Commit**

```bash
git add tests/test_session.py
git commit -m "test(session): the one-repair-turn claim rested on a rule nothing exercised"
```

---

### Task 8: `github_slug` refuses instead of guessing

**Files:**
- Modify: `saffron/phases/package.py:31` (`_SLUG`), `saffron/phases/package.py:85-90`
- Test: `tests/test_package.py:68`

**Interfaces:**
- Consumes: `PackageError`.
- Produces: `github_slug` raises `PackageError` on anything that is not a recognisable forge remote.

Measured, this tree: three of five real inputs return a wrong answer. `https://example.com/repo` → `example.com/repo` takes the **host** as the owner, a case the backlog does not name.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize(
    "url",
    [
        "/Users/joel/Code/saffron",            # measured: -> "Code/saffron"
        "git@gitlab.com:group/owner/repo.git",  # measured: -> "owner/repo"
        "https://example.com/repo",             # measured: -> "example.com/repo"
    ],
)
def test_github_slug_refuses_what_is_not_a_forge_remote(url):
    """A wrong slug reaches `gh` as a repository that cannot exist, and a
    local-path origin is exactly what session.py falls back to."""
    with pytest.raises(PackageError):
        github_slug(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/jtmcn/saffron.git",
        "git@github.com:jtmcn/saffron.git",
        "https://github.com/jtmcn/saffron",
        "ssh://git@github.com/jtmcn/saffron.git",
    ],
)
def test_github_slug_reads_every_shape_git_writes(url):
    assert github_slug(url) == "jtmcn/saffron"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package.py -k github_slug -v`
Expected: FAIL — the three refusal cases return a slug instead of raising.

- [ ] **Step 3: Write minimal implementation**

Replace `_SLUG` at `package.py:31`:

```python
# Anchored on the forge host, not on "the last two segments": the old pattern
# read a local path as `Code/saffron` and a one-segment URL as `host/repo`.
_SLUG = re.compile(r"github\.com[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$")
```

The docstring on `github_slug` becomes:

```python
def github_slug(url: str) -> str:
    """`owner/repo`, from either URL shape git writes — or a refusal.

    Guessing is worse than failing here: the slug reaches `gh`, and a plausible
    wrong one names a repository that does not exist.
    """
```

The `raise PackageError(f"cannot read owner/repo out of {url!r}")` below it already does the right thing and needs no change.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS. `session.py:487-490` already catches `PackageError` from `real_remote` and falls back to `str(repo)`; confirm nothing else calls `github_slug` outside `package()`.

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py
git commit -m "fix(package): a local path read as a slug that named a repo nobody owns"
```

---

### Task 9: record the branch before the pull request, not after

**Files:**
- Modify: `saffron/phases/package.py:565-610` (the `open_draft_pr` call site in `package()`)
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: `_finish(ledger, outcome, out_dir, spec, repo_name, result)`, `PackageResult`.
- Produces: nothing new.

- [ ] **Step 1: Write the failing test**

```python
def test_a_push_that_lands_is_recorded_even_when_gh_fails(tmp_path, monkeypatch):
    """A `gh` that is missing, unauthenticated or refused leaves the branch
    pushed; today the ledger reads READY_FOR_REVIEW with no branch at all."""
    monkeypatch.setattr(
        "saffron.phases.package.open_draft_pr",
        lambda *a, **k: (_ for _ in ()).throw(PackageError("gh: not authenticated")),
    )
    ledger, outcome, spec = _packaged_task(tmp_path)   # existing helper shape

    with pytest.raises(PackageError):
        package(...)

    row = ledger.task(outcome.task_id)
    assert row["branch"] == f"saffron/{spec.id}"
    assert row["pushed_sha"]
```

Follow whatever fixture `tests/test_package.py` already uses to drive `package()` with a fake remote; if the ledger accessor is named differently, use the existing one.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package.py -k gh_fails -v`
Expected: FAIL — `branch` is `None`.

- [ ] **Step 3: Write minimal implementation**

In `package()`, immediately after `push_with_lease` returns and **before** `open_draft_pr` is called, record what is already true:

```python
        # Recorded before the pull request, because the push already happened:
        # a `gh` that fails otherwise leaves a pushed branch the ledger cannot
        # name, and the operator has to know a re-run self-heals.
        ledger.record_push(outcome.task_id, branch=branch, pushed_sha=pushed)
```

If `Ledger` has no such method, add the narrowest one that writes those two columns on the task row, beside the existing task writers in `saffron/ledger.py`. The pull request URL keeps being written where it is written today, after `open_draft_pr` returns.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_package.py tests/test_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py saffron/ledger.py tests/test_package.py
git commit -m "fix(package): a pushed branch whose gh call failed was recorded nowhere but stdout"
```

---

### Task 10: `reverify` runs under the repo's `thread_env`, and `conftest.py` is gate config

**Files:**
- Modify: `saffron/phases/package.py:361-410` (`reverify`)
- Modify: `.saffron/policy.yaml`
- Test: `tests/test_package.py`, `tests/test_integrity.py`

**Interfaces:**
- Consumes: `policy.thread_env`, `cell_env(proxy_ip, thread_env)` as `session.py` uses it.
- Produces: nothing new.

Two unrelated one-liners, together because each is smaller than its own commit cycle deserves and both are about the same residual.

`reverify`'s cell gets `env={}` while the in-cell suite gets `cell_env(proxy_ip, policy.thread_env)`. Empty for Saffron, so no behaviour changes here — it removes a suite-drift vector by construction, the same argument as Task 4.

- [ ] **Step 1: Write the failing tests**

```python
def test_reverify_starts_its_cell_with_the_repo_thread_env(monkeypatch):
    """The two suites being subtracted must not run under different
    environments by construction (§5.7)."""
    seen: dict[str, dict] = {}
    monkeypatch.setattr(
        "saffron.cell.worktree.prepare_worktree",
        lambda **kwargs: seen.update(kwargs),
    )
    policy = Policy(thread_env={"TZ": "UTC"})
    ...  # drive reverify with the existing fake-cell fixture
    assert seen["env"]["TZ"] == "UTC"
```

```python
# tests/test_integrity.py
def test_a_conftest_edit_is_gate_config(...):
    """Collection happens inside the repo's own Python, so `census` cannot see
    a conftest that lies to --collect-only. `integrity` routes it to a person."""
    patterns = IntegrityPatterns(gate_config=["pyproject.toml", ".saffron/**", "**/conftest.py"])
    result = integrity_gate(_diff_touching("tests/conftest.py"), patterns, touches=[])
    assert result.status == "fail"
    assert any(f.code == "gate-config" for f in result.failures)
```

Use whatever the existing `integrity` tests name that failure code; do not invent one.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_package.py -k thread_env tests/test_integrity.py -k conftest -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

In `reverify`, thread `policy.thread_env` into the cell exactly as `run_one_cell` does — `env=cell_env(proxy_ip, policy.thread_env)` — rather than `env={}`.

In `.saffron/policy.yaml`, extend `gate_config`:

```yaml
  # Collection runs inside the repo's own Python, so `census` cannot see a
  # conftest that drops a test only when --collect-only is false. This does not
  # stop that; it routes it to a person.
  gate_config: ["pyproject.toml", ".saffron/**", "**/conftest.py"]
```

- [ ] **Step 4: Run the tests**

Run: `make check`
Expected: PASS. If this repo has a `conftest.py` under `tests/`, confirm the branch's own diff does not touch it — if it does, the spec's `touches` must declare it, which is the exemption working as designed.

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py .saffron/policy.yaml tests/test_package.py tests/test_integrity.py
git commit -m "fix(package): the two subtracted suites ran under different environments"
```

---

### Task 11: the three test gaps

**Files:**
- Test: `tests/test_report.py`, `tests/test_session.py`

**Interfaces:**
- Consumes: `saffron/report/pr_body.py`, `CellOutcome`.
- Produces: nothing.

All three from backlog item 11, each one assertion.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_report.py
def test_a_pipe_in_a_finding_claim_does_not_break_the_table():
    """`|` is likelier in a model-authored claim than in a gate message, and the
    findings and disagreements tables were never covered."""
    body = pr_body(_outcome_with_finding(claim="a | b splits the row"))
    rendered = [line for line in body.splitlines() if "splits the row" in line]
    assert rendered and rendered[0].count("|") == _expected_columns


def test_an_unanchored_finding_is_marked_not_anchored():
    """The half that makes drop rate visible (§5.5) — the existing test checks
    only that the claim renders."""
    body = pr_body(_outcome_with_finding(anchored=False))
    row = next(line for line in body.splitlines() if "unanchorable" in line)
    assert "| no |" in row
```

```python
# tests/test_session.py
def test_a_successful_outcome_carries_its_attempts_failures_reviews_and_rebuttal():
    """No test exercises these four on CellOutcome's success path."""
    outcome = _successful_outcome()
    assert outcome.attempts >= 1
    assert outcome.new_failures == []
    assert outcome.reviews
    assert outcome.rebut_result is not None
```

Read the real field names off `CellOutcome` and `pr_body` before writing these — the names above are from the backlog's prose, and the code is authoritative.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report.py tests/test_session.py -v`
Expected: FAIL on the new cases.

- [ ] **Step 3: Fix whatever they catch**

If the pipe-escaping helper already covers these tables, the first test passes immediately — keep it anyway; the gap was the coverage, not necessarily a defect. If it does not, apply the same escaping `_new_failures` uses.

- [ ] **Step 4: Run the tests**

Run: `make check`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_report.py tests/test_session.py
git commit -m "test(report): the escaping test covered one table and a claim is likelier to hold a pipe"
```

---

### Task 12: `DESIGN.md`, and closing items 11 and 12

**Files:**
- Modify: `DESIGN.md` (§5.1, §5.4, §5.7, the status line at `DESIGN.md:5`, and a new Appendix N)
- Modify: `docs/BACKLOG.md` (items 11 and 12)

**Interfaces:**
- Consumes: everything above.
- Produces: the record.

Add subsections; **never renumber**. Section numbers are an API and specs cite them.

- [ ] **Step 1: §5.1 — cell construction**

Add the default-branch fetch and the `/gates` mount to the per-task listing. Two lines: the fetch that sets `base_sha`, and the read-only bind mount at `/gates` extracted from the mirror at `base_sha`.

- [ ] **Step 2: §5.4 — the invariant, the gate source, the dirty-tree rule**

Add a subsection stating, in this order:

1. **The invariant:** anything that changes what the suite measures must appear in the patch a human reads. Not "the cell cannot lie" — a lie has to be *visible in the diff*.
2. **Gates are executed from a host-supplied copy at `base_sha`**, not from `/work`. Consequence, stated so it does not read as a bug: a task whose job is to change a gate is judged by the pre-change gate, and the new gate takes effect for the next task.
3. **The `committed` gate**, in the gate-role table beside `scope`, `integrity` and `census`: it fails an attempt whose worktree is dirty, because the gates measure `/work` and the patch is `base_sha..HEAD`.
4. **The residual, stated rather than left to be discovered:** a committed `conftest.py` that drops a test only when `collectonly` is false still defeats `census`. `census` buys exactness against an honest suite; the two changes above buy visibility against a dishonest one. Neither buys integrity, and no diff-shaped check will.

- [ ] **Step 3: §5.7 — the base, and the rebase wording**

The base is the head of the remote's default branch as of task start. And one sentence saying step 1's "rebase" is the intent while the v1 subsection's `git apply --3way` is the mechanism — the document never says so, and a reader meeting them in order thinks one contradicts the other.

- [ ] **Step 4: Appendix N, and the status line**

Bump the rev on `DESIGN.md:5` following the existing format, and write the appendix narrating what building this found. The convention every prior rev follows: what was measured, what it corrected, and any numbered principle it earned. At minimum it records the two things the spec found that the backlog did not — `github_slug` taking the host as the owner on a one-segment URL, and the baseline/head gate drift at `session.py:607` that pinning gates closes as a side effect.

- [ ] **Step 5: Close items 11 and 12**

Mark both **done** in `docs/BACKLOG.md` the way items 1 and 3 are: what shipped, and what turned out to be wrong about the item itself — measured, not re-reasoned. Item 11's "two-segment GitHub URL" description undercounts the failure, and item 12's framing of the two halves as independent is right but omits the baseline drift, which is the stronger reason for half (a).

- [ ] **Step 6: Verify and commit**

Run: `make check`
Expected: PASS

```bash
git add DESIGN.md docs/BACKLOG.md
git commit -m "docs(design): the base and the gate runner are now stated, not inherited"
```

---

## Self-Review

**Spec coverage.** Spec part 1 → Tasks 1, 2. Part 2 → Tasks 3, 4, 5. Part 2.1's baseline drift → closed by Task 4, recorded in Task 12. Part 3 → Tasks 6, 7. Part 4's residual → Task 10's `conftest.py` line and Task 12's §5.4 text. Part 5's four smalls → Tasks 8, 9, 10, and Task 12 step 3 for the rebase wording. Part 5's three test gaps → Task 11. Part 6 → Task 12. Part 7's three named tests → Tasks 5, 7, and Task 2's `needs_reverification` case, which is covered by Task 2's test asserting the base equals the remote head; if `package()` has no direct assertion that re-verification is skipped when nothing moved, add it to Task 9's file while it is open.

**Type consistency.** `export_gates` returns `dest` (the directory holding `.saffron/gates/`) in Task 3 and is mounted as `gates_dir` in Task 4, so `policy.gate_executables(Path("/gates"))` resolves to `/gates/.saffron/gates/<name>` — `policy.py` is untouched. `dirty_paths` returns `list[str]` in Task 6 and is consumed as `list[str]` by `committed_gate`. `fetch_default_branch` returns `(branch, head)` in Task 1 and is unpacked as `_, base_sha` in Task 2.

**Known soft spots, flagged rather than papered over.** Task 9's ledger accessor and Task 11's field names are written from the backlog's prose; the code is authoritative and the steps say so. Task 7 tests a claim rather than new code — if it fails, that is a finding about `repair_decision`, not a test to adjust.
