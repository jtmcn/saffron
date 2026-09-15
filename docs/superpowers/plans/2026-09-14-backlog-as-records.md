# The backlog as records — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docs/BACKLOG.md` becomes `docs/backlog/` — one file per item with typed frontmatter — with a dev-only `records/` package that loads, queries and checks them, and integrity tests that hold each item's claims to the specs and code it names.

**Architecture:** `records/` is a top-level dev-only package beside `ontology/` and `harness/`: `kinds.py` (pydantic models, one per record kind), `load.py` (frontmatter + body → `Record`), `check.py` (pure functions returning violations), `__main__.py` (the CLI). Tests under `tests/records/` exercise each check against a good fixture and a broken one; one live test asserts the real directory has no violations. The migration is two mechanical passes in one script plus an agent pass on a narrow brief.

**Tech Stack:** Python 3.12, pydantic 2, PyYAML, argparse, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-14-backlog-as-records-design.md`

## Global Constraints

- Nothing under `saffron/` imports `records/`; `records/` imports nothing from `saffron/` (spec §"Package"). The graph libraries (`rdflib`, `pyoxigraph`, `pyshacl`) stay out of `records/`.
- Frontmatter fields are scalars or lists of ids only. Unknown keys are refused, not ignored.
- Status set: `open | partial | done | superseded | wontfix`. Tier: `0..3` or `null`.
- Canonical citation form is `backlog item 118` (path-free). The check accepts `backlog item N`, `BACKLOG item N`, `item N` and plural/list forms, and only checks that `N` exists.
- Vocabulary (`CONTEXT.md`, enforced by the `retired-vocabulary` prek hook, which covers `docs/backlog/`): "cell" not "sandbox", "batch" ≠ "run", "gate result" not "gate run". The 122 item bodies pass the hook today as one file and pass it split, because the migration does not reword them.
- Comments: terse, 1–2 lines, the non-obvious "why" only.
- Commit subjects: lowercase `type(scope): what changed`, a sentence about the defect, not the file. Every commit ends with the attribution lines in the session's system reminder.
- A new test is run against the unfixed code, or against a mutant, before it is trusted (`CLAUDE.md`). Each check in Task 4–5 therefore has a broken-fixture test.
- `make check` (ruff, ty, ast-grep, retired-vocabulary, pytest) is green at the end of every task. ruff excludes `docs/` and `.saffron/specs`; `records/` and `tests/` are in scope.
- Branching: the spec is committed on `joel/backlog-as-records`. PR 1 (Tasks 1–6) lands on that branch. PR 2 (Tasks 7–10) is stacked on it with `gh stack` (the `gh-stack` skill has the mechanics; plain `git` for everything else). Never `git push --force`.

---

## File structure

```
records/
  __init__.py          # docstring only
  kinds.py             # BacklogItem model, Status/Tier types, Kind registry
  load.py              # RecordError, Record, split_sections, parse, load
  check.py             # Violation + one pure function per integrity rule
  __main__.py          # argparse CLI: list, show, grep
tests/records/
  fixtures/
    good/              # a tiny repo root: docs/backlog/, .saffron/specs/, DESIGN.md, saffron/
  test_records_kinds.py
  test_records_load.py
  test_records_cli.py
  test_records_check.py
  test_records_integrity.py   # the one live test; PR 1 points it at fixtures/good, PR 2 at the repo
docs/backlog/          # PR 2
  README.md
  PRIORITY.md
  001-….md … 122-….md
docs/evidence/scripts/2026-09-14-split-backlog.py   # PR 2, passes 1 and 2
```

---

## PR 1 — the `records/` package

### Task 1: The `BacklogItem` model

**Files:**
- Create: `records/__init__.py`, `records/kinds.py`
- Test: `tests/records/test_records_kinds.py`

**Interfaces:**
- Produces: `records.kinds.BacklogItem` (pydantic `BaseModel`, `extra="forbid"`), `records.kinds.Status = Literal["open","partial","done","superseded","wontfix"]`, `records.kinds.CLOSED: frozenset[str]`, `records.kinds.Kind` (dataclass: `name: str`, `directory: str`, `pattern: str`, `model: type[BaseModel]`), `records.kinds.KINDS: dict[str, Kind]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/records/test_records_kinds.py
"""The frontmatter model refuses what the spec says it refuses, naming the field."""

import pytest
from pydantic import ValidationError

from records.kinds import KINDS, BacklogItem

MINIMAL = {"id": 7, "title": "Seven", "status": "open"}


def test_a_minimal_open_item_validates():
    item = BacklogItem.model_validate(MINIMAL)
    assert item.tier is None
    assert item.specs == [] and item.prs == [] and item.cites == []
    assert item.by_hand is False


def test_an_unknown_key_is_refused_not_ignored():
    with pytest.raises(ValidationError, match="evidence"):
        BacklogItem.model_validate({**MINIMAL, "evidence": ["x.md"]})


@pytest.mark.parametrize("status", ["done", "superseded", "wontfix"])
def test_a_closed_item_needs_a_closed_date(status):
    with pytest.raises(ValidationError, match="closed"):
        BacklogItem.model_validate({**MINIMAL, "status": status, "prs": [1], "superseded_by": 8})


@pytest.mark.parametrize("status", ["done", "wontfix"])
def test_a_closed_item_names_what_closed_it(status):
    with pytest.raises(ValidationError, match="specs, prs or commits"):
        BacklogItem.model_validate({**MINIMAL, "status": status, "closed": "2026-09-14"})


def test_a_superseded_item_names_its_successor():
    with pytest.raises(ValidationError, match="superseded_by"):
        BacklogItem.model_validate(
            {**MINIMAL, "status": "superseded", "closed": "2026-09-14", "prs": [1]}
        )


def test_an_open_item_may_not_carry_a_closed_date():
    with pytest.raises(ValidationError, match="closed"):
        BacklogItem.model_validate({**MINIMAL, "closed": "2026-09-14"})


def test_tier_is_zero_to_three_or_null():
    with pytest.raises(ValidationError, match="tier"):
        BacklogItem.model_validate({**MINIMAL, "tier": 4})
    assert BacklogItem.model_validate({**MINIMAL, "tier": 0}).tier == 0


def test_a_spec_id_has_the_spec_shape():
    with pytest.raises(ValidationError, match="specs"):
        BacklogItem.model_validate({**MINIMAL, "specs": ["87"]})


def test_a_citation_carries_its_section_sign():
    with pytest.raises(ValidationError, match="cites"):
        BacklogItem.model_validate({**MINIMAL, "cites": ["5.4"]})


