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


> **Revision 2.** A plan review against the tree at `3d4df2c` found twelve
> defects in revision 1, three of them blocking. Every one is applied below.
> The three that would have shipped green: `reverify` has its own
> `prepare_worktree` call (`package.py:406`) that revision 1 never mentioned;
> `tests/test_cli.py` stubs `subprocess.run` globally, so Task 2's replacement
> reaches a fake with no `returncode`; and `_stub_the_runtime`
> (`tests/test_session.py:325`) does not cover the two new runtime calls, so
> ~30 tests would shell out to a container that does not exist.

### Task 1: `fetch_default_branch` — one source for both ends

**Files:**
- Modify: `saffron/phases/package.py` (add after `default_branch`, `package.py:92-101`), `saffron/phases/package.py:485-491`
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: `default_branch(url, *, cwd) -> str` (`package.py:92`), `_run(cwd, *args)` (`package.py:61`), `PackageError`.
- Produces: `fetch_default_branch(mirror: Path, url: str) -> tuple[str, str]` returning `(branch_name, head_sha)`. Task 2 calls it from `cli.py`.

**Not a pure refactor, despite appearances.** Two behaviour changes, both deliberate, both stated here because revision 1 claimed there were none:

1. `assert_base_objects` (`package.py:103`) *reads* the mirror's object store and the fetch *writes* it. If `base_sha` is reachable from the remote's default branch but missing from the mirror, running the fetch first would supply the objects and turn today's `PackageError` into a pass. So in `package()` the assert moves **above** the new call — `default_branch` is an `ls-remote` that writes nothing, so nothing else shifts.
2. The new function raises when the remote reports no head. Today `package.py:491` would carry an empty string forward.

- [ ] **Step 1: Write the failing test**

```python
def test_fetch_default_branch_reports_the_remote_head(tmp_path):
    """The head the mirror now holds, not the one the caller happened to have."""
    origin = _repo_with_commit(tmp_path / "origin")
    head = _rev_parse(origin, "HEAD")

    mirror = ensure_mirror(origin, tmp_path / "mirror.git")
    branch, fetched = fetch_default_branch(mirror, str(origin))

    assert fetched == head
    assert branch in ("main", "master")
    # The object is in the mirror, which is what prepare_worktree needs.
    assert subprocess.run(
        ["git", "-C", str(mirror), "cat-file", "-e", f"{fetched}^{{tree}}"]
    ).returncode == 0


def test_fetch_default_branch_refuses_an_unreachable_remote(tmp_path):
    origin = _repo_with_commit(tmp_path / "origin")
    mirror = ensure_mirror(origin, tmp_path / "mirror.git")
    with pytest.raises(PackageError):
        fetch_default_branch(mirror, str(tmp_path / "nowhere"))
```

`tests/test_package.py` has no `_repo_with_commit` or `_rev_parse` helper — write them at the top of the file. `_repo_with_commit(path)` should `mkdir`, `git init -q`, write a file, `git add -A`, and `git -c user.email=t@t -c user.name=T commit -qm first`, returning the path. `_rev_parse(repo, ref)` returns the stripped stdout of `git -C repo rev-parse <ref>`. Add `fetch_default_branch` to the `saffron.phases.package` import block at `tests/test_package.py:23` and `from saffron.repos.mirror import ensure_mirror`.

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

After — note the assert is now **first**, which is what keeps its meaning:

```python
    # Before the fetch, not after: the fetch writes the object store this
    # reads, and would otherwise supply the very objects it is checking for.
    assert_base_objects(mirror, base_sha)
    default, fetch_head = fetch_default_branch(mirror, url)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py
git commit -m "refactor(package): the two ends of the base comparison read one source"
```

---

### Task 2: the base is the remote's default-branch head

**Files:**
- Modify: `saffron/cli.py:114-119`, and the import at `saffron/cli.py:8`
- Test: `tests/test_cli.py:40`, `:90`, `:137`, plus one new case

**Interfaces:**
- Consumes: `fetch_default_branch(mirror, url) -> tuple[str, str]` (Task 1), `package_phase.real_remote(repo) -> str` (`package.py:75`). `package_phase` is already imported at `cli.py:14`.
- Produces: nothing new. `CellSpec.base_sha` now holds the remote's default-branch head.

**Three existing tests break, and the fix is not to restore the old code.** `tests/test_cli.py:40`, `:90` and `:137` each do:

```python
monkeypatch.setattr("subprocess.run", lambda *a, **k: type("P", (), {"stdout": "a" * 40})())
```

stubbing the `git rev-parse HEAD` this task deletes. `package._run` (`package.py:64`) also calls `subprocess.run`, so the replacement hits the same fake — which has no `returncode`, so `real_remote` (`package.py:77`) raises `AttributeError`, `cli.main`'s handler (`cli.py:86`) turns it into exit 2, and the exit-code assertions read `[2, 2, 2]`. Replace that global stub in all three with the narrower one below.

