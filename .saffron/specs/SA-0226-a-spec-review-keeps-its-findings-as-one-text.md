---
id: SA-0226
title: A spec review keeps its findings as one text, so no later defect can name the round that raised it
type: feature
priority: 2
depends_on: [SA-0224]
estimated_lines: 231
estimate_measured: true
touches:
  - saffron/ledger.py
  - saffron/batch.py
  - tests/test_batch.py
  - tests/test_record_migrate.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/spec_review.py
  - saffron/follow_up.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/intake.py
  - saffron/scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_appends.py
  - tests/test_ledger_fold_task.py
  - tests/test_fold.py
  - tests/test_record.py
  - tests/test_spec_review.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 130
risk: elevated
acceptance:
  - claim: >-
      `run_stack_batch` records each spec review round's findings one by
      one. Each finding `read_spec_review` parsed from the round's block
      becomes one `spec_finding` fact on the spec's task and one
      `spec_findings` row. Both carry the round's `n`, the finding's
      `position` from 1 in block order, and its `severity`, `fixes`,
      `claim`, `criterion`, `file` and `line` as read, a null included. A
      `criterion`, `file` or `line` that is null, text, or an integer that
      is not a `bool` and fits in 64 bits is kept as it is. Any other is
      stored as its JSON text in the fact and the row alike, and nothing
      raises. A round's `spec_finding`
      facts are appended after its `spec_review` fact. A round routed
      `error` writes none. The witness drives rounds routed
      `revise`, `run` and `escalate`, a round with no findings, and a
      second round after a revision and after a `wait`. It drives each
      severity, each of the three tags and a null one, and `criterion`,
      `file` and `line` each set and each null. It drives `criterion` and
      `line` as lists, `file` as an object, a float `line`, a `bool`
      `criterion` and a numeric text `criterion`, and compares each stored
      value by type as well as value. Its three `error` rounds
      are a session that reported an error over a block holding a finding,
      a session with no block, and a review that raised.
    witness: tests/test_batch.py::test_each_spec_review_round_records_each_of_its_findings
    wrong_versions:
      - The read path passes no findings, so no round writes any.
      - Positions start at 0.
      - A position counts across the task's rounds, so round 2 starts after round 1's last.
      - A `note` is not recorded.
      - A finding's `fixes` is kept for a `blocker` alone, so a tagged `concern` reads null.
      - A finding's `n` counts only the rounds that held a finding, so a round after a `wait` reads 1.
      - Every finding is filed under round 1.
      - The findings are read from the block whatever the session's error, so an `error` round writes them.
      - The rows are written and no `spec_finding` fact is appended.
      - The findings are sorted by severity before they are numbered.
      - The findings are written in reverse block order.
      - "`file` and `line` are written null."
      - "`criterion` is written null."
      - "`criterion` and `line` are swapped between their columns."
      - A round's `spec_finding` facts are appended before its `spec_review` fact.
      - A list or an object is passed to SQLite as it came, so the write raises.
      - A list or an object is stored as Python's `str` of it.
      - A list or an object is stored null.
      - Only a list or an object becomes JSON text, so a float is kept as it came.
      - A `bool` is kept as an integer.
      - "`criterion`, `file` and `line` are declared `INTEGER`, `TEXT` and `INTEGER`, as the neighbouring tables declare them."
      - "`criterion`, `file` and `line` are declared `TEXT`."
  - claim: >-
      Folding the record into a fresh ledger, and back into the source,
      rebuilds every `spec_findings` row as written. `fold_task` given no
      facts drops that task's rows and no other task's. Given a task's
      facts less its first round's `spec_review` and `spec_finding` facts,
      it keeps the second round's rows with their own `n`. The witness
      drives a fresh ledger holding a task of another repo, the source
      ledger, and both forms of `fold_task`.
    witness: tests/test_batch.py::test_the_spec_findings_fold_back_from_the_record_alone
    wrong_versions:
      - The fold skips `spec_finding` facts, so only the live write fills the table.
      - "`_drop_task_rows` leaves `spec_findings`, so a fold back into the source collides."
      - "`_drop_task_rows` deletes every task's `spec_findings` rows."
      - The fold numbers a finding by the task's `spec_reviews` row count rather than its payload's `n`.
---

## Context

Backlog item **b-98a3be**, under `DESIGN.md` §3.4, as point 2 of its Done
looks like, the storage half. §3.4 says "Every review round records its
findings one by one. Each is a `spec_finding` fact with its round,
severity, tag, claim and file. A stack batch's spec review writes them
too." This spec builds that and nothing that reads it.

Line numbers below were read at `af009e9d`, unless they name
`origin/saffron/SA-0224` at `66cdece1`. The `saffron/ledger.py` lines shift
at the cell's real base, once `SA-0220` to `SA-0224` merge.

