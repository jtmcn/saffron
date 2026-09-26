---
id: SA-0162
title: A stack batch writes its follow-up specs and runs none of them, and closes its row before its end review spends
type: feature
priority: 1
depends_on: [SA-0165]
touches:
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/cli.py
  - tests/test_batch.py
  - tests/test_cli.py
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
  - saffron/ledger.py
  - saffron/end_review.py
  - saffron/spec_review.py
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
  - tests/test_scheduler.py
  - tests/test_task.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_end_review.py
  - tests/test_spec_review.py
  - tests/test_session.py
budget_usd: 37
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      Given `follow_ups`, `run_stack_batch` runs the candidates it returns,
      after `end_review` and then `follow_ups` run once each. It runs them
      in the order returned, each once. Each follow-up is reviewed and run
      on the last layer, the top of generation 0 for the first one. A
      follow-up that misses `READY_FOR_REVIEW`, or whose review routes
      `escalate`, adds no layer, and the next follow-up gets the same
      predecessor. `mint` runs for every spec of the order, one the queue
      handed with a `task_id` included, and never for a follow-up. Each
      follow-up that returns
      `READY_FOR_REVIEW` is recorded as a layer of generation 1, at the
      next position after the batch's layers so far. Every spec of the
      order stays generation 0, a re-queued one included. Neither `end_review`
      nor `follow_ups` runs again. An escalated or missed follow-up is not
      unrun, so the batch prints no `follow-ups unrun  ` line.
    witness: tests/test_batch.py::test_a_stack_batch_runs_its_follow_ups_on_top_as_generation_one_layers
  - claim: >-
      Follow-ups run only when generation 0's loop drained. Before each
      follow-up the batch checks `--until`, the budget and the breaker, in
      that order, as it does for a spec of the order. The budget check
      compares the follow-up's `budget_usd` with the batch budget less
      `batch_spend`. It holds back neither `reserve_usd` nor `writer_usd`.
      The budget check before a follow-up's revision holds back neither
      too, and the one before a revision of a spec of the order still
      holds back both. The breaker's count carries over from generation 0.
      Each follow-up the batch stops before its review reaches `run`,
      `escalate` or `revise` is unrun, one whose review routed `wait`
      included. Once the follow-ups settle, one line starting `follow-ups unrun  ` names each
      unrun spec id, in the order the batch met them. A task that
      generation 0 left in flight lets the follow-ups run, and the batch
      then stops `INCOMPLETE`. The witness drives a follow-up that fits
      only once both are released, and one that fits only if the end
      review's spend is left out. It drives a generation 0 that stops
      `BUDGET`, an end review that runs past `until`, an abort on each side
      of the end review, and a task left in flight. It drives a follow-up
      routed `revise` that either held reserve would leave unrevised, and a
      re-queued spec of the order routed `revise` that fits only with
      `writer_usd` released. It drives a follow-up whose review routes
      `wait` past `until`.
    witness: tests/test_batch.py::test_a_follow_up_meets_until_the_budget_and_the_breaker_as_any_task_does
  - claim: >-
      `run_stack_batch` checks readiness once and closes its batch row once,
      after the end review and the follow-ups. The row's status is the stop
      reason it returns. Its spend is `batch_spend` at that close, the end
      review's and the follow-ups' included. A raise from `end_review` or
      from `follow_ups` closes the row `INFRASTRUCTURE` and leaves
      `run_stack_batch`. A readiness check that raises closes the row
      `INFRASTRUCTURE`, and neither callable runs. The witness drives a
      batch with a follow-up, one with `follow_ups` of `None`, one whose
      follow-up stops it at `BUDGET`, and each of the three raises.
    witness: tests/test_batch.py::test_a_stack_batch_closes_its_row_once_after_its_follow_ups_or_their_raise
  - claim: >-
      Given `open_prs`, `run_stack_batch` calls it once for the follow-ups,
      after `follow_ups` returns at least one follow-up to run and before
      the first is reviewed. Each follow-up then meets gate 0's open pull request
      overlap refusal against that list, after `--until`, the budget and
      the breaker and before its review. An open pull request whose head
      branch is a layer of this batch, or the follow-up's own branch, is
      exempt. One from a task of this batch that added no layer is not, nor
      one from a layer of an earlier batch. A follow-up refused there is
      never reviewed or run, adds no layer, counts as no abort, and emits
      one line. The line is its id padded to ten, then ` refused  `, then
      a reason naming the pull request's url. Such a follow-up is unrun. The `follow-ups unrun  ` line names every follow-up never
      reviewed, refused on the overlap before its review or never reached,
      in the order the batch met them.
      The witness drives an overlap with a layer below the predecessor,
      with a layer that is no longer the predecessor, and with the
      follow-up's own branch. It drives one with a task that ended
      `MERGE_FAILED`, with an earlier batch's layer, and with an unrelated
      branch.
    witness: tests/test_batch.py::test_a_follow_up_meets_gate_0_with_only_this_batchs_layers_exempt
  - claim: >-
      `saffron batch --stack` passes `run_stack_batch` an `open_prs`
      callable where readiness passed, and `None` where it failed. The
      callable reads nothing until it is called. Called, it returns
      `scheduler._open_prs` of the resolved slug, through `_guarded_gh`, so
      a `gh` that cannot start reads as no open pull request. With no slug
      it returns an empty list and runs no `gh`. Either way it prints the
      `note:` line `_print_skipped` prints, with `_GH_REFUSALS_SKIPPED`, as
      `_print_scan_gaps` does for the plan. The witness drives a slug with a
      working `gh`, a slug with a `gh` that cannot start, no slug, and a
      readiness failure.
    witness: tests/test_cli.py::test_a_stack_batch_reads_the_open_pull_requests_a_follow_up_meets
  - claim: >-
      Given `open_prs`, a spec of the order whose task's latest spec text
      has origin `revision` meets gate 0's open pull request overlap
      refusal again, on that text's `touches`. The check runs after its
      review routes `run` and before its runner call, with criterion 4's
      exempt set. The batch calls `open_prs` once for each such check. A
      spec of the order whose task holds no spec text, or whose latest
      text has another origin, meets no check and no call. A refused spec
      is never run, adds no layer, counts as no abort, and emits criterion
      4's ` refused  ` line. The witness drives a revision widened onto a
      layer's pull request below the predecessor, onto a missed task's,
      onto an unrelated one, and onto none. It drives a spec with no text
      and one whose only text is a `follow_up`, each beside an overlapping
      pull request.
    witness: tests/test_batch.py::test_a_revised_spec_meets_gate_0s_open_pull_request_refusals_before_its_cell
  - claim: >-
      `run_batch` still closes its batch row once, with each of its stop
      reasons.
    witness: tests/test_batch.py::test_every_stop_path_closes_the_batch_row_with_its_reason
    preserves: true
  - claim: >-
      A readiness probe that raises in `run_batch` still closes the row
      `INFRASTRUCTURE`.
    witness: tests/test_batch.py::test_a_readiness_probe_that_raises_still_closes_the_batch_row
    preserves: true
  - claim: >-
      `build_queue` still exempts every ancestor's open pull request from
      the overlap refusal.
    witness: tests/test_scheduler.py::test_a_grandparents_open_pull_request_does_not_refuse_its_grandchild
    preserves: true
  - claim: >-
      `build_queue` still refuses a candidate whose `touches` overlaps an
      unrelated open pull request.
    witness: tests/test_scheduler.py::test_an_unrelated_open_pull_request_still_refuses_on_overlap
    preserves: true
  - claim: >-
      `build_queue` still refuses a new task for a spec whose branch has an
      open pull request.
    witness: tests/test_scheduler.py::test_an_open_pr_from_another_task_refuses
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §4.2,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that qualified findings become follow-up specs, one generation
deep. Each passes the same spec review and runs on top of the stack. The
findings a follow-up's own critic leaves go to the backlog, not to a
second generation. ADR 7's principle 54 bullet holds once gate 0 runs
again on every revised and follow-up spec. Section 1 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design.
Its gate 0 paragraph says backlog item 59 exempted a declared chain, and
step 7 exempts the batch's own tasks for follow-ups. Section 3 says every
revised spec passes gate 0 again before its cell.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**. Once the order settles, one
**end review** reads the stack.

