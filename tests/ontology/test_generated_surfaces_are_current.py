"""The committed derived surfaces equal what the vocabulary renders.

The failure this catches is the one measured in the design: a term added to one
of three copies of a closed set, with the other two left behind. A cell cannot
repair it — `CONTEXT.md` is a `protected` path in `.saffron/policy.yaml` and
`ontology/shapes/**` is in `integrity.gate_config`, so the task is refused at
plan time — which is why this has to be a gate the operator sees rather than a
repair anyone can make. (`protected`, repo-wide, is not `forbidden`, which is
per-spec frontmatter; `CONTEXT.md:169-173`.)
"""

from ontology_paths import ONTOLOGY, VOCABULARY

from ontology import render

CONTEXT = ONTOLOGY.parent / "CONTEXT.md"
SHAPES_FILE = ONTOLOGY / "shapes" / "saffron-shapes.ttl"


def test_context_md_is_current_with_the_vocabulary():
    committed = CONTEXT.read_text()
    assert render.render_context(committed, vocabulary=VOCABULARY) == committed, (
        "CONTEXT.md and ontology/saffron.ttl disagree. If the vocabulary is "
        "right, run `uv run python -m ontology.render`; if CONTEXT.md was hand-"
        "edited, that edit belongs in the vocabulary — regenerating discards it."
    )


def test_the_shapes_are_current_with_the_vocabulary():
    committed = SHAPES_FILE.read_text()
    assert render.render_shapes(committed, vocabulary=VOCABULARY) == committed, (
        "saffron-shapes.ttl and ontology/saffron.ttl disagree. If the "
        "vocabulary is right, run `uv run python -m ontology.render`; if the "
        "shapes were hand-edited, that edit belongs in the vocabulary."
    )
