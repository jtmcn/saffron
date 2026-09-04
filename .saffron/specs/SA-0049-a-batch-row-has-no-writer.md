---
id: SA-0049
title: the batches table has no writer, and a night's spend would be a number passed rather than derived
type: feature
priority: 1
depends_on:
  - SA-0048
touches:
  - saffron/ledger.py
  - tests/test_ledger.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 10
max_attempts: 3
max_turns: 70
risk: elevated
acceptance:
  - claim: >-
      A batch can be opened. The row carries its budget and its until, and is
      in flight: no status and no end. §4.2.1's four stop reasons describe how
      a batch *ended*, so a batch that has not ended has none of them, and the
      schema's CHECK is satisfied by NULL for exactly this reason.
    witness: tests/test_ledger.py::test_an_opened_batch_is_in_flight_with_no_stop_reason
  - claim: >-
      A batch can be closed with the reason it stopped for, which sets the end
      and the status together. Modelled on finish_run, which does the same for
      a run and is the shape this repo already uses.
    witness: tests/test_ledger.py::test_closing_a_batch_records_its_stop_reason_and_end
  - claim: >-
      A stop reason outside §4.2.1's four is refused rather than stored. The
      CHECK already says so; this proves the writer surfaces it instead of
      swallowing it, which is the difference between a constraint and a
      constraint nobody can see fire.
    witness: tests/test_ledger.py::test_closing_a_batch_with_an_invented_stop_reason_is_refused
  - claim: >-
      Closing a batch writes the status, the end and the spend in one UPDATE —
      finish_run's shape, one table over — and the spend it writes is the
      reader's return value bound as a parameter, never a second copy of the
      join. Derived rather than passed by a caller, which is set_task_state's
      argument; through the reader rather than repeated in SQL, which is how
      the close and the reader stay one sum. Storing
      it is what gives batches.spent_usd_est a writer; a pure query would leave
      that column written by nobody, which the schema test guarding item 18
      exists to forbid.
    witness: tests/test_ledger.py::test_closing_a_batch_derives_and_stores_its_spend
  - claim: >-
      A batch closed with no runs stores zero, not NULL. The empty sum is a
      real answer about a night that spent nothing, and NULL is reserved for
      the batch still running — the same distinction ended_at draws, and the
      convention events.py fixes: None means not measured, zero is a
      measurement.
    witness: tests/test_ledger.py::test_a_batch_closed_with_no_runs_stores_zero_not_null
  - claim: >-
      A reader returns the runs a batch is made of, so a night can be walked
      from its own row. The column already round-trips through create_run —
      a test added in SA-0045's review round proves that — but no method
      projects it, and queue_lines does not. This witness goes through the new
      reader, never raw SQL, or it re-proves what is already proven.
    witness: tests/test_ledger.py::test_a_batchs_runs_are_readable_from_the_batch
  - claim: >-
      A run can be attached to the batch it ran under after the row already
      exists. create_run accepts a batch id, but the only call that mints a run
      passes none — it is inside run_one_cell, in saffron/cell/**, which the
      loop that owns the batch may not edit — so without this stamp
      runs.batch_id is written by nobody, every join through it returns nothing, and the spend derived
      above is zero for every real night. The shape record_push and
      set_task_package already use on tasks: the row exists, then the fact
      about it arrives.
    witness: tests/test_ledger.py::test_a_run_can_be_attached_to_its_batch_after_the_fact
  - claim: >-
      The same derivation the close performs is readable while the batch is
      still running, so the loop's budget gate reads its spend back rather than
      keeping a tally. task_spend's docstring is the argument one level down —
      "a caller whose own tally lost a frame reads it back rather than
      reporting the gap" — and the close and the reader must not be two
      spellings of one sum that can drift apart.
    witness: tests/test_ledger.py::test_a_running_batchs_spend_is_readable_before_it_closes
---

## Context

`SA-0045` landed the `batches` table and `runs.batch_id`, and deferred the
writer in as many words: *"no `create_batch` method exists yet, and the spec
that adds the loop adds it with its caller."*

**Splitting the writer from the loop is a change from that plan, and the reason
is measurable.** `saffron/ledger.py` is in this repo's `elevate_on`, so any
spec touching it runs at elevated risk, where `size` is **blocking** at 600
changed lines rather than advisory. The loop is the widest piece of the batch
work; making it carry the ledger methods too would put the largest spec under
the strictest ceiling — the arrangement backlog item 25 measured the cost of
(`SA-0009`: 990 changed lines, never converged, `EXHAUSTED` at $31.60), and
item 56 is the un-built check that would have caught it. This half is small and elevated; the loop is large and standard.

## Problem

- **The table has no writer.** Nothing can open a batch or close one, so §6's
  morning queue still has no source for a night's window or stop reason.
- **`runs.batch_id` connects nothing.** The column exists and no code path puts
  a real batch id in it.
- **A night's spend has no defined provenance yet**, and the obvious
  implementation — a caller passing a running total — is the one this repo has
  already rejected once for tasks.

## Out of scope

**The loop.** `SA-0050` iterates the queue and calls these. This spec adds the
methods and their tests, and nothing calls them yet — deliberately, and the
inertness is named here rather than discovered.

**The `saffron batch` command.** `SA-0051`.

**Deciding the stop reason.** Which of the four a night ended for is the loop's
judgement. This stores what it is told, and refuses a fifth.

**Rendering a batch.** `saffron/report/**` is `forbidden`.

## Notes for the agent

**Read `finish_run` before writing `finish_batch`.** Five body lines, and it is
the shape: one `UPDATE`, status and end together, then commit. Do not invent a
second style for the same job one table over.

**Derive the spend; do not accept it.** `set_task_state`'s docstring gives the
argument in one sentence — *"Derived rather than passed, so the figure can
never disagree with the rows it is made of"* — and a batch stands to its tasks
as a task stands to its attempts.

**The join does not stop at `tasks.spent_usd_est`, and this module says why.**
`task_spend`'s docstring: *"Summed, not read off `tasks.spent_usd_est`, which is
only as fresh as the last `set_task_state` and would silently omit the turn that
just closed."* A batch reading that column would inherit exactly that staleness —
the same defect this witness exists to prevent, one level up. Go the whole way:
`batches` → `runs.batch_id` → `tasks.run_id` → `attempts.cost_usd_est`, with a
`COALESCE` to `0.0`, which is what makes the fifth witness true and what
`set_task_state` already does for the same reason.

**Zero and NULL are different answers, and `spent_usd_est` is on both sides of
the line depending on when you look.** While a batch runs it is NULL, with
`ended_at` and `status`, because none of the three has been measured yet — which
is what `SA-0045`'s own schema comment means by *"unset while the batch is still
going"*. When the batch closes, all three are written, and a night that spent
nothing stores `0.0` rather than NULL. `events.py` fixes the convention this
follows: *"`None`, never `0`: a skipped or errored gate had no count computed."*

**These methods have no caller when this merges, and that is the plan.**
`SA-0050` is the first. Do not add one: `saffron/cli.py` and every phase are
`forbidden`, so wiring a caller would fail `scope` on every attempt. If a test
wants to prove the round trip, it calls the methods directly, the way
`tests/test_ledger.py` already tests every other writer.

**No new test may carry the `cell` marker.** `pyproject.toml` sets
`addopts = "-m 'not cell'"` and the `tests` gate passes the same argv to
`--collect-only`, so a cell-marked witness is never collected at head,
`criteria` reports `witness-not-collected`, and the attempt is spent on a test
that was correct. Nothing here needs a container.

**Migrations: this spec adds no column.** `SA-0045` added them all, so none of
this module's several migration shapes should be needed. If one appears to be,
something has been misread.

**Correct one stale cross-reference while you are here.** A comment in this
module names `SA-0049` as the batch loop. The loop is now `SA-0050`; this spec
is the writer. `saffron/ledger.py` is in `touches`, so fix it. The identical
stale reference in `saffron/preflight.py` is `forbidden` here and is being
corrected by hand — leave it alone.

**Witness 1 is not the existing `test_a_batch_still_running_has_no_status_yet`.**
That one asserts the same two NULLs by raw `INSERT`. This one asserts them
through the new opener, which is the part that does not exist. Different node
id, so `criteria` is satisfied either way — but a copy of the old test proves
nothing new and the adequacy lens will say so.

**Four methods, and `SA-0050` calls all four.** An opener, a closer taking the
stop reason, an attach for a run whose row already exists, and a reader for the
spend of a batch still running. The names are yours; the shapes are not, and a
name chosen here is the one the loop will have to find.

**The two readers exist because `SA-0050` cannot reach the writes itself.**
The loop that opens and closes a batch may edit neither `saffron/ledger.py` nor
`saffron/cell/**`, so the attach and the running-spend reader are this spec's
to add and the loop's to call. Both have no caller when this merges, exactly as
the opener and the closer do.

**One sum, not two.** The reader and the close compute the same figure —
`batches` → `runs.batch_id` → `tasks.run_id` → `attempts.cost_usd_est` — so the
close derives its stored value through the reader rather than repeating the
SQL. Two spellings of one sum is how they come to disagree.

**Witness 3: let the constraint speak.** The schema's `CHECK` already refuses a
fifth status and `sqlite3` raises `IntegrityError`. Do not catch it and re-raise
something friendlier — the witness is that the writer surfaces the database's
own refusal rather than swallowing it.

`risk: elevated` because `saffron/ledger.py` is in this repo's `elevate_on`,
which also makes `size` blocking here. The spec is small on purpose.
