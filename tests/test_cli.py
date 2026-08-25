"""The operator's only entry point, so it gets at least one end-to-end test."""

import argparse
import subprocess

import pytest

from saffron import cli
from saffron.cell import session
from saffron.cli import main
from saffron.ledger import Ledger
from saffron.phases import package
from tests.test_replay import target  # noqa: F401 — a pytest fixture, used by name


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


def _ceiling_spec(tmp_path, **frontmatter):
    spec = tmp_path / "SY-2.md"
    declared = "".join(f"{key}: {value}\n" for key, value in frontmatter.items())
    spec.write_text(
        "---\nid: SY-2\ntitle: Two\ntype: feature\ntouches: ['src/**']\n"
        + declared
        + "---\n\n## Acceptance criteria\n- [ ] it works\n"
    )
    return spec


def _capture_cell_spec(monkeypatch, repo, tmp_path, namespace, capsys):
    captured: dict = {}

    def _capture(cell_spec, **_kwargs):
        captured["spec"] = cell_spec
        raise SystemExit(0)

    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    monkeypatch.setattr("saffron.cli.run_one_cell", _capture)
    with pytest.raises(SystemExit):
        cli._run_cell(namespace, Ledger(tmp_path / "l.db"), tmp_path / "out")
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