def test_backlog_is_a_registered_kind():
    kind = KINDS["backlog"]
    assert kind.directory == "docs/backlog"
    assert kind.model is BacklogItem
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/records/test_records_kinds.py -q`
Expected: `ModuleNotFoundError: No module named 'records'`

- [ ] **Step 3: Write the model**

```python
# records/__init__.py
"""Saffron's own project records — backlog items today, specs next — as files
with typed frontmatter. Dev-only, like `ontology/` and `harness/`: nothing
under `saffron/` imports this, and this imports nothing from `saffron/`."""
```

```python
# records/kinds.py
"""One pydantic model per record kind, and the registry that names them.

Every field is a scalar or a list of ids — never prose — so a later lift into
the ontology graph is mechanical (spec, "Follow-ons")."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["open", "partial", "done", "superseded", "wontfix"]
CLOSED: frozenset[str] = frozenset({"done", "superseded", "wontfix"})
_SPEC_ID = r"^[A-Za-z0-9]+-[0-9]+$"
_SECTION = r"^§\d+(\.\d+)*[a-z]?$"


class BacklogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1)
    title: str = Field(min_length=1)
    status: Status
    tier: int | None = Field(default=None, ge=0, le=3)
    filed: dt.date | None = None
    closed: dt.date | None = None
    by_hand: bool = False
    specs: list[str] = Field(default_factory=list)
    prs: list[int] = Field(default_factory=list)
    commits: list[str] = Field(default_factory=list)
    cites: list[str] = Field(default_factory=list)
    related: list[int] = Field(default_factory=list)
    superseded_by: int | None = None

    @model_validator(mode="after")
    def _shapes(self) -> BacklogItem:
        import re

        bad = [s for s in self.specs if not re.match(_SPEC_ID, s)]
        if bad:
            raise ValueError(f"specs: not a spec id: {bad}")
        bad = [c for c in self.cites if not re.match(_SECTION, c)]
        if bad:
            raise ValueError(f"cites: not a § address: {bad}")
        return self

    @model_validator(mode="after")
    def _closure(self) -> BacklogItem:
        if self.status in CLOSED:
            if self.closed is None:
                raise ValueError(f"closed: required when status is {self.status}")
            if not (self.specs or self.prs or self.commits):
                raise ValueError("specs, prs or commits: a close names what closed it")
        elif self.closed is not None:
            raise ValueError(f"closed: set on an item whose status is {self.status}")
        if self.status == "superseded" and self.superseded_by is None:
            raise ValueError("superseded_by: required when status is superseded")
        return self


@dataclass(frozen=True)
class Kind:
    name: str
    directory: str
    pattern: str
    model: type[BaseModel]


KINDS: dict[str, Kind] = {
    "backlog": Kind("backlog", "docs/backlog", r"^(\d{3})-[a-z0-9-]+\.md$", BacklogItem),
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/records/test_records_kinds.py -q`
Expected: 11 passed. If `match="specs, prs or commits"` fails because pydantic wraps the message, the assertion still matches on substring — check the raw message with `-vv` before changing the test.

- [ ] **Step 5: Lint and type-check, then commit**

Run: `make check`
Expected: green.

```bash
git add records/__init__.py records/kinds.py tests/records/test_records_kinds.py
git commit -m "feat(records): a backlog item had no field a program could read, so give it a model"
```

---

### Task 2: Loading a directory of records

**Files:**
- Create: `records/load.py`
- Test: `tests/records/test_records_load.py`, `tests/records/fixtures/good/docs/backlog/*.md`

**Interfaces:**
- Consumes: `records.kinds.Kind`, `KINDS`, `CLOSED`.
- Produces: `records.load.RecordError(ValueError)` (carries `path: Path | None`); `records.load.Record` (dataclass: `model: BaseModel`, `path: Path`, `sections: dict[str, str]` keyed by `## ` heading text, `body: str`); `records.load.split_sections(body: str) -> dict[str, str]`; `records.load.parse(text: str, kind: Kind, path: Path | None = None) -> Record`; `records.load.load(kind: Kind, root: Path) -> list[Record]` sorted by `model.id`; `records.load.REQUIRED_SECTIONS = ("Problem", "Done looks like", "Record")`.

- [ ] **Step 1: Write the good fixture**

Three items and the two hand-written files, at `tests/records/fixtures/good/docs/backlog/`:

`001-a-gate-that-never-ran.md`
```markdown
---
id: 1
title: A gate that never ran read as green
status: done
tier: 1
closed: 2026-09-01
specs: [SA-0001]
prs: [10]
cites: ["§5.4"]
---

## Problem

The `tool` field was a string literal. See backlog item 2.

## Done looks like

`tool` is obtained by executing the tool.

## Record

**Done, 2026-09-01.** `SA-0001`, PR #10.
```

`002-the-index-drifts.md`
```markdown
---
id: 2
title: The index drifts from the items
status: partial
tier: 2
related: [1]
---

## Problem

The hand-sorted index and the items disagree.

## Done looks like

A test holds the index to the records.

## Record

**Done, 2026-09-02**, the first half: the records exist.
```

`003-a-corpse-reads-as-drained.md`
```markdown
---
id: 3
title: A corpse reads as a drained night
status: open
tier: 1
cites: ["§4.2.1"]
---

## Problem

Nothing stamps `ORPHANED`.

## Done looks like

The scan stamps it.
```

`README.md`
```markdown
# Backlog

Numbered in filing order; the numbers are an API.
```

`PRIORITY.md`
```markdown
# Priority — the order to work in

### Tier 1 — breaks at 03:00

~~**1**~~, **3**.

### Tier 2 — the morning after

**2**.
```

Also the rest of the fixture root, used by Task 4–5 and cheap to add now:

`tests/records/fixtures/good/.saffron/specs/done/SA-0001-a-gate.md`
```markdown
---
id: SA-0001
title: a gate
type: bug
---

## Context

backlog item 1.
```

`tests/records/fixtures/good/DESIGN.md`
```markdown
# Design

## 4. Control plane

### 4.2 Scheduler

#### 4.2.1 The first night

## 5. The cell pipeline

### 5.4 Phase 3 — GATE ⇄ REPAIR

Backlog item 3 is the scan.
```

`tests/records/fixtures/good/saffron/example.py`
```python
# backlog item 1: the tool field is executed, never spelled.
TOOL = "measured"
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/records/test_records_load.py
"""A record is its frontmatter plus its body split at `## ` headings; a file
that breaks a rule is refused with the file and the field named."""

from pathlib import Path

import pytest

from records.kinds import KINDS
from records.load import Record, RecordError, load, parse, split_sections

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
BACKLOG = KINDS["backlog"]


def test_sections_split_at_h2_and_keep_h3_inside():
    body = "## Problem\n\nA.\n\n### Defect A\n\nB.\n\n## Record\n\nC.\n"
    assert split_sections(body) == {"Problem": "A.\n\n### Defect A\n\nB.", "Record": "C."}


def test_a_fenced_h2_is_not_a_heading():
    body = "## Problem\n\n```\n## not a heading\n```\n\n## Record\n\nx\n"
    assert list(split_sections(body)) == ["Problem", "Record"]


def test_load_reads_every_item_in_id_order():
    records = load(BACKLOG, FIXTURE)
    assert [r.model.id for r in records] == [1, 2, 3]
    assert all(isinstance(r, Record) for r in records)
    assert records[0].sections["Done looks like"].startswith("`tool` is obtained")


def test_load_ignores_the_hand_written_files():
    names = {r.path.name for r in load(BACKLOG, FIXTURE)}
    assert "README.md" not in names and "PRIORITY.md" not in names


def test_a_filename_whose_prefix_disagrees_with_its_id_is_refused(tmp_path):
    item = tmp_path / "docs" / "backlog" / "009-nine.md"
    item.parent.mkdir(parents=True)
    item.write_text("---\nid: 8\ntitle: Eight\nstatus: open\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n")
    with pytest.raises(RecordError, match="009-nine.md.*id"):
        load(BACKLOG, tmp_path)


def test_a_file_with_no_frontmatter_is_refused():
    with pytest.raises(RecordError, match="frontmatter"):
        parse("## Problem\n\nx\n", BACKLOG)


def test_a_bad_field_names_the_field():
    with pytest.raises(RecordError, match="tier"):
        parse("---\nid: 1\ntitle: T\nstatus: open\ntier: 9\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n", BACKLOG)


@pytest.mark.parametrize("status", ["open", "partial"])
def test_an_unfinished_item_needs_done_looks_like(status):
    text = f"---\nid: 1\ntitle: T\nstatus: {status}\n---\n\n## Problem\n\nx\n\n## Record\n\n**Done, 2026-01-01.** half\n"
    with pytest.raises(RecordError, match="Done looks like"):
        parse(text, BACKLOG)


def test_a_partial_item_needs_a_dated_record_entry():
    text = "---\nid: 1\ntitle: T\nstatus: partial\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n\n## Record\n\nno date here\n"
    with pytest.raises(RecordError, match="Record.*dated"):
        parse(text, BACKLOG)


def test_an_unknown_section_is_refused():
    text = "---\nid: 1\ntitle: T\nstatus: open\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n\n## Notes\n\nz\n"
    with pytest.raises(RecordError, match="Notes"):
        parse(text, BACKLOG)


def test_sections_must_keep_their_order():
    text = "---\nid: 1\ntitle: T\nstatus: open\n---\n\n## Done looks like\n\ny\n\n## Problem\n\nx\n"
    with pytest.raises(RecordError, match="order"):
        parse(text, BACKLOG)
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/records/test_records_load.py -q`
Expected: `ImportError: cannot import name 'Record' from 'records.load'` (or module not found).

- [ ] **Step 4: Write the loader**

```python
# records/load.py
"""Frontmatter and body → `Record`. Mirrors `saffron/intake.py`'s shape on
purpose, so an agent that can write a spec can write an item; it does not
import it, because `records/` stays outside `saffron/`."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from records.kinds import CLOSED, Kind

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
_H2 = re.compile(r"^## (.+?)\s*$")
_FENCE = re.compile(r"^\s*```")
_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")

REQUIRED_SECTIONS = ("Problem", "Done looks like", "Record")


class RecordError(ValueError):
    def __init__(self, message: str, path: Path | None = None) -> None:
        super().__init__(f"{path}: {message}" if path else message)
        self.path = path


@dataclass(frozen=True)
class Record:
    model: BaseModel
    path: Path
    body: str
    sections: dict[str, str]


