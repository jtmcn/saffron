---
id: SA-0206
title: A session a bound cuts records nothing for the tokens it spent, though the runner carries their counts
type: feature
priority: 3
depends_on: [SA-0205]
estimated_lines: 249
estimate_measured: true
touches:
  - images/agent_runner.py
  - saffron/phases/implement.py
  - saffron/cell/session.py
  - saffron/ledger.py
  - tests/test_agent_runner.py
  - tests/test_implement.py
  - tests/test_session.py
  - tests/test_fold.py
  - tests/test_ledger.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/cell-base.python.Dockerfile
  - images/proxy.Dockerfile
  - saffron/cli.py
  - saffron/task.py
  - saffron/replay.py
  - saffron/events.py
  - saffron/batch.py
  - saffron/follow_up.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/record/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 34
max_attempts: 3
max_turns: 190
acceptance:
  - claim: >-
      The runner puts `model` on the event that carries an assistant
      message's per-message counts, set to the name that message gave. No
      other event of that message carries it. A message whose counts the
      runner leaves off, because its id was already seen or it has no usage,
      puts `model` on no event. The witness drives a two-block message
      naming `m-a`, a repeat of its id, a message naming `m-b`, and a
      message with no usage.
    witness: tests/test_agent_runner.py::test_the_event_carrying_a_messages_usage_names_its_model
    wrong_versions:
      - The model is put on every block event of the message.
      - The model is put on the event of a message whose id was already seen.
      - The model is put on the first event of a message that carries no usage.
      - The first model the run met is kept and stamped on every later message.
  - claim: >-
      A turn that ends with no `result` event carries `cost_floor_usd_est` on
      its attempt. It is the sum, over every event other than `result` that
      carries a per-message count, of each count times its model's rate in
      `implement.PRICES_PER_MTOK`, over a million. The witness substitutes
      that table with two models of distinct rates. A null or absent count
      adds nothing. An event whose model the table does not name, `<synthetic>`
      included, or that names no model, adds nothing. So no count is ever
      priced at another model's rate. A turn with no such event carries
      `0.0`. The witness drives `text`, `tool_use` and `thinking` events,
      and each of three endings. They are the idle bound, the wall bound,
      and a runner that exits 1 unbounded.
    witness: tests/test_implement.py::test_a_turn_with_no_result_event_carries_the_floor_its_usage_prices
    wrong_versions:
      - A model the table does not name is priced at the table's first entry.
      - Every event is priced at the model the `init` event names.
      - Only `text` events are counted.
      - A cache-read count is priced at the input rate.
      - A null count raises rather than adding nothing.
      - The floor is set only when a bound fired, so an unbounded exit carries `None`.
      - A turn with no counted event carries `None` rather than `0.0`.
  - claim: >-
      A turn that ends with no `result` event charges, as `cost_usd_est`,
      the larger of its `cost_floor_usd_est` and the `last_cost_usd` it was
      given. Its `cost_floor_usd_est` stays the floor whichever is larger. The
      witness drives a floor above a carry of `0.0` and of `2.0`, a carry
      above the floor, and the two equal.
    witness: tests/test_implement.py::test_a_cut_turn_charges_the_larger_of_its_floor_and_the_last_figure
    wrong_versions:
      - The floor replaces the carry, so a carry above the floor is lost.
      - The floor is added to the carry.
      - The carry alone is charged, as at base.
      - The larger figure is recorded as `cost_floor_usd_est` too.
  - claim: >-
      A cut turn whose stream holds no priced count still charges the
      `last_cost_usd` it was given, as at base.
    witness: tests/test_implement.py::test_a_turn_killed_before_its_result_event_still_reports_what_it_spent
    preserves: true
    wrong_versions:
      - The floor replaces the carry, so a cut turn with no counts charges `0.0`.
  - claim: >-
      A turn that reaches its `result` event carries `cost_floor_usd_est` of
      `None`, and charges what it charges at base. The witness drives a
      clean turn, a failed turn reporting a cost, and two failed turns
      reporting zero, one given a carry and one not. Each stream holds a
      priced count before its result.
    witness: tests/test_implement.py::test_a_turn_that_reached_its_result_event_carries_no_floor
    wrong_versions:
      - The floor is set on every turn, a result event or not.
      - A failed turn whose result reports zero falls back to the floor.
  - claim: >-
      Each turn `record_attempts` wraps closes its attempt row with its
      attempt's `cost_floor_usd_est`. That holds for a returned turn and for one
      that raises `AgentFailed` carrying its attempt. A floor of `0.0` is
      written as `0.0`. A turn whose attempt carries no floor, and one that
      raises with no attempt, write `None`. The witness drives each of those
      outcomes in order through one wrapped agent.
    witness: tests/test_session.py::test_every_recorded_turn_writes_the_floor_its_attempt_carries
    mutant:
      file: saffron/cell/session.py
      find: cost_floor_usd_est=attempt.cost_floor_usd_est if attempt else None,
      replace: cost_floor_usd_est=None,
    wrong_versions:
      - The failed path closes its row with `None` though its attempt carries a floor.
      - A floor of `0.0` is written as `None`.
  - claim: >-
      `Ledger.close_attempt` takes `cost_floor_usd_est`, `None` by default, and
      carries it on the `attempt_closed` fact into `attempts.cost_floor_usd_est`.
      A fold reproduces it. The witness closes attempts with a positive
      floor, `0.0` and `None`. It then appends an `attempt_closed` fact with
      no such key, as a fact written before this change, which folds to
      null. It reads the live rows and the folded rows.
    witness: tests/test_fold.py::test_the_fold_keeps_each_attempts_cost_floor
    mutant:
      file: saffron/ledger.py
      find: '"cost_floor_usd_est": cost_floor_usd_est,'
      replace: '"cost_floor_usd_est": None,'
    wrong_versions:
      - The fold writes null whatever the fact carries.
      - A fact with no such key folds to `0.0`.
      - A floor of `0.0` folds to null.
      - A fact with no such key raises in the fold.
      - The column is written live but the fact leaves the key out.
  - claim: >-
      A ledger file whose `attempts` table predates the column gains it on
      open. A row written before keeps its cost and reads a null floor. A
      row closed after reads the floor it was given.
    witness: tests/test_ledger.py::test_a_ledger_that_predates_the_cost_floor_column_gains_it
    wrong_versions:
      - No column is added to an existing ledger, so closing an attempt raises.
      - The column is added with a default of `0.0`, so an old row reads `0.0`.
