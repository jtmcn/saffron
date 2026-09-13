"""Witnesses for `hooks/retired_vocabulary.py` (docs/BACKLOG.md item 57).

`pygrep` — the engine the `retired-vocabulary` hook used before this script —
matches one line at a time, and every prose file the hook covers is
hard-wrapped, so a retired two-word term split across a line break was
invisible to it. These tests exercise the replacement script directly.

Every test always imports (or execs) the script *inside* a test function,
never at module scope: the `revert` gate re-runs each new witness with the
script deleted, and a module-scope import would turn that run into a
collection error, which reads as `skip` rather than a real failure.

The hook runs over this file too, so no test input spells the retired term as
a literal phrase — each is assembled from independently-named word fragments
at runtime instead.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "hooks" / "retired_vocabulary.py"


def _load_module():
    """Import the script fresh, inside the calling test.

    Registered in `sys.modules` under its own name before execution: the
    script's `Hit` dataclass carries `from __future__ import annotations`,
    and `dataclasses.fields()` resolves a stringified annotation by looking
    the defining module up there.
    """
    spec = importlib.util.spec_from_file_location("retired_vocabulary", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _retired_words():
    """The noun and verb of the one retired term this hook enforces, built
    from parts rather than quoted, so this file is never itself a hit."""
    noun = "".join(["g", "a", "t", "e"])
    verb = "".join(["r", "u", "n"])
    return noun, verb


def _hook_config():
    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    return next(
        hook
        for repo in config["repos"]
        for hook in repo["hooks"]
        if hook["id"] == "retired-vocabulary"
    )


def test_a_retired_term_split_by_a_line_break_is_caught(tmp_path):
    module = _load_module()
    noun, verb = _retired_words()

    plain_wrap = tmp_path / "plain_wrap.md"
    plain_wrap.write_text(f"prose before {noun}\n{verb} after prose\n")

    hyphen_wrap = tmp_path / "hyphen_wrap.md"
    hyphen_wrap.write_text(f"prose before {noun}-\n{verb} after prose\n")

    assert module.check_file(plain_wrap), (
        "a plain wrap (space separator) across a line break should be caught"
    )
    assert module.check_file(hyphen_wrap), (
        "a hyphenated wrap across a line break should be caught"
    )


def test_it_still_catches_what_the_line_by_line_hook_caught(tmp_path):
    """Seeing wrapped terms while dropping ones pygrep matched is a narrower
    hook. pygrep matched bytes: any encoding, a NUL past prek's text sniff, an
    ASCII-only word boundary, and either case."""
    module = _load_module()
    noun, verb = _retired_words()
    term = f"{noun} {verb}".encode()

    latin1 = tmp_path / "latin1.md"
    latin1.write_bytes(b"caf\xe9 then " + term + b" here\n")
    late_nul = tmp_path / "late_nul.md"
    late_nul.write_bytes(b"x" * 2000 + b"\x00\n" + term + b"\n")
    accented = tmp_path / "accented.md"
    accented.write_bytes(term + "é after\n".encode())
    mixed = tmp_path / "mixed.md"
    mixed.write_text(f"prose {noun.upper()}\n{verb.capitalize()}s on\n")

    for path in (latin1, late_nul, accented, mixed):
        assert module.check_file(path), path.name


def test_a_near_miss_stays_a_near_miss_across_a_break(tmp_path):
    module = _load_module()
    noun, verb = _retired_words()
    suffix = "ner"  # turns the verb into a word the pattern's \b already rejects

    one_line = tmp_path / "one_line.md"
    one_line.write_text(f"the {noun}-{verb}{suffix} keeps things moving\n")
    assert not module.check_file(one_line), (
        "the pattern's word boundary already rejects this on one line"
    )

    wrapped = tmp_path / "wrapped.md"
    wrapped.write_text(f"the {noun}-\n{verb}{suffix} keeps things moving\n")
    assert not module.check_file(wrapped), (
        "a wrap must not manufacture a hit out of a near miss"
    )

    blank_line = tmp_path / "blank_line.md"
    blank_line.write_text(f"{noun}\n\n{verb} is a paragraph away, not a wrap\n")
    assert not module.check_file(blank_line), (
        "a blank line is a paragraph break, not a wrap, and must not join the words either side of it"
    )


def test_a_hit_names_the_file_and_the_line_it_starts_on(tmp_path):
    module = _load_module()
    noun, verb = _retired_words()

    target = tmp_path / "multi_line.md"
    target.write_text(
        "line one is unrelated prose\n"
        "line two is also unrelated\n"
        f"line three ends with {noun}\n"
        f"{verb} continues the sentence on line four\n"
        "line five is unrelated too\n"
    )

    hits = module.check_file(target)
    assert hits, "the wrapped term should be reported"
    assert all(hit.path == target for hit in hits)
    assert {hit.line for hit in hits} == {3}, (
        "the hit belongs to the line the term starts on, not the continuation line"
    )
    # What the author sees is the exit code and the printed line, not `Hit`.
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(target)], capture_output=True, text=True
    )
    assert done.returncode == 1
    assert f"{target}:3:" in done.stdout


def test_the_configured_hook_runs_the_check_over_the_same_files():
    hook = _hook_config()
    # Exactly these keys: `pass_filenames: false`, `files:` or `stages:` would
    # each leave the hook passing without checking what it checked before.
    assert set(hook) == {"id", "name", "language", "types", "entry", "exclude"}
    assert hook["types"] == ["text"]
    assert (
        hook["exclude"] == r"^(CONTEXT\.md|CLAUDE\.md|docs/superpowers/|docs/evidence/)"
    )
    assert hook["language"] == "system"
    assert hook["entry"] == "uv run hooks/retired_vocabulary.py"


def test_the_tree_carries_no_retired_term_across_a_line_break():
    module = _load_module()
    hook = _hook_config()
    exclude = re.compile(hook["exclude"])
    assert hook["types"] == ["text"], "the approximation below assumes text-typed files"

    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    hits = []
    for name in tracked:
        if exclude.search(name):
            continue
        path = REPO / name
        if not path.is_file():
            continue
        # The spec's stand-in for `types: [text]`, which prek applies before
        # the hook ever sees a file.
        raw = path.read_bytes()
        if b"\x00" in raw:
            continue
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        hits.extend(module.check_file(path))

    assert not hits, f"found a retired term only a cross-line reading sees: {hits}"


def test_a_file_it_cannot_read_fails_the_hook_rather_than_passing(tmp_path, capsys):
    """Swallowed, an unreadable file reads as clean. A missing path stands in
    for one: the cell runs as root, which reads straight through `chmod 000`."""
    module = _load_module()
    gone = tmp_path / "gone.md"
    assert module.main([str(gone)]) == 1
    assert f"{gone}: unreadable" in capsys.readouterr().out
