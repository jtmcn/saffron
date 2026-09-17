# Prose That Cannot Get Longer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two repo-defined gates over Saffron's living Markdown: `prose` (blocking, a file may not gain findings of any style rule) and `terms` (advisory, a curated list of avoided phrases), plus a commit-time hook and an edit-time hook that apply the same rules.

**Architecture:** One stdlib-only module, `.saffron/gates/prose.py`, parses Markdown and returns findings. Two `sh` wrappers expose it as gates, and baseline subtraction supplies the per-file limit because every `prose` failure's `message` is its rule code. `hooks/prose_limit.py` compares a staged file with its `HEAD` version at commit time and prints new findings at edit time. A new stdlib-only `ontology/spans.py` locates the text `ontology.render` writes, so the gate can exempt it without importing a graph library.

**Tech Stack:** Python 3.12 standard library, pytest, prek, git, Claude Code project hooks.

**Spec:** `docs/superpowers/specs/2026-09-16-prose-ratchet-design.md`

## Global Constraints

- `.saffron/gates/prose.py`, `ontology/spans.py` and `hooks/prose_limit.py` import only the standard library.
- A gate always exits 0 once it has printed its JSON. An advisory gate with findings reports `fail`, never `error` (`saffron/gates/runner.py:153-159`).
- `tool` comes from running `prose.py --version`, which hashes `prose.py` alone. It must be identical at base and head, or `suite_drift` aborts the comparison (`saffron/gates/baseline.py:88-99`).
- The gate runs from `/gates/.saffron/gates/` (the base commit) with cwd `/work`. It reads every other file from the cwd.
- No added line may contain a token from `.saffron/policy.yaml`'s `suppressions` list: `@pytest.mark.skip`, `pytest.skip(`, `xfail`, `# type: ignore`, `# ty: ignore`, `# noqa`, `ast-grep-ignore`, `unittest.skip`, `SkipTest`, `skipTest`, `importorskip`.
- Tests import `prose.py` and `prose_limit.py` inside test functions, never at module scope (the `revert` gate re-runs a witness with the script deleted, `tests/test_retired_vocabulary_hook.py:7-11`).
- Comments: one or two lines, the non-obvious "why" only (operator's global rule).
- Vocabulary: `terms` is **advisory**, never "warning" (`CONTEXT.md` §4). Never write the retired two-word term for one gate's execution.
- Commit subjects: lowercase `type(scope): what changed`, written as a sentence about the defect. End each message with the two attribution lines the session supplies.
- Branches: `joel/prose-ratchet` (PR 1, exists), `joel/prose-terms` (PR 2), `joel/prose-edit-hook` (PR 3), stacked with `gh stack`. Load the `gh-stack` skill before creating or submitting the stack. Never push with `--force` without the operator's approval in chat.

## Deviations from the design, decided while planning

- "Docker" is not in `AVOIDED`. It fails the entry bar: `DESIGN.md:377` and `DESIGN.md:1402` describe the real product. Its exemption is dropped with it.
- `EXCLUDED_DIRS` holds only `.saffron/specs/done/`. `docs/evidence/` and `docs/superpowers/` are outside every included directory, so they are already out of scope, and a test asserts it.
- `DESIGN.md` has no list of this repo's gates (§5.4 shows an example excerpt only), so PR 3 edits `CLAUDE.md` alone. `CLAUDE.md` is at 202 lines, over its ~200 budget, so the edit changes an existing line instead of adding one.
- The closed-set exemption in `CONTEXT.md` covers each definition's whole first sentence, the span `render_context` rewrites within.

## File Structure

| File | PR | Responsibility |
|---|---|---|
| `ontology/spans.py` (new) | 1 | Locate the rendered spans. Stdlib only. |
| `ontology/render.py` (modify) | 1 | Use `spans` for `SETS`, `MEMBER_TOKEN` and the first-sentence span. |
| `ontology/design_record.py` (modify) | 1 | Use `spans` for the principle index span. |
| `tests/ontology/test_spans.py` (new) | 1 | Spans on the real documents. |
| `.saffron/gates/prose.py` (new) | 1, 2 | Parse, rules, scope, gate entry point. |
| `.saffron/gates/prose` (new) | 1 | `sh` wrapper for the `prose` gate. |
| `.saffron/gates/terms` (new) | 2 | `sh` wrapper for the `terms` gate. |
| `.saffron/policy.yaml` (modify) | 1, 2 | Declare the gates. |
| `tests/test_prose_gate.py` (new) | 1, 2 | Rules, scope, spans, contract, subtraction, `AVOIDED`. |
| `tests/test_saffron_gates.py:32-41` (modify) | 1, 2 | The declared gate set. |
| `hooks/prose_limit.py` (new) | 1, 3 | Commit-time limit, then edit-time report. |
| `.pre-commit-config.yaml` (modify) | 1 | The `prose-limit` hook. |
| `tests/test_prose_limit_hook.py` (new) | 1, 3 | The hook in a temporary repository. |
| `.claude/settings.json` (modify) | 3 | The PostToolUse hook. |
| `CLAUDE.md:36` (modify) | 3 | Name the gate in Commands. |

---

## PR 1 — branch `joel/prose-ratchet`

### Task 1: Stdlib-only rendered spans

**Files:**
- Create: `ontology/spans.py`
- Modify: `ontology/render.py` (the `MEMBER_TOKEN` and `SETS` definitions, and the span lines in `render_context`)
- Modify: `ontology/design_record.py:141-173`
- Test: `tests/ontology/test_spans.py`

**Interfaces:**
- Produces: `spans.MEMBER_TOKEN: re.Pattern[str]`, `spans.SETS: dict[str, tuple[str, str]]`, `spans.PRINCIPLE_ANCHOR: str`, `spans.PRINCIPLE_HEADER: str`, `spans.definition_sentence(text: str, term: str) -> tuple[int, int]`, `spans.principle_index(text: str) -> tuple[int, int]`.
- `render.MEMBER_TOKEN` and `render.SETS` stay importable: `tests/ontology/test_vocabulary_agrees_with_context.py:49` and `tests/ontology/test_render.py:200,289` read them.

- [ ] **Step 1: Write the failing test**

```python
# tests/ontology/test_spans.py
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
    from ontology import design_record, render, spans

    assert render.SETS is spans.SETS
    assert render.MEMBER_TOKEN is spans.MEMBER_TOKEN
    assert design_record.ANCHOR == spans.PRINCIPLE_ANCHOR
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ontology/test_spans.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ontology.spans'` (and the ast test with `FileNotFoundError`).

- [ ] **Step 3: Create `ontology/spans.py`**

```python
"""Where `ontology.render` writes, located without a graph library.

`.saffron/gates/prose.py` exempts these spans and runs under a cell's plain
`python3`, so this module imports only the standard library.
"""

from __future__ import annotations

import re

# What counts as a member, and the only definition of it: `render` and the
# CONTEXT.md cross-check both import it, so the write span cannot exceed the
# read span. It rejects a token carrying a `.` or a `/`.
MEMBER_TOKEN = re.compile(r"`([A-Za-z_][A-Za-z0-9_-]*)`")

# CONTEXT.md bold term -> (ontology class, join style). The join styles are the
# ones already committed; a generator that normalised them would rewrite prose
# it does not own.
SETS = {
    "Terminal state": ("TerminalState", "comma"),
    "Batch stop reason": ("BatchStopReason", "or-comma"),
    "Severity": ("Severity", "or-comma"),
    "Risk tier": ("RiskTier", "or-plain"),
    "Gate role": ("GateRole", "comma"),
    "Core gates": ("CoreGate", "comma"),
}

PRINCIPLE_ANCHOR = "## Principles — an index"
PRINCIPLE_HEADER = "| # | The claim | From |\n|---|---|---|\n"


def definition_sentence(text: str, term: str) -> tuple[int, int]:
    """`(start, end)` of `**term**`'s first sentence, the span `render_context` rewrites within."""
    count = text.count(f"**{term}**")
    if count != 1:
        raise ValueError(f"{term}: expected exactly one definition, found {count}")
    start = text.index(f"**{term}**")
    # Bounded at the definition's own blank line. Unbounded, a definition
    # without a trailing period matched a period paragraphs away.
    block_end = text.find("\n\n", start)
    if block_end == -1:
        block_end = len(text)
    stop = re.search(r"\.(?:\s|$)", text[start:block_end])
    if stop is None:
        raise ValueError(f"{term}'s definition has no first sentence to rewrite")
    return start, start + stop.start()


def principle_index(text: str) -> tuple[int, int]:
    """`(start, end)` of the principle index table, its header included."""
    if text.count(PRINCIPLE_ANCHOR) != 1:
        raise ValueError(f"{PRINCIPLE_ANCHOR}: expected exactly one occurrence")
    start = text.find(PRINCIPLE_HEADER, text.index(PRINCIPLE_ANCHOR))
    if start == -1:
        header = PRINCIPLE_HEADER.splitlines()[0]
        raise ValueError(f"{PRINCIPLE_ANCHOR}: no `{header}` header under it")
    end = start + len(PRINCIPLE_HEADER)
    while end < len(text) and text[end] == "|":
        end = text.index("\n", end) + 1
    return start, end
```

- [ ] **Step 4: Point `render.py` at it**

In `ontology/render.py`, delete the `MEMBER_TOKEN = re.compile(...)` block with its comment, and the `SETS = {...}` block with its comment. Add after `from ontology import design_record`:

```python
from ontology.spans import MEMBER_TOKEN, SETS, definition_sentence
```

In `render_context`, replace everything from `if text.count(f"**{term}**") != 1:` through `sentence = text[start:end]` with:

```python
        start, end = definition_sentence(text, term)
        sentence = text[start:end]
```

Leave the rest of the loop body unchanged.

- [ ] **Step 5: Point `design_record.py` at it**

In `ontology/design_record.py`, replace the two constants:

```python
from ontology.spans import PRINCIPLE_ANCHOR, PRINCIPLE_HEADER, principle_index

ANCHOR = PRINCIPLE_ANCHOR
_HEADER = PRINCIPLE_HEADER
```

(put the import with the module's other imports). In `render_principles`, replace from `if text.count(ANCHOR) != 1:` through the `while` loop, keeping the `rows`/`body` lines, with:

```python
    start, end = principle_index(text)
```

so the function reads: `rows = ...`, the empty-rows `raise`, `body = ...`, `start, end = principle_index(text)`, then the unchanged `replaced` check and `return`.

- [ ] **Step 6: Run the ontology tests**

Run: `uv run pytest tests/ontology -v`
Expected: all PASS, including `test_generated_surfaces_are_current.py` (the render output is byte-identical).

- [ ] **Step 7: Mutant check**

Temporarily add `import rdflib` to `ontology/spans.py`, run `uv run pytest tests/ontology/test_spans.py::test_spans_imports_only_the_standard_library`, and confirm it FAILS. Remove the line.

- [ ] **Step 8: Commit**

```bash
git add ontology/spans.py ontology/render.py ontology/design_record.py tests/ontology/test_spans.py
git commit -m "refactor(ontology): the rendered spans could only be located by importing a graph library"
```

### Task 2: The `prose` rules

**Files:**
- Create: `.saffron/gates/prose.py`
- Test: `tests/test_prose_gate.py`

**Interfaces:**
- Consumes: `ontology/spans.py` from Task 1, loaded by file path from `root`.
- Produces: `Finding(line: int, code: str, excerpt: str)` (frozen dataclass), `check(text: str, path: str, gate: str, *, root: Path) -> list[Finding]`, `in_scope(path: str) -> bool`, `protected_words(root: Path) -> frozenset[str]`, constants `ROOT_FILES`, `INCLUDED_DIRS`, `EXCLUDED_DIRS`, `FILLER`, `SENTENCE_LIMIT`, `GATES`, and `main(argv: list[str]) -> int` (Task 3 fills it in).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_prose_gate.py
"""The `prose` gate (docs/superpowers/specs/2026-09-16-prose-ratchet-design.md).

The script is loaded inside each test, never at module scope: the `revert`
gate re-runs a new witness with the script deleted.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
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
    ("hedge", "The gate runs `should_pass` first."),
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
    assert _codes("- If the cell stops, run the gate.\n", ".saffron/specs/SA-0001-x.md") == []


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_prose_gate.py -v`
Expected: FAIL, every test, with `FileNotFoundError` for `.saffron/gates/prose.py`.

- [ ] **Step 3: Write `.saffron/gates/prose.py`**

```python
#!/usr/bin/env python3
"""The `prose` gate: Saffron's house style over its living Markdown.

Design: `docs/superpowers/specs/2026-09-16-prose-ratchet-design.md`. Parsing
adapts `strip_code` and `sentences` from AminBlg/SimpleEnglish
(`evals/ste_lint.py`, MIT), changed to keep every newline so that a finding's
line is its source line.

A `prose` failure's `message` is its rule code, so baseline subtraction cancels
one pre-existing finding per file and rule (§5.4). `hooks/prose_limit.py`
applies the same limit to a commit.

Standard library only: the gate runs under a cell's plain `python3`, from the
base commit's `.saffron/`, and reads everything else from the cwd.
"""

from __future__ import annotations

import bisect
import functools
import importlib.util
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GATES = ("prose",)

ROOT_FILES = ("CONTEXT.md", "CLAUDE.md", "DESIGN.md", "README.md")
INCLUDED_DIRS = ("docs/backlog/", ".saffron/specs/", ".claude/agents/", ".claude/skills/")
# A finished spec records what a cell was told, so it stays as written.
EXCLUDED_DIRS = (".saffron/specs/done/",)

SENTENCE_LIMIT = 25
# Saffron's own intensifiers, measured. "exactly" and "deliberately" carry meaning here.
FILLER = (
    "actually",
    "genuinely",
    "precisely",
    "merely",
    "simply",
    "just",
    "very",
    "really",
    "obviously",
    "clearly",
    "essentially",
    "basically",
    "quietly",
    "in fact",
    "note that",
)

HEDGE = re.compile(r"\b(?:should|may|might)\b", re.I)
EM_DASH = re.compile(r"—|(?<!\d)–(?!\d)|(?<=\s)--(?=\s)|(?<=[A-Za-z]) - (?=[A-Za-z])")
SEMICOLON = re.compile(";")
PERFECT = re.compile(r"\b(?:has|have|had)\s+been\b|\b(?:has|have)\s+\w+ed\b", re.I)
CONTRACTION = re.compile(r"\b\w+(?:n['’]t|['’]ll|['’]re|['’]ve|['’]d)\b|\bit['’]s\b", re.I)
TRAILING = re.compile(r"\s(?:if|when)\s", re.I)
WORD_RULES = (
    ("hedge", HEDGE),
    ("em-dash", EM_DASH),
    ("semicolon", SEMICOLON),
    ("perfect-tense", PERFECT),
    ("contraction", CONTRACTION),
)

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[^\n]*$", re.S | re.M)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_HEADING = re.compile(r"^#{1,6}\s.*$", re.M)
_TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$", re.M)
_TABLE_ROW = re.compile(r"^[ \t]*\|(.*)\|[ \t]*$", re.M)
_CODE_SPAN = re.compile(r"`[^`\n]+`")
_URL = re.compile(r"https?://\S+")
_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
_BREAK = re.compile(r"(?<=[.!?:])\s+|\n[ \t]*\n\s*|\n(?=[ \t]*(?:[-*+]|\d+\.)[ \t])")
_ITEM = re.compile(r"[ \t]*(?:[-*+]|\d+\.)[ \t]+(?:\[[ xX]\][ \t]+)?")
_BOLD_TERM = re.compile(r"^\*\*([^*]+)\*\*", re.M)


@dataclass(frozen=True)
class Finding:
    line: int
    code: str
    excerpt: str


@dataclass(frozen=True)
class _Sentence:
    start: int
    text: str
    is_item: bool


class _Text:
    """Prepared Markdown, with line lookups by offset."""

    def __init__(self, body: str) -> None:
        self.body = body
        self._newlines = [m.start() for m in re.finditer("\n", body)]

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self._newlines, offset) + 1

    def line_text(self, offset: int) -> str:
        n = bisect.bisect_right(self._newlines, offset)
        start = self._newlines[n - 1] + 1 if n else 0
        end = self._newlines[n] if n < len(self._newlines) else len(self.body)
        return self.body[start:end]


def in_scope(path: str) -> bool:
    if not path.endswith(".md") or path.startswith(EXCLUDED_DIRS):
        return False
    return path in ROOT_FILES or path.startswith(INCLUDED_DIRS)


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _cells(match: re.Match[str]) -> str:
    cells = [cell.strip() for cell in match.group(1).split("|")]
    return ". ".join(cell for cell in cells if cell) + "."


def _prepare(text: str) -> str:
    """Remove what is not prose. Every newline stays where it was."""
    for pattern in (_FRONTMATTER, _FENCE, _COMMENT, _HEADING, _TABLE_RULE):
        text = pattern.sub(_blank, text)
    text = _TABLE_ROW.sub(_cells, text)
    # One word per span, with no padding, so "`a`, `b`" is not read as four words.
    text = _CODE_SPAN.sub("CODESPAN", text)
    return _URL.sub(" URL ", text)


def _sentences(body: str) -> Iterator[_Sentence]:
    pos = 0
    for match in [*_BREAK.finditer(body), None]:
        end = match.start() if match else len(body)
        chunk = body[pos:end]
        item = _ITEM.match(chunk)
        offset = pos + (item.end() if item else len(chunk) - len(chunk.lstrip()))
        text = body[offset:end].strip()
        if len(text.split()) >= 2:
            yield _Sentence(offset, text, item is not None)
        if match:
            pos = match.end()


def _excerpt(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= 80 else flat[:79] + "…"


@functools.cache
def _spans(root: Path) -> Any:
    """`ontology/spans.py` from the tree under judgement, loaded by path."""
    path = root / "ontology" / "spans.py"
    spec = importlib.util.spec_from_file_location("saffron_ontology_spans", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rendered(text: str, path: str, root: Path) -> list[tuple[int, int]]:
    """What `ontology.render` writes. A long rendered line is fixed at its source."""
    if path == "DESIGN.md":
        spans = _spans(root)
        return [spans.principle_index(text)] if spans.PRINCIPLE_ANCHOR in text else []
    if path == "CONTEXT.md":
        spans = _spans(root)
        return [
            spans.definition_sentence(text, term)
            for term in spans.SETS
            if f"**{term}**" in text
        ]
    return []


@functools.cache
def protected_words(root: Path) -> frozenset[str]:
    """Defined terms and closed-set members, which no filler list may name."""
    context = root / "CONTEXT.md"
    if not context.exists():
        return frozenset()
    text = context.read_text(encoding="utf-8")
    words = {
        part.strip().lower()
        for term in _BOLD_TERM.findall(text)
        for part in term.split("/")
    }
    spans = _spans(root)
    for term in spans.SETS:
        if f"**{term}**" in text:
            start, end = spans.definition_sentence(text, term)
            words.update(m.lower() for m in spans.MEMBER_TOKEN.findall(text[start:end]))
    return frozenset(words)


@functools.cache
def _filler_pattern(
    filler: tuple[str, ...], protected: frozenset[str]
) -> re.Pattern[str] | None:
    kept = [word for word in filler if word not in protected]
    if not kept:
        return None
    alternation = "|".join(re.escape(word).replace(r"\ ", r"\s+") for word in kept)
    return re.compile(rf"\b(?:{alternation})\b", re.I)


def _style(text: _Text, path: str, root: Path) -> list[Finding]:
    found = []
    spec = path.startswith(".saffron/specs/")
    for sentence in _sentences(text.body):
        if len(sentence.text.split()) > SENTENCE_LIMIT:
            found.append(
                Finding(text.line(sentence.start), "sentence-length", _excerpt(sentence.text))
            )
        if (
            spec
            and sentence.is_item
            and TRAILING.search(sentence.text)
            and not re.match(r"(?:if|when)\b", sentence.text, re.I)
        ):
            found.append(
                Finding(text.line(sentence.start), "trailing-condition", _excerpt(sentence.text))
            )
    # A quoted word is a mention, and CONTEXT.md quotes the words it rules on.
    unquoted = _QUOTED.sub(_blank, text.body)
    rules = list(WORD_RULES)
    filler = _filler_pattern(FILLER, protected_words(root))
    if filler is not None:
        rules.append(("filler", filler))
    for code, pattern in rules:
        for match in pattern.finditer(unquoted):
            line = text.line(match.start())
            found.append(Finding(line, code, _excerpt(text.line_text(match.start()))))
    return found


def check(text: str, path: str, gate: str, *, root: Path) -> list[Finding]:
    """Every finding `gate` reports for `text`, read as the file at `path`."""
    if gate not in GATES:
        raise ValueError(f"unknown gate: {gate}")
    for start, end in _rendered(text, path, root):
        text = text[:start] + re.sub(r"[^\n]", " ", text[start:end]) + text[end:]
    prepared = _Text(_prepare(text))
    found = _style(prepared, path, root)
    return sorted(found, key=lambda f: (f.line, f.code))


def main(argv: list[str]) -> int:
    raise NotImplementedError("Task 3")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Task 3 adds the imports its `main` needs. This step imports only what the rules use, so `ruff` passes.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prose_gate.py -v`
Expected: all PASS. If a MISSES case fails, fix the rule, not the case: each case is a measured false positive.

- [ ] **Step 5: Mutant checks**

Run each mutation, confirm the named test FAILS, then revert it:
- In `_style`, replace `protected_words(root)` with `frozenset()` → `test_a_defined_term_is_never_filler` and `test_the_real_vocabulary_protects_elevated` fail.
- In `check`, delete the `for start, end in _rendered(...)` loop → both rendered-span tests fail.
- In `_style`, drop `and sentence.is_item` → `test_a_trailing_condition_is_read_only_in_a_spec_instruction` still passes. Instead drop `spec and` → it fails.

- [ ] **Step 6: Lint and type-check**

Run: `uv run ruff check .saffron/gates/prose.py tests/test_prose_gate.py && uv run ruff format --check .saffron/gates/prose.py tests/test_prose_gate.py && uv run ty check`
Expected: clean. If `ruff format` rewrites the `FILLER` tuple despite `# fmt: skip`, accept its layout and delete the marker.

- [ ] **Step 7: Commit**

```bash
git add .saffron/gates/prose.py tests/test_prose_gate.py
git commit -m "feat(gates): nothing measured the house style of the prose a cell reads"
```

### Task 3: The `prose` gate

**Files:**
- Modify: `.saffron/gates/prose.py` (`main`)
- Create: `.saffron/gates/prose` (executable)
- Modify: `.saffron/policy.yaml` (the `gates:` map)
- Modify: `tests/test_saffron_gates.py:32-41`
- Test: `tests/test_prose_gate.py`

**Interfaces:**
- Consumes: `check`, `in_scope`, `GATES` from Task 2.
- Produces: the `prose` gate's JSON contract, and `prose.py --version` printing `saffron-prose <12 hex>`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_prose_gate.py`)

```python
def _run_gate(name: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(GATES / name)], cwd=cwd, capture_output=True, text=True, timeout=120
    )


def _init(repo: Path, files: dict[str, str]) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)


def test_prose_names_its_tool_and_reports_on_this_repo():
    from saffron.gates.contract import parse_gate_json

    done = _run_gate("prose", REPO)
    assert done.returncode == 0, done.stderr
    result = parse_gate_json(done.stdout, expected_gate="prose")
    assert result.status in ("pass", "fail"), result.summary
    assert result.tool and result.tool.startswith("saffron-prose ")
    assert all(f.message == f.code for f in result.failures)


def test_prose_reports_the_version_the_script_printed():
    from saffron.gates.contract import parse_gate_json

    printed = subprocess.run(
        [sys.executable, str(SCRIPT), "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    result = parse_gate_json(_run_gate("prose", REPO).stdout, expected_gate="prose")
    assert result.tool == printed


def test_prose_passes_a_clean_tree_and_fails_a_long_sentence(tmp_path):
    from saffron.gates.contract import parse_gate_json

    _init(tmp_path, {"README.md": "The gate passes.\n", "notes.txt": LONG_A})
    clean = parse_gate_json(_run_gate("prose", tmp_path).stdout, expected_gate="prose")
    assert (clean.status, clean.failures) == ("pass", [])

    (tmp_path / "README.md").write_text(LONG_A + "\n")
    red = parse_gate_json(_run_gate("prose", tmp_path).stdout, expected_gate="prose")
    assert red.status == "fail"
    assert [(f.file, f.line, f.code) for f in red.failures] == [
        ("README.md", 1, "sentence-length")
    ]


def test_prose_errors_rather_than_passes_when_nothing_is_in_scope(tmp_path):
    from saffron.gates.contract import parse_gate_json

    _init(tmp_path, {"notes.txt": "nothing to read\n"})
    result = parse_gate_json(_run_gate("prose", tmp_path).stdout, expected_gate="prose")
    assert result.status == "error"
    assert "in scope" in result.summary


def test_a_rewritten_finding_is_not_new_and_an_added_one_is():
    """The per-file limit is baseline subtraction over `(file, code, code)`."""
    from saffron.gates.baseline import subtract_baseline
    from saffron.gates.contract import Failure, GateResult

    prose = _prose()

    def result(text: str) -> GateResult:
        failures = [
            Failure(file="README.md", line=f.line, code=f.code, message=f.code)
            for f in prose.check(text, "README.md", "prose", root=REPO)
        ]
        return GateResult(gate="prose", status="fail", tool="t", failures=failures)

    base = [result(LONG_A + "\n")]
    assert subtract_baseline([result("Intro.\n\n" + LONG_B + "\n")], base) == []
    added = subtract_baseline([result(LONG_A + "\n\n" + LONG_B + "\n")], base)
    assert [(n.gate, n.failure.code) for n in added] == [("prose", "sentence-length")]


def test_scope_reaches_every_place_it_names():
    prose = _prose()
    listed = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    for name in prose.ROOT_FILES:
        assert name in listed and prose.in_scope(name), name
    for directory in prose.INCLUDED_DIRS:
        assert any(p.startswith(directory) and prose.in_scope(p) for p in listed), directory


def test_scope_leaves_the_records_alone():
    prose = _prose()
    assert prose.EXCLUDED_DIRS == (".saffron/specs/done/",)
    for record in (
        ".saffron/specs/done/SA-0001-x.md",
        "docs/evidence/2026-01-01-x.md",
        "docs/superpowers/specs/x.md",
        "docs/backlog/notes.txt",
    ):
        assert not prose.in_scope(record), record
    assert prose.in_scope(".claude/skills/a/b/SKILL.md")
```

In `tests/test_saffron_gates.py`, change the set in `test_the_policy_parses` to add `"prose"`:

```python
    assert set(policy.gates) == {
        "format",
        "lint",
        "types",
        "tests",
        "shacl",
        "structure",
        "prose",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_prose_gate.py tests/test_saffron_gates.py::test_the_policy_parses -v`
Expected: the gate tests FAIL (`FileNotFoundError` for `.saffron/gates/prose`, or `NotImplementedError`), the policy test FAILS on the missing `prose`, and `test_a_rewritten_finding_is_not_new_and_an_added_one_is` and the scope tests PASS already (they read Task 2's code).

- [ ] **Step 3: Write `main`** (replace the stub in `prose.py`)

Add to the imports: `import hashlib`, `import json`, `import subprocess`, and `from collections import Counter`. Then:

```python
def _emit(payload: dict[str, object]) -> int:
    print(json.dumps(payload))
    return 0


def _listed(root: Path) -> subprocess.CompletedProcess[str]:
    # Untracked files count: a cell's edits reach the gates before any commit.
    return subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        text=True,
    )


def main(argv: list[str]) -> int:
    if argv == ["--version"]:
        digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
        print(f"saffron-prose {digest}")
        return 0
    if len(argv) != 1 or argv[0] not in GATES:
        print(f"usage: prose.py --version | {' | '.join(GATES)}", file=sys.stderr)
        return 2
    gate = argv[0]
    try:
        version = subprocess.run(
            [sys.executable, __file__, "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _emit({"gate": gate, "status": "error", "summary": f"--version failed: {exc}"})
    tool = version.stdout.strip()
    if version.returncode != 0 or not tool:
        return _emit({"gate": gate, "status": "error", "summary": "--version printed nothing"})

    root = Path.cwd()
    listed = _listed(root)
    if listed.returncode != 0:
        summary = f"git ls-files failed: {listed.stderr.strip()}"
        return _emit({"gate": gate, "status": "error", "tool": tool, "summary": summary})
    paths = sorted(
        {p for p in listed.stdout.split("\0") if p and in_scope(p) and (root / p).is_file()}
    )
    if not paths:
        summary = "no Markdown file is in scope, so nothing was read"
        return _emit({"gate": gate, "status": "error", "tool": tool, "summary": summary})

    failures: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    try:
        for path in paths:
            text = (root / path).read_text(encoding="utf-8", errors="replace")
            for finding in check(text, path, gate, root=root):
                message = finding.code if gate == "prose" else finding.excerpt
                failures.append(
                    {"file": path, "line": finding.line, "code": finding.code, "message": message}
                )
                counts[finding.code] += 1
    except (OSError, ValueError) as exc:
        summary = f"{type(exc).__name__}: {exc}"
        return _emit({"gate": gate, "status": "error", "tool": tool, "summary": summary})

    by_code = ", ".join(f"{code} {n}" for code, n in counts.most_common())
    return _emit(
        {
            "gate": gate,
            "status": "fail" if failures else "pass",
            "tool": tool,
            "failures": failures,
            "summary": f"{len(failures)} findings in {len(paths)} files. {by_code}".strip(),
        }
    )
```

- [ ] **Step 4: Write the wrapper and declare the gate**

```sh
#!/bin/sh
exec python3 "$(dirname "$0")/prose.py" prose
```

Save it as `.saffron/gates/prose`, then run `chmod +x .saffron/gates/prose`.

In `.saffron/policy.yaml`, add after the `structure:` entry:

```yaml
  # House style over living Markdown. It fails at base as well: subtraction
  # counts, so a task fails only when a file gains findings of one rule.
  prose: { blocking: true }
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prose_gate.py tests/test_saffron_gates.py -v`
Expected: all PASS, including `test_no_gate_script_shadows_a_stdlib_module`.

- [ ] **Step 6: Mutant check**

Replace `tool = version.stdout.strip()` with a literal and run `uv run ast-grep scan -c .saffron/sgconfig.yml .saffron/gates/prose.py`. Expected: `gate-tool-must-be-executed` fires. Revert.

- [ ] **Step 7: Measure the gate on the repository**

Run: `time .saffron/gates/prose | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['status'], r['tool'], r['summary'])"`
Expected: `fail`, a `saffron-prose` tool, a summary with per-rule counts, well under the 900 s gate timeout. Record the summary line for the PR body.

- [ ] **Step 8: Commit**

```bash
git add .saffron/gates/prose.py .saffron/gates/prose .saffron/policy.yaml tests/test_prose_gate.py tests/test_saffron_gates.py
git commit -m "feat(gates): a task could lengthen the prose a cell reads and still come back green"
```

### Task 4: The commit-time limit

**Files:**
- Create: `hooks/prose_limit.py`
- Modify: `.pre-commit-config.yaml` (after the `retired-vocabulary` hook)
- Test: `tests/test_prose_limit_hook.py`

**Interfaces:**
- Consumes: `check`, `in_scope`, `Finding` from `.saffron/gates/prose.py`, loaded by path.
- Produces: `load_prose() -> ModuleType`, `new_findings(prose, root: Path, gate: str, path: str, old_text: str | None, new_text: str) -> list[Finding]`, `rises(prose, root, gate, path, old_text, new_text) -> dict[str, tuple[int, int]]`, `commit_time(root: Path) -> int`, `main(argv: list[str]) -> int`. Task 9 adds `edit_time`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_prose_limit_hook.py
"""`hooks/prose_limit.py`: a staged file may not gain findings of any `prose` rule."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "hooks" / "prose_limit.py"
LONG_A = "alpha " * 30 + "end."
LONG_B = "beta " * 30 + "end."


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    _git(tmp_path, "init", "-q")
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def _stage(repo: Path, name: str, text: str) -> None:
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(text)
    _git(repo, "add", "-A")


def _hook(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK), *args], cwd=repo, capture_output=True, text=True
    )


