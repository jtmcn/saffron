# The ontology becomes authoritative — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Declaring a core gate in `ontology/saffron.ttl` alone updates `CONTEXT.md` and the SHACL shapes from it, with every ontology check green — then run the experiment `DESIGN.md` Appendix O specifies, which decides whether anything further is built.

**Architecture:** A generator reads `ontology/saffron.ttl` and rewrites two derived surfaces: the enumerations in `CONTEXT.md`'s closed-set definitions, and the `sh:in` lists in `ontology/shapes/saffron-shapes.ttl`. A drift test asserts the committed files equal the render. Nothing under `saffron/` imports the generator, and no runtime dependency is added.

**Tech Stack:** Python `>=3.12` (`pyproject.toml`; `[tool.ty.environment]` pins `3.12`, so the generator must not use 3.13+ syntax), `rdflib` and `pyoxigraph` (already dev-only deps), pytest, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-02-ontology-authoritative-design.md`

## Global Constraints

- **`saffron/` runtime dependencies stay `pydantic` and `pyyaml`.** The generator lives under `ontology/`, is dev-only, and must never be imported by anything under `saffron/`.
- **`CONTEXT.md` is injected into agent prompts** by `saffron/agents/context.py`. Do not add marker comments, HTML, or any generator scaffolding to it — the file must read exactly as it does now to a human and to an agent. The generator locates its regions by the existing bold term.
- **The `shacl` gate is blocking** (`.saffron/gates/shacl.py`) and validates every tracked `.ttl` against `ontology/shapes/`. A shapes file that fails SHACL fails the gate suite.
- **Bare "suite" means the gate suite** (`CONTEXT.md`). The repo's own tests are always "the test suite".
- **A new test is not trusted until it has been run against the unfixed code** — or, for one guarding a property already true, against a mutant that breaks it (CLAUDE.md). **A mutant must name a term that is undeclared everywhere.** `saffron:revert` is not one: `73c2b9f` (PR #112) declared it in all three surfaces, so appending it appends a duplicate triple and the test suite stays green — measured, `74 passed`. Every mutant below uses `saffron:probe`, which is declared nowhere.
- **Commit subjects are lowercase `type(scope): what changed`**, written about the defect rather than the file.
- **"Drift test", not "drift gate".** It is a pytest test riding the existing blocking `tests` gate, not a new `.saffron/gates/` executable. That choice is deliberate — it inherits the `tool` field by execution (`pytest --version`), which a hand-written gate would have to obtain itself (§5.4, Appendix H). The cost is that the operator sees "some test failed" rather than a distinct `gate` name in the ledger; if that matters later, promoting it is a separate task. The spec calls it a gate in the loose sense; this plan builds a test.
- **Phase B is a gate.** Tasks 7+ do not exist until it returns, and its pass condition is `DESIGN.md` Appendix O's, not this plan's.
- **A block headed `# append to ontology/render.py` starts two blank lines below what precedes it**, per PEP 8 and `ruff format`. Appending with one is the whole of the difference between a green `format` gate and a red one.
- **Every code block here is gate-clean as written, and must stay so.** `format`, `lint` and `types` are all `blocking: true` (`.saffron/policy.yaml`), and `tests/test_saffron_gates.py` asserts each passes on a clean tree — so a block that only passes pytest fails `make check`. An earlier draft's blocks did exactly that: two unguarded `re` matches gave `ty` two `unresolved-attribute` diagnostics, and three lines were unformatted. **`# ty: ignore` is not the repair** — it is in `integrity.suppressions`, so adding one trips `added-suppression` instead. Guard the match.

## File structure

| File | Responsibility |
|---|---|
| `ontology/render.py` (create) | The only generator. Reads the vocabulary; renders the two derived surfaces. Pure functions over text — no file writes except in `main()`. |
| `tests/ontology/test_render.py` (create) | Unit tests for member extraction and both renderers. |
| `tests/ontology/test_generated_surfaces_are_current.py` (create) | The drift test: committed files equal the render. |
| `CONTEXT.md` (becomes generated; **no diff in Phase A**) | Five enumerations become generated. Prose untouched. A faithful generator changes zero bytes, which is Task 2's proof. |
| `ontology/shapes/saffron-shapes.ttl` (becomes generated; **no diff in Phase A**), lines 81–90 | Two `sh:in` lists become generated. |
| `CLAUDE.md` (modify) | One sentence: `CONTEXT.md` stops being authoritative for the five generated sets (spec part 6, Task 6). |
| `.saffron/policy.yaml` (modify) | `ontology/render.py` joins `integrity.gate_config` (Task 4). |
| `docs/superpowers/plans/2026-09-02-ontology-authoritative.md` | This plan; Phase B's answers are appended to it. |