def split_sections(body: str) -> dict[str, str]:
    """`## ` headings outside fences open a section; `###` stays inside it."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    fenced = False
    for line in body.splitlines():
        if _FENCE.match(line):
            fenced = not fenced
        if not fenced and (heading := _H2.match(line)):
            current = heading.group(1)
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def parse(text: str, kind: Kind, path: Path | None = None) -> Record:
    match = _FRONTMATTER.match(text)
    if match is None:
        raise RecordError("no YAML frontmatter block", path)
    raw, body = match.group(1), match.group(2)
    try:
        fields = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise RecordError(f"frontmatter is not valid YAML: {exc}", path) from exc
    if not isinstance(fields, dict):
        raise RecordError("frontmatter is not a mapping", path)
    fields = {k: v for k, v in fields.items() if v is not None}
    try:
        model = kind.model.model_validate(fields)
    except ValidationError as exc:
        raise RecordError(f"frontmatter is invalid: {exc}", path) from exc

    sections = split_sections(body)
    unknown = [s for s in sections if s not in REQUIRED_SECTIONS]
    if unknown:
        raise RecordError(f"unknown section(s) {unknown}; the body is {REQUIRED_SECTIONS}", path)
    order = [s for s in REQUIRED_SECTIONS if s in sections]
    if list(sections) != order:
        raise RecordError(f"sections out of order: {list(sections)}; the order is {REQUIRED_SECTIONS}", path)
    _check_sections(model, sections, path)
    return Record(model=model, path=path or Path("<text>"), body=body, sections=sections)


def _check_sections(model: BaseModel, sections: dict[str, str], path: Path | None) -> None:
    status = getattr(model, "status", None)
    if status is None:
        return
    if status not in CLOSED and not sections.get("Done looks like"):
        raise RecordError(f"status {status} needs a non-empty `## Done looks like`", path)
    if status == "partial" and not _DATE.search(sections.get("Record", "")):
        raise RecordError("status partial needs a dated entry in `## Record`", path)


def load(kind: Kind, root: Path) -> list[Record]:
    directory = root / kind.directory
    pattern = re.compile(kind.pattern)
    records: list[Record] = []
    for path in sorted(directory.glob("*.md")):
        match = pattern.match(path.name)
        if match is None:
            continue
        record = parse(path.read_text(), kind, path)
        if int(match.group(1)) != record.model.id:  # type: ignore[attr-defined]
            raise RecordError(f"filename prefix {match.group(1)} but id {record.model.id}", path)  # type: ignore[attr-defined]
        records.append(record)
    return sorted(records, key=lambda r: r.model.id)  # type: ignore[attr-defined]
```

The three `type: ignore` comments will fail `integrity`'s suppression scan and `make check`'s ty hook may not need them. Do not ship them: give `Kind` a typed accessor instead —

```python
# in records/kinds.py, add:
class Identified(BaseModel):
    """What every kind's model has: an `id` the filename repeats."""
    id: int | str

# and make BacklogItem subclass Identified, keeping its own `id: int = Field(ge=1)`.
# In Kind: `model: type[Identified]`.
```

Then in `load.py`, `record.model.id` type-checks and the three ignores go. Adjust `KINDS` accordingly.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/records/ -q`
Expected: all pass.

- [ ] **Step 6: Lint, type-check, commit**

Run: `make check`
Expected: green — in particular, `ty` on `records/load.py` with no suppressions.

```bash
git add records/kinds.py records/load.py tests/records/
git commit -m "feat(records): a directory of items loads as records, and a file that breaks a rule names the file and the field"
```

---

### Task 3: The command

**Files:**
- Create: `records/__main__.py`
- Modify: `Makefile` (add a `backlog` target)
- Test: `tests/records/test_records_cli.py`

**Interfaces:**
- Consumes: `records.load.load`, `records.kinds.KINDS`.
- Produces: `python -m records list <kind> [--status S] [--tier N] [--root PATH]`, `python -m records show <id> [--section NAME] [--root PATH]`, `python -m records grep <pattern> [--root PATH]`. Exit `0` on success, `1` on a missing record, `2` on a `RecordError`. `records.__main__.main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/records/test_records_cli.py
"""The command is the retrieval fix: one record in one read, and the open set
on one screen. Run as a subprocess, the way `tests/test_cli.py` runs `saffron`."""

import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
ROOT = Path(__file__).resolve().parents[2]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "records", *args, "--root", str(FIXTURE)],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )


def test_list_prints_one_line_per_item_in_id_order():
    out = run("list", "backlog").stdout.splitlines()
    assert [line.split()[0] for line in out] == ["1", "2", "3"]
    assert out[0].split(maxsplit=3) == ["1", "done", "1", "A gate that never ran read as green"]


def test_list_filters_on_status_and_tier():
    assert [l.split()[0] for l in run("list", "backlog", "--status", "open").stdout.splitlines()] == ["3"]
    assert [l.split()[0] for l in run("list", "backlog", "--tier", "1").stdout.splitlines()] == ["1", "3"]


def test_list_shows_a_dash_for_no_tier(tmp_path):
    (tmp_path / "docs" / "backlog").mkdir(parents=True)
    (tmp_path / "docs" / "backlog" / "001-x.md").write_text(
        "---\nid: 1\ntitle: X\nstatus: open\n---\n\n## Problem\n\np\n\n## Done looks like\n\nd\n"
    )
    proc = subprocess.run(
        [sys.executable, "-m", "records", "list", "backlog", "--root", str(tmp_path)],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    assert proc.stdout.split(maxsplit=3)[:3] == ["1", "open", "-"]


def test_show_prints_the_record_and_nothing_else():
    out = run("show", "2").stdout
    assert out.startswith("---\nid: 2\n")
    assert "## Done looks like" in out
    assert "A gate that never ran" not in out


def test_show_one_section():
    out = run("show", "1", "--section", "Done looks like").stdout
    assert out.strip() == "`tool` is obtained by executing the tool."


def test_show_a_spec_id_lists_the_items_that_name_it():
    proc = run("show", "SA-0001")
    assert proc.returncode == 0
    assert proc.stdout.splitlines()[0].split()[0] == "1"


def test_show_a_missing_id_exits_one_and_says_so():
    proc = run("show", "42")
    assert proc.returncode == 1
    assert "42" in proc.stderr


def test_grep_prints_id_title_and_the_matching_line():
    out = run("grep", "stamps").stdout.splitlines()
    assert out[0].split(maxsplit=1)[0] == "3"
    assert any("Nothing stamps" in line for line in out)


def test_a_broken_directory_exits_two_naming_the_file(tmp_path):
    (tmp_path / "docs" / "backlog").mkdir(parents=True)
    (tmp_path / "docs" / "backlog" / "001-x.md").write_text("---\nid: 1\ntitle: X\nstatus: done\n---\n")
    proc = subprocess.run(
        [sys.executable, "-m", "records", "list", "backlog", "--root", str(tmp_path)],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    assert proc.returncode == 2
    assert "001-x.md" in proc.stderr
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/records/test_records_cli.py -q`
Expected: every test fails with `No module named records.__main__`.

- [ ] **Step 3: Write the command**

```python
# records/__main__.py
"""`python -m records`: list, show, grep. Plain text, one record per line for
`list`, so it composes with grep and reads cleanly in a tool result."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from records.kinds import KINDS
from records.load import Record, RecordError, load

REPO_ROOT = Path(__file__).resolve().parents[1]


def _line(record: Record) -> str:
    m = record.model
    tier = "-" if getattr(m, "tier", None) is None else str(m.tier)
    return f"{m.id:>3}  {m.status:<10}  {tier}  {m.title}"


def _render(record: Record, section: str | None) -> str:
    if section is None:
        return record.path.read_text()
    if section not in record.sections:
        raise SystemExit(f"{record.model.id} has no section {section!r}; it has {list(record.sections)}")
    return record.sections[section] + "\n"


def cmd_list(args: argparse.Namespace) -> int:
    records = load(KINDS[args.kind], args.root)
    for record in records:
        m = record.model
        if args.status and m.status != args.status:
            continue
        if args.tier is not None and getattr(m, "tier", None) != args.tier:
            continue
        print(_line(record))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    records = load(KINDS["backlog"], args.root)
    if args.id.isdigit():
        wanted = [r for r in records if r.model.id == int(args.id)]
        if not wanted:
            print(f"no backlog item {args.id}", file=sys.stderr)
            return 1
        print(_render(wanted[0], args.section), end="")
        return 0
    # Not a kind yet: a spec id answers with the items whose `specs:` name it.
    naming = [r for r in records if args.id in getattr(r.model, "specs", [])]
    if not naming:
        print(f"no backlog item names {args.id}", file=sys.stderr)
        return 1
    for record in naming:
        print(_line(record))
    return 0


def cmd_grep(args: argparse.Namespace) -> int:
    pattern = re.compile(args.pattern, re.IGNORECASE)
    for record in load(KINDS["backlog"], args.root):
        hits = [line for line in record.body.splitlines() if pattern.search(line)]
        if hits:
            print(f"{record.model.id:>3}  {record.model.title}")
            for hit in hits:
                print(f"     {hit}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="records")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repo root (default: this checkout)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="one line per record")
    p.add_argument("kind", choices=sorted(KINDS))
    p.add_argument("--status")
    p.add_argument("--tier", type=int)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="one record, or the records naming a spec id")
    p.add_argument("id")
    p.add_argument("--section")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("grep", help="id, title and matching lines across bodies")
    p.add_argument("pattern")
    p.set_defaults(func=cmd_grep)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RecordError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

`argparse` puts `--root` before the subcommand; the tests pass it *after*. Make `--root` accepted in both places by adding it to each subparser too (`for p in (list, show, grep): p.add_argument("--root", type=Path, default=REPO_ROOT)`), and drop it from the top-level parser — one definition, on the subparsers, is simpler than two.

- [ ] **Step 4: Add the Makefile target**

```makefile
.PHONY: install lint fmt test check backlog

