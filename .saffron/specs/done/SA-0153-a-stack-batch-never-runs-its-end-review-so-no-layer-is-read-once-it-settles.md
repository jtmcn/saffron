---
id: SA-0153
title: A stack batch never runs its end review, so no layer is read once the batch settles and nothing says which layers went unread
type: feature
priority: 1
depends_on: [SA-0146]
touches:
  - saffron/end_review.py
  - saffron/ledger.py
  - saffron/batch.py
  - tests/test_end_review.py
  - tests/test_batch.py
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
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_review.py
  - tests/test_task.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
budget_usd: 28
max_attempts: 3
max_turns: 160
pending_symbols:
  - saffron/end_review.py::review_stack
acceptance:
  - claim: >-
      `end_review.review_stack(ledger, batch_key, reserve_usd, specs, ...)`
      reads the layers of that batch alone, from the highest position down.
      A layer starts only while `reserve_usd`, less the cost of every lens
      the call has run, is at least `budget_usd` times the number of
      entries in `END_LENSES`. A lens that returns an error counts its cost. The first
      layer that fails the check is not reached, nor is any layer below it,
      and no cell is opened for one. Each lens of each layer becomes one
      `end_review` fact under that layer's task: `reviewed` with its cost,
      `error` with its cost and error, or `not_reached` with a cost of 0.
      A raise from `open_cell` or from `review_layer` records both lenses
      of that layer as `error` naming it, and the next layer still runs.
      A layer's findings go through `record_findings` under its own task,
      unanchored, after its in-cell findings. It returns one `LayerReview`
      per layer, top down. Its `reviews` are the `LensReview`s with their
      probes, and empty for a layer not reached. The witness runs two
      batches on one ledger. It drives two layers not reached, a layer
      that meets the check exactly, and a Spec lens that fails with a cost.
      It drives a raise from each of `review_layer` and `open_cell`, each
      above a layer that still runs, and a finding on a line the diff adds.
    witness: tests/test_end_review.py::test_the_end_review_reads_each_layer_top_down_until_its_reserve_runs_short
  - claim: >-
      For each layer it reaches, `review_stack` hands `review_layer` the
      container `open_cell` yields for that layer's fields. The diff is the
      layer's own commit, `git diff` with `DIFF_FLAGS` over
      `<head>^..<head>` in `mirror`. `spec_body`, `acceptance`, `touches`
      and `forbidden` are that layer's `Spec`'s own, from `specs`, and the
      body carries nothing appended. `max_turns`, `budget_usd` and
      `claude_md` pass through as given. The witness drives a bottom layer
      whose run's `base_sha` is not its head's parent, a layer stacked on
      another, and a global git config that sets `diff.noprefix`.
    witness: tests/test_end_review.py::test_each_layer_is_read_from_its_own_commit_in_its_own_cell
  - claim: >-
      Folding the record rebuilds the `end_reviews` rows as written, and each
      layer's end-review findings with them. A fold into a fresh ledger
      whose task ids differ gives the same rows. A fold into the ledger that
      wrote them leaves them as they were, sixteen and no more. `fold_task`
      with a layer's key and no facts removes that layer's rows and no
      other. The witness folds criterion 1's two batches.
    witness: tests/test_end_review.py::test_each_layers_end_review_folds_back_from_the_record
  - claim: >-
      `run_stack_batch` takes `reserve_usd` and `end_review`. Its task loop
      starts a task only while the spec's budget fits within the batch
      budget less the reserve and the batch's own spend. The batch row keeps
      the whole budget. Once the loop returns, it calls `end_review` once,
      with the batch's id as text, the reserve, and each spec of the order
      by its id. It then returns the loop's stop reason. A raise out of the
      loop propagates, and `end_review` is not called. The witness drives
      `BUDGET`, `DRAINED`, `INFRASTRUCTURE` and a readiness check that
      raises, four batches on one ledger.
    witness: tests/test_batch.py::test_a_stack_batch_holds_its_end_review_reserve_and_calls_it_once_the_loop_returns
  - claim: >-
      `Ledger.batch_spend(batch_id)` adds the cost on the `end_reviews` rows
      of that batch's layers to the cost of its attempts. The witness drives
      a batch with an attempt and an end review, and a second batch whose
      end review runs on the same ledger.
    witness: tests/test_end_review.py::test_a_batchs_spend_counts_its_own_end_review
  - claim: >-
      `run_batch`, given no reserve, still refuses a task whose budget
      exceeds what the batch has left.
    witness: tests/test_batch.py::test_the_budget_gate_is_one_comparison_before_each_task
    preserves: true
  - claim: >-
      A fact kind the ledger does not place still aborts the fold.
    witness: tests/test_ledger_fold_task.py::test_a_kind_the_ledger_cannot_place_aborts_the_fold_in_either_mode
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 3 of its Done. It cites `DESIGN.md` §2.1,
§4.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 2 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "The end review",
is the design. Its **Money** paragraph names the reserve and the order down
from the top.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, cut from the head of the
layer below it, its **predecessor**. Once the last queued task settles, one
**end review** reads the stack. ADR 7 takes four exceptions to ADR 4 for
it. One is that a lens with an error has no task to stop, so its layer
shows as unreviewed. Principle 34 holds only once a layer the end review did
not reach, or reached with an error, reads apart from a clean one.

