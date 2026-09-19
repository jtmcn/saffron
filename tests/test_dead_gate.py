"""The `dead` gate (docs/superpowers/specs/2026-09-18-dead-code-gate-design.md).

The script is loaded inside each test, never at module scope: the `revert`
gate re-runs a new witness with the script deleted.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from saffron.gates.contract import identity, parse_gate_json
from saffron.intake import SpecError, parse_spec

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / ".saffron" / "gates" / "dead.py"


def _dead():
    spec = importlib.util.spec_from_file_location("saffron_dead_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: `Unused` is a dataclass under postponed annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_each_vulture_line_becomes_one_failure_keyed_by_kind_and_symbol():
    [unused] = _dead().parse(
        "saffron/util.py:12: unused function 'visible_cpus' (60% confidence)\n"
    )
    assert (unused.file, unused.line, unused.code) == (
        "saffron/util.py",
        12,
        "unused-function",
    )
    assert unused.message == "unused function 'visible_cpus' (60% confidence)"
    assert unused.symbol == "saffron/util.py::visible_cpus"


@pytest.mark.parametrize(
    "message",
    [
        "unreachable code after 'return'",
        "unsatisfiable 'if' condition",
        "unsatisfiable 'while' condition",
        "unsatisfiable 'ternary' condition",
        "redundant if-condition",
        "unreachable 'else' block",
        "unreachable 'else' expression",
    ],
)
def test_each_reachability_line_is_unreachable_code_with_no_symbol(message):
    [unused] = _dead().parse(f"saffron/util.py:30: {message} (100% confidence)\n")
    assert unused.code == "unreachable-code"
    assert unused.message == f"{message} (100% confidence)"
    assert unused.symbol is None


def test_a_line_the_parser_cannot_read_is_an_error_not_a_pass():
    with pytest.raises(ValueError, match="cannot read"):
        _dead().parse("vulture changed its format\n")


SPEC = "---\nid: SA-9001\ntitle: t\ntype: chore\n{extra}---\n\n## Context\nx\n"


def test_an_open_spec_defers_the_symbols_it_lists(tmp_path):
    (tmp_path / "SA-9001-x.md").write_text(
        SPEC.format(extra="pending_symbols:\n  - saffron/util.py::visible_cpus\n")
    )
    assert _dead().pending(tmp_path) == (
        {"saffron/util.py::visible_cpus": "SA-9001-x.md"},
        [],
    )


def test_a_retired_spec_defers_nothing(tmp_path):
    (tmp_path / "done").mkdir()
    (tmp_path / "done" / "SA-9001-x.md").write_text(
        SPEC.format(extra="pending_symbols:\n  - saffron/util.py::visible_cpus\n")
    )
    assert _dead().pending(tmp_path) == ({}, [])


@pytest.mark.parametrize(
    "extra",
    [
        "pending_symbols: saffron/util.py::visible_cpus\n",
        "pending_symbols:\n  - visible_cpus\n",
        "pending_symbols: [unclosed\n",
    ],
)
def test_a_malformed_pending_list_is_an_error(extra):
    with pytest.raises(ValueError):
        _dead().entries(SPEC.format(extra=extra))


AGREEMENT = [
    SPEC.format(extra=""),
    SPEC.format(extra="pending_symbols:\n"),
    SPEC.format(extra="pending_symbols: [saffron/a.py::b, 'saffron/c.py::d']\n"),
    SPEC.format(extra='pending_symbols:\n  # a comment\n  - "saffron/a.py::b"\n'),
]


@pytest.mark.parametrize(
    "text",
    AGREEMENT
    + [p.read_text() for p in sorted((REPO / ".saffron" / "specs").glob("*.md"))],
)
def test_the_gate_reads_the_same_entries_intake_does(text):
    assert _dead().entries(text) == parse_spec(text).pending_symbols


def test_both_readers_refuse_an_entry_that_ends_in_a_newline():
    """`re`'s `$` matches before a trailing newline, and pydantic's does not."""
    text = SPEC.format(extra='pending_symbols:\n  - "saffron/a.py::b\\n"\n')
    with pytest.raises(SpecError):
        parse_spec(text)
    with pytest.raises(ValueError):
        _dead().entries(text)


CLEAN = "def used():\n    return 1\n\n\nprint(used())\n"
ORPHAN = "def orphan():\n    return 2\n"


def _tree(tmp_path: Path) -> Path:
    """A repo with the gate, an empty whitelist and one clean module."""
    gates = tmp_path / ".saffron" / "gates"
    gates.mkdir(parents=True)
    shutil.copy(SCRIPT, gates / "dead.py")
    shutil.copy(REPO / ".saffron" / "gates" / "dead", gates / "dead")
    (tmp_path / ".saffron" / "deadcode-allow.py").write_text("# Nothing yet.\n")
    (tmp_path / ".saffron" / "specs" / "done").mkdir(parents=True)
    (tmp_path / "saffron").mkdir()
    (tmp_path / "saffron" / "core.py").write_text(CLEAN)
    return tmp_path


def _env(path: str | None = None) -> dict[str, str]:
    venv_bin = str(Path(sys.executable).parent)
    return {**os.environ, "PATH": path or f"{venv_bin}{os.pathsep}{os.environ['PATH']}"}


def _script(
    tree: Path, *args: str, python=(sys.executable,), env=None, base=None
) -> str:
    done = subprocess.run(
        [*python, str((base or tree) / ".saffron" / "gates" / "dead.py"), *args],
        cwd=tree,
        capture_output=True,
        text=True,
        timeout=120,
        env=env or _env(),
    )
    return done.stdout


def _run(tree: Path, python=(sys.executable,), env=None, base=None):
    return parse_gate_json(
        _script(tree, python=python, env=env, base=base), expected_gate="dead"
    )


def _stub_vulture(tmp_path: Path, body: str, mode: int) -> dict[str, str]:
    """A PATH whose only vulture is `body`; `/usr/bin` and `/bin` carry no other."""
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "vulture").write_text(f"#!/bin/sh\n{body}")
    (stub / "vulture").chmod(mode)
    return _env(path=f"{stub}:/usr/bin:/bin")


def _spec(tree: Path, entry: str, folder: str = "") -> None:
    (tree / ".saffron" / "specs" / folder / "SA-9001-x.md").write_text(
        SPEC.format(extra=f"pending_symbols:\n  - {entry}\n")
    )


def test_a_tree_with_no_dead_code_passes_and_names_its_tool(tmp_path):
    result = _run(_tree(tmp_path))
    assert result.status == "pass", result.summary
    assert result.tool and result.tool.startswith("vulture")


def test_the_wrapper_runs_the_script(tmp_path):
    tree = _tree(tmp_path)
    done = subprocess.run(
        [str(tree / ".saffron" / "gates" / "dead")],
        cwd=tree,
        capture_output=True,
        text=True,
        timeout=120,
        env=_env(),
    )
    assert parse_gate_json(done.stdout, expected_gate="dead").status == "pass"


def test_a_function_nothing_calls_is_a_failure(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    result = _run(tree)
    assert result.status == "fail"
    assert [(f.file, f.code) for f in result.failures] == [
        ("saffron/extra.py", "unused-function")
    ]


def test_a_function_only_a_test_calls_is_a_failure(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    (tree / "tests").mkdir()
    (tree / "tests" / "test_extra.py").write_text(
        "from saffron.extra import orphan\n\n\ndef test_it():\n    assert orphan() == 2\n"
    )
    assert _run(tree).status == "fail"


def test_an_open_spec_defers_the_symbol_it_lists(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    _spec(tree, "saffron/extra.py::orphan")
    result = _run(tree)
    assert result.status == "pass", result.summary
    assert "1 deferred" in result.summary


def test_a_retired_spec_defers_nothing_at_the_gate(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    _spec(tree, "saffron/extra.py::orphan", folder="done")
    assert _run(tree).status == "fail"


def test_a_stale_pending_entry_does_not_fail_the_gate(tmp_path):
    """The task that implements a spec gives its entries a caller while the spec is open."""
    tree = _tree(tmp_path)
    _spec(tree, "saffron/core.py::used")
    result = _run(tree)
    assert result.status == "pass", result.summary
    assert "1 stale" in result.summary


def test_a_missing_vulture_is_an_error(tmp_path):
    result = _run(_tree(tmp_path), env=_env(path=str(tmp_path / "no-bin")))
    assert result.status == "error"
    assert "could not be run" in result.summary


def test_a_vulture_present_but_not_executable_is_an_error(tmp_path):
    """`execvp` skips a candidate it cannot run, so the PATH holds no other vulture."""
    env = _stub_vulture(tmp_path, "echo 'vulture 0.0-stub'\n", 0o644)
    result = _run(_tree(tmp_path / "repo"), env=env)
    assert result.status == "error", result.summary
    assert "could not be run" in result.summary


def test_a_vulture_that_stops_being_runnable_after_its_version_is_an_error(tmp_path):
    body = 'chmod -x "$0"\necho "vulture 0.0-stub"\n'
    env = _stub_vulture(tmp_path, body, 0o755)
    result = _run(_tree(tmp_path / "repo"), env=env)
    assert result.status == "error", result.summary
    assert "could not be run" in result.summary


def test_a_missing_pyyaml_is_an_error(tmp_path):
    tree = _tree(tmp_path)
    _spec(tree, "saffron/core.py::used")
    # `-S` drops site-packages, where pyyaml lives; vulture is still on PATH.
    result = _run(tree, python=(sys.executable, "-S"))
    assert result.status == "error"
    assert "No module named 'yaml'" in result.summary


def test_a_file_vulture_cannot_read_is_an_error_not_a_failure(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "broken.py").write_text("def (:\n")
    result = _run(tree)
    assert result.status == "error"
    assert "vulture exited 1" in result.summary


def test_a_condition_that_never_holds_is_a_failure_not_an_error(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text("if False:\n    print(1)\n")
    result = _run(tree)
    assert result.status == "fail", result.summary
    assert [f.code for f in result.failures] == ["unreachable-code"]


def test_a_malformed_spec_is_skipped_and_named_while_the_gate_still_runs(tmp_path):
    """Intake refuses the spec, so no task can use its entries: none is deferred."""
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    (tree / ".saffron" / "specs" / "SA-9001-x.md").write_text(
        SPEC.format(
            extra="pending_symbols:\n  - saffron/extra.py::orphan\n  - orphan\n"
        )
    )
    result = _run(tree)
    assert result.status == "fail", result.summary
    assert result.summary.endswith(", skipped unreadable specs: SA-9001-x.md")


def test_the_scanned_tree_cannot_configure_vulture(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    (tree / "pyproject.toml").write_text('[tool.vulture]\nignore_names = ["orphan*"]\n')
    assert [(f.file, f.code) for f in _run(tree).failures] == [
        ("saffron/extra.py", "unused-function")
    ]


def test_the_specs_that_defer_are_the_bases_not_the_scanned_trees(tmp_path):
    """A cell runs the base's `.saffron/` as `/gates`, so a spec it writes defers nothing."""
    base = _tree(tmp_path / "base")
    tree = _tree(tmp_path / "head")
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    _spec(tree, "saffron/extra.py::orphan")
    result = _run(tree, base=base)
    assert result.status == "fail", result.summary
    assert [f.file for f in result.failures] == ["saffron/extra.py"]


def test_a_failure_keeps_its_identity_when_its_line_moves(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    before = [identity("dead", f) for f in _run(tree).failures]
    (tree / "saffron" / "extra.py").write_text("\n" * 30 + ORPHAN)
    after = _run(tree).failures
    assert after[0].line != 1
    assert [identity("dead", f) for f in after] == before


def test_the_report_lists_each_failure_and_each_stale_entry(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    _spec(tree, "saffron/core.py::used")
    lines = _script(tree, "--report").splitlines()
    assert lines[0].startswith("saffron/extra.py:1: unused function 'orphan'")
    assert "stale: saffron/core.py::used (SA-9001-x.md)" in lines
    assert lines[-1] == "1 unused, 0 deferred by open specs, 1 stale pending entries"


def test_make_deadcode_runs_the_report():
    makefile = (REPO / "Makefile").read_text()
    assert "deadcode:\n\tuv run python .saffron/gates/dead.py --report\n" in makefile