**A round's findings are stored as one text.** `run_stack_batch` reads each
review session with `spec_review.read_spec_review` and routes it with
`spec_review_route` (`saffron/batch.py:576-577`). It then records the round
with `ledger.record_spec_review(task_id, route=..., block=read.block,
block_sha256=read.block_sha256, error=read.error)` (`saffron/batch.py:598-604`).
`read.findings` reaches no ledger call. The `spec_reviews` table holds
`block` as one `TEXT` column (`saffron/ledger.py:267-276`). So no row names
one finding, and a later defect cannot point at the round that raised it.

**The parsed findings already exist.** `read_spec_review`
(`saffron/spec_review.py:205-263`) builds one `SpecReviewFinding` per entry
(`:140-149`), with `severity`, `claim`, `fixes`, `criterion`, `file` and
`line`. It copies `criterion`, `file` and `line` with `raw.get` and checks
no type (`:251-253`). So a reviewer's list or object reaches the ledger. Every path that sets `error` returns `findings=[]` through `_error`
(`:192-202`). `spec_review_route` returns `error` only when `error` is set
and `resets_at` is not (`:266-286`). So a round routed `error` has no
parsed findings to write.

**Where the round is recorded.** `Ledger.record_spec_review` is at
`saffron/ledger.py:1624-1655`. It numbers the round one more than the
task's own `spec_reviews` rows (`:1637-1644`). It writes one `spec_review`
fact through `_commit_and_append` (`:540-545`). `_apply`'s
`spec_review` branch (`saffron/ledger.py:846-861`) inserts the row from the
payload's own `n`, so a fold keeps a dropped fact's numbering.
`_drop_task_rows` (`saffron/ledger.py:555-566`) deletes each key-filed
table's rows before `fold_task` (`:547-553`) re-applies a task's facts.
`batch.py` calls `record_spec_review` in one other place, when `review`
itself raised (`saffron/batch.py:564-570`).

**A test at the cell's base calls it too.** `SA-0224`'s
`tests/test_record_migrate.py` calls `source.record_spec_review(` with no
findings at `:1500` and `:1503` on `origin/saffron/SA-0224`. That file does
not exist at `3d594729`. It exists only at the cell's real base, once
`SA-0224` merges. No other caller exists on that branch.

**The kind exists already.** This spec's own pull request adds
`spec_finding` to `KINDS` (`saffron/record/contract.py:42`), to
`factory:FactKind` in `ontology/factory.ttl`, and to `CONTEXT.md`'s
generated list, by hand. `Fact.__post_init__` refuses any other kind
(`saffron/record/contract.py:82`). Nothing appends one at base.

`SA-0227` adds `saffron draft`, which reuses this review path. It expects
`record_spec_review` to write the findings, so it gains them with no
further call of its own.

## Problem

1. **The table.** Add `spec_findings` to `SCHEMA` in `saffron/ledger.py`,
   keyed on `task_key` like `spec_reviews`. Its columns are `task_key`, `n`,
   `position`, `severity`, `fixes`, `claim`, `criterion`, `file` and `line`.
   `fixes`, `criterion`, `file` and `line` are nullable. The key is
   `(task_key, n, position)`. Declare `criterion`, `file` and `line` with
   no column type. SQLite's affinity rewrites a value in a typed column, so
   the row would differ from the fact. The operator measured it: an
   `INTEGER` column stores `'1'` as 1, `'2.5'` as 2.5 and `'40.0'` as 40.
   A `TEXT` column stores 7 as `'7'`. An untyped column keeps each as
   given.
2. **The write.** `record_spec_review` takes the round's parsed findings as
   a keyword with no default. After the round's own fact, it writes one
   `spec_finding` fact per finding through `_commit_and_append`. The
   payload carries the round's `n`, `position` from 1 in the order given,
   and the six fields as read. Keep `None`, a `str`, or an `int` that is
   not a `bool` and lies in the signed 64-bit range, as it is. Any other
   `criterion`, `file` or `line` goes in as `json.dumps` of it. So the fact
   and the row hold the same value.
3. **The callers.** The read path at `saffron/batch.py:598-604` passes
   `read.findings`. The raise path at `:564-570` passes an empty list. Both
   `record_spec_review` calls in `tests/test_record_migrate.py` pass
   `findings=[]`, or that test raises `TypeError` at head.
4. **The fold.** `_apply` gains a `spec_finding` branch that inserts the row
   from the payload alone, `n` included. `_drop_task_rows` deletes the
   task's `spec_findings` rows beside its `spec_reviews` rows. Its
   docstring's "so all six deletes run first" (`saffron/ledger.py:559-560`)
   becomes seven, with `spec_findings` named.
5. **The docstring.** The module docstring's "Only the seventeen kinds
   `_append` writes fold back" (`saffron/ledger.py:6-7`) becomes eighteen.

## Out of scope

- Matching a finding to a later defect, any report over the rows, and any
  view page. `SA-0228` adds attempt totals to the task page and reads no
  finding.
- `spec_reviews.block` stays as it is. The rows add to it.
- The migration. `SA-0222` to `SA-0224` write a stored ledger's rows into
  the record and know nothing of `spec_findings`. A ledger written after
  this change and then migrated loses its findings rows. The operator
  files a follow-up item extending `migrate` to `spec_findings` before any
  cutover.
