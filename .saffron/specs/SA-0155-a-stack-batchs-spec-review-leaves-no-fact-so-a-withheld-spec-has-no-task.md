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
max_turns: 160
acceptance:
  - claim: >-
      Given `review` and `mint`, `run_stack_batch` calls `mint` for a spec
      once, before its first review, and never for a spec it refuses. A spec
      reviewed again after a `wait` keeps the task it was minted. A `mint`
      that raises reaches `_drive` as a runner's raise does, and its spec is
      never reviewed. Each
      runner call for a reviewed spec gets the candidate with `task_id` set
      to the minted task, both calls of a rerun after `RATE_LIMITED`
      included, never the `task_id` the scan set. A second batch on the same
      ledger mints the spec a new task. Given `review` and no `mint`, it
      raises `ValueError` and opens no batch row.
    witness: tests/test_batch.py::test_a_stack_batch_mints_each_reviewed_specs_task_before_its_first_review
  - claim: >-
      Each review that returns adds one attempt to the spec's minted task,
      in phase `SPEC_REVIEW`, with the session's cost, `session_id` and
      turns. Its subtype is `error` when the session carries an error, and
      `success` otherwise. It adds
      one `spec_review` fact holding the review's number on that task from
      1, its route, the read's `block` and `block_sha256`, and the read's
      error. A review routed `escalate` ends the task `SPEC_WITHHELD`, one
      routed `error` ends it `GATE_ERROR`, one routed `wait` leaves it
      `RATE_LIMITED`, and one routed `run` leaves its state alone. A review
      that raises adds no attempt. It adds a `spec_review` fact routed
      `error`, with no block and an error of the exception's type and
      message, and ends the task `GATE_ERROR`. The witness drives each
      route and a raise.
    witness: tests/test_batch.py::test_each_spec_review_is_a_fact_on_its_specs_minted_task
  - claim: >-
      `ledger.batch_spend` counts each review's cost once. The witness
      drives a spec that runs, one withheld, one whose review errored, one
      reviewed again after a `wait`, and one run again after `RATE_LIMITED`.
    witness: tests/test_batch.py::test_a_stack_batch_counts_each_spec_review_once_in_its_spend
  - claim: >-
      Folding the record rebuilds the `spec_reviews` rows as written. A fold
      into a fresh ledger whose task ids differ gives the same rows. A fold
      into the ledger that wrote them leaves them as they were.
      `fold_task` with a key and no facts removes that task's rows and no
      other.
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
in a critic cell, and the `mint` that `saffron batch --stack` passes. It
also has the cell run on the minted task.

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
   `task_id` of a task it created. Given `review` and no `mint`,
   `run_stack_batch` raises `ValueError` before it opens a batch row.
4. **The facts.** Around each review in the runner wrapper, as criteria
   1 and 2 say.
5. **The spend.** Every run a runner call mints is attached to the batch,
   whatever the call returns, so criterion 3 holds.

Also add `SPEC_WITHHELD` to `DONE_STATES`.

Two docstring sentences in `saffron/ledger.py` become false. Its count of
the kinds that fold back gains one. `SA-0145` names `stack_layers` as a
table §4.1 does not list, and `spec_reviews` joins it.

## Out of scope

- **The production `review` and `mint`, and the cell on the minted
  task.** They are `SA-0156`'s. No caller in `saffron/` passes `review`
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
- **`batch_key` on the table.** The fact is built before `_drive`
  attaches the run, so it carries none, the trap `SA-0145` names.
- **Revision rounds.** They are `SA-0150`'s.
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

**One way to build it.** Call `mint` in the wrapper before a spec's first
review. Keep the task id by spec id, beside `SA-0149`'s route. Keep both
per call of `run_stack_batch`, never at module scope. Around `review`, catch any exception, record it, set the state, and raise
it again, so `_drive` counts the abort and `SA-0143` counts the miss. Hand
the runner `dataclasses.replace(candidate, task_id=...)`. For the spend,
`_drive` can sweep with `attach_orphan_runs_to_batch(batch_id, high_water)`
after every runner call, not only after a raise. `run_batch` then sweeps
too, and finds nothing, since `run_one_cell`'s run is the outcome's.