**This spec is the second of four for step 3.** `SA-0146` builds the two
lenses and one call that runs both on a layer. This spec runs
that call over a stack, top down, within a reserve. It records each lens of
each layer, reached or not. `SA-0154` adds the join lens, `layer_cell`, the
critic cell a layer is read in, and `run_end_review`, the one call that
runs the whole end review. `SA-0157` wires that call into
`saffron batch --stack`. `SA-0147` then qualifies the findings.

**What the tree base holds.** This spec's tree base is `SA-0146`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`). The chain
`SA-0142` to `SA-0146` puts `run_stack_batch`, the `stack_layers` table,
`Ledger.record_stack_layer` and `saffron/end_review.py` there. So those are
cited by symbol, and every line number below was read at `e3020b3b`.

- `SA-0143` builds `run_stack_batch` in `saffron/batch.py`. It takes the
  order, the ledger, the budget, `until` and a runner, and the keywords
  `readiness_check`, `clock` and `emit`. It returns the stop reason.
  `SA-0143` suggests it call `run_batch`, whose loop is `_drive`
  (`saffron/batch.py:146-264`).
- `SA-0145` writes one `stack_layers` row per layer, keyed on record keys:
  `task_key`, `batch_key`, `position`, `spec_id`, `predecessor_key`,
  `predecessor_head` and `generation`. `batch_key` is the batch's id as
  text.
- `SA-0146` adds `LayerFields` with `spec_id`, `branch`, `pr_url`, `base`,
  `head` and `known`. `layer_fields(ledger, task_key)` fills one. For a
  bottom layer `base` is the run's `base_sha`, so no diff is built from
  it. It adds `END_LENSES`, whose keys are `spec` then `standards`.
  `review_layer(container, fields, *, spec_body, diff, acceptance,
  touches, forbidden, context_md, claude_md, prompts_dir, max_turns,
  budget_usd, agent, emit)` runs both lenses through `review.run_lens` and
  returns their two `LensReview`s. It anchors nothing, and a Spec finding
  keeps its probe.

**The fact kind exists, and nothing places it.** A cell cannot add a
kind, because `CONTEXT.md` is protected. So `8a41411c` added `end_review`
to `KINDS` by hand (`saffron/record/contract.py:39`), as `75edb212` did
for `stack_layer`. `Ledger._apply` raises on
a kind it has no branch for (`saffron/ledger.py:649`), so an `end_review`
fact aborts a fold there (`saffron/record/fold.py:59-63`).

**How a write reaches the record.** Each write method builds one fact with
`_build_fact` and hands it to `_commit_and_append`
(`saffron/ledger.py:372-404`). `_build_fact` takes the fact's `batch_key`
from the task's run (`:374-391`). `fold_task` drops a task's rows and
applies its facts again (`:406-412`). `_drop_task_rows` deletes each table's
rows for the task by `task_id` (`:414-433`). A fresh ledger mints new task
ids, so a row that must survive a fold is keyed on the record key, as
`SA-0145`'s is.

**How findings are recorded today.** `Ledger.record_findings(task_id,
findings)` numbers each new finding after the task's existing ones and
appends one `finding` fact each (`saffron/ledger.py:1143-1169`). The fact
carries no probe (`:1153-1161`). `_apply` inserts each as a `findings` row
(`:618-636`). So a probe lives only on the `Finding` in memory, and `SA-0147`
needs the `LensReview`s themselves.