def test_an_added_long_sentence_fails(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "README.md", "Short.\n\n" + LONG_A + "\n")
    done = _hook(repo)
    assert done.returncode == 1
    assert "README.md: sentence-length rose from 0 to 1" in done.stdout
    assert "README.md:3:" in done.stdout


def test_a_rewritten_finding_passes(tmp_path):
    repo = _repo(tmp_path, {"README.md": LONG_A + "\n"})
    _stage(repo, "README.md", LONG_B + "\n")
    assert _hook(repo).returncode == 0


def test_a_new_file_compares_against_nothing(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "docs/backlog/1-new.md", LONG_A + "\n")
    done = _hook(repo)
    assert done.returncode == 1
    assert "docs/backlog/1-new.md: sentence-length rose from 0 to 1" in done.stdout


def test_a_rename_keeps_its_count(tmp_path):
    repo = _repo(tmp_path, {"docs/backlog/1-a.md": LONG_A + "\n"})
    _git(repo, "mv", "docs/backlog/1-a.md", "docs/backlog/2-b.md")
    assert _hook(repo).returncode == 0


def test_a_file_out_of_scope_is_not_read(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "docs/evidence/x.md", LONG_A + "\n")
    assert _hook(repo).returncode == 0


def test_prek_runs_the_hook_on_markdown():
    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    hooks = [hook for repo in config["repos"] for hook in repo["hooks"]]
    (hook,) = [hook for hook in hooks if hook["id"] == "prose-limit"]
    assert hook["entry"] == "uv run hooks/prose_limit.py"
    assert hook["pass_filenames"] is False
    assert hook["files"] == r"\.md$"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_prose_limit_hook.py -v`
Expected: FAIL. The hook tests exit 2 with `can't open file`, and the config test raises `ValueError: not enough values to unpack`.