**This spec runs the follow-ups.** `SA-0161` writes them. `SA-0173`
hands `run_stack_batch` the list, which it does not run. `SA-0165` passes that callable
from `saffron batch --stack`. This spec runs that list on top
of the stack. It exempts the batch's own layers from gate 0's overlap
refusal for a follow-up. It runs gate 0's open pull request refusals
again on every revised spec of the order, which `SA-0150`'s `run_task`
cannot run. That closes backlog item b-df59f8. It closes the batch row once all of it is
done. `SA-0151`, the finishing layer, follows it in the chain.

**What the tree base holds.** This spec's tree base is `SA-0165`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`). The chain from
`SA-0142` puts these there, so they are cited by symbol. Every line number
below was read at `a5d52c29`, where no chain code from `SA-0142` on exists.

- From `SA-0135`: `Refused` in `saffron/task.py`. `_drive` skips the
  attach and the breaker's count for a `Refused`.
- From `SA-0143`: `run_stack_batch` in `saffron/batch.py`, which drives
  `_drive` through a runner wrapper that hands each runner call its
  predecessor. `tests/test_batch.py`'s `_candidate` takes `priority` and
  `depends_on`.
- From `SA-0145`: the `stack_layers` table, and
  `Ledger.record_stack_layer(task_id, *, position, predecessor_task_id,
  generation)`. The wrapper numbers each layer from 1 among this batch's
  layers, and writes generation 0.
- From `SA-0148`: the `sleep` keyword and the rate-limit wait.
- From `SA-0149`, `SA-0155` and `SA-0156`: the `review` and `mint`
  keywords and `SpecReviewSession`. A spec is reviewed on the last layer
  before its runner call. `mint` runs for every spec of the order, whatever
  `task_id` the queue handed it, so each spec gets a fresh task tonight.
  An `escalate` route returns a `Refused` with an ` escalated  ` line.
- From `SA-0168`: `CellSpec.task_id` and `run_task(task_id=...)`. The cell
  runs on the task the batch minted, and on that task's run. So every run,
  attempt and layer of a stack batch belongs to tonight's batch, and
  `batch_spend` holds no run an earlier batch attached.
- From `SA-0153` and `SA-0157`: the `reserve_usd` and `end_review`
  keywords. The task loop holds the reserve back from each budget
  comparison. `end_review` runs once after the loop, with the batch's id as
  text, the reserve and each spec of the order by its id. `batch_spend`
  adds the cost of the batch's `end_reviews` rows.
- From `SA-0150`, `SA-0160` and `SA-0164`: `spec_texts`,
  `Ledger.record_spec_text`, `Ledger.spec_text`, and the `revise` keyword
  and route with its rounds. A task with a `spec_texts` row runs that
  text, and its review reads it. `run_task` runs gate 0's other refusals
  again on that text, and leaves the two open pull request refusals to
  this spec. Before each revision the wrapper checks the budget left: the
  batch budget less `reserve_usd`, `writer_usd` and `batch_spend`.
