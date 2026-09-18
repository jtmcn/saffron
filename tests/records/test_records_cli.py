"""The command is the retrieval fix: one record in one read, and the open set
on one screen. Run as a subprocess, the way `tests/test_cli.py` runs `saffron`."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
ROOT = Path(__file__).resolve().parents[2]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "records", *args, "--root", str(FIXTURE)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


def test_list_prints_one_line_per_item_in_id_order():
    out = run("list", "backlog").stdout.splitlines()
    assert [line.split()[0] for line in out] == ["1", "2", "3"]
    assert out[0].split(maxsplit=3) == [
        "1",
        "done",
        "1",
        "A gate that never ran read as green",
    ]


def test_list_filters_on_status_and_tier():
    open_out = run("list", "backlog", "--status", "open").stdout.splitlines()
    assert [line.split()[0] for line in open_out] == ["3"]
    tier_out = run("list", "backlog", "--tier", "1").stdout.splitlines()
    assert [line.split()[0] for line in tier_out] == ["1", "3"]


def test_list_shows_a_dash_for_no_tier(tmp_path):
    (tmp_path / "docs" / "backlog").mkdir(parents=True)
    (tmp_path / "docs" / "backlog" / "001-x.md").write_text(
        "---\nid: 1\ntitle: X\nstatus: open\n---\n\n## Problem\n\np\n\n## Done looks like\n\nd\n"
    )
    proc = subprocess.run(
        [sys.executable, "-m", "records", "list", "backlog", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert proc.stdout.split(maxsplit=3)[:3] == ["1", "open", "-"]


def test_show_prints_the_record_and_nothing_else():
    out = run("show", "2").stdout
    assert out.startswith("---\nid: 2\n")
    assert "## Done looks like" in out
    assert "A gate that never ran" not in out


def test_show_takes_the_zero_padded_filename_prefix():
    assert run("show", "002").stdout.startswith("---\nid: 2\n")


def test_show_one_section():
    out = run("show", "1", "--section", "Done looks like").stdout
    assert out.strip() == "`tool` is obtained by executing the tool."


def test_show_a_spec_id_lists_the_items_that_name_it():
    proc = run("show", "SA-0001")
    assert proc.returncode == 0
    assert proc.stdout.splitlines()[0].split()[0] == "1"


def test_show_a_missing_id_exits_one_and_says_so():
    proc = run("show", "42")
    assert proc.returncode == 1
    assert "42" in proc.stderr


def test_show_a_missing_section_exits_one_and_names_the_sections():
    proc = run("show", "1", "--section", "Nope")
    assert proc.returncode == 1
    assert "Problem" in proc.stderr and "Done looks like" in proc.stderr


def test_grep_prints_id_title_and_the_matching_line():
    proc = run("grep", "stamps")
    assert proc.returncode == 0
    out = proc.stdout.splitlines()
    assert out[0].split(maxsplit=1)[0] == "3"
    assert any("Nothing stamps" in line for line in out)


def test_grep_with_no_match_exits_one():
    proc = run("grep", "zzz-matches-nothing")
    assert proc.returncode == 1
    assert proc.stdout == ""


def test_show_a_spec_id_with_a_section_exits_two_and_says_why():
    proc = run("show", "SA-0001", "--section", "Problem")
    assert proc.returncode == 2
    assert "SA-0001" in proc.stderr and "--section" in proc.stderr
    assert proc.stdout == ""


def test_a_closed_reader_is_not_a_traceback():
    # The read end is closed before the child starts, so its first flush hits EPIPE.
    read, write = os.pipe()
    os.close(read)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "records", "grep", "e", "--root", str(FIXTURE)],
            stdout=write,
            stderr=subprocess.PIPE,
            text=True,
            cwd=ROOT,
            check=False,
        )
    finally:
        os.close(write)
    assert "Traceback" not in proc.stderr and "BrokenPipeError" not in proc.stderr
    assert proc.returncode == 1


def test_grep_with_an_invalid_pattern_exits_two_without_a_traceback():
    proc = run("grep", "(")
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr


def test_list_refuses_an_unknown_status():
    proc = run("list", "backlog", "--status", "opne")
    assert proc.returncode == 2
    assert "opne" in proc.stderr


def test_a_broken_directory_exits_two_naming_the_file(tmp_path):
    (tmp_path / "docs" / "backlog").mkdir(parents=True)
    (tmp_path / "docs" / "backlog" / "001-x.md").write_text(
        "---\nid: 1\ntitle: X\nstatus: done\n---\n"
    )
    proc = subprocess.run(
        [sys.executable, "-m", "records", "list", "backlog", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert proc.returncode == 2
    assert "001-x.md" in proc.stderr


def test_show_list_and_new_id_take_random_ids(tmp_path):
    root = tmp_path / "root"
    shutil.copytree(FIXTURE, root)
    (root / "docs" / "backlog" / "b-3f9a2c-later.md").write_text(
        "---\nid: b-3f9a2c\ntitle: Later\nstatus: open\n---\n\n"
        "## Problem\n\nx\n\n## Done looks like\n\ny\n"
    )

    def at(*args: str) -> str:
        return subprocess.run(
            [sys.executable, "-m", "records", *args, "--root", str(root)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        ).stdout

    assert at("show", "b-3f9a2c").startswith("---\nid: b-3f9a2c\n")
    assert at("list", "backlog").splitlines()[-1].split()[0] == "b-3f9a2c"
    fresh = at("new-id").strip()
    assert re.fullmatch(r"b-[0-9a-f]{6}", fresh) and fresh != "b-3f9a2c"
