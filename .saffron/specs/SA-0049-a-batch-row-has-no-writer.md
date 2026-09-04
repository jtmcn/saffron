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
budget_usd: 8
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
      A night's spend is derived from the tasks that spent it, never passed in.
      The identical argument set_task_state already makes about a task's spend
      and its attempts: a figure passed by a caller can disagree with the rows
      it is made of, and a figure derived from them cannot.
    witness: tests/test_ledger.py::test_a_batchs_spend_is_summed_from_its_tasks_not_passed_in
  - claim: >-
      A batch with no runs yet reports zero spend rather than nothing. The
      empty sum is a real answer about a night that has spent nothing, and a
      NULL there would read as "not measured" — the distinction events.py
      already draws in as many words.
    witness: tests/test_ledger.py::test_a_batch_with_no_runs_has_spent_zero
  - claim: >-
      A run opened inside a batch is reachable from it, so the rows a night is
      made of can be found from the night. This is what runs.batch_id was
      added for and nothing has yet connected the two ends.
    witness: tests/test_ledger.py::test_a_run_opened_inside_a_batch_is_reachable_from_it
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
the strictest ceiling, which is the arrangement backlog item 56 measured the
cost of. This half is small and elevated; the loop is large and standard.

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

**Read `finish_run` before writing `finish_batch`.** It is four lines and it is
the shape: one `UPDATE`, status and end together, then commit. Do not invent a
second style for the same job one table over.

**Derive the spend; do not accept it.** `set_task_state`'s docstring gives the
argument in one sentence — *"Derived rather than passed, so the figure can
never disagree with the rows it is made of"* — and a batch stands in the same
relation to its tasks as a task does to its attempts. The join runs
`batches` → `runs.batch_id` → `tasks.run_id` → `tasks.spent_usd_est`. A
`COALESCE` to `0.0` is what makes the fifth witness true, and `set_task_state`
already uses exactly that for the same reason.

**Zero and NULL are different answers and this schema uses both.** A batch that
has spent nothing has spent `0.0`; `ended_at` and `status` are NULL while it
runs because those are *not yet measured*. `events.py` states the convention
this repo follows — *"`None`, never `0`: a skipped or errored gate had no count
computed"* — and the two columns here fall on opposite sides of it.

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

**Migrations: read the three shapes already in this module.** This spec adds no
column — `SA-0045` added them all — so it should need none of the three. If it
appears to, something has been misread.

`risk: elevated` because `saffron/ledger.py` is in this repo's `elevate_on`,
which also makes `size` blocking here. The spec is small on purpose.