- From `SA-0161`: `write_follow_ups`. Each follow-up it returns is a
  `Candidate` with its task minted and a `spec_text` of origin `follow_up`
  recorded. Each writer session is an attempt on a task whose run is in
  the batch, so `batch_spend` counts it.
- From `SA-0173`: the `follow_ups` and `writer_usd` keywords.
  `follow_ups` is called once after `end_review`, with the batch's key and
  what `end_review` returned, and returns that list. The task loop holds
  `writer_usd` back beside `reserve_usd`.
- From `SA-0165`: `saffron batch --stack` passes `follow_ups` and
  `writer_usd`. Its callable catches every raise, so `follow_ups` never
  raises in production.

**How the loop closes its row today.** `run_batch` opens the row
(`saffron/batch.py:113`) and runs `_drive` (`:120-134`). Every return in
`_drive` goes through `_stop` (`:162-164`). `_stop` names each task left
in flight, and turns an ordinary reason into `INCOMPLETE` for one. It then
calls `close_batch` (`:267-293`). A raise closes the row
`INFRASTRUCTURE` in `run_batch`'s `finally` (`:135-143`). `close_batch`
stores the spend `batch_spend` reads at that moment (`saffron/ledger.py:820-846`). So at
the tree base the row closes before `end_review` runs, and its spend
leaves the end review out. `SA-0153` names this in its Out of scope and
hands the close to this step.

**How `_drive` holds its state.** The breaker's count is a local of
`_drive` (`saffron/batch.py:172`), and so are `started` and `pending`
(`:175-178`). `in_flight` belongs to `run_batch` (`:118`). `_drive`
checks readiness once, at its top (`:165-170`). Before each task it checks
`--until`, then the budget, then the breaker (`:195-203`).

**Gate 0's open pull request refusals.** `_refuse` runs them in
`build_queue`'s plan (`saffron/scheduler.py:623-727`). A spec's own
branch with an open pull request refuses a new task (`:646-662`). An open
pull request whose changed files match the spec's `touches` refuses it,
unless its head branch is the spec's own or an ancestor's
(`:676-698`). The ancestors walk `depends_on[0]` (`:166-201`). A follow-up
has no `depends_on`, so no branch of the stack is its ancestor. Its
`touches` are its anchored files and their tests. Those are files a layer
changed, so the layer's own pull request overlaps it. `build_queue` reads
the list with `_open_prs(repo_slug, gh)` (`:841`), which returns `[]` on
any `gh` failure (`:204-252`). `cli._resolve_queue` reads the slug with
`package_phase.github_slug`, and `None` when it cannot
(`saffron/cli.py:601-604`). `_guarded_gh` records a `gh` that cannot
start and returns exit 127 (`:1075-1090`). For the plan,
`_print_scan_gaps` prints `_print_skipped`'s `note:` line with
`_GH_REFUSALS_SKIPPED` for no slug or a failed `gh` (`:1132-1135`,
`:1170-1191`, `:1204-1212`). `saffron/cli.py` imports `run_gh` from
`scheduler` (`saffron/cli.py:29-37`). `SA-0150` runs the refusals that need no `gh` again on a
recorded text, in `run_task`. `run_task` holds no slug and no `gh`. So
its Out of scope leaves the two open pull request refusals to this spec,
on a revision and on a follow-up. Nothing on the stack path reads the
open pull requests after the plan.

## Problem

Build six things.

1. **The follow-up layers.** Run the follow-ups after `end_review` and
   `follow_ups`, through the same loop and the same wrapper as the order.
   Run them only after generation 0's loop returned `DRAINED`. Criteria 1
   and 2 state the rest. Record each follow-up's layer at generation 1.
   Hold back neither `reserve_usd` nor `writer_usd` for them, in the task
   loop's check or in the check before a revision. Pass the wrapper the
   generation, so that check knows which it runs for. The end review and
   the writing ran already, and their spend is in `batch_spend`. Carry the
   breaker's count and the in-flight list across. Check readiness once,
   before the order.
2. **One close.** Close the row once, after the follow-ups, as criterion 3
   states. `run_batch` keeps closing exactly as it does at the tree base.
3. **The overlap refusal for a follow-up.** Move `_refuse`'s two open pull
   request refusals into a function of `saffron/scheduler.py`. They are the
   same-spec one and the overlap one. The function takes the candidate,
   the list and a set of exempt branches. `_refuse` passes it
   `ancestor_branches`, so `build_queue` refuses what it refuses today.
   The function skips the candidate's own branch in the overlap refusal
   itself, as `_refuse` does at `:676-679`, so no caller adds it to the
   set. Add an `open_prs` keyword to `run_stack_batch`, `None` by default,
   and with `None` nothing is refused. For the follow-ups, call it only
   when at least one follow-up is to run. Refuse a follow-up as criterion 4 states. Its
   exempt set is `_branch` of each layer's spec id in this batch,
   generation 0 and 1, kept by the batch itself. Return a `Refused` from
   the wrapper, so `_drive` counts no abort.
4. **The unrun follow-ups.** An unrun follow-up is one the batch never
   reviewed. Never reviewed means no review of it reached a verdict route:
   `run`, `escalate` or `revise`. Gate 0 refused it on the overlap before
   its review, or the batch stopped before it at `UNTIL`, `BUDGET` or the
   breaker. A follow-up whose review routed `wait` before the batch
   stopped is unrun too. An escalated, unrevised or missed follow-up was
   reviewed, so it is not unrun. Keep
   the unrun follow-ups' task ids, as `int`s, in the order the batch met them. Once
   the follow-ups settle, emit one `follow-ups unrun  ` line naming their
   spec ids in that order. Emit no line when none is unrun. `SA-0151`
   passes that list to `finish` unchanged, as `unrun`.