**Why the diff is the head's own commit.** PACKAGE checks out its target
head (`saffron/phases/package.py:721`). It applies the patch (`:734`)
and makes one squash commit (`:778-787`). Its target is the
default branch's fetched head, or the parent's head when stacked
(`:672-699`). So a layer's pushed head has one parent, the tree PACKAGE
applied it to. A run's `base_sha` is that parent only while the default
branch has not moved. PACKAGE diffs the same range for the pull request
(`:857`). `DIFF_FLAGS` pins the diff's shape against a git config
(`saffron/cell/worktree.py:132-166`), and `mirror.diff_stat` reads a mirror
with it (`saffron/repos/mirror.py:161-170`).

**Why the reserve is checked before a layer.** REVIEW's lens sessions run
under `budget_usd` each (`saffron/phases/review.py:208-234`). Nothing counts
their spend against a batch while they run. `_drive`'s budget comparison
runs before each task (`saffron/batch.py:198-200`), and an end review runs
no task. So the end review keeps its own count against its own reserve.

## Problem

Build three things.

1. **The record of each lens.** Add `end_reviews` to `SCHEMA` in
   `saffron/ledger.py`, with no reference to another table:

   | column | type |
   |---|---|
   | `task_key` | `TEXT NOT NULL` |
   | `lens` | `TEXT NOT NULL` |
   | `status` | `TEXT NOT NULL` |
   | `cost_usd` | `REAL NOT NULL` |
   | `error` | `TEXT` |

   Its primary key is `(task_key, lens)`. Add
   `Ledger.record_end_review(task_id, *, lens, status, cost_usd, error)`.
   It builds one `end_review` fact under the task's own key, with the
   payload `lens`, `status`, `cost_usd` and `error`, and writes it through
   `_commit_and_append`. `_apply` places it as one row, `task_key` from the
   fact and every other value from the payload. `_drop_task_rows` deletes
   the task's `end_reviews` rows. `status` is one of `reviewed`, `error`
   and `not_reached`. `batch_spend` adds the `cost_usd` of each
   `end_reviews` row whose `task_key` has a `stack_layers` row with this
   batch's `batch_key`. An end-review lens opens no attempt, so the join
   through attempts that `batch_spend` sums today
   (`saffron/ledger.py:897-912`) never sees it. A later budget
   comparison in the same batch then counts it.
2. **The end review over a stack.** Add a frozen dataclass `LayerReview`,
   with `task_key` and `reviews`, and `review_stack` to
   `saffron/end_review.py`. Its signature is `review_stack(ledger,
   batch_key, reserve_usd, specs, *, mirror, open_cell, context_md,
   claude_md, prompts_dir, max_turns, budget_usd, agent, emit)`. `specs`
   maps a spec id to its `Spec`. `open_cell` takes a layer's
   `LayerFields` and returns a context manager that yields a container
   name. For each layer of the batch, highest position first:
   - It checks the reserve first. A layer that fails the check, and each
     layer below it, records `not_reached` for each lens.
   - It reads the layer's fields, its `Spec` and its diff. It opens the
     cell and calls `review_layer` in it. `spec_body` is `spec.body`
     alone, and `acceptance`, `touches` and `forbidden` come from the
     same `Spec`. REVIEW appends the criteria to the body
     (`saffron/cell/session.py:2538-2539`). Here the Spec prompt's own
     slots carry them, so an appended copy would send them twice.
   - A raise anywhere in that step gives each lens a `LensReview` with the
     exception's type and message as its error, and a cost of 0.
   - It records the findings as returned, anchoring none, then one
     `end_review` fact per lens.
   It returns the `LayerReview`s in the order it met the layers.
3. **The reserve in the batch.** Add `reserve_usd: float = 0.0` and
   `end_review=None` to `run_stack_batch`. `end_review` takes the batch
   key, the reserve and a mapping of spec id to `Spec`. The task loop holds
   the reserve back from each budget comparison. The batch row still
   records the budget it was given. After the loop returns, `end_review`
   runs once, when one was given. A raise out of the loop propagates, and
   `end_review` does not run.

