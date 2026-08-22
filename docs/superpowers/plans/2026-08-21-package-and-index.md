# PACKAGE + index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a green cell run into a squashed commit on the real remote, a draft pull request whose body carries the critic's findings, and a line in the morning queue.

**Architecture:** A new host-side `saffron/phases/package.py` runs after `run_one_cell` returns and the cell is torn down. It applies the exported `patch.diff` onto today's default branch inside a scratch worktree cut from the local mirror, re-verifies in a gate-only cell when the base moved, refuses to push a patch carrying a credential, pushes with a read lease, and opens a draft PR via `gh`. `run_one_cell` stops returning a bare string and returns a `CellOutcome` — the seam sub-project C's `supervisor.py` will inherit.

**Tech Stack:** Python 3.12, pydantic v2, pytest, `git` (2.50.1 measured), `gh` (2.96.0), `apple/container` via `saffron.cell.runtime`. **No new dependencies** — see Global Constraints.

**Spec:** `docs/superpowers/specs/2026-08-21-package-design.md`

## Global Constraints

- **No new dependencies.** `uv.lock` is in `.saffron/policy.yaml`'s `protected` list, so adding one is structurally blocked. This overrides the spec's part 4 line "the f-strings go" — `report/pr_body.py` **stays f-strings**, no Jinja. Update its `ponytail:` comment to say the dependency, not the conditionals, is what settled it.
- **`error` is not `fail`.** A gate or tool that broke aborts and is charged to nobody; only the repo's code being wrong is `fail` (§5.4).
- **Bare `§` cites `DESIGN.md`.** The spec's own sections are "part N".
- **Never `git push` unprompted** — this plan pushes only to `tmp_path` bare repos in tests. The first push to a real remote is the operator's call.
- **`DESIGN.md` section numbers are an API.** Add subsections; never renumber.
- **Vocabulary is enforced** (`CONTEXT.md`): "cell" not "sandbox", "gate result" not "gate run", a `Finding` carries a **`claim`**, not a message.
- **Commit subjects:** lowercase `type(scope): what changed`, written about the defect rather than the file.
- Run `make check` before every commit. One test file per task, added to `tests/`.

---

### Task 1: `DESIGN.md` — the design decisions, before any code

The spec's part 9. Written first because §5.7 currently describes something this plan does not build, and code landing against a stale design is how the two drift.

**Files:**
- Modify: `DESIGN.md` §5.7 (line ~727), §4.1 (line ~274)

**Interfaces:**
- Consumes: nothing.
- Produces: the design text every later task cites. No code symbols.

- [ ] **Step 1: Add the v1 packaging decisions to §5.7**

After §5.7's numbered list, add a subsection (do not renumber the list):