5. **The wiring.** In `saffron/cli.py`, build the `open_prs` callable
   where the `--stack` path builds `_stack_review`, as criterion 5 states.
   Reach `_open_prs` through the `scheduler` module and `run_gh` through
   `cli`, at call time, since the witness replaces `cli.run_gh`.
6. **The refusal on a revised spec of the order.** This is for a spec of
   generation 0. Once its review routes `run`, read the latest
   `spec_text` row on its task. Act only when its origin is `revision`. Parse
   its text with `parse_spec`. Run the item 3 function on the candidate
   with that spec in place, through `dataclasses.replace`. The exempt set
   is item 3's. Call `open_prs` right before that check. A follow-up meets
   no check here. With `open_prs` of `None`, check nothing. Refuse as
   item 3 does, with the same line. A text `parse_spec` refuses meets no
   check here, and `SA-0150`'s `run_task` refuses it before its cell.
   Criterion 6 states the rest.

**Why only after `DRAINED`.** A follow-up sits above every spec of the
order, so it runs only once each of them has had its turn. A generation 0
that stopped at `BUDGET` left a spec that did not fit, and `_drive` never
skips past one (`saffron/batch.py:198-200`). At `UNTIL` or
`INFRASTRUCTURE`, the first follow-up would meet the same check. Those
follow-ups run on no night of their own. `SA-0151` decides what of them
reaches the finishing commit and `findings.json`.

**Why the reserve is released.** Generation 0 holds back the end review's
reserve and the writer's share, because neither runs until the order
settles. By the follow-ups both ran, and `batch_spend` holds what they
spent. Holding the reserve again would count that money twice. A
revision's check follows the same rule, with both held for generation 0
as `SA-0164` holds them.

**Why one read for the follow-ups.** The list is read once, before
the first follow-up. So a pull request a follow-up opens tonight is not in
it, and never refuses a later follow-up. The exemption for a generation 1
layer is therefore inert, and kept only so the set names every layer. The
read happens after the end review, once every generation 0 layer opened
its pull request. A pull request someone opens by hand during the
follow-ups goes unseen, and `SA-0167` checks each base before any link.

**Why a fresh read for each revised spec of the order.** The plan's list
is `_resolve_queue`'s, and `run_stack_batch` never holds it. A layer or
a missed task can open a pull request after the plan. So a revised spec
of the order reads the list right before its check. An unrevised spec of
the order meets no second read. Its `touches` passed the plan's check.

**Why a revised follow-up needs no second check.** `SA-0150`'s `run_task`
refuses a follow-up's revision whose `touches` is not a subset of its
first row's. That first row passed criterion 4's check before its review.
It met the same list, and an exempt set that only grows as layers are
added. So a revision that passes `run_task` overlaps nothing that first
check did not already see.

**Why layers and not every task.** The exemption stands on backlog item
59's ground. A layer's code is in the follow-up's tree by construction,
since the follow-up is cut from the top of the stack. A task of this
batch that missed `READY_FOR_REVIEW`, such as one that ended
`MERGE_FAILED` with its pull request open, is in no layer's tree. So its
pull request can still conflict, and the refusal stands. A layer of an
earlier batch is not in this stack's tree either. So the batch keeps its
own layers, and reads no other `stack_layers` row.

## Out of scope

- **Writing the follow-ups.** `SA-0161` writes them, mints their tasks and
  records their text. Their spend reaches `batch_spend` there.
- **The review of a follow-up's text.** `SA-0164` has a review read a
  task's recorded text. A follow-up has no file at `base_sha`, so its
  review reads that text alone.
- **The pool.** The findings a follow-up's own critic leaves go to the
  backlog, through the `findings.json` the finishing layer writes
  (`SA-0151`). No end review reads a follow-up's layer here.
- **The finish and its reserve.** `SA-0151` adds a layer after the
  follow-ups and moves the close after it.
- **An unrevised spec of the order and tonight's pull requests.** Its
  `touches` passed the plan's check, and nothing reads the list again for
  it. A pull request a missed task opened tonight goes unseen for it, as
  at the tree base.
- **The `note:` line's words mid-batch.** Criterion 5's callable prints
  its `note:` line once per `open_prs` read. Its clause ends "refusal list
  above is incomplete", and a read during the batch prints no list. Three
  tests pin that text for the plan (`tests/test_cli.py:2451`, `:2495`,
  `:3854`), so rewording `_GH_REFUSALS_SKIPPED` is not cheap here.
- **Gate 0's other refusals on a recorded text.** `SA-0150` runs them in
  `run_task`, on every revised and follow-up spec.
- **An unrun follow-up's text.** Its task keeps the state `SA-0161` left it
  in. `SA-0151` passes the unrun task ids this spec keeps to `finish` as
  `unrun`, so the finish commits their texts. Once merged, a later scan
  offers each as a queued spec. A follow-up that escalated, stayed
  unrevised or missed is not unrun, and the finish commits no text of it.
- **The design record's words.** Section 1 of the design says the batch's
  "own tasks". This spec exempts its layers alone. `docs/**` is forbidden
  here, and the delegate edits that sentence by hand.
- **The vocabulary.** `CONTEXT.md` has no entry for a follow-up spec or a
  generation. Backlog item b-466005 files both by hand.

## Notes for the agent

**Criteria 1 to 6 are new code.** No text at the tree base runs a
follow-up. None closes a stack batch's row after its end review. None
refuses a follow-up or a revised spec on an open pull request, or passes
`open_prs`. So each declares a witness and no mutant, and `witness`
reports `skip` for each. Criteria 7 to 11 are `preserves` and name tests
that pass now.

