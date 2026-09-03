# The ontology becomes authoritative — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Declaring a core gate in `ontology/saffron.ttl` alone updates `CONTEXT.md` and the SHACL shapes from it, with every ontology check green — then run the experiment `DESIGN.md` Appendix O specifies, which decides whether anything further is built.

**Architecture:** A generator reads `ontology/saffron.ttl` and rewrites two derived surfaces: the enumerations in `CONTEXT.md`'s closed-set definitions, and the `sh:in` lists in `ontology/shapes/saffron-shapes.ttl`. A drift test asserts the committed files equal the render. Nothing under `saffron/` imports the generator, and no runtime dependency is added.

**Tech Stack:** Python 3.14, `rdflib` and `pyoxigraph` (already dev-only deps), pytest, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-02-ontology-authoritative-design.md`

## Global Constraints

- **`saffron/` runtime dependencies stay `pydantic` and `pyyaml`.** The generator lives under `ontology/`, is dev-only, and must never be imported by anything under `saffron/`.
- **`CONTEXT.md` is injected into agent prompts** by `saffron/agents/context.py`. Do not add marker comments, HTML, or any generator scaffolding to it — the file must read exactly as it does now to a human and to an agent. The generator locates its regions by the existing bold term.
- **The `shacl` gate is blocking** (`.saffron/gates/shacl.py`) and validates every tracked `.ttl` against `ontology/shapes/`. A shapes file that fails SHACL fails the gate suite.
- **Bare "suite" means the gate suite** (`CONTEXT.md`). The repo's own tests are always "the test suite".
- **A new test is not trusted until it has been run against the unfixed code** — or, for one guarding a property already true, against a mutant that breaks it (CLAUDE.md). **A mutant must name a term that is undeclared everywhere.** `saffron:revert` is not one: `73c2b9f` (PR #112) declared it in all three surfaces, so appending it appends a duplicate triple and the suite stays green — measured, `74 passed`. Every mutant below uses `saffron:probe`, which is declared nowhere.
- **Commit subjects are lowercase `type(scope): what changed`**, written about the defect rather than the file.
- **Phase B is a gate.** Tasks 7+ do not exist until it returns, and its pass condition is `DESIGN.md` Appendix O's, not this plan's.

## File structure

| File | Responsibility |
|---|---|
| `ontology/render.py` (create) | The only generator. Reads the vocabulary; renders the two derived surfaces. Pure functions over text — no file writes except in `main()`. |
| `tests/ontology/test_render.py` (create) | Unit tests for member extraction and both renderers. |
| `tests/ontology/test_generated_surfaces_are_current.py` (create) | The drift test: committed files equal the render. |
| `CONTEXT.md` (modify) | Five enumerations become generated. Prose untouched. |
| `ontology/shapes/saffron-shapes.ttl` (modify, lines 81–90) | Two `sh:in` lists become generated. |
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
from ontology_paths import VOCABULARY

from ontology import render


def test_members_are_returned_in_vocabulary_source_order():
    """CONTEXT.md's terminal-state order is deliberate and is neither
    alphabetical nor rdflib's iteration order, so source order is the only
    rule that can reproduce the committed bytes."""
    assert render.members("CoreGate", vocabulary=VOCABULARY) == [
        "scope", "size", "secrets", "integrity", "census", "committed",
        "criteria", "revert",
    ]


def test_members_of_a_class_with_no_instances_is_empty_not_an_error():
    assert render.members("NoSuchClass", vocabulary=VOCABULARY) == []
```

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