- `saffron/follow_up.py`'s writer opens no review, so it writes no finding.
- `CONTEXT.md`'s **Spec review** term gains a sentence saying each round
  records each finding as a `spec_finding` fact. The operator writes it by
  hand in this spec's pull request, since `CONTEXT.md` is protected.
- The ledger module docstring's count of tables outside §4.1
  (`saffron/ledger.py:11-16`). Leave it, or add `spec_findings` to it.
- `tests/test_fold.py:375` says "one of the seven kinds `_apply` never
  places". That is eight at base and seven again after this change. It
  needs no edit.

## Notes for the agent

**This change is new code inside existing functions.** No text at base
fixes the spelling of what it adds. So each criterion declares a witness
and no mutant, and the `witness` gate reports `skip` for both. The wrong
versions under each criterion are what its witness must kill. Do not run
them yourself.

**The kind is landed by hand in this spec's pull request.** `KINDS`,
`ontology/factory.ttl`, its shapes and `CONTEXT.md`'s list carry
`spec_finding` at base. `CONTEXT.md` is protected, so no cell could
render it. Edit none of them. This spec builds the table, the write and
the fold.

**The parent is `SA-0224`, the top of the chain from `SA-0220`.** `SA-0220`
edits `saffron/ledger.py` too. The overlap walk follows `depends_on[0]`
alone, and `SA-0227` stacks on this spec.

**Every witness must fail at base.** At base no `spec_findings` table
exists. Import nothing at module scope that this change adds.
`saffron/spec_review.py` does not import `saffron/ledger.py` at run time.
So `ledger.py` can import `SpecReviewFinding` for its types.

**One arrangement drives both witnesses.** Build it once in a helper. Use
a `Ledger` backed by a `MemoryRecord`. Use `MintDouble`, `_RevisionWrite`,
`_RevisionRunner`, `_candidate_x` and an `AdvancingClock`. Pass `revise`,
and `sleep=clock.sleep`. The review double pops a scripted
`_review_session` or raises a scripted exception, and takes `**kw`, since a
revised round is called with `spec_text`. Give each finding a claim of its
own, so order shows. Two consecutive aborts fire the breaker
(`saffron/batch.py:67`), so put a clean spec between any two `error` rounds.
Eight specs in this order are enough.

- `TE-1`: round 1 holds three findings in this order. A `concern` tagged
  `witness` names no place. A `blocker` tagged `build` names criterion 1,
  a file and line 40. A `note` names criterion 2 and a file, and no
  line. Line 40 differs from every criterion number, so a swap shows.
  It routes `revise`. One written revision follows. Round 2 holds a `note`
  naming a line alone.
- `TE-2`: a fenced block holding a `concern`, with `error="cell died"`.
- `TE-3`: a `concern` tagged `build` whose criterion is `[1, 2]`, whose
  file is `{"path": "c.py"}` and whose line is `[12, 40]`. Then a `note`
  whose criterion is `true` and whose line is 2.5. It routes `run`.
- `TE-4`: no fenced block.
- `TE-5`: no fenced block with `resets_at` set, routed `wait`, then a
  `note`.
- `TE-6`: the review raises `RuntimeError`.
- `TE-7`: no findings.
- `TE-8`: a `blocker` tagged `scope`, and a `note` whose criterion is the
  text `"2"`. It routes `escalate`.

**What the witness leaves undriven.** A `wait` round whose block parsed is
one. A rejected review session carries empty text
(`saffron/spec_review.py:346-348`), so it parses nothing. An escalation
after the last revision is another (`saffron/batch.py:587`). It records the
same read the `revise` route does. An integer beyond 64 bits is a third.
The rule stores it as JSON text, since `sqlite3` raises `OverflowError` on
one.

**Criterion 1.** For each spec, compare the task's `spec_finding` facts and
its `spec_findings` rows to the same expected list of tuples, field by
field. Compare each value with its Python type beside it, since `True`
equals 1 under `==`. A row read back holds `int`, `float` or `str` as
SQLite stored it. Also assert each task's `spec_reviews` routes, so the arrangement
cannot drift off the routes the claim names. For `TE-1`, assert the
`(kind, n)` order of its `spec_review` and `spec_finding` facts as the
record reads them back.

**Criterion 2.** Read every key you need before the first fold, since a
fold mints new task ids. Fold into a fresh ledger holding one task of
another repo, then back into the source. For the trimmed form, leave out
the facts whose `n` is 1 among `TE-1`'s `spec_review` and `spec_finding`
facts.

**Measured on a prototype.** A prototype at `origin/saffron/SA-0224`,
with the hand vocabulary commit applied, passed both witnesses, and each failed with its source
reverted. Its diff measured 923 changed tokens. Each of the 26 wrong
versions above was applied to it as an edit, and each failed its own
criterion's witness. The rest of the suite passed on it.