**Every witness fails with the source reverted.** Criteria 1, 2 and 4
assert runner calls for follow-ups that the tree base never makes.
Criterion 3's row closes before `end_review` at the tree base, so its
spend and its close count differ. Criterion 4 passes `open_prs=`, which
the tree base does not take, and so does criterion 6. Criterion 5 reads
a keyword the tree base never passes. Import every chain name inside each test body.

**One loop, not two.** Do not copy `_drive`'s checks. One way is to let
`_drive` return without closing and take its breaker's count from its
caller. `run_stack_batch` then calls it for the order, runs `end_review`
and `follow_ups`, calls it again for the follow-ups, and closes through
`_stop` once. A `finally` like `run_batch`'s closes the row on a raise.
The second call checks no readiness. `run_batch` itself keeps its shape.

**Other fakes of `run_stack_batch`.** The chain fakes it in
`tests/test_cli.py`. Each fake must accept the new `open_prs` keyword,
through `**kwargs` or by name. The file is in `touches`, so edit each fake
that refuses it.

**Docstrings this makes false.** `_drive`'s says every return is `_stop`,
the one call to `close_batch` (`saffron/batch.py:160-164`). `_stop`'s
says it is the single call site for `close_batch` (`:285-287`). Reword
each to match what the change builds.

**One shared arrangement.** Criteria 1 to 4 and 6 share doubles over one
`Ledger`, built once in `tests/test_batch.py`. Use `_ready`, the `ledger`
and `repo_id` fixtures, a fake `sleep`, and a clock as `SA-0148`'s
witnesses build one. Pass `reserve_usd` 6.0 and `writer_usd` 2.0.
If the tree base refuses `review` without another keyword, pass the double
the chain's own witnesses pass.

- **The runner double** records `(spec id, predecessor's spec id or
  None)`. It mints its own run and task for the spec, with one closed
  attempt at $1. It sets that task's state to the state its row gives.
  It returns `_outcome` with that run and task, in that state.
  `_outcome`'s default `task_id` of 1 would put two layers on one key.
- **The review double** records the same pair. It returns a fenced `json`
  block. The block holds no findings, or one `scope` blocker for a spec
  routed `escalate`, or one `build` blocker for a spec routed `revise`.
  A spec with a list of routes gets them in turn. A spec routed `wait`
  gets a session with no block and its row's `resets_at`. Every review
  costs 0.
- **The revise double** records the spec id and returns a
  `SpecWriterSession` of a text, cost 0, no error and no reset. Where a
  row gives a revised `touches`, the text is a spec file with the spec's
  id, a title, type `feature`, `budget_usd: 1` and those `touches`.
- **The mint double** records the spec id, and mints a run and a task.
  Where a row gives a `follow_up` text, it records that text on the new
  task, at `.saffron/specs/` plus the spec id and `-f.md`.
- **The end review double** records its call. Where a row gives it a cost,
  it records one `reviewed` Spec lens at that cost with
  `record_end_review`, under the batch's lowest layer. It returns a
  sentinel.
- **The follow-ups double** records its arguments. For each follow-up in
  its row it mints a run and a task and records a `spec_text` of origin
  `follow_up`. It returns each as `_candidate` with the row's budget,
  priority and `touches`, and that `task_id`.

Read the `stack_layers` rows by `batch_key`, with each row's predecessor
spec found through its `predecessor_key`.

**Criterion 1's witness** passes the order `TE-1`, `TE-2`, then `TE-3`
with a `task_id` the witness minted, as the queue hands a re-queued spec.
The follow-ups come back in the order `TE-31`, `TE-27`, `TE-35` and
`TE-29`. Their priorities are 3, 1, 2 and 1, so a sort by id or by
priority reorders them. `TE-27`'s review routes `escalate`.

| spec | runner returns | runner's predecessor |
|---|---|---|
| `TE-1` | `READY_FOR_REVIEW` | `None` |
| `TE-2` | `EXHAUSTED` | `TE-1` |
| `TE-3` | `READY_FOR_REVIEW` | `TE-1` |
| `TE-31` | `READY_FOR_REVIEW` | `TE-3` |
| `TE-27` | never called | |
| `TE-35` | `EXHAUSTED` | `TE-31` |
| `TE-29` | `READY_FOR_REVIEW` | `TE-31` |

It asserts the runner's pairs are exactly the table's, in order. The
review's pairs are the same with `(TE-27, TE-31)` between `TE-31` and
`TE-35`. The mint's calls are `TE-1`, `TE-2` and `TE-3`. `end_review` and
`follow_ups` each run once, in that order, between `TE-3`'s runner call
and `TE-31`'s review. `follow_ups` got the batch's key as text and the
sentinel. The batch's layers are these four.

| spec | position | generation | predecessor |
|---|---|---|---|
| `TE-1` | 1 | 0 | none |
| `TE-3` | 2 | 0 | `TE-1` |
| `TE-31` | 3 | 1 | `TE-3` |
| `TE-29` | 4 | 1 | `TE-31` |

One ` escalated  ` line starts with `TE-27`. No line starts
`follow-ups unrun  `, so none names `TE-27`. The stop reason is
`DRAINED`. These fail it, each measured:

- the follow-ups left unrun, as at the tree base
- a follow-up cut from `base_sha`, which hands `TE-31` `None`
- a follow-up cut from the last follow-up run, which hands `TE-29`
  `TE-35`
- generation 0 for a follow-up
- generation 1 for a candidate the queue handed with a `task_id`, which
  marks `TE-3`
- `mint` only for a candidate with no `task_id`, which leaves `TE-3`
  unminted
