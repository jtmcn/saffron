---
id: SA-0336
title: "No record append emits an event, so a task's `events.jsonl` can omit a fact its record holds"
type: bug
priority: 1
estimated_lines: 20
estimate_measured: true
depends_on: [SA-0335]
touches:
  - saffron/ledger.py
  - saffron/cli.py
  - tests/test_ledger_events.py
  - tests/test_regate.py
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
  - saffron/events.py
  - tests/test_events.py
  - saffron/record/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/watch.py
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
budget_usd: 40
max_attempts: 3
max_turns: 200
risk: standard
acceptance:
  - claim: >-
      Each fact a `Ledger` built with a record and an `events` sink appends
      emits one `RecordAppend` through that sink. The event names the fact's
      kind, its task key and that task's spec id. It is emitted after the
      record took its fact and before the next fact is appended. The witness
      drives every write method that appends, and so all twenty fact kinds
      the notes list. It writes two tasks under two spec ids, and a fact on
      the first task after the second task's `task_created`. It writes two
      findings in one `record_findings` call, and a `spec_review` with one
      `spec_finding`.
    witness: tests/test_ledger_events.py::test_each_fact_the_ledger_appends_emits_one_event_naming_its_kind_and_key
    wrong_versions:
      - The event is emitted before the record's append, so the sink runs while the record lacks its fact.
      - Only `_commit_and_append` emits, so the facts `record_findings` appends in its own loop emit nothing.
      - "`record_findings` emits once per call, so its second finding has no event."
      - "`record_spec_review` emits for its `spec_review` fact and not for each `spec_finding`."
      - The event's spec id is read from the first task in the ledger rather than from the fact's own task.
      - The event's spec id is read from the newest task rather than from the fact's own task.
      - Only `task_created` and `task_state` facts emit.
  - claim: >-
      An append the record refuses emits no event, on both paths a fact is
      appended by. The witness first sees a taken append emit on each path,
      through the same sink. It then drives a refused `task_state` through
      `_commit_and_append`, and a `record_findings` call whose second fact is
      refused. That call emits for its first fact alone.
    witness: tests/test_ledger_events.py::test_an_append_the_record_refuses_emits_no_event
    wrong_versions:
      - The event is emitted before the record's append, so a refused append still emits.
      - "`record_findings` emits for all its facts after its loop, so a refusal of the second fact leaves the first with no event."
      - Only `_commit_and_append` emits, so a taken finding emits nothing.
      - "`_append` catches `RecordError` and returns, so a refused write raises nothing."
  - claim: >-
      A `Ledger` built with an `events` sink and no record emits no event. The
      witness first drives every write method through a ledger built with a
      record and finds all twenty fact kinds through its sink. It then drives
      the same writes through a ledger with no record, and its sink receives
      nothing.
    witness: tests/test_ledger_events.py::test_a_ledger_with_no_record_emits_no_event
    wrong_versions:
      - The emit sits outside the check for a record, so a ledger with no record emits an event for each write.
  - claim: >-
      The `Ledger` that `saffron`'s entry point builds writes each
      `RecordAppend` to the `events.jsonl` of that fact's own task, under the
      command's batch tree. The witness drives both places a batch tree comes
      from: the default under `--home`, through `cell`, and `--out`, through
      `replay`. `cell` writes two tasks under two spec ids, and a fact on the
      first task after the second task's `task_created`. Each task's log
      holds one event for each fact its ref on the mirror holds, in order, and
      no other task's events.
    witness: tests/test_ledger_events.py::test_main_writes_each_append_event_to_its_own_tasks_log
    wrong_versions:
      - The entry point builds its `Ledger` with no sink.
      - The sink writes every event to one log at the batch tree's root.
      - The sink writes under `--home`'s batch tree and ignores `--out`.
      - The event's spec id is read from the first task in the ledger, so the second task's events land in the first task's log.
      - The event's spec id is read from the newest task, so the first task's later fact lands in the second task's log.