Also create an empty `ontology/__init__.py` so `from ontology import render` resolves. Two things to confirm in this step rather than assume: that a test under `tests/ontology/` can `from ontology import render` (the suite's `conftest.py` puts that directory on the path, not the repo root), and that `pyproject.toml`'s `packages = ["saffron"]` keeps the new package out of the wheel — `uv build && unzip -l dist/*.whl | grep -c ontology/` should print `0`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/ontology/test_render.py -v`
Expected: PASS, 2 tests.

- [ ] **Step 5: Verify it is a real check, not a tautology**

Temporarily change `sorted(names, key=first_offset)` to `sorted(names)` and re-run. Expected: FAIL, alphabetical order (`census, committed, criteria, integrity, revert, scope, secrets, size`). Restore.

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
        text, vocabulary=VOCABULARY, _members={"Severity": ["blocker", "concern", "note", "wart"]}  # keyed by class
    )
    assert out == "**Severity**: `blocker`, `concern`, `note`, or `wart`.\n"


def test_prose_outside_the_backticked_span_is_untouched():
    text = "**Gate role**: A name in the contract — `format`, `lint`. The repo supplies it.\n"
    out = render.render_context(
        text, vocabulary=VOCABULARY, _members={"GateRole": ["format", "lint", "types"]}
    )
    assert out == "**Gate role**: A name in the contract — `format`, `lint`, `types`. The repo supplies it.\n"
```

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
    return re.match(r"[ \t]*", text[at:]).group()


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
        # `_members` is keyed by ontology class in both renderers, never by
        # the CONTEXT.md term — one key space, so a test reads the same either side.
        names = (_members or {}).get(class_name) or members(class_name, vocabulary=vocabulary)
        start = text.index(f"**{term}**")
        # First sentence: up to a period followed by whitespace or end of text.
        end = re.search(r"\.(?:\s|$)", text[start:]).start() + start
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
Expected: PASS, 5 tests. **The zero-line-diff test is the one that matters** — it proves the generator reproduces bytes a human wrote before it is trusted to write new ones. All five were run against the real `CONTEXT.md` while this plan was written; a sketch whose expected output has not been executed is the defect this step exists to catch.

- [ ] **Step 5: Prove the zero-diff test can fail**

Two mutants, because the join and the wrap fail independently:

1. Change `"or-comma"` to `"comma"` for `Severity`. Expected: FAIL on `test_each_closed_set_renders_the_committed_bytes_unchanged`.
2. Set `_WIDTH = 80`. Expected: FAIL on the same test, with a three-hunk diff collapsing `Gate role`, `Core gates` and `Terminal state` onto single lines. This is the mutant that matters — it is the bug the first draft of this plan shipped.

Restore both.

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

```python
from ontology_paths import ONTOLOGY

SHAPES_FILE = ONTOLOGY / "shapes" / "saffron-shapes.ttl"


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
        # Same rule as `render_context`: a fixture names the sets it is about.
        if _members is not None and class_name not in _members:
            continue
        names = (_members or {}).get(class_name) or members(class_name, vocabulary=vocabulary)
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
Expected: PASS, 7 tests.

- [ ] **Step 5: Prove the wrap rule is load-bearing**

Temporarily set `_PER_LINE = 4` and re-run. Expected: FAIL on the zero-diff shapes test. Restore.

- [ ] **Step 6: Commit**

```bash
git add ontology/render.py tests/ontology/test_render.py
git commit -m "feat(ontology): the shapes' sh:in lists are a third copy of the same closed sets"
```

---

### Task 4: The drift test, and `main()`

**Files:**
- Modify: `ontology/render.py`
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

Expected: BOTH tests FAIL, each naming the regenerate command.

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

- [ ] **Step 6: Commit**

```bash
git add ontology/render.py tests/ontology/test_generated_surfaces_are_current.py
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
Expected: PASS, 8 tests.

- [ ] **Step 3: Prove Task 5 can fail**

The only task whose assertions are all about a term the tests themselves introduce, so it needs a mutant like the rest. Temporarily make `render_context` return its input unchanged. Expected: FAIL on the `context_out` assertion. Restore.

- [ ] **Step 4: Full verification**

Run: `make check > /tmp/check.log 2>&1; echo "exit: $?"; tail -3 /tmp/check.log`
Expected: exit 0. `ruff format` rewrites files then reports failure — re-run before believing a red result (CLAUDE.md).

`make check` is `lint test` (`Makefile:18`) and does **not** run the `shacl` gate, which is a `.saffron/gates/` executable and is blocking on the file this plan rewrites. Run it directly too:

Run: `uv run python .saffron/gates/shacl.py; echo "exit: $?"`
Expected: a `pass` result. Without this step the design's Phase A criterion — "the blocking `shacl` gate passing" — is asserted rather than checked.

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

## Phase B — Appendix O's spike. **This is a gate.**

Not a task in the sense above: it produces a written answer, not a deliverable. **Do not begin it as part of Phase A's review cycle.** Its pass condition is `DESIGN.md` Appendix O's, quoted below, and it is the only thing that reopens §1.4.

Appendix O assumed §4.2.1's scheduler was unbuilt. It is now built — `saffron/scheduler.py:302` `protected_touch_refusal`, `:374` `retirement_refusal`, `:497` `_dependency_refusal`, `:572` `_refuse`, `:675` `build_queue` — so the experiment is **half the size Appendix O priced**: the Python arm exists, and only the shape arm has to be written.

- [ ] **B1.** Hand-author a graph of in-flight tasks covering the refusal cases `scheduler.py` already implements, under `tests/ontology/fixtures/`.
- [ ] **B2.** Express §4.2.1's refusal predicate as SHACL shapes over that graph.
- [ ] **B3.** Run both arms on the same fixtures and answer, in writing, appended to this plan:
  1. Does the shape form state a refusal the Python form leaves implicit?
  2. Does either catch a case the other misses, on the same fixtures?
  3. What does the graph cost to keep current, per scheduled task?
  4. Can the shape form be read by someone who has not read the Python?
- [ ] **B4.** Apply Appendix O's rule verbatim: *"A yes on 1 and 4 with an acceptable 3 reopens §1.4. Anything else closes it, and `ontology/` stays what §9's v2.5 already says it is: a completed project."*

**If it closes:** stop. Phase A stands on its own, `ontology/queries/` stays as worked examples, and the plan's part 3 renderer is built on SQL as `2026-08-31-operator-visibility.md` already specifies. Record the answers anyway — a negative result that is written down is what stops the question being reopened by argument a third time.

---

## Phases C–E — deliberately not planned

The design's Phases C (emitter), D (query seam) and E (the plan's part 3 on the graph) **have no tasks here, and inventing them would be a placeholder.** Their content depends on Phase B's four answers: whether the shape form states refusals the Python leaves implicit determines what the emitter must carry, and question 3's cost determines whether materialisation is per-task or per-batch.

