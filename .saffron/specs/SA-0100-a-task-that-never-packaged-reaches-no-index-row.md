---
id: SA-0100
title: a task that never reached PACKAGE reaches no index row, so the page ranks eight states it can never show
type: bug
priority: 2
depends_on: []
touches:
  - saffron/task.py
  - tests/test_task.py
forbidden:
  - tests/test_report.py
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/report/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/replay.py
  - saffron/events.py
budget_usd: 16
max_turns: 90
acceptance:
  - claim: >-
      A task whose cell ended in a state other than READY_FOR_REVIEW reaches
      the index with a row carrying that state. Two different such states each
      produce their own row, and each row reads back with the state its own
      cell ended in. Today neither reaches the store at all.
    witness: tests/test_task.py::test_a_task_that_never_packaged_still_reaches_the_index
  - claim: >-
      The row for a task that never packaged carries an empty link. It carries
      no branch name, no mirror path and no invented pull request address, and
      its note says what happened instead.
    witness: tests/test_task.py::test_an_unpackaged_row_carries_no_pull_request_link
  - claim: >-
      A spec whose first task ended unpackaged and whose second task packaged
      leaves one row, holding the packaged outcome and still carrying the pull
      request link PACKAGE wrote. The earlier unpackaged row is replaced rather
      than joined by a second row, and the new write never replaces a packaged
      row's link with an empty one.
    witness: tests/test_task.py::test_a_later_package_replaces_the_unpackaged_row_and_keeps_its_link
  - claim: >-
      Appending a row for a spec that already has one still replaces it rather
      than doubling it, keyed on repo and spec id together.
    witness: tests/test_report.py::test_re_running_a_spec_replaces_its_row_rather_than_doubling_it
    preserves: true
---

## Context

`DESIGN.md` §6 makes the index the page an operator reads first. Its sort order
puts at level 2 "every state that needs you and is not a reviewable diff", and
names eight of them: `MERGE_FAILED`, `PLAN_REJECTED`, `PREFLIGHT_FAILED`,
`GATE_ERROR`, `NOT_IMPLEMENTED`, `EXHAUSTED`, `ORPHANED` and `RATE_LIMITED`.

`saffron/report/index.py` implements that. `_STATE_RANK` ranks twelve states,
including all eight, plus `REVIEWING` and `REBUTTING` at the elevated-risk
level. Its own comment says why each was added: "Absent, they fell to
`_ORDINARY` and sorted below elevated-risk green tasks: a task that could not
pass its own gates, or one whose cell died, reading as reviewable."

Ten of those twelve states can never appear on the page.

`append_queue_line` has exactly two callers. One is `saffron/replay.py:143`,
which is v0 and agent-free. The other is `saffron/phases/package.py:966`,
inside `_finish`. A task reaches `_finish` only by reaching PACKAGE, and
`saffron/task.py:317` gates that on one condition: `outcome.state ==
"READY_FOR_REVIEW"`. Every other outcome takes the `else:` at
`saffron/task.py:335`, which calls `push_unpackaged_work` at `:341`, prints one
line at `:352`, and returns at `:353`. No row is written.

Measured 2026-09-17 against `~/.saffron/ledger.db` and
`~/.saffron/batches/v0/queue.json`: the ledger holds **99** tasks and the store
holds **68** rows. The 68 are the 65 `MERGED` tasks and the 3 at
`READY_FOR_REVIEW`. The missing 31 are `EXHAUSTED` 9, `NOT_IMPLEMENTED` 8,
`ORPHANED` 7, `PLAN_REJECTED` 3, `REBUTTING` 1, `RATE_LIMITED` 1,
`PREFLIGHT_FAILED` 1 and `GATE_ERROR` 1.

So the page an operator triages in ten seconds is blind to a third of the
tasks. It is blind by construction to the ones ranked most urgent.

**One omission here is deliberate, and it is not this one.** `_finish` at
`saffron/phases/package.py:955-958` documents its own. A PACKAGE that raises
writes neither the ledger state nor the row. Its stated reason is that "an
index line whose link points at a pull request that was never opened is worse
than no line". That reasoning is sound, and it is about a link that would be
wrong. It says nothing about a task that never entered PACKAGE, which has no
link because no pull request exists, and `QueueLine.link` is a plain string.

**The second omission is also deliberate, and its reason is why the fix does
not belong in PACKAGE.** `PushResult` in `saffron/phases/package.py` is
"Deliberately not `PackageResult`: that type's `state` field feeds `_finish` (a
ledger state write and a queue line) and neither happens here (§0's own
boundary: this is not packaging)." That boundary is correct. Packaging is not
what produced an `EXHAUSTED` task, so PACKAGE is the wrong place to record one.

The right place is the caller. `saffron/task.py` is the only module that drives
a task end to end, and `CLAUDE.md` names it so. It already holds both branches,
already knows the terminal state, and already prints it.

## Problem

- **Ten of twelve ranked states cannot reach the page.** The ranking was
  written, reviewed and tested against states no row can carry.
- **A third of this repo's own tasks are invisible.** 31 of 99, and every one
  of them is a task that needed a person.