Two docstrings in `saffron/ledger.py` become false. The module's count of
the kinds that fold back gains one. `SA-0145` leaves a sentence naming
`stack_layers` as a table §4.1 does not list, and `end_reviews` joins it.
`batch_spend`'s docstring names the join through attempts as the whole
figure (`saffron/ledger.py:898-903`), and it gains the end review's part.

`review_stack` has no production caller until `SA-0154`'s
`run_end_review` calls it. `SA-0157` then passes a callable over
`run_end_review` to `run_stack_batch`. So it is a `pending_symbols` entry, and the `dead` gate
defers it while this spec is open (`.saffron/gates/dead.py:4-6`).

## Out of scope

- **The critic cell and the wiring.** `SA-0154` builds `layer_cell`,
  which `open_cell` takes. It seeds a critic cell at the layer's head.
  `SA-0154` also builds `run_end_review` (`SA-0154`'s Problem steps 2 and
  3). `SA-0157` wires it into `saffron batch --stack`, with the
  `review_stack` callable and a reserve that is a share of `--budget`.
- **Qualification.** `run_stack_batch` hands what `end_review` returns to
  `follow_ups` (`SA-0173`). `SA-0165`'s `follow_ups` callable binds
  `SA-0147`'s `qualify`, which anchors, probes and groups the findings.
- **The join lens.** Its run and its record are `SA-0154`'s.
- **A revised layer's latest text.** ADR 7 names the end-review Spec lens
  among the sessions whose cell holds the base text of a revised spec.
  That lens judges a revised layer rightly only against its latest
  recorded text, the one its cell ran. Here `specs` holds the order's queued `Spec`s,
  read at `base_sha`. `SA-0150` builds `Ledger.spec_text`, and it sits
  above this spec in the chain, so no recorded text exists in this tree.
  `SA-0173` has `run_stack_batch` hand `end_review` each revised spec's
  latest text, parsed, in place of its queued `Spec`. `review_stack` reads
  `specs` as given, so it needs no change then.
- **Closing the batch row after the end review.** The loop closes the row
  before `end_review` runs. `close_batch` stores `spent_usd_est` through
  `batch_spend` then (`saffron/ledger.py:820-846`), so the stored figure
  lacks the end review. Follow-ups run after the end review in the same
  batch. `SA-0162` closes the row once, after both.
- **Other money in a stack batch.** `reserve_usd` is the end review's
  alone. A spec review (`SA-0149`, `SA-0156`) runs under a task of its own
  and is charged through `batch_spend` like any task. Follow-up writing
  takes a reserve of its own: `SA-0173` holds `writer_usd` back beside
  this one, and `SA-0165` sets it from `--budget`.
- **A raise once a lens spends.** Take a raise out of `review_layer` that
  is not `AgentFailed`, or one out of `open_cell`'s exit. Either records
  both lenses `error` at a cost of 0. `review_layer` returns both lenses
  at once, so a partial result cannot be recovered here. The reserve can
  then undercount by at most one layer's lenses per such raise.
- **The fold's docstring.** `saffron/record/fold.py:11-12` says
  `batch_spend` joins `runs.batch_id`, so every batch reads as $0 spent
  after a fold. The `stack_layers` join makes that false for end-review
  spend. `saffron/record/**` is forbidden here, and the operator files it.
- **The vocabulary.** `CONTEXT.md` has no entry for an end review, its
  reserve or a lens not reached. Backlog item b-466005 files them by hand.

## Notes for the agent

**Every criterion but the last two is new code.** No text at the tree base
runs lenses over a stack or places an `end_review` fact. So criteria 1 to 5
declare a witness and no mutant, and `witness` reports `skip` for them.
Criteria 6 and 7 are `preserves` and name tests that pass now.

**Import every new name inside the test body.** `review_stack`,
`LayerReview` and `record_end_review` do not exist at the tree base. A
module-scope import fails collection when the source is reverted, and
`revert` reads that as `skip`.

**The end review runs past `--until`.** It runs after the loop whatever
the stop reason, `UNTIL` included, and the operator decided so. The review
is the point of a stack batch, its money was held back at the start, and
the reserve bounds its length. `CLAUDE.md` still says a night ends at the
deadline plus at most one task. `CLAUDE.md` is forbidden here, and the
operator corrects that sentence by hand.