---

## Context

Backlog item **b-209696**, which cites `DESIGN.md` §4.3 and §5.3. It was
split from b-d4e015. That item stopped the idle bound from cutting a
session that is still writing. A stalled session, or one that reaches the
wall, still records nothing for what it spent. `SA-0167`'s first cell spent
18 minutes of PLAN tokens and recorded $0.00.

This spec runs after `SA-0205` in one stack batch, and is cut from its
head. `SA-0205` makes the runner's `result` event carry `model` and gives
`AttemptResult` a `model` field. It also makes `_close_attempt` pass that
model. Every line number below was read at `a24e29d5`, before `SA-0205`'s
code. So lines in `images/agent_runner.py`, `saffron/phases/implement.py`
and `saffron/cell/session.py` sit elsewhere at the cell's base. Each
citation names its function. Find it by that name.

**Where the cost comes from today.** `run_agent` reads cost only from the
`result` event (`saffron/phases/implement.py:399-408`). With no `result`
event it raises `AgentFailed` whose attempt charges `last_cost_usd`
(`:360-376`). That is the figure the caller passed in, and its default is
`0.0` (`:228`). The plan turn passes none (`saffron/cell/session.py:570-572`).
So a plan turn cut by a bound charges `$0.00`.

**What the runner already carries.** Each assistant message's first event
carries that message's `input_tokens`, `cache_read_input_tokens` and
`cache_creation_input_tokens` (`images/agent_runner.py:37-41`, `:149-158`). A repeat
of a seen message id carries none (`:153`). Output tokens are left off on
purpose (`:27-41`, `SA-0090`). No event carries the message's model, so
the host cannot price those counts today.

**No price table exists in core.** `git grep` for one finds none. The cell's
rates were fit in `SA-0161`'s notes on 2026-09-25. They are $3, $15, $0.30
and $6 per million input, output, cache-read and cache-write tokens. They
fit 294 result events in `~/.saffron/batches/` exactly. `agent_options`
turns on the one-hour cache (`saffron/phases/implement.py:121`, `:155`), whose
writes cost more than the default's (`DESIGN.md` §7.1).