**Not in this plan:** `Status`/EARL (spec part 6 — not one of the five cross-checked sets, so it blocks nothing here), promoting the other 18 absent terms, and anything requiring an emitter. `ontology/RATIONALE.md` is **not** deferred: the spec's own PR settles it, in place and at zero net lines, so no cap change reaches this plan.

---

## Phase A — the vocabulary generates its derived surfaces

### Task 1: Members of a class, in source order

`rdflib` iterates unordered, and `CONTEXT.md` lists terminal states in a deliberate order that is neither alphabetical nor graph order. Ordering by first appearance in the vocabulary's own text is what makes a byte-identical render possible.

**Files:**
- Create: `ontology/render.py`
- Test: `tests/ontology/test_render.py`

**Interfaces:**
- Produces: `members(class_name: str, *, vocabulary: Path) -> list[str]` — IRI local names of every `?s a saffron:<class_name>`, ordered by first byte offset of `saffron:<name>` in the vocabulary text.

- [ ] **Step 1: Write the failing test**

```python
# tests/ontology/test_render.py
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
```

**The synthetic order is `zulu, alpha, mike`** — deliberately neither alphabetical nor its reverse, so `sorted()` and `sorted(reverse=True)` both break it.

**`ONTOLOGY` and `SHAPES_FILE` are declared here, not in Task 3**, because appending an import mid-file is `E402` and `lint` is blocking. `pytest` is *not* imported yet for the mirror-image reason: nothing in this task uses it, and an unused import is `F401`. Each task adds its imports to the top of the file at the step that first needs them — never below the functions.

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/ontology/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ontology'`

- [ ] **Step 3: Implement**

```python
# ontology/render.py
"""Renders the surfaces derived from `ontology/saffron.ttl`.

Dev-only and deliberately outside `saffron/`: `pyproject.toml` states that
nothing under `saffron/` imports a graph library, and this module imports two.
"""

from __future__ import annotations

import re
from pathlib import Path

import rdflib

NS = "https://saffron.dev/ns#"


def members(class_name: str, *, vocabulary: Path) -> list[str]:
    """Local names of every instance of `saffron:<class_name>`, in the order
    they first appear in the vocabulary's own text.

    Source order, not graph order: rdflib iterates unordered, and the committed
    enumerations are in an order a reader chose. Sorting would rewrite them.
    """
    text = vocabulary.read_text()
    graph = rdflib.Graph().parse(vocabulary, format="turtle")
    names = [
        str(s).removeprefix(NS)
        for s in graph.subjects(rdflib.RDF.type, rdflib.URIRef(f"{NS}{class_name}"))
    ]

    def first_offset(name: str) -> int:
        found = re.search(rf"saffron:{re.escape(name)}\b", text)
        return found.start() if found else len(text)

    return sorted(names, key=first_offset)
```

**The blank lines around `first_offset` are `ruff format`'s, not decoration.** Written without them the block fails the blocking `format` gate.

