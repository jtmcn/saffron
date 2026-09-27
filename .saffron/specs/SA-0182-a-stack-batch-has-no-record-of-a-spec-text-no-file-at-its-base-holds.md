---
id: SA-0182
title: A stack batch has no record of a spec text that no file at its base holds
type: feature
priority: 1
depends_on: [SA-0156]
touches:
  - saffron/ledger.py
  - tests/test_ledger_fold_task.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/events.py
  - saffron/projection.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_task.py
  - tests/test_batch.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_session.py
  - tests/test_record.py
budget_usd: 22
max_attempts: 3
max_turns: 130
estimated_lines: 320
pending_symbols:
  - saffron/ledger.py::record_spec_text
  - saffron/ledger.py::spec_texts
acceptance:
  - claim: >-
      `Ledger.record_spec_text(task_id, *, origin, spec_id, path, text)`
      appends one `spec_text` fact on the task and returns its `n`, 1 more
      than the rows that task already holds. The payload is exactly `n`,
      `origin`, `spec_id`, `path`, `text` and `spec_sha`, the SHA-256 of
      the text's UTF-8 bytes. `Ledger.spec_text(task_id)` returns the
      task's row with the highest `n`, all seven columns, or `None` for a
      task that holds none. `Ledger.spec_texts(task_id)` returns every
      row the task holds, oldest first, or an empty list. All three count
      and read by the task, never by its spec id. Each method raises
      `ValueError` for a task id that names no task. `record_spec_text`
      raises `ValueError`, and writes no row and no fact, for an origin
      outside `SPEC_TEXT_ORIGINS`, a `spec_id` the task does not carry, or
      a path the notes' rule refuses for its origin. The witness drives
      both origins and three outside them, a second spec id, a second task
      of one spec id, and each path in the notes.
    witness: tests/test_ledger_fold_task.py::test_a_spec_text_is_numbered_on_its_task_and_read_back_latest
  - claim: >-
      Folding the record rebuilds the `spec_texts` rows as written. A fold
      into a fresh ledger whose task ids differ gives the same rows. A fold
      into the ledger that wrote them leaves them as they were. `fold_task`
      with a key and no facts removes that task's rows and no other, a
      second task of the same spec id included. Each row's `n` is the
      fact's own.
    witness: tests/test_ledger_fold_task.py::test_the_spec_texts_fold_back_from_the_record_alone
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §4.2
and §4.2.1. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that a stack batch runs spec text that is not at `base_sha`. That
text is a spec review's revision or a follow-up spec, and nothing else.
Section 3 of `docs/superpowers/specs/2026-09-23-stack-batch-design.md`
holds each one as a record fact with its text and `spec_sha`, and the cell
runs that text. The finishing layer commits the files. §4.2.1 already
names this exception (`DESIGN.md:386`).

**This is one of two specs.** They were one, `SA-0150`. A pricing of the
queue on 2026-09-27 put it at the `feature` ceiling of 3000 changed tokens. `saffron/ledger.py` is in `elevate_on`, so `size` would block its
plan. This spec holds the text in the ledger and the record. `SA-0150`
then runs it in `run_task`, behind gate 0 again, at `standard`.

**What the tree base holds.** This spec's tree base is `SA-0156`'s head.
Every line number below was read at `f492629e`, `SA-0168`'s head. The
specs between, `SA-0181`, `SA-0169`, `SA-0175` and `SA-0156`, forbid
`saffron/ledger.py`, so its lines hold at the tree base. Two names come
from the chain below `f492629e`.

- From `SA-0155`: the `spec_reviews` table, keyed on `task_key` and `n`,
  and `record_spec_review` (`saffron/ledger.py:1356`). It numbers a fact 1
  more than the task's rows and applies it through `_commit_and_append`.
  `_drop_task_rows` deletes its rows by key (`:485`).