backlog:
	uv run python -m records list backlog
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/records/test_records_cli.py -q && make backlog`
Expected: tests pass; `make backlog` fails with exit 2 because `docs/backlog/` does not exist yet — that is expected until PR 2. Confirm its stderr names `docs/backlog`. (If `load` raises `FileNotFoundError` instead of `RecordError`, catch it in `load` and raise `RecordError(f"no directory {directory}")`.)

- [ ] **Step 6: Commit**

Run: `make check` → green.

```bash
git add records/__main__.py Makefile tests/records/test_records_cli.py records/load.py
git commit -m "feat(records): reading one backlog item meant reading 400 KB, so give the records a command"
```

---

### Task 4: Integrity checks — ids, links, specs, citations

**Files:**
- Create: `records/check.py`
- Test: `tests/records/test_records_check.py`

**Interfaces:**
- Consumes: `records.load.Record`, `load`, `KINDS`.
- Produces, in `records.check`: `Violation` (dataclass: `path: Path`, `field: str`, `message: str`; `__str__` → `f"{path}: {field}: {message}"`); `check_ids(records) -> list[Violation]`; `check_links(records) -> list[Violation]`; `check_specs_resolve(records, root) -> list[Violation]`; `check_cites_resolve(records, sections: set[str]) -> list[Violation]`; `cited_items(text: str) -> set[int]`; `check_item_citations(root, ids: set[int]) -> list[Violation]`; `CITING = ("saffron", "tests", ".saffron/specs", "DESIGN.md")`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/records/test_records_check.py
"""Each check against the good fixture (no violations) and a broken copy of it
(exactly the violation it exists to find). The broken copy is the mutant the
check is trusted against."""

import shutil
from pathlib import Path

import pytest

from records.check import (
    check_cites_resolve,
    check_ids,
    check_item_citations,
    check_links,
    check_specs_resolve,
    cited_items,
)
from records.kinds import KINDS
from records.load import load

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
BACKLOG = KINDS["backlog"]


@pytest.fixture
def broken(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE, tmp_path / "root")
    return tmp_path / "root"


def _item(root: Path, name: str) -> Path:
    return root / "docs" / "backlog" / name


def _rewrite(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new, 1))


def test_the_good_fixture_has_no_violations():
    records = load(BACKLOG, FIXTURE)
    sections = {"4", "4.2", "4.2.1", "5", "5.4"}
    assert check_ids(records) == []
    assert check_links(records) == []
    assert check_specs_resolve(records, FIXTURE) == []
    assert check_cites_resolve(records, sections) == []
    assert check_item_citations(FIXTURE, {r.model.id for r in records}) == []


def test_ids_must_be_contiguous(broken):
    _item(broken, "003-a-corpse-reads-as-drained.md").rename(_item(broken, "005-a-corpse.md"))
    _rewrite(_item(broken, "005-a-corpse.md"), "id: 3", "id: 5")
    [v] = check_ids(load(BACKLOG, broken))
    assert v.field == "id" and "3" in v.message and "4" in v.message


def test_ids_must_be_unique(broken):
    shutil.copy(_item(broken, "003-a-corpse-reads-as-drained.md"), _item(broken, "003-twice.md"))
    violations = check_ids(load(BACKLOG, broken))
    assert any(v.field == "id" and "twice" in str(v) for v in violations)


def test_related_must_resolve(broken):
    _rewrite(_item(broken, "002-the-index-drifts.md"), "related: [1]", "related: [1, 9]")
    [v] = check_links(load(BACKLOG, broken))
    assert v.field == "related" and "9" in v.message


def test_superseded_by_must_resolve_and_not_be_superseded_itself(broken):
    _rewrite(
        _item(broken, "003-a-corpse-reads-as-drained.md"),
        "status: open\n",
        "status: superseded\nclosed: 2026-09-03\nprs: [1]\nsuperseded_by: 2\n",
    )
    _rewrite(
        _item(broken, "002-the-index-drifts.md"),
        "status: partial\n",
        "status: superseded\nclosed: 2026-09-03\nprs: [1]\nsuperseded_by: 1\n",
    )
    fields = {v.field for v in check_links(load(BACKLOG, broken))}
    assert fields == {"superseded_by"}


def test_specs_must_resolve_to_a_spec_file(broken):
    _rewrite(_item(broken, "001-a-gate-that-never-ran.md"), "specs: [SA-0001]", "specs: [SA-0001, SA-0099]")
    [v] = check_specs_resolve(load(BACKLOG, broken), broken)
    assert v.field == "specs" and "SA-0099" in v.message


def test_cites_must_resolve_to_a_design_section():
    records = load(BACKLOG, FIXTURE)
    [v] = check_cites_resolve(records, {"4", "5"})
    assert v.field == "cites"
    assert "§5.4" in v.message or "§4.2.1" in v.message


@pytest.mark.parametrize(
    "text, expected",
    [
        ("see backlog item 33.", {33}),
        ("(`docs/BACKLOG.md` items 65, 72)", {65, 72}),
        ("items **81**–**85** are done", {81, 85}),
        ("BACKLOG item 118 and item 119", {118, 119}),
        ("the third item in the list", set()),
        ("item 3 of `touches`", {3}),
    ],
)
def test_cited_items_reads_every_form_the_corpus_uses(text, expected):
    assert cited_items(text) == expected


def test_a_code_comment_citing_a_missing_item_is_a_violation(broken):
    (broken / "saffron" / "example.py").write_text("# backlog item 77 says so\n")
    [v] = check_item_citations(broken, {1, 2, 3})
    assert v.path == broken / "saffron" / "example.py" and "77" in v.message


def test_a_spec_context_citing_a_missing_item_is_a_violation(broken):
    spec = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    _rewrite(spec, "backlog item 1.", "backlog item 1 and item 12.")
    [v] = check_item_citations(broken, {1, 2, 3})
    assert "12" in v.message


def test_evidence_is_not_scanned(broken):
    ev = broken / "docs" / "evidence"
    ev.mkdir(parents=True)
    (ev / "2026-01-01-x.md").write_text("item 999 was true then\n")
    assert check_item_citations(broken, {1, 2, 3}) == []
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/records/test_records_check.py -q`
Expected: `ModuleNotFoundError: No module named 'records.check'`.

- [ ] **Step 3: Write the checks**

