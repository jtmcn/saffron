"""`ontology.spans` locates what `ontology.render` writes, without a graph library.

`.saffron/gates/prose.py` exempts these spans and runs under a cell's plain
`python3`, so the module must import nothing outside the standard library.
"""

import ast
import sys

import pytest
from ontology_paths import ONTOLOGY

REPO = ONTOLOGY.parent
SPANS = REPO / "ontology" / "spans.py"


def test_spans_imports_only_the_standard_library():
    tree = ast.parse(SPANS.read_text())
    imported = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}, imported


def test_the_principle_index_span_is_the_whole_table():
    from ontology import spans

    text = (REPO / "DESIGN.md").read_text()
    start, end = spans.principle_index(text)
    table = text[start:end]
    assert table.startswith(spans.PRINCIPLE_HEADER)
    rows = table.removeprefix(spans.PRINCIPLE_HEADER).splitlines()
    assert rows and all(row.startswith("| ") for row in rows)
    assert not text[end:].startswith("|"), "the span stopped inside the table"


def test_a_definition_span_holds_its_members():
    from ontology import spans

    text = (REPO / "CONTEXT.md").read_text()
    start, end = spans.definition_sentence(text, "Risk tier")
    assert text[start:end].startswith("**Risk tier**")
    assert set(spans.MEMBER_TOKEN.findall(text[start:end])) == {"standard", "elevated"}


def test_a_definition_that_is_not_there_is_refused():
    from ontology import spans

    with pytest.raises(ValueError, match="expected exactly one definition"):
        spans.definition_sentence("no terms here.\n", "Risk tier")


def test_render_reads_its_spans_from_the_one_module():
    from ontology import render, spans

    assert render.SETS is spans.SETS
    assert render.MEMBER_TOKEN is spans.MEMBER_TOKEN