- By hand, before this spec: the `spec_text` fact kind in
  `ontology/factory.ttl`, its render in `CONTEXT.md`, and `"spec_text"` in
  `saffron/record/contract.py`'s `KINDS` (`saffron/record/contract.py:42`).

**What `spec_sha` means at the base.** `load_spec` hashes a file's raw
bytes with SHA-256 (`saffron/intake.py:308-319`). A recorded text's
`spec_sha` is the same hash over the text's UTF-8 bytes. Those are the
bytes the finish writes, so the committed file hashes to it.

**How a fact reaches the record.** Each write method builds one fact with
`_build_fact` (`saffron/ledger.py:435`) and applies it through
`_commit_and_append` (`:462-467`). `fold_task` drops a task's rows and
applies its facts again (`:469-475`). `_drop_task_rows` deletes the rows
keyed on the record key first, then the task's own (`:477-500`). `_apply`
resolves a task by its record key before most kinds (`:583-612`).

## Problem

Build two things.

1. **The table and the fact.** Add `spec_texts` to `SCHEMA` in
   `saffron/ledger.py`, with no reference to another table.

   | column | type |
   |---|---|
   | `task_key` | `TEXT NOT NULL` |
   | `n` | `INTEGER NOT NULL` |
   | `origin` | `TEXT NOT NULL` |
   | `spec_id` | `TEXT NOT NULL` |
   | `path` | `TEXT NOT NULL` |
   | `text` | `TEXT NOT NULL` |
   | `spec_sha` | `TEXT NOT NULL` |

   The primary key is `(task_key, n)`. Add `SPEC_TEXT_ORIGINS`, the tuple
   `("revision", "follow_up")`. `_apply` places a `spec_text` fact as one
   row, every value from the fact and the key from `fact.task_key`.
   `_drop_task_rows` deletes the task's rows by its key, beside the four
   deletes by key it runs first.
2. **The three methods.** Add `Ledger.record_spec_text(task_id, *,
   origin, spec_id, path, text) -> int`, `Ledger.spec_text(task_id)` and
   `Ledger.spec_texts(task_id)`, as criterion 1 states. A follow-up's
   path must match
   `re.fullmatch(rf"\.saffron/specs/{re.escape(spec_id)}-[A-Za-z0-9._-]+\.md", path)`,
   since the host names that file. The slug is required, because
   `projection` and `session._spec_path` find a spec only as `<id>-*.md`
   (`saffron/projection.py:144`, `saffron/cell/session.py:443-468`). A
   revision's path is the queued spec's own file, and nothing ties a spec
   file's name to its id. So a revision's path takes any one file name in
   the spec directory:
   `re.fullmatch(r"\.saffron/specs/[A-Za-z0-9][A-Za-z0-9._-]*\.md", path)`.
   Check every argument before `_build_fact`, so a refused call writes
   nothing.

Two docstrings become false. The module docstring counts the kinds that
fold back, fifteen, and the tables outside §4.1's count, five
(`saffron/ledger.py:6`, `:12-15`). Each count gains one.
`_drop_task_rows`'s docstring names the four tables it deletes by key
first (`:480-481`), and gains the fifth.

**The seam `SA-0150` builds on.** `SA-0150` calls these, and its
witnesses pin their shape.

- `SPEC_TEXT_ORIGINS` is the tuple `("revision", "follow_up")`.
- `record_spec_text(task_id: int, *, origin: str, spec_id: str, path:
  str, text: str) -> int` returns the new row's `n`.
- `spec_text(task_id: int) -> sqlite3.Row | None` returns the row with the
  highest `n`. Its keys are `task_key`, `n`, `origin`, `spec_id`, `path`,
  `text` and `spec_sha`.
- `spec_texts(task_id: int) -> list[sqlite3.Row]` returns the same seven
  keys per row, in rising `n`.
- Each raises `ValueError` for a task id that names no task. `SA-0150`
  reads a text only for a task the ledger holds.