- [ ] **Step 3: Write `hooks/prose_limit.py`**

```python
#!/usr/bin/env python3
"""The `prose` gate's limit, applied to a commit.

Each staged Markdown file in scope may not carry more findings of any `prose`
rule than its `HEAD` version. A new file compares against zero, and a rename
against its old path. The gate gets the same limit from baseline subtraction.
Standard library only, like the gate it loads.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROSE = Path(__file__).resolve().parent.parent / ".saffron" / "gates" / "prose.py"


def load_prose() -> Any:
    spec = importlib.util.spec_from_file_location("saffron_prose_gate", PROSE)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(PROSE)
    module = importlib.util.module_from_spec(spec)
    # Registered first: `Finding` is a dataclass under postponed annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def staged(root: Path) -> list[tuple[str | None, str]]:
    """`(path at HEAD or None, staged path)` for each added, modified or renamed file."""
    done = _git(root, "diff", "--cached", "--name-status", "-M", "-z", "--diff-filter=AMR")
    done.check_returncode()
    fields = done.stdout.split("\0")
    pairs: list[tuple[str | None, str]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        if status.startswith("R"):
            pairs.append((fields[i + 1], fields[i + 2]))
            i += 3
        else:
            pairs.append((None if status == "A" else fields[i + 1], fields[i + 1]))
            i += 2
    return pairs


def new_findings(
    prose: Any, root: Path, gate: str, path: str, old_text: str | None, new_text: str
) -> list[Any]:
    """Findings in `new_text` with no matching excerpt in `old_text`, counted."""
    before = Counter(
        f.excerpt for f in prose.check(old_text or "", path, gate, root=root)
    )
    fresh = []
    for finding in prose.check(new_text, path, gate, root=root):
        if before[finding.excerpt]:
            before[finding.excerpt] -= 1
        else:
            fresh.append(finding)
    return fresh


def rises(
    prose: Any, root: Path, gate: str, path: str, old_text: str | None, new_text: str
) -> dict[str, tuple[int, int]]:
    """Rule codes whose count went up, as `code -> (before, after)`."""
    before = Counter(f.code for f in prose.check(old_text or "", path, gate, root=root))
    after = Counter(f.code for f in prose.check(new_text, path, gate, root=root))
    return {code: (before[code], n) for code, n in after.items() if n > before[code]}


def _show(root: Path, spec: str) -> str:
    done = _git(root, "show", spec)
    done.check_returncode()
    return done.stdout


def commit_time(root: Path) -> int:
    prose = load_prose()
    failed = False
    for old, new in staged(root):
        if not prose.in_scope(new):
            continue
        old_text = _show(root, f"HEAD:{old}") if old else None
        new_text = _show(root, f":{new}")
        risen = rises(prose, root, "prose", new, old_text, new_text)
        for code, (was, now) in sorted(risen.items()):
            print(f"{new}: {code} rose from {was} to {now}")
            failed = True
        for finding in new_findings(prose, root, "prose", new, old_text, new_text):
            if finding.code in risen:
                print(f"  {new}:{finding.line}: {finding.code}: {finding.excerpt}")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    if argv:
        print(f"unexpected arguments: {argv}", file=sys.stderr)
        return 2
    return commit_time(Path.cwd())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Register the hook**

In `.pre-commit-config.yaml`, append after the `retired-vocabulary` hook's block:

```yaml
  # The `prose` gate's rules per commit: a staged file in scope may not gain
  # findings of any rule. Scope lives in `.saffron/gates/prose.py`.
  - repo: local
    hooks:
      - id: prose-limit
        name: prose limit (the prose gate's rules)
        language: system
        entry: uv run hooks/prose_limit.py
        pass_filenames: false
        files: \.md$
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prose_limit_hook.py -v`
Expected: all PASS.

- [ ] **Step 6: Mutant checks**

- In `staged`, replace the rename branch's `fields[i + 1]` with `None` → `test_a_rename_keeps_its_count` fails. Revert.
- In `commit_time`, delete `if not prose.in_scope(new): continue` → `test_a_file_out_of_scope_is_not_read` fails. Revert.

- [ ] **Step 7: Commit, letting the new hook run**

```bash
git add hooks/prose_limit.py .pre-commit-config.yaml tests/test_prose_limit_hook.py
git commit -m "feat(hooks): a commit could lengthen the prose a cell reads and nothing said so"
```

Expected: prek skips `prose-limit` (no Markdown staged) and the commit lands.

### Task 5: Verify and open PR 1

- [ ] **Step 1: Run everything**

Run: `make check && uv run ast-grep test -c .saffron/sgconfig.yml && .saffron/gates/structure`
Expected: all green, and `structure` reports `pass`.

- [ ] **Step 2: Prove the hook blocks a real commit**

Append one sentence of 30 words to `README.md`, `git add README.md`, and run `git commit -m "test"`. Expected: `prose-limit` fails and names `README.md: sentence-length rose`. Then run `git restore --staged README.md && git restore README.md`.

- [ ] **Step 3: Push and open the PR**

Load the `gh-stack` skill, and follow it to make `joel/prose-ratchet` the stack's first layer. The PR body states: what the gate enforces, the Task 3 Step 7 summary line, the ledger cost (one row per finding per suite, a few thousand rows), and the design and plan paths. End it with the session's PR attribution lines. Ask the operator before any push the skill says needs approval.

---

## PR 2 — branch `joel/prose-terms`, stacked on PR 1

### Task 6: The `terms` gate

**Files:**
- Modify: `.saffron/gates/prose.py` (`GATES`, `AVOIDED`, `_avoided`, `check`)
- Create: `.saffron/gates/terms` (executable)
- Modify: `.saffron/policy.yaml`
- Modify: `tests/test_saffron_gates.py:32-41`
- Test: `tests/test_prose_gate.py`

**Interfaces:**
- Consumes: `_Text`, `_QUOTED`, `_blank`, `Finding` from Task 2, `main` from Task 3.
- Produces: `AVOIDED: dict[str, tuple[str, str]]` (phrase → (term to use, `CONTEXT.md` section)), and `check(..., "terms", ...)` returning `avoided-term` findings whose `excerpt` is the message.

- [ ] **Step 1: Create the branch**

Follow the `gh-stack` skill to add a layer named `joel/prose-terms` on top of `joel/prose-ratchet`.

- [ ] **Step 2: Measure the entry bar**

For each candidate phrase, list its hits in scope with code spans, fences and quotes removed:

```bash
uv run python - <<'EOF'
import importlib.util, re, subprocess, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("p", ".saffron/gates/prose.py")
p = importlib.util.module_from_spec(spec); sys.modules["p"] = p; spec.loader.exec_module(p)
phrases = ["sandbox", "self-heal", "auto-fix", "soft fail", "ticket", "work item", "the denylist"]
files = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
for f in (f for f in files if p.in_scope(f)):
    body = p._QUOTED.sub(p._blank, p._prepare(Path(f).read_text()))
    for phrase in phrases:
        for m in re.finditer(r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b", body, re.I):
            print(f, body.count("\n", 0, m.start()) + 1, phrase)
EOF
```

Expected: no output. Planning measured zero hits for all seven. If a hit appears, read it. Drop the phrase from `AVOIDED` if the hit is a legitimate use, and fix the text if it is a misuse.

- [ ] **Step 3: Write the failing tests** (append to `tests/test_prose_gate.py`)

```python
def _terms(text: str) -> list[str]:
    return [f.excerpt for f in _prose().check(text, "README.md", "terms", root=REPO)]


def test_an_avoided_phrase_names_the_term_to_use():
    assert _terms("The agent runs in a sandbox.") == [
        'sandbox: say "cell" (CONTEXT.md §1)'
    ]
    assert _terms("A soft\nfail is reported.") == [
        'soft fail: say "advisory" (CONTEXT.md §4)'
    ]


def test_a_quoted_or_coded_phrase_is_a_mention():
    assert _terms('Say "cell", not "sandbox".') == []
    assert _terms("It calls `sandbox.exec()`.") == []


def _definitions(context: str) -> dict[str, tuple[str, str]]:
    """Bold term part -> (its block, its `## N.` section)."""
    found: dict[str, tuple[str, str]] = {}
    section = ""
    for block in context.split("\n\n"):
        heading = re.match(r"## (\d+)\.", block)
        if heading:
            section = f"§{heading.group(1)}"
        bold = re.match(r"\*\*([^*]+)\*\*", block.strip())
        if bold:
            for part in bold.group(1).split("/"):
                # The first definition wins; a later bold lead is not the term.
                found.setdefault(part.strip().lower(), (block, section))
    return found


def _check_avoided_agrees(context: str) -> list[str]:
    problems = []
    definitions = _definitions(context)
    for phrase, (term, section) in _prose().AVOIDED.items():
        if term not in definitions:
            problems.append(f"{term}: no bold definition")
            continue
        block, found_section = definitions[term]
        avoid = block[block.find("_Avoid_") :] if "_Avoid_" in block else ""
        if f'"{phrase}"'.lower() not in avoid.lower():
            problems.append(f"{phrase}: not quoted on {term}'s _Avoid_ line")
        if found_section != section:
            problems.append(f"{phrase}: {term} is in {found_section}, not {section}")
    return problems


def test_every_avoided_phrase_is_on_its_terms_avoid_line():
    assert _check_avoided_agrees((REPO / "CONTEXT.md").read_text()) == []


def test_the_agreement_notices_a_removed_quote():
    context = (REPO / "CONTEXT.md").read_text().replace('"sandbox"', "sandbox", 1)
    assert _check_avoided_agrees(context) == ["sandbox: not quoted on cell's _Avoid_ line"]


def test_terms_reports_fail_and_still_exits_zero(tmp_path):
    from saffron.gates.contract import parse_gate_json

    _init(tmp_path, {"README.md": "The agent runs in a sandbox.\n"})
    done = _run_gate("terms", tmp_path)
    assert done.returncode == 0
    result = parse_gate_json(done.stdout, expected_gate="terms")
    assert result.status == "fail"
    assert [(f.code, f.line) for f in result.failures] == [("avoided-term", 1)]
    assert result.tool and result.tool.startswith("saffron-prose ")
```

Add `import re` to the file's imports. In `tests/test_saffron_gates.py`, add `"terms"` to the set in `test_the_policy_parses`.

- [ ] **Step 4: Run the tests to verify they fail**

Run: `uv run pytest tests/test_prose_gate.py tests/test_saffron_gates.py::test_the_policy_parses -v`
Expected: the new tests FAIL with `ValueError: unknown gate: terms` or `AttributeError: ... 'AVOIDED'`, and the policy test fails on `terms`.

- [ ] **Step 5: Add the rule to `prose.py`**

Change `GATES = ("prose",)` to `GATES = ("prose", "terms")`. Add after `WORD_RULES`:

```python
# Phrase -> (the Saffron term, its CONTEXT.md section). An entry is quoted on
# that term's _Avoid_ line, and every hit in scope was a misuse when it entered.
AVOIDED = {
    "sandbox": ("cell", "§1"),
    "ticket": ("spec", "§2"),
    "work item": ("task", "§2"),
    "the denylist": ("protected paths", "§3"),
    "soft fail": ("advisory", "§4"),
    "self-heal": ("repair", "§4"),
    "auto-fix": ("repair", "§4"),
}
```

Add before `check`:

```python
def _avoided(text: _Text) -> list[Finding]:
    unquoted = _QUOTED.sub(_blank, text.body)
    found = []
    for phrase, (term, section) in AVOIDED.items():
        spelled = re.escape(phrase).replace(r"\ ", r"\s+")
        message = f'{phrase}: say "{term}" (CONTEXT.md {section})'
        for match in re.finditer(rf"\b{spelled}\b", unquoted, re.I):
            found.append(Finding(text.line(match.start()), "avoided-term", message))
    return found
```

In `check`, replace `found = _style(prepared, path, root)` with:

```python
    found = _style(prepared, path, root) if gate == "prose" else _avoided(prepared)
```

Update the module docstring's first line to: `"""The `prose` and `terms` gates: Saffron's house style and vocabulary over its living Markdown.`

- [ ] **Step 6: Write the wrapper and declare the gate**

```sh
#!/bin/sh
exec python3 "$(dirname "$0")/prose.py" terms
```

Save it as `.saffron/gates/terms` and run `chmod +x .saffron/gates/terms`. In `.saffron/policy.yaml`, add under `prose:`:

```yaml
  # Curated avoided phrases from CONTEXT.md; reported, never blocking.
  terms: { blocking: false }
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prose_gate.py tests/test_saffron_gates.py -v`
Expected: all PASS.

- [ ] **Step 8: Run the gate on the repository**

Run: `.saffron/gates/terms | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['status'], r['summary'])"`
Expected: `pass` with `0 findings`, matching Step 2.

- [ ] **Step 9: Commit**

```bash
git add .saffron/gates/prose.py .saffron/gates/terms .saffron/policy.yaml tests/test_prose_gate.py tests/test_saffron_gates.py
git commit -m "feat(gates): an avoided word reached a cell and nothing named the term to use"
```

### Task 7: Verify and open PR 2

- [ ] **Step 1:** Run `make check && .saffron/gates/structure`. Expected: green, `pass`.
- [ ] **Step 2:** Following the `gh-stack` skill, push the layer and open its PR. The body lists the seven entries, the entry-bar measurement (zero hits), and the dropped "Docker" with `DESIGN.md:377` and `:1402` as the reason. Ask before any push that needs approval.

---

## PR 3 — branch `joel/prose-edit-hook`, stacked on PR 2

### Task 8: Name the gate in `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md:36`

- [ ] **Step 1: Create the branch** with the `gh-stack` skill, on top of `joel/prose-terms`.
- [ ] **Step 2: Edit line 36** (inside the Commands code fence) so the line count stays at 202:

```
.saffron/gates/structure  .saffron/gates/prose    # what those gates run; prose limits new findings
```

- [ ] **Step 3: Commit** (the `prose-limit` hook runs on it and must pass: the line is inside a code fence)

```bash
git add CLAUDE.md
git commit -m "docs(claude): the standing instructions did not name the prose gate"
```

### Task 9: The edit-time report

**Files:**
- Modify: `hooks/prose_limit.py` (add `edit_time`, extend `main`, extend the docstring)
- Modify: `.claude/settings.json`
- Test: `tests/test_prose_limit_hook.py`

**Interfaces:**
- Consumes: `load_prose`, `new_findings`, `_git` from Task 4.
- Produces: `edit_time(root: Path, event: dict[str, Any]) -> int`, and `main(["--edited"])` reading the event from stdin.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_prose_limit_hook.py`)

```python
import json


def _edited(repo: Path, file_path: Path) -> subprocess.CompletedProcess[str]:
    event = {"tool_input": {"file_path": str(file_path)}, "cwd": str(repo)}
    return subprocess.run(
        [sys.executable, str(HOOK), "--edited"],
        cwd=repo,
        input=json.dumps(event),
        capture_output=True,
        text=True,
    )


def test_an_edit_that_adds_a_finding_is_reported_to_the_model(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "README.md").write_text("Short.\n\n" + LONG_A + "\n")
    done = _edited(repo, repo / "README.md")
    assert done.returncode == 2
    assert "README.md:3: sentence-length" in done.stderr


def test_an_edit_that_adds_an_avoided_phrase_is_reported(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "README.md").write_text("The agent runs in a sandbox.\n")
    done = _edited(repo, repo / "README.md")
    assert done.returncode == 2
    assert 'sandbox: say "cell"' in done.stderr


def test_a_clean_edit_and_a_file_elsewhere_say_nothing(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "README.md").write_text("Short. Still short.\n")
    assert _edited(repo, repo / "README.md").returncode == 0
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text(LONG_A + "\n")
    assert _edited(repo, outside).returncode == 0


def test_claude_code_runs_the_hook_after_each_edit():
    settings = json.loads((REPO / ".claude" / "settings.json").read_text())
    (entry,) = settings["hooks"]["PostToolUse"]
    assert entry["matcher"] == "Write|Edit"
    (hook,) = entry["hooks"]
    assert hook["command"].endswith("python3 hooks/prose_limit.py --edited")
```

Move `import json` to the top of the file with the other imports.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_prose_limit_hook.py -v`
Expected: the four new tests FAIL (`unexpected arguments: ['--edited']` exits 2 with nothing matching, and `KeyError: 'hooks'`).

- [ ] **Step 3: Add `edit_time`**

Add `import json` to `hooks/prose_limit.py`. Add before `main`:

```python
def edit_time(root: Path, event: dict[str, Any]) -> int:
    """Print the edited file's new findings for the model. The edit already happened."""
    file_path = Path(event.get("tool_input", {}).get("file_path", ""))
    if not file_path.is_absolute():
        file_path = Path(event.get("cwd", root)) / file_path
    try:
        path = file_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return 0
    prose = load_prose()
    if not prose.in_scope(path) or not file_path.is_file():
        return 0
    head = _git(root, "show", f"HEAD:{path}")
    old_text = head.stdout if head.returncode == 0 else None
    new_text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = [
        f"{path}:{f.line}: {f.code}: {f.excerpt}"
        for gate in prose.GATES
        for f in new_findings(prose, root, gate, path, old_text, new_text)
    ]
    if not lines:
        return 0
    print("New house-style findings (.saffron/gates/prose.py):", *lines, sep="\n", file=sys.stderr)
    return 2
```

Replace `main` with:

```python
def main(argv: list[str]) -> int:
    if argv == ["--edited"]:
        return edit_time(Path.cwd(), json.loads(sys.stdin.read() or "{}"))
    if argv:
        print(f"unexpected arguments: {argv}", file=sys.stderr)
        return 2
    return commit_time(Path.cwd())
```

Append to the module docstring:

```
With `--edited`, a Claude Code PostToolUse hook: the edited file's new findings
for both gates go to stderr with exit 2, which Claude Code shows the model.
PostToolUse cannot block, because the edit already happened.
```

- [ ] **Step 4: Register it in `.claude/settings.json`**

```json
{
  "enabledPlugins": {
    "ast-grep@ast-grep-marketplace": true
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"$CLAUDE_PROJECT_DIR\" && python3 hooks/prose_limit.py --edited",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prose_limit_hook.py -v`
Expected: all PASS.

- [ ] **Step 6: Mutant check**

In `edit_time`, replace `for gate in prose.GATES` with `for gate in ("prose",)` → `test_an_edit_that_adds_an_avoided_phrase_is_reported` fails. Revert.

- [ ] **Step 7: Commit**

```bash
git add hooks/prose_limit.py .claude/settings.json tests/test_prose_limit_hook.py
git commit -m "feat(hooks): a model editing prose learned of a new finding only at commit time"
```

### Task 10: Verify and open PR 3

- [ ] **Step 1:** Run `make check && .saffron/gates/structure`. Expected: green.
- [ ] **Step 2: Try the hook live.** In a Claude Code session in this worktree, append a sentence of 30 words to `README.md` with the Edit tool. Expected: the tool result shows `README.md:<n>: sentence-length`. Revert the edit.
- [ ] **Step 3:** Following the `gh-stack` skill, push the layer and open its PR. The body says the hook is advisory and reports both gates' new findings. Ask before any push that needs approval.
