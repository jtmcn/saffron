"""The operator's only entry point, so it gets at least one end-to-end test."""

import argparse
import ast
import functools
import hashlib
import inspect
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from saffron import cli, intake, preflight
from saffron.cell import session
from saffron.cli import main
from saffron.events import PhaseStart, Preflight, describe, read_log
from saffron.ledger import Ledger
from saffron.phases import package
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
        cli,
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

    monkeypatch.setattr(cli, "run_one_cell", _crash)
    assert cli.main(argv) == 2


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

    monkeypatch.setattr(cli, "run_one_cell", _fake_run_one_cell)
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

        monkeypatch.setattr(cli, "run_one_cell", _raise)
        assert cli.main(argv) == 2

    # Including the ones no tuple would have named: an OSError, a sqlite3
    # error, a pydantic failure from an SDK shape change.
    for broke in (OSError("no such device"), ValueError("not the shape")):

        def _raise_other(*_a, _broke=broke, **_k):
            raise _broke

        monkeypatch.setattr(cli, "run_one_cell", _raise_other)
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
        cli,
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

    monkeypatch.setattr("saffron.cli.run_one_cell", _started)
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

    monkeypatch.setattr("saffron.cli.run_one_cell", _started)
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
    monkeypatch.setattr("saffron.cli.run_one_cell", _capture)
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


def test_the_cell_is_cut_from_the_branchs_head_not_the_ledgers_recorded_sha(
    tmp_path, monkeypatch, capsys
):
    """`pushed_sha` is written once, by PACKAGE. Every review fix an operator
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
        "saffron.cli.run_one_cell",
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
        "saffron.cli.run_one_cell",
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

    stacked_on, parent_branch = cli._resolve_stacked_on(
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

    stacked_on, parent_branch = cli._resolve_stacked_on(
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
    assert cli._resolve_stacked_on(
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

    stacked_on, branch = cli._resolve_stacked_on(
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

    stacked_on, parent_branch = cli._resolve_stacked_on(
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
    assert cli._resolve_stacked_on(
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
    assert cli._resolve_stacked_on(
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
        cli._resolve_stacked_on,
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
    monkeypatch.setattr("saffron.cli.run_one_cell", _capture)
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

    monkeypatch.setattr(cli, "run_one_cell", _started)

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

    monkeypatch.setattr("saffron.cli.run_one_cell", _started)
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
        "saffron.cli.run_one_cell",
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
        "saffron.cli.run_one_cell",
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
        "saffron.cli.run_one_cell",
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

    def fake_follow(task_dir, *, verbose=False, interval=1.0):
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

    def fake_follow(task_dir, *, verbose=False, interval=1.0):
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

    def fake_follow(task_dir, *, verbose=False, interval=1.0, sleep=None):
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


def _queue_calls(name, *, keyword=None, value=None):
    """Whether `cli._queue`'s body contains a call to `name` — and, if a
    `keyword` is given, a literal keyword argument matching `value`.

    AST over `inspect.getsource`, not a substring search — a comment or a
    docstring merely naming `name` must not satisfy this — and not a call
    into the real function either: this is a structural check that the
    *printing* command still routes through the extraction, precisely so
    that reverting the extraction (and nothing else) makes it false. This
    file's own `test_no_signature_in_the_package_still_takes_a_watch` is the
    precedent for reading source this way rather than importing and calling
    it."""
    tree = ast.parse(inspect.getsource(cli._queue))
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
            if kw.arg == keyword and isinstance(kw.value, ast.Constant):
                return kw.value.value == value
    return False


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