**The model name is the `init` event's.** `SA-0205`'s notes measured
1,565 `init` events naming `claude-sonnet-5`. Whether an assistant
message names that same string is unmeasured. If it names another, the
floor prices nothing and the turn charges its carry, as at base.

**Where an attempt's cost is written.** `record_attempts` closes one row per
turn, on a return and on `AgentFailed` (`saffron/cell/session.py:242-266`).
`_close_attempt` reads the attempt's fields (`:269-285`). `close_attempt`
builds an `attempt_closed` fact (`saffron/ledger.py:1359-1385`). `_apply`
writes that fact into `attempts`, for a live write and for a fold alike
(`:688-703`, `:528-541`). The record holds the fact's payload as any JSON
dict, so `saffron/record/` needs no edit (`saffron/record/contract.py:72-88`).
`attempts` ends at `cost_usd_est` (`saffron/ledger.py:152-165`). A ledger
opened on an older file gains a missing column by `ALTER TABLE`, one block
per table (`:346-400`).

## Problem

1. **The runner names the model beside the counts.** Where it puts the
   per-message counts on `evts[0]`, put `model` there too, as the message
   named it. Do it only when the counts go on. Keep `<synthetic>` and every
   other name as sent. The table prices none of them it does not hold.
2. **A price table in core.** Add `PRICES_PER_MTOK` to
   `saffron/phases/implement.py`. It maps a model name to a dict keyed by
   the three per-message count names. Each value is dollars per million
   tokens. Hold `claude-sonnet-5` at $3, $0.30 and $6 for input, cache
   read and cache write. One comment above it names `SA-0161`, its fit and
   its date. These are the only real price values in the change.
3. **`AttemptResult` carries the floor.** Add `cost_floor_usd_est: float | None
   = None` as its last field. `run_agent` sums the floor as events arrive,
   by criterion 2's rule. Look the table up through the module at call
   time, so a test that substitutes it changes the price. The no-result
   attempt sets `cost_floor_usd_est` to that sum. It charges the larger of the
   sum and `last_cost_usd`. Every attempt built from a `result` event
   keeps `None`, and its cost path is unchanged.
4. **`_close_attempt` passes it.** With no attempt it passes `None`. Write
   it the way `SA-0205` passes `model` beside it.
5. **The ledger keeps it.** `close_attempt` gains the keyword and puts it
   on the fact beside `cost_usd_est`. `attempts` gains a nullable `REAL`
   column. `_apply` writes it from the fact, and reads a missing key as
   null. The `ALTER TABLE` block adds it to an older file, with no default.

## Out of scope

- **Output tokens.** The runner does not carry them per message, and this
  spec does not add them. The floor is a floor for that reason.
- **A turn that reaches its `result` event.** Its cost path is unchanged,
  `_reconcile_cost` included. A failed turn that reports zero still falls
  back to the last figure, never to a floor.
- **The spec-writing and spec-review rows.** `run_stack_batch` and
  `write_follow_ups` close those from a session that sums several turns.
  A cut turn there charges the larger figure through `cost_usd_est`. Its
  row carries no floor, since `close_attempt` defaults it to `None`.
- **A model name the table lacks.** It prices at nothing, never at a
  neighbour's rate. The table holds one name. Adding another is a later
  edit to that one dict.
- **The wall bound.** `SA-0207` changes `turn_wall_s` in
  `saffron/cell/session.py`. Leave that computation alone. Keep the
  wall-cut text in `run_agent`'s `how` as it is at base, "was cut by the
  wall bound, given Ns". `SA-0207`'s witness reads that phrase.
- **`DESIGN.md`.** §4.1's schema and its fallback sentence need the floor.
  The operator edits them by hand in this spec's branch. Do not touch it.

## Notes for the agent

**Which criteria are new code.** Criteria 1, 2, 5 and 8 add code whose
spelling nothing at base fixes. Criterion 3 edits the no-result attempt's
cost line, but nothing fixes how its new text is spelled. None of the five
declares a mutant, and the `witness` gate reports `skip` for them.
Criteria 6 and 7 edit a call that exists. Each declares a mutant that
mirrors the line beside it. Criterion 4 is `preserves`. Its test exists at
base and must stay green.

