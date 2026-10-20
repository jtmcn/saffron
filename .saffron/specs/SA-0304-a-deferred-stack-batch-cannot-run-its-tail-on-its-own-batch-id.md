---
id: SA-0304
title: A deferred stack batch cannot run its end review, follow-ups and finish later on its own batch id
type: feature
priority: 2
depends_on: [SA-0301]
estimated_lines: 350
touches:
  - saffron/batch.py
  - tests/test_batch.py
pending_symbols:
  - saffron/batch.py::StackResume
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
  - hooks/**
  - saffron/cli.py
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/qualify.py
  - saffron/finish.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/report/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/record/**
  - tests/test_cli.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 28
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      Handed a `StackResume` for a closed batch whose stop reason is
      `DRAINED`, and an empty order, `run_stack_batch` creates no batch row
      and never calls `readiness_check`. It hands `end_review` the resume's
      batch id as a string, its own `reserve_usd` and the resume's specs.
      It hands `follow_ups` that same id and drives the follow-ups it
      returns. The first
      follow-up's predecessor is `resume.top`. The first follow-up layer is
      recorded under the resumed batch at `resume.position + 1`, generation
      1, with the top layer's task as its predecessor. Gate 0 exempts
      `resume.layer_branches`. A follow-up's revision weighs the resumed
      batch's spend, even when a later batch row exists. `finish` gets the
      resumed batch id. The resumed batch's row closes again with the
      follow-ups' stop reason and the spend that stands then. A later
      batch's row is left as it was.
    witness: tests/test_batch.py::test_a_resumed_stack_batch_runs_its_tail_on_the_closed_batchs_own_id
    wrong_versions:
      - "`create_batch` still runs under a resume, so the tail lands on a new row."
      - "`end_review` or `follow_ups` is still handed `ledger.latest_batch_id()`, which names the later batch."
      - "The revision's budget still reads `ledger.latest_batch_id()`'s spend, so a later empty batch lets the revision run."
      - "The predecessor is not seeded, so the first follow-up runs with no predecessor."
      - "`position` starts at 0, so the first follow-up layer is recorded at position 1."
      - "The predecessor task id is not seeded, so the first follow-up layer names no predecessor."
      - "`layer_branches` starts empty, so the follow-up overlapping the top layer's pull request is refused."
      - "The row closes with the resume's original reason although the follow-ups stopped on `BUDGET`."
      - "The resume calls `readiness_check` before its end review."
  - claim: >-
      For each original stop reason `BUDGET`, `UNTIL`, `INFRASTRUCTURE` and
      `INCOMPLETE`, a resume still calls `end_review` and `follow_ups`.
      It drives none of the follow-ups and prints the `follow-ups unrun`
      line. It hands `finish` the task id of each follow-up. It returns
      that original reason and closes the resumed batch's row with it.
    witness: tests/test_batch.py::test_a_resumed_stack_batch_drives_no_follow_up_after_a_stop_other_than_drained
    wrong_versions:
      - "Follow-ups are driven whatever the original stop reason."
      - "Follow-ups are driven unless the original reason is `INFRASTRUCTURE`, so an `INCOMPLETE` batch drives them."
      - "The row closes `DRAINED` because no follow-up pass ran."
      - "`finish` is handed an empty list, so the unrun follow-ups are lost."
  - claim: >-
      When `end_review`, `follow_ups` or `finish` raises during a resume,
      the raise leaves `run_stack_batch`. The resumed batch's row closes
      again with its original stop reason, never `INFRASTRUCTURE`, and
      with the spend that stands then. No batch row is created.
    witness: tests/test_batch.py::test_a_resumed_stack_batch_that_raises_keeps_its_original_stop_reason
    wrong_versions:
      - "The `finally` closes the row `INFRASTRUCTURE`, as a batch's own raise does."
      - "The row is left untouched on a raise, so its spend omits what the tail spent."
      - "The raise is swallowed and the tail's reason returned."
  - claim: >-
      `run_stack_batch` raises `ValueError` before any callable runs and
      any batch row is written in three cases. The resume comes with a
      non-empty order, or with a `budget_usd` other than the resume's
      own, or with a top layer whose `task_id` is `None`.
    witness: tests/test_batch.py::test_a_resume_with_an_order_another_budget_or_no_top_task_raises_before_anything_runs
    wrong_versions:
      - "A non-empty order is driven before the tail."
      - "The positional budget is used and the resume's ignored."
      - "A top layer with no task id records the first follow-up layer with no predecessor."
  - claim: >-
      Without a resume, `end_review` is still handed the batch's own id,
      the reserve and the order's specs.
    witness: tests/test_batch.py::test_a_stack_batch_holds_its_end_review_reserve_and_calls_it_once_the_loop_returns
    preserves: true
  - claim: >-
      Without a resume, follow-ups still run on the order's last layer as
      generation 1 layers.
    witness: tests/test_batch.py::test_a_stack_batch_runs_its_follow_ups_on_top_as_generation_one_layers
    preserves: true
  - claim: >-
      Without a resume, `finish` still gets the batch's own id while its
      row is open.
    witness: tests/test_batch.py::test_the_finish_runs_once_after_the_follow_ups_while_the_batch_row_is_open
    preserves: true
  - claim: >-
      Without a resume, a raise from `end_review` or `follow_ups` still
      closes the row `INFRASTRUCTURE`.
    witness: tests/test_batch.py::test_a_stack_batch_closes_its_row_once_after_its_follow_ups_or_their_raise
    preserves: true
  - claim: >-
      Without a resume, a revision is still refused once the batch's
      budget left cannot pay for it.
    witness: tests/test_batch.py::test_a_revision_waits_on_a_rate_limit_and_stops_on_an_error_a_raise_or_the_budget
    preserves: true
---

## Context

Backlog item **b-8a0c9a**. A stack batch's end review grades the heads
PACKAGE pushed, before the loop's review commits land. `SA-0301` lets a
`--stack` batch end before its end review and write `deferred.json`.
`SA-0305` adds `saffron finish <batch id> --repo .`, which runs the end
review later. This spec gives that command the batch loop's own tail to
call. It is the fourth of the five specs `SA-0301`'s notes lay out.

**The tail runs inside the call that created the batch.**
`run_stack_batch` creates its row at `saffron/batch.py:829`. After the
order's `_drive` returns, it calls `end_review` (`:852-865`), then
`follow_ups` (`:866-869`). It drives their return only when the order's
own reason is `DRAINED` (`:872`). It then calls `finish` (`:908-909`) and
closes the row through `_stop` (`:910`). A raise closes the row
`INFRASTRUCTURE` in the `finally` (`:911-914`).

**Four reads name the batch by the newest row.** `ledger.latest_batch_id()`
returns the highest `batch_id` (`saffron/ledger.py:1337-1345`).
`run_stack_batch` reads it to attach a minted task's run (`:594-596`) and
to weigh a revision's budget (`:747-751`). It also hands `end_review` and
`follow_ups` their key from it (`:864`, `:868`). A finish run days later
sees a newer batch there.

**The follow-up pass starts from the order's state.** `record_layer`
reads `position` and `predecessor_task_id` (`:522-534`). `wrapped` reads
`predecessor` (`:557`) and the exempt set `layer_branches` (`:600-602`).
The order's pass sets all four. `consecutive_aborts` carries the order's
count into the follow-ups' `_drive` (`:894`).

## Problem

Nothing can run a closed stack batch's tail on that batch's id.

Add a frozen dataclass `StackResume` to `saffron/batch.py`. Its fields are
`batch_id: int`, `budget_usd: float`, `stop_reason: StopReason`,
`top: Candidate`, `position: int`, `layer_branches: frozenset[str]` and
`specs: Mapping[str, Spec]`. Add `resume: StackResume | None = None` to
`run_stack_batch`'s keywords.

With a resume, `run_stack_batch` checks the three cases of criterion 4
first. It creates no row and drives no order. Its batch id is
`resume.batch_id`, and its reason starts as `resume.stop_reason`. The
follow-up pass starts from `resume.top` as the predecessor,
`resume.top.task_id` as the predecessor task, `resume.position` and
`set(resume.layer_branches)`, with no standing aborts. `end_review` gets
`resume.specs` in place of the specs built from the order. Every read of
`ledger.latest_batch_id()` in `run_stack_batch` becomes the batch id it
holds, with or without a resume. A raise under a resume closes the row
with `resume.stop_reason`.

**The tail's reason.** A resume returns and records the follow-ups'
`_drive` reason when they are driven, through `_stop` as today. Otherwise
it returns and records `resume.stop_reason`. Follow-ups are driven only
when that is `DRAINED`, the rule at `:872`.

## Out of scope

- **`saffron finish` itself**, reading `deferred.json` and the ledger, and
  building the adapters. `SA-0305` does that and calls this.
- **Grading current heads.** `SA-0302` and `SA-0303`.
- **A ledger accessor for a batch's status, budget or `until_ts`.**
  `saffron/ledger.py` is `elevate_on`. `SA-0305` reads the row.
- **`write_stack_view`'s own `latest_batch_id()`**
  (`saffron/report/stack.py:272`). It is `cli.py`'s call, after the batch.

## Notes for the agent

**New code, so no criterion declares a mutant.** The resume path does not
exist at base. `witness` will report `skip` for criteria 1 to 4. The
`latest_batch_id()` reads change no behaviour without a resume, which the
five `preserves` witnesses hold.

**Where `SA-0305` finds each field.** `deferred.json` (`SA-0301`) holds
`batch_id`, `reserve_usd`, `writer_usd` and `specs`. The rest come from
the ledger. `budget_usd` and `stop_reason` are the batch row's
`budget_usd` and `status`. `top` and `position` are the highest row of
`ledger.stack_layers(batch_id)`, with `top.spec` taken from `specs`. The
runner reads only `predecessor.spec.id` (`saffron/cli.py:677`).
`layer_branches` is `_branch(spec_id)` of each layer, plus the stack
base's branch. The stack base is the task named by the position 1 row's
`predecessor_key`. Nothing the resume needs is in neither place.

**Why `status` and not the order's own reason.** The row holds `_stop`'s
result (`:930-937`). It turns a drained order that left a task in flight
into `INCOMPLETE`. The in-batch path gates on `_drive`'s reason
before that turn (`:872`). So a deferred `INCOMPLETE` batch drives no
follow-ups on resume, where the in-batch path would have. This is a
deliberate, conservative difference. Criterion 2 drives `INCOMPLETE` and
criterion 1 drives `DRAINED`.

**`until`.** The tail meets only the `until` its caller hands. The row's
`until_ts` is not read. The in-batch end review runs after an `UNTIL`
stop too, so a resume after one still runs its end review.

**Where the original stop reason stays.** On the row, unless follow-ups
are driven. Those run only after `DRAINED`, so a row the follow-ups
closed held `DRAINED` before them, as an in-batch row does. A raise keeps it
on the row, unlike a batch's own raise. The row of a resume was already
closed, and its stop reason is the night's. The raise itself reaches
`SA-0305`, which exits on it.

**The standing aborts are not carried.** The row holds no count, so the
follow-ups start at zero. A drained order ends with fewer than two.

**The witnesses.** They call `run_stack_batch` directly with
distinct `reserve_usd` and `writer_usd`, so no share needs patching. Import `StackResume` and `run_stack_batch` inside each
test body, never at module scope, so each fails in its body at base. Use
`StackDoubles` (`tests/test_batch.py:5158`) and one small helper that
creates and closes a batch row with a given reason. The helper mints the
top layer's task on a run of that batch, with an attempt costing 13.0.
The resume's budget is 40.0, its position 2, its top spec `TE-2`, and its
`layer_branches` `{"saffron/TE-2"}`. Pass `reserve_usd` and `writer_usd`
as 6.0 and 2.0, so a swap between them shows.

- **The first** creates a second, later batch row after the helper's, with
  no spend. `follow_ups` returns three, in order. `TE-32` routes `revise`.
  The resumed batch's 13.0 leaves 27.0, under the 27.5 a writer, a review
  and its budget need, so it is refused `unrevised`. `TE-31` touches
  `f.py`, which an open pull request on `saffron/TE-2` also touches.
  `TE-33` costs 100.0, so the pass stops `BUDGET`. Assert the batch count
  is unchanged and a recording `readiness_check` never ran. Assert
  `end_review` got the resumed id, 6.0 and the resume's specs, and
  `follow_ups` the resumed id. Assert that `revise` never ran and
  `TE-31` ran on `TE-2`. Assert its layer row, `finish`'s arguments, the
  resumed row's `BUDGET` and 14.0, and the later row unchanged.
- **The second** loops over the four reasons, a fresh closed batch each,
  with `follow_ups` returning one candidate.
- **The third** loops over the three callables. Each raising one first
  attaches a run costing 2.0 to the resumed batch. The original reason is
  `UNTIL`. Assert the raise, the row's `UNTIL` and 15.0, and the batch count.
- **The fourth** drives each of its three cases and asserts no callable
  ran and the batch count and the row are unchanged.

**The docstring.** `run_stack_batch`'s docstring is at nine lines, and the
`prose` gate caps one at ten. Put the resume's account in `StackResume`'s
docstring. New comments and docstrings take no em dash, semicolon,
contraction, perfect tense or sentence over 25 words.

**`pending_symbols`.** Only `SA-0305` constructs `StackResume` outside the
tests, so the `dead` gate defers it until then.

**Size.** About 70 lines in `saffron/batch.py` and four witnesses with a
helper, about 280 lines.