```python
# records/check.py
"""One pure function per integrity rule, each returning the violations it
found. The live test asserts the list is empty; the unit tests assert each
function finds the one defect its broken fixture plants."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from records.kinds import CLOSED
from records.load import Record

# Where a live `item N` is a promise someone can follow today. Not
# `docs/evidence/`: dated primary records, true on their date.
CITING = ("saffron", "tests", ".saffron/specs", "DESIGN.md")
_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".sh"}

# `item 33`, `items 65, 72`, `items **81**–**85**`, `BACKLOG item 118`. A range
# reads its endpoints, as the § citation test does for appendices.
_ITEMS = re.compile(
    r"(?i)\b(?:backlog\s+)?items?\s+((?:\*{0,2}\d{1,3}\*{0,2}(?:\s*(?:,|and|–|—|-)\s*)?)+)"
)
_NUM = re.compile(r"\d+")


@dataclass(frozen=True)
class Violation:
    path: Path
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.field}: {self.message}"


def _ids(records: list[Record]) -> dict[int, Record]:
    return {int(r.model.id): r for r in records}


def check_ids(records: list[Record]) -> list[Violation]:
    out: list[Violation] = []
    counts = Counter(int(r.model.id) for r in records)
    for r in records:
        if counts[int(r.model.id)] > 1:
            out.append(Violation(r.path, "id", f"{r.model.id} is used more than once"))
    present = set(counts)
    if present:
        missing = sorted(set(range(1, max(present) + 1)) - present)
        if missing:
            out.append(Violation(records[0].path.parent, "id", f"ids are not contiguous; missing {missing}"))
    return out


def check_links(records: list[Record]) -> list[Violation]:
    by_id = _ids(records)
    out: list[Violation] = []
    for r in records:
        m = r.model
        for other in getattr(m, "related", []):
            if other not in by_id:
                out.append(Violation(r.path, "related", f"names item {other}, which does not exist"))
        target = getattr(m, "superseded_by", None)
        if target is not None:
            if target not in by_id:
                out.append(Violation(r.path, "superseded_by", f"names item {target}, which does not exist"))
            elif by_id[target].model.status == "superseded":
                out.append(Violation(r.path, "superseded_by", f"item {target} is itself superseded"))
    return out


def spec_files(root: Path) -> dict[str, Path]:
    """Spec id → file, over the queue and `done/`."""
    found: dict[str, Path] = {}
    for path in (root / ".saffron" / "specs").glob("**/*.md"):
        found[path.name.split("-", 2)[0] + "-" + path.name.split("-", 2)[1]] = path
    return found


def check_specs_resolve(records: list[Record], root: Path) -> list[Violation]:
    specs = spec_files(root)
    return [
        Violation(r.path, "specs", f"{spec} has no file under .saffron/specs/")
        for r in records
        for spec in getattr(r.model, "specs", [])
        if spec not in specs
    ]


def check_cites_resolve(records: list[Record], sections: set[str]) -> list[Violation]:
    return [
        Violation(r.path, "cites", f"{cite} is not a DESIGN.md section")
        for r in records
        for cite in getattr(r.model, "cites", [])
        if cite.lstrip("§") not in sections
    ]


def cited_items(text: str) -> set[int]:
    return {int(n) for m in _ITEMS.finditer(text) for n in _NUM.findall(m.group(1))}


def _citing_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for name in CITING:
        path = root / name
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            out.extend(p for p in path.rglob("*") if p.is_file() and p.suffix in _SUFFIXES)
    return sorted(out)


def check_item_citations(root: Path, ids: set[int]) -> list[Violation]:
    out: list[Violation] = []
    for path in _citing_files(root):
        for n in sorted(cited_items(path.read_text()) - ids):
            out.append(Violation(path, "item", f"cites backlog item {n}, which does not exist"))
    return out
```

`spec_files` splits on the first two hyphens: `SA-0001-a-gate.md` → `SA-0001`. Write it more plainly with a regex `^([A-Za-z0-9]+-\d+)-` and skip files that do not match.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/records/test_records_check.py -q`
Expected: all pass. If `test_cited_items_reads_every_form_the_corpus_uses[the third item…]` fails, the regex is matching "item in" — it requires a digit after the word, so it should not; check the case `"item 3 of"` still passes.

- [ ] **Step 5: Commit**

Run: `make check` → green.

```bash
git add records/check.py tests/records/test_records_check.py
git commit -m "feat(records): an item could name a spec, a section or another item that did not exist, so check every declared link"
```

---

### Task 5: Integrity checks — workflow, the index, and the old path

**Files:**
- Modify: `records/check.py`
- Test: `tests/records/test_records_check.py` (append)

**Interfaces:**
- Produces: `check_done_specs_are_done(records, root) -> list[Violation]`; `check_specs_name_their_items(records, root) -> list[Violation]`; `check_priority(records, priority_md: Path) -> list[Violation]`; `check_no_old_path(root) -> list[Violation]`; `OLD_PATH = "docs/BACKLOG.md"`; `LIVE_SURFACES = ("saffron", "tests", ".saffron/specs", "CLAUDE.md", "DESIGN.md", "README.md", "docs/agents")` — `.saffron/specs/done` is excluded inside the function.
- `check_all(root, sections) -> list[Violation]` runs everything on `load(KINDS["backlog"], root)`.

- [ ] **Step 1: Append the failing tests**

```python
# append to tests/records/test_records_check.py
from records.check import (  # noqa: E402  — appended after the first import block; merge into it
    check_all,
    check_done_specs_are_done,
    check_no_old_path,
    check_priority,
    check_specs_name_their_items,
)


def test_the_good_fixture_passes_every_check():
    assert check_all(FIXTURE, {"4", "4.2", "4.2.1", "5", "5.4"}) == []


def test_a_done_item_may_not_name_a_spec_still_in_the_queue(broken):
    done = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    done.rename(broken / ".saffron" / "specs" / "SA-0001-a-gate.md")
    [v] = check_done_specs_are_done(load(BACKLOG, broken), broken)
    assert v.field == "specs" and "SA-0001" in v.message


def test_a_spec_citing_an_item_must_be_listed_by_it(broken):
    _rewrite(_item(broken, "001-a-gate-that-never-ran.md"), "specs: [SA-0001]\n", "specs: []\ncommits: [abc1234]\n")
    [v] = check_specs_name_their_items(load(BACKLOG, broken), broken)
    assert v.field == "specs" and "SA-0001" in v.message


def test_a_done_spec_may_not_leave_its_item_open(broken):
    _rewrite(_item(broken, "003-a-corpse-reads-as-drained.md"), "status: open", "status: open")
    spec = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    _rewrite(spec, "backlog item 1.", "backlog item 3.")
    _rewrite(_item(broken, "003-a-corpse-reads-as-drained.md"), "cites:", "specs: [SA-0001]\ncites:")
    violations = check_specs_name_their_items(load(BACKLOG, broken), broken)
    assert any(v.field == "status" and "SA-0001" in v.message for v in violations)