- positions counted again from 1 for the follow-ups
- follow-ups run with no review
- `mint` called for a follow-up
- a second `end_review` after the follow-ups, or a second `follow_ups`
- the follow-ups sorted by id, or by priority
- every `Refused` follow-up collected as unrun, which names `TE-27`

**Criterion 2's witness** runs eight batches on one ledger, each with a
budget of 30.0. The runner double costs $1 a call. `SA-0164`'s check
reads `SPEC_WRITER_SESSION_USD` and `SPEC_REVIEW_BUDGET_USD` through the
`saffron.spec_review` module at call time. So batch 7 sets them to 10.0
and 8.0 on that module through `monkeypatch`, and calls their sum of 18
`need`. The check asks for `need` plus the spec's budget.

| batch | order, budgets | follow-ups, budgets | runner returns | end review | stops | runner calls |
|---|---|---|---|---|---|---|
| 1 | `TE-41` 5 | `TE-42` 25 | all ready | $3 | `DRAINED` | `TE-41`, `TE-42` |
| 2 | `TE-43` 5 | `TE-44` 27, `TE-40` 1 | all ready | $3 | `BUDGET` | `TE-43` |
| 3 | `TE-45` 5, `TE-46` 24 | `TE-47` 1 | all ready | none | `BUDGET` | `TE-45` |
| 4 | `TE-48` 5 | `TE-49` 1 | all ready | moves the clock past `until` | `UNTIL` | `TE-48` |
| 5 | `TE-51` 1, `TE-52` 1 | `TE-53` 1, `TE-54` 1 | `TE-52`, `TE-53` `GATE_ERROR` | none | `INFRASTRUCTURE` | `TE-51`, `TE-52`, `TE-53` |
| 6 | `TE-61` 1, `TE-62` 1 | `TE-63` 1 | `TE-62` `REVIEWING` | none | `INCOMPLETE` | all three |
| 7 | `TE-101` 1, then `TE-103` 4, re-queued, routed `revise` | `TE-102` 10, routed `revise` then `run` | all ready | none | `DRAINED` | `TE-101`, `TE-102` |
| 8 | `TE-111` 1 | `TE-112` 1, its review routed `wait` with `resets_at` two hours on | all ready | none | `UNTIL` | `TE-111` |

In batch 1 the spend before `TE-42` is 4, so 26 remain and 25 fits. With
the reserve held, 20 remain, and with the writer's share held, 24. In
batch 2, 26 remain and 27 does not fit. Left out of the spend, the end
review's $3 leaves 29. Batch 4's `until` is an hour after the clock's
start, and the end review double sets the clock a minute past it. Batch 6
emits one line naming `TE-62` as left in flight. Batch 8's `until` is an
hour after the clock's start, so `SA-0148`'s wait stops the batch `UNTIL`.

In batch 7, `TE-103` carries a `task_id` the witness minted, as the queue
hands a re-queued spec. The spend before each revision is 1. `TE-103`'s
check holds both reserves, so 21 remain against its need of 22. With `writer_usd`
released, 23 would remain. `TE-102`'s check holds neither, so 29 remain
against its need of 28. With `writer_usd` held, 27 would remain, and with
`reserve_usd` held, 23. So one dollar separates each side, below
`writer_usd` of 2. Batch 7 calls `revise` once, for `TE-102`. It emits
one ` unrevised  ` line, for `TE-103`.

The `follow-ups unrun  ` lines are these. Batch 2 names `TE-44 TE-40`,
batch 3 `TE-47`, batch 4 `TE-49`, batch 5 `TE-54` and batch 8 `TE-112`.
Batches 1, 6 and 7 print none. These fail it, each measured:

- the reserve still held for the follow-ups, which stops batch 1 at
  `BUDGET`
- the writer's share still held, which stops batch 1 at `BUDGET`
- both still held in the check before a follow-up's revision, which
  leaves `TE-102` unrevised
- only one reserve released in that check, either one, which leaves
  `TE-102` unrevised
- `writer_usd` released for a spec of the order too, which revises
  `TE-103`
- the generation read from the candidate's `task_id`, which revises
  `TE-103`
- follow-ups the batch never reached left out of the unrun line, which
  prints no line for batch 2
- the unrun ids sorted, which prints `TE-40 TE-44`
- a follow-up counted as reviewed once its review is called, which prints
  no line for batch 8
- the spend read from attempts alone, which runs `TE-44`
- the follow-ups run whatever generation 0 stopped on, which runs `TE-47`
- follow-ups run only after a clean `DRAINED`, which leaves `TE-63` unrun
- no `--until` check for a follow-up, which runs `TE-49`
- no budget check for a follow-up, which runs `TE-44`
- the breaker's count reset for the follow-ups, which runs `TE-54`
- the in-flight list dropped between the two, which stops batch 6
  `DRAINED`

**Criterion 3's witness** wraps the ledger's `close_batch` to log each
call beside the doubles' calls, and counts readiness calls.

- A batch of `TE-71`, with an end review at $0.5 and one follow-up
  `TE-72`, both ready. It returns `DRAINED`. The log ends with one close,
  `DRAINED`, after `TE-72`'s runner call. The row's spend is 2.5.
  Readiness ran once.
- A batch of `TE-73` with `follow_ups` of `None` and an end review at
  $0.5. One close, `DRAINED`, after the end review, and a spend of 1.5.
- A batch of `TE-74`, ready at a budget of 1, and one follow-up `TE-75` at
  a budget of 40. It returns `BUDGET`, and the row's status is `BUDGET`.