- **The two states an operator most needs are the two most often missing.** A
  cell that died leaves `ORPHANED`. A task that could not pass its own gates
  leaves `EXHAUSTED`. Together they account for 16 of the 31.
- **The header undercounts.** `tasks` and `spend` are computed from the stored
  rows, so both report a night smaller and cheaper than it was.

## Out of scope

**What a PACKAGE that raises does.** It still writes no row, and no criterion
here weakens that. `saffron/phases/**` is forbidden, so `scope` refuses the
edit that would.

**Moving the index off `queue.json` and onto the ledger.** §6 calls that
source "currently undecided rather than chosen". The ledger cannot reproduce
the store today, because the diff stat sits in no column. That decision belongs
to a person, not to this cell. `saffron/report/**` and `saffron/ledger.py` are
both forbidden.

**The batch header's six fields.** Wall clock, per-repo preflight and the
trailing accept rate all have their own gaps. This spec adds rows, and the
header's two computed counts follow from them.

**`saffron/replay.py`.** It is v0, agent-free, and writes its own row already.
It is forbidden.

**Changing `QueueLine` or `_STATE_RANK`.** Every field an unpackaged task needs
already exists, and every state it can end in is already ranked. A change to
either is a sign the row is being reshaped rather than written.

## Notes for the agent

**This spec's change is new code.** Three criteria declare a witness and no
mutant. The call does not exist, so no text pins honestly, and the spelling is
yours. Expect `witness` to report `skip` for those three. The fourth criterion
is `preserves` over `tests/test_report.py:1622`, which must keep passing.

**`tests/test_task.py` does not exist yet, and that is the reason it is in
`touches`.** Nothing tests `run_task` directly today. Two test files name it
only in comments. Create the file and drive `run_task` in it.

**The seams are patchable at module scope.** `saffron/task.py` imports
`run_one_cell` into its own namespace, so a test replaces
`saffron.task.run_one_cell`. It imports `package as package_phase`, so a test
replaces `push_unpackaged_work` on that module object. Build the doubles from
those two points and pass a real `out_dir`.

**Criterion 1's plausible wrong implementation is a row for one state.** Two
shapes do it. A write guarded by a state list, and a write placed inside a
branch only some outcomes reach. Each satisfies a single-state test and leaves
the hole open. Drive two states that differ, and assert each row carries its
own.

**Criterion 2's plausible wrong implementation is the cell branch in `link`.**
`push_unpackaged_work` returns a branch and a pushed sha on success. Putting
either in `link` renders a row whose link is not a pull request. The index is an
index, and the diffs live in GitHub (§6). An empty link is correct.
Assert the branch name is absent from the row, not only that the link is falsy.

**Criterion 3 is the upsert exercised through the new path.** One row must
survive, and it must keep its link. Writing the unpackaged row after the packaged
one, or keying on the spec id alone, produces two rows or the wrong survivor.
Drive the unpackaged task first, then the packaged one, and assert the store
holds one row whose link is the pull request address.

**The write goes inside the `else:` at `saffron/task.py:335`, and nowhere else.**
This is the one placement that matters. A write at the end of `run_task` passes
criteria 1 and 2. It also passes criterion 3's first wording, while it destroys
every pull request link in the index. The packaged branch reaches
`_finish`, which writes the row with `link=result.pr_url`
(`saffron/phases/package.py:966-978`). Then `saffron/task.py:334` assigns
`outcome.state = result.state`. So a later upsert keyed on the same repo and spec
replaces that row. The surviving state reads as the packaged one, and the link
reads empty. That is `_finish`'s own warning with the sign reversed: a row whose
link points nowhere, for every task that succeeded.

**The upsert key is `repo.name`.** `_finish` takes it as its fifth positional
argument (`saffron/phases/package.py:690`), and `append_queue_line` keys on repo
and spec id together. A new write using `str(repo)` or a resolved path produces
two rows per spec in production while the witness shows one. Assert the row's
`repo` equals `repo.name` rather than trusting the count alone.

**Share one builder across the three tests.** Each needs a `Spec`, a
`ResolvedCeilings`, a `PinnedBase`, a ledger, two doubles and a real `out_dir`.
Written out three times that is most of the `bug` ceiling of 300 changed lines,
before the fix itself. One helper and three short tests fit.

**`tests/test_cli.py` drives this branch and is forbidden.**
`tests/test_cli.py:117-127` and `:174-177` push `EXHAUSTED` and
`PREFLIGHT_FAILED` outcomes through `run_task`, so both will newly write a
`queue.json`. Neither asserts on the store, and `append_queue_line` makes its own
directory, so both stay green. If one breaks, `scope` forbids you from fixing it.
Stop and say so in the pull request body rather than widening the diff.

**The row's state is the cell's own terminal state.** Never map an unpackaged
outcome onto a packaging state. A row reading `READY_FOR_REVIEW` for a task
that never packaged is worse than the missing row. It invites an operator to
review a branch that no gate judged.

**Do not write a row for a task the queue refused.** A refusal produces no
task, no cell and no outcome. It has no state to carry. `SKIPPED` at rank 0
is a repo that produced nothing, which is a different record and not yours.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Commit after each coherent step. Uncommitted work dies with the cell.