**One unstated behaviour change, now stated.** `real_remote` raises `PackageError` on a repo with no `origin`. Today `saffron cell` runs fine against one — `session.py:487-490` catches exactly that and comments *"A repo with no origin is still runnable — it just cannot be packaged."* After this task it exits 2 before the cell starts. That is the right trade (a task with no reachable default branch has no base), and Task 12 records it in §5.1.

- [ ] **Step 1: Repoint the three existing stubs**

In each of the three tests, replace the `subprocess.run` line with:

```python
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda repo: "https://github.com/o/r.git")
    monkeypatch.setattr(
        "saffron.phases.package.fetch_default_branch", lambda mirror, url: ("main", "a" * 40)
    )
```

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS — these stubs satisfy the *current* code too (it still calls `subprocess.run` for `rev-parse`, which is now unstubbed but harmless: the test repos are real git repos). If any test now fails because `rev-parse` returns a real sha where it expected `"a" * 40`, assert on the shape rather than the literal.

- [ ] **Step 2: Write the failing test**

```python
def test_the_base_is_the_remote_default_branch_not_the_checkout(tmp_path, monkeypatch):
    """A task started from a feature branch is still cut from the default branch.

    The property §4.2 needs: a task's base must not depend on where the
    operator was standing.
    """
    repo = _repo_with_commit(tmp_path / "repo")
    default_head = _rev_parse(repo, "HEAD")
    # The bare clone MUST be taken before the branch switch: `git clone --bare`
    # copies the source's HEAD, and `default_branch` reads that symref.
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(repo), str(remote)], check=True)
    _git(repo, "remote", "add", "origin", str(remote))

    _git(repo, "checkout", "-q", "-b", "joel/feature")
    (repo / "extra.txt").write_text("local only\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "local only")
    assert _rev_parse(repo, "HEAD") != default_head

    captured: dict[str, str] = {}

    def _capture(cell_spec, **kwargs):
        captured["base_sha"] = cell_spec.base_sha
        raise SystemExit(0)

    monkeypatch.setattr("saffron.cli.run_one_cell", _capture)
    with pytest.raises(SystemExit):
        cli._run_cell(_namespace(repo, tmp_path), Ledger(tmp_path / "l.db"), tmp_path / "out")

    assert captured["base_sha"] == default_head
```

`_namespace(repo, tmp_path)` builds the `argparse.Namespace` `_run_cell` reads: `repo`, `spec`, `home`, `budget`, `max_attempts`. `_run_cell` calls `load_spec(args.spec)` at `cli.py:108`, so `spec` must be a real spec file on disk — write a minimal one with valid frontmatter (see `tests/test_intake.py` for the shape). `tests/test_cli.py` has no `_run_cell`-level case to model on; this is the first.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -k default_branch_not_the_checkout -v`
Expected: FAIL — `base_sha` is the feature-branch tip.

- [ ] **Step 4: Write minimal implementation**

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

Then `uv run ruff check saffron/cli.py` — `subprocess` is used only at `cli.py:8` and `:114`, so it becomes unused and ruff reports `F401`. Remove the import.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_cli.py -v && uv run ruff check saffron/`
Expected: PASS, clean.

- [ ] **Step 6: Commit**

```bash
git add saffron/cli.py tests/test_cli.py
git commit -m "fix(cli): a task's base was whatever branch the operator was standing on"
```

---

### Task 3: `export_gates` — the base tree's gates, on the host

**Files:**
- Modify: `saffron/repos/mirror.py` (add `import tarfile`, then the function at the end)
- Test: `tests/test_mirror.py`

**Interfaces:**
- Consumes: `GitError` (`mirror.py:19`), `shutil` and `subprocess` (already imported at `mirror.py:11-12`).
- Produces: `export_gates(mirror: Path, sha: str, dest: Path) -> Path`. Returns `dest`, whose only content is `.saffron/gates/`. Tasks 4 mounts `dest` at `/gates`, so `policy.gate_executables(Path("/gates"))` resolves to `/gates/.saffron/gates/<name>` with no change to `policy.py`.

It calls `subprocess.run` directly rather than the module's `_run`, because it needs to redirect stdout to a file. Consequence, accepted: a missing `git` binary raises `OSError` here instead of the `GitError` the rest of the module raises (`tests/test_mirror.py:125` covers that case for `_run`). Mark it with a one-line comment.

**Measured before this plan was written** (against a real bare mirror, git 2.50.1, Python 3.12.12 — `pyproject.toml:5` pins `>=3.12`, so `filter=` is safe):

- `git -C <bare> archive --format=tar <sha> .saffron/gates` → rc 0, member `.saffron/gates/tests` mode `-rwxrwxr-x`.
- A tree with no `.saffron/gates` → rc 128, so the refusal case fires on the returncode branch.
- `tarfile.extractall(..., filter="data")` → `0o100755`, `os.access(..., X_OK)` true. The exec bit survives.

- [ ] **Step 1: Write the failing test**

`tests/test_mirror.py` has `git(repo, *args)` at `:16` and an `origin` fixture at `:23`; it has no `_repo_with_commit`, `_commit_all` or `_rev_parse`. Use the existing `git` helper and add `import os`.

