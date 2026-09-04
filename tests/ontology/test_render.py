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