---

## Context

Backlog item **b-6677b6**, under item 170 and §8 of
`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md` (the
record design below). Every line here was read at `5d843e32`, with the
changes of `SA-0334` and `SA-0335` applied, their tests included. Lines in `saffron/cli.py`, which
`SA-0335` edits, are named by construct.

**The rule.** The record design's §8 reads: "Every record append also emits
an event. No event implies an append." It binds once a production caller
builds a `Ledger` with a record
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:370-375`).
`main` in `saffron/cli.py` is that caller. It builds one `Ledger` with a
`RoutedRecord` for every command but `fold`, `migrate`, `serve` and `next-id`.

**What an append does today.** `Ledger.__init__` takes a path and an optional
record, and nothing else (`saffron/ledger.py:402-403`). Every write method
but one applies its fact, commits, then calls `_append`
(`saffron/ledger.py:656-661`).
`record_findings` commits all its facts, then calls `_append` once per fact in
its own loop (`saffron/ledger.py:2110-2113`). `_append` hands the fact to the
record and emits nothing (`saffron/ledger.py:650-654`). So `events.jsonl` can
omit a fact the record holds, and nothing reports the gap.

**Where a task's log lives.** `main` sets the command's batch tree to `--out`
when the command has one, else to `batches/v0` under `--home`
(`saffron/cli.py:320-321`). Only `replay` takes `--out`. A task's log is
`events.jsonl` in that tree's directory named for the task's spec id
(`saffron/task.py:770`, `saffron/cell/session.py:1029`). `EventLog.append`
writes one line and never raises (`saffron/events.py`, `EventLog.append`).

**The event kind is already in.** This spec's own commit adds `RecordAppend`
to `saffron/events.py`. It is in the `Event` union and `_KINDS`, and
`describe` renders it. Its fields are `timestamp`, `spec_id`, `fact_kind` and
`task_key`, and it carries no payload. The same commit adds
`factory:RecordAppendEvent` to `ontology/factory.ttl`, and the render carries
it into `CONTEXT.md`'s **Event kind** entry and `EventKindShape`. So a
`RecordAppend` constructs, round-trips through `read_log`, and renders at this
spec's base.

**The fact kinds the ledger appends.** Twenty write methods append, from
twenty-one call sites, and they append twenty kinds: `task_created`,
`task_state`, `attempt_opened`, `attempt_closed`, `gate_result`, `finding`,
`rebuttal`, `task_policy`, `task_engine`, `task_push`, `task_package`,
`task_merged_head`, `stack_layer`, `stack_finish`, `task_regate`,
`spec_review`, `spec_finding`, `spec_text`, `end_review` and `qualification`.
`set_task_package` and `adopt_pull_request` both append `task_package`
(`saffron/ledger.py:1706`, `:1735`). `record_spec_review` appends a
`spec_review` and then one `spec_finding` per finding
(`saffron/ledger.py:1936`, `:1952`). The other seven kinds in
`saffron/record/contract.py`'s `KINDS` are appended by no write method.

## Problem

1. **The sink.** `Ledger.__init__` takes an optional keyword `events`, a
   callable taking one `RecordAppend`, defaulting to `None`.
2. **The emit.** In `_append`, once the record's `append` returns, call the
   sink with one `RecordAppend`. Its `fact_kind` is the fact's kind and its
   `task_key` the fact's task key. Its `spec_id` is the `tasks` row's
   `spec_id` under that record key. Its `timestamp` is `time.time()`. Emit
   nothing when the ledger has no record or no sink. An append that raises
   emits nothing.
3. **The wiring.** In `main`, build the shared `Ledger` with a sink. It
   appends each event to an `EventLog` at the batch tree joined with the
   event's `spec_id`.

## Out of scope

- `saffron/events.py`, `tests/test_events.py` and the vocabulary. This spec's
  own commit carries the event kind.
- `saffron migrate`, which appends to each record with no `Ledger`
  (`saffron/record/migrate.py:110-111`). Its appends emit no event.
- `saffron fold`, which builds its `Ledger` with no record.
- A sink that raises. `EventLog.append` never does.
- Printing each event to the terminal. The sink only writes the log.
- The record design's own §8 paragraph, which this spec's own commit amends.
- `saffron/watch.py`'s docstrings, which say `run_task` writes `Ceilings`
  first in a task's log (`saffron/watch.py:26-28`, `:120-121`). A stack
  batch's minted task now logs `RecordAppend` lines before its `Ceilings`.

## Notes for the agent

**One stale word.** The module docstring says nineteen kinds fold back
(`saffron/ledger.py:7`). The count above is twenty, so make it read twenty.

**Mutants and new code.** Every criterion is new code: a new parameter, a new
emit in `_append`, a new argument in `main`, and a new test module. No
criterion declares a mutant, so `witness` reports `skip` for each. Do not run
the wrong versions yourself.

**One emit, in one place.** `_append` is the one method both append paths
reach. An emit there covers `_commit_and_append` and `record_findings`' loop
alike, and runs once per fact.

**The witnesses, in `tests/test_ledger_events.py`.**

- A record for criteria 1 to 3: a class around `MemoryRecord` that keeps
  each fact it took, in order, and refuses a fact a predicate picks with a
  `RecordError`. The sink records each event beside the count of facts the
  record held when it ran. Assert that event *n* saw exactly *n* facts, so
  each event follows its own fact and precedes the next.
- For each event *i*, assert `events[i].task_key == facts[i].task_key`. Assert
  that `events[i].spec_id` equals the spec id the test passed when it created
  that key's task. Compare each event, never a set or a membership check.
- One helper drives each write method once, over two tasks under two spec
  ids in one batch. Create both tasks first, then write at least one fact on
  the first task. A spec id read from the newest task then names the wrong
  task. Assert that the recording record's order holds a first-task fact
  after the second task's `task_created`. `tests/test_ledger_fold_task.py::_drive_every_kind`
  (`tests/test_ledger_fold_task.py:164`) drives twelve of the kinds.
  `tests/test_record_migrate.py::test_a_migrated_stack_folds_back_to_its_key_filed_rows`
  (`tests/test_record_migrate.py:1437`) drives the stack and review kinds.
  Assert that the record took exactly the twenty kinds above.
- Criterion 2 runs each refused write inside `pytest.raises(RecordError)`.
- Criterion 4 builds a bare mirror and a bare origin under `tmp_path`, and a
  repo row naming both. It replaces `saffron.cli._run_cell` and
  `saffron.cli.replay` with stubs that write through the `Ledger` they are
  handed. The `cell` stub creates both tasks before it writes a fact on
  either, so the first task's fact follows the second's `task_created`.
  Read each task's ref with `RefsRecord(mirror).read(key)`, and its
  log with `read_log`.

**What the witnesses leave undriven.** Criterion 4 drives `cell` and
`replay`. Every other command shares the same `Ledger` and the default batch
tree, so no witness drives them one by one. Criterion 2 refuses a fact on
each append path, not each write method.

**The one existing test this changes.**
`tests/test_regate.py::test_regate_passes_reverify_the_exemption_its_task_directory_holds`
runs a re-gate, then creates its task directory (`tests/test_regate.py:496`).
The re-gate's `task_regate` fact now writes `events.jsonl` into that same
directory, so the second `task_dir.mkdir` raises `FileExistsError`. Give that
`mkdir` `exist_ok=True`, and change no assertion.

**Every new test must fail with the source reverted.** Each builds a `Ledger`
with `events=`, or reads a log only the entry point's sink fills. A prototype
of this change failed all four witnesses with `saffron/ledger.py` and
`saffron/cli.py` reverted. It ran the full suite stacked on both parents'
prototypes, their tests included. The regate test above was the one test that
failed with this change and passed without it.
