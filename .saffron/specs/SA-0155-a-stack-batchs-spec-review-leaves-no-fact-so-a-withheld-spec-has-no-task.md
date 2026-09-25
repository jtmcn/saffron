---
id: SA-0155
title: A stack batch's spec review leaves no fact, so a withheld spec has no task, no findings and no spend on record
type: feature
priority: 1
depends_on: [SA-0149]
touches:
  - saffron/batch.py
  - saffron/spec_review.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - tests/test_batch.py
  - tests/test_spec_review.py
  - tests/test_scheduler.py
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
  - saffron/intake.py
  - saffron/events.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_task.py
  - tests/test_cli.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_session.py
  - tests/test_report.py
  - tests/test_spec_loop_driver.py
budget_usd: 27
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      Given `review` and `mint`, `run_stack_batch` calls `mint` for each
      spec once, before its first review, whatever `task_id` its candidate
      carries. It never calls it for a spec refused before its review. A
      task the candidate names gets no review, no attempt and no state. A
      spec reviewed again after a `wait` keeps its task. A `mint` that raises
      counts as an abort, as a runner's raise does, and its spec is never
      reviewed. Each runner call for a reviewed spec gets the candidate with
      `task_id` set to that spec's task, both calls of a rerun after
      `RATE_LIMITED` included. A second batch on the same ledger mints the
      spec a new task. Given `review` and no `mint`, it raises `ValueError`
      and opens no batch row.
    witness: tests/test_batch.py::test_a_stack_batch_mints_each_reviewed_specs_task_before_its_first_review
  - claim: >-
      Each review that returns adds one attempt to the spec's minted task,
      in phase `SPEC_REVIEW`, with the session's cost,
      `session_id` and turns. Its subtype is `error` when the session
      carries an error, and `success` otherwise, whatever the route or the
      read's error. It adds
      one `spec_review` fact holding the review's number on that task from
      1, its route, the read's `block` and `block_sha256`, and the read's
      error. A review routed `escalate` ends the task `SPEC_WITHHELD`, one
      routed `error` ends it `GATE_ERROR`, one routed `wait` leaves it
      `RATE_LIMITED`, and one routed `run` leaves its state alone. A review
      that raises adds no attempt. It adds a `spec_review` fact routed
      `error`, with no block and an error of the exception's type and
      message, and ends the task `GATE_ERROR`. The witness drives each
      route, a raise, a text with no `json` block and no session error, and
      a candidate that carries an older task.
    witness: tests/test_batch.py::test_each_spec_review_is_a_fact_on_its_specs_minted_task
  - claim: >-
      `ledger.batch_spend` counts each review's cost once, and no run the
      stack batch did not review or start. The witness drives a spec that
      runs, one withheld, one whose review errored, one reviewed again after
      a `wait`, one run again after `RATE_LIMITED`, and one whose candidate
      carries an older task. A run minted outside the batch during a
      withheld spec's review is not counted. The older task's run stays
      with the earlier batch that holds it. The stack path attaches each
      minted task's run to tonight's batch right after the mint, before
      the first review. So a review's cost counts in `batch_spend` once its
      attempt closes, before the spec's next review runs.
      `Ledger.task_run` returns a task's `run_id`, and raises `ValueError`
      for a task that does not exist.
    witness: tests/test_batch.py::test_a_stack_batch_counts_each_spec_review_once_in_its_spend
  - claim: >-
      Folding the record rebuilds the `spec_reviews` rows as written. A fold
      into a fresh ledger whose task ids differ gives the same rows. A fold
      into the ledger that wrote them leaves them as they were.
      `fold_task` with a key and no facts removes that task's rows and no
      other. Each row's `n` is the fact's own.
    witness: tests/test_batch.py::test_the_spec_reviews_fold_back_from_the_record_alone
  - claim: >-
      `read_spec_review` carries the text of the last fenced `json` block
      as `block`, stripped, and `artifacts.hash_artifact` of it as
      `block_sha256`, whatever the route. Both are `None` when the text
      holds no `json` block. The witness drives a clean block, a block with
      a blocker, a session with an error, a session with `resets_at`, two
      blocks, a fence that is not `json`, no fence, and a `json` fence
      around text that is not JSON.
    witness: tests/test_spec_review.py::test_a_spec_review_carries_its_last_json_block_and_its_hash
  - claim: >-
      `build_queue` neither queues nor refuses a spec whose task at its
      current `spec_sha` is `SPEC_WITHHELD`. Once the spec is edited, it is
      queued again with no task to resume.
    witness: tests/test_scheduler.py::test_a_spec_withheld_at_this_sha_is_not_queued_until_it_is_edited
    mutant:
      file: saffron/scheduler.py
      find: '"SPEC_WITHHELD",'
      replace: ''