**Criteria 1, 2, 3 and 5 share one arrangement.** A helper builds it and
runs two end reviews. Write a git config file in `tmp_path` that sets
`diff.noprefix = true`, `user.name` and `user.email`. Point
`GIT_CONFIG_GLOBAL` at it with `monkeypatch`, so no commit reads the
host's identity. Build a git repo in `tmp_path` as the mirror. Give every
commit the message `msg <file>`. The `noprefix` and `DIFF_FLAGS` behaviour
below was measured on the host's git, not the cell image's.

- On `main`: `a.txt` as commit `A`, then `m.txt` "moved main", then one
  commit per layer adding `TE-4.txt`, `TE-7.txt`, `TE-3.txt`, `TE-9.txt`
  and `TE-5.txt`, each holding "`<spec>` layer".
- On a branch from `A`: `m2.txt` "moved main", then `TE-1.txt`,
  `TE-8.txt` and `TE-6.txt` the same way.

Build a `Ledger` with a `MemoryRecord` and two batches. Take the specs in
the order `TE-9`, `TE-4`, `TE-7`, `TE-5`, `TE-3`, `TE-6`, `TE-1`, `TE-8`.
For each, create a run with `base_sha` `A` and its batch's id, then a
task. Package
it `READY_FOR_REVIEW` at its commit. Record one correctness concern
"in-cell c5" on `TE-5`, and one closed attempt on `TE-5` costing 1.0.
Record layers with `record_stack_layer`, each on the one before it:

| batch | position | spec |
|---|---|---|
| 1 | 1 | `TE-4` |
| 1 | 2 | `TE-7` |
| 1 | 3 | `TE-3` |
| 1 | 4 | `TE-9` |
| 1 | 5 | `TE-5` |
| 2 | 1 | `TE-1` |
| 2 | 2 | `TE-8` |
| 2 | 3 | `TE-6` |

`specs` holds a `Spec` for each, with the body "body `<spec>`" and one
criterion "claim `<spec>`" whose witness is `tests/test_<spec>.py::t`.
Its `touches` is `<spec>.py` and its `forbidden` is `no-<spec>.py`.
`open_cell` records each spec id it is given. It raises
`RuntimeError("no cell for TE-8")` for `TE-8`, and yields `critic-<spec>`
for the rest. The agent double records each call's container, options and
keywords. It returns the next scripted reply, and raises `AssertionError`
with none left. `budget_usd` is 1.0 and `max_turns` 17. `claude_md` is
one line.

Batch 1's end review has a reserve of 4.0 and six replies, in order. Both
`TE-5` findings sit on `TE-5.txt` line 1, a line its diff adds.

| call | layer, lens | reply | cost |
|---|---|---|---|
| 1 | `TE-5`, Spec | a blocker "f5 spec" with a probe | 0.5 |
| 2 | `TE-5`, Standards | a concern "f5 standards" | 0.5 |
| 3 | `TE-9`, Spec | raises `implement.AgentFailed` | 0.75 |
| 4 | `TE-9`, Standards | a note "f9 standards" | 0.25 |
| 5 | `TE-3`, Spec | no findings | 0.25 |
| 6 | `TE-3`, Standards | no findings | 0.25 |

After `TE-9` the reserve left is exactly 2.0, so `TE-3` runs. After `TE-3`
it is 1.5, so neither `TE-7` nor `TE-4` is reached. Batch 2's end review
has a reserve of 4.0 and three scripted items. The double raises
`RuntimeError("runner crashed")` on `TE-6`'s Spec call. `open_cell` raises
for `TE-8`. `TE-1` then gets two replies with no findings, at 0.25 each.

**Criterion 1's witness** asserts:

- nine agent calls, and `open_cell` given `TE-5`, `TE-9`, `TE-3`, `TE-6`,
  `TE-8` and `TE-1`, in that order.
- batch 1 returns `TE-5`, `TE-9`, `TE-3`, `TE-7` and `TE-4`'s keys in
  that order. `TE-5`'s reviews are `spec` then `standards`, and its first
  finding's probe equals the `Mutant` scripted. `TE-9`'s Spec review
  carries its error and cost 0.75. `TE-7`'s and `TE-4`'s reviews are
  empty.
