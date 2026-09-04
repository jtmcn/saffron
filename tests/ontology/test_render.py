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


def test_declaring_a_core_gate_in_the_vocabulary_alone_updates_both_surfaces(tmp_path):
    """The measured defect, closed. Declaring `saffron:probe` in the vocabulary
    alone fails four checks with no repair a cell can make; here one edit
    propagates to both derived surfaces.

    `probe`, not `revert`: PR #112 declared `revert` in all three surfaces by
    hand, so asserting on it would pass with the generator doing nothing. The
    gate name has to be one the repo has never seen.

    The generated sh:in entry is also what gives the new term a reader —
    test_no_dead_terms regexes `saffron:<name>` over shapes/*.ttl — so this
    does not exempt the term from the dead-term rule, it satisfies it.
    """
    context = (ONTOLOGY.parent / "CONTEXT.md").read_text()
    vocab = tmp_path / "saffron.ttl"
    vocab.write_text(
        VOCABULARY.read_text()
        + "\nsaffron:probe a saffron:CoreGate ; saffron:blockingAt saffron:alwaysBlocking .\n"
    )
    assert "probe" in render.members("CoreGate", vocabulary=vocab)

    context_out = render.render_context(context, vocabulary=vocab)
    assert "`revert`, `probe`." in context_out
    # The claim is that it propagates, so the un-mutated render must differ.
    assert render.render_context(context, vocabulary=VOCABULARY) == context

    shapes_out = render.render_shapes(SHAPES_FILE.read_text(), vocabulary=vocab)
    assert "saffron:probe" in shapes_out


def test_a_definition_whose_first_sentence_is_unterminated_is_refused():
    """Review found `main()` could destroy the file it rewrites. The sentence
    search ran to end of document, so a definition left without a trailing
    period matched a period in a *later paragraph* and the span between — blank
    line and prose — was silently deleted. `CONTEXT.md` is `protected` and
    `main()` writes it in place, and the currency test's message tells the
    operator to run exactly that, so the destructive path was the documented
    remedy. Refuse instead: the definition is the search's upper bound.
    """
    text = (
        "**Severity**: `blocker`, `concern`, or `note`\n"
        "\n"
        "Some later paragraph mentioning `elevate_on` and more. Then more text.\n"
    )
    with pytest.raises(ValueError, match="no first sentence"):
        render.render_context(
            text,
            vocabulary=VOCABULARY,
            _members={"Severity": ["blocker", "concern", "note"]},
        )


def test_render_shapes_refuses_a_closed_set_that_renders_to_no_members():
    """`_join` guards this for CONTEXT.md; the shapes path had no guard, and
    `sh:in (  )` parses as rdf:nil — a constraint nothing can satisfy. It was
    masked only by `main()` rendering CONTEXT.md first, which is ordering, not
    a guard."""
    with pytest.raises(ValueError, match="rendered to no members"):
        render.render_shapes(
            SHAPES_FILE.read_text(), vocabulary=VOCABULARY, _members={"CoreGate": []}
        )


def test_a_one_member_or_comma_set_does_not_open_with_a_comma():
    """`", ".join(ticked[:-1])` is empty for one member, so the join emitted
    a leading comma. The empty-set guard above does not reach this case."""
    out = render.render_context(
        "**Severity**: `blocker`, `concern`, or `note`.\n",
        vocabulary=VOCABULARY,
        _members={"Severity": ["blocker"]},
    )
    assert out == "**Severity**: `blocker`.\n"


def test_the_generator_and_the_cross_check_name_the_same_five_sets():
    """`SETS` governs what is generated; `CLOSED_SETS` governs what is checked
    for agreement. They are deliberately separate — folding one into the other
    would let a set dropped from `SETS` vanish from generation and from the
    cross-check in the same edit. Separate, but they must agree, or a sixth set
    is checked and never generated: the drift class Phase A exists to close.
    """
    from test_vocabulary_agrees_with_context import CLOSED_SETS

    assert {term: cls for term, (cls, _) in render.SETS.items()} == CLOSED_SETS


def test_a_new_terminal_state_reaches_the_shape_that_closes_the_set(tmp_path):
    """Review found the documented workflow — edit the vocabulary, run the
    renderer — turned the blocking `shacl` gate red for three of the five sets.
    `TerminalStateShape`, `FindingShape`'s severity and `TaskShape`'s riskTier
    each hold a second copy that the generator did not cover, and
    `ontology/shapes/**` is `gate_config`, so no cell could repair it.

    `TaskShape`'s endedInState list stays hand-maintained: it closes over
    `EndState`, a superset of the terminal states, so it is not one of the five.
    """
    vocab = tmp_path / "saffron.ttl"
    vocab.write_text(
        VOCABULARY.read_text()
        + "\nsaffron:BUDGET_SPENT a saffron:TerminalState , saffron:EndState .\n"
    )
    out = render.render_shapes(SHAPES_FILE.read_text(), vocabulary=vocab)
    assert "saffron:BUDGET_SPENT" in out
    # It must land in the shape that closes the set, not merely somewhere.
    head = out[out.index("saffron:TerminalStateShape") :]
    assert "saffron:BUDGET_SPENT" in head[: head.index(" .")]


def test_severity_and_risk_tier_render_into_their_nested_property_shapes():
    """Both sit inside an `sh:property [ ... ]` block rather than at the top
    level of a named shape, and `TaskShape`'s first `sh:in` is endedInState —
    so a shape-name anchor would have rewritten the wrong list."""
    out = render.render_shapes(
        SHAPES_FILE.read_text(),
        vocabulary=VOCABULARY,
        _members={"Severity": ["blocker", "concern", "note", "wart"]},
    )
    assert (
        "sh:in ( saffron:blocker saffron:concern saffron:note\n            saffron:wart ) ]"
        in out
    )
    # endedInState is a superset and must not have been touched.
    assert "saffron:MERGED saffron:ORPHANED ) ]" in out
