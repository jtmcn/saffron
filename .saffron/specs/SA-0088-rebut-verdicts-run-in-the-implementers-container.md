---
id: SA-0088
title: REBUT's verdict lenses run in the container the implementer just rebutted from, so the critic's second look has the same hole as its first
type: bug
priority: 1
depends_on: [SA-0087]
touches:
  - saffron/phases/rebut.py
  - saffron/cell/session.py
  - tests/test_rebut.py
  - tests/test_session.py
  - tests/test_events.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/package.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/replay.py
budget_usd: 16
max_attempts: 3
max_turns: 80
risk: elevated
acceptance:
  - claim: >-
      `run_rebut` runs its verdict sessions in a container its caller hands it
      for them, separate from the one the rebuttal turn runs in. Today one
      container serves both, so the lens judging a rebuttal runs where the
      rebutting implementer just had root.
    witness: tests/test_rebut.py::test_the_verdict_sessions_never_run_in_the_rebuttals_container
  - claim: >-
      In a task that reaches REBUT, the verdict sessions run in a critic cell
      whose tree is the base with the post-rebuttal patch applied, and the
      diff they are shown is read from that cell.
    witness: tests/test_session.py::test_rebut_verdicts_read_a_tree_rebuilt_from_the_post_rebuttal_patch
  - claim: >-
      Each lens still verdicts only its own blockers, in a fresh session that
      never resumes another, as it does today.
    witness: tests/test_rebut.py::test_each_lens_verdicts_its_own_blockers_and_never_resumes
    preserves: true
  - claim: >-
      A verdict still lands on the finding REVIEW recorded.
    witness: tests/test_session.py::test_a_verdict_lands_on_the_finding_the_review_recorded
    preserves: true
---

## Context

backlog item **118**, the third of four. `SA-0087` built the
critic cell and moved REVIEW into it. REBUT has the same shape one phase later.
`rebut.run_rebut(container, ...)` takes one container. It runs the rebuttal
turn there, which resumes the implementer's session and may commit fixes. It
then runs one verdict session per lens there too, over `diff()`, which reads
through that container's `.git`.

The rebuttal turn belongs in the implementer's cell: it is the implementer.
The verdicts do not. A verdict session is the critic, and it should judge the
post-rebuttal patch in a container the implementer never ran in, for the
reasons `SA-0087` gives for REVIEW.

## Problem

After `SA-0087`, REVIEW judges the shipped patch in a critic cell, but the
verdict that decides whether a blocker stands still runs in the implementer's
container. The last word on a blocker has the hole the first word no longer
has.

## Out of scope

**The gate re-run after the rebuttal.** `rerun_gates` stays in the
implementer's cell. `SA-0086`'s re-verification at PACKAGE is the verdict of
record on the post-rebuttal commit.

**The rebuttal turn itself**, which stays in the implementer's container.

**Changing how the critic cell is built.** Reuse `SA-0087`'s function. If it
needs a new argument to take the post-rebuttal patch, add it there, in
`session.py`.

## Notes for the agent

**The criteria carry witnesses and no mutants.** The new parameter and the
wiring are new code, so no text exists yet that a mutant could pin honestly.
`witness` will report `skip`, and that is expected.

**Build the critic cell after the rebuttal and the gate re-run, not before.**
The verdicts judge the patch as the rebuttal left it. `run_rebut` returns
early when nothing moved and nothing was argued, and when the re-run is red.
Neither path runs a verdict, so neither should pay for a critic cell.
Take a zero-argument callable that returns the critic container, and call
it only after `rerun_gates()` returns `None`. A plain container argument
cannot do this: the caller evaluates it before `run_rebut` is entered, so
both early paths pay for the cell anyway, and its tree is the one from
*before* the rebuttal's commits — which criterion 2 and `DESIGN.md` §5.6
both forbid.

`tests/test_events.py` is the third caller of `run_rebut`
(`test_the_watch_shaped_callable_phases_still_receive_does_not_raise`), and
a required parameter makes it a `TypeError`. It is in `touches` for that
line alone; `tests/fixtures/watch-golden.txt` must not change, and does
not, because no green run reaches REBUT.

**`diff()` and the verdicts must read the same tree.** Whatever the verdict
prompt carries as the new diff has to come from the critic cell, not from the
implementer's `.git`.

**Criterion 2 claims two things, so its witness observes both.** "The verdict
sessions run in a critic cell" and "the diff they are shown is read from that
cell" are separate, and a build that threads the critic container into the
verdict sessions alone — leaving the `diff` closure reading the implementer's
`.git`, as `session.py` does today — satisfies the first, passes a witness that
watches only where the sessions ran, and leaves the half this spec exists for
false. Item 118 records the identical omission in `SA-0087`'s second criterion,
where pointing `read_head` at the implementer's own container passed all 157
tests in `tests/test_session.py`; `SA-0087` was amended for it and now says to
record which container `export_patch` ran in. Do the same here: record which
container the call feeding the verdict prompt's diff ran in and assert it is
the critic cell's, and assert the patch that cell applied carries the
rebuttal's own commit.

**The REBUT critic cell is torn down the way REVIEW's is.** `SA-0087` makes
that a criterion of its own — container, worktree volume and state volume
removed when the phase ends, a raising lens included. If the function you reuse
owns that `finally` itself, reuse is enough; if its caller owns it, the caller
in `session.py` repeats it here. A witness would see the leak: the
`tests/test_session.py` runtime stub appends every removal to `cell.removed`,
which is the seam `SA-0087`'s own teardown witness reads.

**A post-rebuttal patch that will not apply ends the task the same two ways.**
§5.5's rule does not change at REBUT: a patch that will not apply to its own
base ends `EXHAUSTED`, and the binary-change exception ends `GATE_ERROR`. What
does change is where the ending is produced — `run_rebut` returns a
`RebutResult` carrying its own `state` and `why`, and the rebuttal turn and the
gate re-run have already been paid for. An exception escaping `run_rebut`
instead would be charged to nobody.

**Test both halves at their own seams.** `tests/test_rebut.py` drives
`run_rebut` with a recording agent. Hand it two distinct container names and
assert which turns ran where. `tests/test_session.py`'s `_drive` drives the
whole task, the way `SA-0087`'s witnesses do. Every new witness must fail with
the source reverted. Reverted, `run_rebut` has one container, so a call
passing a second one fails, and the session wiring runs verdicts in the
implementer's container. Import nothing new at module scope: a module-scope
import of a name you add turns the reverted run into a collection error, which
`revert` reads as `skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