- batch 2 returns `TE-6`, `TE-8` and `TE-1`'s keys. `TE-6`'s reviews and
  `TE-8`'s are each `spec` then `standards`, at cost 0, with an error
  naming "runner crashed" and "no cell for TE-8" in turn.
- sixteen `end_reviews` rows. `TE-5`'s two, `TE-9`'s Standards, `TE-3`'s
  two and `TE-1`'s two are `reviewed` at their costs, with no error.
  `TE-9`'s Spec is `error` at 0.75 with an error. `TE-7`'s two and
  `TE-4`'s two are `not_reached` at 0.0. `TE-6`'s two are `error` at 0.0
  naming "runner crashed", and `TE-8`'s two name "no cell for TE-8".
- `TE-5`'s findings are "in-cell c5", "f5 spec" and "f5 standards" in that
  order, of lenses `correctness`, `spec` and `standards`, none anchored.
  `TE-9`'s are "f9 standards" alone. The other six layers have none.

These fail it, each measured:

- layers read bottom up, or ordered by spec id
- the reserve checked after a layer, or with a strict `>`
- the cost of a lens with an error left out of the count
- the reserve checked against one lens's budget
- a layer not reached given no row, or an `error` row
- `not_reached` recorded for the first layer that fails the check, then
  a `break`, which leaves `TE-4` with no row
- a lens's error ignored, so it reads `reviewed`
- findings recorded under the predecessor's task
- findings run through `findings.anchor` before `record_findings`
- every batch's layers read, which raises on the primary key
- the spend kept across calls, so batch 2 is not reached
- a raise that propagates, one that ends the end review, or one recorded
  as `not_reached`
- empty `reviews` for a layer whose read raised
- a fixed lens budget
- the two lenses' reviews reversed

**Criterion 2's witness** asserts each call's container in order:
`critic-TE-5` twice, `critic-TE-9` twice, `critic-TE-3` twice, then
`critic-TE-6` once and `critic-TE-1` twice. Every call has `max_turns` 17,
`max_budget_usd` 1.0 and no `resume`. For calls 1, 3 and 5, the Spec
lens's system prompt holds "+`<spec>` layer", "body `<spec>`", the
`claude_md` line and that spec's witness id. It holds
`context.constraints_block` of that `touches` and `forbidden` whole. The
Standards call after each holds "body `<spec>`" and no "claim `<spec>`",
since only the Spec prompt has a criteria slot. Call 1's prompt holds no
"+TE-9 layer". Call 8, the bottom layer `TE-1`'s Spec call, holds
"+TE-1 layer" and "diff --git a/TE-1.txt b/TE-1.txt", and neither
"moved main" nor "msg TE-1". These fail it, each measured:

- the diff over `fields.base..head`, which holds "moved main" for `TE-1`
- the diff from the run's `base_sha`, which holds "+TE-9 layer" for `TE-5`
- `git show`, which holds the commit message
- a diff with no `DIFF_FLAGS`, which loses the `a/` prefix
- `context.criteria_section` appended to the body, as REVIEW does, which
  puts the claim in the Standards prompt
- the body of the predecessor's `Spec`
- no `acceptance` passed, or `touches` and `forbidden` swapped
- a fixed `max_turns`

**Criterion 3's witness** takes the rows as dicts keyed on `task_key` and
`lens`, and `TE-5`'s findings, from the source ledger. It opens a fresh
`Ledger` with no record, and creates one unrelated repo, run and task
there first. It calls `saffron.record.fold.fold` with the record and the
fresh ledger. It asserts the rows equal the source's, and `TE-5`'s
findings there equal the source's. It asserts the fresh ledger's
`batch_spend` of batch 1's id is 2.5. Only the `stack_layers` join gives
that, since the fold leaves each run's `batch_id` unset. It then folds the record into the
source ledger, and asserts its rows are unchanged, sixteen and no more.
Last, it calls `fold_task` on the fresh ledger with `TE-9`'s key and an
empty list. Fourteen rows remain, and none is `TE-9`'s. These fail it,
each measured:

- `_apply` with no branch for `end_review`, which aborts the fold
- the end review's cost joined through `tasks` and `runs.batch_id`, which
  gives 0.0 on the fresh ledger
- `_drop_task_rows` that leaves the rows, which raises on the primary key
- `INSERT OR REPLACE` with `_drop_task_rows` untouched, which leaves
  `TE-9`'s rows after `fold_task(key, [])`
