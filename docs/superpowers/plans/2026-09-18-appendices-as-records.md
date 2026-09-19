# The appendices as records — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `DESIGN.md`'s appendices A–T move verbatim into `docs/appendices/`, one record each, as `records/`' second kind. Their letters stay permanent ids, both indexes in `DESIGN.md` render from the records, and a new appendix, U, records the reversal and the intent to record decisions as their own records.

**Architecture:** PR 1 teaches `records/` a second kind: an `Appendix` model, section rules that belong to a `Kind` instead of running on every kind, a letter order, a contiguity check and CLI support, all tested on a fixture. PR 2 is the move, in commits ordered so the prose gate checks every new sentence: copy the appendices into records, switch every reader to the records, cut them from `DESIGN.md`, widen the prose gate's scope, then write the backlog item, U and the surfaces that say otherwise.

**Tech Stack:** Python 3.12, pydantic 2, PyYAML, rdflib, pyshacl, argparse, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-18-appendices-as-records-design.md`

## Global Constraints

- Appendix letters are permanent ids. After Z comes AA. The id pattern is `[A-Z]{1,2}`.
- The moved prose is byte-identical to what `DESIGN.md` held. Nothing in an appendix body is reworded.
- An appendix has no `status` and no `superseded_by`. Its frontmatter is exactly `id`, `title`, `revisions`, `question`. Unknown keys are refused.
- `question` is navigation. The appendix body is the record.
- `records/` imports nothing from `saffron/`. `ontology/design_record.py` may import `records/`. `ontology/spans.py` stays standard-library only.
- `DESIGN.md`, `CONTEXT.md`, `.saffron/**` are `protected`, so this is done by hand, never by a cell.
- No commit that removes prose hits from `DESIGN.md` carries a prose edit to it. The cut commit (Task 8) is a pure removal.
- The prose-scope commit (Task 9) stages no file under `docs/appendices/`. Appendix {U} (Task 11) is written after it.
- Comments: one or two lines, the non-obvious why only. Docstrings stay within ten lines (the `prose` gate counts them).
- Commit subjects: lowercase `type(scope): what changed`, a sentence about the defect, not the file. No co-author line.
- A new test is run against the unfixed code, or against a mutant, before it is trusted (`CLAUDE.md`). Every "run it to see it fail" step is mandatory.
- `make check` is green at the end of every task.
- **`Appendix {U}` in this plan means the citation of U, spelled without the braces in the files it is written to.** `tests/test_citations.py` scans `docs/`, so this plan cannot cite a letter that does not exist until Task 11. The same holds for any file committed before Task 11: it names U only in lowercase prose.
- Branching: PR 1 (Tasks 1–5) lands on `joel/appendices-as-records`, which already carries the design doc (#349). PR 2 (Tasks 6–13) is `joel/appendices-move`, stacked on it with `gh stack`. Never `git push --force`. `gh stack submit` needs the operator's approval in chat first.

---

## File structure

```
records/
  kinds.py             # + Appendix model, APPENDIX_ID, Kind.sections, KINDS["appendix"]; Identified loses status
  load.py              # section rules read Kind.sections; letter_order; _check_sections narrowed to BacklogItem
  check.py             # + appendix_letters, check_appendix_letters; status reads narrowed; PR 2 wires check_all
  __main__.py          # list and show learn the appendix kind
tests/records/
  fixtures/good/docs/appendices/A-what-changed-in-rev-2-and-why.md
  fixtures/good/docs/appendices/B-a-second-revision.md
  test_records_kinds.py, test_records_load.py, test_records_check.py, test_records_cli.py
ontology/
  design_record.py     # PR 2: parses appendix records; renders both indexes
  spans.py             # PR 2: + APPENDIX_ANCHOR, APPENDIX_HEADER, appendix_index
  render.py            # PR 2: renders both indexes from the records
  shapes/factory-shapes.ttl   # PR 2: appendixLetter pattern widens
tests/ontology/test_design_record.py, tests/ontology/test_spans.py, tests/test_citations.py
docs/appendices/       # PR 2: A–T moved, U written
docs/evidence/scripts/2026-09-18-split-appendices.py   # PR 2: split and cut
```

---

## PR 1 — `records/` learns a second kind

### Task 1: The `Appendix` model, and `status` onto `BacklogItem`

**Files:**
- Modify: `records/kinds.py` (docstring `:1-4`, `Identified` `:51-57`, `KINDS` `:137-145`)
- Modify: `records/load.py:126-131` (`_check_sections` signature)
- Modify: `records/check.py:49-55` (`_backlog` docstring), `:115`, `:248`, `:282`, `:311`, `:316`
- Test: `tests/records/test_records_kinds.py`, `tests/records/test_records_check.py:292`, `:299`

**Interfaces:**
- Produces: `records.kinds.APPENDIX_ID: str` (`r"[A-Z]{1,2}"`), `records.kinds.Appendix` (pydantic, fields `id: str`, `title: str`, `revisions: list[int]`, `question: str`), `KINDS["appendix"]`. `Identified` has only `id`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/records/test_records_kinds.py`:

```python
def test_an_appendix_is_an_id_a_title_revisions_and_a_question():
    a = Appendix(id="G", title="rev 8: the cell runtime", revisions=[8, 10], question="Which runtime?")
    assert (a.id, a.revisions) == ("G", [8, 10])


@pytest.mark.parametrize("bad", ["g", "ABC", "", "1"])
def test_an_appendix_id_is_one_or_two_capitals(bad: str):
    with pytest.raises(ValidationError):
        Appendix(id=bad, title="t", revisions=[1], question="q")


def test_an_appendix_names_at_least_one_revision():
    with pytest.raises(ValidationError):
        Appendix(id="A", title="t", revisions=[], question="q")


def test_an_appendix_has_no_status():
    """An appendix is never replaced, so a status field is refused, not ignored."""
    with pytest.raises(ValidationError):
        Appendix(id="A", title="t", revisions=[1], question="q", status="open")


def test_identified_carries_only_an_id():
    with pytest.raises(ValidationError):
        Identified(id=1, status="open")


def test_the_appendix_kind_is_registered():
    kind = KINDS["appendix"]
    assert kind.directory == "docs/appendices" and kind.model is Appendix
    assert re.match(kind.pattern, "AA-a-slug.md").group(1) == "AA"
    assert re.match(kind.pattern, "a-lower.md") is None
```

Imports go at the top of the file, never in the appended block: ruff selects `E` and `I`, and `--fix` does not move an E402 import. Add `import re`, and widen the existing `from records.kinds import …` to `KINDS, Appendix, BacklogItem, Identified, new_id`. `pytest` and `ValidationError` are already imported. The parametrized test is not a declared spec witness, so the no-parametrize rule for witnesses does not apply here.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/records/test_records_kinds.py -q`
Expected: FAIL, `ImportError: cannot import name 'Appendix'`.

- [ ] **Step 3: Implement**

In `records/kinds.py`, replace the module docstring's second paragraph:

```python
"""One pydantic model per record kind, and the registry that names them.

Every field is a scalar or a list of ids, so a later lift into the ontology
graph is mechanical. An appendix's `title` and `question` are the exception:
short prose the appendix index renders."""
```

Replace `Identified`:

```python
class Identified(BaseModel):
    """What every kind's model has: an id the filename repeats."""

    model_config = ConfigDict(extra="forbid")

    id: Annotated[int, Strict()] | str
```

`BacklogItem` already declares `status: Status`, so it needs no change. After `BacklogItem`, add:

```python
# A to Z, then AA: letters are permanent ids, and six remain after U.
APPENDIX_ID = r"[A-Z]{1,2}"


class Appendix(Identified):
    """What one revision found. Never replaced, so it has no status."""

    id: Annotated[str, Field(pattern=rf"^{APPENDIX_ID}$")]
    title: str = Field(min_length=1)
    revisions: list[Number] = Field(min_length=1)
    question: str = Field(min_length=1)
```

Add to `KINDS`:

```python
    "appendix": Kind(
        "appendix",
        "docs/appendices",
        rf"^({APPENDIX_ID})-[a-z0-9-]+\.md$",
        Appendix,
    ),
```

In `records/load.py`, change `_check_sections`'s first parameter to `model: BacklogItem` and import `BacklogItem` from `records.kinds`. Its call site in `parse` becomes:

```python
    if isinstance(model, BacklogItem):
        _check_sections(model, sections, path)
```

In `records/check.py`, every `.model.status` read goes through `_backlog`:

```python
# :115
            elif _backlog(by_id[target]).status == "superseded":
# :248
        if _backlog(r).status != "done":
# :282
        if path.parent.name == "done" and _backlog(item).status == "open":
# :311
            elif _backlog(by_id[n]).status not in ("done", "superseded"):
# :316
                        f"strikes item {n}, which is {_backlog(by_id[n]).status}",
```

Replace `_backlog`'s docstring:

```python
    """Narrow a record's model to `BacklogItem`. A field read via `getattr` on
    another kind's model would silently check nothing instead of refusing it."""
```

In `tests/records/test_records_check.py:292` and `:299`, drop `status="open"`: `Identified(id=records[0].model.id)`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/records -q && uv run ty check records`
Expected: PASS, and `ty` reports no errors. `ty` is what finds any `.status` read the list above missed.

- [ ] **Step 5: Commit**

```bash
git add records/ tests/records/
git commit -m "feat(records): an appendix is a record kind with no status, and status is a backlog field"
```

### Task 2: Section rules belong to a kind, and letters sort A to Z then AA

**Files:**
- Modify: `records/kinds.py` (`Kind`, `KINDS["backlog"]`)
- Modify: `records/load.py:23` (`REQUIRED_SECTIONS`), `:105-119` (the three body rules), `:158-175` (`load`, `order`)
- Create: `tests/records/fixtures/good/docs/appendices/A-what-changed-in-rev-2-and-why.md`, `B-a-second-revision.md`
- Test: `tests/records/test_records_load.py`

**Interfaces:**
- Consumes: `Appendix`, `APPENDIX_ID` (Task 1).
- Produces: `Kind.sections: tuple[str, ...]` (empty means free prose), `records.kinds.BACKLOG_SECTIONS`, `records.load.letter_order(record) -> tuple[int, str]`. `load(KINDS["appendix"], root)` returns records in A…Z, AA order.

- [ ] **Step 1: Write the fixture**

`tests/records/fixtures/good/docs/appendices/A-what-changed-in-rev-2-and-why.md`:

```markdown
---
id: A
title: "What changed in rev 2, and why"
revisions: [2]
question: "Why the fixture has an appendix at all"
---

### A finding

1. **A fixture principle.** Numbered the way the real ones are.

---

```

`tests/records/fixtures/good/docs/appendices/B-a-second-revision.md`:

```markdown
---
id: B
title: "rev 3: a second revision"
revisions: [3]
question: "Whether a body with no h2 heading loads"
---

The whole body is prose before any `## ` heading, which the backlog refuses.
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/records/test_records_load.py`:

```python
APPENDIX = KINDS["appendix"]


def test_an_appendix_body_with_no_h2_heading_loads():
    """The backlog refuses prose before the first `## `; an appendix is all such prose."""
    records = load(APPENDIX, FIXTURE)
    assert [r.model.id for r in records] == ["A", "B"]
    assert records[1].body.startswith("\nThe whole body is prose")
    assert records[0].sections == {}


def test_letters_sort_a_to_z_then_aa(tmp_path: Path):
    directory = tmp_path / APPENDIX.directory
    directory.mkdir(parents=True)
    for letter in ("AA", "B", "A"):
        (directory / f"{letter}-x.md").write_text(
            f'---\nid: {letter}\ntitle: "t"\nrevisions: [1]\nquestion: "q"\n---\n\nx\n'
        )
    assert [r.model.id for r in load(APPENDIX, tmp_path)] == ["A", "B", "AA"]


def test_the_backlog_still_refuses_prose_before_its_first_heading(tmp_path: Path):
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    item = next((tmp_path / "docs" / "backlog").glob("001-*.md"))
    text = item.read_text()
    item.write_text(text.replace("## Problem", "stray prose\n\n## Problem", 1))
    with pytest.raises(RecordError, match="prose before the first"):
        load(BACKLOG, tmp_path)
```

- [ ] **Step 3: Run them to see them fail**

Run: `uv run pytest tests/records/test_records_load.py -q`
Expected: `test_an_appendix_body_with_no_h2_heading_loads` FAILS with `prose before the first`, and `test_letters_sort_a_to_z_then_aa` FAILS with `['A', 'AA', 'B']`. The third passes: it guards the backlog rule this task must keep.

- [ ] **Step 4: Implement**

In `records/kinds.py`, add before `Kind`:

```python
BACKLOG_SECTIONS = ("Problem", "Done looks like", "Record")
```

Add a field to `Kind`, last:

```python
    # Required `## ` headings, in order. Empty means the body is free prose.
    sections: tuple[str, ...] = ()
```

and pass `sections=BACKLOG_SECTIONS` in `KINDS["backlog"]`.

In `records/load.py`, delete `REQUIRED_SECTIONS` and first run `grep -rn REQUIRED_SECTIONS records tests` to move any other reader onto `BACKLOG_SECTIONS`. Replace the block from `preamble = _preamble(body)` through the order check with:

```python
    if kind.sections:
        sections = _sectioned(body, kind.sections, path)
    else:
        sections = split_sections(body)
    if isinstance(model, BacklogItem):
        _check_sections(model, sections, path)
```

and add:

```python
def _sectioned(body: str, required: tuple[str, ...], path: Path | None) -> dict[str, str]:
    """A body that is `## ` sections only, drawn from `required`, in its order."""
    preamble = _preamble(body)
    if preamble:
        raise RecordError(f"prose before the first `## ` heading: {preamble!r}", path)
    sections = split_sections(body)
    unknown = [s for s in sections if s not in required]
    if unknown:
        raise RecordError(f"unknown section(s) {unknown}; the body is {required}", path)
    order = [s for s in required if s in sections]
    if list(sections) != order:
        raise RecordError(
            f"sections out of order: {list(sections)}; the order is {required}", path
        )
    return sections
```

In `load`, replace the final `return`:

```python
    return sorted(records, key=letter_order if kind.model is Appendix else order)
```

and add after `order`:

```python
def letter_order(record: Record) -> tuple[int, str]:
    """By length first, so AA sorts after Z rather than before B."""
    return len(str(record.model.id)), str(record.model.id)
```

Import `Appendix` from `records.kinds`.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/records -q && uv run ty check records`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add records/ tests/records/
git commit -m "fix(records): the backlog's section rules ran on every kind and would refuse every appendix body"
```

### Task 3: Appendix letters run contiguously from A

**Files:**
- Modify: `records/check.py` (new functions after `check_ids`)
- Test: `tests/records/test_records_check.py`

**Interfaces:**
- Consumes: `load(KINDS["appendix"], root)` in letter order (Task 2).
- Produces: `records.check.appendix_letters(n: int) -> list[str]`, `records.check.check_appendix_letters(records: list[Record]) -> list[Violation]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/records/test_records_check.py`:

```python
APPENDIX = KINDS["appendix"]


def test_appendix_letters_run_a_to_z_then_aa():
    letters = appendix_letters(28)
    assert letters[:2] == ["A", "B"] and letters[25:] == ["Z", "AA", "AB"]


def test_the_fixture_appendices_are_contiguous():
    assert check_appendix_letters(load(APPENDIX, FIXTURE)) == []


def test_a_skipped_letter_is_a_violation(tmp_path: Path):
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    directory = tmp_path / APPENDIX.directory
    (directory / "B-a-second-revision.md").rename(directory / "C-a-second-revision.md")
    text = (directory / "C-a-second-revision.md").read_text()
    (directory / "C-a-second-revision.md").write_text(text.replace("id: B", "id: C"))
    [v] = check_appendix_letters(load(APPENDIX, tmp_path))
    assert v.field == "id" and "['A', 'C']" in v.message


def test_a_letter_used_twice_is_a_violation(tmp_path: Path):
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    directory = tmp_path / APPENDIX.directory
    shutil.copy(directory / "B-a-second-revision.md", directory / "B-again.md")
    [v] = check_appendix_letters(load(APPENDIX, tmp_path))
    assert "['A', 'B', 'B']" in v.message
```

Put `APPENDIX` beside `BACKLOG` at the top, and add `appendix_letters` and `check_appendix_letters` to the existing `from records.check import (…)` list, never an import in the appended block (E402). The file already has `Path`, `KINDS`, `load` and `FIXTURE`, and adds `shutil` if it lacks it.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/records/test_records_check.py -q -k appendix`
Expected: FAIL, `ImportError: cannot import name 'appendix_letters'`.

- [ ] **Step 3: Implement**

In `records/check.py`, after `check_ids`:

```python
def appendix_letters(n: int) -> list[str]:
    """The first `n` appendix ids: A to Z, then AA, AB, and on."""
    singles = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    return (singles + [a + b for a in singles for b in singles])[:n]


def check_appendix_letters(records: list[Record]) -> list[Violation]:
    ids = [str(r.model.id) for r in records]
    expected = appendix_letters(len(ids))
    if ids == expected:
        return []
    return [
        Violation(
            records[-1].path,
            "id",
            f"appendix letters are {ids}; they run from A with no gap or repeat: {expected}",
        )
    ]
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/records -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add records/check.py tests/records/test_records_check.py
git commit -m "feat(records): appendix letters are checked to run from A with no gap or repeat"
```

### Task 4: `records list appendix` and `records show P`

**Files:**
- Modify: `records/__main__.py` (`cmd_list` `:53-61`, `cmd_show` `:64-90`)
- Test: `tests/records/test_records_cli.py`

**Interfaces:**
- Consumes: `Appendix`, `APPENDIX_ID`, `KINDS["appendix"]`.
- Produces: `records list appendix` prints `id  revisions  title` per line. `records show <letter>` prints the record file. `--status`/`--tier` with `appendix` exits 2.

- [ ] **Step 1: Write the failing tests**

Append to `tests/records/test_records_cli.py`:

```python
def test_list_appendix_prints_one_line_per_appendix_in_letter_order():
    result = run("list", "appendix")
    assert result.returncode == 0, result.stderr
    out = result.stdout.splitlines()
    assert [line.split()[0] for line in out] == ["A", "B"]
    assert out[1].split(maxsplit=2) == ["B", "3", "rev 3: a second revision"]


def test_list_appendix_refuses_backlog_filters():
    result = run("list", "appendix", "--tier", "1")
    assert result.returncode == 2 and "appendices have neither" in result.stderr


def test_show_a_letter_prints_the_appendix():
    result = run("show", "B")
    assert result.returncode == 0, result.stderr
    assert "The whole body is prose" in result.stdout


def test_show_an_unknown_letter_says_so():
    result = run("show", "Z")
    assert result.returncode == 1 and "no appendix Z" in result.stderr
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/records/test_records_cli.py -q -k appendix`
Expected: `list appendix` exits 2 with `not a backlog item`, and `show B` exits 1 with `no backlog item names B`.

- [ ] **Step 3: Implement**

In `records/__main__.py`, import `APPENDIX_ID` and `Appendix` from `records.kinds`, and add:

```python
def _appendix(record: Record) -> Appendix:
    if not isinstance(record.model, Appendix):
        raise RecordError("not an appendix", record.path)
    return record.model


def _appendix_line(record: Record) -> str:
    m = _appendix(record)
    revisions = ",".join(str(n) for n in m.revisions)
    return f"{m.id:>8}  {revisions:<10}  {m.title}"
```

At the top of `cmd_list`:

```python
    if KINDS[args.kind].model is Appendix:
        if args.status or args.tier is not None:
            print("--status and --tier filter backlog items; appendices have neither", file=sys.stderr)
            return 2
        for record in load(KINDS[args.kind], args.root):
            print(_appendix_line(record))
        return 0
```

At the top of `cmd_show`, before the backlog load:

```python
    if re.fullmatch(APPENDIX_ID, args.id):
        found = [r for r in load(KINDS["appendix"], args.root) if r.model.id == args.id]
        if not found:
            print(f"no appendix {args.id}", file=sys.stderr)
            return 1
        text = _render(found[0], args.section)
        if text is None:
            return 1
        print(text, end="")
        return 0
```

Update the `show` parser's help to `"one record by id or letter, or the records naming a spec id"`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/records -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add records/__main__.py tests/records/test_records_cli.py
git commit -m "feat(records): list and show read the appendix kind instead of refusing it as a backlog item"
```

### Task 5: Open PR 1

- [ ] **Step 1:** Run `make check`. Expected: green, with the test count up by the tests Tasks 1–4 added.
- [ ] **Step 2:** `git push`. #349 now carries the design doc and PR 1's four commits.
- [ ] **Step 3:** Edit #349's title and body to cover the records change, following `.github/pull_request_template.md`. Write the body to a scratch file and run `gh pr edit 349 --title "…" --body-file <file>`. Under Verification, name each test watched failing in Tasks 1–4. Under What, say the stack's second layer is the move.

---

## PR 2 — the move

Create the branch and stack it: `gh stack` per the `gh-stack` skill, with the branch name `joel/appendices-move`.

### Task 6: Copy the appendices into records

**Files:**
- Create: `docs/evidence/scripts/2026-09-18-split-appendices.py`
- Create: `docs/appendices/A-…md` … `T-…md` (generated)

**Interfaces:**
- Produces: twenty records that `load(KINDS["appendix"], ROOT)` reads. `DESIGN.md` is unchanged in this task.

- [ ] **Step 1: Write the script**

```python
"""Split `DESIGN.md`'s appendices into `docs/appendices/`, and later cut them.

`split` writes one record per appendix and leaves `DESIGN.md` alone. `cut`
proves the records rebuild the appendix range byte for byte, then removes it.
Design: docs/superpowers/specs/2026-09-18-appendices-as-records-design.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from records.kinds import KINDS, Appendix
from records.load import load

ROOT = Path(__file__).resolve().parents[3]
DESIGN = ROOT / "DESIGN.md"
OUT = ROOT / KINDS["appendix"].directory
HEADING = re.compile(r"^## Appendix ([A-Z]) — (.*)$", re.MULTILINE)
ROW = re.compile(r"^\| \*\*([A-Z])\*\* \| ([0-9, ]+) \| (.*) \| [0-9–]* \|$", re.MULTILINE)
FIRST = "\n## Appendix A — "


def slug(title: str) -> str:
    bare = re.sub(r"^rev \d+: ", "", title)
    return re.sub(r"[^a-z0-9]+", "-", bare.lower()).strip("-")[:60].rstrip("-")


def split() -> None:
    text = DESIGN.read_text()
    rows = {m.group(1): (m.group(2), m.group(3)) for m in ROW.finditer(text)}
    headings = list(HEADING.finditer(text))
    OUT.mkdir(exist_ok=True)
    for i, m in enumerate(headings):
        letter, title = m.group(1), m.group(2)
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[m.end() + 1 : end]
        revisions, question = rows[letter]
        (OUT / f"{letter}-{slug(title)}.md").write_text(
            "---\n"
            f"id: {letter}\n"
            f"title: {json.dumps(title, ensure_ascii=False)}\n"
            f"revisions: [{revisions}]\n"
            f"question: {json.dumps(question, ensure_ascii=False)}\n"
            "---\n"
            f"{body}"
        )
    print(f"wrote {len(headings)} records to {OUT.relative_to(ROOT)}")


def cut() -> None:
    text = DESIGN.read_text()
    kept = text[: text.index(FIRST) + 1]
    rebuilt = ""
    for r in load(KINDS["appendix"], ROOT):
        assert isinstance(r.model, Appendix)
        rebuilt += f"## Appendix {r.model.id} — {r.model.title}\n{r.body}"
    # `kept` already ends with the newline before `## Appendix A`.
    if kept + rebuilt != text:
        sys.exit("the records do not rebuild DESIGN.md's appendix range; nothing cut")
    # The `---` that closed the principle index before Appendix A closes nothing now.
    kept = kept.rstrip().removesuffix("---").rstrip() + "\n"
    DESIGN.write_text(kept)
    print(f"cut {len(text) - len(kept)} bytes from DESIGN.md")


if __name__ == "__main__":
    {"split": split, "cut": cut}[sys.argv[1]]()
```

- [ ] **Step 2: Run the split**

Run: `uv run python docs/evidence/scripts/2026-09-18-split-appendices.py split`
Expected: `wrote 20 records to docs/appendices`.

- [ ] **Step 3: Prove the round trip before committing**

Run: `uv run python docs/evidence/scripts/2026-09-18-split-appendices.py cut && git diff --stat DESIGN.md && git checkout DESIGN.md`
Expected: `cut … bytes`, a diff of about 1,400 removed lines, then `DESIGN.md` restored from the index. If `cut` exits with "do not rebuild", fix the script, never the records by hand.

- [ ] **Step 4: Check every record loads and the letters are contiguous**

Run: `uv run python -c "from pathlib import Path; from records.kinds import KINDS; from records.load import load; from records.check import check_appendix_letters as c; r = load(KINDS['appendix'], Path('.')); print(len(r), c(r))"`
Expected: `20 []`.

- [ ] **Step 5: Commit**

`docs/appendices/` is outside the prose gate's scope in this commit, so the hook passes.

```bash
git add docs/evidence/scripts/2026-09-18-split-appendices.py docs/appendices/
git commit -m "docs(appendices): the appendices are copied into one record each, DESIGN.md unchanged"
```

### Task 7: Every reader of the appendices reads the records

`DESIGN.md` still holds the appendices during this task, so the two copies agree and every test can compare against the committed indexes.

**Files:**
- Modify: `ontology/design_record.py` (whole module below its imports), `ontology/spans.py`, `ontology/render.py:200-205`
- Modify: `ontology/shapes/factory-shapes.ttl:282`
- Modify: `tests/ontology/test_design_record.py`, `tests/ontology/test_spans.py`
- Modify: `tests/test_citations.py` (`:36`, `:95-97`, `:100-137`, `:174`, `:179`, `:231-240`, `:341-354`, `:372`), `tests/records/test_records_integrity.py:14`
- Modify: `records/check.py` (`CITING` `:18`, `LIVE_SURFACES` `:228`, `check_all` `:421`)

**Interfaces:**
- Consumes: `load(KINDS["appendix"], root)`, `Appendix`.
- Produces: `design_record.appendices(root: Path) -> list[Record]`, `design_record.parse(records: list[Record]) -> rdflib.Graph`, `design_record.render_principles(text: str, graph: rdflib.Graph) -> str`, `design_record.render_appendix_index(text: str, records: list[Record], graph: rdflib.Graph) -> str`, `spans.APPENDIX_ANCHOR`, `spans.APPENDIX_HEADER`, `spans.appendix_index(text) -> tuple[int, int]`, `tests.test_citations.cited_letters(line: str) -> list[str]`, `addresses(document) -> set[str]`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_citations.py`, add:

```python
def test_a_two_letter_appendix_citation_is_read_whole():
    """Split into single capitals, AA read as two citations of A and passed."""
    # Joined so this file does not itself cite the two-letter id it tests.
    line = " ".join(["Appendix", "AA", "and", "Appendices", "I–L"])
    assert cited_letters(line) == ["AA", "I", "L"]
```

In `tests/ontology/test_spans.py`, add:

```python
def test_the_appendix_index_span_is_the_whole_table():
    from ontology import spans

    text = (REPO / "DESIGN.md").read_text()
    start, end = spans.appendix_index(text)
    table = text[start:end]
    assert table.startswith(spans.APPENDIX_HEADER)
    rows = table.removeprefix(spans.APPENDIX_HEADER).splitlines()
    assert rows and all(row.startswith("| **") for row in rows)
    assert not text[end:].startswith("|"), "the span stopped inside the table"
```

Rewrite `tests/ontology/test_design_record.py` against the records. The module docstring stays. Replace from `DESIGN = …` through `_graph`:

```python
from dataclasses import replace
from typing import Callable

from records.load import Record

REPO = ONTOLOGY.parent
DESIGN = REPO / "DESIGN.md"


def _records() -> list[Record]:
    return design_record.appendices(REPO)


def _graph() -> rdflib.Graph:
    return design_record.parse(_records())


def _edited(letter: str, edit: Callable[[str], str]) -> list[Record]:
    """The records with one appendix's body edited, for a mutant."""
    out = []
    for r in _records():
        if r.model.id == letter:
            body = edit(r.body)
            assert body != r.body, f"the fixture text was not found in appendix {letter}"
            r = replace(r, body=body)
        out.append(r)
    return out
```

Then change each test as follows, keeping its docstring:

- `test_the_committed_index_is_current_with_the_appendices`: `design_record.render_principles(committed, _graph())`.
- `test_the_currency_check_would_catch_a_dropped_row`: `design_record.render_principles(without, _graph())`.
- Add after it:

```python
def test_the_committed_appendix_index_is_current_with_the_records():
    committed = DESIGN.read_text()
    rendered = design_record.render_appendix_index(committed, _records(), _graph())
    assert rendered == committed, (
        "DESIGN.md's appendix index and the appendix records disagree: run "
        "`uv run python -m ontology.render`. Fix a question in its record's frontmatter."
    )


def test_the_appendix_currency_check_would_catch_a_dropped_row():
    committed = DESIGN.read_text()
    without = "".join(
        ln for ln in committed.splitlines(keepends=True) if not ln.startswith("| **M** | ")
    )
    assert without != committed, "the fixture row was not found — has the index moved?"
    assert design_record.render_appendix_index(without, _records(), _graph()) != without
```

- `test_the_index_reaches_every_appendix`: replace the `source`/`headings` lines with `headings = {str(r.model.id) for r in _records()}`, and its docstring's "Against the headings" with "Against the record ids".
- Delete `test_a_heading_it_cannot_read_is_refused` and its `parametrize`. The parser no longer reads headings. Task 8 adds the guard that replaces it.
- `test_a_principle_number_claimed_twice_is_refused`:

```python
    mutant = _edited("G", lambda b: "\n1. **A numbered list that opens bold**, not a principle.\n" + b)
    with pytest.raises(ValueError, match="2 values for"):
        design_record.principles(design_record.parse(mutant))
```

- Replace `test_a_rev_cell_that_contradicts_its_heading_is_refused` with:

```python
def test_revisions_that_contradict_the_title_are_refused():
    """`revisions` is hand-written and the title states a rev, so a typo has a
    second reading. Without this the shapes accept a well-formed wrong triple."""
    records = [
        replace(r, model=r.model.model_copy(update={"revisions": [9, 10]}))
        if r.model.id == "G" else r
        for r in _records()
    ]
    with pytest.raises(ValueError, match="the title says rev 8"):
        design_record.parse(records)
```

- `test_a_pipe_in_a_claim_keeps_the_row_three_cells_wide`:

```python
    mutant = _edited(
        "P",
        lambda b: b.replace("a third decision, and nobody made it.**", "a third decision | nobody made it.**"),
    )
    rendered = design_record.render_principles(DESIGN.read_text(), design_record.parse(mutant))
    row = next(line for line in rendered.splitlines() if line.startswith("| 57 | "))
```

  and keep its two row assertions.
- `test_a_drifted_table_header_is_refused`: `design_record.render_principles(mutant, _graph())`.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/ontology tests/test_citations.py -q`
Expected: FAIL. `cited_letters` and `appendix_index` do not exist, and `design_record.appendices` does not exist.

- [ ] **Step 3: Implement `ontology/spans.py`**

Replace `principle_index` with a shared locator and two callers:

```python
APPENDIX_ANCHOR = "## Appendices — an index"
APPENDIX_HEADER = "| App. | Rev | The question it settles | Principles |\n|---|---|---|---|\n"


def _table(text: str, anchor: str, header: str) -> tuple[int, int]:
    """`(start, end)` of the table under `anchor`, its header included."""
    if text.count(anchor) != 1:
        raise ValueError(f"{anchor}: expected exactly one occurrence")
    start = text.find(header, text.index(anchor))
    if start == -1:
        raise ValueError(f"{anchor}: no `{header.splitlines()[0]}` header under it")
    end = start + len(header)
    while end < len(text) and text[end] == "|":
        end = text.index("\n", end) + 1
    return start, end


def principle_index(text: str) -> tuple[int, int]:
    """`(start, end)` of the principle index table, its header included."""
    return _table(text, PRINCIPLE_ANCHOR, PRINCIPLE_HEADER)


def appendix_index(text: str) -> tuple[int, int]:
    """`(start, end)` of the appendix index table, its header included."""
    return _table(text, APPENDIX_ANCHOR, APPENDIX_HEADER)
```

- [ ] **Step 4: Implement `ontology/design_record.py`**

Module docstring, first paragraph and the "stays authoritative" paragraph become:

```python
"""The design record as a graph, parsed from the appendix records.

`CONTEXT.md` §11 names the genres the factory records a decision in. Two are
modelled here: a **principle**, and the **revision appendix** that contributed
it, read from `docs/appendices/`. `EvidenceRecord` and `SpikeVerdict` are
deliberately absent: they have no reader yet.

**The appendix records are authoritative.** This module reads them and renders
two indexes into `DESIGN.md` from them, the opposite direction from `render.py`'s
vocabulary renders. Dev-only and outside `saffron/`: nothing there imports a
graph library.
"""
```

Replace the imports and everything from `APPENDIX = …` through `parse` with:

```python
import re
from pathlib import Path

import rdflib

from ontology.spans import (
    APPENDIX_HEADER,
    PRINCIPLE_ANCHOR,
    PRINCIPLE_HEADER,
    appendix_index,
    principle_index,
)
from records.kinds import KINDS, Appendix
from records.load import Record, load

NS = "urn:software-factory:ns#"
FACTORY = rdflib.Namespace(NS)

# An appendix heading at any level or spacing. Nothing reads one in `DESIGN.md`
# any more, so the guard test uses this to refuse one written there.
APPENDIX_OPENS = re.compile(r"^#{2,}\s*Appendix\b")
# A principle opens a line and its claim is the bolded lead. Three wrap before
# the closing `**`, so the claim is read to that marker rather than to the end.
_PRINCIPLE = re.compile(r"^(\d+)\. \*\*")
# Most titles state a rev, so the hand-written `revisions` has a second reading.
_TITLE_REVISION = re.compile(r"\brev (\d+)\b")


def appendices(root: Path) -> list[Record]:
    return load(KINDS["appendix"], root)


def _appendix(record: Record) -> Appendix:
    if not isinstance(record.model, Appendix):
        raise TypeError(f"{record.path}: not an appendix record")
    return record.model
```

Keep `_claim` unchanged, then:

```python
def parse(records: list[Record]) -> rdflib.Graph:
    """Every principle and revision appendix the appendix records declare."""
    graph = rdflib.Graph()
    graph.bind("factory", FACTORY)
    for record in records:
        m = _appendix(record)
        stated = _TITLE_REVISION.search(m.title)
        if stated and int(stated.group(1)) not in m.revisions:
            raise ValueError(
                f"Appendix {m.id}: the title says rev {stated.group(1)}, "
                f"revisions says {m.revisions}"
            )
        appendix = FACTORY[f"Appendix{m.id}"]
        graph.add((appendix, rdflib.RDF.type, FACTORY.RevisionAppendix))
        graph.add((appendix, FACTORY.appendixLetter, rdflib.Literal(m.id)))
        for revision in m.revisions:
            graph.add((appendix, FACTORY.coversRevision, rdflib.Literal(revision)))
        lines = record.body.splitlines()
        for number, line in enumerate(lines):
            if found := _PRINCIPLE.match(line):
                node = FACTORY[f"principle-{found.group(1)}"]
                graph.add((node, rdflib.RDF.type, FACTORY.Principle))
                graph.add((node, FACTORY.principleNumber, rdflib.Literal(int(found.group(1)))))
                graph.add((node, FACTORY.claim, rdflib.Literal(_claim(lines, number))))
                graph.add((node, FACTORY.contributedBy, appendix))
    return graph
```

`_one`, `principles` and `_escaped` stay. `render_principles` takes the graph:

```python
def render_principles(text: str, graph: rdflib.Graph) -> str:
    """Rewrite the principle index's table body from the appendix records."""
    rows = principles(graph)
```

and the rest of its body is unchanged. Add:

```python
def _principle_cell(numbers: list[int]) -> str:
    if not numbers:
        return ""
    lo, hi = min(numbers), max(numbers)
    return str(lo) if lo == hi else f"{lo}–{hi}"


def render_appendix_index(text: str, records: list[Record], graph: rdflib.Graph) -> str:
    """Rewrite the appendix index's table body from the appendix records."""
    blocks: dict[str, list[int]] = {}
    for number, _, letter in principles(graph):
        blocks.setdefault(letter, []).append(number)
    body = ""
    for record in records:
        m = _appendix(record)
        revisions = ", ".join(str(n) for n in m.revisions)
        cell = _principle_cell(blocks.get(m.id, []))
        body += f"| **{m.id}** | {revisions} | {_escaped(m.question)} | {cell} |\n"
    start, end = appendix_index(text)
    replaced = text[start + len(APPENDIX_HEADER) : end]
    if replaced and not all(ln.startswith("| ") for ln in replaced.splitlines()):
        raise ValueError("the span after the appendix header is not a table body")
    return text[:start] + APPENDIX_HEADER + body + text[end:]
```

- [ ] **Step 5: Implement `ontology/render.py`**

Replace the `DESIGN.md` block in `main` (its comment and two lines at `:200-204`):

```python
    # `DESIGN.md`'s two indexes render from the appendix records, not from the
    # vocabulary: an appendix owns its prose, and the indexes are downstream of it.
    design = root / "DESIGN.md"
    records = design_record.appendices(root)
    graph = design_record.parse(records)
    text = design_record.render_principles(design.read_text(), graph)
    rendered[design] = design_record.render_appendix_index(text, records, graph)
```

- [ ] **Step 6: Widen the shape**

`ontology/shapes/factory-shapes.ttl:282`: `sh:pattern "^[A-Z]$"` becomes `sh:pattern "^[A-Z]{1,2}$"`.

- [ ] **Step 7: Implement `tests/test_citations.py`**

- Replace `from ontology.design_record import APPENDIX` with `from records.kinds import KINDS` and `from records.load import load`.
- `_APPENDIX_CITATION`: `[A-Z]\b` becomes `[A-Z]{1,2}\b`.
- Add after it:

```python
def cited_letters(line: str) -> list[str]:
    """Every appendix letter a line cites, a range read at its endpoints."""
    return [
        letter
        for match in _APPENDIX_CITATION.finditer(line)
        for letter in re.findall(r"\b[A-Z]{1,2}\b", match.group(1))
    ]
```

- `_cited`: replace the inner `for match in _APPENDIX_CITATION…` loop with `appendices.extend((path, number, letter) for letter in cited_letters(line))`.
- `addresses` returns `set[str]`: delete the `appendices` set and the `elif appendix := APPENDIX.match(line)` branch (an appendix heading is an unnumbered `##`, which `_ANY_H2` already closes), and return `sections`.
- `_by_document` returns `dict[str, set[str]]` only: `per_document[Path(name).name] = addresses(ROOT / name)`.
- Module globals become:

```python
PER_DOCUMENT = _by_document()
APPENDICES = {str(r.model.id) for r in load(KINDS["appendix"], ROOT)}
SECTION_CITATIONS, APPENDIX_CITATIONS = _cited()
```

- `test_every_appendix_citation_resolves`'s docstring: `"""An appendix letter is unambiguous: every appendix is a record in `docs/appendices/`."""`
- Delete `test_the_appendix_index_lists_every_appendix`. The appendix index currency test replaces it.
- `:372`: `addresses(ROOT / "CONTEXT.md")[0]` becomes `addresses(ROOT / "CONTEXT.md")`.

`tests/records/test_records_integrity.py:14`: `sections, _ = addresses(…)` becomes `sections = addresses(…)`.

- [ ] **Step 8: Wire the records check**

In `records/check.py`, `CITING` and `LIVE_SURFACES` each gain `"docs/appendices"`, and `check_all` gains `+ check_appendix_letters(load(KINDS["appendix"], root))`.

- [ ] **Step 9: Run everything**

Run: `git add ontology/ tests/ records/check.py && uv run python -m ontology.render && git diff --exit-code DESIGN.md CONTEXT.md ontology/ && make check`
Staging first matters: this task's own `ontology/` edits are uncommitted, and an unstaged diff of them would exit 1 before `make check` runs. Expected: the render changes nothing (both indexes reproduce the committed rows byte for byte), and `make check` is green. A diff here means a record's `question` or `revisions` differs from its row: fix the split script and rerun Task 6, never the row.

- [ ] **Step 10: Mutant for the two-letter reader**

Revert only `cited_letters`' `{1,2}` to single-letter (`[A-Z]\b` in `_APPENDIX_CITATION`, `\b[A-Z]\b` in the `findall`), run `uv run pytest tests/test_citations.py -q -k two_letter`, see it FAIL, restore.

- [ ] **Step 11: Commit**

```bash
git add ontology/ tests/ records/check.py
git commit -m "refactor(ontology): the design record is parsed from the appendix records, and both indexes render from them"
```

### Task 8: Cut the appendices from `DESIGN.md`

A pure removal. No other `DESIGN.md` edit goes in this commit.

**Files:**
- Modify: `DESIGN.md` (lines 1,657 to the end removed)
- Test: `tests/ontology/test_design_record.py`

**Interfaces:**
- Consumes: `design_record.APPENDIX_OPENS` (Task 7).

- [ ] **Step 1: Write the guard**

Append to `tests/ontology/test_design_record.py`:

```python
def _appendix_headings(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if design_record.APPENDIX_OPENS.match(ln)]


def test_design_md_holds_no_appendix():
    """An appendix written into `DESIGN.md` the old way is read by nothing: its
    principles never reach the index, and every other test stays green."""
    assert _appendix_headings(DESIGN.read_text()) == [], (
        "DESIGN.md has an appendix heading. Appendices are records: "
        "write it under docs/appendices/."
    )


def test_the_guard_would_catch_an_appendix_written_the_old_way():
    mutant = DESIGN.read_text() + "\n## Appendix Q — rev 21: written the old way\n"
    assert _appendix_headings(mutant)
```

- [ ] **Step 2: Run the guard to see it fail**

Run: `uv run pytest tests/ontology/test_design_record.py -q -k "old_way or holds_no_appendix"`
Expected: `test_design_md_holds_no_appendix` FAILS, listing the twenty headings still in `DESIGN.md`.

- [ ] **Step 3: Cut**

Run: `uv run python docs/evidence/scripts/2026-09-18-split-appendices.py cut`
Expected: `cut … bytes from DESIGN.md`. `DESIGN.md` now ends at the principle index's last row, with one trailing newline and no dangling `---`.

- [ ] **Step 4: Run everything**

Run: `uv run python -m ontology.render && git diff --exit-code -- ontology/ CONTEXT.md && make check`
Expected: green. The prose hook sees `DESIGN.md` lose hits and gain none.

- [ ] **Step 5: Commit**

```bash
git add DESIGN.md tests/ontology/test_design_record.py
git commit -m "docs(design): the appendices leave DESIGN.md, which keeps its sections and two rendered indexes"
```

### Task 9: The prose gate reads the appendices, and they are protected

This commit stages no file under `docs/appendices/`, so the moved prose becomes the baseline.

**Files:**
- Modify: `.saffron/gates/prose.py:36` (`INCLUDED_DIRS`)
- Modify: `.saffron/policy.yaml:57` (`protected`)

- [ ] **Step 1: Edit**

In `INCLUDED_DIRS`, add after `"docs/backlog/",`:

```python
    "docs/appendices/",
```

In `.saffron/policy.yaml`'s `protected` list, add after `- CONTEXT.md`:

```yaml
  # The design record left DESIGN.md as records, and stays as protected (Appendix {U}).
  - docs/appendices/**
```

Appendix {U} does not exist yet, and `test_every_appendix_citation_resolves` scans `.saffron/`. Write the comment as `# The design record left DESIGN.md as records, and stays as protected.` instead, and add `(Appendix {U})` in Task 11.

- [ ] **Step 2: Confirm nothing under `docs/appendices/` is staged, then run**

Run: `git add .saffron/gates/prose.py .saffron/policy.yaml && git diff --cached --name-only && make check`
Expected: exactly those two paths, and green. `test_scope_reaches_every_place_it_names` now requires a tracked file under `docs/appendices/`, which Task 6 committed.

- [ ] **Step 3: Commit**

```bash
git commit -m "fix(prose): the appendices left DESIGN.md and with it the prose gate's scope and protected"
```

### Task 10: File the backlog item for the decision kind

**Files:**
- Create: `docs/backlog/<new id>-decisions-have-no-record-of-their-own.md`

- [ ] **Step 1: Write the item**

```bash
ID=$(uv run python -m records new-id)
cat > "docs/backlog/$ID-decisions-have-no-record-of-their-own.md" <<EOF
---
id: $ID
title: Decisions have no record of their own, so where one stands today is spread across appendices
status: open
tier: null
filed: 2026-09-18
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

The appendices are records now, one per revision, and a revision records
several decisions. Where one decision stands today still means reading every
appendix that touched it: the emitter spans \`ontology/RATIONALE.md\` and
Appendices O, P and T. Nothing marks a decision replaced.

## Done looks like

A record kind holding one decision per file, designed and landed, with the
reversal the new appendix, U, records migrated into it first. The design
answers four things:

- Numbering. Principles are one sequence each appendix claims a block of, which
  is why per-decision files written in parallel were refused. The backlog's
  answer, random ids after item 177, is the one to try first.
- Supersession. \`superseded_by\` holds one id, and a decision can be replaced
  by several.
- The name. "ADR" is on \`CONTEXT.md\`'s _Avoid_ list, and "decision record"
  already means prior art's records there. It goes into \`ontology/factory.ttl\`
  when chosen.
- Which decisions migrate, and whether an appendix then cites them.
EOF
echo "$ID"
```

The item cites "Appendices O, P and T", which exist. It names U only in lowercase prose, because U does not exist until Task 11 and the citation test would fail on "Appendix {U}".

- [ ] **Step 2: Run the records check**

Run: `uv run pytest tests/records -q`
Expected: PASS. `tier: null` needs no `PRIORITY.md` line.

- [ ] **Step 3: Commit**

```bash
git add docs/backlog/
git commit -m "docs(backlog): decisions have no record of their own once the appendices are records"
```

### Task 11: Appendix {U}, rev 25

Written after Task 9, so the prose hook compares U against zero hits.

**Files:**
- Create: `docs/appendices/U-the-appendices-become-records.md`
- Modify: `DESIGN.md:5` (the status line), and the two indexes by render
- Modify: `.saffron/policy.yaml` (the comment from Task 9 gains `(Appendix {U})`)

- [ ] **Step 1: Write U**

```bash
ID=$(ls docs/backlog | sed -n 's/^\(b-[0-9a-f]*\)-decisions-have-no-record-of-their-own\.md$/\1/p')
cat > docs/appendices/U-the-appendices-become-records.md <<EOF
---
id: U
title: "rev 25: the appendices become records"
revisions: [25]
question: "Should the appendices leave \`DESIGN.md\`? Yes — a refusal reaches only as far as its reason, and the reason against ADRs was a parallel tree"
---

Appendix P answered no to ADRs three times, and \`CONTEXT.md\` §11 gave the
reason: a \`docs/adr/\` tree beside the appendices would be a second address
space for what §-numbers and letters already address, and the first two
records to disagree would do it undetectably. That reason is about a *parallel*
tree. It was read as a refusal of any record per file, which it never argued.

Two costs grew under that reading. The appendices record decisions as a
timeline, so where one decision stands today is spread across several: the
emitter across \`ontology/RATIONALE.md\` and Appendices O, P and T. And nothing
marks a decision replaced. Appendix P still says the emitter is deferred after
Appendix T reopened it.

**What changed.** The twenty appendices, A to T, moved verbatim into
\`docs/appendices/\`, one record each, as \`records/\`' second kind. Their letters
are permanent ids, so every citation still resolves. \`DESIGN.md\` keeps §0 to
§11, and both of its indexes render from the records. \`docs/appendices/**\` is
\`protected\`, as \`DESIGN.md\` is. Design:
\`docs/superpowers/specs/2026-09-18-appendices-as-records-design.md\`.

**What did not change.** There is still no \`docs/adr/\`, and ADR still means
prior art's records. An appendix is still a permanent record of what one
revision found. It is never replaced and has no status.

**The intent.** Decisions are to be recorded one per file, as their own kind,
and migrated out of the appendices. That kind is not designed here. Its name,
its numbering, and how one decision replaces several are open in backlog item
$ID, and the first record it holds is this reversal.

62. **A refusal reaches only as far as its reason.** "No ADRs" was argued
    against a parallel tree and enforced against every record per file. Read
    the reason before the verdict. Where the reason stops, the refusal stops,
    and a question outside it is still open.
EOF
```

- [ ] **Step 2: The status line**

In `DESIGN.md:5`, replace `**Status:** rev 24: ` with:

```markdown
**Status:** rev 25: **a refusal reaches only as far as its reason**. The appendices moved into `docs/appendices/` as records with their letters intact, and this document keeps §0 to §11 and two indexes rendered from them (Appendix {U}, principle 62). Prior: rev 24: 
```

The trailing space before the old text is part of the replacement.

- [ ] **Step 3: Render, then add the policy citation**

Run: `uv run python -m ontology.render && git diff DESIGN.md`
Expected: the status line, one new principle row `| 62 | A refusal reaches only as far as its reason | U |`, and one new appendix row for U with `62` in its last cell.

In `.saffron/policy.yaml`, the Task 9 comment ends with ` (Appendix {U}).` before the period.

- [ ] **Step 4: Run everything, prose hook included**

Run: `git add docs/appendices/U-the-appendices-become-records.md DESIGN.md .saffron/policy.yaml && uv run hooks/prose_limit.py && make check`
Expected: green. The prose hook reads U against zero hits and `DESIGN.md`'s new lines against its previous version. If it reports a hit in U, reword U. The hit is real, since U is new prose.

- [ ] **Step 5: Commit**

```bash
git commit -m "docs(design): rev 25 records that no ADRs was argued against a parallel tree and never reached the appendices"
```

### Task 12: The surfaces that say otherwise

**Files:**
- Modify: `CONTEXT.md` (§11 **Revision appendix**, **ADR**, naming decision 4)
- Modify: `DESIGN.md` (`:1424` §10 tree, `:1536-1537`, `:1582-1583`)
- Modify: `docs/agents/domain.md:8`, `:11`, `:18`
- Modify: `CLAUDE.md:15-17`
- Modify: `tests/test_citations.py` (module docstring `:23-25`, `test_saffron_keeps_no_adrs` docstring)
- Modify: every live file carrying the `DESIGN.md` qualifier on an appendix

- [ ] **Step 1: `CONTEXT.md` §11**

**Revision appendix**, first sentence: `A \`DESIGN.md\` appendix recording what a revision found` becomes `A record under \`docs/appendices/\` recording what a revision found`.

**ADR** entry, whole:

```markdown
**ADR**: Prior art's. The term appears in the design record only when citing
another project's decision records (Appendix D), and `docs/adr/` does not exist here.
**Saffron keeps no `docs/adr/`.** A decision becomes a principle, a revision appendix, a
`DESIGN.md` subsection, or a settled naming decision below. A parallel `docs/adr/`
tree would be a second address space for what §-numbers and letters already address,
and the first two records to disagree would do it undetectably. The appendices are
themselves records, in the one address space their letters name (Appendix {U}).
```

Naming decision 4 gains a closing sentence:

```markdown
   Narrowed in rev 25: the refusal was argued against a parallel tree, and the
   appendices became records under `docs/appendices/` with their letters intact
   (Appendix {U}, principle 62).
```

- [ ] **Step 2: `DESIGN.md`**

§10 tree, after the `DESIGN.md` line:

```
  docs/appendices/       # the revision appendices, one record each (Appendix {U})
```

`:1536-1537`: `It is navigation, not authority: where it disagrees with an appendix, the appendix is right.` becomes `It is generated from the appendix records, and its questions are navigation, not authority: where one disagrees with its appendix, the appendix is right.`

`:1582-1583`: `rewrites it from the\nappendices below` becomes `rewrites it from the\nappendix records in \`docs/appendices/\``. Keep the line wrap.

- [ ] **Step 3: `docs/agents/domain.md`**

`:8`: `and the appendices that carry the design record (\`CONTEXT.md\` §11)` becomes `and two indexes over \`docs/appendices/\`, the revision appendices that carry the design record, one record each (\`CONTEXT.md\` §11)`.

`:11`, after `a second address space for the same decisions.`, insert: `The appendices themselves are records under \`docs/appendices/\`, cited by the same letters (Appendix {U}).`

`:18`: `← §-numbered design + revision appendices + principles` becomes `← §-numbered design + the appendix and principle indexes`, and add after it:

```
├── docs/appendices/            ← revision appendices, one record each; the letter is the id
```

- [ ] **Step 4: `CLAUDE.md:15-17`**

```markdown
checked. The same command also rewrites `DESIGN.md`'s principle and appendix indexes, and those
run the other way: the appendix records in `docs/appendices/` are authoritative and the indexes
are their render, so a new principle is written into its appendix record and never into a table
(Appendix {U}).
```

- [ ] **Step 5: `tests/test_citations.py` docstrings**

Module docstring, the last paragraph:

```python
Written while deciding *against* splitting `DESIGN.md` into per-decision files.
It is what let the appendices move out as records with every letter intact
(Appendix {U}).
```

`test_saffron_keeps_no_adrs`, first line: `"""\`CONTEXT.md\` §11 refuses a \`docs/adr/\` tree beside the appendix records, and prose is what failed last time.` Keep the rest, and keep the test: `docs/adr/` still must not exist.

- [ ] **Step 6: Sweep the `DESIGN.md` qualifier**

Run: ``grep -rnE "DESIGN\.md\`? (§[0-9.]+, )?Appendi" --include='*.py' --include='*.md' --include='*.yml' --include='*.yaml' --include='*.sh' --include='*.ttl' . | grep -v -e '/.venv/' -e 'docs/evidence/' -e 'specs/done/' -e 'docs/superpowers/'``
Expected: about 20 lines. Rewrite each by hand:

- `DESIGN.md Appendix G` and `` `DESIGN.md` Appendix G `` become `Appendix G`.
- `(\`DESIGN.md\` §5.4, Appendix H)` becomes `(\`DESIGN.md\` §5.4; Appendix H)`, keeping the qualifier on the section it belongs to.

Re-run the grep. Expected: no output.

- [ ] **Step 7: Run everything**

Run: `git add -A ontology/ && uv run python -m ontology.render && git diff --exit-code -- ontology/ && make check && uv run hooks/prose_limit.py`
The sweep may edit files under `ontology/`, so they are staged before the diff checks only what the render changed.
Expected: green. The prose hook checks every edited file in scope, `CONTEXT.md`, `DESIGN.md`, `CLAUDE.md` and `docs/agents/` among them, and `.saffron/rules/*.yml` are read by the `structure` gate's own tests.

- [ ] **Step 8: Commit**

```bash
git add -A CONTEXT.md DESIGN.md CLAUDE.md docs/agents/ tests/test_citations.py saffron/ .saffron/ spikes/ ontology/ docs/backlog/
git commit -m "docs: the surfaces that said the appendices live in DESIGN.md and that Saffron keeps no records per file"
```

### Task 13: Finish

- [ ] **Step 1:** `make check`, then `uv run python -m ontology.render && git status --short`. Expected: green and a clean tree.
- [ ] **Step 2:** `uv run python -m records list appendix`. Expected: 21 lines, A to U.
- [ ] **Step 3:** Push the branch. Ask the operator before `gh stack submit`. The PR body follows `.github/pull_request_template.md`: under Verification, name the round trip from Task 6 Step 3, the guard's red run from Task 8, the two-letter mutant from Task 7, and `make check`'s count.
- [ ] **Step 4:** Dispatch the adversarial reviewer against PR 2's diff before it merges. The design was reviewed twice, and the implementation has not been reviewed yet.

---

## Self-review

- **Spec coverage.** Record location, pattern and two-letter readers: Tasks 1, 2, 7. Frontmatter and no status: Task 1. The four loader rules: Task 2. CLI: Task 4. Readers (`design_record`, both indexes, `render`, prose exemption left alone, `test_citations`, `CITING`/`LIVE_SURFACES`): Task 7. Validation (letters, citations, principle test rewrites, heading guard, `CONTRIBUTES_NO_PRINCIPLE`): Tasks 3, 7, 8. U contributes principle 62, so `CONTRIBUTES_NO_PRINCIPLE` stays empty. Protection and prose scope: Task 9. Commit ordering rule: Tasks 8, 9, 11. Pass 3 and the qualifier sweep: Task 12. Follow-on: Task 10.
- **Deliberate gap.** The spec says `prose.py` needs no change for the appendix index, and this plan makes none.
- **Names used across tasks:** `APPENDIX_ID`, `Appendix`, `BACKLOG_SECTIONS`, `Kind.sections`, `letter_order`, `appendix_letters`, `check_appendix_letters`, `design_record.appendices`, `design_record.parse(records)`, `render_principles(text, graph)`, `render_appendix_index(text, records, graph)`, `spans.APPENDIX_ANCHOR`, `spans.APPENDIX_HEADER`, `spans.appendix_index`, `cited_letters`, `addresses -> set[str]`.
