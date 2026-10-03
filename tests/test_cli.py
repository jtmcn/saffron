"""The operator's only entry point, so it gets at least one end-to-end test."""

import argparse
import ast
import functools
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from saffron import (
    cli,
    end_review,
    follow_up,
    intake,
    preflight,
    qualify,
    spec_review,
    task,
)
from saffron.agents import context
from saffron.agents.findings import Finding
from saffron.cell import session
from saffron.cell.session import CellOutcome
from saffron.cli import main
from saffron.events import (
    FAMILIES,
    Ceilings,
    PhaseStart,
    Preflight,
    describe,
    read_log,
)
from saffron.ledger import Ledger
from saffron.phases import implement, package, review
from saffron.reconcile import HeadMoved, ReconcileResult
from saffron.record.memory import MemoryRecord
from saffron.repos.mirror import GitError
from saffron.repos.policy import Policy, load_policy
from saffron.scheduler import Candidate, Refusal
from tests.conftest import HostToolExecInTest
from tests.test_replay import target  # noqa: F401 — a pytest fixture, used by name


@pytest.fixture(autouse=True)
def a_token(monkeypatch):
    """`_run_cell` refuses without one; only the guard's own test unsets it."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-test")


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo_with_commit(path):
    path.mkdir()
    _git(path, "init", "-q")
    (path / "f.txt").write_text("a\n")
    _git(path, "add", "-A")
    _git(path, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "first")
    return path


def _rev_parse(repo, ref):
    return _git(repo, "rev-parse", ref)


def _namespace(repo, tmp_path):
    spec = tmp_path / "SY-1.md"
    spec.write_text(
        "---\nid: SY-1\ntitle: One\ntype: feature\ntouches: ['src/**']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    return argparse.Namespace(
        repo=repo,
        spec=spec,
        home=tmp_path / "home",
        budget=None,
        max_attempts=None,
        max_turns=None,
    )


def test_replay_from_the_command_line_lands_everything_under_home(
    target,  # noqa: F811 — the imported fixture, injected by pytest
    tmp_path,
    capsys,
):
    home = tmp_path / "home"

    assert main(["--home", str(home), "replay", str(target), "7"]) == 0

    assert (home / "mirrors").is_dir()
    assert (home / "ledger.db").is_file()
    out_dir = home / "batches" / "v0"
    assert (out_dir / "SY-9001" / "pr_body.md").is_file()
    assert (out_dir / "index.html").is_file()
    assert "SY-9001" in capsys.readouterr().out


def test_the_exit_code_distinguishes_the_terminal_states(monkeypatch, tmp_path):
    """A script reads the exit code and nothing else: 0 reviewable, 2 the
    infrastructure failed, 1 the task did not make it (§3.3)."""
    from saffron import cli

    spec = tmp_path / "SY-1.md"
    spec.write_text(
        "---\nid: SY-1\ntitle: One\ntype: feature\ntouches: ['src/**']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.repos.mirror.ensure_mirror", lambda repo, at: at)
    monkeypatch.setattr(
        "saffron.phases.package.real_remote", lambda repo: "https://github.com/o/r.git"
    )
    monkeypatch.setattr(
        "saffron.phases.package.fetch_default_branch",
        lambda mirror, url: ("main", "a" * 40),
    )

    # PACKAGE is wired in behind READY_FOR_REVIEW and has its own tests; what
    # this one asserts is the exit code the wiring produces.
    monkeypatch.setattr(
        cli.package_phase,
        "package",
        lambda outcome, **kwargs: package.PackageResult(
            state="READY_FOR_REVIEW", pr_url="https://github.com/o/r/pull/1"
        ),
    )

    states = iter(["READY_FOR_REVIEW", "EXHAUSTED", "PREFLIGHT_FAILED"])
    monkeypatch.setattr(
        task,
        "run_one_cell",
        lambda *a, **k: session.CellOutcome(
            state=next(states), task_id=1, run_id=1, task_dir=tmp_path
        ),
    )

    argv = ["--home", str(tmp_path / "home"), "cell", str(spec)]
    assert [cli.main(argv), cli.main(argv), cli.main(argv)] == [0, 1, 2]

    # A driver crash is an infrastructure abort too. Without a handler it exits
    # 1 — the code that means "the task did not make it", i.e. the abort reading
    # as an ordinary task outcome.
    def _crash(*_a, **_k):
        raise session.CellSessionError("the turn returned no session_id")

    monkeypatch.setattr(task, "run_one_cell", _crash)
    assert cli.main(argv) == 2


def test_an_unpackaged_task_names_the_branch_its_work_was_pushed_to(
    monkeypatch, tmp_path, capsys
):
    """The operator's only route back to work PACKAGE never packaged is
    knowing the batch tree exists. After `push_unpackaged_work`, it is one
    line of output — and `saffron cell` still exits 1 for it, as it does for
    a push that failed (§3.3)."""
    from saffron import cli

    spec = tmp_path / "SY-3.md"
    spec.write_text(
        "---\nid: SY-3\ntitle: Three\ntype: feature\ntouches: ['src/**']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.repos.mirror.ensure_mirror", lambda repo, at: at)
    monkeypatch.setattr(
        "saffron.phases.package.real_remote", lambda repo: "https://github.com/o/r.git"
    )
    monkeypatch.setattr(
        "saffron.phases.package.fetch_default_branch",
        lambda mirror, url: ("main", "a" * 40),
    )
    monkeypatch.setattr(
        cli.package_phase,
        "push_unpackaged_work",
        lambda *a, **k: package.PushResult(
            pushed=True,
            branch="saffron/SY-3",
            pushed_sha="b" * 40,
            note=f"pushed saffron/SY-3 @ {'b' * 12}",
        ),
    )
    monkeypatch.setattr(
        task,
        "run_one_cell",
        lambda *a, **k: session.CellOutcome(
            state="EXHAUSTED", task_id=1, run_id=1, task_dir=tmp_path
        ),
    )

    argv = ["--home", str(tmp_path / "home"), "cell", str(spec)]
    assert cli.main(argv) == 1

    printed = capsys.readouterr().out
    assert "saffron/SY-3" in printed
    assert "b" * 12 in printed
    assert "SY-3" in printed and "EXHAUSTED" in printed


def test_no_signature_in_the_package_still_takes_a_watch():
    """`SA-0031` migrated `cell/session.py`'s own 64 call sites off a bare
    `watch(str)` callback onto `emit(Event)`; this spec finishes the seam for
    the two files that were left behind. No function anywhere in `saffron/`
    may still take a parameter named `watch`, and neither
    `saffron/phases/package.py` nor `saffron/cli.py` may still call one."""
    import ast

    root = Path(cli.__file__).resolve().parent

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            # `ast.Lambda` is in the walk because this spec's own `emit`
            # defaults are lambdas: a lambda is the shape a `watch` parameter
            # would come back in, and without it one passed this test.
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                names = {
                    arg.arg
                    for arg in (
                        *node.args.posonlyargs,
                        *node.args.args,
                        *node.args.kwonlyargs,
                    )
                }
                assert "watch" not in names, (
                    f"{path.relative_to(root)}:{getattr(node, 'name', '<lambda>')} "
                    "still takes watch"
                )

    # Calls, parsed — not the substring `watch(`, which a comment recalling
    # "the old `watch(str)` callback" would fail while changing nothing.
    for path in (root / "phases" / "package.py", Path(cli.__file__)):
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if not isinstance(node, ast.Call):
                continue
            called = node.func
            name = (
                called.id
                if isinstance(called, ast.Name)
                else called.attr
                if isinstance(called, ast.Attribute)
                else ""
            )
            assert name != "watch", f"{path.name}:{node.lineno} still calls watch"


def test_package_events_land_in_the_runs_own_log(monkeypatch, tmp_path):
    """`cli.py` builds one `emit` fan-out and hands the identical object to
    both `run_one_cell` and `package()`, so PACKAGE's own events reach the
    same `events.jsonl` as everything else in the run — not merely the
    terminal, which the old free-string `watch(...)` already reached."""
    spec = tmp_path / "SY-1.md"
    spec.write_text(
        "---\nid: SY-1\ntitle: One\ntype: feature\ntouches: ['src/**']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.repos.mirror.ensure_mirror", lambda repo, at: at)
    monkeypatch.setattr(
        "saffron.phases.package.real_remote", lambda repo: "https://github.com/o/r.git"
    )
    monkeypatch.setattr(
        "saffron.phases.package.fetch_default_branch",
        lambda mirror, url: ("main", "a" * 40),
    )

    captured: list = []

    def _fake_run_one_cell(cell_spec, **kwargs):
        emit = kwargs["emit"]
        captured.append(emit)
        emit(
            Preflight(
                timestamp=1.0,
                spec_id=cell_spec.spec_id,
                step="cell_up",
                detail="from run_one_cell",
            )
        )
        return session.CellOutcome(
            state="READY_FOR_REVIEW", task_id=1, run_id=1, task_dir=tmp_path
        )

    def _fake_package(outcome, **kwargs):
        emit = kwargs["emit"]
        captured.append(emit)
        emit(
            PhaseStart(
                timestamp=2.0,
                spec_id=kwargs["spec"].id,
                phase="PACKAGE",
                label="PACKAGE",
                detail="from package",
            )
        )
        return package.PackageResult(
            state="READY_FOR_REVIEW", pr_url="https://github.com/o/r/pull/1"
        )

    monkeypatch.setattr(task, "run_one_cell", _fake_run_one_cell)
    monkeypatch.setattr(cli.package_phase, "package", _fake_package)

    home = tmp_path / "home"
    assert cli.main(["--home", str(home), "cell", str(spec)]) == 0

    # The same object, not two lookalikes: proof it was built once and shared.
    assert len(captured) == 2 and captured[0] is captured[1]

    events = read_log(home / "batches" / "v0" / "SY-1")
    details = [
        event.detail for event in events if isinstance(event, Preflight | PhaseStart)
    ]
    assert "from run_one_cell" in details
    assert "from package" in details


def test_a_setup_failure_before_the_cell_exits_two_as_well(monkeypatch, tmp_path):
    """Everything the setup path raises — an unreadable spec or policy, a mirror
    that will not clone, a repo with no HEAD — happens before a cell exists and
    is the same infrastructure failure. Unhandled it is a traceback and a 1."""
    from saffron import cli
    from saffron.repos.mirror import GitError
    from saffron.repos.policy import PolicyError

    spec = tmp_path / "SY-2.md"
    spec.write_text(
        "---\nid: SY-2\ntitle: Two\ntype: feature\ntouches: ['src/**']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.repos.mirror.ensure_mirror", lambda repo, at: at)
    monkeypatch.setattr(
        "saffron.phases.package.real_remote", lambda repo: "https://github.com/o/r.git"
    )
    monkeypatch.setattr(
        "saffron.phases.package.fetch_default_branch",
        lambda mirror, url: ("main", "a" * 40),
    )
    argv = ["--home", str(tmp_path / "home"), "cell", str(spec)]

    for broke in (
        PolicyError("policy.yaml declares a gate that is not executable"),
        GitError("the mirror could not be cloned"),
        subprocess.CalledProcessError(128, "git rev-parse HEAD"),
    ):

        def _raise(*_a, _broke=broke, **_k):
            raise _broke

        monkeypatch.setattr(task, "run_one_cell", _raise)
        assert cli.main(argv) == 2

    # Including the ones no tuple would have named: an OSError, a sqlite3
    # error, a pydantic failure from an SDK shape change.
    for broke in (OSError("no such device"), ValueError("not the shape")):

        def _raise_other(*_a, _broke=broke, **_k):
            raise _broke

        monkeypatch.setattr(task, "run_one_cell", _raise_other)
        assert cli.main(argv) == 2

    # And the spec itself, which is read before `run_one_cell` is ever called.
    bad = tmp_path / "SY-3.md"
    bad.write_text("no frontmatter here\n")
    assert cli.main(["--home", str(tmp_path / "home"), "cell", str(bad)]) == 2


def test_a_package_that_fails_and_one_that_breaks_exit_differently(
    monkeypatch, tmp_path
):
    """MERGE_FAILED is the task's problem (1); a PackageError is the
    toolchain's (2). Collapsing them would send an operator to read a diff
    when the real failure was their credentials."""
    from saffron import cli

    spec = tmp_path / "SY-3.md"
    spec.write_text(
        "---\nid: SY-3\ntitle: Three\ntype: feature\ntouches: ['src/**']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.repos.mirror.ensure_mirror", lambda repo, at: at)
    monkeypatch.setattr(
        "saffron.phases.package.real_remote", lambda repo: "https://github.com/o/r.git"
    )
    monkeypatch.setattr(
        "saffron.phases.package.fetch_default_branch",
        lambda mirror, url: ("main", "a" * 40),
    )
    monkeypatch.setattr(
        task,
        "run_one_cell",
        lambda *a, **k: session.CellOutcome(
            state="READY_FOR_REVIEW", task_id=1, run_id=1, task_dir=tmp_path
        ),
    )
    argv = ["--home", str(tmp_path / "home"), "cell", str(spec)]

    monkeypatch.setattr(
        cli.package_phase,
        "package",
        lambda outcome, **kwargs: package.PackageResult(
            state="MERGE_FAILED", note="conflicts with main"
        ),
    )
    assert cli.main(argv) == 1

    def _broke(outcome, **kwargs):
        raise package.PackageError("gh is unavailable")

    monkeypatch.setattr(cli.package_phase, "package", _broke)
    assert cli.main(argv) == 2


def test_a_non_github_origin_fails_before_the_cell_starts(tmp_path, monkeypatch):
    """`package` needs the slug and does not reach it until the budget is
    spent, so the refusal belongs beside the unreachable-remote one (§5.1)."""
    repo = _repo_with_commit(tmp_path / "repo")
    _git(repo, "remote", "add", "origin", "git@gitlab.com:group/owner/repo.git")

    started = False

    def _started(*_a, **_k):
        nonlocal started
        started = True
        raise SystemExit(0)

    monkeypatch.setattr("saffron.task.run_one_cell", _started)
    # Matched, not merely typed: a `fetch_default_branch` that reached gitlab
    # and failed raises the same class, and would pass a bare `raises`.
    with pytest.raises(package.PackageError, match="cannot read owner/repo"):
        cli._run_cell(
            _namespace(repo, tmp_path), Ledger(tmp_path / "l.db"), tmp_path / "out"
        )
    assert not started


def _local_origin(tmp_path):
    """A repo whose origin is a bare clone on disk. `_run_cell` fetches the
    default branch for real, so a github.com URL would reach the network."""
    repo = _repo_with_commit(tmp_path / "repo")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(repo), str(remote)], check=True)
    _git(repo, "remote", "add", "origin", str(remote))
    return repo


def _push_parent_branch(repo, branch, *, content="the parent's work\n"):
    """A real branch on the real origin, at a real commit. `_resolve_stacked_on`
    fetches the parent rather than trusting the ledger's recorded sha, so a
    parent that exists only as a ledger row is not a parent."""
    was = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(repo, "checkout", "-q", "-b", branch)
    (repo / f"{branch.replace('/', '-')}.txt").write_text(content)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", branch)
    head = _rev_parse(repo, "HEAD")
    _git(repo, "push", "-q", "origin", branch)
    _git(repo, "checkout", "-q", was)
    return head


def _mirror_of(tmp_path, repo, *, name="resolver.git"):
    """The pair `_resolve_stacked_on` needs, built the way `_run_cell` builds
    them: a real bare mirror and the origin url it fetches from."""
    from saffron.repos import mirror as git_mirror

    return git_mirror.ensure_mirror(repo, tmp_path / name), package.real_remote(repo)


def _local_origin_with_policy(tmp_path, policy_yaml, *, dirname="repo-protected"):
    """`_local_origin`, plus a real `.saffron/policy.yaml` committed *before*
    the bare clone is cut — the same ordering `_repo_with_spec` uses, and for
    the same reason: `base_sha` is the remote's head, so a file added after
    the clone would never reach the export `_run_cell` reads it from."""
    repo = _repo_with_commit(tmp_path / dirname)
    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text(policy_yaml)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "policy")
    remote = tmp_path / f"{dirname}-remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(repo), str(remote)], check=True)
    _git(repo, "remote", "add", "origin", str(remote))
    # The working copy's policy is then made to disagree with the committed
    # one. Without this the two reads are indistinguishable, and rewriting
    # the export read to a working-copy read — backlog items 13 and 15, the
    # exact mistake `SA-0023`'s own notes name twice — leaves the suite
    # green. Measured: it did, until this line.
    (repo / ".saffron" / "policy.yaml").write_text(
        "gates: {}\nprotected: []\nintegrity:\n  test_paths: ['tests/**']\n"
    )
    return repo


def _local_origin_with_marker(tmp_path, path, spec_id, *, dirname="repo-marked"):
    """`_local_origin_with_policy`'s shape, for a marker instead of a
    policy — committed before the bare clone is cut."""
    repo = _repo_with_commit(tmp_path / dirname)
    marker = repo / path
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f"# saffron:retired-by {spec_id}\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "marker")
    remote = tmp_path / f"{dirname}-remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(repo), str(remote)], check=True)
    _git(repo, "remote", "add", "origin", str(remote))
    return repo


def test_a_spec_whose_touches_cannot_reach_its_own_marker_refuses_before_the_cell_starts(
    tmp_path, monkeypatch, capsys
):
    """`SA-0027`'s attended-path witness: a real marker at `base_sha` a real
    spec's `touches` do not cover, driven through the real `cli._run_cell` —
    the defect `SA-0026`'s own review fixed by hand twice (item 35)."""
    repo = _local_origin_with_marker(tmp_path, "tests/test_package.py", "SY-9")
    args = _namespace(repo, tmp_path)
    args.spec = tmp_path / "SY-9.md"
    args.spec.write_text(
        "---\nid: SY-9\ntitle: Nine\ntype: feature\ntouches: ['saffron/x.py']\n"
        "---\n\n## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    started = False

    def _started(*_a, **_k):
        nonlocal started
        started = True
        raise SystemExit(0)

    monkeypatch.setattr("saffron.task.run_one_cell", _started)
    ledger = Ledger(tmp_path / "l.db")

    result = cli._run_cell(args, ledger, tmp_path / "out")

    assert result == 1
    assert not started  # no cell, no model call
    out = capsys.readouterr().out
    assert "tests/test_package.py" in out
    assert "saffron/x.py" in out
    # No row left behind: the refusal happened before a task ever existed.
    count = ledger._db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 0
    ledger.close()


def _ceiling_spec(tmp_path, **frontmatter):
    spec = tmp_path / "SY-2.md"
    declared = "".join(f"{key}: {value}\n" for key, value in frontmatter.items())
    spec.write_text(
        "---\nid: SY-2\ntitle: Two\ntype: feature\ntouches: ['src/**']\n"
        + declared
        + "---\n\n## Acceptance criteria\n- [ ] it works\n"
    )
    return spec


def _capture_cell_spec(monkeypatch, repo, tmp_path, namespace, capsys, ledger=None):
    """`ledger` is `None` for every caller before `SA-0026` — a fresh, unseeded
    one, same as always. A caller proving `depends_on` resolution needs one
    already carrying a parent's row, so it may pass its own instead."""
    captured: dict = {}

    def _capture(cell_spec, **_kwargs):
        captured["spec"] = cell_spec
        raise SystemExit(0)

    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    monkeypatch.setattr("saffron.task.run_one_cell", _capture)
    with pytest.raises(SystemExit):
        cli._run_cell(namespace, ledger or Ledger(tmp_path / "l.db"), tmp_path / "out")
    return captured["spec"], capsys.readouterr().out


def test_a_specs_own_ceilings_reach_the_cell(tmp_path, monkeypatch, capsys):
    """All three were parsed and validated and then discarded for the flags'
    defaults. `SA-0005` was stopped by the turn ceiling it could not raise,
    with more than half of the budget it *had* declared unspent."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, budget_usd=31.5, max_attempts=7, max_turns=120)

    cell_spec, printed = _capture_cell_spec(monkeypatch, repo, tmp_path, args, capsys)

    assert (cell_spec.budget_usd, cell_spec.max_attempts, cell_spec.max_turns) == (
        31.5,
        7,
        120,
    )
    assert "budget_usd=31.5 (spec)" in printed
    assert "max_turns=120 (spec)" in printed


def test_a_ceiling_the_spec_never_stated_is_not_labelled_as_the_specs(
    tmp_path, monkeypatch, capsys
):
    """A pydantic default is not a declaration. Calling it `(spec)` sends the
    operator to grep a spec file for a line that is not in it — the same
    conflation, one layer down from the argparse one."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)  # its spec declares no ceiling at all

    cell_spec, printed = _capture_cell_spec(monkeypatch, repo, tmp_path, args, capsys)

    assert cell_spec.max_turns == 60
    assert "max_turns=60 (default)" in printed
    assert "(spec)" not in printed


def test_a_flag_overrides_the_spec_and_says_which_it_was(tmp_path, monkeypatch, capsys):
    """The flag is how an operator re-runs a spec under a different ceiling, so
    it still wins — but which one is in force has to be visible on the way in,
    not inferred from an exit code on the way out."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, budget_usd=31.5, max_attempts=7, max_turns=120)
    args.max_turns = 40

    cell_spec, printed = _capture_cell_spec(monkeypatch, repo, tmp_path, args, capsys)

    assert cell_spec.max_turns == 40
    assert cell_spec.budget_usd == 31.5  # untouched by the one flag given
    assert "max_turns=40 (flag)" in printed
    assert "budget_usd=31.5 (spec)" in printed


def test_a_specs_declared_risk_reaches_the_cell(tmp_path, monkeypatch, capsys):
    """`SA-0005` computed `effective_risk` from `CellSpec.risk`, but nothing
    ever set it, so `effective_risk`'s first clause — set explicitly in the
    spec — could only ever see the pydantic default `standard`. The spec here
    declares `elevated`; the cell must be handed exactly that, not the field's
    default."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, risk="elevated")

    cell_spec, _printed = _capture_cell_spec(monkeypatch, repo, tmp_path, args, capsys)

    assert cell_spec.risk == "elevated"


def test_a_depends_on_reaches_the_cell_unstacked(tmp_path, monkeypatch, capsys):
    """`_run_cell` does consult `depends_on` now (`SA-0026`,
    `_resolve_stacked_on`) — but this repo's fresh `Ledger` has never seen
    this origin, so `resolve_repo_id` finds nothing and resolution falls
    through to unstacked, the correct answer for a repo the ledger has no
    history for. `test_a_resolvable_parent_reaches_the_cell_stacked` below is
    the seeded-ledger case this one is not."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SA-0001]")

    cell_spec, _printed = _capture_cell_spec(monkeypatch, repo, tmp_path, args, capsys)

    # The `depends_on` half of the claim, not just the `stacked_on` half:
    # a field silently dropped at intake would leave this green.
    assert intake.load_spec(args.spec)[0].depends_on == ["SA-0001"]
    assert cell_spec.stacked_on is None


def test_a_resolvable_parent_reaches_the_cell_stacked(tmp_path, monkeypatch, capsys):
    """The seeded-ledger half of the claim above: a parent recorded
    `READY_FOR_REVIEW`, with its branch really pushed, resolves to a real
    `CellSpec.stacked_on` — read back through the whole of `_run_cell` from a
    ledger row and a git ref the test did not hand the resolver.

    The recorded `pushed_sha` is deliberately a commit no repository holds:
    the ledger says *which branch*, and the branch says which commit."""
    repo = _local_origin(tmp_path)
    head = _push_parent_branch(repo, "saffron/SY-9000")
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SY-9000]")

    ledger = Ledger(tmp_path / "seeded.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    parent = _seed_task(ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW")
    ledger.record_push(parent, "d" * 40)

    cell_spec, printed = _capture_cell_spec(
        monkeypatch, repo, tmp_path, args, capsys, ledger=ledger
    )

    assert cell_spec.stacked_on == head != "d" * 40
    # Which tree a run was cut from is not in the exit code.
    assert f"stacked on saffron/SY-9000 @ {head[:12]}" in printed


def test_a_parent_branch_the_mirror_cannot_reach_is_an_unstacked_cell(
    tmp_path, monkeypatch, capsys
):
    """`ensure_mirror` fetches `+refs/*:refs/*` from the operator's local
    checkout with `--prune`, so a parent branch they do not happen to have
    locally is deleted from the mirror — this repo's own mirror had already
    lost `saffron/SA-0025` that way. The resolver fetches the branch itself;
    when there is none to fetch, the answer is an ordinary unstacked cell and
    a line saying so, never a dead run."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SY-9000]")

    # Everything the ledger can say is right; the branch is simply not there.
    ledger = Ledger(tmp_path / "seeded.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    parent = _seed_task(ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW")
    ledger.record_push(parent, "d" * 40)

    cell_spec, printed = _capture_cell_spec(
        monkeypatch, repo, tmp_path, args, capsys, ledger=ledger
    )

    assert cell_spec.stacked_on is None
    assert "unstacked: parent branch saffron/SY-9000 is gone" in printed


def _gh_by_url(urls_asked, answers):
    """A `gh` double keyed by the exact pull request url in `argv`, the shape
    `b-877e93`'s three witnesses share: each records every url it is asked
    about and answers only the ones a caller declared."""

    def fake_gh(argv):
        url = argv[3]
        urls_asked.append(url)
        answer = answers.get(url, {"state": "OPEN", "reviewDecision": None})
        return subprocess.CompletedProcess(argv, 0, json.dumps(answer), "")

    return fake_gh


def _new_parent_preflights(out_dir, spec_id, parent_id, before):
    """The `Preflight` events one `_capture_cell_spec` call added, naming
    `parent_id`. Never the ones an earlier call in the same test already
    wrote to the same `events.jsonl`."""
    events = read_log(out_dir / spec_id)[before:]
    return [
        event
        for event in events
        if isinstance(event, Preflight) and parent_id in event.detail
    ]