- a row written and no fact appended
- findings inserted by SQL of your own, with no fact
- `not_reached` for the first failing layer, then a `break`

**Criterion 4's witness** runs four stack batches on one `Ledger`, with a
reserve of 6.0. The order is `TE-1`, `TE-2` and `TE-3`, each with a budget
of 5.0 from `_candidate`. The runner appends each spec id to a shared log.
It creates a run and a task for the spec, opens and closes one attempt
costing 5.0, and packages the task `READY_FOR_REVIEW`. It returns
`_outcome` with that task's own `task_id` and run. `end_review` appends
its three arguments to the same log.

| batch | budget | runner | readiness | runs | ends |
|---|---|---|---|---|---|
| 1 | 20.0 | as above | `_ready` | `TE-1`, `TE-2` | `BUDGET` |
| 2 | 30.0 | as above | `_ready` | all three | `DRAINED` |
| 3 | 30.0 | appends, then raises `RuntimeError` | `_ready` | `TE-1`, `TE-2` | `INFRASTRUCTURE` |
| 4 | 30.0 | as above | raises `RuntimeError` | none | the raise |

For batches 1 to 3 it asserts the runs and the stop reason. The log ends
with one `end_review` entry, of `str` of that batch's id, 6.0 and the
order's three specs by id. The batch row's `budget_usd` is the budget
given. For batch 4 it asserts the raise leaves `run_stack_batch`, and the
log gains no entry. These fail it, each measured on a stand-in built over
`run_batch`:

- no reserve held, which runs `TE-3` in batch 1
- `run_batch` given the budget less the reserve, which records 14.0
- the spend counted over the whole ledger, which stops batch 2 at `BUDGET`
- `end_review` called before the loop, or only after `DRAINED`
- `end_review` called in a `finally`, which logs it for batch 4
- the batch id passed as an `int`
- a mapping of the layers' specs alone

**Criterion 5's witness** asserts `batch_spend` of batch 1 is 3.5, the
attempt's 1.0 and the end review's 2.5, and of batch 2 is 0.5. These fail
it, each measured:

- `batch_spend` left as it is, which gives 1.0 and 0.0
- every batch's `end_reviews` rows summed, which gives 4.0 and 3.0
- the end review's cost in place of the attempts', which gives 2.5

Nothing at the tree base writes an `end_reviews` row, so every existing
caller and test of `batch_spend` reads the same figure. The join names
`stack_layers`, so it runs only on a ledger that has that table, which
`SA-0145` adds to `SCHEMA`.

**How the lists were measured.** Two throwaway simulations ran on
2026-09-23 at `4f57467c`. The first subclassed `Ledger` with `SA-0145`'s
table, this spec's table, both write methods and the wider `batch_spend`.
It stood in for `layer_fields`, and for `review_layer` with `SA-0146`'s
keywords. It ran the real `review.run_lens`, with a Spec model whose probe
is optional, and the real `findings.anchor` for that wrong version. It ran
the arrangement above on the host's git. The second built
`run_stack_batch` over `run_batch`. The right build passed each witness,
and every wrong version listed failed its own. The code of `SA-0143` to
`SA-0146` is not at `4f57467c`, so no witness ran against it.

**What the witnesses leave undriven.**

- A raise from `layer_fields`, the spec lookup or the diff. Catch those in
  the same place as a raise from `open_cell`.
- The `context_md`, `prompts_dir` and `emit` pass-through. Pass each to
  `review_layer` as given.
- The stop reasons `UNTIL` and `INCOMPLETE`. `end_review` runs after the
  loop whatever it returns.
- A layer of generation 1. Follow-up layers are `SA-0162`'s, after the
  end review.

**The double's `AssertionError` is caught.** `review_stack` catches a raise
from `review_layer`, the double's included. So a lens the script did not
expect reads as `error`, and the call count is what fails.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). A
prototype of this change, measured with `size_gate`, came to 1841 changed
tokens. That was 343 in `end_review.py`, 213 in `ledger.py` and 83 in
`batch.py`, then 1004 in `tests/test_end_review.py` and 198 in
`tests/test_batch.py`. It had few docstrings. Keep the helper shared and
the test docstrings short.
