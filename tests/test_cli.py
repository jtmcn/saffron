"""The operator's only entry point, so it gets at least one end-to-end test."""

import subprocess

from saffron.cell import session
from saffron.cli import main
from tests.test_replay import target  # noqa: F401 — a pytest fixture, used by name


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
        "subprocess.run", lambda *a, **k: type("P", (), {"stdout": "a" * 40})()
    )

    states = iter(["READY_FOR_REVIEW", "EXHAUSTED", "PREFLIGHT_FAILED"])
    monkeypatch.setattr(cli, "run_one_cell", lambda *a, **k: next(states))

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
        "subprocess.run", lambda *a, **k: type("P", (), {"stdout": "a" * 40})()
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
