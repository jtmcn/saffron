---
id: SA-0050
title: the scan resolves a queue and nothing executes it, so a night cannot happen
type: feature
priority: 1
depends_on:
  - SA-0049
touches:
  - saffron/batch.py
  - tests/test_batch.py
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
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 16
max_attempts: 4
max_turns: 110
risk: standard
acceptance:
  - claim: >-
      A queue that drains runs every candidate once, in the order it was
      handed, through an injected runner, and returns DRAINED. An empty queue
      drains immediately rather than being a special case — a night with
      nothing to do ended by draining.
    witness: tests/test_batch.py::test_a_drained_queue_runs_every_candidate_once_in_order
  - claim: >-
      The budget gate is one comparison before each task — the batch's
      uncommitted budget against that task's own budget_usd — and a task that
      does not fit is never started. §4.2.1 at K=1: the reserved-budget
      machinery exists only to stop K tasks passing the gate on the same last
      $12, and at K=1 that race cannot occur. The stop reason is BUDGET.
    witness: tests/test_batch.py::test_the_budget_gate_is_one_comparison_before_each_task
  - claim: >-
      A task admitted under the gate that then overshoots its own budget_usd
      does not stop the batch on that account. The batch ceiling is what binds;
      a task's ceiling is best-effort and enforced inside the cell, which is
      backlog item 44's decision and the reason the gate is checked before a
      task rather than after.
    witness: tests/test_batch.py::test_a_task_overshooting_its_own_budget_does_not_stop_the_batch
  - claim: >-
      The deadline is read from an injected clock, never a bare wall-clock call
      inside the loop, and is compared before starting a task rather than
      during one. The stop reason is UNTIL. An eight-hour window is untestable
      any other way, and a test that has to wait is a test nobody runs.
    witness: tests/test_batch.py::test_the_until_deadline_is_read_from_an_injected_clock
  - claim: >-
      Two consecutive aborts stop the batch as INFRASTRUCTURE and no further
      task is started. What counts is exactly GATE_ERROR, PREFLIGHT_FAILED and
      RATE_LIMITED — enumerated here, never taken from scheduler.REQUEUE_STATES,
      which also contains CHANGES_REQUESTED and ORPHANED and would count two
      states a task earned as aborts.
    witness: tests/test_batch.py::test_two_consecutive_aborts_fire_the_breaker
  - claim: >-
      A state a task earned resets the counter, up to and including EXHAUSTED,
      so an EXHAUSTED between two aborts prevents the fire. §4.2.1 names this
      as the one most likely to be got wrong: "any terminal state" would reset
      on GATE_ERROR and PREFLIGHT_FAILED themselves, which are terminal, and
      the counter would never reach two.
    witness: tests/test_batch.py::test_an_exhausted_task_between_two_aborts_resets_the_breaker
  - claim: >-
      A batches row is opened when the night starts and closed with the reason
      it stopped, through the writer SA-0049 added. Every stop path closes it,
      including the breaker and a readiness failure — a night that ends with no
      ended_at and no status is indistinguishable from one still running, which
      is the state §6's morning queue reads.
    witness: tests/test_batch.py::test_every_stop_path_closes_the_batch_row_with_its_reason
  - claim: >-
      Each run the night produces is attached to the batch. runs.batch_id is
      nullable and create_run does not take one, so without this stamp the
      column is written by nobody, every join through it returns nothing, and
      the spend SA-0049 derives is zero for every real night.
    witness: tests/test_batch.py::test_each_run_is_attached_to_the_batch_it_ran_under
  - claim: >-
      A readiness failure ends the night as INFRASTRUCTURE with the batch row
      opened and closed and no task started. §4.4 step 1 skips a repo that
      fails preflight rather than treating it as fatal; at one repo the skip is
      the whole night, and it has to leave a row behind or an expired token at
      22:00 produces a night with no record that it was attempted.
    witness: tests/test_batch.py::test_a_readiness_failure_closes_the_batch_without_starting_a_task
---

## Context

§4.2.1: *"K = 1, and the scheduler is a `for` loop over a sorted list."*
Ordering is priority then FIFO, *"sorted once in memory"* — which is what
`build_queue` already returns.

*"A batch ends four ways, and says which. The queue drains, the budget is gone,
`--until` hits, or the breaker fires."* The four are the `status` values
`SA-0045` already put a `CHECK` on: `DRAINED`, `BUDGET`, `UNTIL`,
`INFRASTRUCTURE`.

Backlog item 58 is the standing item: nothing in Saffron runs more than one
cell, so §9's v1 criterion — an unattended night — is structurally unreachable.
Every mechanism up to the sort exists. The consumer does not.

## Problem

- **The queue is printed and abandoned.** `saffron queue` resolves candidates
  and prints them. Nothing consumes the list.
- **A batch has four ways to end and no way to say which.** The column exists
  with its `CHECK`; no code path writes it.