def test_saffron_cell_cuts_from_the_default_branch_once_its_parents_newest_task_merged_or_closed(
    tmp_path, monkeypatch, capsys
):
    """`b-877e93`: `saffron cell` reconciles the parent it stacks on, so a
    merge or a close nobody scanned for yet still cuts the child loose.
    The newest task decides, even over an older row still waiting. Only
    the parent's own tasks are ever asked about."""
    repo = _local_origin(tmp_path)
    head = _push_parent_branch(repo, "saffron/SY-9000")
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SY-9000]")

    ledger = Ledger(tmp_path / "seeded.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    older_pr = "https://github.com/o/r/pull/1"
    newer_pr = "https://github.com/o/r/pull/2"
    sibling_pr = "https://github.com/o/r/pull/3"
    older = _seed_task(
        ledger, repo_id, spec_id="SY-9000", state="ORPHANED", pr_url=older_pr
    )
    ledger.record_push(older, "1" * 40)
    newer = _seed_task(
        ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW", pr_url=newer_pr
    )
    # A different spec whose id starts with the parent's: the filter must
    # match `SY-9000` exactly, never by prefix.
    sibling = _seed_task(
        ledger, repo_id, spec_id="SY-90001", state="READY_FOR_REVIEW", pr_url=sibling_pr
    )

    urls_asked: list[str] = []
    answers: dict[str, dict] = {}
    monkeypatch.setattr("saffron.cli.run_gh", _gh_by_url(urls_asked, answers))

    def state_of(task_id):
        row = ledger._db.execute(
            "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return row["state"]

    def run_and_check(expected_state, expected_urls):
        urls_asked.clear()
        before = len(read_log(tmp_path / "out" / "SY-2"))
        cell_spec, _printed = _capture_cell_spec(
            monkeypatch, repo, tmp_path, args, capsys, ledger=ledger
        )
        assert cell_spec.stacked_on is None
        assert urls_asked == expected_urls
        assert state_of(newer) == expected_state
        lines = _new_parent_preflights(tmp_path / "out", "SY-2", "SY-9000", before)
        assert len(lines) == 1
        assert lines[0].step == "unstacked"
        assert expected_state in lines[0].detail
        for other in {"MERGED", "REJECTED", "CHANGES_REQUESTED"} - {expected_state}:
            assert other not in lines[0].detail

    # 1. The newer task is READY_FOR_REVIEW, and gh answers merged.
    answers[newer_pr] = {"state": "MERGED", "reviewDecision": None}
    run_and_check("MERGED", [newer_pr])

    # 2. Nothing is reset, so the newer task is already MERGED, not asked.
    run_and_check("MERGED", [])

    # 3. The newer task is APPROVED, and gh answers merged.
    ledger.set_task_state(newer, "APPROVED")
    run_and_check("MERGED", [newer_pr])

    # 4. The newer task is READY_FOR_REVIEW, and gh answers CLOSED.
    ledger.set_task_state(newer, "READY_FOR_REVIEW")
    answers[newer_pr] = {"state": "CLOSED", "reviewDecision": None}
    run_and_check("REJECTED", [newer_pr])

    # 5. Both tasks are READY_FOR_REVIEW. gh answers open for the older
    # one and merged for the newer one.
    ledger.set_task_state(older, "READY_FOR_REVIEW")
    ledger.set_task_state(newer, "READY_FOR_REVIEW")
    answers[older_pr] = {"state": "OPEN", "reviewDecision": None}
    answers[newer_pr] = {"state": "MERGED", "reviewDecision": None}
    run_and_check("MERGED", [older_pr, newer_pr])

    assert state_of(older) == "READY_FOR_REVIEW"
    assert state_of(sibling) == "READY_FOR_REVIEW"

    # 6. A dead newest task does not decide. The older waiting task stacks.
    ledger.set_task_state(newer, "ORPHANED")
    urls_asked.clear()
    before = len(read_log(tmp_path / "out" / "SY-2"))
    cell_spec, _printed = _capture_cell_spec(
        monkeypatch, repo, tmp_path, args, capsys, ledger=ledger
    )
    assert cell_spec.stacked_on == head
    assert urls_asked == [older_pr]
    assert state_of(older) == "READY_FOR_REVIEW"
    lines = _new_parent_preflights(tmp_path / "out", "SY-2", "SY-9000", before)
    assert all(line.step != "unstacked" for line in lines)
    ledger.close()


def test_saffron_cell_stacks_on_a_parent_it_could_not_ask_about_and_says_so_once(
    tmp_path, monkeypatch, capsys
):
    """`b-877e93`: a `gh` that cannot answer must not refuse an attended run.
    It leaves the parent's task exactly as it was, and says, once, that
    GitHub could not be asked, whatever state that row keeps."""
    repo = _local_origin(tmp_path)
    head = _push_parent_branch(repo, "saffron/SY-9000")
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SY-9000]")

    ledger = Ledger(tmp_path / "seeded.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    older_pr = "https://github.com/o/r/pull/1"
    newer_pr = "https://github.com/o/r/pull/2"
    older = _seed_task(
        ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW", pr_url=older_pr
    )
    newer = _seed_task(
        ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW", pr_url=newer_pr
    )
    ledger.record_push(older, "1" * 40)
    ledger.record_push(newer, "2" * 40)

    def run_once(before):
        cell_spec, _printed = _capture_cell_spec(
            monkeypatch, repo, tmp_path, args, capsys, ledger=ledger
        )
        assert cell_spec.stacked_on == head
        return _new_parent_preflights(tmp_path / "out", "SY-2", "SY-9000", before)

    def assert_gh_line(line):
        assert line.step == "gh_unreachable"
        assert "GitHub could not be asked" in line.detail
        assert "SY-9000" in line.detail
        assert any(describe(line).startswith(f.prefix) for f in FAMILIES)

    def exit_one(_argv):
        return subprocess.CompletedProcess(_argv, 1, "", "boom")

    def cannot_start(_argv):
        raise FileNotFoundError("gh")

    def answers_undecided(_argv):
        return subprocess.CompletedProcess(
            _argv, 0, '{"state": "OPEN", "reviewDecision": "REVIEW_REQUIRED"}', ""
        )

    before = len(read_log(tmp_path / "out" / "SY-2"))
    monkeypatch.setattr("saffron.cli.run_gh", exit_one)
    lines = run_once(before)
    assert len(lines) == 1
    assert lines[0].step != "unstacked"
    assert_gh_line(lines[0])

    before = len(read_log(tmp_path / "out" / "SY-2"))
    monkeypatch.setattr("saffron.cli.run_gh", cannot_start)
    lines = run_once(before)
    assert len(lines) == 1
    assert lines[0].step != "unstacked"
    assert_gh_line(lines[0])

    before = len(read_log(tmp_path / "out" / "SY-2"))
    monkeypatch.setattr("saffron.cli.run_gh", answers_undecided)
    lines = run_once(before)
    assert lines == []

    ledger.set_task_state(newer, "CHANGES_REQUESTED")
    before = len(read_log(tmp_path / "out" / "SY-2"))
    monkeypatch.setattr("saffron.cli.run_gh", exit_one)
    lines = run_once(before)
    assert len(lines) == 2
    assert all(line.step != "unstacked" for line in lines)
    assert sum("CHANGES_REQUESTED" in line.detail for line in lines) == 1
    assert_gh_line(lines[0])
    ledger.close()


def test_saffron_cell_stacks_on_a_changes_requested_parent_and_names_the_state(
    tmp_path, monkeypatch, capsys
):
    """`b-877e93`: a `CHANGES_REQUESTED` parent still keeps its child
    stacked on the parent's branch, where the review fixes land. It says so
    once, whether this reconcile moved the task there or the ledger
    already held it there."""
    repo = _local_origin(tmp_path)
    head = _push_parent_branch(repo, "saffron/SY-9000")
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SY-9000]")

    ledger = Ledger(tmp_path / "seeded.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    parent_pr = "https://github.com/o/r/pull/1"
    parent = _seed_task(
        ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW", pr_url=parent_pr
    )
    ledger.record_push(parent, "1" * 40)

    def fake_gh(_argv):
        return subprocess.CompletedProcess(
            _argv, 0, '{"state": "OPEN", "reviewDecision": "CHANGES_REQUESTED"}', ""
        )

    monkeypatch.setattr("saffron.cli.run_gh", fake_gh)

    for _ in range(2):
        before = len(read_log(tmp_path / "out" / "SY-2"))
        cell_spec, _printed = _capture_cell_spec(
            monkeypatch, repo, tmp_path, args, capsys, ledger=ledger
        )
        assert cell_spec.stacked_on == head
        row = ledger._db.execute(
            "SELECT state FROM tasks WHERE task_id = ?", (parent,)
        ).fetchone()
        assert row["state"] == "CHANGES_REQUESTED"
        lines = _new_parent_preflights(tmp_path / "out", "SY-2", "SY-9000", before)
        assert len(lines) == 1
        assert lines[0].step != "unstacked"
        assert "CHANGES_REQUESTED" in lines[0].detail

    ledger.close()


def test_the_cell_is_cut_from_the_branchs_head_not_the_ledgers_recorded_sha(
    tmp_path, monkeypatch, capsys
):
    """`pushed_sha` is written by PACKAGE — or, since `SA-0069`, by a push of
    unpackaged work when PACKAGE never ran. Every review fix an operator
    commits by hand moves the branch past it, so the recorded sha is a tree
    the parent's pull request no longer shows — measured on this repository:
    task 26's `pushed_sha` was a commit behind `saffron/SA-0026`'s head while
    that pull request was open. A child cut from the recorded sha spends a
    whole cell on code the operator has already amended."""
    repo = _local_origin(tmp_path)
    packaged = _push_parent_branch(repo, "saffron/SY-9000")

    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SY-9000]")

    ledger = Ledger(tmp_path / "seeded.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    parent = _seed_task(ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW")
    ledger.record_push(parent, packaged)

    # The operator's review fix, after PACKAGE recorded the push.
    _git(repo, "checkout", "-q", "saffron/SY-9000")
    (repo / "fix.txt").write_text("the operator's review fix\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "fix")
    reviewed = _rev_parse(repo, "HEAD")
    _git(repo, "push", "-q", "origin", "saffron/SY-9000")
    _git(repo, "checkout", "-q", "-")

    cell_spec, _printed = _capture_cell_spec(
        monkeypatch, repo, tmp_path, args, capsys, ledger=ledger
    )

    assert cell_spec.stacked_on == reviewed != packaged


def test_a_stacked_worktree_passes_its_parents_branch_to_package(
    tmp_path, monkeypatch, capsys
):
    """Criterion 4: a task whose worktree was stacked must not reach a pull
    request that is not — `parent_branch` has to travel the same path as
    `stacked_on`, all the way to the `package()` call."""
    repo = _local_origin(tmp_path)
    _push_parent_branch(repo, "saffron/SY-9000")
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SY-9000]")

    ledger = Ledger(tmp_path / "seeded.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    parent = _seed_task(ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW")
    ledger.record_push(parent, "d" * 40)

    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    monkeypatch.setattr(
        "saffron.task.run_one_cell",
        lambda cell_spec, **k: session.CellOutcome(
            state="READY_FOR_REVIEW", task_id=1, run_id=1, task_dir=tmp_path
        ),
    )
    captured: dict = {}

    def _fake_package(outcome, **kwargs):
        captured.update(kwargs)
        return package.PackageResult(
            state="READY_FOR_REVIEW", pr_url="https://github.com/o/r/pull/1"
        )

    monkeypatch.setattr(cli.package_phase, "package", _fake_package)

    assert cli._run_cell(args, ledger, tmp_path / "out") == 0

    assert captured["parent_branch"] == "saffron/SY-9000"


def test_an_unstacked_worktree_passes_no_parent_branch_to_package(
    tmp_path, monkeypatch, capsys
):
    """The converse, and what `SA-0025`'s deleted text-search guard was
    reaching for: the parent branch is `None` on the path an operator takes
    for a spec with nothing to stack on. Asserted on the call `package()`
    actually received, so a keyword spelled some other way cannot satisfy it.
    """
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    args.spec = _ceiling_spec(tmp_path, depends_on="[SY-9000]")

    # Seeded, so the repo row exists and resolution genuinely runs — the
    # parent's task is `MERGED`, which needs no stacking.
    ledger = Ledger(tmp_path / "seeded.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    parent = _seed_task(ledger, repo_id, spec_id="SY-9000", state="MERGED")
    ledger.record_push(parent, "d" * 40)

    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    monkeypatch.setattr(
        "saffron.task.run_one_cell",
        lambda cell_spec, **k: session.CellOutcome(
            state="READY_FOR_REVIEW", task_id=1, run_id=1, task_dir=tmp_path
        ),
    )
    captured: dict = {}

    def _fake_package(outcome, **kwargs):
        captured.update(kwargs)
        return package.PackageResult(
            state="READY_FOR_REVIEW", pr_url="https://github.com/o/r/pull/1"
        )

    monkeypatch.setattr(cli.package_phase, "package", _fake_package)

    assert cli._run_cell(args, ledger, tmp_path / "out") == 0

    assert "parent_branch" in captured and captured["parent_branch"] is None


def test_only_the_first_depends_on_entry_is_a_stacking_candidate(tmp_path):
    """K=1: a spec with two unmerged parents does not stack on either one it
    does not name first — `depends_on[1]`'s own resolvable, waiting task and
    its real pushed branch must not leak into the result just because they
    could stack too."""
    repo = _local_origin(tmp_path)
    _push_parent_branch(repo, "saffron/SY-2")
    mirror, url = _mirror_of(tmp_path, repo)
    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, "/o")
    second = _seed_task(ledger, repo_id, spec_id="SY-2", state="READY_FOR_REVIEW")
    ledger.record_push(second, "b" * 40)

    stacked_on, parent_branch = task._resolve_stacked_on(
        ledger,
        repo_id,
        ["SY-1", "SY-2"],
        mirror=mirror,
        url=url,
        spec_id="SY-1",
        emit=lambda _: None,
    )

    assert (stacked_on, parent_branch) == (None, None)
    ledger.close()


def test_which_of_a_parents_rows_supplies_the_sha_is_the_newest_waiting_one(
    tmp_path,
):
    """This repo's own ledger holds ten tasks at one `spec_id`, mixing
    `READY_FOR_REVIEW` with three `ORPHANED` (`SA-0013`) — "the parent's
    task" is not a thing that exists until this states which row wins."""
    repo = _local_origin(tmp_path)
    head = _push_parent_branch(repo, "saffron/SA-0013")
    mirror, url = _mirror_of(tmp_path, repo)
    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, "/o")
    states = [
        "QUEUED",
        "ORPHANED",
        "REJECTED",
        "ORPHANED",
        "EXHAUSTED",
        "CHANGES_REQUESTED",
        "ORPHANED",
        "GATE_ERROR",
        "READY_FOR_REVIEW",
        "NOT_IMPLEMENTED",
    ]
    assert len(states) == 10
    assert states.count("ORPHANED") == 3
    waiting_row = None
    for i, state in enumerate(states):
        task_id = _seed_task(
            ledger, repo_id, spec_id="SA-0013", state=state, spec_sha=f"{i}" * 40
        )
        ledger.record_push(task_id, str(i) * 40)
        if state == "READY_FOR_REVIEW":
            waiting_row = task_id

    stacked_on, parent_branch = task._resolve_stacked_on(
        ledger,
        repo_id,
        ["SA-0013"],
        mirror=mirror,
        url=url,
        spec_id="SA-0013",
        emit=lambda _: None,
    )

    # The only READY_FOR_REVIEW row is index 8, and it is what admits the
    # parent at all. The sha is the branch's, not that row's `pushed_sha`
    # (which is `8` * 40, a commit no repository holds).
    assert (stacked_on, parent_branch) == (head, "saffron/SA-0013")

    # ...and with that one row's state changed, the same ten rows and the
    # same real branch resolve to nothing: it is the state that decides.
    assert waiting_row is not None
    ledger.set_task_state(waiting_row, "ORPHANED")
    assert task._resolve_stacked_on(
        ledger,
        repo_id,
        ["SA-0013"],
        mirror=mirror,
        url=url,
        spec_id="SA-0013",
        emit=lambda _: None,
    ) == (None, None)
    ledger.close()


def test_the_newest_of_several_waiting_rows_wins_not_the_first(tmp_path):
    """Waiting outranks dead whatever the row order, the same precedence
    `scheduler._dependency_refusal` gives it — proven here by a row that
    would win under "first waiting" losing to a later, still-waiting one.

    The rows carry *different* branches, which a task's rows normally do not:
    since the sha is now fetched from the branch, rows sharing one branch
    resolve to one sha whichever wins, and the choice would be unobservable."""
    repo = _local_origin(tmp_path)
    first = _push_parent_branch(repo, "saffron/SY-9-first")
    newest = _push_parent_branch(repo, "saffron/SY-9-newest")
    assert first != newest
    mirror, url = _mirror_of(tmp_path, repo)

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, "/o")
    for state, branch in [
        ("READY_FOR_REVIEW", "saffron/SY-9-first"),
        ("ORPHANED", "saffron/SY-9-orphan"),
        ("APPROVED", "saffron/SY-9-newest"),
    ]:
        task_id = _seed_task(
            ledger, repo_id, spec_id="SY-9", state=state, branch=branch
        )
        ledger.record_push(task_id, "1" * 40)

    stacked_on, branch = task._resolve_stacked_on(
        ledger,
        repo_id,
        ["SY-9"],
        mirror=mirror,
        url=url,
        spec_id="SY-9",
        emit=lambda _: None,
    )

    assert (stacked_on, branch) == (newest, "saffron/SY-9-newest")
    ledger.close()


@pytest.mark.parametrize(
    "bad_sha",
    [None, "", "not-a-sha", "abc123", "g" * 40, "a" * 40 + " ; rm -rf /"],
    ids=["absent", "empty", "short-non-hex", "too-short", "non-hex-40", "trailing"],
)
def test_an_unresolved_pushed_sha_yields_an_unstacked_cell_not_a_construction_error(
    tmp_path, bad_sha
):
    """`CellSpec.__post_init__` (`SA-0022`) raises `ValueError` on anything
    that is not `None` or a resolved sha — an operator's `saffron cell` must
    not die on a parent row this attended path cannot fully trust."""
    repo = _local_origin(tmp_path)
    # Pushed for real, so the fetch below would succeed: the only thing that
    # can refuse this row is the recorded push it does not evidence.
    _push_parent_branch(repo, "saffron/SY-9")
    mirror, url = _mirror_of(tmp_path, repo)

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, "/o")
    task_id = _seed_task(ledger, repo_id, spec_id="SY-9", state="READY_FOR_REVIEW")
    if bad_sha is not None:
        ledger.record_push(task_id, bad_sha)

    stacked_on, parent_branch = task._resolve_stacked_on(
        ledger,
        repo_id,
        ["SY-9"],
        mirror=mirror,
        url=url,
        spec_id="SY-9",
        emit=lambda _: None,
    )

    assert (stacked_on, parent_branch) == (None, None)
    ledger.close()


def test_a_row_with_no_branch_recorded_resolves_unstacked(tmp_path):
    """`tasks.branch` is nullable (`ledger.py`), and the branch is the half
    the ledger actually contributes now — a row without one cannot name a
    parent to fetch, however good its `pushed_sha` looks."""
    repo = _local_origin(tmp_path)
    _push_parent_branch(repo, "saffron/SY-9")
    mirror, url = _mirror_of(tmp_path, repo)

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, "/o")
    task_id = _seed_task(ledger, repo_id, spec_id="SY-9", state="READY_FOR_REVIEW")
    ledger.record_push(task_id, "1" * 40)
    ledger._db.execute("UPDATE tasks SET branch = NULL WHERE task_id = ?", (task_id,))
    ledger._db.commit()

    seen = []
    assert task._resolve_stacked_on(
        ledger,
        repo_id,
        ["SY-9"],
        mirror=mirror,
        url=url,
        spec_id="SY-9",
        emit=seen.append,
    ) == (None, None)
    # The row, not a ref that was never looked for.
    assert [describe(event) for event in seen] == [
        "unstacked: SY-9's newest waiting task records no pushed branch"
    ]
    ledger.close()


def test_a_parent_branch_that_is_gone_says_so_through_emit(tmp_path):
    """The second of the resolver's two `unstacked:` lines, and the one no
    test drove: a parent branch deleted between PACKAGE and this run. It is
    not a failure — a deleted branch has merged or been abandoned, and either
    way the default branch is the right cut — but an operator reading the
    morning's log has to be able to see why a spec with `depends_on` came out
    unstacked, which a line that only ever reached the terminal cannot tell
    them."""
    # No `_push_parent_branch`: the origin really has no `saffron/SY-9`, so
    # the fetch fails for git's own reason rather than a patched one. The
    # ledger row still looks perfect — a recorded branch and a resolved sha —
    # which is exactly the state a merged-and-deleted parent leaves behind.
    repo = _local_origin(tmp_path)
    mirror, url = _mirror_of(tmp_path, repo)

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, "/o")
    task_id = _seed_task(ledger, repo_id, spec_id="SY-9", state="READY_FOR_REVIEW")
    ledger.record_push(task_id, "1" * 40)

    seen = []
    assert task._resolve_stacked_on(
        ledger,
        repo_id,
        ["SY-9"],
        mirror=mirror,
        url=url,
        spec_id="SY-9",
        emit=seen.append,
    ) == (None, None)
    # git's own stderr rides along in the detail, so the line is matched by
    # its head rather than whole — the branch name is the part an operator
    # needs, and the part a demotion to `print` takes away.
    assert len(seen) == 1
    assert describe(seen[0]).startswith("unstacked: parent branch saffron/SY-9 is gone")
    ledger.close()


def test_no_repo_id_or_no_depends_on_resolves_unstacked(tmp_path):
    """A repo the ledger has never seen and a spec naming no parent are both
    the ordinary case, not an edge one — neither should need a task row to
    answer `(None, None)`."""
    repo = _local_origin(tmp_path)
    _push_parent_branch(repo, "saffron/SY-9")
    mirror, url = _mirror_of(tmp_path, repo)

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, "/o")
    task_id = _seed_task(ledger, repo_id, spec_id="SY-9", state="READY_FOR_REVIEW")
    ledger.record_push(task_id, "1" * 40)

    resolve = functools.partial(
        task._resolve_stacked_on,
        mirror=mirror,
        url=url,
        spec_id="SY-9",
        emit=lambda _: None,
    )
    assert resolve(ledger, None, ["SY-9"]) == (None, None)
    assert resolve(ledger, repo_id, []) == (None, None)
    ledger.close()