**This narrows one of `SA-0135`'s claims.** Its criterion 7 says a batch
whose runner returns a `Refused` attaches no run. `run_task` mints no run
before it refuses, so that stays true of `run_batch`. A withheld spec's
wrapper minted one on purpose, and its review's cost is on it. If
`test_a_batch_steps_over_a_refused_task` fails under the sweep, its
refusing runner mints a run. Then attach the minted run on the stack path
alone, and say so in your notes.

**Update `SA-0149`'s four loop witnesses.** Each calls `run_stack_batch`
with `review`, so each now raises `ValueError`. Pass them the shared mint
double below and change nothing else. They are
`test_a_stack_batch_runs_a_spec_only_when_its_own_review_routes_it_to_run`,
`test_a_spec_run_again_after_a_rate_limit_keeps_its_first_review`,
`test_a_spec_review_that_raises_or_errors_counts_toward_the_breaker` and
`test_a_rate_limited_spec_review_waits_and_reviews_again`.

**Criteria 1 to 4 share one arrangement.** Write it once in
`tests/test_batch.py`. It uses a `Ledger` built with a `MemoryRecord`, and
the `repo_id` fixture. It also takes `_ready`, a budget of 100 and
`until=None`. Use `SA-0148`'s clock and a fake `sleep`.

- **The mint double** appends `("mint", spec id)` to a call log shared
  with the review double. It creates a run on the repo at `"a" * 40` and
  a task for the spec id, and returns the task id. For `TE-8` it raises
  `RuntimeError`.
- **The review double** appends `("review", spec id)` to that log and
  returns or raises what the table says, in turn. Each clean or blocker
  text is a `json.dumps` inside a fenced `json` block.
- **The runner double** records `(spec id, candidate.task_id)`. It mints
  its own run and task with one closed attempt at $1, as `SA-0149`'s
  does, and returns `_outcome(...)` with that call's run and task.