- **`runs.batch_id` connects nothing.** `create_run` does not take a batch, and
  the only caller is inside `run_one_cell`, which this spec may not edit.
- **Two consecutive aborts would burn the night to learn one fact.** Each
  remaining task pays a preflight and a baseline suite to die of the same
  global condition.

## Out of scope

**The command.** `saffron/cli.py` is `forbidden`. `SA-0051` adds
`saffron batch`, its flags and its exit codes, and it is the spec that extracts
the scan so `queue` and `batch` share one.

**Resolving the queue.** `run_batch` takes the sorted candidates as an
argument. `_queue` already resolves the mirror, exports `.saffron/` at
`base_sha` and calls `build_queue` using four `cli`-private helpers; `cli.py`
is `forbidden`, so re-deriving the scan here would mean copying them. Taking
the resolved list is also what makes every witness above injectable.

**Stamping a corpse `ORPHANED`.** §4.2.1 requires the *batch scan* to pass
`reconcile(..., stamp_orphaned=True)` — deliberately not what `saffron queue`
does, and its docstring says why. That belongs with the scan, which is
`SA-0051`'s, and this spec never calls `reconcile`.

**Concurrency.** K=1. No pool, no `--concurrency`, no reserved-budget
arithmetic — §4.2.1 cuts all three and names the night each returns.

**Multi-repo.** v2 (§9). `run_batch` takes one repo, so §4.4's per-repo
baseline and skipped-repo lines have nothing to iterate yet.

**`saffron gc` (§4.5).** Deferred at K=1. The disk *check* is not deferred with
it and already landed in `SA-0048`.

**Rendering the night.** `saffron/report/**` is `forbidden`.

## Notes for the agent

**Everything the loop reaches out to is injected, and that is the whole test
strategy.** The cell runner, the clock and the readiness check each take a real
default bound as a keyword — the shape `scheduler.build_queue` uses for `gh`
and `phases/package.py` uses for its runner. An eight-hour window, a live
token probe and a real cell are all untestable; a fake clock, a callable
returning canned `CellOutcome`s and a stub readiness are not. **If a criterion
above seems to need a real night, the seam is in the wrong place.**

**Do not reuse `scheduler.REQUEUE_STATES` for the breaker.** It is the right
list for a different question — what re-queues tomorrow — and it contains
`CHANGES_REQUESTED` and `ORPHANED`, both of which a task *earned*. The breaker
counts three states and they are worth naming in their own frozenset in this
module, with a comment saying which set it is deliberately not.

**Attach the run after the cell returns, not at creation.** `CellOutcome`
carries `run_id`. `create_run` takes no batch and lives in `saffron/ledger.py`;
the call that mints the run is in `run_one_cell`, in `saffron/cell/**`. Both
are `forbidden`, so the stamp is a ledger method `SA-0049` adds and this spec
calls once per task. It is the shape `record_push` and `set_task_package`
already use on `tasks`: the row exists, then the fact about it arrives.

**Read the batch's spend back; do not keep a tally.** `task_spend`'s docstring
is the instruction — *"a caller whose own tally lost a frame reads it back
rather than reporting the gap"* — and `CellOutcome.spent_usd` is exactly such a
tally: its own docstring says the field is defaulted because several early
returns precede the binding. `SA-0049` exposes the batch's derived spend as a
reader; the budget gate calls it.

**Order the checks and say so in one comment.** Before each task: the deadline,
then the budget, then the breaker's standing count. The batch row is closed
once, on whichever fired.

**`saffron/batch.py` is a new file, and §10's layout does not list it.** That
layout also lists `supervisor.py`, `gc.py` and `cell/database.py`, none of
which exist, while the module it does name for this job — `scheduler.py` — is
the scan, is `forbidden` here, and has an open pull request against it. A new
module is right; `DESIGN.md` is protected and Task 8 corrects §10 by hand.

**`risk: standard`, and it is a declaration rather than an oversight.**
`saffron/batch.py` is in no `elevate_on` pattern, so `size` is advisory here.
That is deliberate and it is why `SA-0049` exists as a separate spec: this is
the widest piece of the batch work, and item 25 measured what the strictest
ceiling does to the widest spec — `SA-0009`, 990 changed lines against a
600-line `feature` ceiling, `EXHAUSTED` at $31.60 with nothing merged. Advisory
is not permission to sprawl; the critic still reads the diff.

**No new test may carry the `cell` marker.** `pyproject.toml` sets
`addopts = "-m 'not cell'"` and the `tests` gate passes the same argv to
`--collect-only`, so a cell-marked witness is never collected at head,
`criteria` reports `witness-not-collected`, and the attempt is spent on a test
that was correct. Nothing here needs a container — that is what the injected
runner is for.

**Nothing calls `run_batch` when this merges, and that is the plan.**
`SA-0051` is the first caller. Do not add one: `saffron/cli.py` is `forbidden`,
so wiring the command would fail `scope` on every attempt.