**Why the names end in `_est`.** `DESIGN.md` §4.1 says a dollar estimate
carries its suffix everywhere it is stored. The floor is priced from a
table that drifts like the runtime's own, so it is an estimate too.
Annotate the table where it is declared. The `types` rule on unannotated
identities is gated.

**Commit as each witness passes.** Seven new witnesses, seven commits at
least. A turn cut by a bound then loses one witness's work, not seven.

**Every witness must fail with the source reverted.** Import nothing this
spec adds at module scope. Substitute the table with
`monkeypatch.setattr(implement, "PRICES_PER_MTOK", ...)`, which raises at
base. Build an attempt with a floor through `dataclasses.replace`. Pass the
new keyword to `close_attempt` in the test body. Each then fails at base,
and none is a collection error that `revert` reads as `skip`.

**No witness reads the real prices.** Criteria 2, 3 and 5 substitute a
table of two models, `m-a` and `m-b`. Give the two distinct rates on all
three counts, and give each count a distinct rate within a model. Then a
count priced at the wrong key or the wrong model changes the sum. Compare
dollars with `pytest.approx`.

**Criterion 1.** Call `runner.events` on `SimpleNamespace` messages, as
`test_the_counts_for_one_message_id_reach_the_log_once` does
(`tests/test_agent_runner.py:222-256`). Give the first message two text
blocks, so its second event shows a model put on every block. The
autouse fixture already clears the seen ids (`:38-45`).

**Criterion 2.** Use `_stream`, `_no_reap` and `pytest.raises(AgentFailed)`
(`tests/test_implement.py:176-214`). Open the stream with an `init`
system event naming `m-a`, then price an `m-b` event, so a floor priced at
the `init` model fails. Put a null cache-read count on one event. Add one
event each naming `m-c`, `<synthetic>` and no model, with counts large
enough to show if priced. Run the same lines three times: `timed_out=True`
with `bound="idle"`, the same with `bound="wall"`, and `returncode=1` with
no bound. Then run a stream holding only the `init` event. The runner
can put counts on a `passthrough` event too. The witness leaves that kind
undriven, and the claim names only the three it drives.

**Criterion 3.** One priced event fixes the floor. Drive carries of
`0.0`, `2.0`, a value above the floor, and the floor itself. Assert both
`cost_usd_est` and `cost_floor_usd_est` on each row.

**Criterion 5.** Put the same priced event ahead of each `_result_line`.
The zero-cost rows use `subtype="error_during_execution"` and
`total_cost_usd=0`. The row with no carry must charge `0.0`, so a fallback
to the floor fails there.

**Criterion 6.** Build a real `Ledger` under `tmp_path` with one repo, run
and task. Wrap a scripted agent in `session.record_attempts` and call it
once per outcome. Read the rows back with `ledger.attempts`. The returned
attempt and the raised attempt each carry a distinct floor.

**Criterion 7.** Use the `record` fixture and `fold`
(`tests/test_fold.py:16-18`). Append the legacy fact to the
`MemoryRecord` yourself, after opening a fourth attempt for it to close.
Assert the floors on the source ledger's rows as well as the folded ones.

**An existing test needs a floor.**
`test_every_task_fact_kind_folds_back_to_the_rows_its_write_made` asserts
every folded column is non-null (`tests/test_ledger_fold_task.py:209-227`).
Its `_close` helper (`:121-131`) passes no floor, so the new column reads
null and the test fails. Pass a non-null `cost_floor_usd_est` there.

**Criterion 8.** Follow
`test_a_ledger_that_predates_the_tool_column_gains_it`
(`tests/test_ledger.py:1286-1312`). Build the old file from `SCHEMA` with
the new column removed, and assert the two differ. Insert one attempt row
with a cost before opening it.

**Where the column's comment goes.** A comment above the last column of a
table breaks `DROP COLUMN` on SQLite 3.51.0
(`saffron/ledger.py:143-145`). If the new column is last in `attempts`,
put its comment below it, as `merged_head_sha`'s is.