Write that plan after Phase B returns, from the answers. The design's part 6 already records what it must settle first: IRI minting for ledger rows and `prov:qualifiedAssociation` nodes, stable across re-emits because `Q4`'s chain depends on it; where the emitted graph lives; and whether `pyproject.toml`'s *"nothing under `saffron/` imports either"* is amended or the renderer loads its SPARQL from `ontology/queries/*.rq`.

## Self-review notes

- **Spec coverage.** Part 4 Phase A → Tasks 1–5. Part 4 Phase B → Phase B above. Part 7's Phase A criterion → Task 5. Part 3's `test_no_dead_terms` correction → Task 5 Step 1's docstring, which states why the `sh:in` entry satisfies rather than exempts. Parts 3/4 Phases C–E → deliberately unplanned, with the reason stated.
- **Not covered, and named in the spec as such:** `Status`/EARL (spec part 6) is a decision, not a task, and is listed above as out of plan; it blocks nothing here because it is not one of the five cross-checked sets. `RATIONALE.md` is settled in the spec's own PR, in place and at zero net lines.
- **Every code block here was executed against the real files before this plan was committed.** That is what produced Task 1's eight-member expectation, Task 2's `_WIDTH` band, the `_members` guard, and `probe` in place of `revert` — four defects a reading pass had already missed. A plan that prints runnable Python next to an expected result is making a measured claim, and CLAUDE.md's "run the tool, don't merely locate it" applies to it.