def test_a_specs_declared_witnesses_reach_the_cell(tmp_path, monkeypatch, capsys):
    """`cli.load_spec` parses the operator's host-side copy before the cell
    starts, so the witnesses the gate checks were never in `/work` — that, and
    `.saffron/**` being outside `touches`, is what stops the cell relaxing one.
    Parsed and then discarded would leave the gate with nothing to check."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    spec = tmp_path / "SY-3.md"
    spec.write_text(
        "---\nid: SY-3\ntitle: Three\ntype: feature\ntouches: ['src/**']\n"
        "acceptance:\n"
        "  - claim: it works\n"
        "    witness: tests/test_x.py::test_it_works\n"
        "---\n\nbody\n"
    )
    args.spec = spec

    cell_spec, _printed = _capture_cell_spec(monkeypatch, repo, tmp_path, args, capsys)

    assert [c.witness for c in cell_spec.acceptance] == [
        "tests/test_x.py::test_it_works"
    ]


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
    _git(
        repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "local only"
    )
    assert _rev_parse(repo, "HEAD") != default_head

    captured: dict[str, str] = {}

    def _capture(cell_spec, **kwargs):
        captured["base_sha"] = cell_spec.base_sha
        raise SystemExit(0)

    # A local-path origin, not shaped like a forge remote, so the preflight
    # slug is faked rather than the fixture contorted into a github.com URL.
    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    monkeypatch.setattr("saffron.task.run_one_cell", _capture)
    with pytest.raises(SystemExit):
        cli._run_cell(
            _namespace(repo, tmp_path), Ledger(tmp_path / "l.db"), tmp_path / "out"
        )

    assert captured["base_sha"] == default_head


def test_a_missing_token_fails_before_the_image_is_built(tmp_path, monkeypatch):
    """`session` forwards the token only if it is set, so an unset one bought a
    full preflight and then reached the agent as "Not logged in"."""
    repo = _repo_with_commit(tmp_path / "repo")
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

    reached = False

    def _reached(*_a, **_k):
        nonlocal reached
        reached = True
        raise SystemExit(0)

    # The mirror is the first thing `_run_cell` touches; nothing may run.
    # Patched at the canonical module, not through `cli`'s own namespace:
    # the hoist into `preflight.prepare_mirror` moved the call site, and a
    # dotted string through `saffron.cli` would have to keep tracking where
    # the call lives rather than what it calls.
    monkeypatch.setattr("saffron.repos.mirror.ensure_mirror", _reached)
    with pytest.raises(RuntimeError, match="CLAUDE_CODE_OAUTH_TOKEN is unset"):
        cli._run_cell(
            _namespace(repo, tmp_path), Ledger(tmp_path / "l.db"), tmp_path / "out"
        )
    assert not reached


def test_one_cell_still_prepares_itself_in_order_after_the_hoist(tmp_path, monkeypatch):
    """`_run_cell`'s own preparation, unchanged in order by the hoist into
    `preflight.prepare_mirror`: the token refusal still fires before the
    mirror is ever touched, and the mirror fetch, the non-forge origin
    refusal and the default-branch pin all still happen before a cell
    starts (`SA-0048`) — asserted on the order calls land in, not on the
    exit code alone."""
    order: list[str] = []

    def _mk(name, result):
        def _fn(*_a, **_k):
            order.append(name)
            return result

        return _fn

    monkeypatch.setattr(
        preflight.git_mirror, "ensure_mirror", _mk("mirror", tmp_path / "m")
    )
    monkeypatch.setattr(
        preflight.package_phase,
        "real_remote",
        _mk("real_remote", "https://github.com/o/r.git"),
    )
    monkeypatch.setattr(preflight.package_phase, "github_slug", _mk("origin", "o/r"))
    monkeypatch.setattr(
        preflight.package_phase,
        "fetch_default_branch",
        _mk("default_branch", ("main", "a" * 40)),
    )

    def _started(*_a, **_k):
        order.append("cell")
        raise SystemExit(0)

    monkeypatch.setattr(task, "run_one_cell", _started)

    repo = _repo_with_commit(tmp_path / "repo")
    with pytest.raises(SystemExit):
        cli._run_cell(
            _namespace(repo, tmp_path), Ledger(tmp_path / "l.db"), tmp_path / "out"
        )

    assert order == ["mirror", "real_remote", "origin", "default_branch", "cell"]

    # And the token refusal still fires before any of it: nothing above ran.
    order.clear()
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="CLAUDE_CODE_OAUTH_TOKEN is unset"):
        cli._run_cell(
            _namespace(repo, tmp_path), Ledger(tmp_path / "l2.db"), tmp_path / "out"
        )
    assert order == []


def test_a_spec_whose_touches_are_protected_refuses_before_the_cell_starts(
    tmp_path, monkeypatch, capsys
):
    """`SA-0023`'s attended-path witness, end to end: a real `.saffron/
    policy.yaml` at `base_sha`, a real spec whose `touches` collide with one
    of its literal entries, driven through the real `cli._run_cell` — not a
    refusal reason handed to an assertion. `SA-0021`'s own shape: `DESIGN.md`
    declared in `touches`."""
    repo = _local_origin_with_policy(
        tmp_path, "protected:\n  - DESIGN.md\n  - CONTEXT.md\n"
    )
    args = _namespace(repo, tmp_path)
    args.spec = tmp_path / "SY-9.md"
    args.spec.write_text(
        "---\nid: SY-9\ntitle: Nine\ntype: docs\ntouches: ['DESIGN.md']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    started = False

    def _started(*_a, **_k):
        nonlocal started
        started = True
        raise SystemExit(0)

    monkeypatch.setattr("saffron.task.run_one_cell", _started)
    ledger = Ledger(tmp_path / "l.db")

    result = cli._run_cell(args, ledger, tmp_path / "out")

    assert result == 1
    assert not started  # no cell, no model call
    out = capsys.readouterr().out
    assert "DESIGN.md" in out
    assert "protected" in out
    assert "forbidden" in out
    # No row left behind: the refusal happened before a task ever existed.
    count = ledger._db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 0
    ledger.close()


def _repo_with_spec(
    tmp_path,
    *,
    spec_text,
    dirname="repo",
    extra_specs=None,
    policy_yaml=None,
    markers=None,
):
    """A repo whose `origin` is a local bare clone, cut *after* the spec is
    committed — so the remote's default-branch head, which is what `_queue`
    (like `_run_cell`) exports `.saffron/` from, actually contains it. A
    local-path origin, not a forge remote, so `github_slug` genuinely fails on
    it rather than needing to be faked.

    `policy_yaml` is `None` by default — every caller before `SA-0023` gets a
    repo with no `.saffron/policy.yaml` at all, exactly as before, since
    `_protected_paths` is best-effort about that (`cli.py`).

    `markers` is `{path: spec_id}` — real `saffron:retired-by` markers
    (`SA-0027`) committed at the same sha as the specs, `None` by default so
    every caller before `SA-0027` gets exactly the repo it already had."""
    repo = tmp_path / dirname
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "f.txt").write_text("a\n")
    specs = repo / ".saffron" / "specs"
    specs.mkdir(parents=True)
    (specs / "SY-1.md").write_text(spec_text)
    for name, text in (extra_specs or {}).items():
        (specs / name).write_text(text)
    if policy_yaml is not None:
        (repo / ".saffron" / "policy.yaml").write_text(policy_yaml)
    for path, spec_id in (markers or {}).items():
        marker = repo / path
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"# saffron:retired-by {spec_id}\n")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "first")
    remote = tmp_path / f"{dirname}-remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(repo), str(remote)], check=True)
    _git(repo, "remote", "add", "origin", str(remote))
    if policy_yaml is not None:
        # Same reason as `_local_origin_with_policy`: with the committed
        # and working-copy policies identical, a read of either passes and
        # the export-not-working-copy property has no witness.
        (repo / ".saffron" / "policy.yaml").write_text("protected: []\n")
    return repo


_A_SPEC = (
    "---\nid: SY-1\ntitle: One\ntype: chore\n---\n\n"
    "## Acceptance criteria\n- [ ] it works\n"
)


def test_queue_prints_the_real_scheduler_queue_and_writes_nothing_to_the_ledger(
    tmp_path, capsys
):
    """The queue printed has to come from `saffron/scheduler.py`'s real
    `build_queue` reading real files, not a value the test hands the CLI and
    then asserts back — that defect shipped `SA-0005` green and was caught in
    `SA-0007`'s review. And a repo this ledger has never seen must stay
    unseen: an unseen repo resolves to no `repo_id`, so the reconcile
    `queue` now runs before it scans has nothing to ask about and writes
    nothing. `queue` does write, on a repo the ledger knows."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC)
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "SY-1" in out
    assert "queue: 1 candidate(s)" in out

    ledger = Ledger(home / "ledger.db")
    for table in ("repos", "runs", "tasks"):
        count = ledger._db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count == 0, f"{table} should be empty against an unseen repo"
    ledger.close()


def test_the_attended_run_says_the_protected_check_did_not_run(
    tmp_path, monkeypatch, capsys
):
    """The attended path is the one that spends — an image build and a
    preflight suite follow. A check that could not run must say so before the
    money, which is the whole argument for running it here rather than at the
    plan checkpoint."""
    repo = _local_origin_with_policy(
        tmp_path, "protected: [oh: no: unbalanced\n", dirname="repo-attended-bad"
    )
    args = _namespace(repo, tmp_path)
    args.spec = tmp_path / "SY-9.md"
    args.spec.write_text(
        "---\nid: SY-9\ntitle: Nine\ntype: docs\ntouches: ['DESIGN.md']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    monkeypatch.setattr(
        "saffron.task.run_one_cell",
        lambda *_a, **_k: (_ for _ in ()).throw(SystemExit(0)),
    )
    ledger = Ledger(tmp_path / "l.db")

    with pytest.raises(SystemExit):
        cli._run_cell(args, ledger, tmp_path / "out")

    out = capsys.readouterr().out
    # Unreadable, so nothing was refused — and the operator is told which
    # check did not run rather than being left to read `refusals: 0`.
    assert "policy.yaml at this base_sha could not be read" in out
    assert "this spec was not checked against the protected list" in out
    ledger.close()


def test_a_repo_with_no_saffron_dir_is_absence_and_says_nothing(
    tmp_path, monkeypatch, capsys
):
    """`git archive` fails on an unmatched pathspec, so every repo not yet
    onboarded reaches `_protected_paths_at`'s error handler — the ordinary
    case, not a broken one. Reporting it as an unreadable policy is the same
    absence-as-unreadability defect `_protected_paths` was fixed for, and the
    note would then print on every first run against a new repo."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    monkeypatch.setattr(
        "saffron.task.run_one_cell",
        lambda *_a, **_k: (_ for _ in ()).throw(SystemExit(0)),
    )
    ledger = Ledger(tmp_path / "l.db")

    with pytest.raises(SystemExit):
        cli._run_cell(args, ledger, tmp_path / "out")

    out = capsys.readouterr().out
    assert "could not be read" not in out
    assert "protected list" not in out
    ledger.close()


def test_the_attended_run_does_not_refuse_a_path_its_own_forbidden_bars(
    tmp_path, monkeypatch, capsys
):
    """The false-refusal direction, on the path that has shipped every spec in
    this repository — `_run_cell` never calls `build_queue`, so the gate-0
    witness does not cover it. A `protected` path the spec's own `forbidden`
    already bars is barred twice over (`validate_plan`, and `scope` against
    the diff since `SA-0024`), so refusing here costs a night for nothing."""
    repo = _local_origin_with_policy(
        tmp_path,
        "gates: {}\nprotected: ['DESIGN.md']\nintegrity:\n  test_paths: ['tests/**']\n",
        dirname="repo-attended-forbidden",
    )
    args = _namespace(repo, tmp_path)
    args.spec = tmp_path / "SY-8.md"
    args.spec.write_text(
        "---\nid: SY-8\ntitle: Eight\ntype: docs\ntouches: ['**']\n"
        "forbidden: ['DESIGN.md']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    reached = []
    monkeypatch.setattr(
        "saffron.task.run_one_cell",
        lambda *_a, **_k: (reached.append(True), (_ for _ in ()).throw(SystemExit(0)))[
            0
        ],
    )
    ledger = Ledger(tmp_path / "l.db")

    with pytest.raises(SystemExit):
        cli._run_cell(args, ledger, tmp_path / "out")

    out = capsys.readouterr().out
    assert "refused" not in out, out
    assert reached, "the run was refused before it reached a cell"
    ledger.close()


def test_queue_says_the_protected_check_did_not_run_when_policy_is_unreadable(
    tmp_path, capsys
):
    """A scan that could not read `policy.yaml` must not print what a scan
    that read it and found no collision prints (§5.4) — and it must not claim
    the *other* refusals were the ones that did not run, which is the defect
    this whole gate removes one level up."""
    spec_text = (
        "---\nid: SY-1\ntitle: One\ntype: docs\ntouches: ['DESIGN.md']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    repo = _repo_with_spec(
        tmp_path,
        spec_text=spec_text,
        dirname="repo-badpolicy",
        policy_yaml="protected: [oh: no: unbalanced\n",
    )
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    # This repo's origin is a local bare clone, so no slug resolves and the
    # `gh` note legitimately prints too. The property is per-line: the policy
    # note must carry its own consequence, not borrow the `gh` one.
    policy_line = next(
        line for line in out.splitlines() if "policy.yaml at this base_sha" in line
    )
    assert "no spec was checked against the protected list" in policy_line
    assert "open-pull-request" not in policy_line


def test_queue_says_nothing_when_a_repo_simply_declares_no_policy(tmp_path, capsys):
    """Absent is not unreadable. Every repo not yet onboarded has no
    `policy.yaml`, and that is the ordinary case, not a skipped check."""
    spec_text = (
        "---\nid: SY-1\ntitle: One\ntype: docs\ntouches: ['src/**']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    repo = _repo_with_spec(tmp_path, spec_text=spec_text, dirname="repo-nopolicy")
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    assert "protected list" not in capsys.readouterr().out


def test_queue_refuses_a_spec_whose_touches_match_a_protected_path(tmp_path, capsys):
    """`SA-0023`'s scan-side witness: a real `.saffron/policy.yaml` declaring
    `protected:`, and a real spec whose `touches` collide with one of its
    literal entries, driven through the real `saffron queue` — not a
    refusal reason handed to an assertion."""
    spec_text = (
        "---\nid: SY-1\ntitle: One\ntype: docs\ntouches: ['DESIGN.md']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    repo = _repo_with_spec(
        tmp_path,
        spec_text=spec_text,
        dirname="repo-protected",
        policy_yaml="protected:\n  - DESIGN.md\n  - CONTEXT.md\n",
    )
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "queue: 0 candidate(s)" in out
    assert "refusals: 1" in out
    assert "SY-1.md" in out
    assert "DESIGN.md" in out
    assert "protected" in out
    assert "forbidden" in out


def test_queue_refuses_a_spec_whose_touches_cannot_reach_its_own_marker(
    tmp_path, capsys
):
    """`SA-0027`'s scan-side witness: a real `saffron:retired-by` marker
    committed alongside the spec, and a real spec whose `touches` do not
    cover it, driven through the real `saffron queue`."""
    spec_text = (
        "---\nid: SY-1\ntitle: One\ntype: feature\ntouches: ['saffron/x.py']\n"
        "---\n\n## Acceptance criteria\n- [ ] it works\n"
    )
    repo = _repo_with_spec(
        tmp_path,
        spec_text=spec_text,
        dirname="repo-marker",
        markers={"tests/test_package.py": "SY-1"},
    )
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "queue: 0 candidate(s)" in out
    assert "refusals: 1" in out
    assert "tests/test_package.py" in out
    assert "saffron/x.py" in out


def test_queue_prints_a_dangling_marker_by_its_own_repo_relative_path(tmp_path, capsys):
    """A marker naming a spec id nothing in the specs directory declares gets
    its own line — `SA-0024`'s `done/` rule applied to a marker instead of a
    `depends_on` — and it names a path the export never held, so `_print_queue`
    must not raise trying to make it relative to the export root."""
    repo = _repo_with_spec(
        tmp_path,
        spec_text=_A_SPEC,
        dirname="repo-ghost",
        markers={"saffron/ghost.py": "ZZ-404"},
    )
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    # SY-1 is unrelated to the dangling marker and is still queued.
    assert "queue: 1 candidate(s)" in out
    assert "refusals: 1" in out
    assert "saffron/ghost.py" in out
    assert "ZZ-404" in out


def test_queue_says_which_refusals_did_not_run_when_no_slug_resolves(tmp_path, capsys):
    """A local-path origin has no GitHub slug. The two refusals that need one
    must not silently no-op — an empty refusal list from a scan that could not
    check GitHub must not read the same as a clean one."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-noslug")
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "did not run" in out
    assert "open-pull-request" in out
    assert "touches-overlap" in out


def test_queue_hands_build_queue_a_real_gh_invoking_runner_once_a_slug_resolves(
    tmp_path, monkeypatch
):
    """The CLI, not a test double, has to hand `build_queue` a runner that
    *really* invokes `gh` once a slug resolves — only `github_slug` is faked
    here, exactly as `test_the_base_is_the_remote_default_branch_not_the_checkout`
    fakes it, for the same reason (a local-path origin is not shaped like a
    forge remote). Proof, the same way `test_build_queue_touches_no_network_and_no_cell`
    proves the opposite case in `tests/test_scheduler.py`: `tests/conftest.py`'s
    `no_host_tool_exec` guard raises the moment anything unmarked actually
    execs `gh`, and it fires here — this repo has no `gh` binary to call for
    real, so the guard firing is the only honest way to show the wiring reaches
    it rather than a `gh=` mock that would prove nothing about `cli.py`."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-slug")
    home = tmp_path / "home"
    monkeypatch.setattr("saffron.cli.package_phase.github_slug", lambda _url: "o/r")

    with pytest.raises(HostToolExecInTest):
        cli.main(["--home", str(home), "queue", "--repo", str(repo)])


def test_queue_exits_two_when_the_repo_cannot_be_read(tmp_path):
    """No `origin` remote at all: the same infrastructure failure `_run_cell`
    treats as exit 2, not the slug-unresolved case `queue` tolerates."""
    repo = _repo_with_commit(tmp_path / "repo-no-origin")
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 2


def test_queue_prints_paths_the_operator_can_open(tmp_path, capsys):
    """`build_queue` reads the specs out of a temporary export that is deleted
    before anything is printed, so an absolute path names a file that is
    already gone — and a spec that failed to parse has no id to fall back on,
    which leaves the path as the only thing identifying it."""
    repo = _repo_with_spec(
        tmp_path,
        spec_text=_A_SPEC,
        dirname="repo-paths",
        extra_specs={"SY-3.md": "no frontmatter at all\n"},
    )
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "refusals: 1" in out
    assert ".saffron/specs/SY-3.md:" in out
    assert ".saffron/specs/SY-1.md" in out
    assert tempfile.gettempdir() not in out


def test_queue_reads_the_specs_at_base_sha_not_the_working_copy(tmp_path, capsys):
    """The fixture commits its spec before cutting the remote, so a `_queue`
    that read `repo/.saffron/specs` straight from the working copy would pass
    every other test here. A spec committed locally and never pushed is the
    witness: `base_sha` is the remote's default-branch head, so it must not
    reach the queue."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-basesha")
    (repo / ".saffron" / "specs" / "SY-2.md").write_text(
        _A_SPEC.replace("SY-1", "SY-2")
    )
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "unpushed")
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "queue: 1 candidate(s)" in out
    assert "SY-1" in out
    assert "SY-2" not in out


def _seed_repo(ledger, origin, *, name="repo"):
    return ledger.upsert_repo(name, origin, "/m.git", policy_sha="p" * 64)


def _seed_task(
    ledger, repo_id, *, spec_id, state, pr_url=None, spec_sha="s" * 40, branch=None
):
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id,
        spec_id=spec_id,
        spec_sha=spec_sha,
        branch=branch or f"saffron/{spec_id}",
    )
    ledger.set_task_state(task_id, state)
    if pr_url is not None:
        ledger._db.execute(
            "UPDATE tasks SET pr_url = ? WHERE task_id = ?", (pr_url, task_id)
        )
        ledger._db.commit()
    return task_id


def _task_state(home, task_id):
    ledger = Ledger(home / "ledger.db")
    row = ledger._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    ledger.close()
    return row["state"]


def _fake_gh_says_merged(argv):
    return subprocess.CompletedProcess(
        argv, 0, '{"state": "MERGED", "reviewDecision": null}', ""
    )


def _fake_gh_says_changes_requested(argv):
    return subprocess.CompletedProcess(
        argv, 0, '{"state": "OPEN", "reviewDecision": "CHANGES_REQUESTED"}', ""
    )


def _no_gh(_argv):
    raise FileNotFoundError("gh")


@pytest.mark.parametrize(
    "fake_gh, expect_state, expect_substring",
    [
        (_fake_gh_says_merged, "MERGED", "MERGED"),
        (_no_gh, "READY_FOR_REVIEW", "could not be run"),
    ],
    ids=["gh-answers", "gh-missing"],
)
def test_reconcile_writes_what_gh_says_or_withholds_when_it_cannot_answer(
    tmp_path, monkeypatch, capsys, fake_gh, expect_state, expect_substring
):
    """`saffron reconcile --repo .`, end to end: seed the ledger the way a
    prior night would have, drive the real command through `cli.main`, and
    check the row rather than handing `set_task_state` the value under test.
    A `gh` that cannot run leaves it exactly as it found it."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-reconcile")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    task_id = _seed_task(
        ledger,
        repo_id,
        spec_id="SY-9",
        state="READY_FOR_REVIEW",
        pr_url="https://github.com/o/r/pull/9",
    )
    ledger.close()
    monkeypatch.setattr("saffron.cli.run_gh", fake_gh)

    assert cli.main(["--home", str(home), "reconcile", "--repo", str(repo)]) == 0

    assert expect_substring in capsys.readouterr().out
    assert _task_state(home, task_id) == expect_state


def test_watch_reads_the_batch_tree_the_cli_already_computes(tmp_path, monkeypatch):
    """The task directory `watch` reads is `out_dir / task` — the same
    batch-tree root `main` already computes from `--home` for every other
    subcommand, never a second reading of it. `follow` itself is stubbed:
    this witness is about which path reaches it, not about following."""
    seen = {}

    def fake_follow(task_dir, *, verbose=False, whole_log=False, interval=1.0):
        seen["task_dir"] = task_dir
        return iter(())

    monkeypatch.setattr(cli, "follow", fake_follow)

    assert cli.main(["--home", str(tmp_path), "watch", "SY-1"]) == 0

    assert seen["task_dir"] == tmp_path / "batches" / "v0" / "SY-1"


def test_watch_exits_one_and_names_the_directory_for_an_unknown_task(tmp_path, capsys):
    """A mistyped spec id exits 1, and the message says where it looked.

    Driven through the command rather than through `follow`, because the whole
    content of the decision is the exit code an operator sees. Delete the
    handler in `_watch` and `UnknownTask` reaches `main`'s catch-all, which
    returns 2 — infrastructure failed — for what is a typo. A module-level
    test of the exception leaves that edit invisible.
    """
    assert cli.main(["--home", str(tmp_path), "watch", "SA-9999"]) == 1

    printed = capsys.readouterr().out
    assert str(tmp_path / "batches" / "v0" / "SA-9999") in printed


def test_watch_passes_its_flags_through_to_the_follower(tmp_path, monkeypatch):
    """Both flags reach `follow`. Without this, dropping `verbose=args.all`
    and `interval=args.interval` from the call leaves every other test in the
    suite green — the flags parse, print in `--help`, and change nothing,
    which is a CLI wearing the same defect item 18 found in a dataclass.
    """
    seen = {}

    def fake_follow(task_dir, *, verbose=False, whole_log=False, interval=1.0):
        seen.update(verbose=verbose, interval=interval)
        return iter(())

    monkeypatch.setattr(cli, "follow", fake_follow)

    assert (
        cli.main(
            ["--home", str(tmp_path), "watch", "SY-1", "--all", "--interval", "0.25"]
        )
        == 0
    )

    assert seen == {"verbose": True, "interval": 0.25}


def test_watch_passes_the_whole_log_flag_through_to_the_follower(tmp_path, monkeypatch):
    """`--whole-log` reaches `follow` as `whole_log=True`; its absence is
    `whole_log=False`, never omitted — `--all` already means something else,
    so this is a second flag, not a second meaning for the first."""
    seen = {}

    # No default for `whole_log`: a `_watch` that omitted it would raise here.
    def fake_follow(task_dir, *, verbose=False, whole_log, interval=1.0):
        seen["whole_log"] = whole_log
        return iter(())

    monkeypatch.setattr(cli, "follow", fake_follow)

    assert cli.main(["--home", str(tmp_path), "watch", "SY-1", "--whole-log"]) == 0
    assert seen["whole_log"] is True

    assert cli.main(["--home", str(tmp_path), "watch", "SY-1"]) == 0
    assert seen["whole_log"] is False


def test_watch_no_follow_hands_the_follower_a_poll_that_stops(tmp_path, monkeypatch):
    """`--no-follow` reaches `follow` as the poll that ends it, and without
    the flag nothing is passed at all — the real default stays bound in
    `follow`'s own signature rather than being respelled here.

    Stubbed deliberately, beside the end-to-end witness below: unwire this
    and that one does not fail, it *hangs*, following a finished log for
    ever. This says which line broke.
    """
    from saffron import watch

    seen = {}

    def fake_follow(
        task_dir, *, verbose=False, whole_log=False, interval=1.0, sleep=None
    ):
        seen["sleep"] = sleep
        return iter(())

    monkeypatch.setattr(cli, "follow", fake_follow)

    assert cli.main(["--home", str(tmp_path), "watch", "SY-1", "--no-follow"]) == 0
    assert seen["sleep"] is watch.once

    assert cli.main(["--home", str(tmp_path), "watch", "SY-1"]) == 0
    assert seen["sleep"] is None


def test_watch_prints_the_lines_the_follower_yields(tmp_path, capsys):
    """The rendered lines actually reach stdout.

    Nothing else asserts this: both witnesses above stub `follow` with an
    empty iterator, so `print(line)` in `_watch` can be deleted outright with
    the whole suite still green — the one thing an operator runs this command
    for, untested. Driven end to end through the real `follow` and the real
    `EventLog`, with `--no-follow` for a finite run.
    """
    from saffron.events import EventLog, Teardown, describe

    task_dir = tmp_path / "batches" / "v0" / "SY-1"
    log = EventLog(task_dir)
    events = [
        Teardown(timestamp=1.0, spec_id="SY-1", step="start", ok=True),
        Teardown(timestamp=2.0, spec_id="SY-1", step="network", ok=True),
    ]
    for event in events:
        log.append(event)

    assert cli.main(["--home", str(tmp_path), "watch", "SY-1", "--no-follow"]) == 0

    printed = capsys.readouterr().out.splitlines()
    assert printed == [describe(event) for event in events]


@pytest.mark.parametrize("interval", ["0", "-1"])
def test_watch_refuses_a_poll_interval_that_never_waits(tmp_path, interval, capsys):
    """A poll interval that is not a wait dies at parse time, with a usage
    message and before a single line is printed.

    `0` busy-loops re-reading the log at full CPU; a negative reaches
    `time.sleep`, which raises only *after* the whole log has been rendered —
    and `main`'s catch-all turns that into exit `2`, infrastructure failed,
    for what is a mistyped flag. Argparse's own usage exit is the same one
    every other malformed argv already gets.
    """
    with pytest.raises(SystemExit):
        cli.main(["--home", str(tmp_path), "watch", "SY-1", "--interval", interval])

    assert "--interval" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["queue", "reconcile"])
def test_an_in_flight_task_survives_being_looked_at(tmp_path, command):
    """`ORPHANED` is in `scheduler.REQUEUE_STATES`, so a row stamped while
    its cell is alive is handed back out as resumable — a second cell on the
    same branch. Driven through the CLI, not the stamping function, because
    which command an operator runs is the property that matters."""
    repo = _repo_with_spec(
        tmp_path, spec_text=_A_SPEC, dirname=f"repo-inflight-{command}"
    )
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    task_id = _seed_task(ledger, repo_id, spec_id="SY-11", state="IMPLEMENTING")
    ledger.close()

    assert cli.main(["--home", str(home), command, "--repo", str(repo)]) == 0

    assert _task_state(home, task_id) == "IMPLEMENTING"


def test_queue_reconciles_before_it_scans_so_the_refusal_gate_sees_current_state(
    tmp_path, monkeypatch, capsys
):
    """`queue` must see the state that is true *today*, not whatever PACKAGE
    wrote once."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-queue-reconciles")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    _seed_task(
        ledger,
        repo_id,
        spec_id="SY-1",
        state="READY_FOR_REVIEW",
        pr_url="https://github.com/o/r/pull/11",
        spec_sha=hashlib.sha256(_A_SPEC.encode()).hexdigest(),
    )
    ledger.close()
    monkeypatch.setattr("saffron.cli.run_gh", _fake_gh_says_merged)

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "MERGED" in out
    # SY-1's task just became MERGED, one of `scheduler.DONE_STATES`.
    assert "queue: 0 candidate(s)" in out


def _dep_spec(spec_id, depends_on=None):
    dep = f"depends_on:\n  - {depends_on}\n" if depends_on else ""
    return (
        f"---\nid: {spec_id}\ntitle: t\ntype: chore\n{dep}---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )


_ID = ("-c", "user.email=t@t", "-c", "user.name=T")


def _pushed_branch(repo, branch, filename):
    """A commit on its own branch, pushed. Returns that commit's sha."""
    _git(repo, "checkout", "-q", "-b", branch)
    (repo / filename).write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, *_ID, "commit", "-qm", branch)
    sha = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "-q", "origin", branch)
    return sha


def test_queue_admits_a_child_whose_exhausted_parent_merged_by_hand(tmp_path, capsys):
    """`SA-0131`: a parent's task ends `EXHAUSTED`, and the operator opens a
    pull request from its branch by hand and merges it with a merge commit.
    The child is admitted anyway, because its parent's recorded push reached
    the default branch, whatever the ledger row still says."""
    sy3_text, sy5_text = _dep_spec("SY-3"), _dep_spec("SY-5")
    repo = _repo_with_spec(
        tmp_path,
        spec_text=_A_SPEC,
        dirname="repo-pushed-landed",
        extra_specs={
            "SY-2.md": _dep_spec("SY-2", "SY-1"),
            "SY-3.md": sy3_text,
            "SY-4.md": _dep_spec("SY-4", "SY-3"),
            "SY-5.md": sy5_text,
            "SY-6.md": _dep_spec("SY-6", "SY-5"),
        },
    )
    default_name = _git(repo, "symbolic-ref", "--short", "HEAD")
    pre_merge_head = _git(repo, "rev-parse", "HEAD")
    remote = tmp_path / "repo-pushed-landed-remote.git"

    # SY-1's branch, merged by hand on a second clone with a merge commit.
    parent1_sha = _pushed_branch(repo, "saffron/SY-1", "p1.txt")
    _git(repo, "checkout", "-q", default_name)
    merge_clone = tmp_path / "repo-pushed-landed-merge-clone"
    subprocess.run(["git", "clone", "-q", str(remote), str(merge_clone)], check=True)
    _git(merge_clone, "fetch", "-q", "origin", "saffron/SY-1")
    _git(merge_clone, *_ID, "merge", "--no-ff", "-q", "-m", "m", "origin/saffron/SY-1")
    merge_sha = _git(merge_clone, "rev-parse", "HEAD")
    _git(merge_clone, "push", "-q", "origin", default_name)

    # SY-3's branch, pushed and never merged. SY-5's pushed sha never exists.
    parent2_sha = _pushed_branch(repo, "saffron/SY-3", "p2.txt")
    _git(repo, "checkout", "-q", default_name)
    parent3_sha = "b" * 40

    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    url = package.real_remote(repo)
    repo_id = _seed_repo(ledger, url)
    for spec_id, text, pushed_sha in (
        ("SY-1", _A_SPEC, parent1_sha),
        ("SY-3", sy3_text, parent2_sha),
        ("SY-5", sy5_text, parent3_sha),
    ):
        task_id = _seed_task(
            ledger,
            repo_id,
            spec_id=spec_id,
            state="EXHAUSTED",
            spec_sha=hashlib.sha256(text.encode()).hexdigest(),
        )
        ledger.record_push(task_id, pushed_sha)
    ledger.close()

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert out.index("SY-2") < out.index("refusals:")
    sy4_reason = next(line for line in out.splitlines() if "SY-4.md:" in line)
    assert "SY-3" in sy4_reason and "EXHAUSTED" in sy4_reason
    sy6_reason = next(line for line in out.splitlines() if "SY-6.md:" in line)
    assert "SY-5" in sy6_reason and "EXHAUSTED" in sy6_reason

    # The pinned path, driven on either side of the merge.
    ledger = Ledger(home / "ledger.db")
    mirror = cli._mirror_path(repo, home)
    assert _git(mirror, "rev-parse", f"refs/heads/{default_name}") == merge_sha
    assert _git(mirror, "rev-parse", "HEAD") == merge_sha
    assert _git(mirror, "rev-parse", "FETCH_HEAD") == merge_sha

    ahead = task.PinnedBase(mirror=mirror, url=url, base_sha=pre_merge_head)
    resolved_ahead = cli._resolve_queue(
        repo, home, ledger, stamp_orphaned=False, pinned=ahead
    )
    assert resolved_ahead.candidates == []
    ahead_reason = next(
        r.reason for r in resolved_ahead.refusals if r.path.name == "SY-2.md"
    )
    assert "SY-1" in ahead_reason and "EXHAUSTED" in ahead_reason

    _git(mirror, "update-ref", f"refs/heads/{default_name}", pre_merge_head)
    behind = task.PinnedBase(mirror=mirror, url=url, base_sha=merge_sha)
    resolved_behind = cli._resolve_queue(
        repo, home, ledger, stamp_orphaned=False, pinned=behind
    )
    assert [c.spec.id for c in resolved_behind.candidates] == ["SY-2"]
    assert {r.path.name for r in resolved_behind.refusals} == {"SY-4.md", "SY-6.md"}
    ledger.close()

    with pytest.raises(cli.git_mirror.GitError):
        cli._pushed_landed(tmp_path / "no-such-mirror", merge_sha, parent1_sha)
    with pytest.raises(cli.git_mirror.GitError):
        cli._pushed_landed(mirror, "c" * 40, parent1_sha)
    assert cli._pushed_landed(mirror, merge_sha, "b" * 40) is False


def test_queue_schedules_a_task_reconcile_moved_into_a_requeue_state(
    tmp_path, monkeypatch, capsys
):
    """The case that proves the wiring rather than merely reaching it.

    A seeded `READY_FOR_REVIEW` is already in `DONE_STATES`, so a queue of
    zero holds whether reconcile ran or not — the test above witnesses the
    call, not its effect. `CHANGES_REQUESTED` is in `REQUEUE_STATES`, so a
    task reconcile moves there has to *appear* as a candidate it was not.
    """
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-queue-requeues")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    _seed_task(
        ledger,
        repo_id,
        spec_id="SY-1",
        state="READY_FOR_REVIEW",
        pr_url="https://github.com/o/r/pull/12",
        spec_sha=hashlib.sha256(_A_SPEC.encode()).hexdigest(),
    )
    ledger.close()

    # Unasked, the same spec is filtered out as done — the before half.
    monkeypatch.setattr("saffron.cli.run_gh", _no_gh)
    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0
    assert "queue: 0 candidate(s)" in capsys.readouterr().out

    monkeypatch.setattr("saffron.cli.run_gh", _fake_gh_says_changes_requested)
    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "CHANGES_REQUESTED" in out
    assert "queue: 1 candidate(s)" in out
    assert "SY-1" in out


def test_queue_says_the_refusals_did_not_run_when_gh_is_not_installed(
    tmp_path, monkeypatch, capsys
):
    """A machine with no `gh` binary must not turn a readable repo into exit 2.
    And `_open_prs` treats a `gh` that failed as "nothing found" by design, so
    without the guard the two GitHub refusals go quiet exactly the way an
    unresolved slug would — with nothing on the output saying so."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-nogh")
    home = tmp_path / "home"
    monkeypatch.setattr("saffron.cli.package_phase.github_slug", lambda _url: "o/r")

    def _no_gh(_argv):
        raise FileNotFoundError("gh")

    monkeypatch.setattr("saffron.cli.run_gh", _no_gh)

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert "gh could not be run" in out
    assert "did not run" in out


def test_resolving_a_queue_is_one_function_over_the_pinned_base(tmp_path, monkeypatch):
    """`_resolve_queue` does what `_queue` did inline, and in the same order:
    the mirror, the pinned base, the reconcile, the slug, the export, and the
    scan over that export — never the working copy, which is what makes an
    unpushed spec a draft rather than tonight's work."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-resolve-order")
    # Committed, never pushed — the pinned-base witness. A `_resolve_queue`
    # that scanned the working copy would see this too.
    (repo / ".saffron" / "specs" / "SY-2.md").write_text(
        _A_SPEC.replace("SY-1", "SY-2")
    )
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "unpushed")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    # A task at a spec id the queue's own directory need not carry — reconcile
    # scans every row in the repo, not just this scan's candidates, so this is
    # a clean witness that reconcile ran without disturbing SY-1's own status.
    task_id = _seed_task(
        ledger,
        repo_id,
        spec_id="SY-9",
        state="READY_FOR_REVIEW",
        pr_url="https://github.com/o/r/pull/1",
    )

    order = []
    real_ensure = cli.git_mirror.ensure_mirror
    real_fetch = cli.package_phase.fetch_default_branch
    real_reconcile = cli.reconcile
    real_slug = cli.package_phase.github_slug
    real_export = cli.git_mirror.export_saffron_dir
    real_build = cli.build_queue

    def _ensure(*a, **k):
        order.append("mirror")
        return real_ensure(*a, **k)

    def _fetch(*a, **k):
        order.append("base")
        return real_fetch(*a, **k)

    def _reconcile(*a, **k):
        order.append("reconcile")
        return real_reconcile(*a, **k)

    def _slug(*a, **k):
        order.append("slug")
        return real_slug(*a, **k)

    def _export(*a, **k):
        order.append("export")
        return real_export(*a, **k)

    def _build(*a, **k):
        order.append("scan")
        return real_build(*a, **k)

    monkeypatch.setattr(cli.git_mirror, "ensure_mirror", _ensure)
    monkeypatch.setattr(cli.package_phase, "fetch_default_branch", _fetch)
    monkeypatch.setattr(cli, "reconcile", _reconcile)
    monkeypatch.setattr(cli.package_phase, "github_slug", _slug)
    monkeypatch.setattr(cli.git_mirror, "export_saffron_dir", _export)
    monkeypatch.setattr(cli, "build_queue", _build)
    monkeypatch.setattr(cli, "run_gh", _fake_gh_says_merged)

    resolved = cli._resolve_queue(repo, home, ledger, stamp_orphaned=False)

    assert order == ["mirror", "base", "reconcile", "slug", "export", "scan"]
    assert resolved.repo_id == repo_id
    assert [c.spec.id for c in resolved.candidates] == ["SY-1"]
    assert resolved.reconciled.merged == [task_id]
    # The local origin here has no GitHub slug to resolve.
    assert resolved.repo_slug is None
    ledger.close()


def test_a_resolution_given_a_pinned_base_does_not_derive_one(tmp_path, monkeypatch):
    """Handed the mirror, the origin and the base a night's readiness already
    found, `_resolve_queue` uses them and reaches for none of the three
    functions that would derive them again — the fix itself, asserted by
    counting rather than by the returned fields happening to match."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-pinned-given")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")

    # Derived once, for real, before the counters go on — the answer a
    # night's readiness would already have handed in.
    digest = hashlib.sha256(str(repo.resolve()).encode()).hexdigest()[:12]
    mirror = cli.git_mirror.ensure_mirror(
        repo, home / "mirrors" / f"{repo.name}-{digest}.git"
    )
    url = cli.package_phase.real_remote(repo)
    _, base_sha = cli.package_phase.fetch_default_branch(mirror, url)

    counts = {"mirror": 0, "remote": 0, "fetch": 0}

    def _ensure(*a, **k):
        counts["mirror"] += 1
        return mirror

    def _remote(*a, **k):
        counts["remote"] += 1
        return url

    def _fetch(*a, **k):
        counts["fetch"] += 1
        return ("main", base_sha)

    monkeypatch.setattr(cli.git_mirror, "ensure_mirror", _ensure)
    monkeypatch.setattr(cli.package_phase, "real_remote", _remote)
    monkeypatch.setattr(cli.package_phase, "fetch_default_branch", _fetch)

    resolved = cli._resolve_queue(
        repo,
        home,
        ledger,
        stamp_orphaned=False,
        pinned=task.PinnedBase(mirror=mirror, url=url, base_sha=base_sha),
    )

    assert counts == {"mirror": 0, "remote": 0, "fetch": 0}
    # A sanity check that the resolution still ran the scan over the pinned
    # tree, not the main assertion above.
    assert [c.spec.id for c in resolved.candidates] == ["SY-1"]
    ledger.close()


def test_a_resolution_given_no_pinned_base_still_derives_its_own(tmp_path, monkeypatch):
    """Handed nothing, `_resolve_queue` derives the base itself exactly as it
    does today — `saffron queue`'s own path, and the reason the argument is
    optional rather than required: the default is the full derivation, not a
    stub that returns something empty."""
    # `pinned` exists and defaults to `None` — the shape this whole witness is
    # about. A `_resolve_queue` with no such parameter at all (as it read
    # before this change) has nothing here to be optional about.
    assert inspect.signature(cli._resolve_queue).parameters["pinned"].default is None

    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-pinned-none")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")

    real_ensure = cli.git_mirror.ensure_mirror
    real_remote = cli.package_phase.real_remote
    real_fetch = cli.package_phase.fetch_default_branch
    counts = {"mirror": 0, "remote": 0, "fetch": 0}

    def _ensure(*a, **k):
        counts["mirror"] += 1
        return real_ensure(*a, **k)

    def _remote(*a, **k):
        counts["remote"] += 1
        return real_remote(*a, **k)

    def _fetch(*a, **k):
        counts["fetch"] += 1
        return real_fetch(*a, **k)

    monkeypatch.setattr(cli.git_mirror, "ensure_mirror", _ensure)
    monkeypatch.setattr(cli.package_phase, "real_remote", _remote)
    monkeypatch.setattr(cli.package_phase, "fetch_default_branch", _fetch)

    resolved = cli._resolve_queue(repo, home, ledger, stamp_orphaned=False)

    assert counts == {"mirror": 1, "remote": 1, "fetch": 1}
    assert [c.spec.id for c in resolved.candidates] == ["SY-1"]
    ledger.close()


def test_the_stamping_premise_is_a_required_argument(tmp_path):
    """A default here would decide the premise for whichever caller forgets
    to think about it — so there is no default to fall back on."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-stamp-required")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")

    # `getattr` with a name built at runtime, not a direct call: a static
    # type checker would catch a missing required keyword argument at the
    # call site, but the whole point of this witness is that the *runtime*
    # enforces it too — there is no default `stamp_orphaned` value for a
    # caller to fall back on.
    attr = "_resolve" + "_queue"
    resolve_queue = getattr(cli, attr)
    with pytest.raises(TypeError):
        resolve_queue(repo, home, ledger)  # no stamp_orphaned given

    ledger.close()


def test_told_to_stamp_it_orphans_an_in_flight_task_and_re_queues_it(tmp_path):
    """Told to stamp, it stamps: a task left in an in-flight state is
    recorded orphaned and re-queues by the ordinary rule (`ORPHANED` is in
    `scheduler.REQUEUE_STATES`)."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-stamp-yes")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    task_id = _seed_task(
        ledger,
        repo_id,
        spec_id="SY-1",
        state="IMPLEMENTING",
        spec_sha=hashlib.sha256(_A_SPEC.encode()).hexdigest(),
    )

    resolved = cli._resolve_queue(repo, home, ledger, stamp_orphaned=True)

    row = ledger._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    assert row["state"] == "ORPHANED"
    assert task_id in resolved.reconciled.orphaned
    assert len(resolved.candidates) == 1
    assert resolved.candidates[0].task_id == task_id
    ledger.close()


def test_told_not_to_stamp_it_leaves_an_in_flight_task_alone(tmp_path):
    """Told not to stamp, it leaves an in-flight task exactly as it found
    it — the existing behaviour of the attended command, and the reason the
    argument exists rather than a constant."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-stamp-no")
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    task_id = _seed_task(
        ledger,
        repo_id,
        spec_id="SY-1",
        state="IMPLEMENTING",
        spec_sha=hashlib.sha256(_A_SPEC.encode()).hexdigest(),
    )

    resolved = cli._resolve_queue(repo, home, ledger, stamp_orphaned=False)

    row = ledger._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    assert row["state"] == "IMPLEMENTING"
    assert resolved.reconciled.orphaned == []
    assert len(resolved.candidates) == 1
    assert resolved.candidates[0].task_id is None
    ledger.close()


def _source_calls(fn, name, *, keyword=None, value=None, present=False):
    """Whether `fn`'s body contains a call to `name` — and, if a `keyword` is
    given, a literal keyword argument matching `value` (in any matching call).

    `present=True` asks a different question: is the keyword passed *at all*,
    whatever the node. The `value` form matches only an `ast.Constant`, so
    `f(pinned=None)` is seen and `f(pinned=derived)` is not — which inverts
    the usual intent, since a variable is exactly what a regression would
    pass. Use `present` to assert a call site does not route through an
    argument; use `value` to assert which literal it routes with.

    AST over `inspect.getsource`, not a substring search — a comment or a
    docstring merely naming `name` must not satisfy this — and not a call
    into the real function either: this is a structural check that a
    *caller* still routes through the named function, precisely so that
    reverting that routing (and nothing else) makes it false. This file's own
    `test_no_signature_in_the_package_still_takes_a_watch` is the precedent
    for reading source this way rather than importing and calling it."""
    tree = ast.parse(inspect.getsource(fn))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if called != name:
            continue
        if keyword is None:
            return True
        for kw in node.keywords:
            if kw.arg != keyword:
                continue
            if present:
                return True
            if isinstance(kw.value, ast.Constant) and kw.value.value == value:
                return True
    return False


def _queue_calls(name, *, keyword=None, value=None, present=False):
    return _source_calls(
        cli._queue, name, keyword=keyword, value=value, present=present
    )


def test_the_printed_queue_is_unchanged_by_the_extraction(tmp_path, capsys):
    """The attended command prints what it printed before — the candidates,
    the refusals, the reconcile summary, and the two lines that say a slug or
    a policy could not be read — asserted against the current output rather
    than against the fact that output happened. And it prints it by way of
    the extraction, not a second, inline copy of the same sequence — the
    defect a copy would eventually drift into."""
    repo = _repo_with_spec(
        tmp_path,
        spec_text=_A_SPEC,
        dirname="repo-unchanged-output",
        extra_specs={"SY-3.md": "no frontmatter at all\n"},
    )
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert out == (
        "reconcile: nothing moved\n"
        "queue: 1 candidate(s)\n"
        "  SY-1       priority=3  .saffron/specs/SY-1.md\n"
        "refusals: 1\n"
        "  .saffron/specs/SY-3.md: spec has no YAML frontmatter block\n"
        "note: no GitHub slug could be read from the remote — the "
        "open-pull-request and touches-overlap refusals did not run, so the "
        "refusal list above is incomplete\n"
    )
    assert _queue_calls("_resolve_queue"), (
        "the printed queue must come from `_resolve_queue`, not a second "
        "copy of its sequence"
    )


def test_the_printed_queue_is_unchanged_by_sharing_the_base(tmp_path, capsys):
    """`saffron queue` prints exactly what it printed before — it is the
    caller that gains nothing from sharing the pinned base with `saffron
    batch`, and must lose nothing to it either. `_queue` never has a pinned
    base to offer, so this is the same full derivation, producing the same
    output, byte for byte."""
    # The sharing mechanism exists — `_resolve_queue` now has a `pinned`
    # parameter to *not* use — and `_queue` still never reaches for it.
    #
    # `present=`, not `value=`: the literal form only sees an `ast.Constant`,
    # so it caught the harmless `pinned=None` and missed `pinned=derived`,
    # which is the regression this line is here for. Measured — a `_queue`
    # that derived its own base and passed it down left this assertion green
    # and the output byte-identical.
    assert inspect.signature(cli._resolve_queue).parameters["pinned"].default is None
    assert not _queue_calls("_resolve_queue", keyword="pinned", present=True)

    repo = _repo_with_spec(
        tmp_path,
        spec_text=_A_SPEC,
        dirname="repo-unchanged-by-sharing",
        extra_specs={"SY-3.md": "no frontmatter at all\n"},
    )
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    out = capsys.readouterr().out
    assert out == (
        "reconcile: nothing moved\n"
        "queue: 1 candidate(s)\n"
        "  SY-1       priority=3  .saffron/specs/SY-1.md\n"
        "refusals: 1\n"
        "  .saffron/specs/SY-3.md: spec has no YAML frontmatter block\n"
        "note: no GitHub slug could be read from the remote — the "
        "open-pull-request and touches-overlap refusals did not run, so the "
        "refusal list above is incomplete\n"
    )

    # A real `depends_on` edge, where the stack order (`SA-0142`) admits
    # both specs. This checks that `--stack` truly defaults to `False`.
    parent = _dep_spec("SY-5")
    child = _dep_spec("SY-6", "SY-5")
    stack_default_repo = _repo_with_spec(
        tmp_path,
        spec_text=parent,
        dirname="repo-unchanged-by-sharing-stack-default",
        extra_specs={"SY-6.md": child},
    )
    stack_default_home = tmp_path / "home-stack-default"

    assert (
        cli.main(
            [
                "--home",
                str(stack_default_home),
                "queue",
                "--repo",
                str(stack_default_repo),
            ]
        )
        == 0
    )

    without_stack = capsys.readouterr().out
    assert "queue: 1 candidate(s)" in without_stack
    admitted = without_stack.split("refusals:")[0]
    assert "SY-5" in admitted
    assert "SY-6" not in admitted


def test_queue_stack_prints_the_stack_order(tmp_path, capsys):
    """`saffron queue --stack` prints `build_queue`'s stack order
    (`SA-0142`): SY-1 depends on SY-2, so it runs after SY-2 although its
    own priority is higher. SY-3 depends on SY-9, which no spec here
    declares, and stays refused either way. Without `--stack` the same repo
    admits SY-2 alone and refuses SY-1, since no task recorded it merged."""
    sy2 = _dep_spec("SY-2")
    sy1 = (
        "---\nid: SY-1\ntitle: t\ntype: chore\npriority: 1\n"
        "depends_on:\n  - SY-2\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    sy3 = _dep_spec("SY-3", "SY-9")
    repo = _repo_with_spec(
        tmp_path,
        spec_text=sy1,
        dirname="repo-queue-stack",
        extra_specs={"SY-2.md": sy2, "SY-3.md": sy3},
    )
    home = tmp_path / "home"

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo), "--stack"]) == 0

    stacked = capsys.readouterr().out
    assert "queue: 2 candidate(s)" in stacked
    ordered = [line for line in stacked.splitlines() if line.startswith("  SY-")]
    assert [line.split()[0] for line in ordered] == ["SY-2", "SY-1"]
    assert any(
        "SY-3.md" in line and "SY-9" in line
        for line in stacked.splitlines()
        if line.startswith("  ")
    )

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    plain = capsys.readouterr().out
    assert "queue: 1 candidate(s)" in plain
    plain_candidates = [line for line in plain.splitlines() if line.startswith("  SY-")]
    assert [line.split()[0] for line in plain_candidates] == ["SY-2"]
    assert any(
        "SY-1.md" in line and "SY-2" in line
        for line in plain.splitlines()
        if line.startswith("  ")
    )


def test_looking_at_the_queue_still_never_stamps_a_corpse(tmp_path):
    """The existing guarantee, re-asserted at the level where it could
    regress: the extraction is what put a stamping switch within reach of
    this path for the first time, and `queue` must still never flip it —
    which means passing `stamp_orphaned=False` at the call site, not relying
    on a default that does not exist."""
    repo = _repo_with_spec(
        tmp_path, spec_text=_A_SPEC, dirname="repo-queue-never-stamps"
    )
    home = tmp_path / "home"
    home.mkdir()
    ledger = Ledger(home / "ledger.db")
    repo_id = _seed_repo(ledger, package.real_remote(repo))
    task_id = _seed_task(ledger, repo_id, spec_id="SY-1", state="IMPLEMENTING")
    ledger.close()

    assert cli.main(["--home", str(home), "queue", "--repo", str(repo)]) == 0

    assert _task_state(home, task_id) == "IMPLEMENTING"
    assert _queue_calls("_resolve_queue", keyword="stamp_orphaned", value=False), (
        "`saffron queue` must pass `stamp_orphaned=False` explicitly — the "
        "switch the extraction put within `_queue`'s reach"
    )


def test_the_plan_checkpoint_still_rejects_what_the_refusal_could_not_decide(
    tmp_path,
):
    """`SA-0023`'s fifth acceptance criterion: the plan checkpoint's own
    protected-path rejection stays exactly as it is, and it is still the
    backstop for the case `protected_touch_refusal` deliberately leaves
    undecided (its own `ponytail:`) — a `protected` entry that is itself a
    glob. `.saffron/**` is this repo's own such entry."""
    from saffron.agents.artifacts import PlanRejected, validate_plan
    from saffron.scheduler import protected_touch_refusal

    touches = [".saffron/**"]
    protected = [".saffron/**"]

    # The refusal cannot decide a glob against a glob — this is the gap the
    # plan checkpoint exists to close.
    assert protected_touch_refusal(touches, protected, []) is None

    raw = (
        "<output>"
        + json.dumps(
            {
                "understanding": "u",
                "approach": "a",
                "files_to_change": [".saffron/policy.yaml"],
                "test_strategy": "t",
                "risks": [],
                "blocking_questions": [],
                "estimated_lines": 5,
            }
        )
        + "</output>"
    )

    with pytest.raises(PlanRejected, match="protected"):
        validate_plan(
            raw, touches=touches, forbidden=[], protected=protected, spec_type="docs"
        )


def test_an_orphan_only_resolution_names_the_rows_it_stamped(capsys):
    """`orphaned` counted toward "something moved" — suppressing the "nothing
    moved" line — while having no bucket of its own, so a resolution that only
    orphaned printed nothing whatsoever. `ReconcileResult`'s own docstring
    promises "task ids, not bare counts, so an operator can trace exactly
    which row moved and why", and this was the one bucket that did not.

    `saffron queue` never orphans, so the only caller that reaches this line
    is the unattended night — the one with nobody watching it happen."""
    cli._print_reconcile_summary(ReconcileResult(orphaned=[7, 9]))

    printed = capsys.readouterr().out
    assert "reconcile: task 7 → ORPHANED" in printed
    assert "reconcile: task 9 → ORPHANED" in printed
    assert "nothing moved" not in printed


def test_a_moved_head_is_named_with_both_shas(capsys):
    """Item 97: the line names the task and both commits, so an operator can
    `git log packaged..head` the commits no gate judged — and it is not
    followed by "nothing moved", which would read as nothing to look at."""
    cli._print_reconcile_summary(
        ReconcileResult(head_moved=[HeadMoved(7, "a" * 40, "b" * 40)])
    )

    printed = capsys.readouterr().out
    assert "reconcile: task 7" in printed
    assert "aaaaaaaaaaaa..bbbbbbbbbbbb" in printed
    assert "nothing moved" not in printed


def test_a_resolution_that_changed_nothing_still_says_so(capsys):
    """The other half: silence must not read as "there was nothing to ask
    about"."""
    cli._print_reconcile_summary(ReconcileResult())

    assert "reconcile: nothing moved" in capsys.readouterr().out


def _readiness_passes(monkeypatch):
    """Readiness now runs *before* the scan (§4.4 step 1 ahead of step 4), so
    a test that fakes `_resolve_queue` and not this one never reaches the
    scan at all.

    Carries real-shaped `mirror`/`url`/`base_sha` dummy values, not the bare
    `ok=True` this once was: `_batch` now reads and shares them with
    `_resolve_queue`, and a passing `Readiness` with none set is not a shape
    `check_readiness` itself ever returns."""
    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(
            True,
            mirror=Path("/tmp/pinned-mirror.git"),
            url="https://github.com/o/r.git",
            base_sha="a" * 40,
        ),
    )


def _fake_batch_resolution(tmp_path, *, repo_id=None, candidates=None):
    """The empty-queue `QueueResolution` every `saffron batch` witness below
    needs when it fakes `_resolve_queue` out entirely — real fields, no real
    scan, so `run_batch` (real or faked in turn) has something to iterate
    over that is never more than the caller asked for."""
    return cli.QueueResolution(
        repo_id=repo_id,
        mirror=tmp_path / "m.git",
        base_sha="a" * 40,
        repo_slug=None,
        exported=tmp_path,
        candidates=candidates or [],
        refusals=[],
        reconciled=cli.ReconcileResult(),
        gh_failures=[],
        policy_unread=[],
    )


def test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes(
    tmp_path, monkeypatch
):
    """The command runs a night against one repo, resolving its queue
    through `_resolve_queue` — the function `SA-0051` extracted — and
    handing it to `run_batch`. Its two defaults are the ones §4.2.1 fixes:
    `--repo` defaults to the working directory, matching the attended
    `saffron cell` beside it, and `--budget` defaults to 50, sized against
    the queue rather than against capacity."""
    home = tmp_path / "home"
    monkeypatch.chdir(tmp_path)

    captured: dict = {}

    def _fake_resolve_queue(
        repo, home_arg, ledger, *, stamp_orphaned, pinned=None, stack=False
    ):
        captured["repo"] = repo
        return _fake_batch_resolution(tmp_path)

    def _fake_run_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        captured["candidates"] = candidates
        captured["budget_usd"] = budget_usd
        captured["until"] = until
        return "DRAINED"

    _readiness_passes(monkeypatch)
    monkeypatch.setattr(cli, "_resolve_queue", _fake_resolve_queue)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(cli, "run_batch", _fake_run_batch)

    assert main(["--home", str(home), "batch"]) == 0

    assert captured["repo"] == tmp_path.resolve()
    assert captured["budget_usd"] == 50.0
    assert captured["until"] is None


def test_the_batch_scan_asks_for_the_stamping_the_attended_one_refuses():
    """§4.2.1's batch-scan premise: one batch runs at a time, so an
    in-flight row found while scanning tonight's queue is a corpse a dead
    scan left behind, not live work an operator is watching, and is stamped
    `ORPHANED` before the queue is filtered — `stamp_orphaned=True`.
    `saffron queue` asserts the opposite argument for the opposite reason
    (`test_looking_at_the_queue_still_never_stamps_a_corpse`); the behaviour
    itself was proven where `_resolve_queue` was built, not here."""
    assert _source_calls(
        cli._batch, "_resolve_queue", keyword="stamp_orphaned", value=True
    )


def test_the_batch_rescans_through_the_pinned_base_without_stamping_orphans(
    tmp_path, monkeypatch
):
    """`saffron batch` rescans through `_resolve_queue`, against the exact
    `PinnedBase` the opening call used, with `stamp_orphaned=False` — a task
    this same night left in flight is live, not a corpse. A task started
    after that rescan receives the `repo_id` the rescan resolved, not the
    opening scan's, which matters on a repo's first night when the opening
    `repo_id` is `None` (backlog item b-d6bff7)."""
    home = tmp_path / "home"
    monkeypatch.chdir(tmp_path)

    resolve_calls: list[dict] = []
    recorded_repo_ids: list[int | None] = []
    candidate = Candidate(
        path=Path("SY-1.md"),
        spec=intake.Spec(id="SY-1", title="t", type="chore"),
        spec_sha="s" * 64,
        task_id=None,
    )
    rescanned = Candidate(
        path=Path("SY-2.md"),
        spec=intake.Spec(id="SY-2", title="t", type="chore"),
        spec_sha="r" * 64,
        task_id=None,
    )

    def _fake_resolve_queue(
        repo, home_arg, ledger, *, stamp_orphaned, pinned=None, stack=False
    ):
        resolve_calls.append(
            {"stamp_orphaned": stamp_orphaned, "pinned": pinned, "stack": stack}
        )
        # The opening call: `None`, no candidates. The rescan: an id, its own list.
        if len(resolve_calls) == 1:
            return _fake_batch_resolution(tmp_path, repo_id=None)
        return _fake_batch_resolution(tmp_path, repo_id=99, candidates=[rescanned])

    def _fake_run_batch(
        candidates, ledger, budget_usd, until, runner, *, rescan, **kwargs
    ):
        # The rescan's own list, not the opening one or an empty one.
        assert list(rescan()) == [rescanned]
        runner(candidate)
        return "DRAINED"

    def _recording_run_task(spec, spec_sha, *, repo_id, **kwargs):
        recorded_repo_ids.append(repo_id)
        return CellOutcome(
            state="READY_FOR_REVIEW", task_id=1, run_id=1, task_dir=tmp_path
        )

    _readiness_passes(monkeypatch)
    monkeypatch.setattr(cli, "_resolve_queue", _fake_resolve_queue)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(cli, "run_batch", _fake_run_batch)
    monkeypatch.setattr(cli, "run_task", _recording_run_task)

    assert main(["--home", str(home), "batch"]) == 0

    assert len(resolve_calls) == 2
    assert resolve_calls[0]["stamp_orphaned"] is True
    assert resolve_calls[1]["stamp_orphaned"] is False
    assert resolve_calls[0]["pinned"] is not None
    assert resolve_calls[1]["pinned"] is resolve_calls[0]["pinned"]
    assert [call["stack"] for call in resolve_calls] == [False, False]
    assert recorded_repo_ids == [99]


def test_saffron_batch_stack_plans_once_and_runs_that_order(
    tmp_path, monkeypatch, capsys
):
    """`saffron batch --stack` resolves the queue once, with `stack=True` and
    `stamp_orphaned=True`, against the pinned base. It never calls
    `run_batch`. It hands the resolved order to `run_stack_batch`, with the
    runner `_stack_runner` builds. That runner looks up `repo_id` fresh per
    task, so a repo recorded after the opening scan still reaches the
    first candidate. A readiness failure and a queue that raises both still reach
    the real `run_stack_batch`, so both still close the batch row
    `INFRASTRUCTURE`."""
    real_stack_runner = cli._stack_runner
    real_run_stack_batch = cli.run_stack_batch
    sentinel_runner = object()

    def _run_batch_must_not_run(*_a, **_k):
        pytest.fail("cli.run_batch was called on the --stack path")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "run_batch", _run_batch_must_not_run)

    # Case 1: readiness passes.
    sy2 = Candidate(
        path=Path("SY-2.md"),
        spec=intake.Spec(id="SY-2", title="t", type="chore", priority=3),
        spec_sha="s" * 64,
        task_id=None,
    )
    sy1 = Candidate(
        path=Path("SY-1.md"),
        spec=intake.Spec(
            id="SY-1", title="t", type="chore", priority=1, depends_on=["SY-2"]
        ),
        spec_sha="r" * 64,
        task_id=None,
    )
    resolve_calls: list[dict] = []
    stack_runner_calls: list[dict] = []
    recorded: dict = {}

    def _fake_resolve_queue(
        repo, home_arg, ledger, *, stamp_orphaned, pinned=None, stack=False
    ):
        resolve_calls.append(
            {"stamp_orphaned": stamp_orphaned, "pinned": pinned, "stack": stack}
        )
        return _fake_batch_resolution(tmp_path, repo_id=None, candidates=[sy2, sy1])

    def _fake_stack_runner(**kwargs):
        stack_runner_calls.append(kwargs)
        return sentinel_runner

    def _recording_run_task(
        spec, spec_sha, *, repo_id, handoff, repo, out_dir, ledger, base, **kwargs
    ):
        recorded["repo_id"] = repo_id
        recorded["handoff"] = handoff
        recorded["repo"] = repo
        recorded["out_dir"] = out_dir
        recorded["ledger"] = ledger
        recorded["base"] = base
        return CellOutcome(
            state="READY_FOR_REVIEW", task_id=1, run_id=1, task_dir=tmp_path
        )

    def _fake_run_stack_batch(
        candidates, ledger, budget_usd, until, runner, *, readiness_check, **kwargs
    ):
        recorded["candidates"] = candidates
        recorded["runner"] = runner
        recorded["upserted_repo_id"] = ledger.upsert_repo(
            "r", "https://github.com/o/r.git", "/m.git", policy_sha=None
        )
        built = real_stack_runner(**stack_runner_calls[0])
        built(candidates[0], None)
        return "DRAINED"

    _readiness_passes(monkeypatch)
    monkeypatch.setattr(cli, "_resolve_queue", _fake_resolve_queue)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(cli, "_stack_runner", _fake_stack_runner)
    monkeypatch.setattr(cli, "run_task", _recording_run_task)
    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)

    home_pass = tmp_path / "home-pass"
    assert main(["--home", str(home_pass), "batch", "--stack"]) == 0

    assert len(resolve_calls) == 1
    assert resolve_calls[0]["stack"] is True
    assert resolve_calls[0]["stamp_orphaned"] is True
    assert resolve_calls[0]["pinned"] is not None
    assert [c.spec.id for c in recorded["candidates"]] == ["SY-2", "SY-1"]
    assert recorded["runner"] is sentinel_runner
    assert recorded["repo_id"] == recorded["upserted_repo_id"]
    assert recorded["handoff"] == task.Handoff(stacked_on=None, target_branch=None)
    assert recorded["repo"] == tmp_path.resolve()
    assert recorded["out_dir"] == home_pass / "batches" / "v0"
    assert recorded["repo"] != recorded["out_dir"]

    # Case 2: readiness fails, with the real `run_stack_batch`.
    monkeypatch.setattr(cli, "run_stack_batch", real_run_stack_batch)
    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(False, "auth", "token invalid"),
    )

    home_fails = tmp_path / "home-fails"
    assert main(["--home", str(home_fails), "batch", "--stack"]) == 2

    out = capsys.readouterr().out
    assert "auth" in out
    assert "token invalid" in out

    ledger = Ledger(home_fails / "ledger.db")
    row = ledger._db.execute(
        "SELECT status, ended_at FROM batches ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()
    ledger.close()
    assert row["status"] == "INFRASTRUCTURE"
    assert row["ended_at"] is not None

    # Case 3: `_resolve_queue` raises, with the real `run_stack_batch`.
    _readiness_passes(monkeypatch)

    def _raise(*a, **k):
        raise RuntimeError("the mirror could not be fetched mid-scan")

    monkeypatch.setattr(cli, "_resolve_queue", _raise)

    home_raises = tmp_path / "home-raises"
    assert main(["--home", str(home_raises), "batch", "--stack"]) == 2

    out = capsys.readouterr().out
    batch_lines = [line for line in out.splitlines() if line.startswith("batch:")]
    assert any(
        "the queue could not be resolved" in line and "mid-scan" in line
        for line in batch_lines
    )
    assert "readiness failed" not in out

    ledger = Ledger(home_raises / "ledger.db")
    row = ledger._db.execute(
        "SELECT status, ended_at FROM batches ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()
    ledger.close()
    assert row["status"] == "INFRASTRUCTURE"
    assert row["ended_at"] is not None


def _raises(exc):
    def _raise(*_a, **_k):
        raise exc

    return _raise


def test_a_stack_batch_holds_a_quarter_of_its_budget_and_reads_its_stack_at_the_pinned_base(
    tmp_path, monkeypatch, capsys
):
    """`saffron batch --stack --budget N` reserves `N` times
    `end_review.RESERVE_SHARE` and hands `run_stack_batch` an
    `end_review` callable built by `cli._stack_end_review`. It reads
    `CLAUDE.md`, `.saffron/` and `CONTEXT.md` at the pinned base, never
    from the operator's own checkout.

    A raise from any of its reads, or from `run_end_review` itself,
    records every layer as an error, never twice for one lens and
    never silently.
    """
    mirror = tmp_path / "end-review-mirror"
    mirror.mkdir()
    _git(mirror, "init", "-q")
    (mirror / ".saffron").mkdir()
    (mirror / ".saffron" / "policy.yaml").write_text(
        "gates: {}\nthread_env:\n  X: base\n"
    )
    (mirror / "CLAUDE.md").write_text("claude at base\n")
    _git(mirror, "add", "-A")
    _git(mirror, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "base")
    base_sha = _rev_parse(mirror, "HEAD")
    (mirror / ".saffron" / "policy.yaml").write_text(
        "gates: {}\nthread_env:\n  X: head\n"
    )
    (mirror / "CLAUDE.md").write_text("claude at head\n")
    _git(mirror, "add", "-A")
    _git(mirror, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "head")

    repo = tmp_path / "operator-repo"
    repo.mkdir()
    (repo / "CLAUDE.md").write_text("the operator's own CLAUDE.md, unread here\n")
    (repo / "CONTEXT.md").write_text("the operator's own CONTEXT.md, unread here\n")
    monkeypatch.chdir(repo)

    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(
            True, mirror=mirror, url="https://github.com/o/r.git", base_sha=base_sha
        ),
    )

    spec = intake.Spec(id="SY-1", title="t", type="chore")
    candidate = Candidate(
        path=Path("SY-1.md"), spec=spec, spec_sha="s" * 64, task_id=None
    )
    resolved = cli.QueueResolution(
        repo_id=None,
        mirror=mirror,
        base_sha=base_sha,
        repo_slug=None,
        exported=tmp_path,
        candidates=[candidate],
        refusals=[],
        reconciled=cli.ReconcileResult(),
        gh_failures=[],
        policy_unread=[],
    )
    monkeypatch.setattr(cli, "_resolve_queue", lambda *a, **k: resolved)

    run_captured: dict = {}
    sentinel = object()

    def _fake_run_stack_batch(
        candidates, ledger, budget_usd, until, runner, *, readiness_check, **kwargs
    ):
        run_captured["budget_usd"] = budget_usd
        run_captured["reserve_usd"] = kwargs["reserve_usd"]
        run_captured["end_review_result"] = kwargs["end_review"](
            "7", 10.5, {spec.id: spec}
        )
        return "DRAINED"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)

    review_captured: dict = {}

    def _fake_run_end_review(ledger_arg, batch_key, reserve_usd, specs, **kwargs):
        review_captured["ledger"] = ledger_arg
        review_captured["batch_key"] = batch_key
        review_captured["reserve_usd"] = reserve_usd
        review_captured["specs"] = specs
        review_captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(cli.end_review, "run_end_review", _fake_run_end_review)

    agent_calls: list[dict] = []

    def _fake_run_agent(
        container,
        *,
        prompt,
        options,
        spec_id,
        resume=None,
        emit=lambda event: None,
        last_cost_usd=0.0,
        timeout_s=3600,
        **kwargs,
    ):
        agent_calls.append({"spec_id": spec_id, "timeout_s": timeout_s})
        return implement.AttemptResult(
            session_id=None,
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=0.0,
            rate_limit_status="rejected",
        )

    monkeypatch.setattr(cli.implement, "run_agent", _fake_run_agent)

    cell_up_calls: list[dict] = []
    cell_down_calls: list[dict] = []

    def _fake_cell_up(
        *,
        repo,
        mirror,
        tree_base,
        branch,
        network,
        critic_network,
        volume,
        state,
        container,
        gates_dir,
        thread_env,
        created,
        note,
    ):
        cell_up_calls.append(
            {
                "repo": repo,
                "mirror": mirror,
                "tree_base": tree_base,
                "gates_dir": gates_dir,
                "thread_env": dict(thread_env),
            }
        )
        note("cell_up", "cell up")

    def _fake_cell_down(
        *, network, critic_network, volume, state, container, created, note
    ):
        cell_down_calls.append({"container": container})
        note("cell_down", True, "cell down")

    monkeypatch.setattr(session, "cell_up", _fake_cell_up)
    monkeypatch.setattr(session, "cell_down", _fake_cell_down)
    monkeypatch.setattr(cli.runtime, "remove_container", lambda _container: None)

    home = tmp_path / "home"
    assert main(["--home", str(home), "batch", "--stack", "--budget", "42"]) == 0

    printed = capsys.readouterr().out
    assert "budget $42.00, reserve $10.50, writer $10.50, until none" in printed

    assert run_captured["budget_usd"] == 42.0
    assert run_captured["reserve_usd"] == 10.5
    assert run_captured["end_review_result"] is sentinel

    assert review_captured["batch_key"] == "7"
    assert review_captured["reserve_usd"] == 10.5
    assert review_captured["specs"] == {spec.id: spec}
    assert review_captured["mirror"] == mirror
    assert review_captured["claude_md"] == "claude at base\n"
    assert (
        review_captured["context_md"] == (cli._SAFFRON_ROOT / "CONTEXT.md").read_text()
    )
    assert review_captured["prompts_dir"] == cli.context.PROMPTS_DIR
    assert review_captured["max_turns"] == end_review.LENS_MAX_TURNS
    assert review_captured["budget_usd"] == end_review.LENS_BUDGET_USD

    fields = end_review.LayerFields(
        spec_id="SY-1", branch="b", pr_url="", base="base", head="h" * 40, known=""
    )
    with review_captured["open_cell"](fields) as container:
        assert isinstance(container, str)
    assert len(cell_up_calls) == 1
    assert cell_up_calls[0]["thread_env"] == {"X": "base"}
    assert cell_up_calls[0]["repo"] == repo
    assert cell_up_calls[0]["mirror"] == mirror
    assert cell_up_calls[0]["tree_base"] == "h" * 40
    policy_text = (
        cell_up_calls[0]["gates_dir"] / ".saffron" / "policy.yaml"
    ).read_text()
    assert "X: base" in policy_text
    assert len(cell_down_calls) == 1

    with pytest.raises(session.RateLimited):
        review_captured["agent"](
            "some-container", prompt="hi", options={}, emit=lambda event: None
        )
    assert agent_calls[-1]["spec_id"] == "end-review-7"
    assert agent_calls[-1]["timeout_s"] == session.TURN_TIMEOUT_S

    # Second half: `_stack_end_review` built directly, over its own ledger,
    # against five batches whose two layers are created in mixed order.
    memory = MemoryRecord()
    ledger2 = Ledger(tmp_path / "l2.db", record=memory)
    repo_id = ledger2.upsert_repo("r", "https://github.com/o/r2.git", "/m2.git", None)

    batch_keys: dict[int, str] = {}
    layer_keys: dict[int, tuple[str, str]] = {}
    layer_task_ids: dict[int, tuple[int, int]] = {}

    def _build_batch(number: int, *, top_first: bool) -> None:
        batch_id = ledger2.create_batch(budget_usd=100.0)
        run_id = ledger2.create_run(repo_id, base_sha, batch_id=batch_id)

        def _top() -> int:
            return ledger2.create_task(
                run_id, f"SY-TOP-{number}", "t" * 64, f"top-{number}"
            )

        def _bottom() -> int:
            return ledger2.create_task(
                run_id, f"SY-BOTTOM-{number}", "b" * 64, f"bottom-{number}"
            )

        if top_first:
            top_id = _top()
            ledger2.record_stack_layer(
                top_id, position=2, predecessor_task_id=None, generation=0
            )
            bottom_id = _bottom()
            ledger2.record_stack_layer(
                bottom_id, position=1, predecessor_task_id=None, generation=0
            )
        else:
            bottom_id = _bottom()
            ledger2.record_stack_layer(
                bottom_id, position=1, predecessor_task_id=None, generation=0
            )
            top_id = _top()
            ledger2.record_stack_layer(
                top_id, position=2, predecessor_task_id=None, generation=0
            )
        if number == 2:
            ledger2.create_task(run_id, "SY-EXTRA-2", "e" * 64, "extra-2")

        top_key = ledger2.record_key(top_id)
        bottom_key = ledger2.record_key(bottom_id)
        assert top_key is not None
        assert bottom_key is not None
        batch_keys[number] = str(batch_id)
        layer_keys[number] = (top_key, bottom_key)
        layer_task_ids[number] = (top_id, bottom_id)

    _build_batch(1, top_first=True)
    _build_batch(2, top_first=False)
    _build_batch(3, top_first=True)
    _build_batch(4, top_first=False)
    _build_batch(5, top_first=False)

    callable_ = cli._stack_end_review(
        pinned=task.PinnedBase(
            mirror=mirror, url="https://github.com/o/r.git", base_sha=base_sha
        ),
        repo=repo,
        ledger=ledger2,
        out_dir=tmp_path / "out2",
    )

    def _end_review_rows(keys: tuple[str, str]) -> list:
        return ledger2._db.execute(
            "SELECT task_key, lens, status, cost_usd, error FROM end_reviews "
            "WHERE task_key IN (?, ?) ORDER BY task_key, lens",
            keys,
        ).fetchall()

    def _end_review_facts(keys: tuple[str, str]) -> list:
        return [
            fact
            for key in keys
            for fact in memory.read(key)
            if fact.kind == "end_review"
        ]

    def _assert_all_error(result: object, keys: tuple[str, str], text: str) -> None:
        assert isinstance(result, end_review.StackReview)
        assert result.join is None
        assert [layer.task_key for layer in result.layers] == list(keys)
        for layer in result.layers:
            assert [lr.lens for lr in layer.reviews] == list(end_review.END_LENSES)
            for lr in layer.reviews:
                assert lr.cost_usd == 0.0
                assert lr.error is not None
                assert text in lr.error

    with monkeypatch.context() as m:
        m.setattr(cli.git_mirror, "export_saffron_dir", _raises(GitError("unreadable")))
        result1 = callable_(batch_keys[1], 10.5, {})
    _assert_all_error(result1, layer_keys[1], "unreadable")
    rows1 = _end_review_rows(layer_keys[1])
    assert len(rows1) == 4
    assert all(row["status"] == "error" and row["cost_usd"] == 0.0 for row in rows1)
    assert all("unreadable" in row["error"] for row in rows1)
    assert len(_end_review_facts(layer_keys[1])) == 4

    with monkeypatch.context() as m:
        m.setattr(cli, "load_policy", _raises(cli.PolicyError("unreadable")))
        result2 = callable_(batch_keys[2], 10.5, {})
    _assert_all_error(result2, layer_keys[2], "unreadable")
    rows2 = _end_review_rows(layer_keys[2])
    assert len(rows2) == 4
    assert len(_end_review_facts(layer_keys[2])) == 4

    with monkeypatch.context() as m:
        m.setattr(cli.git_mirror, "file_at", _raises(GitError("unreadable")))
        result3 = callable_(batch_keys[3], 10.5, {})
    _assert_all_error(result3, layer_keys[3], "unreadable")
    rows3 = _end_review_rows(layer_keys[3])
    assert len(rows3) == 4
    assert len(_end_review_facts(layer_keys[3])) == 4

    top_id_4, _bottom_id_4 = layer_task_ids[4]

    def _fake_run_end_review_case4(ledger_arg, batch_key, reserve_usd, specs, **kwargs):
        ledger_arg.record_end_review(
            top_id_4, lens="spec", status="reviewed", cost_usd=0.5, error=None
        )
        # A join row is no lens row of the layer's own: its note stays off.
        ledger_arg.record_end_review(
            _bottom_id_4, lens="join", status="not_reached", cost_usd=0.0, error=None
        )
        raise RuntimeError("review broke")

    with monkeypatch.context() as m:
        m.setattr(cli.end_review, "run_end_review", _fake_run_end_review_case4)
        result4 = callable_(batch_keys[4], 10.5, {})
    assert isinstance(result4, end_review.StackReview)
    top_key_4, bottom_key_4 = layer_keys[4]
    assert result4.join is None
    assert [layer.task_key for layer in result4.layers] == [top_key_4, bottom_key_4]
    top_layer_4, bottom_layer_4 = result4.layers
    assert [lr.lens for lr in top_layer_4.reviews] == list(end_review.END_LENSES)
    for lr in top_layer_4.reviews:
        assert lr.cost_usd == 0.0
        assert lr.error is not None
        assert "review broke" in lr.error
        assert "written first" in lr.error
    for lr in bottom_layer_4.reviews:
        assert lr.cost_usd == 0.0
        assert lr.error is not None
        assert "review broke" in lr.error
        assert "written first" not in lr.error
    rows4 = _end_review_rows(layer_keys[4])
    assert len(rows4) == 5
    reviewed = [row for row in rows4 if row["status"] == "reviewed"]
    assert len(reviewed) == 1
    assert reviewed[0]["lens"] == "spec"
    assert reviewed[0]["task_key"] == top_key_4
    assert reviewed[0]["cost_usd"] == 0.5
    errored = [row for row in rows4 if row["status"] == "error"]
    assert len(errored) == 3
    assert all("review broke" in row["error"] for row in errored)
    assert len(_end_review_facts(layer_keys[4])) == 5

    def _fake_run_end_review_case5(ledger_arg, batch_key, reserve_usd, specs, **kwargs):
        raise RuntimeError("review broke")

    with monkeypatch.context() as m:
        m.setattr(cli.end_review, "run_end_review", _fake_run_end_review_case5)
        m.setattr(ledger2, "record_end_review", _raises(OSError("record broke")))
        result5 = callable_(batch_keys[5], 10.5, {})
    _assert_all_error(result5, layer_keys[5], "review broke")
    rows5 = _end_review_rows(layer_keys[5])
    assert len(rows5) == 0
    assert len(_end_review_facts(layer_keys[5])) == 0

    printed2 = capsys.readouterr().out
    end_review_lines = [
        line for line in printed2.splitlines() if line.startswith("end review:")
    ]
    assert len(end_review_lines) == 6
    assert sum("unreadable" in line for line in end_review_lines) == 3
    assert sum("review broke" in line for line in end_review_lines) == 3
    assert sum("record broke" in line for line in end_review_lines) == 1
    assert all(
        "unreadable" in line or "review broke" in line for line in end_review_lines
    )


def test_a_deadline_earlier_than_now_resolves_to_tomorrow():
    """`06:30` is a time of day, not a duration: resolved at 22:00 the same
    night it means 06:30 *tomorrow*, not a window that closed sixteen hours
    ago. The case an operator hits every night they ask for the morning.
    `23:00` resolved at the same 22:00 is still tonight, the other half of
    the same rule."""
    now = datetime(2026, 9, 5, 22, 0)

    assert cli._resolve_until("06:30", now) == datetime(2026, 9, 6, 6, 30)
    assert cli._resolve_until("23:00", now) == datetime(2026, 9, 5, 23, 0)


def test_the_batch_command_offers_no_concurrency_or_multi_repo_flag(capsys):
    """Neither a concurrency flag nor a multi-repo flag exists on `batch`
    itself. §4.2.1 refuses both by name — a flag for a knob with one
    position is the same defect in a command that item 18 found in a
    dataclass.

    Read off `batch --help`'s own usage line, not off a generic "unknown
    argument" `SystemExit` — that `SystemExit` fires just as readily for an
    unrecognized *subcommand*, so it would pass just as green if `batch`
    did not exist at all. `--help` exits `0` only when `batch` is a real
    subcommand parsed by its own parser (an unknown subcommand exits `2`
    instead, `saffron: error: argument command: invalid choice`), so the
    zero here is itself proof that `batch`'s own argument set — not some
    other command's — was read.
    """
    with pytest.raises(SystemExit) as excinfo:
        main(["batch", "--help"])
    assert excinfo.value.code == 0

    out = capsys.readouterr().out
    assert "--concurrency" not in out
    assert "--repos" not in out
    # The positive control: the three flags §4.2.1 does name are there.
    assert "--repo" in out
    assert "--budget" in out
    assert "--until" in out


def test_the_three_ordinary_stop_reasons_all_exit_zero(tmp_path, monkeypatch, capsys):
    """Draining, running out of budget, and reaching the deadline are the
    same answer to "did the night make it": a batch that drains with three
    failed tasks still did its job, and the individual outcomes are the
    morning queue's business, not this exit code's.

    The printed line is asserted alongside the code. An exit status is not
    what an operator reads at 7am — it is gone by then, and `launchd` keeps
    only the log. Replacing `print(f"batch: {stop}")` with `pass` left the
    whole suite green, so the one line that says how the night ended was
    guarded by nothing."""
    home = tmp_path / "home"

    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")

    for reason in ("DRAINED", "BUDGET", "UNTIL"):
        monkeypatch.setattr(cli, "run_batch", lambda *a, _r=reason, **k: _r)
        assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 0
        assert f"batch: {reason}" in capsys.readouterr().out


def test_infrastructure_and_a_failed_readiness_both_exit_two(tmp_path, monkeypatch):
    """The breaker firing and a readiness failure that takes the whole
    night are the same exit code — both say the infrastructure failed,
    which is what an unattended caller reads to decide whether tomorrow is
    worth attempting."""
    home = tmp_path / "home"

    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")

    # The breaker: `run_batch` itself says `INFRASTRUCTURE`, no readiness
    # check ever recorded.
    with monkeypatch.context() as m:
        m.setattr(cli, "run_batch", lambda *a, **k: "INFRASTRUCTURE")
        assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2

    # A readiness failure: the real `run_batch` runs, calls the real
    # readiness check, and stops before any candidate.
    with monkeypatch.context() as m:
        m.setattr(
            cli.preflight,
            "check_readiness",
            lambda *a, **k: preflight.Readiness(False, "auth", "boom"),
        )
        assert (
            main(["--home", str(home / "two"), "batch", "--repo", str(tmp_path)]) == 2
        )


def test_a_night_that_left_a_task_in_flight_exits_two(tmp_path, monkeypatch, capsys):
    """`saffron batch` exits 2 for an INCOMPLETE night and prints
    `batch: INCOMPLETE`, not the infrastructure line. `0` means the night
    made it, and this one did not, but the machine did not break either, and
    a line saying it did sends the operator to the wrong place. It still
    never exits `1`, which is reserved for a task's own failure (§4.2.1)."""
    home = tmp_path / "home"

    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(cli, "run_batch", lambda *a, **k: "INCOMPLETE")

    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2

    printed = capsys.readouterr().out
    assert "batch: INCOMPLETE" in printed
    assert "infrastructure failed" not in printed
    assert "readiness failed" not in printed


def test_a_batch_never_exits_one_whatever_stopped_it(tmp_path, monkeypatch):
    """§4.2.1 reserves `1` rather than reusing it: a batch is not a task, and
    letting `1` mean something here would merge two vocabularies that answer
    different questions. Walked across all five stop reasons."""
    home = tmp_path / "home"

    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")

    for reason in ("DRAINED", "BUDGET", "UNTIL", "INFRASTRUCTURE", "INCOMPLETE"):
        monkeypatch.setattr(cli, "run_batch", lambda *a, _r=reason, **k: _r)
        assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) != 1


def test_a_batch_on_a_runtime_never_proven_end_to_end_is_refused(
    tmp_path, monkeypatch, capsys
):
    """podman has not started a cell end to end, so a night on it is refused
    before readiness spends anything — and refused as infrastructure, 2."""
    from saffron.cell import runtime
    from saffron.cell.runtimes import podman

    monkeypatch.setattr(runtime, "_selected", podman.DIALECT)

    def _no_readiness(*a, **k):
        raise AssertionError("readiness ran for a refused night")

    monkeypatch.setattr(cli.preflight, "check_readiness", _no_readiness)
    assert main(["--home", str(tmp_path / "h"), "batch", "--repo", str(tmp_path)]) == 2
    assert "batch: refused" in capsys.readouterr().out


def test_an_unknown_runtime_name_exits_two_not_one(tmp_path, monkeypatch, capsys):
    """A typo in `SAFFRON_CELL_RUNTIME` is the operator's infrastructure, not a
    task that did not make it. Under launchd, 1 reads as a night that ran."""
    from saffron.cell import runtime

    monkeypatch.setattr(runtime, "_selected", None)
    monkeypatch.setenv(runtime.RUNTIME_ENV, "bogus")
    assert main(["--home", str(tmp_path / "h"), "batch", "--repo", str(tmp_path)]) == 2
    assert "bogus" in capsys.readouterr().out


def test_the_night_is_given_a_real_readiness_check_not_the_loops_default(
    tmp_path, monkeypatch
):
    """`run_batch`'s own default is to proceed — the right default for a
    loop that cannot know a repo's paths or hold its token, and the wrong
    one for a night. `saffron batch` passes a real callable, bound to this
    run's own repo, mirror path, home and token, so an expired token at
    22:00 does not buy a night of clean-looking nothing."""
    home = tmp_path / "home"
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-real")
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )

    seen: dict = {}

    def _fake_check_readiness(repo_arg, mirror_path, *, scratch, home, token):
        seen.update(repo=repo_arg, mirror_path=mirror_path, home=home, token=token)
        return preflight.Readiness(
            True,
            mirror=Path("/tmp/pinned-mirror.git"),
            url="https://github.com/o/r.git",
            base_sha="a" * 40,
        )

    monkeypatch.setattr(cli.preflight, "check_readiness", _fake_check_readiness)

    captured: dict = {}

    def _fake_run_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        captured.update(kwargs)
        return "DRAINED"

    monkeypatch.setattr(cli, "run_batch", _fake_run_batch)

    assert main(["--home", str(home), "batch", "--repo", str(repo)]) == 0

    readiness_check = captured["readiness_check"]
    # There is no longer a permissive default to be "not" — `run_batch`
    # requires the argument, so a caller that forgot cannot start a night at
    # all. What is left to check is that the one supplied is bound to this
    # run's own paths and token, which is what makes it a gate rather than a
    # formality.
    readiness_check()

    assert seen["repo"] == repo.resolve()
    assert seen["token"] == "sk-real"
    assert Path(seen["home"]) == home
    assert seen["mirror_path"] == cli._mirror_path(repo.resolve(), home)


def test_a_readiness_failure_names_the_step_that_failed(tmp_path, monkeypatch, capsys):
    """An expired token and a full disk are the same exit code and
    different mornings — the result carries the step precisely so a caller
    need not guess which."""
    home = tmp_path / "home"

    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(False, "auth", "token invalid"),
    )

    result = main(["--home", str(home), "batch", "--repo", str(tmp_path)])

    assert result == 2
    out = capsys.readouterr().out
    assert "auth" in out
    assert "token invalid" in out


def test_the_adapter_packages_a_ready_task_and_reports_what_packaging_made_of_it(
    tmp_path, monkeypatch, capsys
):
    """`run_one_cell` stops at `READY_FOR_REVIEW`; the branch is pushed and the
    pull request opened by `package_phase.package`, which the attended path
    calls afterwards and the loop cannot call at all. Without this the night
    runs to completion and opens nothing — backlog item 45's failure mode by
    construction rather than by accident.

    And the outcome handed back carries what packaging made of the task, not
    what the cell left behind: `run_batch` reads `outcome.state` to drive the
    breaker and the batch record, so a `MERGE_FAILED` reported as
    `READY_FOR_REVIEW` misstates the night in the one column that says why it
    ended.
    """
    repo = _local_origin(tmp_path)
    mirror, url = _mirror_of(tmp_path, repo)
    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, url)

    runner = cli._batch_runner(
        pinned=task.PinnedBase(mirror=mirror, url=url, base_sha="a" * 40),
        repo_id=lambda: repo_id,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
    )

    task_id = _seed_task(ledger, repo_id, spec_id="SY-1", state="READY_FOR_REVIEW")
    outcome = CellOutcome(
        state="READY_FOR_REVIEW",
        task_id=task_id,
        run_id=1,
        task_dir=tmp_path / "out" / "SY-1",
    )
    monkeypatch.setattr(task, "run_one_cell", lambda *a, **k: outcome)

    packaged: dict = {}

    def _package(*args, **kwargs):
        packaged["called"] = True
        packaged.update(kwargs)
        return SimpleNamespace(state="MERGE_FAILED", pr_url=None, note="pushed, no PR")

    monkeypatch.setattr(cli.package_phase, "package", _package)

    candidate = Candidate(
        path=Path("SY-1.md"),
        spec=intake.Spec(id="SY-1", title="t", type="chore", touches=["src/**"]),
        spec_sha="s" * 64,
        task_id=task_id,
    )

    returned = runner(candidate)

    assert packaged.get("called") is True
    # This candidate declares no `consumes`, so the runner never refuses it.
    assert isinstance(returned, CellOutcome)
    assert returned.state == "MERGE_FAILED"
    # The line the operator reads. Replacing it with `pass` left the suite
    # green, and this is the only place a task's fate is rendered at all.
    printed = capsys.readouterr().out
    assert "SY-1" in printed
    assert "MERGE_FAILED" in printed
    assert "pushed, no PR" in printed
    ledger.close()


def test_a_night_says_what_its_own_scan_could_not_check(tmp_path, monkeypatch, capsys):
    """A `gh` that could not start means the open-pull-request and
    touches-overlap refusals never ran, and an unreadable `policy.yaml` at
    `base_sha` means the protected-path refusal never ran. The attended
    command says so; unsaid here, a degraded night is indistinguishable in the
    morning from one whose refusals all passed, on the one path where nobody
    is awake to notice.
    """
    resolved = cli.QueueResolution(
        repo_id=1,
        mirror=tmp_path / "m.git",
        base_sha="a" * 40,
        repo_slug="jtmcn/saffron",
        exported=tmp_path,
        candidates=[],
        refusals=[],
        reconciled=cli.ReconcileResult(),
        gh_failures=["gh: command not found"],
        policy_unread=["policy.yaml: no such file"],
    )
    _readiness_passes(monkeypatch)
    monkeypatch.setattr(cli, "_resolve_queue", lambda *a, **k: resolved)
    monkeypatch.setattr(cli.package_phase, "real_remote", lambda _repo: "u")
    monkeypatch.setattr(cli, "_batch_runner", lambda *a, **k: lambda _c: None)
    monkeypatch.setattr(cli, "run_batch", lambda *a, **k: "DRAINED")

    args = argparse.Namespace(
        repo=tmp_path, home=tmp_path / "home", budget=50.0, until=None, stack=False
    )
    ledger = Ledger(tmp_path / "l.db")
    assert cli._batch(args, ledger, tmp_path / "out") == 0
    ledger.close()

    printed = capsys.readouterr().out
    assert "gh could not be run" in printed
    assert "policy.yaml at this base_sha could not be read" in printed


def test_the_unattended_path_records_the_ceilings_that_bound_each_task(
    tmp_path, monkeypatch, capsys
):
    """A night keeps no record of what bounded each of its tasks.

    `_run_cell` prints all three on the way in, for the reason `_ceilings`
    exists: `SA-0005` died at the turn ceiling with more than half its budget
    left and nothing said what any of the three were. The unattended path
    never resolved them — it read the spec's fields straight into `CellSpec`,
    correctly, and said nothing — so the one path whose stdout *is* the
    night's only human-readable record was the one that kept no record.

    `budget_usd` survives in `tasks.budget_usd`; `max_attempts` and
    `max_turns` are in no column and in no event, and the `Budget` event
    carries a `limit` only for the ceiling that actually fired. So a task
    that ended any other way left both unrecoverable.
    """
    repo = _local_origin(tmp_path)
    mirror, url = _mirror_of(tmp_path, repo)
    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, url)

    runner = cli._batch_runner(
        pinned=task.PinnedBase(mirror=mirror, url=url, base_sha="a" * 40),
        repo_id=lambda: repo_id,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
    )

    task_id = _seed_task(ledger, repo_id, spec_id="SY-1", state="EXHAUSTED")
    monkeypatch.setattr(
        task,
        "run_one_cell",
        lambda *a, **k: CellOutcome(
            state="EXHAUSTED",
            task_id=task_id,
            run_id=1,
            task_dir=tmp_path / "out" / "SY-1",
        ),
    )

    # `max_turns` declared, the other two left to their model defaults: the
    # three-label distinction `_ceilings` draws is the whole point of the
    # record, so a fixture that declares all three or none would not show it.
    candidate = Candidate(
        path=Path("SY-1.md"),
        spec=intake.Spec(
            id="SY-1", title="t", type="chore", touches=["src/**"], max_turns=42
        ),
        spec_sha="s" * 64,
        task_id=task_id,
    )
    runner(candidate)
    ledger.close()

    printed = capsys.readouterr().out
    assert "ceilings:" in printed, "the night says nothing about what bound the task"
    assert "max_turns=42 (spec)" in printed
    assert "max_attempts=" in printed and "(default)" in printed

    # Both halves of the record, not just the one a terminal scrolls away:
    # `saffron watch` and any morning report read `events.jsonl`, so a line
    # that printed and did not persist would leave the night's durable record
    # exactly as empty as it was.
    logged = [e for e in read_log(tmp_path / "out" / "SY-1") if isinstance(e, Ceilings)]
    assert [(e.max_turns, e.turns_source) for e in logged] == [(42, "spec")]


def test_the_adapter_stacks_a_child_on_its_parents_branch(tmp_path, monkeypatch):
    """The adapter this command hands the loop resolves what each candidate
    stacks on, exactly as the attended path already does: a child runs cut
    from its parent's real branch head, never the pinned `base_sha`."""
    repo = _local_origin(tmp_path)
    head = _push_parent_branch(repo, "saffron/SY-9000")
    mirror, url = _mirror_of(tmp_path, repo)

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, url)
    parent = _seed_task(ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW")
    ledger.record_push(parent, "d" * 40)

    runner = cli._batch_runner(
        pinned=task.PinnedBase(mirror=mirror, url=url, base_sha="a" * 40),
        repo_id=lambda: repo_id,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
    )

    captured: dict = {}

    def _capture(cell_spec, **_kwargs):
        captured["spec"] = cell_spec
        raise SystemExit(0)

    monkeypatch.setattr(task, "run_one_cell", _capture)

    candidate = Candidate(
        path=Path("SY-1.md"),
        spec=intake.Spec(
            id="SY-1",
            title="t",
            type="chore",
            touches=["src/**"],
            depends_on=["SY-9000"],
        ),
        spec_sha="s" * 64,
        task_id=None,
    )

    with pytest.raises(SystemExit):
        runner(candidate)

    assert captured["spec"].stacked_on == head != "d" * 40
    ledger.close()


def test_the_adapter_stacks_on_the_first_dependency_only(tmp_path, monkeypatch):
    """K=1: a second dependency is still not a stacking base. The adapter
    must not widen that rule just because it is new code doing an old job —
    `depends_on[1]`'s own resolvable, waiting task and its real pushed
    branch must not leak into the result."""
    repo = _local_origin(tmp_path)
    _push_parent_branch(repo, "saffron/SY-2")
    mirror, url = _mirror_of(tmp_path, repo)

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, url)
    second = _seed_task(ledger, repo_id, spec_id="SY-2", state="READY_FOR_REVIEW")
    ledger.record_push(second, "b" * 40)

    runner = cli._batch_runner(
        pinned=task.PinnedBase(mirror=mirror, url=url, base_sha="a" * 40),
        repo_id=lambda: repo_id,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
    )

    captured: dict = {}

    def _capture(cell_spec, **_kwargs):
        captured["spec"] = cell_spec
        raise SystemExit(0)

    monkeypatch.setattr(task, "run_one_cell", _capture)

    candidate = Candidate(
        path=Path("SY-1.md"),
        spec=intake.Spec(
            id="SY-1",
            title="t",
            type="chore",
            touches=["src/**"],
            depends_on=["SY-1-parent", "SY-2"],
        ),
        spec_sha="s" * 64,
        task_id=None,
    )

    with pytest.raises(SystemExit):
        runner(candidate)

    assert captured["spec"].stacked_on is None
    ledger.close()


def test_the_stack_runner_hands_each_task_its_predecessors_fetched_branch(
    tmp_path, monkeypatch
):
    """`_stack_runner` fetches the predecessor's branch fresh into the
    mirror rather than reading the ledger, and never falls back to
    `_resolve_stacked_on`."""
    from saffron.task import Handoff

    repo = _local_origin(tmp_path)
    head = _push_parent_branch(repo, "saffron/SY-9000")
    _push_parent_branch(repo, "saffron/SY-5555")
    _git(repo, "branch", "-D", "saffron/SY-9000")
    mirror, url = _mirror_of(tmp_path, repo)

    with pytest.raises(subprocess.CalledProcessError):
        _rev_parse(mirror, "refs/heads/saffron/SY-9000")

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, url)
    parent = _seed_task(ledger, repo_id, spec_id="SY-5555", state="READY_FOR_REVIEW")
    ledger.record_push(parent, "d" * 40)

    runner = cli._stack_runner(
        pinned=task.PinnedBase(mirror=mirror, url=url, base_sha="a" * 40),
        repo_id=lambda: repo_id,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
    )

    captured: dict = {}

    def _run_task(*_a, **kwargs):
        captured["handoff"] = kwargs["handoff"]
        return CellOutcome(
            state="READY_FOR_REVIEW",
            task_id=1,
            run_id=1,
            task_dir=tmp_path / "out" / "SY-1",
        )

    monkeypatch.setattr(cli, "run_task", _run_task)

    def _as_candidate(spec_id, *, depends_on=None):
        return Candidate(
            path=Path(f"{spec_id}.md"),
            spec=intake.Spec(
                id=spec_id,
                title="t",
                type="chore",
                touches=["src/**"],
                depends_on=depends_on or [],
            ),
            spec_sha="s" * 64,
            task_id=None,
        )

    candidate = _as_candidate("SY-1", depends_on=["SY-5555"])

    runner(candidate, _as_candidate("SY-9000"))
    assert captured["handoff"] == Handoff(
        stacked_on=head, target_branch="saffron/SY-9000"
    )
    assert _rev_parse(mirror, "refs/heads/saffron/SY-9000") == head

    runner(candidate, None)
    assert captured["handoff"] == Handoff(stacked_on=None, target_branch=None)

    captured.clear()
    with pytest.raises(package.ParentGone):
        runner(candidate, _as_candidate("SY-7777"))
    assert "handoff" not in captured
    ledger.close()


def test_only_the_stack_runner_hands_run_task_the_candidates_task(
    tmp_path, monkeypatch
):
    """`_stack_runner` forwards each candidate's own `task_id`, never a
    predecessor's, so its cell runs on the task its own review opened.
    `_batch_runner` forwards none: that departure is its own backlog item."""
    monkeypatch.setattr(package, "fetch_parent_branch", lambda *_a, **_k: "d" * 40)

    recorded: list[int | None] = []

    def _recording_run_task(
        spec,
        spec_sha,
        *,
        ceilings,
        base,
        repo_id,
        repo,
        ledger,
        out_dir,
        token,
        handoff=None,
        task_id=None,
        emit=None,
    ):
        recorded.append(task_id)
        return CellOutcome(
            state="READY_FOR_REVIEW", task_id=1, run_id=1, task_dir=tmp_path
        )

    monkeypatch.setattr(cli, "run_task", _recording_run_task)

    def _candidate(spec_id, task_id):
        return Candidate(
            path=Path(f"{spec_id}.md"),
            spec=intake.Spec(id=spec_id, title="t", type="chore"),
            spec_sha="s" * 64,
            task_id=task_id,
        )

    pinned = task.PinnedBase(
        mirror=tmp_path / "m.git", url="https://github.com/o/r.git", base_sha="a" * 40
    )
    ledger = Ledger(tmp_path / "l.db")

    stack_runner = cli._stack_runner(
        pinned=pinned,
        repo_id=lambda: 1,
        repo=tmp_path / "repo",
        ledger=ledger,
        out_dir=tmp_path / "out",
    )
    stack_runner(_candidate("SY-1", 7), None)
    stack_runner(_candidate("SY-2", 8), _candidate("SY-1", 3))

    batch_runner = cli._batch_runner(
        pinned=pinned,
        repo_id=lambda: 1,
        repo=tmp_path / "repo",
        ledger=ledger,
        out_dir=tmp_path / "out",
    )
    batch_runner(_candidate("SY-5", 5))
    ledger.close()

    assert recorded == [7, 8, None]


def test_the_night_cannot_start_without_a_readiness_gate():
    """The loop used to bind a permissive stub, so a caller who simply forgot
    the argument got a vacuous §4.4 step 1 and a night that could start on an
    expired token. It is now required, which is a stronger guarantee than any
    assertion about which callable was passed: forgetting is a TypeError."""
    import inspect

    from saffron.batch import run_batch

    parameter = inspect.signature(run_batch).parameters["readiness_check"]
    assert parameter.default is inspect.Parameter.empty
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_the_adapter_packages_a_stacked_child_against_its_parents_branch(
    tmp_path, monkeypatch
):
    """`SA-0026`'s whole point: the sha and the branch travel together or
    neither does. The stacking witness above pins `CellSpec.stacked_on` — the
    sha — and nothing pinned `parent_branch`, the half that decides what the
    pull request targets. Mutating it to `None` left all of `test_cli.py`
    green while every night silently opened its stacked children against
    `main`."""
    repo = _local_origin(tmp_path)
    head = _push_parent_branch(repo, "saffron/SY-9000")
    mirror, url = _mirror_of(tmp_path, repo)

    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, url)
    parent = _seed_task(ledger, repo_id, spec_id="SY-9000", state="READY_FOR_REVIEW")
    ledger.record_push(parent, "d" * 40)

    runner = cli._batch_runner(
        pinned=task.PinnedBase(mirror=mirror, url=url, base_sha="a" * 40),
        repo_id=lambda: repo_id,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
    )

    task_id = _seed_task(ledger, repo_id, spec_id="SY-1", state="READY_FOR_REVIEW")
    monkeypatch.setattr(
        task,
        "run_one_cell",
        lambda *a, **k: CellOutcome(
            state="READY_FOR_REVIEW",
            task_id=task_id,
            run_id=1,
            task_dir=tmp_path / "out" / "SY-1",
        ),
    )

    packaged: dict = {}

    def _package(*args, **kwargs):
        packaged.update(kwargs)
        return SimpleNamespace(state="READY_FOR_REVIEW", pr_url="u", note=None)

    monkeypatch.setattr(cli.package_phase, "package", _package)

    candidate = Candidate(
        path=Path("SY-1.md"),
        spec=intake.Spec(
            id="SY-1",
            title="t",
            type="chore",
            touches=["src/**"],
            depends_on=["SY-9000"],
        ),
        spec_sha="s" * 64,
        task_id=task_id,
    )
    runner(candidate)

    assert packaged["parent_branch"] == "saffron/SY-9000"
    assert head  # the parent's branch really exists, so this is not a typo
    ledger.close()


def test_an_unstacked_task_is_packaged_against_no_parent(tmp_path, monkeypatch):
    """The other half: a candidate with no `depends_on` must target the
    default branch, so `parent_branch` has to be `None` rather than a stale
    value carried from a previous candidate."""
    repo = _local_origin(tmp_path)
    mirror, url = _mirror_of(tmp_path, repo)
    ledger = Ledger(tmp_path / "l.db")
    repo_id = _seed_repo(ledger, url)

    runner = cli._batch_runner(
        pinned=task.PinnedBase(mirror=mirror, url=url, base_sha="a" * 40),
        repo_id=lambda: repo_id,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
    )

    task_id = _seed_task(ledger, repo_id, spec_id="SY-2", state="READY_FOR_REVIEW")
    monkeypatch.setattr(
        task,
        "run_one_cell",
        lambda *a, **k: CellOutcome(
            state="READY_FOR_REVIEW",
            task_id=task_id,
            run_id=1,
            task_dir=tmp_path / "out" / "SY-2",
        ),
    )

    packaged: dict = {}

    def _package(*args, **kwargs):
        packaged.update(kwargs)
        return SimpleNamespace(state="READY_FOR_REVIEW", pr_url="u", note=None)

    monkeypatch.setattr(cli.package_phase, "package", _package)

    runner(
        Candidate(
            path=Path("SY-2.md"),
            spec=intake.Spec(id="SY-2", title="t", type="chore", touches=["src/**"]),
            spec_sha="s" * 64,
            task_id=task_id,
        )
    )

    assert packaged["parent_branch"] is None
    ledger.close()


def test_readiness_is_probed_before_the_scan_that_depends_on_it(tmp_path, monkeypatch):
    """§4.4's order, step 1 ahead of step 4. Run after the scan, `Readiness`'s
    `mirror`, `origin` and `default_branch` steps were unreachable from this
    command: the scan does those same three things unguarded and raises
    first, so `main` printed a traceback and no `batches` row existed at all
    for the night that was attempted — the outcome `run_batch`'s
    readiness-close was written to prevent."""
    home = tmp_path / "home"
    order: list[str] = []

    def _readiness(*_a, **_k):
        order.append("readiness")
        return preflight.Readiness(False, "mirror", "could not fetch")

    def _scan(*_a, **_k):
        order.append("scan")
        raise AssertionError("the scan ran despite readiness failing")

    monkeypatch.setattr(cli.preflight, "check_readiness", _readiness)
    monkeypatch.setattr(cli, "_resolve_queue", _scan)

    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2
    assert order == ["readiness"]


def test_readiness_still_runs_before_the_scan_it_now_feeds(tmp_path, monkeypatch):
    """The order is not traded away for the sharing: readiness still runs
    first, and what it found is exactly what `_resolve_queue` receives — the
    pinned base travels downward, from readiness into the scan, never
    upward."""
    home = tmp_path / "home"
    order: list[str] = []
    found = preflight.Readiness(
        True,
        mirror=Path("/tmp/pinned-mirror.git"),
        url="https://github.com/o/r.git",
        base_sha="b" * 40,
    )

    def _readiness(*_a, **_k):
        order.append("readiness")
        return found

    seen: dict = {}

    def _resolve(repo, home_arg, ledger, *, stamp_orphaned, pinned=None, stack=False):
        order.append("resolve")
        seen["pinned"] = pinned
        return _fake_batch_resolution(tmp_path)

    monkeypatch.setattr(cli.preflight, "check_readiness", _readiness)
    monkeypatch.setattr(cli, "_resolve_queue", _resolve)
    monkeypatch.setattr(cli, "run_batch", lambda *a, **k: "DRAINED")

    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 0

    assert order == ["readiness", "resolve"]
    pinned = seen["pinned"]
    assert pinned is not None
    assert pinned.mirror == found.mirror
    assert pinned.url == found.url
    assert pinned.base_sha == found.base_sha


def test_a_failed_readiness_still_scans_nothing(tmp_path, monkeypatch, capsys):
    """A readiness failure still means no scan at all — not a scan given a
    half-built base. The three derivation calls run once, for readiness, and
    `_resolve_queue` never runs at all."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-failed-readiness")
    home = tmp_path / "home"

    real_ensure = cli.git_mirror.ensure_mirror
    real_remote = cli.package_phase.real_remote
    counts = {"mirror": 0, "remote": 0, "fetch": 0}

    def _ensure(*a, **k):
        counts["mirror"] += 1
        return real_ensure(*a, **k)

    def _remote(*a, **k):
        counts["remote"] += 1
        return real_remote(*a, **k)

    def _fetch(*a, **k):
        counts["fetch"] += 1
        raise package.PackageError("no default branch could be fetched")

    monkeypatch.setattr(cli.git_mirror, "ensure_mirror", _ensure)
    monkeypatch.setattr(cli.package_phase, "real_remote", _remote)
    monkeypatch.setattr(cli.package_phase, "fetch_default_branch", _fetch)

    def _fake_check_readiness(repo_arg, mirror_path, *, scratch, home, token):
        mirror = cli.git_mirror.ensure_mirror(repo_arg, mirror_path)
        url = cli.package_phase.real_remote(repo_arg)
        try:
            cli.package_phase.fetch_default_branch(mirror, url)
        except package.PackageError as exc:
            return preflight.Readiness(False, "default_branch", str(exc))
        raise AssertionError("fetch_default_branch should have raised")

    monkeypatch.setattr(cli.preflight, "check_readiness", _fake_check_readiness)
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: pytest.fail("the scan ran")
    )
    # Not a scan given a half-built base: on a failed readiness, `_batch`
    # must not even build the `PinnedBase` it would otherwise share —
    # asserted by making its construction fail loudly if reached at all.
    monkeypatch.setattr(
        cli,
        "PinnedBase",
        lambda *a, **k: pytest.fail(
            "PinnedBase must not be built when readiness failed"
        ),
    )

    assert main(["--home", str(home), "batch", "--repo", str(repo)]) == 2
    assert counts == {"mirror": 1, "remote": 1, "fetch": 1}
    # The exit code alone does not distinguish "readiness stopped the night"
    # from "something raised on the way to the scan": deleting the `readiness
    # .ok` guard makes the narrowing assert below it raise, which `main` also
    # reports as 2, with the scan still unreached. Measured — without this
    # line the test survived the mutant of the property it names. The printed
    # reason is what says *which* stop happened, and it is also the only
    # account an operator gets at 7am.
    assert "readiness failed at default_branch" in capsys.readouterr().out


def test_a_night_pins_its_base_once(tmp_path, monkeypatch):
    """One night fetches the mirror once. `ensure_mirror`, `real_remote` and
    `fetch_default_branch` each run exactly once — the defect itself, and the
    only witness that measures it.

    Across `_batch` and the scan, with readiness stood in for: the stand-in
    makes the three calls the real `check_readiness` makes, so the readiness
    half of each count comes from the fake and the scan half comes from the
    production `_resolve_queue`. That is the half this spec can move —
    `saffron/preflight.py` is `forbidden` here — but it means a second
    derivation added *inside* `check_readiness` would not be seen. Said
    plainly rather than left as "end to end", which claimed more."""
    repo = _repo_with_spec(tmp_path, spec_text=_A_SPEC, dirname="repo-one-night")
    home = tmp_path / "home"

    real_ensure = cli.git_mirror.ensure_mirror
    real_remote = cli.package_phase.real_remote
    real_fetch = cli.package_phase.fetch_default_branch
    counts = {"mirror": 0, "remote": 0, "fetch": 0}

    def _ensure(*a, **k):
        counts["mirror"] += 1
        return real_ensure(*a, **k)

    def _remote(*a, **k):
        counts["remote"] += 1
        return real_remote(*a, **k)

    def _fetch(*a, **k):
        counts["fetch"] += 1
        return real_fetch(*a, **k)

    monkeypatch.setattr(cli.git_mirror, "ensure_mirror", _ensure)
    monkeypatch.setattr(cli.package_phase, "real_remote", _remote)
    monkeypatch.setattr(cli.package_phase, "fetch_default_branch", _fetch)

    def _fake_check_readiness(repo_arg, mirror_path, *, scratch, home, token):
        mirror = cli.git_mirror.ensure_mirror(repo_arg, mirror_path)
        url = cli.package_phase.real_remote(repo_arg)
        _, base_sha = cli.package_phase.fetch_default_branch(mirror, url)
        return preflight.Readiness(True, mirror=mirror, url=url, base_sha=base_sha)

    monkeypatch.setattr(cli.preflight, "check_readiness", _fake_check_readiness)
    monkeypatch.setattr(cli, "run_batch", lambda *a, **k: "DRAINED")

    assert main(["--home", str(home), "batch", "--repo", str(repo)]) == 0

    assert counts == {"mirror": 1, "remote": 1, "fetch": 1}


def test_an_unready_night_still_leaves_a_row_saying_it_was_attempted(
    tmp_path, monkeypatch, capsys
):
    """A readiness failure before the scan must still reach `run_batch`, which
    is what opens and closes the `batches` row. Otherwise the night that could
    not start is a night with no record it was tried."""
    home = tmp_path / "home"
    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(False, "auth", "token expired"),
    )
    monkeypatch.setattr(cli, "_resolve_queue", lambda *a, **k: pytest.fail("scanned"))

    ledger_path = home / "ledger.db"
    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2

    ledger = Ledger(ledger_path)
    row = ledger._db.execute(
        "SELECT status, ended_at FROM batches ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()
    ledger.close()
    assert row["status"] == "INFRASTRUCTURE"
    assert row["ended_at"] is not None
    assert "readiness failed at auth: token expired" in capsys.readouterr().out


def test_a_queue_discovery_refuses_still_leaves_a_closed_batch_row(
    tmp_path, monkeypatch
):
    """A spec directory `discover_specs` refuses — absent, or not a
    directory (`SA-0065`) — while readiness has already passed still leaves
    a `batches` row behind, closed `INFRASTRUCTURE`, and no task started.
    Before this, the `SpecError` reached `main`'s catch-all straight past
    `run_batch`, and no row existed at all for the night that was
    attempted."""
    home = tmp_path / "home"
    _readiness_passes(monkeypatch)

    def _raise(*a, **k):
        raise intake.SpecError("spec directory does not exist")

    monkeypatch.setattr(cli, "_resolve_queue", _raise)

    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2

    ledger = Ledger(home / "ledger.db")
    row = ledger._db.execute(
        "SELECT status, ended_at FROM batches ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()
    tasks = ledger._db.execute("SELECT task_id FROM tasks").fetchall()
    ledger.close()

    assert row["status"] == "INFRASTRUCTURE"
    assert row["ended_at"] is not None
    assert tasks == []


def test_any_raise_resolving_the_queue_still_closes_the_batch_row(
    tmp_path, monkeypatch
):
    """Not only a `SpecError`: resolving the queue is real work — a mirror
    fetch, a reconcile, a `git archive` — and any exception it raises, after
    readiness has already passed, must still reach the same close. A
    `SpecError` from discovery is only the case that was measured."""
    home = tmp_path / "home"
    _readiness_passes(monkeypatch)

    def _raise(*a, **k):
        raise RuntimeError("the mirror could not be fetched mid-scan")

    monkeypatch.setattr(cli, "_resolve_queue", _raise)

    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2

    ledger = Ledger(home / "ledger.db")
    row = ledger._db.execute(
        "SELECT status, ended_at FROM batches ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()
    tasks = ledger._db.execute("SELECT task_id FROM tasks").fetchall()
    ledger.close()

    assert row["status"] == "INFRASTRUCTURE"
    assert row["ended_at"] is not None
    assert tasks == []


def test_a_queue_that_cannot_be_resolved_says_so_on_the_batch_line(
    tmp_path, monkeypatch, capsys
):
    """The printed line must say resolution failed, carrying the
    exception's own text — and must not say readiness failed, since
    readiness passed. A line naming the wrong step sends the operator to
    re-check a token and a mirror that were fine."""
    home = tmp_path / "home"
    _readiness_passes(monkeypatch)

    def _raise(*a, **k):
        raise RuntimeError("spec directory /nowhere does not exist")

    monkeypatch.setattr(cli, "_resolve_queue", _raise)

    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2

    printed = capsys.readouterr().out
    batch_lines = [line for line in printed.splitlines() if line.startswith("batch:")]
    assert batch_lines, printed
    assert any("spec directory /nowhere does not exist" in line for line in batch_lines)
    assert "readiness failed" not in printed


def test_a_raise_from_the_loop_itself_is_not_blamed_on_the_queue(
    tmp_path, monkeypatch, capsys
):
    """The queue resolved; `run_batch` is what raised. That must reach `main`'s
    catch-all as itself, not be relabelled "the queue could not be resolved"
    — a line naming the wrong step is what the resolution line exists to stop."""
    home = tmp_path / "home"
    _readiness_passes(monkeypatch)
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")

    def _raise(*a, **k):
        raise RuntimeError("the ledger went away mid-night")

    monkeypatch.setattr(cli, "run_batch", _raise)

    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2

    printed = capsys.readouterr().out
    assert "saffron: RuntimeError: the ledger went away mid-night" in printed
    assert "could not be resolved" not in printed


def test_a_ledger_failure_after_a_failed_scan_is_not_blamed_on_the_queue(
    tmp_path, monkeypatch, capsys
):
    """The scan raised, then `create_batch` raised before the row existed. The
    line must name the ledger's failure, not send the operator to the specs."""
    home = tmp_path / "home"
    _readiness_passes(monkeypatch)

    def _scan(*a, **k):
        raise intake.SpecError("spec directory does not exist")

    def _create(*a, **k):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(cli, "_resolve_queue", _scan)
    monkeypatch.setattr(Ledger, "create_batch", _create)

    assert main(["--home", str(home), "batch", "--repo", str(tmp_path)]) == 2

    printed = capsys.readouterr().out
    assert "saffron: RuntimeError: database is locked" in printed
    assert "could not be resolved" not in printed


def test_a_night_names_the_specs_its_scan_refused(tmp_path, monkeypatch, capsys):
    """`saffron queue` prints refusals; this printed only the gaps, so a spec
    refused at gate 0 — a dead `depends_on` parent, protected `touches`, a
    dangling `saffron:retired-by` marker — vanished with no line in the log
    and no ledger row. "An empty queue" and "three specs all refused" produced
    byte-identical output at 7am."""
    resolved = cli.QueueResolution(
        repo_id=1,
        mirror=tmp_path / "m.git",
        base_sha="a" * 40,
        repo_slug="jtmcn/saffron",
        exported=tmp_path,
        candidates=[],
        refusals=[
            Refusal(
                path=tmp_path / "SY-7.md",
                reason="depends_on SY-9000 is unknown",
                kind="depends_on",
            )
        ],
        reconciled=cli.ReconcileResult(),
        gh_failures=[],
        policy_unread=[],
    )
    _readiness_passes(monkeypatch)
    monkeypatch.setattr(cli, "_resolve_queue", lambda *a, **k: resolved)
    monkeypatch.setattr(cli.package_phase, "real_remote", lambda _repo: "u")
    monkeypatch.setattr(cli, "_batch_runner", lambda *a, **k: lambda _c: None)
    monkeypatch.setattr(cli, "run_batch", lambda *a, **k: "DRAINED")

    args = argparse.Namespace(
        repo=tmp_path, home=tmp_path / "home", budget=50.0, until=None, stack=False
    )
    ledger = Ledger(tmp_path / "l.db")
    assert cli._batch(args, ledger, tmp_path / "out") == 0
    ledger.close()

    printed = capsys.readouterr().out
    assert "refusals: 1" in printed
    assert "depends_on SY-9000 is unknown" in printed


def test_a_night_says_what_it_set_out_to_do_before_what_became_of_it(
    tmp_path, monkeypatch, capsys
):
    """The unattended twin of `_run_cell`'s `ceilings:` line. Without it the
    log's first word about the night is its last."""
    _readiness_passes(monkeypatch)
    monkeypatch.setattr(
        cli,
        "_resolve_queue",
        lambda *a, **k: _fake_batch_resolution(tmp_path),
    )
    monkeypatch.setattr(cli.package_phase, "real_remote", lambda _repo: "u")
    monkeypatch.setattr(cli, "_batch_runner", lambda *a, **k: lambda _c: None)
    monkeypatch.setattr(cli, "run_batch", lambda *a, **k: "DRAINED")

    args = argparse.Namespace(
        repo=tmp_path,
        home=tmp_path / "home",
        budget=25.0,
        until=None,
        stack=False,
    )
    ledger = Ledger(tmp_path / "l.db")
    assert cli._batch(args, ledger, tmp_path / "out") == 0
    ledger.close()

    printed = capsys.readouterr().out
    assert "budget $25.00" in printed
    assert "until none" in printed


def test_the_printed_night_is_unchanged_by_sharing_the_base(
    tmp_path, monkeypatch, capsys
):
    """`saffron batch` prints exactly what it printed before — the plan
    header, the reconcile summary, the refusals and the scan gaps. The
    night's log is its only human-readable record, so a refactor that
    quietly drops a line from it is not a refactor."""
    refusal_path = tmp_path / "SY-7.md"
    resolved = cli.QueueResolution(
        repo_id=1,
        mirror=tmp_path / "m.git",
        base_sha="a" * 40,
        repo_slug="o/r",
        exported=tmp_path,
        candidates=[
            Candidate(
                path=Path("SY-1.md"),
                spec=intake.Spec(
                    id="SY-1", title="t", type="chore", touches=["src/**"]
                ),
                spec_sha="s" * 64,
                task_id=None,
            )
        ],
        refusals=[
            Refusal(
                path=refusal_path,
                reason="depends_on SY-9000 is unknown",
                kind="depends_on",
            )
        ],
        reconciled=cli.ReconcileResult(merged=[3]),
        gh_failures=["gh: command not found"],
        policy_unread=["policy.yaml: no such file"],
    )
    _readiness_passes(monkeypatch)
    monkeypatch.setattr(cli, "_resolve_queue", lambda *a, **k: resolved)
    monkeypatch.setattr(cli, "_batch_runner", lambda *a, **k: lambda _c: None)
    monkeypatch.setattr(cli, "run_batch", lambda *a, **k: "DRAINED")

    args = argparse.Namespace(
        repo=tmp_path, home=tmp_path / "home", budget=50.0, until=None, stack=False
    )
    ledger = Ledger(tmp_path / "l.db")
    assert cli._batch(args, ledger, tmp_path / "out") == 0
    ledger.close()

    printed = capsys.readouterr().out
    assert printed == (
        "reconcile: task 3 → MERGED\n"
        "batch: 1 candidate(s), budget $50.00, until none\n"
        f"  {'SY-1':<10} priority=3\n"
        "refusals: 1\n"
        f"  {refusal_path}: depends_on SY-9000 is unknown\n"
        "note: gh could not be run (gh: command not found) — the "
        "open-pull-request and touches-overlap refusals did not run, so the "
        "refusal list above is incomplete\n"
        "note: policy.yaml at this base_sha could not be read — no spec "
        "was checked against the protected list, so the refusal list "
        "above is incomplete\n"
        "batch: DRAINED\n"
    )


@pytest.mark.parametrize("value", ["6:30pm", "06:30:00", "0630", "", "25:00", "06:99"])
def test_a_malformed_until_is_a_usage_error_not_an_infrastructure_failure(value):
    """These all reached `_resolve_until` and died in `int()`, which `main`
    reports as exit 2 — "infrastructure failed" — for an operator's typo. The
    empty string was worse: falsy, so `--until ""` silently meant no deadline
    at all, turning an eight-hour night unbounded. Reachable from a shell
    variable that went unset in the plist."""
    with pytest.raises(SystemExit) as exit_info:
        main(["batch", "--until", value])
    assert exit_info.value.code == 2  # argparse's usage exit, not main's catch-all


@pytest.mark.parametrize("value", ["-50", "0"])
def test_a_budget_that_can_buy_nothing_is_refused(value):
    """`--budget -50` opened a `batches` row, stopped at `BUDGET` immediately,
    printed `batch: BUDGET` and exited 0 — a night that ran nothing and
    reported success."""
    with pytest.raises(SystemExit):
        main(["batch", "--budget", value])


def test_the_stack_mint_opens_a_run_at_the_pinned_base_and_a_task_per_call(tmp_path):
    """`cli._stack_mint` mints a fresh run and task on every call, at the
    pinned base, whatever `task_id` the candidate already carries. The
    repo row is upserted at the pinned url, and an older task's run and
    state are left alone."""
    ledger = Ledger(tmp_path / "l.db")
    # Another repo first, so the upserted one's id is not 1.
    ledger.upsert_repo("other", "https://github.com/o/other.git", "/other.git", None)
    repo_id = ledger.upsert_repo(
        "old", "https://github.com/o/r.git", "/old.git", policy_sha="p" * 64
    )
    older_run = ledger.create_run(repo_id, "e" * 40)
    older_task = ledger.create_task(older_run, "SY-1", "s" * 64, "saffron/SY-1")
    ledger.set_task_state(older_task, "RATE_LIMITED")

    pinned = task.PinnedBase(
        mirror=tmp_path / "m.git", url="https://github.com/o/r.git", base_sha="a" * 40
    )
    mint = cli._stack_mint(pinned=pinned, repo=tmp_path / "checkout", ledger=ledger)

    sy1 = intake.Spec(
        id="SY-1", title="t", type="chore", budget_usd=7.5, risk="elevated"
    )
    sy2 = intake.Spec(id="SY-2", title="t", type="chore")

    def _candidate(spec, task_id):
        return Candidate(
            path=Path(f"{spec.id}.md"), spec=spec, spec_sha="c" * 64, task_id=task_id
        )

    minted_1 = mint(_candidate(sy1, older_task))
    minted_2 = mint(_candidate(sy1, None))
    minted_3 = mint(_candidate(sy2, None))

    assert len({minted_1, minted_2, minted_3}) == 3
    assert older_task not in {minted_1, minted_2, minted_3}

    def _row(task_id):
        return ledger._db.execute(
            "SELECT t.spec_id, t.spec_sha, t.branch, t.state, t.risk, "
            "t.budget_usd, t.policy_sha, t.prompt_sha, t.run_id, "
            "r.base_sha, r.batch_id, r.repo_id FROM tasks t "
            "JOIN runs r ON r.run_id = t.run_id WHERE t.task_id = ?",
            (task_id,),
        ).fetchone()

    row1, row2, row3 = _row(minted_1), _row(minted_2), _row(minted_3)
    for row, spec_id in ((row1, "SY-1"), (row2, "SY-1"), (row3, "SY-2")):
        assert row["spec_id"] == spec_id
        assert row["spec_sha"] == "c" * 64
        assert row["branch"] == f"saffron/{spec_id}"
        assert row["state"] == "QUEUED"
        assert row["policy_sha"] is None
        assert row["prompt_sha"] == context.prompt_sha()
        assert row["base_sha"] == "a" * 40
        assert row["batch_id"] is None
        assert row["repo_id"] == repo_id
    assert row1["budget_usd"] == 7.5 and row1["risk"] == "elevated"
    assert row2["budget_usd"] == 7.5 and row2["risk"] == "elevated"
    assert row3["budget_usd"] == 12.0 and row3["risk"] == "standard"
    assert row1["run_id"] != row2["run_id"]

    older_row = ledger._db.execute(
        "SELECT state, run_id FROM tasks WHERE task_id = ?", (older_task,)
    ).fetchone()
    assert older_row["state"] == "RATE_LIMITED"
    assert older_row["run_id"] == older_run

    repo_row = ledger._db.execute(
        "SELECT name, mirror_path, policy_sha FROM repos WHERE repo_id = ?",
        (repo_id,),
    ).fetchone()
    assert repo_row["name"] == "checkout"
    assert repo_row["mirror_path"] == str(pinned.mirror)
    assert repo_row["policy_sha"] == "p" * 64
    ledger.close()

    fresh_ledger = Ledger(tmp_path / "l2.db")
    fresh_mint = cli._stack_mint(
        pinned=pinned, repo=tmp_path / "checkout2", ledger=fresh_ledger
    )
    fresh_task = fresh_mint(_candidate(sy1, None))
    fresh_row = fresh_ledger._db.execute(
        "SELECT r.repo_id FROM tasks t JOIN runs r ON r.run_id = t.run_id "
        "WHERE t.task_id = ?",
        (fresh_task,),
    ).fetchone()
    fresh_repo = fresh_ledger._db.execute(
        "SELECT origin, policy_sha FROM repos WHERE repo_id = ?",
        (fresh_row["repo_id"],),
    ).fetchone()
    assert fresh_repo["origin"] == pinned.url
    assert fresh_repo["policy_sha"] is None
    fresh_ledger.close()


def test_a_spec_review_fills_cores_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head(
    tmp_path, monkeypatch
):
    """`cli._stack_review` seeds its cell at a layer's fetched head, or at
    the pinned `base_sha` with no layer. It always reads its prompt and
    gates from the pinned `base_sha`'s own export, never a layer's head,
    the operator's checkout, or the mirror's `HEAD`."""
    rig = _spec_session_rig(tmp_path, monkeypatch)
    mirror, bare_sha, base_sha = rig.mirror, rig.bare_sha, rig.base_sha
    repo, out_dir, _candidate = rig.repo, rig.out_dir, rig.candidate
    fetch_calls, cell_up_calls = rig.fetch_calls, rig.cell_up_calls
    cell_down_calls, unpriv_calls = rig.cell_down_calls, rig.unpriv_calls
    layer_cell_calls = rig.layer_cell_calls

    agent_calls: list[dict] = []

    def _fake_run_agent(
        container,
        *,
        prompt,
        options,
        spec_id,
        timeout_s,
        resume=None,
        emit=None,
        last_cost_usd=0.0,
    ):
        agent_calls.append({"spec_id": spec_id, "timeout_s": timeout_s})
        return implement.AttemptResult(
            session_id="sid",
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=0.0,
            rate_limit_status="rejected",
        )

    monkeypatch.setattr(implement, "run_agent", _fake_run_agent)

    review_calls: list[dict] = []
    sentinels: list[object] = []

    def _fake_run_spec_review(container, *, system_prompt, prompt, agent):
        agent(container, prompt="x", options={})
        sentinel = object()
        sentinels.append(sentinel)
        review_calls.append(
            {"container": container, "system_prompt": system_prompt, "prompt": prompt}
        )
        return sentinel

    monkeypatch.setattr(spec_review, "run_spec_review", _fake_run_spec_review)

    pinned = task.PinnedBase(
        mirror=mirror, url="https://github.com/o/r.git", base_sha=base_sha
    )
    review = cli._stack_review(pinned=pinned, repo=repo, out_dir=out_dir)

    assert not (out_dir / "spec-review").exists()

    sy1 = _candidate("SY-1")
    sy2 = _candidate("SY-2", depends_on=["SY-9"])
    layer7 = _candidate("SY-7")
    layer8 = _candidate("SY-8")

    result1 = review(sy1, None)
    result2 = review(sy2, layer7)
    with pytest.raises(package.ParentGone):
        review(_candidate("SY-3"), layer8)

    assert result1 is sentinels[0]
    assert result2 is sentinels[1]

    assert fetch_calls == [
        (mirror, pinned.url, "saffron/SY-7"),
        (mirror, pinned.url, "saffron/SY-8"),
    ]

    assert len(cell_up_calls) == 2
    assert len(cell_down_calls) == 2
    assert [c["tree_base"] for c in cell_up_calls] == [base_sha, "d" * 40]
    for c in cell_up_calls:
        assert c["repo"] == repo
        assert c["mirror"] == mirror
        assert c["thread_env"] == {"X": "base"}
        assert c["cap_add"] == implement.UNPRIVILEGED_BASH_CAPS
    assert cell_up_calls[0]["gates_dir"] == out_dir / "spec-review" / "SY-1"
    assert cell_up_calls[1]["gates_dir"] == out_dir / "spec-review" / "SY-2"
    for c in cell_up_calls:
        policy_text = (c["gates_dir"] / ".saffron" / "policy.yaml").read_text()
        assert "X: base" in policy_text

    assert len(unpriv_calls) == 2
    assert unpriv_calls == [c["container"] for c in cell_up_calls]

    assert len(layer_cell_calls) == 2
    assert all(call["kwargs"]["spec_session"] is True for call in layer_cell_calls)
    assert [call["fields"].branch for call in layer_cell_calls] == [
        "saffron/SY-1",
        "saffron/SY-2",
    ]

    assert len(review_calls) == 2
    for i, spec_id in enumerate(("SY-1", "SY-2")):
        exported = out_dir / "spec-review" / spec_id
        policy, _ = load_policy(exported)
        expected_prompt = spec_review.spec_review_system_prompt(
            policy, prompts_dir=context.PROMPTS_DIR
        )
        assert review_calls[i]["system_prompt"] == expected_prompt
        assert "`base/**`" in expected_prompt
        assert "head/**" not in expected_prompt
        assert "checkout/**" not in expected_prompt
        prompt = review_calls[i]["prompt"]
        assert f".saffron/specs/{spec_id}-x.md" in prompt
        # The seeded tree, not the pinned `base_sha`. The two differ for
        # SY-2, whose layer's fetched head is `"d" * 40`.
        assert f"base: {cell_up_calls[i]['tree_base']}" in prompt
        assert "is a snapshot of the base" in prompt
        assert str(tmp_path) not in prompt
        for banned in ("/opt/", "pytest", "uv run", "make check", ".claude", "://"):
            assert banned not in prompt
        for line in (
            "Your Bash runs as an account that can read /work but cannot write it.",
            "To run anything that writes, clone the tree first: "
            "git clone -q /work /tmp/w && cd /tmp/w",
            "Call a tool by its full path when its name does not resolve.",
        ):
            assert line in prompt.splitlines()
        assert review_calls[i]["container"] == cell_up_calls[i]["container"]

    assert len(agent_calls) == 2
    assert [c["spec_id"] for c in agent_calls] == ["SY-1", "SY-2"]
    assert spec_review.SPEC_REVIEW_TIMEOUT_S == 1800
    assert all(c["timeout_s"] == spec_review.SPEC_REVIEW_TIMEOUT_S for c in agent_calls)

    pinned_bare = task.PinnedBase(
        mirror=mirror, url="https://github.com/o/r.git", base_sha=bare_sha
    )
    review_bare = cli._stack_review(pinned=pinned_bare, repo=repo, out_dir=out_dir)
    review_bare(_candidate("SY-4"), None)

    expected_bare_prompt = spec_review.spec_review_system_prompt(
        Policy(), prompts_dir=context.PROMPTS_DIR
    )
    assert review_calls[-1]["system_prompt"] == expected_bare_prompt
    assert cell_up_calls[-1]["thread_env"] == {}


def _spec_session_rig(tmp_path, monkeypatch, spec_file=None):
    """The mirror, checkout and cell fakes a spec session callable runs over:
    `bare`, `base` and `head` commits, and a spy on `layer_cell`."""
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    _git(mirror, "init", "-q")
    (mirror / ".saffron").mkdir()
    (mirror / ".saffron" / "README").write_text("bare\n")
    _git(mirror, "add", "-A")
    _git(mirror, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "bare")
    bare_sha = _rev_parse(mirror, "HEAD")

    (mirror / ".saffron" / "policy.yaml").write_text(
        "gates: {}\nthread_env:\n  X: base\nprotected:\n  - base/**\n"
    )
    # A named spec file differs in all three trees, so a read shows which.
    if spec_file:
        (mirror / spec_file).parent.mkdir(parents=True, exist_ok=True)
        (mirror / spec_file).write_text("queued at base\n")
    _git(mirror, "add", "-A")
    _git(mirror, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "base")
    base_sha = _rev_parse(mirror, "HEAD")

    (mirror / ".saffron" / "policy.yaml").write_text(
        "gates: {}\nthread_env:\n  X: head\nprotected:\n  - head/**\n"
    )
    if spec_file:
        (mirror / spec_file).write_text("at head\n")
    _git(mirror, "add", "-A")
    _git(mirror, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "head")

    repo = tmp_path / "checkout"
    (repo / ".saffron").mkdir(parents=True)
    (repo / ".saffron" / "policy.yaml").write_text(
        "gates: {}\nthread_env:\n  X: checkout\nprotected:\n  - checkout/**\n"
    )
    if spec_file:
        (repo / spec_file).parent.mkdir(parents=True, exist_ok=True)
        (repo / spec_file).write_text("in the checkout\n")

    out_dir = tmp_path / "out"

    fetch_calls: list[tuple] = []

    def _fake_fetch(mirror_arg, url_arg, branch):
        fetch_calls.append((mirror_arg, url_arg, branch))
        if branch == "saffron/SY-8":
            raise package.ParentGone("gone")
        return "d" * 40

    monkeypatch.setattr(package, "fetch_parent_branch", _fake_fetch)

    cell_up_calls: list[dict] = []

    def _fake_cell_up(
        *,
        repo,
        mirror,
        tree_base,
        branch,
        network,
        critic_network,
        volume,
        state,
        container,
        gates_dir,
        thread_env,
        created,
        note,
        cap_add=None,
    ):
        cell_up_calls.append(
            {
                "repo": repo,
                "mirror": mirror,
                "tree_base": tree_base,
                "branch": branch,
                "gates_dir": gates_dir,
                "thread_env": dict(thread_env),
                "container": container,
                "cap_add": cap_add,
            }
        )
        created.add(container)
        note("cell_up", "cell up")

    cell_down_calls: list[dict] = []

    def _fake_cell_down(
        *, network, critic_network, volume, state, container, created, note
    ):
        cell_down_calls.append({"container": container})
        note("cell_down", True, "cell down")

    monkeypatch.setattr(session, "cell_up", _fake_cell_up)
    monkeypatch.setattr(session, "cell_down", _fake_cell_down)
    monkeypatch.setattr(cli.runtime, "remove_container", lambda _container: None)

    unpriv_calls: list[str] = []
    monkeypatch.setattr(
        session,
        "assert_bash_is_unprivileged",
        lambda container: unpriv_calls.append(container),
    )

    real_layer_cell = end_review.layer_cell
    layer_cell_calls: list[dict] = []

    @contextmanager
    def _spy_layer_cell(fields, **kwargs):
        layer_cell_calls.append({"fields": fields, "kwargs": kwargs})
        with real_layer_cell(fields, **kwargs) as container:
            yield container

    monkeypatch.setattr(end_review, "layer_cell", _spy_layer_cell)

    def _spec_path(spec_id):
        return tmp_path / "export" / ".saffron" / "specs" / f"{spec_id}-x.md"

    def _candidate(spec_id, *, depends_on=None):
        return Candidate(
            path=_spec_path(spec_id),
            spec=intake.Spec(
                id=spec_id, title="t", type="chore", depends_on=depends_on or []
            ),
            spec_sha="s" * 64,
            task_id=None,
        )

    return SimpleNamespace(
        mirror=mirror,
        bare_sha=bare_sha,
        base_sha=base_sha,
        repo=repo,
        out_dir=out_dir,
        fetch_calls=fetch_calls,
        cell_up_calls=cell_up_calls,
        cell_down_calls=cell_down_calls,
        unpriv_calls=unpriv_calls,
        layer_cell_calls=layer_cell_calls,
        candidate=_candidate,
    )


def test_a_spec_revision_fills_cores_writer_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head(
    tmp_path, monkeypatch
):
    """`cli._stack_revise` seeds its cell at a layer's fetched head, or at
    the pinned `base_sha` with no layer. It always reads its prompt and
    gates from the pinned `base_sha`'s own export, never a layer's head,
    the operator's checkout, or the mirror's `HEAD`."""
    from saffron.agents.artifacts import hash_artifact

    rig = _spec_session_rig(tmp_path, monkeypatch)
    mirror, bare_sha, base_sha = rig.mirror, rig.bare_sha, rig.base_sha
    repo, out_dir, _candidate = rig.repo, rig.out_dir, rig.candidate
    fetch_calls, cell_up_calls = rig.fetch_calls, rig.cell_up_calls
    cell_down_calls, unpriv_calls = rig.cell_down_calls, rig.unpriv_calls
    layer_cell_calls = rig.layer_cell_calls

    def _turn(text="t", **fields):
        # Unannotated like test_spec_review's `_attempt`, so a str reset type-checks.
        return implement.AttemptResult(
            subtype="success", terminal_reason=None, text=text, **fields
        )

    agent_calls: list[dict] = []

    def _fake_run_agent(
        container,
        *,
        prompt,
        options,
        spec_id,
        timeout_s,
        resume=None,
        emit=None,
        last_cost_usd=0.0,
    ):
        agent_calls.append(
            {
                "container": container,
                "prompt": prompt,
                "options": options,
                "spec_id": spec_id,
                "timeout_s": timeout_s,
                "resume": resume,
                "last_cost_usd": last_cost_usd,
            }
        )
        if spec_id == "SY-2":
            return _turn(
                session_id="s-2",
                num_turns=1,
                cost_usd_est=0.25,
                rate_limit_status="rejected",
                rate_limit_resets_at="soon",
            )
        if resume is not None:
            return _turn(
                session_id="s-1",
                num_turns=1,
                cost_usd_est=0.25,
                structured_output={"spec": "---\nid: SY-1\n---\nrevised"},
            )
        return _turn(session_id="s-1", num_turns=7, cost_usd_est=0.5, text="report")

    monkeypatch.setattr(implement, "run_agent", _fake_run_agent)

    pinned = task.PinnedBase(
        mirror=mirror, url="https://github.com/o/r.git", base_sha=base_sha
    )
    revise = cli._stack_revise(pinned=pinned, repo=repo, out_dir=out_dir)

    assert not (out_dir / "spec-write").exists()

    sy1 = _candidate("SY-1")
    sy2 = _candidate("SY-2", depends_on=["SY-9"])
    layer7 = _candidate("SY-7")
    layer8 = _candidate("SY-8")

    result1 = revise(sy1, None, "spec one\n", "review one")
    result2 = revise(sy2, layer7, "spec two\n", "review two")
    with pytest.raises(package.ParentGone):
        revise(_candidate("SY-3"), layer8, "spec three\n", "review three")

    revised_text = "---\nid: SY-1\n---\nrevised\n"
    assert result1 == spec_review.SpecWriterSession(
        text=revised_text,
        cost_usd=0.75,
        error=None,
        resets_at=None,
        session_id="s-1",
        num_turns=8,
        spec_sha=hash_artifact(revised_text),
    )
    assert result2.text == ""
    assert result2.error is None
    assert result2.resets_at == 1
    assert result2.cost_usd == 0.25

    assert fetch_calls == [
        (mirror, pinned.url, "saffron/SY-7"),
        (mirror, pinned.url, "saffron/SY-8"),
    ]

    assert len(cell_up_calls) == 2
    assert len(cell_down_calls) == 2
    assert [c["tree_base"] for c in cell_up_calls] == [base_sha, "d" * 40]
    for c in cell_up_calls:
        assert c["repo"] == repo
        assert c["mirror"] == mirror
        assert c["thread_env"] == {"X": "base"}
    assert cell_up_calls[0]["gates_dir"] == out_dir / "spec-write" / "SY-1"
    assert cell_up_calls[1]["gates_dir"] == out_dir / "spec-write" / "SY-2"
    for c in cell_up_calls:
        policy_text = (c["gates_dir"] / ".saffron" / "policy.yaml").read_text()
        assert "X: base" in policy_text

    assert len(unpriv_calls) == 2
    assert unpriv_calls == [c["container"] for c in cell_up_calls]

    assert len(layer_cell_calls) == 2
    assert all(call["kwargs"]["spec_session"] is True for call in layer_cell_calls)
    assert [call["fields"].branch for call in layer_cell_calls] == [
        "saffron/SY-1",
        "saffron/SY-2",
    ]

    assert len(agent_calls) == 3
    assert [c["spec_id"] for c in agent_calls] == ["SY-1", "SY-1", "SY-2"]
    assert spec_review.SPEC_WRITER_TIMEOUT_S == 3600
    assert all(c["timeout_s"] == spec_review.SPEC_WRITER_TIMEOUT_S for c in agent_calls)
    assert agent_calls[0]["container"] == cell_up_calls[0]["container"]
    assert agent_calls[1]["container"] == cell_up_calls[0]["container"]
    assert agent_calls[2]["container"] == cell_up_calls[1]["container"]

    assert agent_calls[1]["resume"] == "s-1"
    assert agent_calls[1]["last_cost_usd"] == 0.5
    assert agent_calls[1]["prompt"] == spec_review.SPEC_WRITER_EXTRACT_PROMPT
    assert agent_calls[1]["options"]["output_format"] == spec_review.SPEC_WRITER_FORMAT
    assert agent_calls[0]["resume"] is None
    assert agent_calls[2]["resume"] is None

    for spec_id in ("SY-1", "SY-2"):
        exported = out_dir / "spec-write" / spec_id
        policy, _ = load_policy(exported)
        expected_prompt = spec_review.spec_writer_system_prompt(
            policy, prompts_dir=context.PROMPTS_DIR
        )
        first_call = agent_calls[0] if spec_id == "SY-1" else agent_calls[2]
        assert first_call["options"]["system_prompt"] == expected_prompt
        assert "`base/**`" in expected_prompt
        assert "head/**" not in expected_prompt
        assert "checkout/**" not in expected_prompt
        prompt = first_call["prompt"]
        review_text = "review one" if spec_id == "SY-1" else "review two"
        spec_text = "spec one\n" if spec_id == "SY-1" else "spec two\n"
        tree = base_sha if spec_id == "SY-1" else "d" * 40
        expected_lines = [
            "review: the spec review between the review tags below.",
            f"spec: .saffron/specs/{spec_id}-x.md",
            f"base: {tree}",
            "The checkout is a snapshot of the base.",
            "The text between the spec tags below is the spec's current "
            "text, and it replaces the file at that path.",
            "Keep the spec's id and its exact depends_on.",
            "Raise no budget_usd, max_turns or max_attempts.",
            "A follow-up's revision keeps its touches within its first text's touches.",
        ]
        assert prompt.splitlines()[:8] == expected_lines
        assert prompt.index("<review>") < prompt.index(review_text)
        assert prompt.index(review_text) < prompt.index("</review>")
        assert prompt.index("</review>") < prompt.index("<spec>")
        assert prompt.index("<spec>") < prompt.index(spec_text)
        assert prompt.index(spec_text) < prompt.index("</spec>")
        assert str(tmp_path) not in prompt

    pinned_bare = task.PinnedBase(
        mirror=mirror, url="https://github.com/o/r.git", base_sha=bare_sha
    )
    revise_bare = cli._stack_revise(pinned=pinned_bare, repo=repo, out_dir=out_dir)
    revise_bare(_candidate("SY-4"), None, "spec four\n", "review four")

    expected_bare_prompt = spec_review.spec_writer_system_prompt(
        Policy(), prompts_dir=context.PROMPTS_DIR
    )
    assert agent_calls[-1]["options"]["system_prompt"] == expected_bare_prompt
    assert cell_up_calls[-1]["thread_env"] == {}


def test_a_stack_batch_wires_its_spec_review_and_mint_once_readiness_passes(
    tmp_path, monkeypatch
):
    """`saffron batch --stack` builds `cli._stack_review` and
    `cli._stack_mint` once each, only after readiness pins a base, and
    passes them to `run_stack_batch` as `review` and `mint`. Neither is
    built when readiness fails or `--stack` is absent."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")

    review_calls: list[dict] = []
    mint_calls: list[dict] = []
    review_sentinel = object()
    mint_sentinel = object()

    def _fake_stack_review(**kwargs):
        review_calls.append(kwargs)
        return review_sentinel

    def _fake_stack_mint(**kwargs):
        mint_calls.append(kwargs)
        return mint_sentinel

    monkeypatch.setattr(cli, "_stack_review", _fake_stack_review)
    monkeypatch.setattr(cli, "_stack_mint", _fake_stack_mint)
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )

    export_calls: list[tuple] = []

    def _fake_export(mirror, sha, dest):
        export_calls.append((mirror, sha, dest))
        return dest

    monkeypatch.setattr(cli.git_mirror, "export_saffron_dir", _fake_export)

    stack_batch_calls: list[dict] = []

    def _fake_run_stack_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        stack_batch_calls.append({"ledger": ledger, **kwargs})
        return "DRAINED"

    plain_batch_calls: list[dict] = []

    def _fake_run_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        plain_batch_calls.append({"ledger": ledger, **kwargs})
        return "DRAINED"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)
    monkeypatch.setattr(cli, "run_batch", _fake_run_batch)

    # Case 1: readiness passes, `--stack`.
    _readiness_passes(monkeypatch)
    home1 = tmp_path / "home1"
    assert main(["--home", str(home1), "batch", "--stack"]) == 0

    assert len(review_calls) == 1
    assert len(mint_calls) == 1
    pinned = task.PinnedBase(
        mirror=Path("/tmp/pinned-mirror.git"),
        url="https://github.com/o/r.git",
        base_sha="a" * 40,
    )
    assert review_calls[0]["pinned"] == pinned
    assert mint_calls[0]["pinned"] == pinned
    assert review_calls[0]["repo"] == tmp_path.resolve()
    assert mint_calls[0]["repo"] == tmp_path.resolve()
    assert review_calls[0]["out_dir"] == home1 / "batches" / "v0"
    assert len(stack_batch_calls) == 1
    assert stack_batch_calls[0]["ledger"] is mint_calls[0]["ledger"]
    assert stack_batch_calls[0]["review"] is review_sentinel
    assert stack_batch_calls[0]["mint"] is mint_sentinel
    assert export_calls == []
    assert plain_batch_calls == []

    # Case 2: readiness fails.
    review_calls.clear()
    mint_calls.clear()
    stack_batch_calls.clear()
    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(False, "auth", "token invalid"),
    )
    home2 = tmp_path / "home2"
    main(["--home", str(home2), "batch", "--stack"])

    assert review_calls == []
    assert mint_calls == []
    assert len(stack_batch_calls) == 1
    assert stack_batch_calls[0]["review"] is None
    assert stack_batch_calls[0]["mint"] is None

    # Case 3: `batch` without `--stack`.
    review_calls.clear()
    mint_calls.clear()
    plain_batch_calls.clear()
    _readiness_passes(monkeypatch)
    home3 = tmp_path / "home3"
    assert main(["--home", str(home3), "batch"]) == 0

    assert review_calls == []
    assert mint_calls == []
    assert len(plain_batch_calls) == 1


def test_a_stack_batch_passes_run_stack_batch_its_spec_revision(tmp_path, monkeypatch):
    """`saffron batch --stack` builds `cli._stack_revise` once, with the
    pinned base, the resolved `--repo` and `main`'s `out_dir`, and passes
    it to `run_stack_batch` as `revise`. Readiness failing builds none and
    passes `revise=None`, the way `_stack_review` and `_stack_mint` do."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")

    revise_calls: list[dict] = []
    revise_sentinel = object()

    def _fake_stack_revise(**kwargs):
        revise_calls.append(kwargs)
        return revise_sentinel

    monkeypatch.setattr(cli, "_stack_revise", _fake_stack_revise)
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )

    stack_batch_calls: list[dict] = []

    def _fake_run_stack_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        stack_batch_calls.append({"ledger": ledger, **kwargs})
        return "DRAINED"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)

    # Case 1: readiness passes, `--stack`.
    _readiness_passes(monkeypatch)
    home1 = tmp_path / "home1"
    assert main(["--home", str(home1), "batch", "--stack", "--repo", "."]) == 0

    assert len(revise_calls) == 1
    pinned = task.PinnedBase(
        mirror=Path("/tmp/pinned-mirror.git"),
        url="https://github.com/o/r.git",
        base_sha="a" * 40,
    )
    assert revise_calls[0]["pinned"] == pinned
    assert revise_calls[0]["repo"] == tmp_path.resolve()
    assert revise_calls[0]["out_dir"] == home1 / "batches" / "v0"
    assert len(stack_batch_calls) == 1
    assert stack_batch_calls[0]["revise"] is revise_sentinel

    # Case 2: readiness fails.
    revise_calls.clear()
    stack_batch_calls.clear()
    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(False, "auth", "token invalid"),
    )
    home2 = tmp_path / "home2"
    main(["--home", str(home2), "batch", "--stack"])

    assert revise_calls == []
    assert len(stack_batch_calls) == 1
    assert stack_batch_calls[0]["revise"] is None


def test_a_review_reads_a_recorded_text_and_a_revision_starts_from_the_queued_file(
    tmp_path, monkeypatch
):
    """`cli._stack_review`'s callable takes an optional keyword
    `spec_text`, adding it in `<spec>` tags beside a sentence naming a
    scope blocker. `cli._stack_revise`, handed `None`, reads
    `.saffron/specs/` at the pinned base through `git_mirror.file_at`,
    never a layer's head or the checkout. It raises `ValueError` before
    any cell for a path absent there."""
    rig = _spec_session_rig(tmp_path, monkeypatch, ".saffron/specs/SY-1-x.md")
    prompts: list[str] = []

    def _fake_run_agent(
        container,
        *,
        prompt,
        options,
        spec_id,
        timeout_s,
        resume=None,
        emit=None,
        last_cost_usd=0.0,
    ):
        prompts.append(prompt)
        if resume is None:
            structured = None
        elif options.get("output_format") is spec_review.SPEC_REVIEW_FORMAT:
            structured = {"findings": []}
        else:
            structured = {"spec": "ignored"}
        return implement.AttemptResult(
            subtype="success",
            terminal_reason=None,
            text="",
            session_id=f"s-{len(prompts)}",
            num_turns=1,
            cost_usd_est=0.1,
            is_error=False,
            bound="",
            rate_limit_status=None,
            rate_limit_resets_at=None,
            structured_output=structured,
        )

    monkeypatch.setattr(implement, "run_agent", _fake_run_agent)

    pinned = task.PinnedBase(
        mirror=rig.mirror, url="https://github.com/o/r.git", base_sha=rig.base_sha
    )
    review = cli._stack_review(pinned=pinned, repo=rig.repo, out_dir=rig.out_dir)
    revise = cli._stack_revise(pinned=pinned, repo=rig.repo, out_dir=rig.out_dir)

    sy1 = rig.candidate("SY-1")
    layer7 = rig.candidate("SY-7")
    sy5 = rig.candidate("SY-5")

    review(sy1, None)
    review(sy1, None, spec_text="revised\n")

    revise(sy1, None, None, "rt")
    revise(sy1, layer7, None, "rt")
    revise(sy1, None, "given\n", "rt")

    first_review_prompt, second_review_prompt = prompts[0], prompts[2]
    assert second_review_prompt.startswith(first_review_prompt)
    assert "<spec>\nrevised\n\n</spec>" in second_review_prompt
    assert "review that text" in second_review_prompt
    assert "scope blocker" in second_review_prompt
    assert "<spec>" not in first_review_prompt
    assert "review that text" not in first_review_prompt
    assert "scope blocker" not in first_review_prompt

    writer_prompts = [prompts[4], prompts[6], prompts[8]]
    for prompt in writer_prompts[:2]:
        assert "<spec>\nqueued at base\n\n</spec>" in prompt
    assert "<spec>\ngiven\n\n</spec>" in writer_prompts[2]
    for prompt in writer_prompts:
        assert "at head" not in prompt
        assert "in the checkout" not in prompt
        assert "None" not in prompt

    before = len(rig.cell_up_calls)
    with pytest.raises(ValueError, match=r"\.saffron/specs/SY-5-x\.md"):
        revise(sy5, None, None, "rt")
    assert len(rig.cell_up_calls) == before


def test_a_stack_batch_holds_the_writer_share_and_passes_its_follow_up_writer(
    tmp_path, monkeypatch, capsys
):
    """`saffron batch --stack --budget N` holds `N * follow_up.WRITER_SHARE`
    back for the spec writer, beside the reserve. It builds `_stack_follow_ups`
    once, only once readiness and the scan both pass, and passes it and
    `writer_usd` to `run_stack_batch`. Readiness failing builds no callable
    and still passes the same `writer_usd`."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(follow_up, "WRITER_SHARE", 0.125)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )

    sentinel = object()
    follow_ups_builds: list[dict] = []

    def _fake_stack_follow_ups(**kwargs):
        follow_ups_builds.append(kwargs)
        return sentinel

    monkeypatch.setattr(cli, "_stack_follow_ups", _fake_stack_follow_ups)

    run_stack_batch_calls: list[dict] = []

    def _fake_run_stack_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        run_stack_batch_calls.append(
            {"ledger": ledger, "budget_usd": budget_usd, **kwargs}
        )
        return "DRAINED"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)

    # Case 1: readiness passes.
    _readiness_passes(monkeypatch)
    home1 = tmp_path / "home1"
    assert main(["--home", str(home1), "batch", "--stack", "--budget", "42"]) == 0

    printed = capsys.readouterr().out
    assert "budget $42.00, reserve $10.50, writer $5.25, until none" in printed

    assert len(run_stack_batch_calls) == 1
    call = run_stack_batch_calls[0]
    assert call["budget_usd"] == 42.0
    assert call["reserve_usd"] == 10.5
    assert call["writer_usd"] == 5.25
    assert call["follow_ups"] is sentinel

    assert len(follow_ups_builds) == 1
    built = follow_ups_builds[0]
    pinned = task.PinnedBase(
        mirror=Path("/tmp/pinned-mirror.git"),
        url="https://github.com/o/r.git",
        base_sha="a" * 40,
    )
    assert built["pinned"] == pinned
    assert built["repo"] == tmp_path.resolve()
    assert built["ledger"] is call["ledger"]
    assert built["out_dir"] == home1 / "batches" / "v0"
    assert built["cap_usd"] == 5.25
    assert built["pooled"] == []

    # Case 2: readiness fails.
    follow_ups_builds.clear()
    run_stack_batch_calls.clear()
    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(False, "auth", "token invalid"),
    )
    home2 = tmp_path / "home2"
    main(["--home", str(home2), "batch", "--stack", "--budget", "42"])

    assert follow_ups_builds == []
    assert len(run_stack_batch_calls) == 1
    assert run_stack_batch_calls[0]["follow_ups"] is None
    assert run_stack_batch_calls[0]["writer_usd"] == 5.25


_SA0162_PR = {
    "number": 1,
    "headRefName": "saffron/SY-1",
    "url": "https://example.invalid/pull/1",
    "files": [],
}


def test_a_stack_batch_reads_the_open_pull_requests_a_follow_up_meets(
    tmp_path, monkeypatch, capsys
):
    """`saffron batch --stack` passes `run_stack_batch` an `open_prs`
    callable once readiness passed and the queue resolved, and `None`
    where readiness failed. The callable reads nothing until it is called.
    Called, it returns `scheduler._open_prs` of the resolved slug, through
    `_guarded_gh`, so a `gh` that cannot start reads as no open pull
    request. With no slug it returns an empty list and runs no `gh`. Either
    way it prints the `note:` line `_print_skipped` prints, with
    `_GH_REFUSALS_SKIPPED`, as `_print_scan_gaps` does for the plan."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")

    run_stack_batch_calls: list[dict] = []

    def _fake_run_stack_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        run_stack_batch_calls.append(kwargs)
        return "DRAINED"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)

    gh_calls: list[list[str]] = []

    def _fake_run_gh(argv):
        gh_calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps([_SA0162_PR]), "")

    def _raising_gh(argv):
        raise OSError("no gh")

    # Case 1: slug `o/r`, a working `gh`.
    _readiness_passes(monkeypatch)
    monkeypatch.setattr(
        cli,
        "_resolve_queue",
        lambda *a, **k: replace(_fake_batch_resolution(tmp_path), repo_slug="o/r"),
    )
    monkeypatch.setattr("saffron.cli.run_gh", _fake_run_gh)
    home1 = tmp_path / "home1"
    assert main(["--home", str(home1), "batch", "--stack", "--budget", "40"]) == 0
    capsys.readouterr()

    assert len(run_stack_batch_calls) == 1
    open_prs1 = run_stack_batch_calls[0]["open_prs"]
    assert gh_calls == []  # nothing read until the callable itself is called
    result1 = open_prs1()
    assert result1 == [_SA0162_PR]
    assert len(gh_calls) == 1
    argv1 = gh_calls[0]
    assert argv1[argv1.index("--repo") + 1] == "o/r"
    out1 = capsys.readouterr().out
    assert "note:" not in out1

    # Case 2: slug `o/r`, `cli.run_gh` cannot start.
    run_stack_batch_calls.clear()
    gh_calls.clear()
    monkeypatch.setattr("saffron.cli.run_gh", _raising_gh)
    home2 = tmp_path / "home2"
    assert main(["--home", str(home2), "batch", "--stack", "--budget", "40"]) == 0
    capsys.readouterr()

    open_prs2 = run_stack_batch_calls[0]["open_prs"]
    result2 = open_prs2()
    assert result2 == []
    out2 = capsys.readouterr().out
    assert out2.count("note:") == 1
    assert "gh could not be run" in out2
    assert cli._GH_REFUSALS_SKIPPED in out2

    # Case 3: no slug.
    run_stack_batch_calls.clear()
    gh_calls.clear()
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )
    monkeypatch.setattr("saffron.cli.run_gh", _fake_run_gh)
    home3 = tmp_path / "home3"
    assert main(["--home", str(home3), "batch", "--stack", "--budget", "40"]) == 0
    capsys.readouterr()

    open_prs3 = run_stack_batch_calls[0]["open_prs"]
    result3 = open_prs3()
    assert result3 == []
    assert gh_calls == []
    out3 = capsys.readouterr().out
    assert out3.count("note:") == 1
    assert "no GitHub slug could be read" in out3
    assert cli._GH_REFUSALS_SKIPPED in out3

    # Case 4: readiness fails. No callable is built at all.
    run_stack_batch_calls.clear()
    monkeypatch.setattr(
        cli.preflight,
        "check_readiness",
        lambda *a, **k: preflight.Readiness(False, "auth", "token invalid"),
    )
    home4 = tmp_path / "home4"
    main(["--home", str(home4), "batch", "--stack", "--budget", "40"])
    assert len(run_stack_batch_calls) == 1
    assert run_stack_batch_calls[0]["open_prs"] is None


def _exec_file(path, text="#!/bin/sh\nexit 0\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


def _follow_ups_mirror(tmp_path):
    """`broken`, `base` and `head`: three commits of one mirror. Each has
    its own `.saffron/gates/tests` executable. A read at any sha but the
    pinned one then shows in what the callable gets."""
    mirror = tmp_path / "follow-ups-mirror"
    mirror.mkdir()
    _git(mirror, "init", "-q")

    _exec_file(mirror / ".saffron" / "gates" / "tests")
    (mirror / ".saffron" / "policy.yaml").write_text(
        "gates:\n  tests: {}\n"
        "integrity:\n  test_paths: ['tests/**']\n"
        "thread_env:\n  X: broken\n"
        "protected: ['broken/**']\n"
        "nope: 1\n"
    )
    _git(mirror, "add", "-A")
    _git(mirror, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "broken")
    broken_sha = _rev_parse(mirror, "HEAD")

    _exec_file(mirror / ".saffron" / "gates" / "tests")
    (mirror / ".saffron" / "policy.yaml").write_text(
        "gates:\n  tests: {}\n"
        "integrity:\n  test_paths: ['tests/**']\n"
        "thread_env:\n  X: base\n"
        "protected: ['base/**']\n"
    )
    specs_dir = mirror / ".saffron" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "SY-1-x.md").write_text("at base\n")
    _git(mirror, "add", "-A")
    _git(mirror, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "base")
    base_sha = _rev_parse(mirror, "HEAD")

    _exec_file(mirror / ".saffron" / "gates" / "tests")
    _exec_file(mirror / ".saffron" / "gates" / "lint")
    (mirror / ".saffron" / "policy.yaml").write_text(
        "gates:\n  lint: {}\n"
        "integrity:\n  test_paths: ['spec/**']\n"
        "thread_env:\n  X: head\n"
        "protected: ['head/**']\n"
    )
    (specs_dir / "SY-1-x.md").write_text("at head\n")
    _git(mirror, "add", "-A")
    _git(mirror, "-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "head")

    return SimpleNamespace(mirror=mirror, broken_sha=broken_sha, base_sha=base_sha)


def _follow_up_group(task_key, file, claims):
    findings = tuple(
        qualify.Qualified(
            task_key=task_key,
            finding=Finding(
                lens="adequacy",
                severity="blocker",
                file=file,
                line=i + 1,
                claim=claim,
            ),
            outcome="qualified",
            reason="",
        )
        for i, claim in enumerate(claims)
    )
    return qualify.FollowUpGroup(task_key=task_key, file=file, findings=findings)


def test_a_stack_batchs_follow_ups_are_qualified_and_written_from_the_pinned_base_at_the_stacks_top(
    tmp_path, monkeypatch, capsys
):
    """`cli._stack_follow_ups` reads every input at the pinned base, not the
    mirror's own `HEAD` and not `repo`'s own policy, before it writes
    anything. A raise after `qualify` returns still pools each unaccepted
    finding its walk never reached."""
    rig = _follow_ups_mirror(tmp_path)
    mirror, broken_sha, base_sha = rig.mirror, rig.broken_sha, rig.base_sha

    checkout = tmp_path / "checkout"
    (checkout / ".saffron").mkdir(parents=True)
    (checkout / ".saffron" / "policy.yaml").write_text(
        "gates: {}\nthread_env:\n  X: checkout\nprotected:\n  - checkout/**\n"
    )

    out_dir = tmp_path / "out"
    pinned_url = "https://github.com/o/r.git"

    ledger = Ledger(tmp_path / "ledger.db")
    ledger.upsert_repo(
        "other", "https://github.com/o/other.git", "/other.git", policy_sha=None
    )
    repo_id = ledger.upsert_repo("r", pinned_url, str(mirror), policy_sha=None)
    assert repo_id == 2

    pinned = task.PinnedBase(mirror=mirror, url=pinned_url, base_sha=base_sha)

    def _fake_layer_fields(ledger_arg, task_key):
        assert ledger_arg is ledger
        if task_key == "k-top":
            return end_review.LayerFields(
                spec_id="SY-2",
                branch="saffron/SY-2",
                pr_url="",
                base="z" * 40,
                head="2" * 40,
                known="",
            )
        if task_key == "k-bot":
            return end_review.LayerFields(
                spec_id="SY-1",
                branch="saffron/SY-1",
                pr_url="",
                base="y" * 40,
                head="1" * 40,
                known="",
            )
        raise KeyError(task_key)

    monkeypatch.setattr(cli.end_review, "layer_fields", _fake_layer_fields)

    log: list[str] = []
    cell_up_calls: list[dict] = []
    cell_down_calls: list[dict] = []
    unpriv_calls: list[str] = []

    def _fake_cell_up(
        *,
        repo,
        mirror,
        tree_base,
        branch,
        network,
        critic_network,
        volume,
        state,
        container,
        gates_dir,
        thread_env,
        created,
        note,
        cap_add=None,
    ):
        log.append("up")
        created.add(container)
        cell_up_calls.append(
            {
                "repo": repo,
                "mirror": mirror,
                "tree_base": tree_base,
                "branch": branch,
                "container": container,
                "gates_dir": gates_dir,
                "thread_env": dict(thread_env),
                "cap_add": cap_add,
            }
        )
        note("cell_up", "cell up")

    def _fake_cell_down(
        *, network, critic_network, volume, state, container, created, note
    ):
        log.append("down")
        cell_down_calls.append({"container": container})
        note("cell_down", True, "cell down")

    def _fake_unpriv(container):
        log.append("check")
        unpriv_calls.append(container)

    monkeypatch.setattr(session, "cell_up", _fake_cell_up)
    monkeypatch.setattr(session, "cell_down", _fake_cell_down)
    monkeypatch.setattr(session, "assert_bash_is_unprivileged", _fake_unpriv)
    monkeypatch.setattr(cli.runtime, "remove_container", lambda _container: None)

    real_layer_cell = end_review.layer_cell
    layer_cell_calls: list[dict] = []

    @contextmanager
    def _spy_layer_cell(fields, **kwargs):
        layer_cell_calls.append({"fields": fields, **kwargs})
        with real_layer_cell(fields, **kwargs) as container:
            yield container

    monkeypatch.setattr(cli.end_review, "layer_cell", _spy_layer_cell)

    real_stack_mint = cli._stack_mint
    stack_mint_builds: list[dict] = []

    def _spy_stack_mint(**kwargs):
        stack_mint_builds.append(kwargs)
        return real_stack_mint(**kwargs)

    monkeypatch.setattr(cli, "_stack_mint", _spy_stack_mint)

    agent_calls: list[dict] = []

    def _fake_run_agent(container, *, spec_id, timeout_s, **kwargs):
        log.append("agent")
        agent_calls.append({"spec_id": spec_id, "timeout_s": timeout_s})
        return implement.AttemptResult(
            session_id="s",
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=0.0,
            rate_limit_status="rejected",
        )

    monkeypatch.setattr(cli.implement, "run_agent", _fake_run_agent)

    writer_calls: list[dict] = []
    writer_counter = [0]

    def _fake_run_spec_writer(container, *, system_prompt, prompt, agent):
        log.append("writer")
        writer_calls.append(
            {"container": container, "system_prompt": system_prompt, "prompt": prompt}
        )
        agent(container, prompt=prompt)
        writer_counter[0] += 1
        made = spec_review.SpecWriterSession(
            text="draft\n",
            cost_usd=0.0,
            error=None,
            resets_at=None,
            session_id=f"w{writer_counter[0]}",
            num_turns=1,
            spec_sha="s" * 64,
        )
        writer_calls[-1]["session"] = made
        return made

    monkeypatch.setattr(cli.spec_review, "run_spec_writer", _fake_run_spec_writer)

    kbot_group = _follow_up_group("k-bot", "src/a.py", ["bot one", "bot two"])
    ktop_group = _follow_up_group("k-top", "src/a.py", ["top one", "top two"])

    qualify_calls: list[dict] = []

    def _fake_qualify(ledger_arg, layers, join, **kwargs):
        qualify_calls.append(
            {"ledger": ledger_arg, "layers": layers, "join": join, **kwargs}
        )
        kwargs["note"]("survived", False, "volume v survived")
        return qualify.Qualification(groups=[kbot_group, ktop_group], pool=[])

    monkeypatch.setattr(cli.qualify, "qualify", _fake_qualify)

    write_follow_ups_calls: list[dict] = []
    written_sessions: list = []

    def _fake_write_follow_ups(
        ledger_arg,
        stack_arg,
        *,
        batch_key,
        qualify,
        write,
        mint,
        mirror,
        specs_dir,
        repo_id,
        test_paths,
        cap_usd,
        emit,
        pooled,
    ):
        write_follow_ups_calls.append(
            {
                "ledger": ledger_arg,
                "stack": stack_arg,
                "batch_key": batch_key,
                "mirror": mirror,
                "specs_dir": specs_dir,
                "repo_id": repo_id,
                "test_paths": test_paths,
                "cap_usd": cap_usd,
                "pooled": pooled,
            }
        )
        qualification = qualify(stack_arg.layers, stack_arg.join)
        kbot, ktop = qualification.groups
        pooled.append(follow_up.Pooled(group=kbot, reason="p1"))
        written_sessions.append(write(kbot, "prompt k-bot"))
        written_sessions.append(write(ktop, "prompt k-top"))
        candidate = Candidate(
            path=Path(".saffron/specs/SY-3-x.md"),
            spec=intake.Spec(
                id="SY-3", title="t", type="feature", touches=["src/a.py"]
            ),
            spec_sha="c" * 64,
            task_id=None,
        )
        minted_id = mint(candidate)
        emit("pooled line")
        return [replace(candidate, task_id=minted_id)]

    monkeypatch.setattr(cli.follow_up, "write_follow_ups", _fake_write_follow_ups)

    p0_group = _follow_up_group("k-old", "src/z.py", ["old"])
    pooled: list[follow_up.Pooled] = [
        follow_up.Pooled(group=p0_group, reason="pre-existing")
    ]

    join_sentinel = review.LensReview(lens="join")
    stack = end_review.StackReview(
        join=join_sentinel,
        layers=[
            end_review.LayerReview("k-top", []),
            end_review.LayerReview("k-bot", []),
        ],
    )

    make = cli._stack_follow_ups(
        pinned=pinned,
        repo=checkout,
        ledger=ledger,
        out_dir=out_dir,
        cap_usd=6.5,
        pooled=pooled,
    )
    result = make("7", stack)

    printed = capsys.readouterr().out

    # --- the success path ---
    assert len(result) == 1
    assert write_follow_ups_calls[0]["pooled"] is pooled
    assert [p.reason for p in pooled] == ["pre-existing", "p1"]
    assert "pooled line" in printed

    call = write_follow_ups_calls[0]
    assert call["ledger"] is ledger
    assert call["stack"] is stack
    assert call["batch_key"] == "7"
    assert call["mirror"] == mirror
    assert call["repo_id"] == 2
    assert call["test_paths"] == ["tests/**"]
    assert call["cap_usd"] == 6.5
    specs_dir = call["specs_dir"]
    assert out_dir in specs_dir.parents
    assert (specs_dir / "SY-1-x.md").read_text() == "at base\n"

    minted_task_id = result[0].task_id
    row = ledger._db.execute(
        "SELECT spec_id, run_id FROM tasks WHERE task_id = ?", (minted_task_id,)
    ).fetchone()
    assert row["spec_id"] == "SY-3"
    run_row = ledger._db.execute(
        "SELECT base_sha FROM runs WHERE run_id = ?", (row["run_id"],)
    ).fetchone()
    assert run_row["base_sha"] == base_sha

    assert len(stack_mint_builds) == 1
    assert stack_mint_builds[0] == {
        "pinned": pinned,
        "repo": checkout,
        "ledger": ledger,
    }

    assert len(qualify_calls) == 1
    qcall = qualify_calls[0]
    assert qcall["ledger"] is ledger
    assert qcall["layers"] == stack.layers
    assert qcall["join"] is join_sentinel
    assert qcall["mirror"] == mirror
    assert qcall["repo"] == checkout
    assert qcall["thread_env"] == {"X": "base"}
    assert qcall["test_paths"] == ["tests/**"]
    assert qcall["gates"] == {"tests": Path("/gates/.saffron/gates/tests")}
    assert qcall["gates_dir"] == out_dir / "follow-ups" / "7"
    assert isinstance(qcall["created"], set)
    assert "volume v survived" in printed
    gates_policy_text = (qcall["gates_dir"] / ".saffron" / "policy.yaml").read_text()
    assert "X: base" in gates_policy_text

    assert log == ["up", "check", "writer", "agent", "down"] * 2
    assert all(c["spec_session"] is True for c in layer_cell_calls)
    assert unpriv_calls == [
        cell_up_calls[0]["container"],
        cell_up_calls[1]["container"],
    ]
    assert cell_up_calls[0]["container"] == "saffron-endreview-SY-2"
    assert cell_up_calls[1]["container"] == "saffron-endreview-SY-2"
    for c in cell_up_calls:
        assert c["tree_base"] == "2" * 40
        assert c["branch"] == "saffron/SY-2"
        assert c["repo"] == checkout
        assert c["mirror"] == mirror
        assert c["thread_env"] == {"X": "base"}
        assert "X: base" in (c["gates_dir"] / ".saffron" / "policy.yaml").read_text()

    assert [c["prompt"] for c in writer_calls] == ["prompt k-bot", "prompt k-top"]
    assert [c["container"] for c in writer_calls] == [
        u["container"] for u in cell_up_calls
    ]
    assert len(written_sessions) == 2
    assert all(
        got is c["session"]
        for got, c in zip(written_sessions, writer_calls, strict=True)
    )
    exported_policy, _ = load_policy(qcall["gates_dir"])
    expected_prompt = spec_review.spec_writer_system_prompt(
        exported_policy, prompts_dir=context.PROMPTS_DIR
    )
    for c in writer_calls:
        assert c["system_prompt"] == expected_prompt
    assert "base/**" in expected_prompt
    assert "head/**" not in expected_prompt
    assert "checkout/**" not in expected_prompt

    assert [c["spec_id"] for c in agent_calls] == ["follow-up-SY-1", "follow-up-SY-2"]
    assert all(c["timeout_s"] == spec_review.SPEC_WRITER_TIMEOUT_S for c in agent_calls)

    # --- the single-line "stopped" cases ---
    log.clear()
    cell_up_calls.clear()
    cell_down_calls.clear()
    unpriv_calls.clear()
    qualify_calls.clear()
    writer_calls.clear()
    agent_calls.clear()
    write_follow_ups_calls.clear()
    monkeypatch.setattr(cli.follow_up, "write_follow_ups", _fake_write_follow_ups)

    def _fresh_pooled():
        return [follow_up.Pooled(group=p0_group, reason="pre-existing")]

    def _run_case(pinned_case, stack_case):
        pooled_case = _fresh_pooled()
        made = cli._stack_follow_ups(
            pinned=pinned_case,
            repo=checkout,
            ledger=ledger,
            out_dir=out_dir,
            cap_usd=6.5,
            pooled=pooled_case,
        )
        outcome = made("7", stack_case)
        lines = capsys.readouterr().out.splitlines()
        return outcome, pooled_case, lines

    bad_sha_pinned = task.PinnedBase(mirror=mirror, url=pinned_url, base_sha="f" * 40)
    bad_url_pinned = task.PinnedBase(
        mirror=mirror, url="https://github.com/o/none.git", base_sha=base_sha
    )
    broken_pinned = task.PinnedBase(mirror=mirror, url=pinned_url, base_sha=broken_sha)
    gone_stack = end_review.StackReview(
        join=None, layers=[end_review.LayerReview("k-gone", [])]
    )

    for pinned_case, stack_case, needle in (
        (broken_pinned, stack, "nope"),
        (bad_sha_pinned, stack, "ffffffffffff"),
        (bad_url_pinned, stack, "o/none"),
        (pinned, gone_stack, "k-gone"),
    ):
        outcome, pooled_case, lines = _run_case(pinned_case, stack_case)
        assert outcome == []
        assert [p.reason for p in pooled_case] == ["pre-existing"]
        assert len(lines) == 1
        assert lines[0].startswith("follow-ups: stopped, ")
        assert needle in lines[0]

    assert cell_up_calls == []
    assert qualify_calls == []
    assert writer_calls == []

    def _raising_write_follow_ups(*_a, **_k):
        raise RuntimeError("mint broke")

    monkeypatch.setattr(cli.follow_up, "write_follow_ups", _raising_write_follow_ups)
    outcome, pooled_case, lines = _run_case(pinned, stack)
    assert outcome == []
    assert [p.reason for p in pooled_case] == ["pre-existing"]
    assert len(lines) == 1
    assert lines[0].startswith("follow-ups: stopped, ")
    assert "mint broke" in lines[0]
    assert cell_up_calls == []
    assert qualify_calls == []
    assert writer_calls == []

    # --- a raise part-way through qualify's groups, twice ---
    a_group = _follow_up_group("k-top", "src/a.py", ["a0", "a1"])
    b_group = _follow_up_group("k-bot", "src/b.py", ["b0", "b1"])
    c_group = _follow_up_group("k-bot", "src/c.py", ["c0", "c1"])
    d_group = _follow_up_group("k-top", "src/d.py", ["d0", "d1"])
    e_group = _follow_up_group("k-top", "src/b.py", ["e0", "e1"])

    def _fake_qualify_5(ledger_arg, layers, join, **kwargs):
        return qualify.Qualification(
            groups=[a_group, b_group, c_group, d_group, e_group], pool=[]
        )

    def _make_partial_double(round_no):
        def _double(
            ledger_arg,
            stack_arg,
            *,
            batch_key,
            qualify,
            write,
            mint,
            mirror,
            specs_dir,
            repo_id,
            test_paths,
            cap_usd,
            emit,
            pooled,
        ):
            qualification = qualify(stack_arg.layers, stack_arg.join)
            a, b, c, d, _e = qualification.groups
            pooled.append(
                follow_up.Pooled(
                    group=replace(a, findings=(a.findings[0],)), reason="own a"
                )
            )
            pooled.append(
                follow_up.Pooled(
                    group=replace(b, findings=(b.findings[0],)), reason="moved"
                )
            )
            write(replace(b, findings=(b.findings[1],)), "prompt b1")
            minted = mint(
                Candidate(
                    path=Path(".saffron/specs/SY-9-x.md"),
                    spec=intake.Spec(
                        id="SY-9", title="t", type="feature", touches=["src/b.py"]
                    ),
                    spec_sha="d" * 64,
                    task_id=None,
                )
            )
            ledger_arg.record_spec_text(
                minted,
                origin="follow_up",
                spec_id="SY-9",
                path=".saffron/specs/SY-9-x.md",
                text="draft\n",
            )
            pooled.append(
                follow_up.Pooled(
                    group=replace(c, findings=(c.findings[0],)), reason="own c"
                )
            )
            if round_no == 1:
                write(d, "prompt d")
                mint(
                    Candidate(
                        path=Path(".saffron/specs/SY-10-x.md"),
                        spec=intake.Spec(
                            id="SY-10",
                            title="t",
                            type="feature",
                            touches=["src/d.py"],
                        ),
                        spec_sha="e" * 64,
                        task_id=None,
                    )
                )
            raise RuntimeError("record broke")

        return _double

    for round_no in (1, 2):
        monkeypatch.setattr(cli.qualify, "qualify", _fake_qualify_5)
        monkeypatch.setattr(
            cli.follow_up, "write_follow_ups", _make_partial_double(round_no)
        )
        pooled_case = _fresh_pooled()
        made = cli._stack_follow_ups(
            pinned=pinned,
            repo=checkout,
            ledger=ledger,
            out_dir=out_dir,
            cap_usd=6.5,
            pooled=pooled_case,
        )
        outcome = made("7", stack)
        printed = capsys.readouterr().out

        assert outcome == []
        reasons = [p.reason for p in pooled_case]
        assert reasons[:4] == ["pre-existing", "own a", "moved", "own c"]
        assert reasons[4:] == ["RuntimeError: record broke"] * 4
        assert [
            tuple(f.finding.claim for f in p.group.findings) for p in pooled_case[4:]
        ] == [("a1",), ("c1",), ("d0", "d1"), ("e0", "e1")]
        assert "follow-ups: stopped, RuntimeError: record broke" in printed

    # --- an empty stack short-circuits before any export ---
    shutil.rmtree(out_dir)
    monkeypatch.setattr(cli.follow_up, "write_follow_ups", _fake_write_follow_ups)
    monkeypatch.setattr(cli.qualify, "qualify", _fake_qualify)
    empty_stack = end_review.StackReview(join=None, layers=[])
    made = cli._stack_follow_ups(
        pinned=pinned,
        repo=checkout,
        ledger=ledger,
        out_dir=out_dir,
        cap_usd=6.5,
        pooled=_fresh_pooled(),
    )
    assert made("7", empty_stack) == []
    assert capsys.readouterr().out == ""
    assert not out_dir.exists()

    ledger.close()


def test_a_stack_batch_commits_its_finish_and_survives_a_raise(
    tmp_path, monkeypatch, capsys
):
    """`saffron batch --stack` passes `run_stack_batch` the `finish` closure
    `cli._stack_finish` builds. It calls `finish.commit_finish` through the
    module, with the pinned mirror and a workdir under `out_dir`. It prints
    one line naming the outcome, and never lets a raise out of it reach
    `main`."""
    from saffron import finish as finish_module

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )

    captured_finish = {}

    def _fake_run_stack_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        captured_finish["finish"] = kwargs["finish"]
        kwargs["finish"](3, [5, 6])
        return "UNTIL"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)

    commit_calls = []

    def _recording_commit_finish(ledger, batch_id, unrun, *, mirror, workdir, **kw):
        commit_calls.append(
            {
                "ledger": ledger,
                "batch_id": batch_id,
                "unrun": unrun,
                "mirror": mirror,
                "workdir": workdir,
            }
        )
        return "c" * 40

    monkeypatch.setattr(finish_module, "commit_finish", _recording_commit_finish)
    monkeypatch.setattr(finish_module, "publish_finish", lambda *a, **k: [])

    _readiness_passes(monkeypatch)
    home = tmp_path / "home"
    assert main(["--home", str(home), "batch", "--stack"]) == 0

    assert len(commit_calls) == 1
    call = commit_calls[0]
    assert call["batch_id"] == 3
    assert call["unrun"] == [5, 6]
    assert call["mirror"] == Path("/tmp/pinned-mirror.git")
    assert call["workdir"] == home / "batches" / "v0" / "finish" / "3" / "tree"
    printed = capsys.readouterr().out
    assert f"finish: committed {'c' * 40}" in printed.splitlines()
    assert "finish: linked nothing, no line reported a push" in printed.splitlines()

    # A `GitError`, then a `ValueError`, from `commit_finish`. Each prints
    # its own line and the night still exits 0.
    with monkeypatch.context() as m:
        m.setattr(
            finish_module,
            "commit_finish",
            lambda *a, **k: (_ for _ in ()).throw(GitError("mirror gone")),
        )
        assert main(["--home", str(tmp_path / "home-git"), "batch", "--stack"]) == 0
        printed = capsys.readouterr().out
        assert "finish: GitError: mirror gone" in printed

    with monkeypatch.context() as m:
        m.setattr(
            finish_module,
            "commit_finish",
            lambda *a, **k: (_ for _ in ()).throw(ValueError("path off")),
        )
        assert main(["--home", str(tmp_path / "home-value"), "batch", "--stack"]) == 0
        printed = capsys.readouterr().out
        assert "finish: ValueError: path off" in printed

    # `None` with no layer, then `None` with one. Each prints its own line.
    with monkeypatch.context() as m:
        m.setattr(finish_module, "commit_finish", lambda *a, **k: None)
        m.setattr(Ledger, "stack_layers", lambda self, batch_id: [])
        assert main(["--home", str(tmp_path / "home-nolayer"), "batch", "--stack"]) == 0
        printed = capsys.readouterr().out
        assert "finish: no layer, so nothing committed" in printed

    with monkeypatch.context() as m:
        m.setattr(finish_module, "commit_finish", lambda *a, **k: None)
        m.setattr(Ledger, "stack_layers", lambda self, batch_id: [{"position": 1}])
        assert (
            main(["--home", str(tmp_path / "home-unchanged"), "batch", "--stack"]) == 0
        )
        printed = capsys.readouterr().out
        assert "finish: the tree is unchanged, so nothing committed" in printed


def test_a_stack_batch_writes_its_findings_from_the_pooled_list_its_writer_filled(
    tmp_path, monkeypatch, capsys
):
    """`cli._stack_finish` takes `pooled`, and `saffron batch --stack` passes
    it the same list it passes `_stack_follow_ups`. The findings call runs
    in its own `try`, guarding `Exception`, before the commit's own guard
    on `GitError` and `ValueError`."""
    from saffron import finish as finish_module

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )

    sentinel = follow_up.Pooled(
        group=qualify.FollowUpGroup(task_key="k", file="f.py", findings=()),
        reason="sentinel",
    )
    seen_pooled: dict[str, list] = {}
    real_follow_ups = cli._stack_follow_ups
    real_finish = cli._stack_finish

    def _spy_follow_ups(**kwargs):
        seen_pooled["follow_ups"] = kwargs["pooled"]
        return real_follow_ups(**kwargs)

    def _spy_finish(**kwargs):
        seen_pooled["finish"] = kwargs["pooled"]
        return real_finish(**kwargs)

    monkeypatch.setattr(cli, "_stack_follow_ups", _spy_follow_ups)
    monkeypatch.setattr(cli, "_stack_finish", _spy_finish)

    def _fake_run_stack_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        seen_pooled["follow_ups"].append(sentinel)
        kwargs["finish"](3, [5, 6])
        return "UNTIL"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)

    calls: list[tuple] = []

    def _recording_write_findings(ledger, batch_id, unrun, dest, *, pooled=()):
        calls.append(("findings", batch_id, unrun, dest, list(pooled)))

    def _recording_commit_finish(ledger, batch_id, unrun, *, mirror, workdir, **kw):
        calls.append(("commit", batch_id, unrun))
        return "c" * 40

    monkeypatch.setattr(finish_module, "write_findings", _recording_write_findings)
    monkeypatch.setattr(finish_module, "commit_finish", _recording_commit_finish)
    monkeypatch.setattr(finish_module, "publish_finish", lambda *a, **k: [])

    _readiness_passes(monkeypatch)
    home = tmp_path / "home"
    assert main(["--home", str(home), "batch", "--stack"]) == 0

    assert seen_pooled["follow_ups"] is seen_pooled["finish"]
    expected_dest = (
        home / "batches" / "v0" / "finish" / "3" / finish_module.FINDINGS_NAME
    )
    assert calls == [
        ("findings", 3, [5, 6], expected_dest, [sentinel]),
        ("commit", 3, [5, 6]),
    ]
    printed = capsys.readouterr().out
    assert f"finish: findings at {expected_dest}" in printed
    assert "finish: linked nothing, no line reported a push" in printed.splitlines()

    # A `GitError`, then a `ValueError`, then a `KeyError` from
    # `write_findings`. Each prints its own line, and the commit still runs.
    for exc, label in [
        (GitError("disk"), "GitError: disk"),
        (ValueError("bad row"), "ValueError: bad row"),
        (KeyError("task_id"), "KeyError: 'task_id'"),
    ]:
        calls.clear()
        with monkeypatch.context() as m:
            m.setattr(
                finish_module,
                "write_findings",
                lambda *a, _exc=exc, **k: (_ for _ in ()).throw(_exc),
            )
            home_i = tmp_path / f"home-{type(exc).__name__}"
            assert main(["--home", str(home_i), "batch", "--stack"]) == 0
            printed = capsys.readouterr().out
            assert f"finish: {label}" in printed
            assert calls == [("commit", 3, [5, 6])]

    # `commit_finish` raising still leaves the findings call recorded.
    calls.clear()
    with monkeypatch.context() as m:
        m.setattr(finish_module, "write_findings", _recording_write_findings)
        m.setattr(
            finish_module,
            "commit_finish",
            lambda *a, **k: (_ for _ in ()).throw(GitError("gone")),
        )
        home_commit = tmp_path / "home-commit-raise"
        assert main(["--home", str(home_commit), "batch", "--stack"]) == 0
        printed = capsys.readouterr().out
        assert "finish: GitError: gone" in printed
    assert calls[0][0] == "findings"


def test_a_stack_batch_publishes_its_finish_through_the_finishing_suite(
    tmp_path, monkeypatch, capsys
):
    """`cli._stack_finish` judges a real commit with `_finish_verify` and
    publishes it through `finish.publish_finish`, inside its own `try`
    guarding `Exception`. A raise from `publish_finish`, or from
    `package_phase.github_slug` before it, prints one line and keeps the
    night's own exit code."""
    import shutil

    from saffron import finish as finish_module
    from saffron.phases import package as package_phase
    from saffron.repos import image as repo_image

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )

    def _fake_run_stack_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        kwargs["finish"](3, [5, 6])
        return "UNTIL"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)
    monkeypatch.setattr(finish_module, "write_findings", lambda *a, **k: Path("x"))
    monkeypatch.setattr(finish_module, "commit_finish", lambda *a, **k: "c" * 40)

    repo_root = Path(__file__).resolve().parents[1]
    export_calls: list[tuple] = []

    def _fake_export(mirror, sha, dest):
        export_calls.append((mirror, sha, dest))
        dest_saffron = dest / ".saffron"
        dest_saffron.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            repo_root / ".saffron" / "policy.yaml", dest_saffron / "policy.yaml"
        )
        shutil.copytree(repo_root / ".saffron" / "gates", dest_saffron / "gates")
        return dest

    monkeypatch.setattr(cli.git_mirror, "export_saffron_dir", _fake_export)

    reverify_calls: list[dict] = []

    class _Comparison:
        new_failures = ("a", "b")

    def _fake_reverify(**kwargs):
        reverify_calls.append(kwargs)
        return _Comparison()

    monkeypatch.setattr(package_phase, "reverify", _fake_reverify)

    publish_calls: list[dict] = []
    verify_result: dict[str, int] = {}

    def _fake_publish_finish(
        ledger, batch_id, sha, *, mirror, url, slug, verify, gh, workdir
    ):
        publish_calls.append(
            {
                "ledger": ledger,
                "batch_id": batch_id,
                "sha": sha,
                "mirror": mirror,
                "url": url,
                "slug": slug,
                "gh": gh,
                "workdir": workdir,
            }
        )
        verify_result["value"] = verify("c" * 40, "d" * 40)
        return ["a published line"]

    monkeypatch.setattr(finish_module, "publish_finish", _fake_publish_finish)

    _readiness_passes(monkeypatch)
    home = tmp_path / "home"
    assert main(["--home", str(home), "batch", "--stack"]) == 0

    printed = capsys.readouterr().out.splitlines()
    assert f"finish: committed {'c' * 40}" in printed
    assert "finish: a published line" in printed
    assert "finish: linked nothing, no line reported a push" in printed

    assert len(publish_calls) == 1
    call = publish_calls[0]
    gates_dir = home / "batches" / "v0" / "finish" / "3" / "gates"
    assert call["batch_id"] == 3
    assert call["sha"] == "c" * 40
    assert call["mirror"] == Path("/tmp/pinned-mirror.git")
    assert call["url"] == "https://github.com/o/r.git"
    assert call["slug"] == "o/r"
    assert call["workdir"] == home / "batches" / "v0" / "finish" / "3" / "push"
    assert verify_result["value"] == 2
    assert export_calls == [(Path("/tmp/pinned-mirror.git"), "a" * 40, gates_dir)]

    assert len(reverify_calls) == 1
    rcall = reverify_calls[0]
    assert rcall["mirror"] == Path("/tmp/pinned-mirror.git")
    assert rcall["packaged_sha"] == "c" * 40
    assert rcall["new_base_sha"] == "d" * 40
    assert rcall["gates_dir"] == gates_dir
    assert rcall["image"] == repo_image.cell_tag(tmp_path)

    export_policy, _policy_sha = load_policy(gates_dir)
    expected_spec, expected_policy = finish_module.finish_suite(export_policy)
    assert rcall["policy"].model_dump() == expected_policy.model_dump()
    assert rcall["spec"] == expected_spec

    # `gh` cannot start, so the guarded callable it was handed still answers.
    with monkeypatch.context() as m:
        m.setattr(cli, "run_gh", lambda argv: (_ for _ in ()).throw(OSError("no gh")))
        assert main(["--home", str(tmp_path / "home-gh127"), "batch", "--stack"]) == 0
        assert publish_calls[-1]["gh"](["gh", "--version"]).returncode == 127

    # `publish_finish` raising `GitError`, then `KeyError`: each prints its
    # own line, and the night still exits 0.
    for exc, label in [
        (GitError("gone"), "GitError: gone"),
        (KeyError("x"), "KeyError: 'x'"),
    ]:
        with monkeypatch.context() as m:
            m.setattr(
                finish_module,
                "publish_finish",
                lambda *a, _exc=exc, **k: (_ for _ in ()).throw(_exc),
            )
            home_i = tmp_path / f"home-{type(exc).__name__}"
            assert main(["--home", str(home_i), "batch", "--stack"]) == 0
            printed = capsys.readouterr().out
            assert f"finish: publish stopped: {label}" in printed.splitlines()

    # `github_slug` raising before `publish_finish` is ever reached.
    before = len(publish_calls)
    with monkeypatch.context() as m:
        m.setattr(
            package_phase,
            "github_slug",
            lambda *a, **k: (_ for _ in ()).throw(
                package_phase.PackageError("no slug")
            ),
        )
        home_slug = tmp_path / "home-slug"
        assert main(["--home", str(home_slug), "batch", "--stack"]) == 0
        printed = capsys.readouterr().out
        assert "finish: publish stopped: PackageError: no slug" in printed
    assert len(publish_calls) == before

    # A `None` commit calls no publish.
    before = len(publish_calls)
    with monkeypatch.context() as m:
        m.setattr(finish_module, "commit_finish", lambda *a, **k: None)
        m.setattr(Ledger, "stack_layers", lambda self, batch_id: [])
        home_none = tmp_path / "home-none"
        assert main(["--home", str(home_none), "batch", "--stack"]) == 0
        printed = capsys.readouterr().out
        assert "finish: no layer, so nothing committed" in printed
    assert len(publish_calls) == before


def test_a_stack_batch_links_its_pushed_stack_through_a_repo_bound_gh(
    tmp_path, monkeypatch, capsys
):
    """`cli._stack_finish` links its pushed stack only once some published
    line starts with `pushed `. The runner it hands `link_stack` carries
    the batch's own repository and `GH_REPO`, and turns a `gh` that
    cannot start into exit 127. Every other path prints one line saying
    no push was reported, and calls no link."""
    from saffron import finish as finish_module

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("saffron.phases.package.real_remote", lambda _repo: "o/r")
    monkeypatch.setattr(
        cli, "_resolve_queue", lambda *a, **k: _fake_batch_resolution(tmp_path)
    )

    def _fake_run_stack_batch(candidates, ledger, budget_usd, until, runner, **kwargs):
        kwargs["finish"](3, [5, 6])
        return "UNTIL"

    monkeypatch.setattr(cli, "run_stack_batch", _fake_run_stack_batch)
    monkeypatch.setattr(finish_module, "write_findings", lambda *a, **k: Path("x"))
    monkeypatch.setattr(finish_module, "commit_finish", lambda *a, **k: "c" * 40)

    pushed_lines = [
        "pushed cccccccccccc to saffron/batch-3-finish, draft pull request "
        "https://github.com/o/r/pull/200",
        "worktree left at /p: GitError: busy",
    ]
    monkeypatch.setattr(
        finish_module, "publish_finish", lambda *a, **k: list(pushed_lines)
    )

    link_calls: list[dict] = []

    def _fake_link_stack(ledger, batch_id, *, mirror, url, gh):
        link_calls.append(
            {
                "ledger": ledger,
                "batch_id": batch_id,
                "mirror": mirror,
                "url": url,
                "gh": gh,
            }
        )
        return ["linked line one", "linked line two"]

    monkeypatch.setattr(finish_module, "link_stack", _fake_link_stack)

    _readiness_passes(monkeypatch)
    home = tmp_path / "home"
    assert main(["--home", str(home), "batch", "--stack"]) == 0

    printed = capsys.readouterr().out.splitlines()
    expected = [
        f"finish: {pushed_lines[0]}",
        f"finish: {pushed_lines[1]}",
        "finish: linked line one",
        "finish: linked line two",
    ]
    start = printed.index(expected[0])
    assert printed[start : start + 4] == expected
    assert "finish: linked nothing, no line reported a push" not in printed

    assert len(link_calls) == 1
    call = link_calls[0]
    assert call["batch_id"] == 3
    assert call["mirror"] == Path("/tmp/pinned-mirror.git")
    assert call["url"] == "https://github.com/o/r.git"

    gh = call["gh"]
    with monkeypatch.context() as m:
        recorded: dict = {}

        def _recorder(argv, **kwargs):
            recorded["argv"] = list(argv)
            recorded.update(kwargs)
            return subprocess.CompletedProcess(argv, 0, "linked\n", "")

        m.setattr(cli.subprocess, "run", _recorder)
        result = gh(["gh", "stack", "link", "--base", "trunk"])
    assert recorded["argv"] == ["gh", "stack", "link", "--base", "trunk"]
    assert recorded["cwd"] == tmp_path.resolve()
    assert recorded["env"]["GH_REPO"] == "o/r"
    assert recorded["env"]["PATH"] == os.environ.get("PATH")
    assert result.returncode == 0

    with monkeypatch.context() as m:

        def _raiser(argv, **kwargs):
            raise OSError("no gh")

        m.setattr(cli.subprocess, "run", _raiser)
        result = gh(["gh", "stack", "link"])
    assert result.returncode == 127

    # The worktree line first, the pushed line second: a link still runs
    # once, since every line is checked, not only the first.
    link_calls.clear()
    with monkeypatch.context() as m:
        m.setattr(
            finish_module,
            "publish_finish",
            lambda *a, **k: [pushed_lines[1], pushed_lines[0]],
        )
        home_i = tmp_path / "home-worktree-first"
        assert main(["--home", str(home_i), "batch", "--stack"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert len(link_calls) == 1
    assert "finish: linked nothing, no line reported a push" not in printed

    # An escalation line holding `pushed` as a substring, never at its
    # start, calls no link.
    link_calls.clear()
    with monkeypatch.context() as m:
        m.setattr(
            finish_module,
            "publish_finish",
            lambda *a, **k: ["escalate: nothing pushed to x"],
        )
        home_i = tmp_path / "home-escalate"
        assert main(["--home", str(home_i), "batch", "--stack"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert link_calls == []
    assert printed.count("finish: linked nothing, no line reported a push") == 1

    # A raising publish calls no link.
    link_calls.clear()
    with monkeypatch.context() as m:
        m.setattr(
            finish_module,
            "publish_finish",
            lambda *a, **k: (_ for _ in ()).throw(GitError("gone")),
        )
        home_i = tmp_path / "home-publish-raise"
        assert main(["--home", str(home_i), "batch", "--stack"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert link_calls == []
    assert printed.count("finish: linked nothing, no line reported a push") == 1

    # A raising commit calls no publish and no link.
    link_calls.clear()
    with monkeypatch.context() as m:
        m.setattr(
            finish_module,
            "commit_finish",
            lambda *a, **k: (_ for _ in ()).throw(GitError("gone")),
        )
        home_i = tmp_path / "home-commit-giterror"
        assert main(["--home", str(home_i), "batch", "--stack"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert link_calls == []
    assert printed.count("finish: linked nothing, no line reported a push") == 1

    link_calls.clear()
    with monkeypatch.context() as m:
        m.setattr(
            finish_module,
            "commit_finish",
            lambda *a, **k: (_ for _ in ()).throw(ValueError("off")),
        )
        home_i = tmp_path / "home-commit-valueerror"
        assert main(["--home", str(home_i), "batch", "--stack"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert link_calls == []
    assert printed.count("finish: linked nothing, no line reported a push") == 1

    # A `None` commit calls no publish and no link, with no layer and
    # with one.
    link_calls.clear()
    with monkeypatch.context() as m:
        m.setattr(finish_module, "commit_finish", lambda *a, **k: None)
        m.setattr(Ledger, "stack_layers", lambda self, batch_id: [])
        home_i = tmp_path / "home-none-norow"
        assert main(["--home", str(home_i), "batch", "--stack"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert link_calls == []
    assert printed.count("finish: linked nothing, no line reported a push") == 1

    link_calls.clear()
    with monkeypatch.context() as m:
        m.setattr(finish_module, "commit_finish", lambda *a, **k: None)
        m.setattr(Ledger, "stack_layers", lambda self, batch_id: [{"position": 1}])
        home_i = tmp_path / "home-none-onerow"
        assert main(["--home", str(home_i), "batch", "--stack"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert link_calls == []
    assert printed.count("finish: linked nothing, no line reported a push") == 1

    # A raising `link_stack` prints its own line and keeps the night's
    # own exit code.
    link_calls.clear()
    with monkeypatch.context() as m:
        m.setattr(
            finish_module,
            "link_stack",
            lambda *a, **k: (_ for _ in ()).throw(GitError("gone")),
        )
        home_i = tmp_path / "home-link-raise"
        assert main(["--home", str(home_i), "batch", "--stack"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert "finish: nothing linked: GitError: gone" in printed
    assert "finish: linked nothing, no line reported a push" not in printed