```python
def test_export_gates_takes_the_tree_at_the_sha(tmp_path, origin):
    gates = origin / ".saffron" / "gates"
    gates.mkdir(parents=True)
    (gates / "tests").write_text("#!/bin/sh\necho honest\n")
    (gates / "tests").chmod(0o755)
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", "gates")
    base = git(origin, "rev-parse", "HEAD").strip()

    (gates / "tests").write_text("#!/bin/sh\necho lying\n")
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", "a gate that lies")

    mirror = ensure_mirror(origin, tmp_path / "mirror.git")
    dest = export_gates(mirror, base, tmp_path / "gates-out")

    exported = dest / ".saffron" / "gates" / "tests"
    assert "honest" in exported.read_text()
    assert "lying" not in exported.read_text()
    # A gate that is not executable reads identically to one that is missing.
    assert os.access(exported, os.X_OK)


def test_export_gates_refuses_a_tree_with_no_gates(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "mirror.git")
    with pytest.raises(GitError):
        export_gates(mirror, git(origin, "rev-parse", "HEAD").strip(), tmp_path / "out")
```

Check the `origin` fixture's actual return type and whether `git()` returns stdout before using it this way; adapt rather than assume.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mirror.py -k export_gates -v`
Expected: FAIL with `ImportError: cannot import name 'export_gates'`

- [ ] **Step 3: Write minimal implementation**

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
    # subprocess.run, not _run: stdout goes to a file rather than a pipe.
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

### Task 4: mount the gates read-only, in both cells that run a suite

**Files:**
- Modify: `saffron/cell/worktree.py:17` (`GATES_MOUNT`), `:21-31` (`mounts`), `:33-50` (`prepare_worktree` signature), `:96-105` (the `mounts(...)` call)
- Modify: `saffron/cell/session.py:478`, `:565-575`, and the `task_dir.mkdir` at `:612`
- Modify: `saffron/phases/package.py:361-368` (`reverify` signature), `:406-417` (its `prepare_worktree`), `:424` (its gate paths), `:374-377` (its docstring)
- Test: `tests/test_worktree.py:52`, `:94`, `:129`, `:172`, `:204`; `tests/test_session.py:325` (`_stub_the_runtime`); `tests/test_package.py`

**Interfaces:**
- Consumes: `export_gates(mirror, sha, dest) -> Path` (Task 3), `runtime.Mount(kind, source, target, readonly)` (`runtime.py:62`).
- Produces: `worktree.GATES_MOUNT = "/gates"`; `mounts(volume, state_volume, gates_dir)`; `prepare_worktree(..., gates_dir: Path)`; `reverify(..., gates_dir: Path)`.

`gates_dir` is a **required** argument, like `network` and `env` before it. v0.5 shipped a cell where an omitted argument meant every containment control applied to a different container (Appendix I); a defaulted `gates_dir` would mean a cell silently falling back to `/work`'s gates with nothing to notice it.

**`reverify` is in scope and cannot be deferred.** There are two production `prepare_worktree` call sites — `session.py:565` and `package.py:406` — and a required argument breaks the second the moment it is added. Worse, `package.py:424` builds its gate paths from `WORKTREE_MOUNT`, so leaving it alone would have `reverify` running the **patch's own** gates while the in-cell suite runs host-pinned ones: the two suites `package.py:440` subtracts would come from different executables, which is precisely the drift the spec's part 2.1 exists to close. `reverify` exports gates at `new_base_sha` — the new default-branch head, a tree the cell never wrote — and uses them for both of its runs.

Its docstring at `package.py:374-377` currently says the applied tree carries `.saffron/gates/*` *"exactly as the patch left them"*. That stops being true and must be rewritten.

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

- [ ] **Step 3: `worktree.py`**

Beside `WORKTREE_MOUNT`:

```python
GATES_MOUNT = "/gates"
```

```python
def mounts(volume: str, state_volume: str, gates_dir: Path) -> list[runtime.Mount]:
    """The mounts every cell gets, and why they are separate.

    Session state and any credential file must not live in the tree the agent
    can write, that the scope gate walks, and that gets patch-exported. The
    gates are read-only and come from a sha the cell never wrote: the
    executables that judge a task are not the ones the task can edit (§5.4).
    """
    return [
        runtime.Mount("volume", volume, WORKTREE_MOUNT),
        runtime.Mount("volume", state_volume, STATE_MOUNT),
        runtime.Mount("bind", str(gates_dir), GATES_MOUNT, readonly=True),
    ]
```

Add `gates_dir: Path` to `prepare_worktree`'s keyword-only parameters, no default, beside `network` and `env`. Pass it at the `run_detached` call: `mounts=mounts(volume, state, gates_dir)`.

- [ ] **Step 4: `session.py`**

At `:478`:

```python
    # Cell-side, and from the read-only mount rather than /work: an in-cell
    # edit to a gate — committed or not — never reaches the runner (§5.4).
    gates = policy.gate_executables(Path(worktree.GATES_MOUNT))
```