## Out of scope

- **Running the text.** `SA-0150` runs a task's latest text in
  `run_task`, and runs gate 0 on it first.
- **Recording a revision, and writing a follow-up.** They are `SA-0164`'s
  and `SA-0161`'s. No code in `saffron/` calls `record_spec_text` until
  `SA-0164`, and none calls `spec_texts` until `SA-0150`. So both are
  `pending_symbols`, and the `dead` gate defers each while this spec is
  open (`.saffron/gates/dead.py:4-6`, `:113-127`). A prototype's `dead`
  gate reported `spec_texts` and deferred `record_spec_text`.
- **`saffron/record/fold.py:1-3`**, which lists what the fold rebuilds and
  becomes incomplete. That file is forbidden here, so the operator files
  it.

## Notes for the agent

**Every criterion is new code.** No text at the tree base places a
`spec_text` fact or reads a recorded spec. So each criterion declares a
witness and no mutant, and `witness` reports `skip` for each.

**Import `SPEC_TEXT_ORIGINS` inside the test body.** The tree base lacks
it. A module-scope import makes the reverted run a collection error,
which `revert` reads as `skip`. Each witness then fails with the source
reverted, on a missing method.

**Criterion 1's witness** opens a `Ledger` with a `MemoryRecord` and makes
three tasks with `_minimal` (`tests/test_ledger_fold_task.py:134`): `SY-1`,
`SY-2` and `SY-3`. The text `first` is `"---\nid: SY-1\n---\nfirst é\n"`,
and `second` is `"second\n"`. The fields default to origin `revision` and
path `.saffron/specs/<id>-a.md`.

- `SY-3` gives `None` and `spec_texts` an empty list, before any write.
- It records `first` on `SY-1` and gets 1. `spec_text` then has `n` 1.
- It records `b` on `SY-2` with origin `follow_up` and path
  `.saffron/specs/SY-2-b.md`, and gets 1.
- It records `second` on `SY-1` and gets 2.
- It makes a second `SY-1` task with `_minimal`. That task gives `None`,
  and recording `again` on it gives 1.
- It records `o` on `SY-3` with origin `revision` and path
  `.saffron/specs/other.md`, and gets 1.
- `dict(spec_text(...))` of the first `SY-1` task is the key, 2,
  `revision`, `SY-1`, the path, `second` and `second`'s hash.
- `spec_texts` gives that task's texts as `first` then `second`, and the
  second `SY-1` task's as `again` alone.
- That task's `spec_text` facts carry exactly the two payloads, each hash
  computed with `hashlib.sha256(t.encode("utf-8"))`.

Then each call below raises `ValueError`, and the rows and the record's
fact count are unchanged: origins `Revision`, `follow-up` and the empty
string, spec id `SY-2` on `SY-1`'s task, task 999 for all three methods,
and these paths.

| path | origin | wrong because |
|---|---|---|
| `docs/SY-1-a.md` | both | outside the spec directory |
| `.saffron/specs/done/SY-1-a.md` | both | the retired directory |
| `.saffron/specs/../SY-1-a.md` | both | climbs out |
| `/r/.saffron/specs/SY-1-a.md` | both | absolute |
| `./.saffron/specs/SY-1-a.md` | both | not the plain spelling |
| `.saffron/specs/SY-1-a.txt` | both | not Markdown |
| `.saffron/specs/SY-1-a/b.md` | both | a subdirectory |
| `.saffron/specs/SY-1-a.md.bak` | both | ends past `.md` |
| `.saffron/specs/SY-10-a.md` | `follow_up` | another id sharing the prefix |
| `.saffron/specs/other.md` | `follow_up` | not named for its id |
| `.saffron/specs/SY-1.md` | `follow_up` | no slug |

These fail it:

- a count across the ledger, which gives `SY-2` 2
- the follow-up slug left optional, which admits `SY-1.md`
- `spec_texts` newest first, or keyed on the spec id
- a count per spec id, which gives the second `SY-1` task 3
- a read by spec id, which gives the second `SY-1` task a row
- the lowest `n` read back, which gives 1 after the second write
- `spec_text` that returns `None` for a missing task
- no origin check, or no spec id check
- the origin checked after the write, which leaves a fact
- a path checked by its prefix, which admits `done/` and `..`
- a path checked by its parent and `.md`, which admits `other.md` for a
  follow-up
- either name pattern ending `.*`, which admits the subdirectory or
  another id
- a revision held to the follow-up pattern, which refuses `other.md`
- a follow-up given the revision pattern, which admits `SY-10-a.md`
- a hash over the stripped text, or over Latin-1 bytes

**Criterion 2's witness** follows
`test_every_task_fact_kind_folds_back_to_the_rows_its_write_made`
(`tests/test_ledger_fold_task.py:208`). It reads the rows through a
`sqlite3` connection of its own, ordered by `task_key` and `n`. On a
source ledger with a `MemoryRecord`, it makes `SY-1` and `SY-2` with
`_minimal`. It records `first` on `SY-1`, `other` on `SY-2` with origin
`follow_up`, and `second` on `SY-1`. It makes a second `SY-1` task and
records `again` on it. It keeps `SY-1`'s key now. A later fold drops and
inserts each task again, so a key looked up afterwards by the old
`task_id` names another task.

- A fresh ledger, seeded by `_seed_unrelated_task` (`:141`), takes
  `fold(record, into)`. Its rows equal the source's.
- `fold_task` of each key into the source leaves its rows unchanged.
- `fold_task(key, [])` on the fresh ledger leaves `SY-2`'s row and the
  second `SY-1` task's row alone.
- `fold_task` there with `SY-1`'s facts less its first `spec_text` fact
  leaves one `SY-1` row, with `n` 2.

These fail it:

- `_apply` with no branch for `spec_text`, which raises at the first write,
  since the live write applies the fact too
- `_drop_task_rows` that leaves the rows, which raises on the primary key
- `_drop_task_rows` that deletes by the task's spec id, which drops the
  second `SY-1` task's row
- `INSERT OR REPLACE` with `_drop_task_rows` untouched, which leaves
  `SY-1`'s rows after `fold_task(key, [])`
- an `n` counted from the rows in `_apply`, which gives the last row 1

**How the lists were measured.** A prototype ran on 2026-09-27 at
`f492629e`, ported from `SA-0150`'s of 2026-09-24. Both witnesses passed,
and the whole suite and `ty` stayed green. Each wrong version above was
applied as a text edit, with no bytecode cache, and each failed its own
witness. With `saffron/ledger.py` reverted, both witnesses failed, and
neither failed collection.

**What the witnesses leave undriven.**

- Two texts recorded for one task at once. SQLite serialises the two
  writes, and the second takes the next `n`.
- A text holding a lone surrogate. `text.encode()` raises
  `UnicodeEncodeError` while the payload is built, before any write.

**`ty` reads the tests.** `spec_text` returns `sqlite3.Row | None`, so
assert the row is not `None` before indexing it.

**Measure with no bytecode cache.** Two text edits of equal length in one
second leave a stale `.pyc`. The second edit then runs as the first. Set
`PYTHONDONTWRITEBYTECODE=1` when you try a wrong build.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 changed tokens (`saffron/gates/core/size.py:26`).
The prototype, formatted with `ruff format`, measured 913 changed tokens
with `size_gate`'s own count: 431 in `ledger.py` and 482 in the test.
Sibling cells landed at 1.4 times their authors' estimates, so about 1278
tokens, 43% of the ceiling. The plan's `estimated_lines` counts lines, and
the checkpoint prices each line at 4 tokens
(`saffron/gates/core/size.py:39`). So plan this at about 320 changed
lines, not at a token count.
