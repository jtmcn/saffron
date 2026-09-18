"""The `dead` gate (docs/superpowers/specs/2026-09-18-dead-code-gate-design.md).

The script is loaded inside each test, never at module scope: the `revert`
gate re-runs a new witness with the script deleted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from saffron.intake import parse_spec

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


def test_unreachable_code_is_a_failure_with_no_symbol_to_defer():
    [unused] = _dead().parse(
        "saffron/util.py:30: unreachable code after 'return' (100% confidence)\n"
    )
    assert unused.code == "unreachable-code"
    assert unused.symbol is None


def test_a_line_the_parser_cannot_read_is_an_error_not_a_pass():
    with pytest.raises(ValueError, match="cannot read"):
        _dead().parse("vulture changed its format\n")


SPEC = "---\nid: SA-9001\ntitle: t\ntype: chore\n{extra}---\n\n## Context\nx\n"


def test_an_open_spec_defers_the_symbols_it_lists(tmp_path):
    (tmp_path / "SA-9001-x.md").write_text(
        SPEC.format(extra="pending_symbols:\n  - saffron/util.py::visible_cpus\n")
    )
    assert _dead().pending(tmp_path) == {
        "saffron/util.py::visible_cpus": "SA-9001-x.md"
    }


def test_a_retired_spec_defers_nothing(tmp_path):
    (tmp_path / "done").mkdir()
    (tmp_path / "done" / "SA-9001-x.md").write_text(
        SPEC.format(extra="pending_symbols:\n  - saffron/util.py::visible_cpus\n")
    )
    assert _dead().pending(tmp_path) == {}


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