Move the `task_dir.mkdir(parents=True, exist_ok=True)` from `:612` up to just before the `prepare_worktree` call at `:565` — the gates must exist before the container is created. Nothing between `:502` (where `task_dir` is bound) and `:612` touches the directory. Then:

```python
        task_dir.mkdir(parents=True, exist_ok=True)
        gates_dir = mirror_ops.export_gates(mirror, spec.base_sha, task_dir / "gates")
```

and add `gates_dir=gates_dir,` to `prepare_worktree(...)`. `_drive_cell` (`session.py:452`, **not** `run_one_cell`, which is the nine-line wrapper at `:418`) uses **function-local** imports at `:462-471` — deliberately. Add `from saffron.repos import mirror as mirror_ops` there, in the same style, not at module level.

- [ ] **Step 5: `package.py`'s `reverify`**

Add `gates_dir: Path` to `reverify`'s keyword-only parameters. In `package()`, build it before the call:

```python
            gates_dir = mirror_ops.export_gates(
                mirror, fetch_head, out_dir / "package" / spec.id / "gates"
            )
```

Pass `gates_dir=gates_dir` to `prepare_worktree` at `:406`, and change `:424` to `policy.gate_executables(Path(worktree.GATES_MOUNT))`. Rewrite the docstring at `:374-377`: both of `reverify`'s runs use gates exported from `new_base_sha`, so the two suites it subtracts come from one set of executables and the patch's own `.saffron/gates/*` are never executed.

- [ ] **Step 6: Fix every existing call site**

Five non-cell and cell `prepare_worktree` calls in `tests/test_worktree.py` — `:52`, `:94`, `:129`, `:172`, `:204` — each needs `gates_dir`. Build a real directory with an empty `.saffron/gates/` under `tmp_path`; the mount source must exist.

And `_stub_the_runtime` (`tests/test_session.py:325`) must gain the new call, or ~30 `_drive` tests run `git archive` against `tmp_path / "m.git"`, which is never created:

```python
    monkeypatch.setattr("saffron.repos.mirror.export_gates", lambda mirror, sha, dest: dest)
```

- [ ] **Step 7: Run the tests**

Run: `make check`
Expected: PASS. Then `uv run pytest -m cell -v` — expected PASS.

- [ ] **Step 8: Commit**

```bash
git add saffron/cell/worktree.py saffron/cell/session.py saffron/phases/package.py tests/
git commit -m "fix(cell): the gate runner lived in the tree the cell could rewrite"
```

---

### Task 5: prove it from inside a cell

**Files:**
- Test: `tests/test_worktree.py` (it already holds the cell-marked worktree cases and the `network` fixture)

**Interfaces:**
- Consumes: everything from Tasks 3 and 4.
- Produces: nothing.

Appendix I's rule binds here: **start the cell the way production does and probe from inside it.** A test that asserts the mount list is a test of a list.

Two corrections to revision 1, both from the review. There is no `_unique_names`, `_teardown`, `CELL_IMAGE` or `_repo_with_gate` in any test file — model the setup on `_seed_repo` and the `network` fixture (`tests/test_worktree.py:15`). And use that real `network` fixture rather than `network="none"`: every existing cell test starts a real network, and nothing establishes the runtime accepts `none`.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.cell
def test_a_gate_edited_inside_the_cell_never_runs(tmp_path, network):
    repo = _seed_repo(tmp_path)          # then add .saffron/gates/demo and commit
    ...
    gates_dir = export_gates(mirror, base, tmp_path / "gates-out")
    worktree.prepare_worktree(..., network=network, env={}, gates_dir=gates_dir)

    # The agent's move: rewrite the gate and commit, so no diff-reading gate
    # can tell it from ordinary work. Heredoc, not nested quotes: POSIX sh has
    # no backslash escape inside single quotes, and revision 1's one-liner
    # silently failed — which would have passed this test for the wrong reason.
    runtime.exec_(container, ["sh", "-euc", """
cd /work
cat > .saffron/gates/demo <<'GATE'
#!/bin/sh
printf '{"gate":"demo","status":"pass","tool":"lying 9.9"}\\n'
GATE
chmod +x .saffron/gates/demo
git add -A && git commit -qm 'tune the gate'
"""])
    # The edit must have landed, or the assertion below proves nothing.
    assert "lying" in runtime.exec_(
        container, ["cat", "/work/.saffron/gates/demo"]
    ).stdout

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
```

The honest gate written into the repo before the mirror is made should `printf '{"gate":"demo","status":"pass","tool":"honest 1.0"}\n'`.

- [ ] **Step 2: Run it**

Build the images first if absent:

```bash
container build -t saffron/cell-base:python -f images/cell-base.python.Dockerfile .
```

Run: `uv run pytest -m cell -k gate_edited_inside -v`
Expected: PASS. Confirm the `"lying" in ...` assertion is what proves the setup worked — if that one fails, the test is broken, not the code.

- [ ] **Step 3: Run the whole cell suite**

Run: `uv run pytest -m cell -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_worktree.py
git commit -m "test(cell): the gate-source claim had no test that could go red"
```

---

### Task 6: `committed` — the tree the gates measure is the tree the patch contains

**Files:**
- Create: `saffron/gates/core/committed.py`
- Modify: `saffron/cell/worktree.py` (add `dirty_paths`), `saffron/cell/session.py:591-603` (`_suite`), `tests/test_session.py:325` (`_stub_the_runtime`)
- Test: `tests/test_committed.py` (new), `tests/test_worktree.py`

**Interfaces:**
- Consumes: `GateResult`, `Failure` (`contract.py:42-74`); `runtime.CellRuntimeError` (`runtime.py:45`); `_git(container, *args)` (`worktree.py:130`).
- Produces: `worktree.dirty_paths(container: str) -> list[str]`; `committed.committed_gate(dirty: list[str]) -> GateResult`.

Shaped like `scope`: `session.py` reads the cell, the gate is a pure function that executes nothing. No `tool` field — core gates are constructed directly and never claim to have run one, and `run_gate`'s pass/fail-without-tool rule (`runner.py:146-152`) applies only to executed gates.

**"One repair turn, then abort" needs no new control flow, and the review confirmed the trace.** A dirty tree produces `fail` with one failure per path; the baseline tree is freshly cloned so `subtract_baseline` cancels nothing; `previous = new` is assigned at `session.py:331` after the decision and before `repair(new)`; `repair_decision` returns `repair` on attempt 1 and `no-progress` → `EXHAUSTED` on identical failures at attempt 2. `suite_drift` sees `tool=None` on both sides and reports nothing.

`git status --porcelain -z` parsing was measured: `' M keep.txt\x00R  new.txt\x00old.txt\x00?? untracked.py\x00'`. The rename entry carries the **new** path at `entry[3:]` and the source follows as the next NUL field, so the skip drops exactly the right chunk. Consequence worth knowing: a rename's source deletion never appears in the failure list.

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

And in `tests/test_worktree.py`, cell-marked:

```python
@pytest.mark.cell
def test_dirty_paths_sees_an_uncommitted_edit(tmp_path, network):
    ...  # prepare_worktree as in Task 5
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