---

## Context

Backlog item **b-792ab2**, step 6 of its Done. It cites `DESIGN.md` §3.3,
§4.1 and §4.2.1. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:50-57`)
decides that spec review runs inside a stack batch, before each spec's
first cell. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design.
Section 4 says each escalation is a record fact (`:238-239`).

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Step 6 is three specs.** `SA-0149` routes each spec on its review,
through an injected `review` callable. This spec gives each review a task
and a record. The batch mints the spec's task before its review. So the
review and any escalation are facts on it. The review's cost then counts
against the batch. `SA-0156` builds the production `review`, a session
in a critic cell, and the `mint` that `saffron batch --stack` passes.
`SA-0168` has the cell run on the minted task.

**What the tree base holds.** This spec's tree base is `SA-0149`'s head.
The chain below it runs `SA-0135` and `SA-0136`, then `SA-0142` to
`SA-0145`, `SA-0146`, `SA-0153`, `SA-0154`, `SA-0147` and `SA-0148`.
Every line number below was read at `ec5e6989`. The chain edits
`batch.py`, `ledger.py`, `scheduler.py` and `tests/test_batch.py`, so read
those there by symbol. This spec consumes these names.

- From `SA-0135`: `Refused`. `_drive` counts a raise as an abort, and
  skips both the attach and the breaker's count for a `Refused`.
- From `SA-0143`: `run_stack_batch` and its runner wrapper, which hands a
  runner `(candidate, predecessor)`. A spec that reaches a miss through a
  `depends_on` entry is refused and never reaches the runner.
  `tests/test_batch.py`'s `_candidate` takes `depends_on`.
- From `SA-0145`: the `stack_layers` table, and its row deleted in
  `Ledger._drop_task_rows`.
- From `SA-0148`: `run_stack_batch`'s `sleep` keyword, and
  `CellOutcome.resets_at`. A `RATE_LIMITED` task waits and runs its spec
  again on the same predecessor.
- From `SA-0149`: `saffron/spec_review.py`, with `SpecReviewSession`,
  `SpecReview`, `read_spec_review` and `spec_review_route`.
  `run_stack_batch`'s `review` keyword. It reviews a spec inside the
  runner wrapper, keeps its route by spec id, and reviews it once. An
  `escalate` returns a `Refused`. An `error` raises. A `wait` goes through
  `SA-0148`'s wait and reviews the spec again.

**What a review leaves today, at the tree base.** Nothing. `SA-0149`'s
Out of scope says its review's cost reaches no ledger row. A task exists
only once `run_one_cell` mints one (`saffron/cell/session.py:1689-1705`),
so a withheld spec has none, and neither does a spec whose review raised.

**Where spend is read.** `ledger.batch_spend` sums `attempts.cost_usd_est`
over the tasks of the runs attached to the batch
(`saffron/ledger.py:897-912`). `_drive` attaches the outcome's run
(`saffron/batch.py:233`). After a raise it sweeps each run minted since
the call began (`:227`, `saffron/ledger.py:880-895`). A `Refused` gets
neither, from `SA-0135`.

**A stack batch mints a fresh task for every spec.** The operator decided
this on 2026-09-24, and it replaces the resume this spec first built.
§4.2.1 says a re-queued spec "resumes that task row" (`DESIGN.md:387`).
`build_queue` sets `Candidate.task_id` to that row
(`saffron/scheduler.py:792-794`). A plain `saffron batch` already mints a
new task for it, since `_batch_runner` passes the cell no task
(`saffron/cli.py:475-490`). Gate 0 exempts such a candidate
(`saffron/scheduler.py:650-656`). In stack mode the batch mints too,
whatever `task_id` the candidate carries, and leaves the older task's
state as it is. So every run, attempt and layer belongs to tonight's
batch, and `batch_spend` and every budget check stay exact.

**How a fact reaches the record.** Each write method builds one fact with
`_build_fact` and applies it through `_commit_and_append`
(`saffron/ledger.py:372-404`). `open_attempt` takes a `phase`
(`:1000-1023`), and `replay.py` passes one (`saffron/replay.py:88`).
`close_attempt` writes the cost and turns (`:1025-1049`). `set_task_state`
writes the state (`:992-998`). `fold_task` drops a task's rows and applies
its facts again (`:406-433`). `record_findings` numbers each fact on its
own task and carries the number in the payload (`:1143-1169`).

**Why the new state is done with the spec.** §4.2.1 queues a spec unless
its task at that `spec_sha` is done with it (`DESIGN.md:389`). It
re-queues "when nothing was learned about the spec". A blocker is
something learned. Running the same text again would meet the same
review. So `SPEC_WITHHELD`
joins `DONE_STATES` (`saffron/scheduler.py:68-81`), and an edit, a new
`spec_sha`, queues the spec again. A review that errored learned nothing.
`GATE_ERROR` already names "a verdict session never started"
(`DESIGN.md:273-276`), counts toward the breaker (`saffron/batch.py:49`),
and re-queues (`saffron/scheduler.py:108-116`).

**The vocabulary lands first, by hand.** `SPEC_WITHHELD` and
`spec_review` are in `ontology/factory.ttl`, `CONTEXT.md` and
`saffron/record/contract.py`'s `KINDS` at the tree base. No cell can add
a fact kind or a terminal state, and `KINDS` is held equal to the
ontology (`tests/ontology/test_vocabulary_agrees_with_code.py`). Commit
`75edb212` did the same for `stack_layer`.

## Problem

Build five things.

1. **The block on the read.** `SpecReview` gains `block: str | None` and
   `block_sha256: str | None`, as criterion 5 says. `SpecReviewSession`
   gains `session_id: str | None = None` and `num_turns: int = 0`, which
   the attempt row takes. `SA-0156` fills both from its session.
2. **The table and the fact.** Add `spec_reviews` to `SCHEMA` in
   `saffron/ledger.py`, with no reference to another table.

   | column | type |
   |---|---|
   | `task_key` | `TEXT NOT NULL` |
   | `n` | `INTEGER NOT NULL` |
   | `route` | `TEXT NOT NULL` |
   | `block` | `TEXT` |
   | `block_sha256` | `TEXT` |
   | `error` | `TEXT` |

   The primary key is `(task_key, n)`. Add
   `Ledger.record_spec_review(task_id, *, route, block, block_sha256,
   error)`. It numbers the review 1 more than the task's rows, and builds
   one `spec_review` fact with a payload of `n`, `route`, `block`,
   `block_sha256` and `error`. It writes through `_commit_and_append`.
   `_apply` places the fact as one row, every value from the fact.
   `_drop_task_rows` deletes the task's rows by its key.
3. **The mint.** Add a keyword `mint: Callable[[Candidate], int] | None =
   None` to `run_stack_batch`. It takes a candidate and returns the
   `task_id` of a task it created. The batch calls it for every candidate,
   whatever its `task_id`. Given `review` and no `mint`,
   `run_stack_batch` raises `ValueError` before it opens a batch row.
4. **The facts.** Around each review in the runner wrapper, as criteria
   1 and 2 say.
5. **The spend.** Add `Ledger.task_run(task_id)`, which returns the
   task's `run_id` and raises `ValueError` for a task that does not
   exist. The stack path reads the minted task's run with it, and
   attaches that run with `attach_run_to_batch`. It does so right after
   the mint, before the first review, so criterion 3 holds. `SA-0164`'s revision rounds
   read `batch_spend` inside one call, between reviews. The run is one `mint` created tonight with no batch,
   so the plain update is enough (`saffron/ledger.py:848-866`). `_drive`'s
   shared sweep stays as it is, after a raise alone, and `run_batch` does
   not change.

Also add `SPEC_WITHHELD` to `DONE_STATES`.

Three docstring sentences in `saffron/ledger.py` become false. Its count
of the kinds that fold back gains one. `SA-0145` names `stack_layers` as a
table §4.1 does not list, and `spec_reviews` joins it. `open_attempt` says
only `replay` passes a phase (`saffron/ledger.py:1003-1004`), and the batch
now does too. `saffron/record/fold.py:1-3` lists what the fold rebuilds
and becomes incomplete. That file is forbidden here, so the operator files
it.

## Out of scope

- **The production callables and the cell.** `SA-0156` builds the
  `review` and the `mint`. `SA-0168` runs the cell on the minted task. No caller in `saffron/` passes `review`
  or `mint` until then. `run_one_cell` still mints its own task
  (`saffron/cell/session.py:1689`), and `run_task` reads no
  `candidate.task_id` (`saffron/task.py:218-383`).
- **The morning page.** A withheld spec never reaches `run_task`, so it
  appends no queue line (`saffron/task.py:364`). `_STATE_RANK` and a
  stack view with escalations are `SA-0152`'s.
- **The minted run's status.** It stays `RUNNING` (`saffron/ledger.py:775`),
  as every run a fold rebuilds does (`:470`). Nothing reads the column.
- **`resets_at` on the fact.** A cell supplies it, and SQLite's `INTEGER`
  holds 64 bits. `10**20` raised `OverflowError` on insert, measured on
  the host on 2026-09-23. The route `wait` says the rest.
- **`batch_key` on the table.** The attach precedes the first review, so
  each `spec_review` fact's envelope now carries the batch's key. The
  table still keeps none. A task hangs from one run, and the run names
  its batch. A column would restate that join, and could disagree with
  it after a fold.
- **Revision rounds.** They are `SA-0164`'s.
- **The vocabulary.** `SPEC_WITHHELD` and `spec_review` are at the tree
  base. The phase label `SPEC_REVIEW` joins backlog item b-466005.

## Notes for the agent

**Criteria 1 to 5 are new code.** No text at the tree base mints a task
for a review or places a `spec_review` fact. So criteria 1 to 5 declare a
witness and no mutant, and `witness` reports `skip` for them. Criterion 6
edits an existing set, so it declares a mutant. It deletes the member as
`ruff format` writes one in that set.

**Every witness fails with the source reverted.** Criteria 1 to 4 pass
`mint=` to `run_stack_batch`, which the tree base does not take. Criterion
5 reads `block`, which `SpecReview` lacks there. Criterion 6's spec is
queued there, measured below. Import `spec_review`'s names inside each
test body, as `SA-0149`'s witnesses do.

**One way to build it.** In the wrapper, before a spec's first review,
call `mint`, whatever the candidate's `task_id`. Keep the
task id by spec id, beside `SA-0149`'s route. Keep both per call of
`run_stack_batch`, never at module scope. Then attach that task's run to
the batch. How the stack path learns the batch id is your choice, as it
was for `SA-0145`'s layer record. Around `review`, catch any exception,
record it, set the state, and raise it again. `_drive` then counts the
abort and `SA-0143` counts the miss. Hand the runner
`dataclasses.replace(candidate, task_id=...)`.

**Why not a sweep in `_drive`.** `_drive` sweeps runs minted since a call
began only after a raise (`saffron/batch.py:227`). A sweep after every
call would also run in `run_batch`, and would attach a run another
process minted meanwhile, such as an attended `saffron cell`. So the
stack path attaches only the task it reviewed.

**Update `SA-0149`'s four loop witnesses.** Each calls `run_stack_batch`
with `review`, so each now raises `ValueError`. Pass each the shared mint
double, built with no ids to raise on, and change nothing else. Its log is
its own, so their review lists do not change. They are
`test_a_stack_batch_runs_a_spec_only_when_its_own_review_routes_it_to_run`,
`test_a_spec_run_again_after_a_rate_limit_keeps_its_first_review`,
`test_a_spec_review_that_raises_or_errors_counts_toward_the_breaker` and
`test_a_rate_limited_spec_review_waits_and_reviews_again`.

**Criteria 1 to 4 share one arrangement.** Write it once in
`tests/test_batch.py`. It uses a `Ledger` built with a `MemoryRecord`. The
`repo_id` fixture belongs to the `ledger` fixture, which has no record. So
open the `MemoryRecord` ledger on that fixture's file, or add a repo of its
own. It also takes `_ready`, a budget of 100 and
`until=None`. Use `SA-0148`'s clock and a fake `sleep`.

- **The mint double** is a class shared with `SA-0149`'s witnesses. It
  takes the ledger, the repo id and a set of spec ids to raise on. Each
  call appends the spec id to its own log. For an id in the set it raises
  `RuntimeError`. Otherwise it creates a run on the repo at `"a" * 40`
  and a task for the spec id, and returns the task id.
- **The review double** records `(spec id, length of the mint log)` and
  returns or raises what the table says, in turn. For a spec the table
  gives no review, it raises `AssertionError`. Each clean or blocker
  text is a `json.dumps` inside a fenced `json` block. On each call it
  also records the batch that holds the run of the spec's newest task.
  For `TE-5` it also records `batch_spend` of the newest batch. For
  `TE-2` it also creates an unrelated run and task with one closed
  attempt at $8, as an attended `saffron cell` would meanwhile.
- **The runner double** records `(spec id, candidate.task_id)`. It mints
  its own run and task with one closed attempt at $1, as `SA-0149`'s
  does, and returns `_outcome(...)` with that call's run and task.

Before the batch, create an earlier batch, and an older task for `TE-7`
on a run in that batch. Give it one closed attempt at $2, and end it
`GATE_ERROR`.
Build `TE-7`'s candidate with `dataclasses.replace(_candidate("TE-7"),
task_id=<that task>)`, as a scan that re-queued it would. The mint double
raises on `TE-80` alone.

| order | spec | `depends_on` | reviews in turn | runner returns |
|---|---|---|---|---|
| 1 | `TE-1` | none | clean, cost 0.5, `session_id` `s-1`, 7 turns | `READY_FOR_REVIEW` |
| 2 | `TE-2` | none | one `scope` blocker, cost 0.25 | never called |
| 3 | `TE-3` | `TE-2` | never called | never called |
| 4 | `TE-4` | none | `error` `cell died`, text a clean block, cost 0.125 | never called |
| 5 | `TE-5` | none | no fence and `resets_at` 60 seconds on, cost 0.0625, then clean, cost 0.03125 | `RATE_LIMITED` resetting 60 seconds on, then `READY_FOR_REVIEW` |
| 6 | `TE-6` | none | raises `RuntimeError("critic cell would not start")` | never called |
| 7 | `TE-7` | none, `task_id` the older task | clean, cost 0.75 | `RATE_LIMITED` resetting 60 seconds on, then `READY_FOR_REVIEW` |
| 8 | `TE-9` | none | `text` with no fence and no error, cost 0.015625 | never called |
| 9 | `TE-80` | none | never called | never called |
| 10 | `TE-81` | none | never called | never called |

The costs are powers of two, so each sum is exact in binary. The breaker
counts 1 at `TE-4` and `TE-6`, and a layer resets it after each. It
counts 1 at `TE-9` and 2 at `TE-80`, so the batch stops `INFRASTRUCTURE`
before `TE-81`.

**Criterion 1's witness** asserts the stop reason `INFRASTRUCTURE`. The
mint log is exactly `TE-1`, `TE-2`, `TE-4`, `TE-5`, `TE-6`, `TE-7`,
`TE-9` and `TE-80`. The review pairs are exactly `(TE-1, 1)`,
`(TE-2, 2)`, `(TE-4, 3)`, `(TE-5, 4)`, `(TE-5, 4)`, `(TE-6, 5)`,
`(TE-7, 6)` and `(TE-9, 7)`. Exactly one emitted line starts with `TE-80` padded to ten
and holds `raised RuntimeError`. The runner's pairs are `TE-1`, `TE-5`,
`TE-5`, `TE-7` and `TE-7`. Each gets the task its mint returned, one
task for both of `TE-7`'s calls, and never the older task. It then runs
a second batch on the same ledger with `TE-1` alone. Its mint log is
`TE-1`, and that task's one `spec_review` fact has `n` 1. Last, a call
with `review` and no `mint` raises `ValueError`, and the count of
`batches` rows is unchanged. These fail it:

- a mint after the review, which leaves `TE-6` with no task
- a mint on every review, which mints `TE-5` twice
- a mint on every runner call, which mints `TE-5` and `TE-7` again
- no mint for a candidate that carries a `task_id`, which reviews and
  runs `TE-7` on the older task
- a task minted for every spec at batch start, which mints `TE-3`
- a review called after its mint raised
- a mint's raise turned into a `Refused`, which mints and reviews `TE-81`
- the task handed to the first runner call only, which hands `TE-5`'s
  second call `None`
- a store of minted tasks at module scope, which mints nothing in the
  second batch

**Criterion 2's witness** reads each reviewed task's `spec_review` facts
from the record, under `ledger.record_key(task_id)`, and its attempts and
state from the ledger. Each attempt is in phase `SPEC_REVIEW`, with
`session_id` `None` and 0 turns unless the row says otherwise.

| spec | `n` and route | state | attempts: cost and subtype |
|---|---|---|---|
| `TE-1` | 1 `run` | `QUEUED` | 0.5 `success`, `s-1`, 7 turns |
| `TE-2` | 1 `escalate` | `SPEC_WITHHELD` | 0.25 `success` |
| `TE-4` | 1 `error` | `GATE_ERROR` | 0.125 `error` |
| `TE-5` | 1 `wait`, 2 `run` | `RATE_LIMITED` | 0.0625 `success`, then 0.03125 `success` |
| `TE-6` | 1 `error` | `GATE_ERROR` | none |
| `TE-7`, its minted task | 1 `run` | `QUEUED` | 0.75 `success` |
| `TE-9` | 1 `error` | `GATE_ERROR` | 0.015625 `success` |

The older task keeps `GATE_ERROR`, its one attempt and no `spec_review`
fact.

`TE-2`'s `block` is the `json.dumps` text the double fenced, and its
`block_sha256` is `hash_artifact` of that text. `TE-4`'s `block` is its
clean text, and its error holds `cell died`. `TE-6`'s `block` and
`block_sha256` are `None`, and its error is exactly
`RuntimeError: critic cell would not start`. Each `run` fact's error is
`None`. These fail it:

- no state for a withheld task, which leaves `TE-2` `QUEUED`
- no state after an `error` route, or `SPEC_WITHHELD` for it
- no state after a `wait`, which leaves `TE-5` `QUEUED`
- a raise that records nothing, which leaves `TE-6` `QUEUED`
- an attempt opened before the review, which leaves one on `TE-6`
- a review numbered across the ledger, which gives `TE-2` 2
- a `block` dropped for a session that carries an error
- a subtype keyed on the route, which gives `TE-9` `error`
- a subtype keyed on the read's error, which gives `TE-5`'s first
  attempt `error`
- an attempt with a fixed `session_id` or turn count

**Criterion 3's witness** asserts `ledger.batch_spend` of the first batch
is exactly 6.734375. That is seven review costs, 1.734375, and five
runner calls at $1. The $8 run is not in it. The earlier batch's spend is
exactly 2.0, the older task's attempt. Every batch the review double
recorded is tonight's. At `TE-5`'s second review, `batch_spend` is
exactly 1.9375, which holds `TE-5`'s first review's 0.0625. Last,
`ledger.task_run` of a task id no row holds raises `ValueError`. These
fail it, each measured:

- a missing task read as run 0, measured in `SA-0168`'s prototype

- the build `attached when the wrapper returns`. A first review then runs
  on a run tonight's batch does not yet hold.
- no attach on the stack path, which gives 5.140625
- no mint for a candidate that carries a `task_id`, with the plain attach,
  which gives 8.734375 and leaves the earlier batch 0.0
- the same with an attach that keeps a run's batch, which gives 5.984375
  and leaves the earlier batch 2.75
- a sweep after every call in the shared `_drive`, which gives 14.734375
- the review's attempt added again on a rerun
- no attempt for a review

**Criterion 4's witness** runs the arrangement, then reads the
`spec_reviews` rows ordered by `task_key` and `n`. It takes `TE-5`'s
record key now. A later fold drops and inserts each task again, so a key
looked up afterwards by the old `task_id` names another task. It opens a
fresh `Ledger` with no record, and creates one unrelated repo, run and
task there first. It folds the record into it and asserts the same rows.
It folds the record into the source ledger and asserts its rows are
unchanged. It calls `fold_task` on the fresh ledger with `TE-5`'s key
and an empty list. `TE-5`'s two rows are gone, and every other row
stays. Last, it calls `fold_task` there with `TE-5`'s facts less its
first `spec_review` fact. `TE-5`'s one row then has `n` 2. These fail it:

- `_apply` with no branch for `spec_review`, which raises at the first
  review, since the live write applies the fact too
- `_drop_task_rows` that leaves the rows, which raises on the primary key
- `INSERT OR REPLACE` with `_drop_task_rows` untouched, which leaves
  `TE-5`'s rows after `fold_task(key, [])`
- an `n` counted from the rows in `_apply`, which gives the last row 1

**Criterion 5's witness** builds each session as `SA-0149`'s witness
does, and asserts `block` and `block_sha256` on the read. Write the clean
block as `{"findings":  []}`, with two spaces, so a block serialised again
reads differently.

| session | `block` |
|---|---|
| a clean block | its text |
| a block with a `blocker` | its text |
| `error` set, text a clean block | its text |
| `resets_at` set, text a clean block | its text |
| a block with a `blocker`, then a clean block | the clean block's text |
| a clean block fenced as `text` | `None` |
| text with no fence | `None` |
| a `json` fence around `not json` | `not json` |

These fail it:

- the first block in place of the last
- the parsed block serialised again with `json.dumps`
- the hash of the whole text
- a `block` set for the `run` route alone
- a `block` of `None` for text that does not parse

**Criterion 6's witness** follows `test_a_spec_done_at_this_sha_is_not_queued`
(`tests/test_scheduler.py:256-267`). It writes `TE-1`, and adds a task at
its `spec_sha` ended `SPEC_WITHHELD`. It asserts `build_queue` returns no
candidate and no refusal. It then rewrites `TE-1` with a changed body, and
asserts `TE-1` is the one candidate, with `task_id` `None`. These fail it:

- the state left out of `DONE_STATES`, which queues `TE-1`
- the state added to `REQUEUE_STATES`, which queues `TE-1` with its task

**How the lists were measured.** A throwaway model ran criteria 1 to 4
on 2026-09-23 against a real `Ledger` with a `MemoryRecord`, at
`ec5e6989`. It modelled `SA-0143`'s refusal, `SA-0148`'s rerun and
`SA-0149`'s routing, and subclassed `Ledger` with the table. The right
build passed all four. Each wrong build under criteria 1 to 4 failed at
least one, with the failure named. Criterion 6's two wrong builds and the
tree base were run with the real `build_queue`, patching the two sets. The
tree base and both wrong builds queued `TE-1` on the first scan. The tree
base is what the mutant leaves. Criterion
5 is unmeasured, since the read does not exist at `c9d46ca8`.

**Measured again under the operator's decision.** A second throwaway
model ran criteria 1 to 3 on 2026-09-24 at `f2a08a9f`, with the mint for
every candidate. It used a real `Ledger` with a `MemoryRecord`, and stood
in for `record_spec_review`, and modelled when the run is attached. The
right build passed. Each wrong build under criteria 1 and 3 failed, with
the figures above. The older task
kept its state and its one attempt.

**What the witnesses leave undriven.** A `RATE_LIMITED` rerun whose spec
was reviewed again is not driven, since `SA-0149` reviews it once. A cost
of `NaN`, or one too large for a float, is not driven. `record_attempts`
takes a turn's cost as it comes (`saffron/cell/session.py:184-208`), and
`SA-0156` fills this one.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`).
`batch.py` changes about 50 lines at 6.6 tokens a line, and `ledger.py`
about 55 at 4.8. `spec_review.py` changes about 10 at 5.3, and
`scheduler.py` 3. That source comes to about 660 tokens. The tests add
about 240 lines to `tests/test_batch.py` at 3.3, and 35 to
`tests/test_spec_review.py` at 4.7. They add 22 to
`tests/test_scheduler.py` at 3.4. That is about 1030 tokens of test, and
about 1690 in all.
