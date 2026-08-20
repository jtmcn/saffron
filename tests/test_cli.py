"""The operator's only entry point, so it gets at least one end-to-end test."""

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