def test_priority_may_not_name_a_missing_item(broken):
    _rewrite(broken / "docs" / "backlog" / "PRIORITY.md", "**3**.", "**3**, **9**.")
    [v] = check_priority(load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md")
    assert "9" in v.message


def test_priority_may_not_strike_an_open_item(broken):
    _rewrite(broken / "docs" / "backlog" / "PRIORITY.md", "**3**.", "~~**3**~~.")
    [v] = check_priority(load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md")
    assert "3" in v.message and "open" in v.message


def test_a_tiered_item_is_named_under_its_tier(broken):
    _rewrite(_item(broken, "002-the-index-drifts.md"), "tier: 2", "tier: 1")
    [v] = check_priority(load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md")
    assert v.field == "tier" and "2" in v.message


def test_an_id_named_under_another_tier_in_prose_is_fine(broken):
    # The index narrates a move under the old tier; the rule runs records → index.
    _rewrite(broken / "docs" / "backlog" / "PRIORITY.md", "**2**.", "**2**. (**3** moved to tier 1.)")
    assert check_priority(load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md") == []


def test_no_live_surface_names_the_old_path(broken):
    (broken / "saffron" / "example.py").write_text("# see docs/BACKLOG.md item 1\n")
    [v] = check_no_old_path(broken)
    assert v.path.name == "example.py"


def test_a_done_spec_may_still_name_the_old_path(broken):
    spec = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    _rewrite(spec, "backlog item 1.", "`docs/BACKLOG.md` item 1.")
    assert check_no_old_path(broken) == []
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/records/test_records_check.py -q`
Expected: `ImportError: cannot import name 'check_all'`.

- [ ] **Step 3: Write the checks**

```python
# append to records/check.py
OLD_PATH = "docs/BACKLOG.md"
LIVE_SURFACES = ("saffron", "tests", ".saffron/specs", "CLAUDE.md", "DESIGN.md", "README.md", "docs/agents")

_TIER_HEADING = re.compile(r"^### Tier (\d)\b")
_STRUCK = re.compile(r"~~\*\*(\d+)\*\*~~")
_BOLD = re.compile(r"(?<!~)\*\*(\d+)\*\*(?!~)")


def check_done_specs_are_done(records: list[Record], root: Path) -> list[Violation]:
    specs = spec_files(root)
    out: list[Violation] = []
    for r in records:
        if r.model.status != "done":
            continue
        for spec in getattr(r.model, "specs", []):
            path = specs.get(spec)
            if path is not None and path.parent.name != "done":
                out.append(Violation(r.path, "specs", f"item is done but {spec} is still in the queue"))
    return out


def check_specs_name_their_items(records: list[Record], root: Path) -> list[Violation]:
    """The inverse link: a spec whose `## Context` cites an item is listed by it,
    and a spec in `done/` leaves no item open."""
    by_id = _ids(records)
    out: list[Violation] = []
    for spec_id, path in spec_files(root).items():
        context = _context_section(path.read_text())
        for n in cited_items(context):
            item = by_id.get(n)
            if item is None:
                continue  # check_item_citations reports it
            if spec_id not in getattr(item.model, "specs", []):
                out.append(Violation(item.path, "specs", f"{spec_id} cites this item and is not listed"))
            if path.parent.name == "done" and item.model.status == "open":
                out.append(Violation(item.path, "status", f"open, but {spec_id} is in done/"))
    return out


def _context_section(spec_text: str) -> str:
    body = spec_text.split("\n---\n", 2)[-1]
    from records.load import split_sections

    return split_sections(body).get("Context", "")


def check_priority(records: list[Record], priority_md: Path) -> list[Violation]:
    by_id = _ids(records)
    out: list[Violation] = []
    named_under: dict[int, set[int]] = {}
    tier: int | None = None
    for line in priority_md.read_text().splitlines():
        if heading := _TIER_HEADING.match(line):
            tier = int(heading.group(1))
            continue
        for n in map(int, _STRUCK.findall(line)):
            if n not in by_id:
                out.append(Violation(priority_md, "index", f"strikes item {n}, which does not exist"))
            elif by_id[n].model.status not in ("done", "superseded"):
                out.append(Violation(priority_md, "index", f"strikes item {n}, which is {by_id[n].model.status}"))
        for n in map(int, _BOLD.findall(line)):
            if n not in by_id:
                out.append(Violation(priority_md, "index", f"names item {n}, which does not exist"))
        if tier is not None:
            for n in map(int, _NUM.findall(" ".join(_STRUCK.findall(line) + _BOLD.findall(line)))):
                named_under.setdefault(n, set()).add(tier)
    for n, r in by_id.items():
        t = getattr(r.model, "tier", None)
        if t is not None and t not in named_under.get(n, set()):
            out.append(Violation(r.path, "tier", f"tier {t}, but PRIORITY.md does not name it under tier {t}"))
    return out


def check_no_old_path(root: Path) -> list[Violation]:
    out: list[Violation] = []
    for name in LIVE_SURFACES:
        path = root / name
        files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()] if path.is_dir() else []
        for file in files:
            if "specs" in file.parts and "done" in file.parts:
                continue
            if file.suffix in _SUFFIXES and OLD_PATH in file.read_text():
                out.append(Violation(file, "path", f"names {OLD_PATH}, which no longer exists"))
    return sorted(out, key=lambda v: v.path)


def check_all(root: Path, sections: set[str]) -> list[Violation]:
    from records.kinds import KINDS
    from records.load import load

    records = load(KINDS["backlog"], root)
    priority = root / KINDS["backlog"].directory / "PRIORITY.md"
    return (
        check_ids(records)
        + check_links(records)
        + check_specs_resolve(records, root)
        + check_cites_resolve(records, sections)
        + check_item_citations(root, {int(r.model.id) for r in records})
        + check_done_specs_are_done(records, root)
        + check_specs_name_their_items(records, root)
        + check_priority(records, priority)
        + check_no_old_path(root)
    )
```

Move the two function-local imports to the top of the module; they are there only to keep the snippet self-contained. `records.load` importing nothing from `records.check` means no cycle.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/records/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Run: `make check` → green.

```bash
git add records/check.py tests/records/test_records_check.py
git commit -m "feat(records): an item could say done while its spec sat in the queue and the index said otherwise, so check the workflow"
```

---

### Task 6: The live integrity test, and PR 1

**Files:**
- Create: `tests/records/test_records_integrity.py`
- Modify: `tests/test_citations.py` (nothing yet — read only, to confirm `addresses` is importable as `tests.test_citations.addresses`)

**Interfaces:**
- Consumes: `records.check.check_all`, `tests.test_citations.addresses(document: Path) -> tuple[set[str], set[str]]`.

- [ ] **Step 1: Write the test**

```python
# tests/records/test_records_integrity.py
"""The one live check: the records hold. PR 1 points it at the good fixture;
the migration (PR 2) points it at the repository root and never back."""

from pathlib import Path

from records.check import check_all
from tests.test_citations import addresses

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
ROOT = FIXTURE  # PR 2 flips this to REPO


def test_the_backlog_records_hold():
    sections, _ = addresses(ROOT / "DESIGN.md")
    violations = check_all(ROOT, sections)
    assert violations == [], "\n".join(str(v) for v in violations)
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/records/test_records_integrity.py -q`
Expected: passes. If `from tests.test_citations import addresses` fails, `tests/__init__.py` exists so the package import should work from the repo root; check `pytest --import-mode` is the default and that the test is being run from `ROOT`.

- [ ] **Step 3: Full check and PR 1**

Run: `make check`
Expected: green, and `uv run ast-grep scan -c .saffron/sgconfig.yml` reports nothing new under `records/`.

```bash
git add tests/records/test_records_integrity.py
git commit -m "test(records): one live test asserts the records hold, pointed at a fixture until the migration lands"
```

Open PR 1 from `joel/backlog-as-records` (draft, per `CLAUDE.md`'s PACKAGE convention). Body: the spec's "Approach" and "The loader and the command" sections, and the note that `docs/backlog/` does not exist yet — `make backlog` exits 2 until PR 2. End with the attribution lines from the session's system reminder.

---

## PR 2 — the migration

Stacked on PR 1 with `gh stack` (invoke the `gh-stack` skill for the branch and submit mechanics). Branch name: `joel/backlog-migration`.

### Task 7: Passes 1 and 2 — split and extract

**Files:**
- Create: `docs/evidence/scripts/2026-09-14-split-backlog.py`, `docs/backlog/*.md`, `docs/backlog/README.md`, `docs/backlog/PRIORITY.md`
- Read: `docs/BACKLOG.md` (not yet deleted)

**Interfaces:**
- Consumes: nothing from `records/` — the script must run before the records are valid, so it writes YAML by hand and does not call `load`.
- Produces: 122 files whose frontmatter has `id`, `title`, `status`, `tier`, `closed`, `specs`, `prs`, `commits`, `cites`, `related`, and a body `## Problem` holding the item text verbatim.

- [ ] **Step 1: Write the script**

```python
# docs/evidence/scripts/2026-09-14-split-backlog.py
"""Passes 1 and 2 of the backlog migration (spec: 2026-09-14-backlog-as-records-design.md).

Pass 1 splits `docs/BACKLOG.md` into one file per item with the item text
verbatim under `## Problem`. Pass 2 fills the frontmatter from what a regex
can read without judgement; `specs`, `prs`, `commits` and `related` are
candidates the agent pass confirms or prunes. Run once, from the repo root:

    uv run python docs/evidence/scripts/2026-09-14-split-backlog.py
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs" / "BACKLOG.md"
OUT = ROOT / "docs" / "backlog"

ITEM = re.compile(r"^## (\d+)\. (.+)$")
PRIORITY = "## Priority — the order to work in"
NOT_HERE = "## What is *not* here, deliberately"

SECTION = re.compile(r"§(\d+(?:\.\d+)*[a-z]?)")
SPEC = re.compile(r"\bSA-\d{4}\b")
PR = re.compile(r"(?:PR|pull request) #(\d+)", re.IGNORECASE)
COMMIT = re.compile(r"`([0-9a-f]{7,10})`")
ITEMS = re.compile(r"(?i)\b(?:backlog\s+)?items?\s+((?:\*{0,2}\d{1,3}\*{0,2}(?:\s*(?:,|and|–|—|-)\s*)?)+)")
DONE_DATE = re.compile(r"^\*\*Done, (20\d\d-\d\d-\d\d)", re.MULTILINE)
STATUS_LINE = re.compile(r"^\*\*Status:\*\* (.+)$", re.MULTILINE)
TIER_HEADING = re.compile(r"^### Tier (\d)\b")
STRUCK = re.compile(r"~~\*\*(\d+)\*\*~~")
BOLD = re.compile(r"\*\*(\d+)\*\*")


def slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-").split("-")
    out = ""
    for w in words:
        if len(out) + len(w) + 1 > 70:
            break
        out = f"{out}-{w}" if out else w
    return out


def split(text: str) -> tuple[str, str, list[tuple[int, str, str]], str]:
    lines = text.splitlines()
    p = next(i for i, l in enumerate(lines) if l == PRIORITY)
    first = next(i for i, l in enumerate(lines) if ITEM.match(l))
    end = next(i for i, l in enumerate(lines) if l == NOT_HERE)
    preamble = "\n".join(lines[:p]).rstrip()
    priority = "\n".join(lines[p:first]).rstrip()
    items: list[tuple[int, str, str]] = []
    current: tuple[int, str] | None = None
    body: list[str] = []

    def flush() -> None:
        if current is not None:
            text = "\n".join(body).strip()
            text = re.sub(r"\n---\s*$", "", text).rstrip()  # the `---` rule between items
            items.append((current[0], current[1], text))

    for line in lines[first:end]:
        if m := ITEM.match(line):
            flush()
            current, body = (int(m.group(1)), m.group(2)), []
        else:
            body.append(line)
    flush()
    closing = "\n".join(lines[end:]).rstrip()
    return preamble, priority, items, closing


def tiers(priority: str) -> tuple[dict[int, int], set[int]]:
    """id → lowest tier it is named under; ids struck through anywhere."""
    tier_of: dict[int, int] = {}
    struck: set[int] = set()
    tier: int | None = None
    for line in priority.splitlines():
        if m := TIER_HEADING.match(line):
            tier = int(m.group(1))
            continue
        struck.update(map(int, STRUCK.findall(line)))
        if tier is not None:
            for n in map(int, BOLD.findall(line)):
                tier_of[n] = min(tier, tier_of.get(n, 9))
    return tier_of, struck


def status_of(body: str, struck: bool) -> tuple[str, str | None]:
    dates = DONE_DATE.findall(body)
    line = STATUS_LINE.search(body)
    head = (line.group(1).lower() if line else "")
    if "partly" in head or "half" in head or "partial" in head:
        return "partial", None
    if "done" in head or "merged" in head or dates or struck:
        return "done", (dates[-1] if dates else None)
    return "open", None


def frontmatter(n: int, title: str, body: str, tier: int | None, struck: bool) -> dict:
    status, closed = status_of(body, struck)
    related = sorted({int(x) for m in ITEMS.finditer(body) for x in re.findall(r"\d+", m.group(1))} - {n})
    fm: dict = {"id": n, "title": title, "status": status, "tier": tier}
    if closed:
        fm["closed"] = closed
    fm["specs"] = sorted(set(SPEC.findall(body)))
    fm["prs"] = sorted({int(x) for x in PR.findall(body)})
    fm["commits"] = sorted(set(COMMIT.findall(body)))
    fm["cites"] = sorted({f"§{s}" for s in SECTION.findall(body)}, key=lambda s: [int(p) if p.isdigit() else p for p in re.findall(r"\d+|[a-z]", s)])
    fm["related"] = related
    return fm


def main() -> None:
    preamble, priority, items, closing = split(SOURCE.read_text())
    OUT.mkdir(exist_ok=True)
    tier_of, struck = tiers(priority)
    for n, title, body in items:
        fm = frontmatter(n, title, body, tier_of.get(n), n in struck)
        head = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=10_000).rstrip()
        (OUT / f"{n:03d}-{slug(title)}.md").write_text(f"---\n{head}\n---\n\n## Problem\n\n{body}\n")
    (OUT / "README.md").write_text(preamble.replace("# Backlog —", "# Backlog —", 1) + "\n\n" + closing + "\n")
    (OUT / "PRIORITY.md").write_text("# " + priority.removeprefix("## ") + "\n")
    print(f"{len(items)} items → {OUT}")


if __name__ == "__main__":
    main()
```

Note: `closed` is only set when a `**Done, YYYY-MM-DD**` line exists. Items the index strikes but that carry no date get `status: done` with no `closed`, which the model refuses — deliberately: the agent pass must supply the date from the item's own prose, and a file that will not load is a file that cannot be forgotten.

- [ ] **Step 2: Run it and look**

Run:
```bash
uv run python docs/evidence/scripts/2026-09-14-split-backlog.py
ls docs/backlog | wc -l          # expect 124 (122 items + README + PRIORITY)
uv run python -m records list backlog 2>&1 | head -5
```
Expected: 124 files. `list` will exit 2 on the first file that fails validation (a struck item with no `closed`, or one whose body has `**Done looks like**` inline rather than as a heading) — that is the worklist for Task 8, not a defect here. Record how many files load: temporarily run

```bash
for f in docs/backlog/[0-9]*.md; do uv run python -c "
import sys; from pathlib import Path
from records.kinds import KINDS; from records.load import parse, RecordError
try: parse(Path(sys.argv[1]).read_text(), KINDS['backlog'], Path(sys.argv[1]))
except RecordError as e: print(e)
" "$f"; done | wc -l
```

and note the count in the commit body.

- [ ] **Step 3: Spot-check three items**

Open `docs/backlog/118-*.md`, `docs/backlog/001-*.md`, `docs/backlog/058-*.md`. Confirm: heading gone, text otherwise byte-identical to the source (`diff <(sed -n '/^## 118\. /,/^---$/p' docs/BACKLOG.md | sed '1d;$d') <(sed '1,/^## Problem$/d' docs/backlog/118-*.md)` should show only blank-line differences at the ends). Confirm `PRIORITY.md` starts with `# Priority — the order to work in` and its `### Tier` headings are intact.

- [ ] **Step 4: Commit passes 1 and 2**

`docs/BACKLOG.md` stays in place until Task 9 so the diff reviewer can compare.

```bash
git add docs/evidence/scripts/2026-09-14-split-backlog.py docs/backlog/
git commit -m "docs(backlog): split the one file into one record per item, with the fields a regex can read"
```

---

### Task 8: Pass 3 — the agent pass

**Files:**
- Modify: `docs/backlog/NNN-*.md` (122 files), frontmatter and section boundaries only

**Interfaces:**
- Consumes: the files from Task 7 and the loader's rules (`records/load.py`, `records/kinds.py`).
- Produces: every file loads (`uv run python -m records list backlog` exits 0), plus a residue list for the operator.

- [ ] **Step 1: Dispatch one subagent per batch of ~12 items, in parallel**

Use the Agent tool (general-purpose). Ten batches: items 1–12, 13–24, …, 109–122. The brief, verbatim, with `{RANGE}` filled in:

> You are migrating backlog items {RANGE} in `docs/backlog/` of this repository. Each file has YAML frontmatter and a single `## Problem` section holding the original item text verbatim. Your job is **moves and frontmatter only — never reword, delete or add prose**. A reviewer will diff your result against the original and must see nothing lost.
>
> For each file in your range:
>
> 1. **Split the body into three sections, in this order: `## Problem`, `## Done looks like`, `## Record`.** Cut at boundaries the prose already has:
>    - A paragraph beginning `**Done looks like**` or `**Done looks like:**`, or a `### Done looks like` heading, becomes the `## Done looks like` section (drop the bold lead / `###` and keep the text). If the item has no such paragraph and its status is `open` or `partial`, write `## Done looks like` with the one sentence the prose already states as the exit criterion, quoted from the item — if there is none, leave the section empty and put the item on your residue list.
>    - Every dated paragraph (`**Done, 2026-…**`, `**Status:** …` when it names a date or a PR, `Stale by the evening…`, `**Re-measured …**`) moves under `## Record`, in chronological order, oldest first. Keep `### ` subheadings inside whichever `##` section they belong to.
>    - Everything else stays under `## Problem`.
> 2. **Set `status`.** `done` when the item says it is done and names what closed it; `partial` when it says half/part shipped; `superseded` when it says another item replaced it (set `superseded_by`); `wontfix` when it says it will not be done; otherwise `open`. Trust a `**Status:**` line over an index strikethrough.
> 3. **Set `closed`** (YYYY-MM-DD) for `done`/`superseded`/`wontfix`, from the item's own dated paragraph. If no date exists in the prose, use the date of the PR or commit it names if the prose gives one; else put the item on your residue list and leave it `open`.
> 4. **Prune the candidate lists.** `specs`, `prs`, `commits`, `related` were filled from every mention. Keep only true links: a spec that *implements* this item, a PR or commit that *closed or advanced* it, an item it is genuinely related to (a cause, a twin, a successor). Drop a spec mentioned as an example, a PR mentioned as evidence of something else, "not the same defect as item 13". `cites` stays as generated.
> 5. **Set `by_hand: true`** when the item says it must be done by hand / cannot go through a cell.
> 6. **Set `filed`** only when the item states the date it was found or filed.
> 7. **Verify** with `uv run python -m records show N` — it must print the file with exit 0. If it exits 2, the error names the field; fix the frontmatter, not the prose.
>
> Report: a list of files you changed, and a **residue list** — each item you could not classify with confidence, with one line saying why (missing date, ambiguous status, a link you were unsure about). Do not guess on the residue; leave it `open` and say so.

- [ ] **Step 2: Collect the residue lists and bring them to the operator**

Concatenate the ten residue lists. Expected: 10–20 items. Present them to the user as a table (id, title, question) and apply their answers to the frontmatter.

- [ ] **Step 3: Verify every file loads and the prose is intact**

Run:
```bash
uv run python -m records list backlog | wc -l      # 122
uv run python -m records list backlog --status open
uv run python -m records list backlog --status partial
```

Then the "nothing lost" check — for every item, the sorted multiset of non-blank lines in the new file's body (minus the three `## ` headings and minus bold-lead markers) equals that of the original item text:

```bash
uv run python - <<'EOF'
import re, subprocess
from pathlib import Path
src = Path("docs/BACKLOG.md").read_text().splitlines()
items, cur = {}, None
for l in src:
    if m := re.match(r"^## (\d+)\. ", l): cur = int(m.group(1)); items[cur] = []
    elif cur and not l.startswith("## What is *not* here"): items[cur].append(l)
def norm(lines):
    out = []
    for l in lines:
        l = re.sub(r"^\*\*Done looks like:?\*\*:?\s*", "", l)
        l = re.sub(r"^### Done looks like$", "", l)
        l = l.strip()
        if l and l != "---" and not l.startswith("## "): out.append(l)
    return sorted(out)
bad = 0
for p in sorted(Path("docs/backlog").glob("[0-9]*.md")):
    n = int(p.name[:3]); body = p.read_text().split("\n---\n", 1)[1].splitlines()
    if norm(body) != norm(items[n]): bad += 1; print("DIFFERS", p.name)
print("differing:", bad)
EOF
```
Expected: `differing: 0`. Any difference is a reworded or dropped line — restore it from `docs/BACKLOG.md`.

- [ ] **Step 4: Commit**

```bash
git add docs/backlog/
git commit -m "docs(backlog): every item now says what it is, what closed it and what is left, in fields"
```

---

### Task 9: The citation sweep, the deletion, and the live test

**Files:**
- Delete: `docs/BACKLOG.md`
- Modify: every live surface naming `docs/BACKLOG.md` — `saffron/` (17 files), `tests/` (15 files, incl. `tests/test_scheduler.py:1088`'s fake path and `tests/test_citations.py:93`'s comment), `.saffron/specs/*.md` (open specs only), `DESIGN.md` (8 mentions), `README.md:175`, `CLAUDE.md:23`, `docs/agents/issue-tracker.md` (lines 52, 81, 92, 120), `docs/agents/triage-labels.md:13`
- Modify: `tests/records/test_records_integrity.py` (`ROOT = REPO`)

- [ ] **Step 1: Sweep the citation form**

The three shapes and their replacements, applied with `sed -i ''` (macOS) over the live surfaces only — not `.saffron/specs/done/`, not `docs/evidence/`:

| from | to |
|---|---|
| `` `docs/BACKLOG.md` item `` | `backlog item` |
| `` `docs/BACKLOG.md` items `` | `backlog items` |
| `docs/BACKLOG.md item` (unbackticked, in `.py` comments) | `backlog item` |
| `docs/BACKLOG.md items` | `backlog items` |

```bash
files=$(grep -rl 'docs/BACKLOG\.md' saffron tests .saffron/specs/*.md DESIGN.md README.md CLAUDE.md docs/agents)
for f in $files; do
  sed -i '' -e 's/`docs\/BACKLOG\.md` items/backlog items/g' \
            -e 's/`docs\/BACKLOG\.md` item/backlog item/g' \
            -e 's/docs\/BACKLOG\.md items/backlog items/g' \
            -e 's/docs\/BACKLOG\.md item/backlog item/g' "$f"
done
grep -rn 'BACKLOG\.md' saffron tests .saffron/specs/*.md DESIGN.md README.md CLAUDE.md docs/agents
```

What the last `grep` still prints is the bare-pointer set — handle each by hand:
- `CLAUDE.md:23`: replace the sentence with: `` `docs/backlog/` is what v0.5 left undone, one record per item; `make backlog` lists them and `uv run python -m records show 118` prints one. `docs/backlog/PRIORITY.md` is the order to work in. Read it before picking up work; `docs/evidence/` holds the primary records. ``
- `README.md:175`: same sentence, with the link `[docs/backlog/](docs/backlog/)`.
- `docs/agents/issue-tracker.md:120` and `triage-labels.md:13`: `docs/backlog/`.
- `tests/test_scheduler.py:1088`: the string is a fake spec path in a test; change it to `"docs/README.md"` (any path that is not the old one).
- `tests/test_citations.py:93`: the comment cites the file as an example of plural forms; change to `` (`docs/backlog/`) ``.
- `DESIGN.md`: read each of the 8 in context; a bare pointer becomes `docs/backlog/`, an item citation was already swept.
- `tests/test_retired_vocabulary_hook.py`: its docstring names the old path; `backlog item 57`.

- [ ] **Step 2: Delete the monolith and flip the live test**

```bash
git rm docs/BACKLOG.md
```

In `tests/records/test_records_integrity.py`: `ROOT = REPO` and delete the `FIXTURE` line and the comment about PR 2.

- [ ] **Step 3: Run the live test and work the violations down to zero**

Run: `uv run pytest tests/records/test_records_integrity.py -q`
Expected on first run: a list of violations. Each names a file and a field. The likely classes, and what to do:
- `cites: §X is not a DESIGN.md section` — the body cites a section that was renamed; fix the frontmatter entry to the real section (the body prose stays).
- `item: cites backlog item N, which does not exist` — either a false positive on "item N" in ordinary prose (reword *that* sentence, e.g. "entry N"), or a real dangling citation (fix the number).
- `specs: SA-NNNN cites this item and is not listed` — add the spec to the item's `specs:`.
- `status: open, but SA-NNNN is in done/` — set `partial` or `done` per the item's prose; if the prose is silent, ask the operator.
- `tier: N, but PRIORITY.md does not name it under tier N` — the min-tier heuristic chose wrong; set the tier the index actually argues for.
- `index: strikes item N, which is open` — the item's own prose says open and the index says done: ask the operator which is true; do not guess.
- `path: names docs/BACKLOG.md` — a live surface the sweep missed.

Re-run until the test passes, then the whole suite:

Run: `make check`
Expected: green. `tests/test_citations.py` scans `docs/backlog/*.md` too (its `SKIP_DIRS` does not exclude `docs`), so any `§` citation in a body that was already dangling before will now surface — fix the citation, and note in the PR body that it was pre-existing.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs(backlog): the one file is gone, every live surface cites items by number, and the integrity test runs against the real records"
```

---

### Task 10: Finish

- [ ] **Step 1: `make backlog` and the three questions**

Run:
```bash
make backlog | head
uv run python -m records list backlog --status open --tier 1
uv run python -m records show 118 --section "Done looks like"
uv run python -m records show SA-0087
```
Expected: each answers in one screen. Paste the tier-1 open list into the PR body — it is the comprehension fix, demonstrated.

- [ ] **Step 2: Memory and follow-ons**

Append to `docs/backlog/README.md` a short "How to add an item" paragraph: copy the frontmatter shape from any open item; the next id is the highest + 1; `uv run pytest tests/records -q` before committing; a spec that cites an item goes in that item's `specs:` in the same commit.

- [ ] **Step 3: Submit PR 2 on the stack**

Invoke the `gh-stack` skill to submit `joel/backlog-migration` stacked on `joel/backlog-as-records`. Draft. PR body: the spec's "Migration" section, the count of items by status, the residue list and how each was resolved, and the pre-existing dangling `§` citations if any surfaced. End with the attribution lines.

---

## Self-review

**Spec coverage.** Record location, frontmatter, body, citation form → Tasks 1, 2, 7, 9. Package layout, `list`/`show`/`grep`, `make backlog` → Task 3. Every validation bullet → Tasks 4–5 (ids, specs, cites, related/superseded, item citations, closed/what-closed-it and section rules are in the model/loader from Tasks 1–2, done⇒specs done, spec↔item inverse, PRIORITY.md rules, no old path); "not checked: PR merged" → nothing, correctly. Migration passes 1–3, the sweep, deletion, `CLAUDE.md` → Tasks 7–9. Two-PR stack → Task 6 and Task 10. Follow-ons need no task.

**Placeholders.** None: every step has its code, command and expected result. The one open-ended step is Task 8's agent pass, which is open-ended by design and bounded by its brief and by Task 8 Step 3's "nothing lost" check.

**Type consistency.** `Record(model, path, body, sections)` is used identically in Tasks 2–5. `Kind.model: type[Identified]` after Task 2's fix, and `check.py` reads `r.model.id`, `.status`, `.tier`, `.specs`, `.related`, `.superseded_by` through `getattr` where a future kind may lack them and directly where every kind has them (`id`, `status`) — `status` is not on `Identified`; either add `status: str` to `Identified` or use `getattr(r.model, "status", None)` in `check_links`, `check_priority` and `check_done_specs_are_done`. Add it to `Identified`: every kind this design names has a status. `check_all(root, sections)` signature matches Task 6's call. `spec_files` is defined in Task 4 and used in Task 5.
