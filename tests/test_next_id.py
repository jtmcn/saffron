"""`saffron next-id`: the next free spec id for a checkout (backlog b-589cf6)."""

import re
import subprocess
from pathlib import Path

from saffron.cli import main
from saffron.ledger import Ledger

_SPEC_ID_LINE = re.compile(r"^[A-Za-z0-9]+-[0-9]+$")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)


def _bare_checkout(repo: Path, origin: str | None) -> None:
    repo.mkdir()
    _git(repo, "init", "-q")
    if origin is not None:
        _git(repo, "remote", "add", "origin", origin)


def _write(path: Path, name: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / name).write_text("not a real spec\n")


def _seed_ledger(home: Path, origin: str, spec_id: str) -> None:
    ledger = Ledger(home / "ledger.db")
    try:
        repo_id = ledger.upsert_repo("acme", origin, "/m.git", policy_sha=None)
        run_id = ledger.create_run(repo_id, base_sha="a" * 40)
        ledger.create_task(run_id, spec_id, "s" * 64, f"saffron/{spec_id}")
    finally:
        ledger.close()


def _row_counts(ledger_path: Path) -> tuple[int, int, int]:
    ledger = Ledger(ledger_path)
    try:
        repos = ledger._db.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
        runs = ledger._db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        tasks = ledger._db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    finally:
        ledger.close()
    return repos, runs, tasks


def test_next_id_prints_one_past_a_task_whose_spec_file_exists_in_neither_directory(
    tmp_path, monkeypatch, capsys
):
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    origin = "https://example.com/acme/repo.git"
    other_origin = "https://example.com/acme/other.git"
    _bare_checkout(repo, origin)
    specs_dir = repo / ".saffron" / "specs"
    _write(specs_dir, "TE-0005-a.md")
    _write(specs_dir / "done", "TE-0007-b.md")

    ledger = Ledger(home / "ledger.db")
    repo_id = ledger.upsert_repo("acme", origin, "/m.git", policy_sha=None)
    other_repo_id = ledger.upsert_repo(
        "other", other_origin, "/m2.git", policy_sha=None
    )
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    ledger.create_task(run_id, "TE-0009", "s" * 64, "saffron/TE-0009")
    other_run_id = ledger.create_run(other_repo_id, base_sha="a" * 40)
    ledger.create_task(other_run_id, "TE-0050", "s" * 64, "saffron/TE-0050")
    ledger.close()

    before = _row_counts(home / "ledger.db")

    assert main(["--home", str(home), "next-id", "--repo", str(repo)]) == 0
    assert capsys.readouterr().out == "TE-0010\n"

    monkeypatch.chdir(repo)
    assert main(["--home", str(home), "next-id"]) == 0
    assert capsys.readouterr().out == "TE-0010\n"

    monkeypatch.chdir(tmp_path)
    assert main(["--home", str(home), "next-id", "--repo", "repo"]) == 0
    assert capsys.readouterr().out == "TE-0010\n"
    monkeypatch.chdir(repo)

    assert _row_counts(home / "ledger.db") == before

    _write(specs_dir, "TE-0012-c.md")
    assert main(["--home", str(home), "next-id"]) == 0
    assert capsys.readouterr().out == "TE-0013\n"

    _write(specs_dir / "done", "TE-0015-d.md")
    assert main(["--home", str(home), "next-id"]) == 0
    assert capsys.readouterr().out == "TE-0016\n"

    assert _row_counts(home / "ledger.db") == before


def test_next_id_prints_one_past_the_files_when_the_ledger_holds_nothing_for_the_repo(
    tmp_path, monkeypatch, capsys
):
    other_origin = "https://example.com/acme/other.git"

    def _fresh_repo(*, origin):
        repo = tmp_path / f"repo-{origin}"
        _bare_checkout(repo, origin)
        specs_dir = repo / ".saffron" / "specs"
        _write(specs_dir, "TE-0005-a.md")
        _write(specs_dir / "done", "TE-0007-b.md")
        return repo

    # Case 1: no ledger file at all.
    home_a = tmp_path / "home-a"
    repo_a = _fresh_repo(origin="first")
    assert main(["--home", str(home_a), "next-id", "--repo", str(repo_a)]) == 0
    assert capsys.readouterr().out == "TE-0008\n"
    assert not (home_a / "ledger.db").is_file()

    # Case 2: a ledger with no row for this origin.
    home_b = tmp_path / "home-b"
    _seed_ledger(home_b, other_origin, "TE-0050")
    before_b = _row_counts(home_b / "ledger.db")
    repo_b = _fresh_repo(origin="second")
    assert main(["--home", str(home_b), "next-id", "--repo", str(repo_b)]) == 0
    assert capsys.readouterr().out == "TE-0008\n"
    assert _row_counts(home_b / "ledger.db") == before_b

    # Case 3: a checkout with no `origin` remote at all.
    home_c = tmp_path / "home-c"
    _seed_ledger(home_c, other_origin, "TE-0050")
    before_c = _row_counts(home_c / "ledger.db")
    repo_c = _fresh_repo(origin=None)
    assert main(["--home", str(home_c), "next-id", "--repo", str(repo_c)]) == 0
    assert capsys.readouterr().out == "TE-0008\n"
    assert _row_counts(home_c / "ledger.db") == before_c


def test_next_id_prints_no_id_when_the_specs_hold_no_prefix_or_two(tmp_path, capsys):
    home = tmp_path / "home"

    no_prefix = tmp_path / "no-prefix"
    _bare_checkout(no_prefix, "https://example.com/acme/repo.git")
    specs_dir = no_prefix / ".saffron" / "specs"
    _write(specs_dir, "README.md")
    _write(specs_dir, "notes.md")
    assert main(["--home", str(home), "next-id", "--repo", str(no_prefix)]) == 2
    out = capsys.readouterr().out
    assert out.strip() != ""
    assert not any(_SPEC_ID_LINE.match(line) for line in out.splitlines())

    two_prefixes = tmp_path / "two-prefixes"
    _bare_checkout(two_prefixes, "https://example.com/acme/repo.git")
    specs_dir = two_prefixes / ".saffron" / "specs"
    _write(specs_dir, "TE-0001-a.md")
    _write(specs_dir, "SY-0002-b.md")
    assert main(["--home", str(home), "next-id", "--repo", str(two_prefixes)]) == 2
    out = capsys.readouterr().out
    assert out.strip() != ""
    assert not any(_SPEC_ID_LINE.match(line) for line in out.splitlines())