In `session.py`'s `_suite`, beside the other host-side core gates. Left-to-right evaluation matters: `dirty_paths` is read before `run_suite` can leave test artifacts in `/work`.

```python
            results = [
                scope_gate(changed, spec.touches, diff=diff),
                integrity_gate(diff, policy.integrity, spec.touches),
                committed_gate(worktree.dirty_paths(container)),
                *run_suite(gates, cwd=repo, executor=executor),
            ]
```

Import `committed_gate` beside the other core-gate imports.

- [ ] **Step 4: Extend the runtime stub**

`_stub_the_runtime` (`tests/test_session.py:325`) does not cover `dirty_paths`, so ~30 `_drive` tests would exec against a container that does not exist. Add:

```python
    monkeypatch.setattr("saffron.cell.worktree.dirty_paths", lambda container: [])
```

- [ ] **Step 5: Run the tests**

Run: `make check`
Expected: PASS. Existing `session.py` tests that assert on the gate list need `committed` added; it is `pass` at baseline, which a freshly cloned worktree gives.

- [ ] **Step 6: Commit**

```bash
git add saffron/gates/core/committed.py saffron/cell/worktree.py saffron/cell/session.py tests/
git commit -m "fix(gates): an uncommitted edit was live for the suite and absent from the patch"
```

---

### Task 7: one repair turn, then the loop's own rule

**Files:**
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `session.repair_loop` (`session.py:292`), `committed_gate` (Task 6). `tests/test_session.py` imports `session` as a module and calls `session.repair_loop` (`:229`) — follow that, and import `committed_gate` at the top.
- Produces: nothing.

Task 6 claims the existing loop already gives "one repair turn, then abort". The review traced it and it holds; this task is the test that keeps it holding.

- [ ] **Step 1: Write the test**

```python
def _dirty_suite(paths):
    return [committed_gate(paths)]


def test_a_dirty_tree_buys_one_repair_turn():
    """Attempt 1 repairs, attempt 2 is clean."""
    calls: list[str] = []
    trees = iter([["a.py"], []])

    state, attempts, _ = session.repair_loop(
        run_gates=lambda: _dirty_suite(next(trees)),
        baseline=_dirty_suite([]),
        max_attempts=4,
        repair=lambda new: calls.append("repair"),
        watch=lambda _: None,
    )
    assert calls == ["repair"]
    assert state == "READY_FOR_REVIEW"
    assert attempts == 2


def test_a_tree_still_dirty_after_the_repair_turn_ends_the_attempt():
    calls: list[str] = []

    state, attempts, new = session.repair_loop(
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

`list.append` returns `None`, so the lambda does not stop the loop early — that is load-bearing, not incidental.

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/test_session.py -k dirty -v`
Expected: PASS. **If not** — if `repair` is called more than once, or the state is not `EXHAUSTED` — stop and say so rather than changing the test: the design chose one repair turn, and a loop that gives four is a finding about `repair_decision`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_session.py
git commit -m "test(session): the one-repair-turn claim rested on a rule nothing exercised"
```

---

### Task 8: `github_slug` refuses instead of guessing

**Files:**
- Modify: `saffron/phases/package.py:31` (`_SLUG`), `:85-90`
- Test: `tests/test_package.py:59-68`

**Interfaces:**
- Consumes: `PackageError`.
- Produces: `github_slug` raises `PackageError` on anything that is not a recognisable forge remote.

Measured, this tree: three of five real inputs return a wrong answer. `https://example.com/repo` → `example.com/repo` takes the **host** as the owner, a case the backlog does not name.

