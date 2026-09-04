import pytest
from ontology_paths import ONTOLOGY, VOCABULARY

from ontology import render

SHAPES_FILE = ONTOLOGY / "shapes" / "saffron-shapes.ttl"


def test_members_are_returned_in_vocabulary_source_order(tmp_path):
    """CONTEXT.md's terminal-state order is deliberate and is neither
    alphabetical nor rdflib's iteration order, so source order is the only rule
    that can reproduce the committed bytes.

    Pinned on a synthetic vocabulary: pinning the real one would make this test
    a fourth hand-maintained copy of the set Phase A exists to generate, so
    declaring a ninth core gate would need a hand edit here. The real order is
    covered end to end by the zero-diff test.
    """
    vocabulary = tmp_path / "saffron.ttl"
    vocabulary.write_text(
        "@prefix saffron: <https://saffron.dev/ns#> .\n"
        "saffron:zulu a saffron:CoreGate .\n"
        "saffron:alpha a saffron:CoreGate .\n"
        "saffron:mike a saffron:CoreGate .\n"
    )
    assert render.members("CoreGate", vocabulary=vocabulary) == [
        "zulu",
        "alpha",
        "mike",
    ]


def test_members_of_a_class_with_no_instances_is_empty_not_an_error():
    assert render.members("NoSuchClass", vocabulary=VOCABULARY) == []


def test_each_closed_set_renders_the_committed_bytes_unchanged():
    """The five sets are already asserted equal by
    test_vocabulary_agrees_with_context, so a faithful generator changes
    nothing. A non-empty diff here means the generator is wrong, not CONTEXT.md."""
    committed = (VOCABULARY.parents[1] / "CONTEXT.md").read_text()
    assert render.render_context(committed, vocabulary=VOCABULARY) == committed


def test_a_new_member_lands_in_the_sentence_with_the_declared_join():
    text = "**Severity**: `blocker`, `concern`, or `note`.\n"
    out = render.render_context(
        text,
        vocabulary=VOCABULARY,
        # `_members` is keyed by ontology class, not by the CONTEXT.md term.
        _members={"Severity": ["blocker", "concern", "note", "wart"]},
    )
    assert out == "**Severity**: `blocker`, `concern`, `note`, or `wart`.\n"


def test_prose_outside_the_backticked_span_is_untouched():
    text = "**Gate role**: A name in the contract — `format`, `lint`. The repo supplies it.\n"
    out = render.render_context(
        text, vocabulary=VOCABULARY, _members={"GateRole": ["format", "lint", "types"]}
    )
    assert (
        out
        == "**Gate role**: A name in the contract — `format`, `lint`, `types`. The repo supplies it.\n"
    )


@pytest.mark.parametrize("width", [81, 82, 83, 84, 85])
def test_the_width_band_is_82_to_84_and_nothing_else(width, monkeypatch):
    """83 was found by search, so it is a fact about the committed CONTEXT.md
    that a later hand edit can invalidate silently."""
    committed = (VOCABULARY.parents[1] / "CONTEXT.md").read_text()
    monkeypatch.setattr(render, "_WIDTH", width)
    reproduces = render.render_context(committed, vocabulary=VOCABULARY) == committed
    assert reproduces == (82 <= width <= 84)


def test_a_closed_set_that_renders_to_no_members_is_an_error():
    """An empty enumeration would leave `**Severity**: , or .` behind and pass
    every assertion above. The fixture reaches this only because the lookup is
    by `in` — an empty list is falsy and `or` fell through to the vocabulary."""
    with pytest.raises(ValueError, match="rendered to no members"):
        render.render_context(
            "**Severity**: `blocker`, `concern`, or `note`.\n",
            vocabulary=VOCABULARY,
            _members={"Severity": []},
        )


def test_the_shapes_render_the_committed_bytes_unchanged():
    committed = SHAPES_FILE.read_text()
    assert render.render_shapes(committed, vocabulary=VOCABULARY) == committed


def test_the_in_list_wraps_at_three_terms_per_line():
    """The committed file wraps at three, with a twelve-space continuation
    indent. Reflowing it would be a diff in a file the shacl gate reads."""
    out = render.render_shapes(
        SHAPES_FILE.read_text(),
        vocabulary=VOCABULARY,
        _members={"CoreGate": ["a", "b", "c", "d"]},
    )
    assert "sh:in ( saffron:a saffron:b saffron:c\n            saffron:d ) ." in out
