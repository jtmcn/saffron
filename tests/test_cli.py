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