Also create an empty `ontology/__init__.py` so `from ontology import render` resolves. Two things to confirm in this step rather than assume: that a test under `tests/ontology/` can `from ontology import render` (the test suite's `conftest.py` puts that directory on the path, not the repo root), and that `pyproject.toml`'s `packages = ["saffron"]` keeps the new package out of the wheel — `uv build && unzip -l dist/*.whl | grep -c ontology/` should print `0`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/ontology/test_render.py -v`
Expected: PASS, 2 tests.

- [ ] **Step 5: Verify it is a real check, not a tautology**

Temporarily change `sorted(names, key=first_offset)` to `sorted(names)` and re-run. Expected: FAIL — `test_members_are_returned_in_vocabulary_source_order` gets `["alpha", "mike", "zulu"]`. Restore.

Measured against the finished Task 5 file this mutant fails **7 of 14**, because source order is what every zero-diff assertion rests on. Each mutant below states the test it is aimed at *and* the total, so a run showing more reds than the aim is not a surprise to investigate.

- [ ] **Step 6: Commit**

```bash
git add ontology/render.py ontology/__init__.py tests/ontology/test_render.py
git commit -m "feat(ontology): rdflib iterates unordered, so a rendered enumeration needs source order"
```

---

### Task 2: Render `CONTEXT.md`'s five enumerations

The write path mirrors the existing read path exactly: `test_vocabulary_agrees_with_context.py:context_enumeration()` finds `**Term**`, takes the first sentence, and reads its backticked tokens. This replaces that same span.

**Files:**
- Modify: `ontology/render.py`
- Test: `tests/ontology/test_render.py`

**Interfaces:**
- Consumes: `members()` from Task 1.
- Produces: `render_context(text: str, *, vocabulary: Path) -> str`.

- [ ] **Step 1: Write the failing test**

Add `import pytest` to the top of `tests/ontology/test_render.py` — the first two tests below need it, and Task 1 could not carry it without tripping `F401`. Then append:

```python
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
```

**The width band is committed, not probed.** The design says 83 is "a fact about the committed file that a later hand edit can invalidate silently", so the boundary has to leave a witness: a temporary edit made during authoring and then restored does not. `monkeypatch` sets the module global, which `render_context` reads at call time.

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/ontology/test_render.py -v`
Expected: FAIL — `AttributeError: module 'ontology.render' has no attribute 'render_context'`

- [ ] **Step 3: Implement**

Add `import textwrap` to the module's imports; the rest appends.

```python
# append to ontology/render.py

# Measured, not chosen: greedy-wrapping the five spans reproduces the committed
# bytes at 82, 83 and 84 and at no other width (76-92 searched).
_WIDTH = 83

# CONTEXT.md bold term -> (ontology class, join style). The join styles are the
# ones already committed; a generator that normalised them would rewrite prose
# it does not own.
SETS = {
    "Terminal state": ("TerminalState", "comma"),
    "Severity": ("Severity", "or-comma"),
    "Risk tier": ("RiskTier", "or-plain"),
    "Gate role": ("GateRole", "comma"),
    "Core gates": ("CoreGate", "comma"),
}


def _join(names: list[str], style: str) -> str:
    # A closed set that renders to nothing is a generator bug, not an output:
    # `**Terminal state**: A state that reaches the operator — .` would pass
    # every assertion below and be silently wrong.
    if not names:
        raise ValueError("a closed set rendered to no members")
    ticked = [f"`{n}`" for n in names]
    if style == "comma":
        return ", ".join(ticked)
    if style == "or-comma":
        return ", ".join(ticked[:-1]) + f", or {ticked[-1]}"
    if style == "or-plain":
        return " or ".join(ticked)
    raise ValueError(f"unknown join style: {style}")


def _continuation_indent(text: str, span_start: int, span_end: int) -> str:
    """The indent the committed continuation lines carry. A span that already
    wraps shows it directly; one that does not inherits its own line's indent."""
    newline = text.find("\n", span_start, span_end)
    at = newline + 1 if newline != -1 else text.rfind("\n", 0, span_start) + 1
    # Sliced rather than `re.match(...).group()`: that match is `Match | None` to
    # `ty`, and the blocking `types` gate does not take "this pattern always
    # matches" for an answer.
    rest = text[at:]
    return rest[: len(rest) - len(rest.lstrip(" \t"))]


def render_context(text: str, *, vocabulary: Path, _members=None) -> str:
    """Rewrite each closed set's backticked span in place.

    The span is first-backtick to last-backtick within the definition's first
    sentence — the same span `context_enumeration` reads. Everything outside it,
    including the em dash, the connective prose and the sentences after, is
    left exactly as committed.

    Three of the five sets wrap across source lines, so the rewritten span is
    re-wrapped at the committed width and continuation indent. Emitting it on
    one line reproduces the members correctly and the bytes wrongly.
    """
    for term, (class_name, style) in SETS.items():
        # A fixture that supplies `_members` names the sets it is about; the
        # others are not in its text and indexing for them would raise.
        if _members is not None and class_name not in _members:
            continue
        # `in`, not `or`: an empty member list is falsy, and falling through to
        # the real vocabulary would make an empty-set fixture silently pass.
        # `_members` is keyed by ontology class in both renderers, never by the
        # CONTEXT.md term — one key space, so a test reads the same either side.
        names = (
            _members[class_name]
            if _members is not None
            else members(class_name, vocabulary=vocabulary)
        )
        start = text.index(f"**{term}**")
        # First sentence: up to a period followed by whitespace or end of text.
        # Guarded, not asserted: a definition with no sentence end is a real
        # input, and `ty` rejects `.start()` on `Match | None` regardless.
        stop = re.search(r"\.(?:\s|$)", text[start:])
        if stop is None:
            raise ValueError(f"{term}'s definition has no first sentence to rewrite")
        end = stop.start() + start
        sentence = text[start:end]
        first, last = sentence.index("`"), sentence.rindex("`") + 1
        # `rfind`, not `rindex`: a one-line fixture has no preceding newline.
        column = start + first - (text.rfind("\n", 0, start + first) + 1)
        indent = _continuation_indent(text, start + first, start + last)
        body = textwrap.fill(
            _join(names, style),
            width=_WIDTH,
            initial_indent=" " * column,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )[column:]
        text = text[:start] + sentence[:first] + body + sentence[last:] + text[end:]
    return text
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/ontology/test_render.py -v`
Expected: PASS, 11 tests — 5 named above plus the 5 width parameters and the empty-set case. **The zero-line-diff test is the one that matters** — it proves the generator reproduces bytes a human wrote before it is trusted to write new ones. All eleven were run against the real `CONTEXT.md` while this plan was written; a sketch whose expected output has not been executed is the defect this step exists to catch.

- [ ] **Step 5: Prove the zero-diff test can fail**

Three mutants, because the join, the wrap and the empty-set guard fail independently:

1. Change `"or-comma"` to `"comma"` for `Severity`. Expected: FAIL on `test_each_closed_set_renders_the_committed_bytes_unchanged` (6 of 14 — the width parameters rest on the same render).
2. Replace the whole `textwrap.fill(...)` call with `body = _join(names, style)`. Expected: FAIL on the same test (5 of 14, including the three in-band width parameters), **with a three-hunk diff collapsing `Gate role`, `Core gates` and `Terminal state` each onto one line.** This is the mutant that matters — it is the bug the first draft of this plan shipped.
3. Replace `if not names:` with `if False:` in `_join`. Expected: FAIL on `test_a_closed_set_that_renders_to_no_members_is_an_error` alone (1 of 14).

Restore all three.

**`_WIDTH = 80` is not the mutant for hunk 2, and an earlier draft said it was.** Measured, it produces **one** hunk, on `Core gates` alone, and it *adds* a line break rather than collapsing anything — narrowing a greedy wrap can only wrap earlier. No width in 76-92 gives three hunks. The collapse is what dropping the wrap entirely does, which is what the first draft actually shipped; the sentence was right about the bug and attached to the wrong edit. The width boundary is covered instead by the committed `test_the_width_band_is_82_to_84_and_nothing_else`, which a temporary `_WIDTH` edit could never leave behind.

- [ ] **Step 6: Commit**

```bash
git add ontology/render.py tests/ontology/test_render.py
git commit -m "feat(ontology): the glossary's enumerations render from the vocabulary, byte for byte"
```

---

### Task 3: Render the shapes' `sh:in` lists

`ontology/shapes/saffron-shapes.ttl:81-90` is the third copy of two of these sets, and it is enforced by a **blocking** gate. Without this task, declaring a gate in the vocabulary still fails `test_shapes::test_the_lifecycle_graph_conforms` and the `shacl` gate.

**Files:**
- Modify: `ontology/render.py`
- Test: `tests/ontology/test_render.py`

**Interfaces:**
- Produces: `render_shapes(text: str, *, vocabulary: Path) -> str`.

- [ ] **Step 1: Write the failing test**

`ONTOLOGY` and `SHAPES_FILE` are already at the top of the file from Task 1 — appending an import here instead is `E402 Module level import not at top of file`, and `lint` is blocking. This block is functions only:

```python
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
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/ontology/test_render.py -v`
Expected: FAIL — no attribute `render_shapes`.

- [ ] **Step 3: Implement**

```python
# append to ontology/render.py

# Shape name -> ontology class whose members fill its sh:in list.
SHAPE_SETS = {"CoreGateShape": "CoreGate", "GateRoleShape": "GateRole"}
_PER_LINE = 3
_INDENT = " " * 12


def render_shapes(text: str, *, vocabulary: Path, _members=None) -> str:
    """Rewrite each `sh:in ( … )` list from the vocabulary.

    Three terms per line with a twelve-space continuation indent, which is what
    is committed. The `shacl` gate reads this file, so a reflow is a gate diff.
    """
    for shape, class_name in SHAPE_SETS.items():
        # Same rules as `render_context`: a fixture names the sets it is about,
        # and an empty list is looked up by `in` rather than falling through.
        if _members is not None and class_name not in _members:
            continue
        names = (
            _members[class_name]
            if _members is not None
            else members(class_name, vocabulary=vocabulary)
        )
        rows = [
            " ".join(f"saffron:{n}" for n in names[i : i + _PER_LINE])
            for i in range(0, len(names), _PER_LINE)
        ]
        body = f"\n{_INDENT}".join(rows)
        start = text.index(f"saffron:{shape}")
        open_at = text.index("sh:in (", start)
        close_at = text.index(")", open_at)
        text = text[:open_at] + f"sh:in ( {body} " + text[close_at:]
    return text
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/ontology/test_render.py -v`
Expected: PASS, 13 tests.

- [ ] **Step 5: Prove the wrap rule is load-bearing**

Temporarily set `_PER_LINE = 4` and re-run. Expected: FAIL on the zero-diff shapes test (2 of 14, with `test_the_in_list_wraps_at_three_terms_per_line`). Restore.

- [ ] **Step 6: Commit**

```bash
git add ontology/render.py tests/ontology/test_render.py
git commit -m "feat(ontology): the shapes' sh:in lists are a third copy of the same closed sets"
```

---

### Task 4: The drift test, and `main()`

**Files:**
- Modify: `ontology/render.py`, `.saffron/policy.yaml`
- Create: `tests/ontology/test_generated_surfaces_are_current.py`

**Interfaces:**
- Produces: `python -m ontology.render` rewrites both files in place.

- [ ] **Step 1: Write the failing test**

```python
# tests/ontology/test_generated_surfaces_are_current.py
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
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/ontology/test_generated_surfaces_are_current.py -v`
Expected: PASS, 2 tests — the surfaces are already current, because Tasks 2 and 3 proved the render is byte-identical.

- [ ] **Step 3: Prove it fails when the vocabulary moves ahead**

This guards a property that is already true, so it must be run against a mutant (CLAUDE.md). In a scratch worktree only:

```bash
git worktree add -q --detach /tmp/drift-check HEAD
cd /tmp/drift-check
printf '\nsaffron:probe a saffron:CoreGate ; saffron:blockingAt saffron:alwaysBlocking .\n' >> ontology/saffron.ttl
uv run pytest tests/ontology/test_generated_surfaces_are_current.py -v
```

Expected: BOTH tests FAIL (2 of 2 in that file), each naming the regenerate command.

**`probe`, not `revert`.** `saffron:revert` is already declared in all three surfaces (`73c2b9f`), so appending it appends a duplicate triple: measured on a worktree at this branch's HEAD, `tests/ontology/` reports **`74 passed`** and nothing fails. A mutant that does not mutate would let this test — the whole point of Phase A — be committed having never been seen to fail. `saffron:probe` is declared nowhere, and appending it fails four checks at HEAD (`test_no_dead_terms` ×2, `test_shapes::test_the_lifecycle_graph_conforms`, `test_vocabulary_agrees_with_context[Core gates-CoreGate]`), which is the design's measurement reproduced. Then:

```bash
git worktree remove --force /tmp/drift-check
```

- [ ] **Step 4: Add `main()`**

```python
# append to ontology/render.py

def main() -> None:
    root = Path(__file__).resolve().parents[1]
    vocabulary = root / "ontology" / "saffron.ttl"
    for path, fn in (
        (root / "CONTEXT.md", render_context),
        (root / "ontology" / "shapes" / "saffron-shapes.ttl", render_shapes),
    ):
        path.write_text(fn(path.read_text(), vocabulary=vocabulary))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Verify `main()` is a no-op on a current tree**

Run: `uv run python -m ontology.render && git diff --stat`
Expected: no output from `git diff --stat`.

- [ ] **Step 6: Route the generator itself to a person**

`CONTEXT.md` is `protected` and `ontology/shapes/**` is in `integrity.gate_config`, so a cell cannot edit either derived surface. Nothing covers the file that decides whether they are *current*: replacing `render_context`'s body with `return text` makes both drift tests pass unconditionally, and neither `integrity` nor `protected_touch_refusal` sees it. Add to `.saffron/policy.yaml`'s `integrity.gate_config` list:

```yaml
      "ontology/render.py",
```

Same argument the list already makes for `conftest.py` and `ontology/shapes/**`: the rules a gate enforces have to be routed to a person, not just the gate's own executable. Note the list is scanned for the tokens it declares, so describe the path — do not add a comment quoting a suppression.

- [ ] **Step 7: Commit**

```bash
git add ontology/render.py tests/ontology/test_generated_surfaces_are_current.py .saffron/policy.yaml
git commit -m "feat(ontology): a closed set split across three files drifts silently"
```

---

### Task 5: The success criterion, end to end

Proves the thing the design exists to deliver. Verified by hand on a worktree at this branch's HEAD: appending `saffron:probe` alone fails four checks, and updating all three surfaces makes `tests/ontology/` green — the generated `sh:in` entry is itself the reader that satisfies `test_no_dead_terms`.

**Files:**
- Test: `tests/ontology/test_render.py`

- [ ] **Step 1: Write the test**

```python
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
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/ontology/test_render.py -v`
Expected: PASS, 14 tests. Whole directory: **`90 passed`** (74 existing + 14 + Task 4's 2).

- [ ] **Step 3: Prove Task 5 can fail**

The only task whose assertions are all about a term the tests themselves introduce, so it needs a mutant like the rest. Temporarily make `render_context` return its input unchanged. Expected: FAIL on the `context_out` assertion (6 of 14 — including the width band's 81 and 85, which an identity render reproduces at every width). Restore.

- [ ] **Step 4: Full verification**

Run: `make check > /tmp/check.log 2>&1; echo "exit: $?"; tail -3 /tmp/check.log`
Expected: exit 0, **`1230 passed, 20 deselected`**. `ruff format` rewrites files then reports failure — re-run before believing a red result (CLAUDE.md).

`make check` is `lint test` (`Makefile:18`) and does **not** run two blocking gates that this plan's files reach. Run both directly:

Run: `uv run python .saffron/gates/shacl.py; echo "exit: $?"`
Expected: a `pass` result, `0 violations across 2 graphs`. Without this the design's Phase A criterion — "the blocking `shacl` gate passing" — is asserted rather than checked.

Run: `uv run python .saffron/gates/typecheck.py; echo "exit: $?"`
Expected: a `pass` result, `no type errors`. Same reason, and not hypothetical: an earlier draft of Task 2's implementation left two `re` matches unguarded and this gate reported two `unresolved-attribute` diagnostics on them. `make check`'s `lint` target runs `prek`, which does run `ty` — but reading the gate's own JSON is what the criterion is stated in.

- [ ] **Step 5: Record that `SA-0044`'s workaround is spent**

`SA-0044` is a **completed** spec at `.saffron/specs/done/SA-0044-the-anti-theater-gate-is-unbuilt.md`. Its "Notes for the agent" tells the agent not to declare `saffron:revert` because the sides could not be reconciled from inside a cell, and it already said the operator would make the three edits together — which PR #112 did.

**Append one line; do not delete the paragraph.** Deleting it edits the record of why a shipped task was scoped as it was, which is exactly the kind of quiet history rewrite `docs/evidence/` exists to prevent. Add after the paragraph beginning **"Do not declare the gate in `ontology/saffron.ttl`."**:

> Discharged: PR #112 made the three edits by hand, and Phase A of `2026-09-02-ontology-authoritative.md` makes them one command.

Leave `touches`/`forbidden` unchanged.

- [ ] **Step 6: Commit**

```bash
git add tests/ontology/test_render.py .saffron/specs/done/SA-0044-the-anti-theater-gate-is-unbuilt.md
git commit -m "feat(ontology): one declaration reaches all three copies, so the note SA-0044 carried is spent"
```

---

### Task 6: `CLAUDE.md` stops claiming an authority it no longer has

Spec part 6 requires this and calls it the point: *"an authoritative file that is quietly no longer authoritative is the defect this design exists to remove, not one to introduce."* `CLAUDE.md:5-6` reads *"`DESIGN.md` is authoritative for what the system does; `CONTEXT.md` is authoritative for what the words mean."* After Task 2 that holds for the file as a whole but not for the five generated sets, where the vocabulary is authoritative and `CONTEXT.md` is its render.

**Files:**
- Modify: `CLAUDE.md`
- Modify: `tests/ontology/test_vocabulary_agrees_with_context.py` (docstring only)

- [ ] **Step 1: Amend the sentence**

One sentence, after the existing pair — the budget is ~200 lines and the file is the standing instruction surface for cells:

> For the five closed sets `tests/ontology/test_vocabulary_agrees_with_context.py` names, `ontology/saffron.ttl` is authoritative and `CONTEXT.md` is generated from it: edit the vocabulary and run `uv run python -m ontology.render`.

- [ ] **Step 2: Correct a count the cross-check has had wrong since before this plan**

`test_vocabulary_agrees_with_context.py`'s module docstring says the overlap is *"three sets both documents already enumerate"*; `CLOSED_SETS` holds **five**. Pre-existing, and not this plan's defect — but Task 2 makes that file the naming authority the `CLAUDE.md` sentence above points at, so it cannot be left saying the wrong number. One word.

- [ ] **Step 3: Verify**

Run: `uv run pytest tests/ tests/ontology/ -q && uv run python .saffron/gates/lint.py`
Expected: green, and `CLAUDE.md` still under its ~200-line budget.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md tests/ontology/test_vocabulary_agrees_with_context.py
git commit -m "docs(ontology): CLAUDE.md named CONTEXT.md authoritative for words the vocabulary now owns"
```

---

## Phase B — Appendix O's spike. **This is a gate.**

Not a task in the sense above: it produces a written answer, not a deliverable. **Do not begin it as part of Phase A's review cycle.** Its pass condition is `DESIGN.md` Appendix O's, quoted below, and it is the only thing that reopens §1.4.

Appendix O assumed §4.2.1's scheduler was unbuilt. It is now built — `saffron/scheduler.py:302` `protected_touch_refusal`, `:374` `retirement_refusal`, `:497` `_dependency_refusal`, `:572` `_refuse`, `:675` `build_queue` — so the experiment is **half the size Appendix O priced**: the Python arm exists, and only the shape arm has to be written.

- [x] **B1.** Hand-author a graph of in-flight tasks covering the refusal cases `scheduler.py` already implements, under `tests/ontology/fixtures/`.
- [x] **B2.** Express §4.2.1's refusal predicate as SHACL shapes over that graph. **Write them from §4.2.1's prose, not by reading `scheduler.py`.** This is the one place the shrunk experiment threatens its own result: questions 1 and 2 ask whether the shape form states something the Python leaves implicit and whether either catches what the other misses, and a shape arm transcribed from the Python inherits its blind spots by construction and answers both trivially. Appendix O priced two arms built from the same spec; only one of them still has to be built, so the discipline that made them independent has to be supplied by hand. Record in B3 which source each shape came from.
- [x] **B3.** Run both arms on the same fixtures and answer, in writing, appended to this plan:
  1. Does the shape form state a refusal the Python form leaves implicit?
  2. Does either catch a case the other misses, on the same fixtures?
  3. What does the graph cost to keep current, per scheduled task?
  4. Can the shape form be read by someone who has not read the Python?
- [x] **B4.** Apply Appendix O's rule verbatim: *"A yes on 1 and 4 with an acceptable 3 reopens §1.4. Anything else closes it, and `ontology/` stays what §9's v2.5 already says it is: a completed project."*

**If it closes:** stop. Phase A stands on its own, `ontology/queries/` stays as worked examples, and the plan's part 3 renderer is built on SQL as `2026-08-31-operator-visibility.md` already specifies. Record the answers anyway — a negative result that is written down is what stops the question being reopened by argument a third time.


### Phase B — the answers, and the verdict

Run 2026-09-04. The shape arm was written from §4.2 gate 0 and §4.2.1's prose
with `saffron/scheduler.py` unread, and the scheduler was opened only afterwards,
to score both arms on the same twelve hand-authored in-flight tasks. Artifacts
were kept out of the tree deliberately: the rule below closes the question, and
the plan says a closing result means they do not land.

**Appendix O's premise does not survive contact.** It says "its refusal predicate
is pure set containment". Four of the eight refusals are glob matching, not set
containment: `touches` against an open PR's changed files (2), a criterion's path
against `touches` (5), `touches` against protected paths (7), and a
`saffron:retired-by` marker against `touches` (8). Set containment is what the
other four are, and it is what shapes are for; the half the appendix rests on is
the half that is not.

**1. Does the shape form state a refusal the Python form leaves implicit?**
**No — and the inverse is true.** `_unmatched_criterion_path` carries a condition
§4.2.1 never states: a path token covered by the spec's own `forbidden` is a
citation, not a target, because `SA-0016`'s criteria name a path for a shape to
copy while forbidding that directory, and the unguarded form refused that very
spec. A shape arm written from the prose, as Appendix O requires, cannot contain
that rule — the prose does not have it. The Python also skips tokens holding glob
characters, and records a measured trade (two of seventeen falsely refused) that
has no declarative expression at all.

**2. Does either catch a case the other misses, on the same fixtures?**
**Yes, one-way: the shape arm misses, the Python does not.** On `**/size.py`
against `saffron/gates/core/size.py`, `scope.matches` returns `True` and the
task is admitted; the shape arm refuses it. That is a false refusal at gate 0,
which §4.2.1 prices at "a whole spec overnight with no cell started and nothing
to notice until morning". SHACL has no glob operator, and SPARQL's `REGEX` needs
a regex the graph does not carry. The empty-`touches` bug case failed the same
way for a different reason — `FILTER NOT EXISTS` is vacuously true over an empty
set, so the declarative form's *default* is the wrong answer, and the guard had
to be added after watching it refuse the whole bug class. The Python states that
skip as its first line. No case was found that the shape arm catches and the
Python misses.

**3. What does the graph cost to keep current, per scheduled task?**
**Unacceptable.** The refusal predicate needs 28 terms the vocabulary does not
have — a ~30% extension of 91 — because the run record describes tasks that have
*ended* and the scheduler reasons about tasks that have not. `TaskShape` requires
`endedInState` with `sh:minCount 1`, so an in-flight task cannot be represented
at all without failing the blocking `shacl` gate, and the vocabulary declares
zero in-flight states. `MERGE_TRAIN`, named twice in §4.2.1's own rules, is not
in the vocabulary either. Per scheduled task the emitter would carry the spec,
both `spec_sha`s, the state, every `touches` pattern, every criterion path,
`depends_on`, the open PR set with changed files, protected paths, retirement
markers and preflight status. And for the four glob refusals to work at all it
must also carry a **pre-translated regex per pattern** — reimplementing
`scope.matches` in the emitter, which is the second source of truth
`_unmatched_criterion_path`'s own docstring forbids in the same breath: *"the
same function `scope`, `integrity` and `size` all reuse, so 'declared' means one
thing in every gate — never a second, more permissive rule invented here."*

**4. Can the shape form be read by someone who has not read the Python?**
**No better than the Python, and it lies.** The four shapes are SPARQL text
carrying fully-qualified IRIs inside string literals, opaque to SHACL's own
validation; the readable half is the `sh:message`. It cannot state the
`forbidden` carve-out, and on `**/size.py` it states a refusal that is wrong. A
form that reads clearly and answers incorrectly is worse than one that reads
plainly and is right.

**B4 — the rule applied verbatim.** *"A yes on 1 and 4 with an acceptable 3
reopens §1.4. Anything else closes it."* No on 1, no on 4, and 3 is not
acceptable. **§1.4 stands, and `ontology/` stays what §9's v2.5 already says it
is: a completed project.** Phase A stands on its own — it made the vocabulary
authoritative for five closed sets it already described, which is documentation
generation and reopens nothing. `ontology/queries/` stays as worked examples, and
the operator-visibility renderer is built on SQL as
`2026-08-31-operator-visibility.md` specifies. Phases C-E are not written.

Recorded rather than left implicit, per the instruction above: a negative result
that is written down is what stops the question being reopened by argument a
third time. Principle 56 applies to this run too — it answers the operational
question on its own evidence, and nothing else.

---

## Phases C–E — deliberately not planned

The design's Phases C (emitter), D (query seam) and E (the plan's part 3 on the graph) **have no tasks here, and inventing them would be a placeholder.** Their content depends on Phase B's four answers: whether the shape form states refusals the Python leaves implicit determines what the emitter must carry, and question 3's cost determines whether materialisation is per-task or per-batch.

Write that plan after Phase B returns, from the answers. The design's part 6 already records what it must settle first: IRI minting for ledger rows and `prov:qualifiedAssociation` nodes, stable across re-emits because `Q4`'s chain depends on it; where the emitted graph lives; and whether `pyproject.toml`'s *"nothing under `saffron/` imports either"* is amended or the renderer loads its SPARQL from `ontology/queries/*.rq`.

## Self-review notes

- **Spec coverage.** Part 4 Phase A → Tasks 1–5. Part 6's `CLAUDE.md` amendment → **Task 6**, which an earlier draft of this plan left out entirely: the spec instructed it, this plan neither scheduled nor excluded it, and it is the one instruction the spec calls the defect the design exists to remove. Part 4 Phase B → Phase B above. Part 7's Phase A criterion → Task 5. Part 3's `test_no_dead_terms` correction → Task 5 Step 1's docstring, which states why the `sh:in` entry satisfies rather than exempts. Parts 3/4 Phases C–E → deliberately unplanned, with the reason stated.
- **Not covered, and named in the spec as such:** `Status`/EARL (spec part 6) is a decision, not a task, and is listed above as out of plan; it blocks nothing here because it is not one of the five cross-checked sets. `RATIONALE.md` is settled in the spec's own PR, in place and at zero net lines.
- **Every code block here was executed against the real files, and run through the blocking gates, before this plan was committed.** Executing them produced Task 2's `_WIDTH` band, the `_members` guard, and `probe` in place of `revert`. Running the *gates* over them produced the rest: `ty` rejected two unguarded `re` matches, `ruff format` rewrote three lines, and `make check` therefore could not reach the exit 0 Task 5 Step 4 claimed. Pytest-green is not gate-green, and this plan asserted the second having only measured the first.
- **Two stated numbers did not reproduce and are corrected above.** `_WIDTH = 80` does not collapse three sets onto single lines — dropping `textwrap.fill` does, which is the bug the first draft shipped and is now the mutant. Task 1's eight-member expectation was real but made the test a fourth hand-maintained copy of the set Phase A generates: with it, the spec's own part 7 success path reported `1 failed, 83 passed`. On a synthetic vocabulary it reports `90 passed`. A plan that prints runnable Python next to an expected result is making a measured claim, and CLAUDE.md's "run the tool, don't merely locate it" applies to it.