- Three batches of one spec each. In turn, `end_review` raises
  `RuntimeError("end_review")`, `follow_ups` raises
  `RuntimeError("follow_ups")`, and the readiness check raises
  `RuntimeError("readiness")`. Each raise leaves `run_stack_batch`, and the
  row is `INFRASTRUCTURE` with an `ended_at`. After the readiness raise the
  doubles logged nothing.

`SA-0165`'s callable never raises, so the `follow_ups` raise is the
double's alone. These fail it, each measured:

- the row closed as generation 0's loop returns, which stores a spend of
  1.0
- the row closed with generation 0's reason, which writes `DRAINED` for
  `TE-74`'s batch
- a second close after the first
- readiness checked again for the follow-ups
- no `finally` around the end review and the follow-ups, which leaves the
  row open after a raise

**Criterion 4's witness** first runs an earlier stack batch on the same
ledger, of `TE-79` alone, ready. Its `follow_ups` returns an empty list,
and its `open_prs` recorder is never called. It then passes the order
`TE-81`, `TE-82` and `TE-83`, each with a budget of 1. `TE-82` ends `MERGE_FAILED`, and the
others are ready. The follow-ups come back in the order `TE-91` touching
`a.py`, `TE-96` touching `e.py`, `TE-92` touching `b.py`, `TE-93` touching
`d.py` and `TE-94` touching `c.py`. `TE-91` and `TE-94` return ready. `open_prs`
records the length of the doubles' log when it is called, and returns six
pull requests.

| number | head branch | changed file |
|---|---|---|
| 1 | `saffron/TE-81` | `a.py` |
| 2 | `saffron/TE-82` | `b.py` |
| 3 | `saffron/TE-83` | `c.py` |
| 4 | `saffron/SA-9000` | `d.py` |
| 5 | `saffron/TE-79` | `e.py` |
| 6 | `saffron/TE-91` | `a.py` |

Each pull request's url ends `/pull/<number>`. It asserts the runner's
follow-up pairs are `(TE-91, TE-83)` then `(TE-94, TE-91)`, and the
review's follow-up ids are `TE-91` then `TE-94`. It asserts one
` refused  ` line for each of `TE-96`, naming `/pull/5`, `TE-92`, naming
`/pull/2`, and `TE-93`, naming `/pull/4`, and no other. It asserts one
line `follow-ups unrun  TE-96 TE-92 TE-93`. `open_prs` ran once, right after
`follow_ups`. The stop reason is `DRAINED`. `TE-91`'s overlaps are with a
layer below its predecessor and with its own branch. `TE-94`'s is with a
layer that stopped being the predecessor. These fail it, each measured:

- no refusal for a follow-up, as at the tree base
- nothing exempt, which refuses `TE-91`
- the predecessor's branch alone exempt, which refuses `TE-91` and
  `TE-94`
- the own-branch skip left to the caller's set, which refuses `TE-91` on
  pull request 6
- every task of the batch exempt, which runs `TE-92`
- every open pull request exempt, which runs `TE-93`
- the layers of every batch exempt, read from `stack_layers`, which runs
  `TE-96`
- every task at `READY_FOR_REVIEW` exempt, which runs `TE-96`
- a refusal counted as an abort, which fires the breaker before `TE-94`
- the list read again before each follow-up
- a review before the refusal
- no `follow-ups unrun  ` line
- the unrun ids sorted, which prints `TE-92 TE-93 TE-96`
- `open_prs` called whenever `follow_ups` is given, which calls it for
  `TE-79`'s batch

**Criterion 5's witness** follows `SA-0156`'s wiring witness, with
`_readiness_passes` and `_fake_batch_resolution`
(`tests/test_cli.py:2603-2640`). `_resolve_queue` returns that resolution
with `repo_slug` set by `dataclasses.replace`. A fake `run_stack_batch`
records its keywords and returns `DRAINED`. `cli.run_gh` is replaced with a
recorder that returns exit 0 and a JSON list of one pull request. It runs
`main` with `batch --stack --budget 40` three times, and reads the output
with `capsys` after each call of the callable.

- Slug `o/r`. After `main`, no `gh` ran. The `open_prs` it got returns the
  one pull request, and the `gh` argv holds `o/r`. No `note:` line names
  `_GH_REFUSALS_SKIPPED`.
- Slug `o/r`, with `cli.run_gh` raising `OSError("no gh")`. The callable
  returns an empty list and raises nothing. The output holds one `note:`
  line with `gh could not be run` and `_GH_REFUSALS_SKIPPED`.
- No slug. The callable returns an empty list, and no `gh` ran. The
  output holds one `note:` line with `no GitHub slug could be read` and
  `_GH_REFUSALS_SKIPPED`.

It then fails readiness, as `SA-0144`'s witness does, and asserts
`open_prs` is `None`. These are unmeasured, since the `--stack` path is
not at `68892367`:

- no `open_prs` passed
- the list read as the callable is built, so `gh` runs before `main`
  returns
- `run_gh` called unguarded, which raises `OSError`
- a `gh` run with no slug
- no `note:` line for no slug, or for a `gh` that could not start
- a callable passed after a readiness failure

**Criterion 6's witness** runs one batch with a budget of 30 and
`follow_ups` of `None`. It sets `SPEC_WRITER_SESSION_USD` and
`SPEC_REVIEW_BUDGET_USD` to 1.0 each on the `saffron.spec_review` module
through `monkeypatch`, as batch 7 does. Its order is `TE-141` to `TE-148`,
each with a budget of 1 and `touches` of `m.py`, but `TE-146`'s of
`d.py`. `TE-142` ends `MERGE_FAILED`, and the rest are ready. The mint
double records a `follow_up` text on `TE-148`'s task, a spec file whose
`touches` are `m.py` and `d.py`. A spec with a revised `touches` below
routes `revise`, then `run`, and every other spec routes `run`.
`open_prs` records the length of the doubles' log when it is called, and
returns three pull requests.