`tests/test_package.py:59-68` **already parametrizes the four accepting shapes** — extend that test rather than duplicating it. Only the refusal cases are new.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize(
    "url",
    [
        "/Users/joel/Code/saffron",             # measured: -> "Code/saffron"
        "git@gitlab.com:group/owner/repo.git",  # measured: -> "owner/repo"
        "https://example.com/repo",             # measured: -> "example.com/repo"
    ],
)
def test_github_slug_refuses_what_is_not_a_forge_remote(url):
    """A wrong slug reaches `gh` as a repository that cannot exist, and a
    local-path origin is exactly what session.py falls back to."""
    with pytest.raises(PackageError):
        github_slug(url)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package.py -k github_slug -v`
Expected: FAIL — all three return a slug instead of raising.

- [ ] **Step 3: Write minimal implementation**

```python
# Anchored on the forge host, not on "the last two segments": the old pattern
# read a local path as `Code/saffron` and a one-segment URL as `host/repo`.
_SLUG = re.compile(r"(?:^|[@/.])github\.com[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$")
```

The `[@/.]` boundary is deliberate — without it `https://notgithub.com/a/b.git` still matches. Verify all four accepting shapes in the existing parametrize still pass, `ssh://git@github.com/jtmcn/saffron.git` included.

Update the docstring:

```python
def github_slug(url: str) -> str:
    """`owner/repo`, from either URL shape git writes — or a refusal.

    Guessing is worse than failing: the slug reaches `gh`, and a plausible
    wrong one names a repository that does not exist.
    """
```

The existing `raise PackageError(...)` below needs no change.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS. `github_slug` has one caller, `package.py:484`.

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py
git commit -m "fix(package): a local path read as a slug that named a repo nobody owns"
```

---

### Task 9: record the pushed sha before the pull request, not after

**Files:**
- Modify: `saffron/ledger.py` (add beside `set_task_package`, `:332`), `saffron/phases/package.py` (the `open_draft_pr` call site)
- Test: `tests/test_package.py`, `tests/test_ledger.py`

**Interfaces:**
- Consumes: `Ledger.queue_lines()` (`ledger.py:439`) — it already exposes `pushed_sha`, so no read accessor is needed.
- Produces: `Ledger.record_push(task_id: int, pushed_sha: str) -> None`.

**Half of item 11's claim is already true.** `branch` is written at insert time by `create_task` (`ledger.py:249-253`) from `spec.branch` (`session.py:497`, set in `cli.py:124`). Only `pushed_sha` is genuinely absent — it is written solely by `set_task_package` (`ledger.py:332-348`), which runs after `open_draft_pr`. So the fix is one column, not two, and the task shrinks accordingly. There is no `Ledger.task()` accessor and none is needed.

- [ ] **Step 1: Write the failing test**

```python
def test_a_push_that_lands_is_recorded_even_when_gh_fails(tmp_path, monkeypatch):
    """A `gh` that is missing, unauthenticated or refused leaves the branch
    pushed; today the ledger has no sha for it."""
    monkeypatch.setattr(
        "saffron.phases.package.open_draft_pr",
        lambda *a, **k: (_ for _ in ()).throw(PackageError("gh: not authenticated")),
    )
    ...  # drive package() with the existing fixture
    row = next(r for r in ledger.queue_lines() if r["task_id"] == task_id)
    assert row["pushed_sha"]
```

Model the driving on whatever fixture `tests/test_package.py` already uses for `package()` with a fake remote, and the `queue_lines` read on `tests/test_ledger.py:201-203`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package.py -k gh_fails -v`
Expected: FAIL — `pushed_sha` is `None`.

- [ ] **Step 3: Write minimal implementation**

In `saffron/ledger.py`, beside `set_task_package`:

```python
    def record_push(self, task_id: int, pushed_sha: str) -> None:
        """The push already happened, so it is recorded before the pull request
        is opened: a `gh` that fails otherwise leaves a pushed branch the
        ledger cannot name (§5.7)."""
        self._db.execute(
            "UPDATE tasks SET pushed_sha = ?, updated_at = datetime('now') "
            "WHERE task_id = ?",
            (pushed_sha, task_id),
        )
        self._db.commit()
```

In `package()`, immediately after `push_with_lease` returns and **before** `open_draft_pr`:

```python
        ledger.record_push(outcome.task_id, pushed)
```

`set_task_package` keeps writing all four columns at the end; this is an earlier, narrower write of one of them.

- [ ] **Step 4: Run the tests**