Before the batch, create an older task for `TE-7` and end it `GATE_ERROR`.
Build `TE-7`'s candidate with `dataclasses.replace(_candidate("TE-7"),
task_id=<that task>)`, as a scan that found it would.

| order | spec | `depends_on` | reviews in turn | runner returns |
|---|---|---|---|---|
| 1 | `TE-1` | none | clean, cost 0.5, `session_id` `s-1`, 7 turns | `READY_FOR_REVIEW` |
| 2 | `TE-2` | none | one `scope` blocker, cost 0.25 | never called |
| 3 | `TE-3` | `TE-2` | never called | never called |
| 4 | `TE-4` | none | `error` `cell died`, text a clean block, cost 0.125 | never called |
| 5 | `TE-5` | none | no fence and `resets_at` 60 seconds on, cost 0.0625, then clean, cost 0.03125 | `READY_FOR_REVIEW` |
| 6 | `TE-6` | none | raises `RuntimeError("review cell would not start")` | never called |
| 7 | `TE-7` | none | clean, cost 0.75 | `RATE_LIMITED` resetting 60 seconds on, then `READY_FOR_REVIEW` |
| 8 | `TE-8` | none | never called | never called |

The costs are powers of two, so each sum is exact in binary. The
breaker counts 1 at `TE-4`, `TE-6` and `TE-8`, and a layer resets it
between each, so the stop reason is `DRAINED`.

**Criterion 1's witness** asserts the call log is exactly
`(mint, TE-1)`, `(review, TE-1)`, `(mint, TE-2)`, `(review, TE-2)`,
`(mint, TE-4)`, `(review, TE-4)`, `(mint, TE-5)`, `(review, TE-5)`,
`(review, TE-5)`, `(mint, TE-6)`, `(review, TE-6)`, `(mint, TE-7)`,
`(review, TE-7)`, `(mint, TE-8)`. Exactly one emitted line starts with
`TE-8` padded to ten and holds `raised RuntimeError`. It asserts the
runner's pairs are
`TE-1`, `TE-5`, `TE-7` and `TE-7`, each with the task its mint returned.
The older `TE-7` task keeps `GATE_ERROR` and has no attempt. It then runs
a second batch on the same ledger with `TE-1` alone. That mints a new
task, whose one `spec_review` fact has `n` 1. Last, a call with `review`
and no `mint` raises `ValueError`, and the count of `batches` rows is
unchanged. These fail it:

- a mint after the review, which leaves `TE-6` with no task
- a mint on every review, which mints `TE-5` twice
- a mint on every runner call, which mints `TE-7` twice
- a task minted for every spec at batch start, which mints `TE-3`
- a review called after its mint raised
- a mint's raise turned into a `Refused`, which emits no `raised` line
- the scan's `task_id` kept over the minted one, which hands `TE-7` the
  older task
- the minted task handed to the first runner call only
- a store of minted tasks at module scope, which hands the second batch
  the first batch's task

**Criterion 2's witness** reads each minted task's `spec_review` facts
from the record, under `ledger.record_key(task_id)`, and its attempts and
state from the ledger.

| spec | `n` and route | state | attempts |
|---|---|---|---|
| `TE-1` | 1 `run` | `QUEUED` | one, `SPEC_REVIEW`, 0.5, `s-1`, 7 turns, `success` |
| `TE-2` | 1 `escalate` | `SPEC_WITHHELD` | one, 0.25 |
| `TE-4` | 1 `error` | `GATE_ERROR` | one, 0.125, subtype `error` |
| `TE-5` | 1 `wait`, 2 `run` | `RATE_LIMITED` | two, 0.0625 then 0.03125 |
| `TE-6` | 1 `error` | `GATE_ERROR` | none |
| `TE-7` | 1 `run` | `QUEUED` | one, 0.75 |

`TE-2`'s `block` is the `json.dumps` text the double fenced, and its
`block_sha256` is `hash_artifact` of that text. `TE-4`'s `block` is its
clean text, and its error holds `cell died`. `TE-6`'s `block` and
`block_sha256` are `None`, and its error is exactly
`RuntimeError: review cell would not start`. Each `run` fact's error is
`None`. These fail it:

- no state for a withheld task, which leaves `TE-2` `QUEUED`
- no state after an `error` route, or `SPEC_WITHHELD` for it
- no state after a `wait`, which leaves `TE-5` `QUEUED`
- a raise that records nothing, which leaves `TE-6` `QUEUED`
- an attempt opened before the review, which leaves one on `TE-6`
- a review numbered across the ledger, which gives `TE-2` 2
- a `block` dropped for a session that carries an error
- an attempt with a fixed `session_id` or turn count, reasoned and not
  run

**Criterion 3's witness** asserts `ledger.batch_spend` of the first batch
is exactly 5.71875. That is the six review costs, 1.71875, and four runner
calls at $1. These fail it:

- a withheld spec's minted run left out of the batch, which gives 5.46875
- the review's attempt added again on the rerun, which gives 6.46875
- no attempt for a review, which gives 4.0

**Criterion 4's witness** runs the arrangement, then reads the
`spec_reviews` rows ordered by `task_key` and `n`. It takes `TE-5`'s
record key now. A later fold drops and inserts each task again, so a key
looked up afterwards by the old `task_id` names another task. It opens a
fresh `Ledger` with no record, and creates one unrelated repo, run and
task there first. It folds the record into it and asserts the same rows.
It folds the record into the source ledger and asserts its rows are
unchanged. Last, it calls `fold_task` on the fresh ledger with `TE-5`'s
key and an empty list. `TE-5`'s two rows are gone, and every other row
stays. These fail it:

- `_apply` with no branch for `spec_review`, which raises at the first
  review, since the live write applies the fact too
- `_drop_task_rows` that leaves the rows, which raises on the primary key
- `INSERT OR REPLACE` with `_drop_task_rows` untouched, which leaves
  `TE-5`'s rows after `fold_task(key, [])`

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
`c9d46ca8`. It modelled `SA-0143`'s refusal, `SA-0148`'s rerun and
`SA-0149`'s routing, and subclassed `Ledger` with the table. The right
build passed all four. Each wrong build under criteria 1 to 4 failed at
least one, with the failure named. Criterion 6's two wrong builds and the
tree base were run with the real `build_queue`, patching the two sets. The
tree base and both wrong builds queued `TE-1` on the first scan. The tree
base is what the mutant leaves. Criterion
5 is unmeasured, since the read does not exist at `c9d46ca8`.

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
`batch.py` changes about 45 lines at 6.6 tokens a line, and `ledger.py`
about 50 at 4.8. `spec_review.py` changes about 10 at 5.3, and
`scheduler.py` 3. That source comes to about 600 tokens. The tests add
about 210 lines to `tests/test_batch.py` at 3.3, and 35 to
`tests/test_spec_review.py` at 4.7. They add 22 to
`tests/test_scheduler.py` at 3.4. That is about 930 tokens of test, and
about 1530 in all.