```markdown
#### v1: one squashed commit, a draft PR, and re-verification only when the base moved

v1 packages **one squashed commit**, not the agent's own. The cell's commits
live on the worktree volume and die with it, so `patch.diff` — a squashed
`git diff` — is the only thing that survives teardown (§5.1). The consequence
is a provenance seam and the body states both halves: **the pushed sha is not
the cell's head sha**, and the cell's head names an object no longer reachable
anywhere. The agent's own commit subjects are captured before teardown and
carried in the commit body, which is the record they would otherwise only have
in a transcript.

The PR opens as a **draft**. Real enough to exercise the path nightly, without
pinging reviewers while v1 settles.

**Re-verification runs when, and only when, the base moved.** If the default
branch head still equals `base_sha`, the merged tree is byte-identical to the
one the suite already ran on and re-running it is provably redundant; the body
says it was skipped and why. Otherwise the suite re-runs — **inside a cell,
never host-side**, because the applied tree carries `.saffron/gates/*` exactly
as the patch left them, and exec'ing those on the host is the control plane
executing model-authored code (§2). The base having moved also invalidates the
baseline, so the gate-only cell runs the suite twice — at the new default-branch
head for a fresh baseline, and at the packaged commit — and subtracts as always.
New failures are `MERGE_FAILED`: the change did not survive contact with today's
main.

**Two measured `git apply --3way` hazards** (git 2.50.1), both of which break
the obvious implementation:

- A **conflicting** apply exits 1 **and still writes the file**, with `<<<<<<<`
  markers and a staged `U` entry. "The apply failed" and "nothing happened" are
  not the same state.
- A **degraded** apply exits **0**. With the preimage blob absent and the hunk's
  context matching, git prints `error: repository lacks the necessary blob to
  perform 3-way merge. / Falling back to direct application...` to stderr and
  succeeds. Conflict detection silently becomes a context match.

So the exit code alone decides nothing: a non-zero exit is `MERGE_FAILED`, and a
zero exit whose stderr names the missing blob is an `error`.

**PACKAGE refuses to push a patch carrying the cell's credential.** It is the
first component that moves cell-authored bytes off the host, and the cell holds
`CLAUDE_CODE_OAUTH_TOKEN` (§5.1). A token pushed to a real remote is effectively
undeletable. This is a refusal, not the `secrets` gate — that gate is still v1's
to build, and until it exists **the residual risk is every credential shape the
refusal does not know**, stated here rather than left to be discovered.

Model-authored text is neutralized before it enters a commit body or a PR body:
GitHub acts on `Fixes #12` and `@name` in both, so a cell can close an issue or
notify a person without executing anything.

Two deviations from the list above, each waiting on a named sub-project: the
acceptance-criteria checklist ships **unchecked**, because no lens produces a
per-criterion assessment; and there is no root-cause section, because DIAGNOSE
does not exist.
```

- [ ] **Step 2: Correct §4.1's account of `repos`**

In §4.1, where the `repos` table is described, add:

```markdown
`repos.origin` is the **real remote** — the URL a PR is opened against.
`repos.mirror_path` is the local bare mirror, which is the only remote a cell
ever reads (§5.1). v0 and v0.5 stored the mirror's *source* in both, so nothing
downstream knew where the real remote was; PACKAGE is the first component that
needs the distinction and the first that enforces it.
```

- [ ] **Step 3: Verify nothing was renumbered**

Run: `grep -n "^#\{1,3\} " DESIGN.md | head -60`
Expected: the same section numbers as before, with new `####` subsections only.

- [ ] **Step 4: Commit**

```bash
git add DESIGN.md
git commit -m "docs(design): what v1 packages, and the two apply hazards it must not trust"
```

---

### Task 2: `CellOutcome` — widen the return without changing behaviour

`run_one_cell` returns a bare string, so everything the PR body needs is computed and discarded. This task changes only the type; every state it returns today it returns tomorrow.

**Files:**
- Modify: `saffron/cell/session.py` (12 return points: lines 488, 531, 539, 573, 601, 736, 748, and the `repair_loop` returns at 239, 244, 251, 256 stay `str`)
- Modify: `saffron/cli.py:124` (`_run_cell`)
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  ```python
  @dataclass
  class CellOutcome:
      state: str
      task_id: int
      run_id: int
      task_dir: Path
      spent_usd: float = 0.0
      attempts: int = 0
      cell_head_sha: str | None = None
      gates: list[GateResult] = field(default_factory=list)
      new_failures: list[NewFailure] = field(default_factory=list)
      reviews: list[review.LensReview] = field(default_factory=list)
      rebut_result: rebut.RebutResult | None = None
      agent_subjects: list[str] = field(default_factory=list)
  ```
  `run_one_cell(...) -> CellOutcome`.

- [ ] **Step 1: Write the failing test**

In `tests/test_session.py`:

```python
def test_an_early_return_still_produces_a_complete_outcome(tmp_path, monkeypatch):
    """PREFLIGHT_FAILED returns before `spent` and `reviews` are bound.

    Defaults on CellOutcome are not tidiness: constructing one at that return
    without them raises UnboundLocalError on the failure path that matters most.
    """
    from saffron.cell.session import CellOutcome

    outcome = CellOutcome(
        state="PREFLIGHT_FAILED", task_id=1, run_id=1, task_dir=tmp_path
    )
    assert outcome.spent_usd == 0.0
    assert outcome.attempts == 0
    assert outcome.reviews == []
    assert outcome.rebut_result is None
    assert outcome.agent_subjects == []
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/test_session.py::test_an_early_return_still_produces_a_complete_outcome -v`
Expected: FAIL — `ImportError: cannot import name 'CellOutcome'`

- [ ] **Step 3: Add the dataclass**

In `saffron/cell/session.py`, beside `CellSpec`:

```python
@dataclass
class CellOutcome:
    """What one cell produced. Every field defaulted, because `session.py`'s
    early returns precede the bindings: `spent` is first bound by
    `plan_checkpoint` while PREFLIGHT_FAILED and PLAN_REJECTED return before it,
    and `reviews` is unbound on every path that skipped REVIEW.

    ponytail: this is the seam v1's supervisor.py inherits — a supervisor that
    returns a bare string cannot be given a caller.
    """

    state: str
    task_id: int
    run_id: int
    task_dir: Path
    spent_usd: float = 0.0
    attempts: int = 0
    cell_head_sha: str | None = None
    gates: list[GateResult] = field(default_factory=list)
    new_failures: list[NewFailure] = field(default_factory=list)
    reviews: list[review.LensReview] = field(default_factory=list)
    rebut_result: rebut.RebutResult | None = None
    agent_subjects: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run it to make sure it passes**

Run: `uv run pytest tests/test_session.py::test_an_early_return_still_produces_a_complete_outcome -v`
Expected: PASS

- [ ] **Step 5: Convert every `run_one_cell` return**

Change the signature at `session.py:342` to `-> CellOutcome`. Then at each of lines 488, 531, 539, 573, 601, 736, 748, replace `return "STATE"` with `return CellOutcome(state="STATE", task_id=task_id, run_id=run_id, task_dir=task_dir, ...)`, passing whatever is bound at that point and nothing that is not. At line 736 (the success path) pass all of `spent_usd=spent`, `gates=green`, `reviews=reviews`, `rebut_result=result if outcome != "READY_FOR_REVIEW" else None`.

`repair_loop`'s four returns stay `str` — it reports a decision, not an outcome.

- [ ] **Step 6: Thread `attempts` and `new_failures` out of `repair_loop`**

`repair_loop` (line 219) currently returns `str`. Change it to return `tuple[str, int, list[NewFailure]]` — the decision, the attempt count reached, and the last new-failure list — and unpack at its one call site (line ~640). These are loop locals today; the spec's part 1 is explicit that they are not free plumbing.

- [ ] **Step 7: Update the caller**

In `saffron/cli.py`, `_run_cell` (line ~124):

```python
    outcome = run_one_cell(
        cell_spec, repo=repo, mirror=mirror, ledger=ledger, out_dir=out_dir
    )
    print(f"{spec.id:<10} {outcome.state}")
    return CELL_EXIT.get(outcome.state, 1)
```

- [ ] **Step 8: Run the whole suite**

Run: `make check`
Expected: PASS. Any test asserting `run_one_cell(...) == "STATE"` becomes `.state == "STATE"`.

- [ ] **Step 9: Commit**

```bash
git add saffron/cell/session.py saffron/cli.py tests/test_session.py
git commit -m "refactor(session): a supervisor that returns a string cannot be given a caller"
```

---

### Task 3: The real remote — resolution, slug, default branch

`session.py:363` stores the local filesystem path in `repos.origin`. Nothing downstream knows where the real remote is.

**Files:**
- Create: `saffron/phases/package.py`
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: `CellOutcome` (Task 2).
- Produces:
  ```python
  class PackageError(RuntimeError): ...        # infrastructure: exit 2
  def real_remote(repo: Path) -> str
  def github_slug(url: str) -> str
  def default_branch(url: str, *, cwd: Path) -> str
  def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]
  ```

- [ ] **Step 1: Write the failing tests**

Create `tests/test_package.py`:

```python
import subprocess

import pytest

from saffron.phases.package import (
    PackageError,
    default_branch,
    github_slug,
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
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `uv run pytest tests/test_package.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'saffron.phases.package'`

- [ ] **Step 3: Write the implementation**

Create `saffron/phases/package.py`:

```python
"""PACKAGE — a green cell becomes a branch, a draft PR and a queue line (§5.7).

Host-side, no model, and no cell except the gate-only one part 3 of the spec
describes. It runs after the cell is torn down: the host should not be talking
to the real remote while an untrusted container is alive.

No named remote is ever added to the mirror, and no long-lived ref is created.
`mirror.ensure_mirror` fetches `+refs/*:refs/*` with `--prune`, so any ref left
behind that the local repo does not have is deleted on the next run — including
a branch this module just created.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_SLUG = re.compile(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$")


class PackageError(RuntimeError):
    """Infrastructure. Raised, caught by `cli.main`, exits 2 (§3.3)."""


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Every git call here inspects `returncode` *and* `stderr` — see
    `apply_patch`, where a zero exit does not mean what it looks like."""
    try:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise PackageError(f"git {' '.join(args)}: {exc}") from exc


def real_remote(repo: Path) -> str:
    """The URL a pull request is opened against — never the mirror's source."""
    done = _run(repo, "remote", "get-url", "origin")
    if done.returncode != 0 or not done.stdout.strip():
        raise PackageError(
            f"{repo} has no 'origin' remote, so there is nowhere to open a "
            "pull request"
        )
    return done.stdout.strip()


def github_slug(url: str) -> str:
    """`owner/repo`, from either URL shape git writes."""
    if not (found := _SLUG.search(url)):
        raise PackageError(f"cannot read owner/repo out of {url!r}")
    return f"{found.group(1)}/{found.group(2)}"


def default_branch(url: str, *, cwd: Path) -> str:
    """What the remote says HEAD points at. Not hardcoded `main`."""
    done = _run(cwd, "ls-remote", "--symref", url, "HEAD")
    if done.returncode != 0:
        raise PackageError(f"cannot reach {url}: {done.stderr.strip()[:200]}")
    for line in done.stdout.splitlines():
        if line.startswith("ref: "):
            return line.removeprefix("ref: ").split("\t")[0].removeprefix(
                "refs/heads/"
            )
    raise PackageError(f"{url} reported no symbolic HEAD")
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS (4 tests, one parametrized ×4)

- [ ] **Step 5: Store the real remote in the ledger**

In `saffron/cell/session.py:363`, replace:

```python
    repo_id = ledger.upsert_repo(repo.name, str(repo), str(mirror), policy_sha)
```

with:

```python
    # §4.1: `origin` is the real remote, `mirror_path` the local mirror. v0
    # stored the mirror's source in both, so nothing downstream knew where a
    # pull request would go. A repo with no origin is still runnable — it just
    # cannot be packaged, and PACKAGE is what says so.
    from saffron.phases import package

    try:
        origin_url = package.real_remote(repo)
    except package.PackageError:
        origin_url = str(repo)
    repo_id = ledger.upsert_repo(repo.name, origin_url, str(mirror), policy_sha)
```

- [ ] **Step 6: Run the suite**

Run: `make check`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py saffron/cell/session.py
git commit -m "feat(package): where a pull request actually goes, which the ledger did not know"
```

---

### Task 4: Applying the patch — neither hazard trusted

The heart of it. Both measured hazards live here.

**Files:**
- Modify: `saffron/phases/package.py`
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: `_run`, `PackageError` (Task 3).
- Produces:
  ```python
  APPLY_OK = "ok"; APPLY_CONFLICT = "conflict"
  def assert_base_objects(mirror: Path, base_sha: str) -> None
  def apply_patch(worktree: Path, patch: Path) -> str   # APPLY_OK | APPLY_CONFLICT; raises PackageError on `error`
  ```

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_package.py`:

```python
from saffron.phases.package import APPLY_CONFLICT, APPLY_OK, apply_patch

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
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `uv run pytest tests/test_package.py -k apply -v`
Expected: FAIL — `ImportError: cannot import name 'APPLY_OK'`

- [ ] **Step 3: Write the implementation**

Append to `saffron/phases/package.py`:

```python
APPLY_OK = "ok"
APPLY_CONFLICT = "conflict"

# Measured on git 2.50.1 (Apple Git-155). Both of these appear on stderr while
# git exits 0, which is why neither the exit code nor the output alone decides.
_NO_BLOB = "lacks the necessary blob"
_NO_FULL_INDEX = "without full index line"


def assert_base_objects(mirror: Path, base_sha: str) -> None:
    """Refuse to apply against a mirror missing the patch's preimage.

    Without this, `--3way` degrades to a context match and reports success —
    see `apply_patch`. Checked up front so the failure names its cause.
    """
    done = _run(mirror, "cat-file", "-e", f"{base_sha}^{{tree}}")
    if done.returncode != 0:
        raise PackageError(
            f"mirror {mirror} lacks the objects for base {base_sha[:12]}, so a "
            "three-way merge cannot be performed"
        )


def apply_patch(worktree: Path, patch: Path) -> str:
    """Apply the cell's squashed patch. §5.7's rebase, one commit long.

    Two measured hazards, and the exit code alone catches neither:

    - A **conflicting** apply exits 1 *and writes the file*, with `<<<<<<<`
      markers and a staged `U` entry. Non-zero is APPLY_CONFLICT and the
      worktree must be discarded unread — never committed.
    - A **degraded** apply exits **0**: with the preimage blob absent and the
      hunk's context matching, git falls back to direct application and
      succeeds. That is `error`, not `pass` — the toolchain, charged to nobody.
    """
    if not patch.is_file():
        raise PackageError(f"no patch at {patch}: there is nothing to package")
    done = _run(worktree, "apply", "--3way", "--index", str(patch))
    stderr = done.stderr
    if _NO_FULL_INDEX in stderr:
        raise PackageError(
            "the patch carries a binary change with no full index line, so it "
            "was never appliable — not a conflict"
        )
    if _NO_BLOB in stderr:
        raise PackageError(
            "git fell back to direct application: the preimage blob is absent, "
            "so no three-way merge happened and a clean exit would mean only "
            "that the context matched"
        )
    return APPLY_OK if done.returncode == 0 else APPLY_CONFLICT
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS (all four apply tests plus Task 3's)

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py
git commit -m "feat(package): a zero exit from git apply is not a merge"
```

---

### Task 5: What must not leave the host

**Files:**
- Modify: `saffron/phases/package.py`
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: `PackageError` (Task 3).
- Produces:
  ```python
  def find_credentials(patch_text: str, *, token: str | None) -> list[str]
  def neutralize(text: str) -> str
  ```
  `find_credentials` returns human-readable descriptions, **never the value**.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_package.py`:

```python
from saffron.phases.package import find_credentials, neutralize


def test_the_cells_own_token_is_found_and_never_echoed():
    """The cell carries CLAUDE_CODE_OAUTH_TOKEN — the one sanctioned in-cell
    credential. Pushed to a real remote it is effectively undeletable."""
    token = "sk-ant-oat01-EXAMPLE-NOT-REAL-0000"
    patch = f"+++ b/config.py\n+TOKEN = \"{token}\"\n"
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
    ["Fixes #12", "closes #45", "Resolved #7", "ping @someone"],
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
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `uv run pytest tests/test_package.py -k "credential or neutraliz or github_acts" -v`
Expected: FAIL — `ImportError: cannot import name 'find_credentials'`

- [ ] **Step 3: Write the implementation**

Append to `saffron/phases/package.py`:

```python
# ponytail: a refusal, not the `secrets` gate (§5.4) — that is v1's to build.
# The ceiling is named in DESIGN.md §5.7: every credential shape not listed here
# still reaches the remote, and the upgrade path is the gate, not more regexes.
_CREDENTIAL_SHAPES = (
    ("an Anthropic API key", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9_\-]{16,}")),
    ("an Anthropic OAuth token", re.compile(r"sk-ant-oat\d{2}-[A-Za-z0-9_\-]{8,}")),
    ("a GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}")),
    ("an AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

_CLOSES = re.compile(
    r"\b(clos(e|es|ed)|fix(es|ed)?|resolv(e|es|ed))\b(?=\s*:?\s*#\d)",
    re.IGNORECASE,
)
_MENTION = re.compile(r"(?<![\w/])@(?=\w)")


def _added_lines(patch_text: str) -> list[tuple[str, str]]:
    """(path, added line) for every `+` line. A credential removed by the patch
    is already in history and is not this push's doing."""
    path, out = "?", []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            path = line.removeprefix("+++ b/")
        elif line.startswith("+") and not line.startswith("+++"):
            out.append((path, line[1:]))
    return out


def find_credentials(patch_text: str, *, token: str | None) -> list[str]:
    """Describe every credential the patch would push. Never returns the value.

    The literal token is checked first and separately: it is the one secret we
    know is in the cell, so a miss there is not a heuristic failure.
    """
    found = []
    for path, line in _added_lines(patch_text):
        if token and len(token) > 8 and token in line:
            found.append(f"{path}: the cell's own CLAUDE_CODE_OAUTH_TOKEN")
            continue
        for what, pattern in _CREDENTIAL_SHAPES:
            if pattern.search(line):
                found.append(f"{path}: {what}")
                break
    return found


def neutralize(text: str) -> str:
    """Defang model-authored text before it reaches GitHub.

    GitHub closes an issue named by `Fixes #12` in a commit body *and* in a pull
    request body, and `@name` notifies a real account. This is the one place a
    cell's output causes an effect outside the boundary without executing (§2).
    """
    return _MENTION.sub("@​", _CLOSES.sub(lambda m: m.group(0) + "​", text))
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py
git commit -m "feat(package): the one credential the cell holds, and the text github acts on"
```

---

### Task 6: Commit and push with a read lease

**Files:**
- Modify: `saffron/phases/package.py`
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: `_run`, `PackageError`, `neutralize` (Tasks 3, 5).
- Produces:
  ```python
  def commit_squash(worktree: Path, *, spec_id: str, title: str, base_sha: str,
                    cell_head: str | None, attempts: int, spent_usd: float,
                    agent_subjects: list[str]) -> str   # the new sha
  def remote_sha(url: str, branch: str, *, cwd: Path) -> str
  def push_with_lease(worktree: Path, *, url: str, branch: str, expect: str) -> None
  ```

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_package.py`:

```python
from saffron.phases.package import commit_squash, push_with_lease, remote_sha


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
    with pytest.raises(PackageError, match="moved underneath|stale"):
        push_with_lease(
            repo, url=str(bare_remote), branch="saffron/SA-0005", expect=stale
        )
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `uv run pytest tests/test_package.py -k "squash or lease or moved" -v`
Expected: FAIL — `ImportError: cannot import name 'commit_squash'`

- [ ] **Step 3: Write the implementation**

Append to `saffron/phases/package.py`:

```python
def commit_squash(
    worktree: Path,
    *,
    spec_id: str,
    title: str,
    base_sha: str,
    cell_head: str | None,
    attempts: int,
    spent_usd: float,
    agent_subjects: list[str],
) -> str:
    """One commit. Not the repo's `type(scope):` convention — that describes a
    commit a person wrote about a defect they understood, and this one is
    generated; a subject mimicking it would claim a judgement nothing made.

    `cell_head` names an object that no longer exists anywhere: the cell's
    commits died with the volume. It is recorded because it is the only name
    the transcript and the batch tree share.
    """
    lines = [
        f"saffron {spec_id}: {neutralize(title)}",
        "",
        f"base {base_sha[:12]}",
        f"cell head {cell_head[:12] if cell_head else '(unknown)'} "
        "(unreachable: the cell's commits died with its volume)",
        f"{attempts} attempts, ${spent_usd:.2f}",
    ]
    if agent_subjects:
        lines += ["", "The agent's own commits, squashed into this one:"]
        lines += [f"  * {neutralize(s)}" for s in agent_subjects]
    done = _run(worktree, "commit", "-q", "-m", "\n".join(lines))
    if done.returncode != 0:
        raise PackageError(f"commit failed: {done.stderr.strip()[:200]}")
    return _run(worktree, "rev-parse", "HEAD").stdout.strip()


def remote_sha(url: str, branch: str, *, cwd: Path) -> str:
    """What the remote has for this branch right now — "" if it has nothing.

    Read rather than assumed: this is the lease, and a guessed lease protects
    nothing.
    """
    done = _run(cwd, "ls-remote", url, f"refs/heads/{branch}")
    if done.returncode != 0:
        raise PackageError(f"cannot reach {url}: {done.stderr.strip()[:200]}")
    return done.stdout.split("\t")[0].strip() if done.stdout.strip() else ""


def push_with_lease(worktree: Path, *, url: str, branch: str, expect: str) -> None:
    """Push, pinned to what the remote said. An empty `expect` means the branch
    is not there — measured: git treats that as "expect it to be absent" and
    rejects with `stale info` if it appeared."""
    done = _run(
        worktree,
        "push",
        f"--force-with-lease=refs/heads/{branch}:{expect}",
        url,
        f"HEAD:refs/heads/{branch}",
    )
    if done.returncode != 0:
        raise PackageError(
            f"the branch moved underneath us: {done.stderr.strip()[:300]}"
        )
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py
git commit -m "feat(package): a lease read from the remote, not guessed at"
```

---

### Task 7: `gh` behind a seam

**Files:**
- Modify: `saffron/phases/package.py`
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: `PackageError`, `github_slug` (Task 3).
- Produces:
  ```python
  GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]
  def run_gh(argv: list[str]) -> subprocess.CompletedProcess[str]
  def open_draft_pr(*, slug: str, branch: str, base: str, title: str,
                    body_path: Path, gh: GhRunner = run_gh) -> str
  ```

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_package.py`:

```python
import subprocess as sp

from saffron.phases.package import open_draft_pr


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
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `uv run pytest tests/test_package.py -k "draft or second_package or missing_gh" -v`
Expected: FAIL — `ImportError: cannot import name 'open_draft_pr'`

- [ ] **Step 3: Write the implementation**

Append to `saffron/phases/package.py` (add `from collections.abc import Callable` to the imports):

```python
GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def run_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def open_draft_pr(
    *,
    slug: str,
    branch: str,
    base: str,
    title: str,
    body_path: Path,
    gh: GhRunner = run_gh,
) -> str:
    """Open the pull request as a draft, or report the one already there.

    Called *after* the push, deliberately: a missing or unauthenticated `gh`
    then leaves a branch you can open by hand, where the other order loses the
    work to a CLI.
    """
    create = [
        "gh", "pr", "create",
        "--repo", slug,
        "--draft",
        "--base", base,
        "--head", branch,
        # Not optional: without it and without --fill, gh prompts, and a prompt
        # in an unattended batch is a hang.
        "--title", title,
        "--body-file", str(body_path),
    ]
    try:
        done = gh(create)
    except OSError as exc:
        raise PackageError(
            f"gh is unavailable ({exc}); branch {branch} is already pushed, so "
            "the pull request can be opened by hand"
        ) from exc
    if done.returncode == 0:
        return done.stdout.strip().splitlines()[-1]

    view = gh(["gh", "pr", "view", branch, "--repo", slug, "--json", "url",
               "--jq", ".url"])
    if view.returncode == 0 and view.stdout.strip():
        return view.stdout.strip()
    raise PackageError(
        f"gh could not open or find a pull request for {branch} "
        f"(it is already pushed): {done.stderr.strip()[:200]}"
    )
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py
git commit -m "feat(package): a draft pull request, and the one already open"
```

---

### Task 8: The pull-request body

**Files:**
- Modify: `saffron/report/pr_body.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `Finding` (`saffron.agents.findings`), `LensReview` (`saffron.phases.review`), `RebutResult` (`saffron.phases.rebut`), `Policy` (`saffron.repos.policy`).
- Produces: an extended
  ```python
  def render_pr_body(spec, results, new_failures, *, base_sha, head_sha,
                     added, removed, transcript_path,
                     reviews=(), rebut_result=None, attempts=1,
                     spent_usd=0.0, test_paths=(), diff="",
                     verified_on="base") -> str
  ```
  `verified_on` is `"base"` (skipped, base unmoved) or `"packaged"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_report.py`:

```python
from saffron.agents.findings import Finding
from saffron.phases.review import LensReview


def _finding(**kw):
    base = dict(
        lens="correctness", severity="blocker", file="a.py", line=3,
        claim="the tz default is wrong", anchored=True,
    )
    return Finding(**{**base, **kw})


def test_disagreements_sort_above_the_gate_table(spec, gate_results):
    """§6: disagreements first, because that is where your judgment is worth
    the most."""
    body = render_pr_body(
        spec, gate_results, [], base_sha="a" * 40, head_sha="b" * 40,
        added=1, removed=0, transcript_path="/t",
        reviews=[LensReview(lens="correctness", findings=[_finding()])],
    )
    assert body.index("Disagreements") < body.index("### Gates")


def test_the_body_renders_two_columns_never_adjudication(spec, gate_results):
    """rebut.py keeps `verdict` and `rebuttal`; `adjudication` is the
    operator's, and it happens in GitHub against the PR this phase creates.
    test_rebut.py asserts it is absent from the record — rendering it here is
    chronologically impossible."""
    body = render_pr_body(
        spec, gate_results, [], base_sha="a" * 40, head_sha="b" * 40,
        added=1, removed=0, transcript_path="/t",
        reviews=[LensReview(lens="correctness", findings=[_finding()])],
    )
    assert "adjudication" not in body.lower()


def test_an_unanchored_finding_still_appears(spec, gate_results):
    """`anchored = False` is kept, never dropped: drop rate per lens is the
    signal that a lens is badly prompted (§5.5)."""
    body = render_pr_body(
        spec, gate_results, [], base_sha="a" * 40, head_sha="b" * 40,
        added=1, removed=0, transcript_path="/t",
        reviews=[LensReview(lens="schema", findings=[_finding(anchored=False)])],
    )
    assert "the tz default is wrong" in body


def test_the_test_file_diff_is_shown_separately(spec, gate_results):
    """§7's second countermeasure for gate gaming. Filtered by the repo's
    declared `integrity.test_paths` — not one line of language knowledge in
    core (§2.1)."""
    diff = (
        "diff --git a/tests/test_x.py b/tests/test_x.py\n"
        "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n"
        "@@ -1,3 +0,0 @@\n-def test_x():\n-    assert thing()\n"
        "diff --git a/saffron/x.py b/saffron/x.py\n"
        "--- a/saffron/x.py\n+++ b/saffron/x.py\n@@ -1 +1 @@\n-a\n+b\n"
    )
    body = render_pr_body(
        spec, gate_results, [], base_sha="a" * 40, head_sha="b" * 40,
        added=1, removed=2, transcript_path="/t",
        test_paths=["tests/**"], diff=diff,
    )
    assert "Test files changed" in body
    assert body.index("Test files changed") < body.index("### Gates")
    assert "def test_x" in body


def test_the_body_says_which_tree_the_gates_ran_on(spec, gate_results):
    skipped = render_pr_body(
        spec, gate_results, [], base_sha="a" * 40, head_sha="b" * 40,
        added=1, removed=0, transcript_path="/t", verified_on="base",
    )
    assert "base had not moved" in skipped
    rerun = render_pr_body(
        spec, gate_results, [], base_sha="a" * 40, head_sha="b" * 40,
        added=1, removed=0, transcript_path="/t", verified_on="packaged",
    )
    assert "packaged commit" in rerun
```

Add fixtures at the top of the file if `spec` / `gate_results` do not already exist there; reuse the existing ones if they do.

- [ ] **Step 2: Run them to make sure they fail**

Run: `uv run pytest tests/test_report.py -k "disagreement or two_columns or unanchored or test_file_diff or which_tree" -v`
Expected: FAIL — `TypeError: render_pr_body() got an unexpected keyword argument 'reviews'`

- [ ] **Step 3: Extend the renderer**

In `saffron/report/pr_body.py`, replace the `ponytail:` comment with:

```python
ponytail: f-strings, not Jinja. Not "until the conditionals arrive" — they have
arrived and f-strings still handle them. The dependency is what settles it:
`uv.lock` is in `.saffron/policy.yaml`'s `protected` list, so adding jinja2 is
structurally blocked. Revisit only if a template needs inheritance.
```

Add the parameters from the Interfaces block above, and these sections, placing `_disagreements` and `_test_diff` **before** `_gate_table` in the `sections` list:

```python
def _disagreements(reviews, rebut_result) -> str:
    """§6: disagreements first. Two columns — the implementer's rebuttal and
    the critic's verdict. Never `adjudication`: that is the operator's, and it
    happens in GitHub against the pull request this phase is creating."""
    anchored = [
        f for r in reviews for f in r.findings
        if f.anchored and f.severity == "blocker"
    ]
    if not anchored:
        return ""
    rebuttals = {}
    verdicts = {}
    if rebut_result is not None:
        rebuttals = {r.finding: r for r in rebut_result.rebuttal.rebuttals}
        verdicts = {
            v.finding: v for lens in rebut_result.verdicts for v in lens.verdicts
        }
    lines = [
        "### Disagreements",
        "",
        "| # | lens | where | claim | implementer | critic |",
        "|---|---|---|---|---|---|",
    ]
    for number, finding in enumerate(anchored, start=1):
        rebuttal = rebuttals.get(number)
        verdict = verdicts.get(number)
        lines.append(
            f"| {number} | `{_cell(finding.lens)}` "
            f"| {_cell(finding.file)}:{finding.line} "
            f"| {_cell(finding.claim)} "
            f"| {_cell(rebuttal.action + ': ' + rebuttal.argument) if rebuttal else '—'} "
            f"| {_cell(verdict.verdict + ': ' + verdict.reason) if verdict else '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _findings(reviews) -> str:
    rows = [(r.lens, f) for r in reviews for f in r.findings]
    if not rows:
        return ""
    lines = [
        "### Findings",
        "",
        "| lens | severity | where | claim | anchored |",
        "|---|---|---|---|---|",
    ]
    for lens, finding in rows:
        lines.append(
            f"| `{_cell(lens)}` | `{finding.severity}` "
            f"| {_cell(finding.file)}:{finding.line} | {_cell(finding.claim)} "
            f"| {'yes' if finding.anchored else 'no'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _test_diff(diff: str, test_paths) -> str:
    """§7's second countermeasure. `test_paths` is the repo's declaration
    (`policy.integrity.test_paths`); core supplies the question, never the
    answer (§2.1)."""
    import fnmatch

    if not diff or not test_paths:
        return ""
    sections, current, keep = [], [], False
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if keep and current:
                sections.append("".join(current))
            path = line.split(" b/", 1)[-1].strip()
            keep = any(fnmatch.fnmatch(path, p) for p in test_paths)
            current = [line]
        else:
            current.append(line)
    if keep and current:
        sections.append("".join(current))
    if not sections:
        return ""
    return (
        "### Test files changed\n\n"
        "Shown separately because a green gate says nothing about a deleted "
        "test (§7).\n\n```diff\n" + "".join(sections) + "```\n"
    )


def _verification(verified_on: str) -> str:
    if verified_on == "base":
        return (
            "Gates ran at `base_sha`, and were not re-run: the base had not "
            "moved, so the packaged tree is byte-identical to the one they saw."
        )
    return (
        "Gates were re-run on the **packaged commit**, because the base moved "
        "after this task started."
    )
```

- [ ] **Step 4: Run them to make sure they pass**

Run: `uv run pytest tests/test_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add saffron/report/pr_body.py tests/test_report.py
git commit -m "feat(report): the critic's findings, which nothing has ever rendered"
```

---

### Task 9: Re-verification when the base moved

**Files:**
- Modify: `saffron/phases/package.py`
- Test: `tests/test_package.py` (host logic), `tests/test_package_cell.py` (cell-marked)

**Interfaces:**
- Consumes: `runner.run_suite`, `runner.CellExecutor`, `baseline.subtract_baseline`, `worktree.prepare_worktree`, `runtime` (existing modules).
- Produces:
  ```python
  def needs_reverification(fetch_head: str, base_sha: str) -> bool
  def reverify(*, mirror: Path, packaged_sha: str, new_base_sha: str,
               policy: Policy, image: str, watch) -> list[NewFailure]
  ```

- [ ] **Step 1: Write the failing test for the skip rule**

Append to `tests/test_package.py`:

```python
from saffron.phases.package import needs_reverification


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
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/test_package.py -k reverification -v`
Expected: FAIL — `ImportError: cannot import name 'needs_reverification'`

- [ ] **Step 3: Write the implementation**

Append to `saffron/phases/package.py`:

```python
def needs_reverification(fetch_head: str, base_sha: str) -> bool:
    """Re-run only when the base moved (§5.7).

    Equal shas mean the packaged tree is the tree the suite already ran on, so
    a re-run is provably redundant rather than merely expensive.
    """
    return fetch_head != base_sha


def reverify(
    *,
    mirror: Path,
    packaged_sha: str,
    new_base_sha: str,
    policy,
    image: str,
    watch,
) -> list["NewFailure"]:
    """Run the suite on the packaged commit, in a cell.

    **Never host-side.** The applied tree carries `.saffron/gates/*` exactly as
    the patch left them, and exec'ing those on the host is the control plane
    executing model-authored code — the one thing §2 says it never does.

    Twice, because the base moved: the old baseline describes a tree that no
    longer exists, and comparing against it would charge this task with the
    default branch's own drift. So a fresh baseline at `new_base_sha`, the head
    suite at `packaged_sha`, and the usual subtraction (§4.4 steps 2-3).
    """
    from saffron.cell import runtime, worktree
    from saffron.gates import runner
    from saffron.gates.baseline import subtract_baseline

    results = {}
    for label, sha in (("baseline", new_base_sha), ("head", packaged_sha)):
        volume = f"saffron-pkg-{label}-{sha[:12]}"
        container = f"saffron-pkg-{label}-{sha[:12]}"
        network = f"{container}-net"
        created: set[str] = set()
        try:
            # `create_network` hardcodes --internal (runtime.py:146) and
            # returns None, so the name is ours to hold. Passed explicitly to
            # `prepare_worktree` because a cell created without a network joins
            # the runtime's default one with full egress, and every control the
            # caller ran then applies to some other container (Appendix I).
            runtime.create_network(network)
            runtime.create_volume(volume)
            created.add(volume)
            worktree.prepare_worktree(
                mirror=mirror,
                volume=volume,
                base_sha=sha,
                branch=f"pkg-{label}",
                image=image,
                container=container,
                # No agent, no credential, and no route out: this cell only
                # runs gates.
                network=network,
                env={},
                created=created,
            )
            watch(f"re-verify: {label} suite at {sha[:12]}")
            # Gate paths are cell-side (`/work/.saffron/gates/...`); `cwd` is
            # a host path that `CellExecutor` ignores. Same shape as
            # `session.py:361` and `:467` — matched deliberately, so the two
            # suites cannot drift in how they name a gate.
            results[label] = runner.run_suite(
                policy.gate_executables(Path(worktree.WORKTREE_MOUNT)),
                cwd=mirror,
                executor=runner.CellExecutor(container),
            )
        finally:
            runtime.remove_container(container)
            runtime.remove_volume(volume)
            runtime.remove_volume(f"{volume}-state")
            runtime.remove_network(network)

    return subtract_baseline(results["head"], results["baseline"])
```

- [ ] **Step 4: Run it to make sure it passes**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS

- [ ] **Step 5: Write the cell-marked integration test**

Create `tests/test_package_cell.py`:

```python
"""Re-verification against a real cell. Needs the images CLAUDE.md names:

    container build -t saffron/cell-base:python -f images/cell-base.python.Dockerfile .
"""

from pathlib import Path

import pytest

from saffron.phases.package import reverify
from saffron.repos import image as repo_image
from saffron.repos import mirror as mirror_ops
from saffron.repos.policy import load_policy

pytestmark = pytest.mark.cell

SAFFRON_ROOT = Path(__file__).resolve().parent.parent


def test_reverification_runs_the_suite_inside_a_cell(tmp_path):
    """The applied tree carries the repo's own `.saffron/gates/*`; running them
    on the host would be the control plane executing model-authored code (§2).

    Asserts they ran *and* that every result carries a `tool` — a gate that
    never ran reads identically otherwise (§5.4, Appendix H). This is the
    "run the tool, don't merely locate it" rule as a test.
    """
    mirror = mirror_ops.ensure_mirror(SAFFRON_ROOT, tmp_path / "m.git")
    head = mirror_ops._git(mirror, "rev-parse", "HEAD")
    policy, _ = load_policy(SAFFRON_ROOT)
    tag = repo_image.build_cell_image(SAFFRON_ROOT)

    seen = []
    # Same sha for both suites: the subtraction must then be empty, which is
    # the invariant worth pinning — a non-empty result here would mean the
    # gates are not deterministic, not that the packaged commit is bad.
    new_failures = reverify(
        mirror=mirror,
        packaged_sha=head,
        new_base_sha=head,
        policy=policy,
        image=tag,
        watch=seen.append,
    )
    assert new_failures == []
    assert any("baseline suite" in line for line in seen)
    assert any("head suite" in line for line in seen)


def test_the_reverification_cell_carries_no_credential(tmp_path, monkeypatch):
    """It runs gates and nothing else: no agent, no credential, no egress.

    Probed at the call rather than by reading source: a cell started without an
    explicit network joins the runtime's default one with full egress, and
    every control the caller ran then applies to some other container
    (Appendix I). `runtime.create_network` hardcodes --internal, so what is
    worth pinning here is that a network is passed at all and that `env` is
    empty — CLAUDE_CODE_OAUTH_TOKEN must not reach a cell that only runs gates.
    """
    seen = {}

    def spy(**kwargs):
        seen.update(kwargs)
        raise RuntimeError("stop after the arguments are captured")

    monkeypatch.setattr("saffron.cell.worktree.prepare_worktree", spy)
    mirror = mirror_ops.ensure_mirror(SAFFRON_ROOT, tmp_path / "m.git")
    policy, _ = load_policy(SAFFRON_ROOT)
    with pytest.raises(RuntimeError):
        reverify(
            mirror=mirror, packaged_sha="a" * 40, new_base_sha="a" * 40,
            policy=policy, image="unused", watch=lambda _: None,
        )
    assert seen["env"] == {}
    assert seen["network"]
```

- [ ] **Step 6: Commit**

```bash
git add saffron/phases/package.py tests/test_package.py tests/test_package_cell.py
git commit -m "feat(package): a gate table that says which tree it ran on"
```

---

### Task 10: The index, and the link that is not artifacts

**Files:**
- Modify: `saffron/report/index.py:113` (`_row`)
- Create: the append helper in `saffron/report/index.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `QueueLine` (existing).
- Produces:
  ```python
  def append_queue_line(out_dir: Path, line: QueueLine, *, header: dict[str, str]) -> Path
  ```
  Writes `out_dir/queue.json` and re-renders `out_dir/index.html`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_report.py`:

```python
import json

from saffron.report.index import QueueLine, append_queue_line


def test_a_second_task_joins_the_first_without_an_orchestrator(tmp_path):
    """Appending rather than rewriting is what lets sub-project C arrive later."""
    first = QueueLine(
        repo="saffron", spec_id="SA-0005", state="READY_FOR_REVIEW", attempts=1,
        cost_usd_est=6.4, concerns=0, added=10, removed=2,
        link="https://github.com/o/r/pull/7",
    )
    second = QueueLine(
        repo="saffron", spec_id="SA-0006", state="MERGE_FAILED", attempts=2,
        cost_usd_est=3.1, concerns=1, added=4, removed=0, link="",
        note="conflicts with #7",
    )
    append_queue_line(tmp_path, first, header={"spend": "$6.40"})
    append_queue_line(tmp_path, second, header={"spend": "$9.50"})

    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [row["spec_id"] for row in stored] == ["SA-0005", "SA-0006"]
    html = (tmp_path / "index.html").read_text()
    # MERGE_FAILED ranks above an ordinary green task (§6's sort order)
    assert html.index("SA-0006") < html.index("SA-0005")


def test_a_pull_request_link_is_not_labelled_artifacts(tmp_path):
    """index.py:113 captioned every link `artifacts`; §6's own mock shows
    `→ PR #211`. Repointing `link` at a PR without relabelling mislabels it."""
    line = QueueLine(
        repo="saffron", spec_id="SA-0005", state="READY_FOR_REVIEW", attempts=1,
        cost_usd_est=6.4, concerns=0, added=10, removed=2,
        link="https://github.com/o/r/pull/7",
    )
    append_queue_line(tmp_path, line, header={})
    html = (tmp_path / "index.html").read_text()
    assert "PR #7" in html
    assert ">artifacts<" not in html
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/test_report.py -k "second_task or labelled_artifacts" -v`
Expected: FAIL — `ImportError: cannot import name 'append_queue_line'`

- [ ] **Step 3: Fix the link label and add the append helper**

In `saffron/report/index.py`, in `_row`, replace the link cell:

```python
        _link(line.link),
```

and add:

```python
def _link(url: str) -> str:
    """A pull request is not an artifact directory. §6's own mock reads
    `→ PR #211`, and a link captioned `artifacts` sends you to the wrong
    mental model of the page."""
    if not url:
        return ""
    label = f"PR #{url.rstrip('/').rsplit('/', 1)[-1]}" if "/pull/" in url else "artifacts"
    return f'<a href="{html.escape(url)}">{html.escape(label)}</a>'


def append_queue_line(
    out_dir: Path, line: QueueLine, *, header: dict[str, str]
) -> Path:
    """§5.7 step 4. Append, then re-render from the whole list.

    Appending rather than rewriting is what lets a second task join a first
    without the batch orchestrator that does not exist yet (sub-project C).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    store = out_dir / "queue.json"
    rows = json.loads(store.read_text()) if store.is_file() else []
    rows.append(asdict(line))
    store.write_text(json.dumps(rows, indent=2))
    index = out_dir / "index.html"
    index.write_text(
        render_index([QueueLine(**row) for row in rows], header=header)
    )
    return index
```

Add `import json`, `from dataclasses import asdict`, `from pathlib import Path` to the module imports.

- [ ] **Step 4: Run it to make sure it passes**

Run: `uv run pytest tests/test_report.py -v`
Expected: PASS. `replay.py`'s `_write_index` still works — it calls `render_index` directly and is untouched.

- [ ] **Step 5: Commit**

```bash
git add saffron/report/index.py tests/test_report.py
git commit -m "feat(report): a queue a second task can join, and a link that names a pull request"
```

---

### Task 11: `package()` — the whole path, wired into the CLI

**Files:**
- Modify: `saffron/phases/package.py`
- Modify: `saffron/cli.py`
- Modify: `saffron/ledger.py` (add `set_task_package`)
- Test: `tests/test_package.py`, `tests/test_cli.py`, `tests/test_ledger.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  ```python
  @dataclass
  class PackageResult:
      state: str
      pr_url: str = ""
      pushed_sha: str = ""
      branch: str = ""
      note: str = ""

  def package(outcome: CellOutcome, *, spec: Spec, repo: Path, mirror: Path,
              policy: Policy, image: str, ledger: Ledger, out_dir: Path,
              token: str | None, gh: GhRunner = run_gh, watch=print) -> PackageResult
  ```
  `Ledger.set_task_package(task_id, state, branch, pushed_sha, pr_url) -> None`.

- [ ] **Step 1: Write the failing test for persistence**

Append to `tests/test_ledger.py`:

```python
def test_package_writes_back_a_state_the_run_had_already_closed(tmp_path):
    """run_one_cell has already set READY_FOR_REVIEW and finished the run
    COMPLETE before PACKAGE runs (session.py:734-735). Left alone, a
    MERGE_FAILED task reads READY_FOR_REVIEW forever and the failure exists
    nowhere but stdout."""
    ledger = Ledger(tmp_path / "l.db")
    repo_id = ledger.upsert_repo("r", "git@github.com:o/r.git", "/m", "sha")
    run_id = ledger.create_run(repo_id, "a" * 40)
    task_id = ledger.create_task(run_id, "SA-0005", "s" * 40, branch="saffron/SA-0005")
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    ledger.finish_run(run_id, "COMPLETE")

    ledger.set_task_package(
        task_id, "MERGE_FAILED", "saffron/SA-0005", "c" * 40,
        "https://github.com/o/r/pull/7",
    )
    row = next(r for r in ledger.queue_lines() if r["task_id"] == task_id)
    assert row["state"] == "MERGE_FAILED"
    assert row["pushed_sha"] == "c" * 40
    assert row["pr_url"] == "https://github.com/o/r/pull/7"
    ledger.close()
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/test_ledger.py -k package_writes_back -v`
Expected: FAIL — `AttributeError: 'Ledger' object has no attribute 'set_task_package'`

- [ ] **Step 3: Extend the ledger**

In `saffron/ledger.py`, add to the `tasks` DDL in `SCHEMA`:

```sql
    pushed_sha TEXT,
    pr_url     TEXT,
```

Because `CREATE TABLE IF NOT EXISTS` will not alter an existing database, add after `executescript(SCHEMA)` in `__init__`:

```python
        # An existing ledger predates these columns, and `IF NOT EXISTS` does
        # not alter. Additive only — never a migration that can lose a row.
        existing = {
            row["name"]
            for row in self._db.execute("PRAGMA table_info(tasks)").fetchall()
        }
        for column in ("pushed_sha", "pr_url"):
            if column not in existing:
                self._db.execute(f"ALTER TABLE tasks ADD COLUMN {column} TEXT")
        self._db.commit()
```

Add the method:

```python
    def set_task_package(
        self,
        task_id: int,
        state: str,
        branch: str,
        pushed_sha: str,
        pr_url: str,
    ) -> None:
        """PACKAGE's own write-back. It runs after `finish_run`, so the state it
        sets is the last word on the task (§5.7)."""
        self._db.execute(
            """UPDATE tasks
                  SET state = ?, branch = ?, pushed_sha = ?, pr_url = ?,
                      updated_at = datetime('now')
                WHERE task_id = ?""",
            (state, branch, pushed_sha, pr_url, task_id),
        )
        self._db.commit()
```

Add `t.pushed_sha, t.pr_url` to `queue_lines`'s SELECT list.

- [ ] **Step 4: Run it to make sure it passes**

Run: `uv run pytest tests/test_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Write `package()`**

Append to `saffron/phases/package.py`:

```python
@dataclass
class PackageResult:
    state: str
    pr_url: str = ""
    pushed_sha: str = ""
    branch: str = ""
    note: str = ""


def package(
    outcome,
    *,
    spec,
    repo: Path,
    mirror: Path,
    policy,
    image: str,
    ledger,
    out_dir: Path,
    token: str | None,
    gh: GhRunner = run_gh,
    watch=print,
) -> PackageResult:
    """§5.7, host-side, after the cell is gone."""
    from saffron.report import index as index_report
    from saffron.report import pr_body
    from saffron.repos import mirror as mirror_ops

    branch = f"saffron/{spec.id}"
    patch = outcome.task_dir / "patch.diff"
    base_sha = json.loads((outcome.task_dir / "patch.json").read_text())["base_sha"]
    url = real_remote(repo)
    slug = github_slug(url)
    default = default_branch(url, cwd=mirror)

    assert_base_objects(mirror, base_sha)
    fetched = _run(mirror, "fetch", url, f"refs/heads/{default}")
    if fetched.returncode != 0:
        raise PackageError(f"cannot fetch {default} from {url}: {fetched.stderr[:200]}")
    fetch_head = _run(mirror, "rev-parse", "FETCH_HEAD").stdout.strip()

    scratch = out_dir / "package" / spec.id
    worktree_path = mirror_ops.add_worktree(mirror, fetch_head, scratch)
    try:
        # -B, not -b: -b fails when the ref exists, which is the second-package
        # path exactly.
        _run(worktree_path, "checkout", "-B", branch)

        if apply_patch(worktree_path, patch) == APPLY_CONFLICT:
            watch(f"PACKAGE: {branch} conflicts with {default}")
            return _finish(
                ledger, outcome, index_report, out_dir, spec, repo.name,
                PackageResult(state="MERGE_FAILED", branch=branch,
                              note=f"conflicts with {default}"),
            )

        if leaked := find_credentials(patch.read_text(), token=token):
            watch(f"PACKAGE: refusing to push — {'; '.join(leaked)}")
            return _finish(
                ledger, outcome, index_report, out_dir, spec, repo.name,
                PackageResult(state="MERGE_FAILED", branch=branch,
                              note=f"credential in the patch: {'; '.join(leaked)}"),
            )

        pushed = commit_squash(
            worktree_path,
            spec_id=spec.id,
            title=spec.title,
            base_sha=base_sha,
            cell_head=outcome.cell_head_sha,
            attempts=outcome.attempts,
            spent_usd=outcome.spent_usd,
            agent_subjects=outcome.agent_subjects,
        )

        verified_on = "base"
        if needs_reverification(fetch_head, base_sha):
            new = reverify(
                mirror=mirror, packaged_sha=pushed, new_base_sha=fetch_head,
                policy=policy, image=image, watch=watch,
            )
            verified_on = "packaged"
            if new:
                watch(f"PACKAGE: {len(new)} new failures against {default}")
                return _finish(
                    ledger, outcome, index_report, out_dir, spec, repo.name,
                    PackageResult(state="MERGE_FAILED", branch=branch,
                                  pushed_sha=pushed,
                                  note=f"{len(new)} new failures after rebase"),
                )

        diff = _run(worktree_path, "diff", f"{fetch_head}..HEAD").stdout
        body_path = outcome.task_dir / "pr_body.md"
        body_path.write_text(
            pr_body.render_pr_body(
                spec, outcome.gates, outcome.new_failures,
                base_sha=base_sha, head_sha=pushed,
                added=0, removed=0,
                transcript_path=str(outcome.task_dir),
                reviews=outcome.reviews, rebut_result=outcome.rebut_result,
                attempts=outcome.attempts, spent_usd=outcome.spent_usd,
                test_paths=policy.integrity.test_paths, diff=diff,
                verified_on=verified_on,
            )
        )

        push_with_lease(
            worktree_path, url=url, branch=branch,
            expect=remote_sha(url, branch, cwd=mirror),
        )
        pr_url = open_draft_pr(
            slug=slug, branch=branch, base=default,
            title=f"{spec.id} — {neutralize(spec.title)}",
            body_path=body_path, gh=gh,
        )
        watch(f"PACKAGE: {pr_url}")
        return _finish(
            ledger, outcome, index_report, out_dir, spec, repo.name,
            PackageResult(state="READY_FOR_REVIEW", pr_url=pr_url,
                          pushed_sha=pushed, branch=branch),
        )
    finally:
        # The worktree otherwise leaks on every raise path, including the
        # missing-`gh` case this module deliberately creates.
        mirror_ops.remove_worktree(mirror, scratch)


def _finish(ledger, outcome, index_report, out_dir, spec, repo_name, result):
    """Persist and append. A PACKAGE that *raises* reaches neither, and that is
    deliberate: an index line whose link points at a pull request that was
    never opened is worse than no line."""
    ledger.set_task_package(
        outcome.task_id, result.state, result.branch, result.pushed_sha,
        result.pr_url,
    )
    index_report.append_queue_line(
        out_dir,
        index_report.QueueLine(
            repo=repo_name, spec_id=spec.id, state=result.state,
            attempts=outcome.attempts, cost_usd_est=outcome.spent_usd,
            concerns=sum(
                f.anchored and f.severity == "concern"
                for r in outcome.reviews for f in r.findings
            ),
            added=0, removed=0, link=result.pr_url, note=result.note,
            risk=spec.risk,
        ),
        header={"spend": f"${outcome.spent_usd:.2f}"},
    )
    return result
```

Add `import json` and `from dataclasses import dataclass` to the module imports.

- [ ] **Step 6: Wire it into the CLI**

In `saffron/cli.py`, add `MERGE_FAILED` to `CELL_EXIT` with value `1` (it is already the default for unknown states, but naming it documents the intent), and in `_run_cell` after `run_one_cell` returns:

```python
    if outcome.state == "READY_FOR_REVIEW":
        from saffron.phases import package as package_phase
        from saffron.repos import policy as repo_policy

        policy, _ = repo_policy.load_policy(repo)
        result = package_phase.package(
            outcome,
            spec=spec,
            repo=repo,
            mirror=mirror,
            policy=policy,
            image=image,
            ledger=ledger,
            out_dir=out_dir,
            token=os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
        )
        print(f"{spec.id:<10} {result.state}  {result.pr_url or result.note}")
        return CELL_EXIT.get(result.state, 1)

    print(f"{spec.id:<10} {outcome.state}")
    return CELL_EXIT.get(outcome.state, 1)
```

Add `import os` and `from saffron.repos import image as repo_image` to `cli.py`, and set `image=repo_image.cell_tag(repo)` in the call above. `cell_tag` derives the tag without rebuilding (`repos/image.py:19`), and `run_one_cell` has already built it during preflight — so nothing needs threading through `CellOutcome`.

- [ ] **Step 7: Write the end-to-end test**

Append to `tests/test_package.py`:

```python
import json
from types import SimpleNamespace

from saffron.ledger import Ledger
from saffron.phases.package import package


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

    # The cell's patch touches line 3 ...
    patch_text = (
        "diff --git a/f.txt b/f.txt\n--- a/f.txt\n+++ b/f.txt\n"
        "@@ -1,5 +1,5 @@\n a\n b\n-c\n+CELL\n d\n e\n"
    )
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

    outcome = SimpleNamespace(
        state="READY_FOR_REVIEW", task_id=task_id, run_id=run_id,
        task_dir=task_dir, spent_usd=6.4, attempts=1, cell_head_sha="c" * 40,
        gates=[], new_failures=[], reviews=[], rebut_result=None,
        agent_subjects=[],
    )
    spec = SimpleNamespace(
        id="SA-0005", title="package a green cell", risk="standard",
        touches=[], acceptance_criteria=[], type="feature",
    )
    policy = SimpleNamespace(integrity=SimpleNamespace(test_paths=["tests/**"]))

    def never_called(argv):
        raise AssertionError("gh must not be reached on a conflict")

    result = package(
        outcome, spec=spec, repo=work, mirror=mirror, policy=policy,
        image="unused", ledger=ledger, out_dir=tmp_path / "batch",
        token=None, gh=never_called, watch=lambda _: None,
    )

    assert result.state == "MERGE_FAILED"
    row = next(r for r in ledger.queue_lines() if r["task_id"] == task_id)
    assert row["state"] == "MERGE_FAILED"
    # The remote must be untouched — the assertion the state alone cannot make.
    assert remote_sha(str(remote), "saffron/SA-0005", cwd=tmp_path) == ""
    ledger.close()
```

- [ ] **Step 8: Run everything**

Run: `make check`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add saffron/phases/package.py saffron/cli.py saffron/ledger.py tests/
git commit -m "feat(package): a green cell becomes a pull request"
```

---

## Verification

- [ ] `make check` passes.
- [ ] `uv run pytest -m cell` passes, with the images from CLAUDE.md built.
- [ ] `grep -rn "pytest.skip\|TODO\|FIXME" tests/test_package*.py` returns nothing.
- [ ] `uv run saffron cell .saffron/specs/SA-0002-size-gate.md --repo .` on a green task opens a draft PR, and the branch is cut from today's default branch.
- [ ] `grep -rn "jinja" saffron/ pyproject.toml` returns nothing — `uv.lock` is unchanged.
- [ ] `git diff main --stat -- saffron/gates/` is empty: this sub-project touches no gate.