Run: `make check`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add saffron/ledger.py saffron/phases/package.py tests/
git commit -m "fix(package): a pushed branch whose gh call failed had no sha in the ledger"
```

---

### Task 10: `conftest.py` is gate config

**Files:**
- Modify: `.saffron/policy.yaml`
- Test: `tests/test_integrity.py`

**Interfaces:**
- Consumes: `IntegrityPatterns(gate_config=[...])` (`policy.py:44`), `integrity_gate(diff, patterns, touches)` (`integrity.py:201`).
- Produces: nothing.

`reverify`'s `thread_env` moved into Task 4 — it is one line of the same call `gates_dir` changes, and splitting them would leave that cell half-updated across a commit.

Collection runs inside the repo's own Python, so `census` cannot see a `conftest.py` that drops a test only when `collectonly` is false. This does not stop that; it routes it to a person. There is **no `conftest.py` anywhere in this repo today**, so the change is inert here — which is the design intent, not an oversight.

The failure code is `gate-config-changed` (`integrity.py:266`), not `gate-config`.

- [ ] **Step 1: Write the failing test**

```python
def test_a_conftest_edit_is_gate_config():
    """`census` cannot see a conftest that lies to --collect-only; `integrity`
    routes it to a person."""
    patterns = IntegrityPatterns(
        gate_config=["pyproject.toml", ".saffron/**", "**/conftest.py"]
    )
    result = integrity_gate(_diff_touching("tests/conftest.py"), patterns, [])
    assert result.status == "fail"
    assert any(f.code == "gate-config-changed" for f in result.failures)
```

Use whatever diff-building helper `tests/test_integrity.py` already has rather than writing `_diff_touching` fresh.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_integrity.py -k conftest -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

In `.saffron/policy.yaml` — two comment lines, not three (`CLAUDE.md` caps YAML comments at 1–2):

```yaml
  # Collection runs in the repo's own Python, so `census` cannot see a conftest
  # that hides a test from the runner. This routes the edit to a person.
  gate_config: ["pyproject.toml", ".saffron/**", "**/conftest.py"]
```

- [ ] **Step 4: Run the tests**

Run: `make check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .saffron/policy.yaml tests/test_integrity.py
git commit -m "fix(policy): a conftest could hide a test from the runner and from every gate"
```

---

### Task 11: the three test gaps

**Files:**
- Test: `tests/test_report.py:335`, plus new cases; `tests/test_session.py`

**Interfaces:**
- Consumes: `render_pr_body(spec, gates, new_failures, *, base_sha, head_sha, added, removed, transcript_path, reviews=..., rebut_result=..., ...)` (`pr_body.py:53`) — **not** `pr_body(outcome)`; it does not take a `CellOutcome`. The file's existing helpers are `SPEC` (`:20`), `RESULTS` (`:35`), `body()` (`:50`) and `_finding(**kw)` (`:251`). Use them.
- Produces: nothing.

Three corrections from the review. `CellOutcome` really does have `attempts`, `new_failures`, `reviews`, `rebut_result` (`session.py:180-185`) — the plan's earlier hedge was wrong. `_findings` already routes `claim` through `_cell` (`pr_body.py:191`), so the pipe test should pass on the first run; keep it, because the gap was the coverage. And `test_an_unanchored_finding_still_appears` **already exists** at `tests/test_report.py:335` — amend it rather than adding a second test beside it.

**The pipe assertion must discount escapes.** `_cell` escapes as `\|` (`pr_body.py:107`), so a raw `count("|")` counts the escaped one. The correct idiom is already in the file at `tests/test_report.py:239`: `row.count("|") - row.count("\\|") == 5`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_report.py
def test_a_pipe_in_a_finding_claim_does_not_break_the_table():
    """`|` is likelier in a model-authored claim than in a gate message, and the
    findings and disagreements tables were never covered."""
    rendered = body(reviews=[_review(_finding(claim="a | b splits the row"))])
    row = next(line for line in rendered.splitlines() if "splits the row" in line)
    assert row.count("|") - row.count("\\|") == _columns_in_the_findings_table
```

Read the real column count off the header row rather than hardcoding a guess, and do the same for the disagreements table in a second case.

Then amend the existing `test_an_unanchored_finding_still_appears` (`:335`) with the assertion it lacks — that the row is marked `no`, which is the half that makes drop rate visible (§5.5).

```python
# tests/test_session.py
def test_a_successful_outcome_carries_its_attempts_failures_reviews_and_rebuttal():
    """No test exercises these four on CellOutcome's success path."""
    outcome = ...  # drive a green run with the existing _drive helper
    assert outcome.attempts >= 1
    assert outcome.new_failures == []
    assert outcome.reviews
    assert outcome.rebut_result is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report.py tests/test_session.py -v`
Expected: the amended anchoring assertion and the `CellOutcome` case FAIL; the pipe cases may pass immediately, which is fine — the gap was coverage, not necessarily a defect.

- [ ] **Step 3: Fix whatever they catch**

If a table does not escape, apply the same `_cell` treatment `_new_failures` uses.

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
- Modify: `DESIGN.md:5` (the status line, currently rev 15), §5.1, §5.4 (the gate-role table is at `:621-632`), §5.7, and a new **Appendix N** (the last is M at `:2041`)
- Modify: `docs/BACKLOG.md:539` (item 11), `:614` (item 12)