| number | head branch | changed file |
|---|---|---|
| 1 | `saffron/TE-141` | `a.py` |
| 2 | `saffron/TE-142` | `b.py` |
| 3 | `saffron/SA-9000` | `d.py` |

| spec | its task's texts | revised `touches` | predecessor | outcome |
|---|---|---|---|---|
| `TE-141` | none | none | none | runs |
| `TE-142` | none | none | `TE-141` | runs, and ends `MERGE_FAILED` |
| `TE-143` | a revision | `m.py`, `n.py` | `TE-141` | runs |
| `TE-144` | a revision | `m.py`, `b.py` | `TE-143` | refused, naming `/pull/2` |
| `TE-145` | a revision | `m.py`, `d.py` | `TE-143` | refused, naming `/pull/3` |
| `TE-146` | none | none | `TE-143` | runs |
| `TE-147` | a revision | `m.py`, `a.py` | `TE-146` | runs |
| `TE-148` | a `follow_up` | none | `TE-147` | runs |

**The margins.** A revision's check holds back `reserve_usd` and
`writer_usd`, 8 together, and needs 1.0 plus 1.0 plus the spec's budget
of 1, so 3. Each runner call costs 1, and nothing else costs. The most
spent before a revision is 4, before `TE-147`, so the least left is 18.
Every revision in the table runs. With the real constants, 18.5 and 6.0,
the need is 25.5 against at most 22 left, and every revision would stay
unrevised.

It asserts the runner's spec ids are `TE-141`, `TE-142`, `TE-143`,
`TE-146`, `TE-147` and `TE-148`, in order. The layers are the same less
`TE-142`. It asserts `revise` ran once each for `TE-143`, `TE-144`,
`TE-145` and `TE-147`. It asserts one ` refused  ` line each for
`TE-144` and `TE-145`, each naming the url the table gives, and no
other. `open_prs` ran four times, each right after the last review of
`TE-143`, `TE-144`, `TE-145` and `TE-147` in turn. The stop reason is
`DRAINED`. These fail it, each unmeasured:

- no check on a revised spec, as at the tree base, which runs `TE-145`
- the queued `touches` checked in place of the revision's, which runs
  `TE-144` and `TE-145`
- the check before the review, where no revision is recorded yet, which
  runs `TE-145`
- nothing exempt, which refuses `TE-147`
- the predecessor's branch alone exempt, which refuses `TE-147`
- every task of the batch exempt, which runs `TE-144`
- every spec of the order checked, revised or not, which refuses `TE-146`
- the check on any spec text, whatever its origin, which refuses `TE-148`
- one read for the whole order, which calls `open_prs` once
- a refusal counted as an abort, which fires the breaker before `TE-146`

**How the lists were measured.** A throwaway simulation ran on 2026-09-24
at `68892367`. It stood in for the chain's loop: `_drive`'s checks,
`SA-0143`'s handoff, `SA-0145`'s layers, `SA-0149`'s routing, `SA-0153`'s
reserve and end review, `SA-0155`'s mint, `SA-0164`'s revision check and
`SA-0173`'s `follow_ups`. It ran a real `Ledger` with the two tables
added, and a `batch_spend` that adds the `end_reviews` rows. Criterion 4
ran a prototype of the moved refusal function against the real
`scheduler.py`. The right build passed criteria 1 to 4. Each wrong build
listed as measured failed its own witness. Batch 7 ran with the
constants of that day, a writer session of 12.5 and a review of 6.0, so
a `need` of 18.5. Today's sum is 24.5. The witness patches both, so its
`need` of 18 and its one-dollar margins hold either way. Criterion 5 needs `SA-0144`'s
`--stack` path, so nothing ran it. Criterion 6 came after the simulation,
so nothing ran it either.

**What the witnesses leave undriven.**

- A follow-up routed `error` or `wait`. The same wrapper routes it as it
  routes a spec of the order.
- A generation 0 that stops `UNTIL` or `INFRASTRUCTURE`. Its first
  follow-up would meet the same check and stop the same way, so a build
  that runs follow-ups after either is indistinguishable here.
- `open_prs` after a generation 0 that did not drain. Criterion 4 drives
  an empty list of follow-ups alone.
- A raise from `open_prs`. It leaves `run_stack_batch` like any raise
  after the loop, and the row closes `INFRASTRUCTURE`.
- A follow-up left unrevised. It was reviewed, so it is not unrun, as
  Problem 4 states. Criterion 1 drives the escalated and missed cases.
- The same-spec refusal on a revised spec of the order. The item 3
  function runs it too, and criterion 6 claims only the overlap. A revision keeps the
  spec's id (`SA-0150`), so its branch is the one the plan checked.
- A revised text `parse_spec` refuses. It meets no check here, and
  `SA-0150`'s `run_task` refuses it before its cell.
- A revised spec of the order with `open_prs` of `None`. Criterion 2's
  batch 7 passes none, but its one spec of the order stays unrevised.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). A
prototype of this change, formatted by `ruff format`, measured 2173
changed tokens with `size_gate` itself. `batch.py` took 407,
`scheduler.py` 197, `cli.py` 89, `tests/test_batch.py` 1315 and
`tests/test_cli.py` 165. The prototype's `batch.py` stood in for the
chain's wrapper and the verdict-route record, so allow about 170 more
there. Criterion 6 adds about 60 to `batch.py` and about 260 to
`tests/test_batch.py`, reasoned from criterion 4's share. That is about
2660, 89% of the ceiling, and past the 80% a spec aims under. Keep the
doubles in one shared class, and criterion 6's witness on them.
