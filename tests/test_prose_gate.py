"""The `prose` gate (docs/superpowers/specs/2026-09-16-prose-ratchet-design.md).

The script is loaded inside each test, never at module scope: the `revert`
gate re-runs a new witness with the script deleted.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GATES = REPO / ".saffron" / "gates"
SCRIPT = GATES / "prose.py"
LONG_A = "alpha " * 30 + "end."
LONG_B = "beta " * 30 + "end."


def _prose():
    spec = importlib.util.spec_from_file_location("saffron_prose_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: `Finding` is a dataclass under postponed annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _codes(text: str, path: str = "README.md", root: Path = REPO) -> list[str]:
    return [f.code for f in _prose().check(text, path, "prose", root=root)]


HITS = [
    ("sentence-length", "word " * 26 + "end."),
    ("hedge", "The gate should pass."),
    ("em-dash", "The cell stops — then it restarts."),
    ("em-dash", "The cell stops -- then it restarts."),
    ("semicolon", "The cell stops; it restarts."),
    ("filler", "The gate actually passes."),
    ("filler", "The gate passes, in fact."),
    ("perfect-tense", "The gate has been declared."),
    ("contraction", "The gate doesn't pass."),
]


@pytest.mark.parametrize("code,text", HITS)
def test_each_rule_fires_on_its_own_hit(code, text):
    assert _codes(text) == [code]


MISSES = [
    ("sentence-length", "word " * 24 + "end."),
    ("sentence-length", "# " + "word " * 30),
    ("sentence-length", "```\n" + "word " * 30 + "\n```\n"),
    ("hedge", 'The rule flags "should" in prose.'),
    ("hedge", "The gate calls `should_pass` first."),
    ("em-dash", "Rows 3–5 hold the ranges."),
    ("em-dash", "- The first item.\n- The second item."),
    ("filler", "The suite has exactly one baseline."),
    ("filler", "The choice was made deliberately."),
    ("perfect-tense", "The gate had a result."),
    ("trailing-condition", "The gate fails when the cell stops."),
]


@pytest.mark.parametrize("code,text", MISSES)
def test_each_rule_holds_its_measured_false_positive(code, text):
    assert code not in _codes(text)


def test_a_trailing_condition_is_read_only_in_a_spec_instruction():
    item = "- Run the gate when the cell stops.\n"
    assert _codes(item, ".saffron/specs/SA-0001-x.md") == ["trailing-condition"]
    assert "trailing-condition" not in _codes(item, "docs/backlog/1-x.md")
    assert (
        _codes("- If the cell stops, run the gate.\n", ".saffron/specs/SA-0001-x.md")
        == []
    )


def test_a_numbered_item_is_read_as_its_own_list_item():
    assert _codes(
        "1. Run the gate when the cell stops.\n", ".saffron/specs/SA-0001-x.md"
    ) == ["trailing-condition"]
    assert _codes(
        "  2. Run the gate when the cell stops.\n", ".saffron/specs/SA-0001-x.md"
    ) == ["trailing-condition"]


def test_a_numbered_reference_still_splits_the_sentence():
    # Merged, this would be 29 words (over the limit); split, neither half is.
    text = "word " * 6 + "rev 21. " + "word " * 20 + "end."
    assert "sentence-length" not in _codes(text)


def test_a_list_item_is_its_own_sentence():
    items = "".join(f"- {'word ' * 15}end\n" for _ in range(3))
    assert "sentence-length" not in _codes(items)


def test_a_finding_names_its_source_line():
    text = "```\ncode\n```\n\nIntro.\n\nThe gate should pass.\n"
    (finding,) = _prose().check(text, "README.md", "prose", root=REPO)
    assert (finding.line, finding.code) == (7, "hedge")


def test_a_defined_term_is_never_filler(tmp_path):
    (tmp_path / "ontology").mkdir()
    shutil.copy(REPO / "ontology" / "spans.py", tmp_path / "ontology" / "spans.py")
    assert _codes("It actually works.", root=tmp_path) == ["filler"]
    (tmp_path / "CONTEXT.md").write_text("**Actually**: a defined term.\n")
    assert _codes("It actually works.", root=tmp_path) == []


def test_a_closed_set_member_is_never_filler(tmp_path):
    (tmp_path / "ontology").mkdir()
    shutil.copy(REPO / "ontology" / "spans.py", tmp_path / "ontology" / "spans.py")
    (tmp_path / "CONTEXT.md").write_text("**Risk tier**: `standard` or `quietly`.\n")
    assert _codes("It quietly works.", root=tmp_path) == []


def test_the_real_vocabulary_protects_elevated(monkeypatch):
    prose = _prose()
    assert {"elevated", "standard"} <= prose.protected_words(REPO)
    monkeypatch.setattr(prose, "FILLER", (*prose.FILLER, "elevated"))
    assert prose.check("An elevated task.", "README.md", "prose", root=REPO) == []


def test_a_rendered_principle_is_counted_once():
    claim = "word " * 30
    design = (
        "## Principles — an index\n\n"
        "| # | The claim | From |\n|---|---|---|\n"
        f"| 1 | {claim} | A |\n\n"
        "## Appendix A\n\n"
        f"1. **{claim}.** Body.\n"
    )
    assert _codes(design, "DESIGN.md").count("sentence-length") == 1
    assert _codes(design, "README.md").count("sentence-length") == 2


def test_a_rendered_closed_set_is_not_counted():
    members = ", ".join(f"`m{i}`" for i in range(30))
    context = f"**Risk tier**: {members}.\n"
    assert _codes(context, "CONTEXT.md") == []
    assert _codes(context, "README.md") == ["sentence-length"]