**Interfaces:**
- Consumes: everything above.
- Produces: the record.

Add subsections; **never renumber**.

- [ ] **Step 1: §5.1 — cell construction**

The default-branch fetch that sets `base_sha`, and the read-only `/gates` mount extracted from the mirror at `base_sha`. Plus the consequence Task 2 introduced: a repo with no reachable `origin` can no longer start a cell, where `session.py:487-490` previously allowed one that simply could not be packaged.

- [ ] **Step 2: §5.4 — the invariant, the gate source, the dirty-tree rule**

1. **The invariant:** anything that changes what the suite measures must appear in the patch a human reads. Not "the cell cannot lie" — a lie has to be *visible in the diff*.
2. **Gates are executed from a host-supplied copy**, at `base_sha` for a task's cell and at `new_base_sha` for `reverify`'s, never from `/work`. Consequence, stated so it does not read as a bug: a task whose job is to change a gate is judged by the pre-change gate, and the new gate takes effect for the next task.
3. **`committed`**, in the gate-role table at `:621-632` beside `scope`, `integrity` and `census`.
4. **The residual:** a committed `conftest.py` that drops a test only when `collectonly` is false still defeats `census`. `census` buys exactness against an honest suite; the gate source and the dirty-tree rule buy visibility against a dishonest one. Neither buys integrity, and no diff-shaped check will.
5. **One sentence on §2.1's "seam to watch" (`DESIGN.md:150`)**: `dirty_paths` widens core's in-cell git surface, and the boundary holds only because the gate itself stays a pure function over a list of paths.

- [ ] **Step 3: §5.7 — the base, and the rebase wording**

The base is the head of the remote's default branch as of task start. And one sentence saying step 1's "rebase" is the intent while the v1 subsection's `git apply --3way` is the mechanism.

- [ ] **Step 4: Appendix N, and the status line**

Bump `DESIGN.md:5` following the existing format. The appendix records what building this found, at minimum:

- `github_slug` takes the **host** as the owner on a one-segment URL — three of five real inputs wrong, not the two item 11 names.
- The baseline/head gate drift at `session.py:607`, which pinning gates closes as a side effect and which is the stronger of the two reasons for doing it.
- `reverify` had its own cell, its own `prepare_worktree`, and its own `WORKTREE_MOUNT` gate paths — a second copy of the same seam, found by review rather than by running.
- `branch` was already recorded at insert time; only `pushed_sha` was missing. Item 11 overstated it.

- [ ] **Step 5: Close items 11 and 12**

Mark both **done** in `docs/BACKLOG.md` the way items 1 and 3 are: what shipped, and what turned out to be wrong about the item itself — measured, not re-reasoned. Item 11's "two-segment GitHub URL" undercounts the failure and its branch/`pushed_sha` claim is half true; item 12's two halves are right but omit both the baseline drift and `reverify`'s second copy of the seam.

- [ ] **Step 6: Verify and commit**

Run: `make check`
Expected: PASS

```bash
git add DESIGN.md docs/BACKLOG.md
git commit -m "docs(design): the base and the gate runner are now stated, not inherited"
```

---

## Self-Review (revision 2)

**Spec coverage.** Part 1 → Tasks 1, 2. Part 2 → Tasks 3, 4, 5. Part 2.1's baseline drift → Task 4, recorded in Task 12. Part 3 → Tasks 6, 7. Part 4's residual → Task 10 and Task 12 step 2. Part 5's four smalls → Task 8, Task 9, Task 4 (`reverify`'s `thread_env`), Task 12 step 3 (the rebase wording). Part 5's three test gaps → Task 11. Part 6 → Task 12. Part 7's three named tests → Tasks 5, 7, and Task 2.

**Where `make check` is green at each commit.** Task 2 repoints the three `test_cli.py` stubs *before* changing `cli.py`, so its own step 1 is green. Task 4 fixes all seven `prepare_worktree` call sites and extends `_stub_the_runtime` in the same commit as the required argument. Task 6 extends the stub again for `dirty_paths`. No task is left red.

**Type consistency.** `export_gates` returns `dest` (the directory holding `.saffron/gates/`) in Task 3, mounted as `gates_dir` in Task 4, so `gate_executables(Path("/gates"))` gives `/gates/.saffron/gates/<name>` — `policy.py` untouched. `dirty_paths -> list[str]` feeds `committed_gate(dirty: list[str])`. `fetch_default_branch -> (branch, head)` is unpacked as `_, base_sha`. `record_push(task_id, pushed_sha)` writes the column `queue_lines()` already reads.

**Soft spots that remain, flagged rather than papered over.** Task 9's `package()` fixture shape and Task 11's exact column counts are to be read off the test files at execution time, not guessed. Task 5's cell test needs helpers that do not exist yet and must be written against `_seed_repo` and the `network` fixture. Task 7 tests a claim rather than new code — if it fails, that is a finding about `repair_decision`.
