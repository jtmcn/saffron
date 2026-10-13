---
id: SA-0287
title: A lens that errors halts its task at `REVIEWING`, so a stamping scan reads the halt as a crash
type: bug
priority: 2
depends_on: [SA-0276, SA-0273, SA-0282]
estimated_lines: 110
estimate_measured: true
touches:
  - saffron/phases/review.py
  - tests/test_review.py
  - tests/test_session.py
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
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/cell/**
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - saffron/phases/implement.py
  - tests/test_scheduler.py
  - tests/test_reconcile.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_cli.py
  - tests/test_report.py
  - tests/test_rebut.py
  - tests/test_accept_rate.py
  - tests/test_spec_loop_driver.py
  - tests/test_view_graph.py
budget_usd: 25
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      `review_state` ends `REVIEW_INCOMPLETE` when any lens carries an error.
      The witness drives an errored lens alone and beside a clean lens. It
      also drives it beside an anchored blocker and beside an anchored
      concern, each once before it and once after it. Each case keeps its
      line naming the errored lens and saying the review is incomplete.
      With no errored lens, a review with no findings and one with a concern
      still end `READY_FOR_REVIEW`, and one with a blocker still ends
      `REBUTTING`.
    witness: tests/test_review.py::test_a_lens_that_errored_ends_review_incomplete_whatever_the_others_found
    mutant:
      file: saffron/phases/review.py
      find: |-
        "REVIEW_INCOMPLETE",
                    f"{errored} produced no findings
      replace: |-
        "REVIEWING",
                    f"{errored} produced no findings
    wrong_versions:
      - The new state returned only when every lens errored, so an errored lens beside a clean one ends `READY_FOR_REVIEW`.
      - The blocker check moved ahead of the errored check, so an errored lens beside an anchored blocker ends `REBUTTING`.
      - The errored check reads only the first lens, so an errored lens after a lens with findings goes unseen.
      - The new state returned for any review with no anchored finding, so a clean review reads as incomplete.
  - claim: >-
      `run_one_cell` returns `REVIEW_INCOMPLETE` for a lens whose session
      failed, and writes it to the task row. `on_state` still hears
      `REVIEWING` as REVIEW starts. A reconcile that stamps orphans then
      leaves that row as it is, while it stamps a `REVIEWING` row beside it
      `ORPHANED`, and it asks GitHub nothing. `build_queue` over both specs
      then offers only the stamped one, resuming its row.
    witness: tests/test_session.py::test_a_lens_that_errored_ends_its_task_in_a_state_no_batch_scan_takes_back
    mutant:
      file: saffron/cell/session.py
      find: ledger.set_task_state(task_id, outcome)
      replace: ledger.set_task_state(task_id, "REVIEWING" if outcome == "REVIEW_INCOMPLETE" else outcome)
    wrong_versions:
      - The cell returns the new state but writes `REVIEWING` to the row, so the scan stamps it `ORPHANED` and the queue offers it again.
      - The new state joins the in-flight set, so a stamping reconcile stamps the row `ORPHANED`.
      - The new state sits in the re-queue set rather than the done set, so `build_queue` offers its spec again.
      - The cell writes the new state as REVIEW starts, so `on_state` never hears `REVIEWING`.
      - A reconcile that reads no rows, so it stamps nothing whatever the row's state.
---

## Context

Backlog item **b-032c3e**. It cites `DESIGN.md` §4.2.1 and §5.5. Every line
number below was read at `cf3db797`, with this spec's own commit applied.
`SA-0276` lands first and moves some of them.

**A lens that errors halts its task in an in-flight state.** `review_state`
returns `REVIEWING` when any lens carries an error
(`saffron/phases/review.py:863-875`). A lens carries one when its session
failed (`:321-326`) or its output was not the schema after one re-prompt
(`:337-351`). The cell writes `REVIEWING` to the row as REVIEW starts
(`saffron/cell/session.py:2805-2808`). It takes its outcome from
`review_state` (`:3104`). It writes that outcome to the row at the end
(`saffron/cell/session.py:3271-3273`). So the row keeps `REVIEWING` after
the cell exits.

**Each reader takes that row for a live cell or a corpse.** `REVIEWING` is in
`IN_FLIGHT_STATES` (`saffron/reconcile.py:53-64`). A reconcile that stamps
orphans sets every such row `ORPHANED` (`:206-210`), and `ORPHANED`
re-queues the spec. The batch command opens its night with that scan,
passing `stamp_orphaned=True` (`saffron/cli.py:1978-1985`). The scan calls
`reconcile` (`saffron/cli.py:1622-1624`) and then `build_queue` (`:1639`).
The batch loop also notes a task that returns in a state in
`IN_FLIGHT_STATES` (`saffron/batch.py:336-341`). Such a task ends the night
`INCOMPLETE` (`saffron/batch.py:51-56`). PACKAGE never runs on the halted task.
`run_task` pushes its branch through `push_unpackaged_work` and opens no
pull request (`saffron/task.py:729-740`). The spec loop's run 34 measured
this on `SA-0259`, whose night closed `INCOMPLETE` and exited 2.

**This spec's own commit adds the state.** `REVIEW_INCOMPLETE` is a terminal
state in `ontology/factory.ttl`, `CONTEXT.md` §6 and `DESIGN.md` §3.3 and
§5.5. It is in `ledger.TaskState` (`saffron/ledger.py:64`) and in
`DONE_STATES` (`saffron/scheduler.py:70-87`). It is in
`DEPENDENCY_WAITING_STATES` (`:99-107`), so a child stacks on the pushed
branch, as it does on a `REBUTTAL_UNJUDGED` parent. The morning queue ranks
it with the states that need you (`saffron/report/index.py:54-55`). It is
not in `IN_FLIGHT_STATES`, so no reader above takes it for a live cell.
Nothing writes it yet.

## Problem

Make REVIEW's halt write `REVIEW_INCOMPLETE`.

Return `REVIEW_INCOMPLETE` from the errored-lens return in `review_state`.
Keep its line of text, and keep the errored check ahead of the blocker check.
Update the docstring above it, which says the stop happens at `REVIEWING`
(`saffron/phases/review.py:864-870`). Leave the write that marks REVIEW live
(`saffron/cell/session.py:2805-2808`) as it is: `REVIEWING` stays the state
while REVIEW runs. The cell's end write then records the new state with no
edit to `saffron/cell/session.py`.

Then update the two existing assertions of `REVIEWING` as a halt's outcome.
Both are in `tests/test_review.py`. Keep each test's name.

- `test_output_that_is_not_the_schema_is_an_incomplete_review_not_a_clean_one`
  (`tests/test_review.py:177-190`).
- `test_a_lens_whose_session_failed_still_charges_what_it_spent`
  (`tests/test_review.py:202-207`).

Leave every `REVIEWING` that names the live state or an attempt's phase.
`test_a_cell_reports_each_phase_state_as_it_enters_it` still hears
`REVIEWING` as REVIEW starts, and an attempt row's phase stays `REVIEWING`.
Leave every test that uses a `REVIEWING` row or outcome to stand for an
in-flight task. `tests/test_batch.py`, `tests/test_cli.py` and
`tests/test_task.py` hold such tests.

## Out of scope

- **The state's vocabulary, its scheduler sets and its rank.** This spec's
  own commit lands them, with `DESIGN.md` and `CONTEXT.md`.
- **`reconcile` asking GitHub about a halted row with no `pr_url`.** It asks
  only about a row with one, in a pending or merge-only state
  (`saffron/reconcile.py:163-170`). `SA-0259`'s row stayed `REVIEWING` after
  its hand-opened #809 merged, and the delegate stamped it `MERGED` by hand.
  A `REVIEW_INCOMPLETE` row is skipped there too, with or without a
  `pr_url`.
- **The probes an errored lens drops.** Backlog item b-f7a591 owns them.
- **A refused push and a resumed row's open pull request.** Backlog items
  b-f603c9 and b-af24d1 own both gaps for `REBUTTAL_UNJUDGED`. The same two
  hold for this state.
- **ADR 4 and ADR 8.** Each still says a lens that errors stops the task at
  `REVIEWING`. They are edited by hand once this lands.
- **Rows already left `REVIEWING`.** No migration rewrites them. A stamping
  scan still stamps them `ORPHANED`.
- **Exit code.** The new state has no entry in `CELL_EXIT`
  (`saffron/cli.py:80-96`). So the default of 1 applies to it
  (`saffron/cli.py:603`), as it does to the other new state.

## Notes for the agent

**Each criterion pins existing text.** Criterion 1 swaps a literal in place
in a return that already exists. Criterion 2 mutates the end of the cell,
which this change leaves alone. So each declares a mutant.

**Criterion 1's return grows past the line limit.** `ruff format` then wraps
it into a parenthesised two-line tuple. Run `make fmt` before committing.

**Criterion 1** calls `review.review_state` directly with `LensReview`
values (`saffron/phases/review.py:138-147`). Give the errored lens an
`error` and no findings. Give the blocker and the concern lenses one
`Finding` each with `anchored=True`. Use one lens name for the errored lens,
and assert it appears in each line. Assert the three cases with no errored
lens too: a clean lens alone, a clean lens beside a concern, and a clean
lens beside a blocker.

**Criterion 2** drives `_drive` (`tests/test_session.py:1350`) with a plan
turn, an implement turn and then an `implement.AgentFailed` for the first
lens. The stub raises any exception it finds in the turn list
(`tests/test_session.py:1445-1448`), and later lenses default to a clean
review. Pass `on_state` a list's `append`. Write two spec files to a
directory of their own, as `tests/test_cli.py` writes `_A_SPEC`
(`:1627-1630`), with ids `SY-1` and `SY-2`. Give the cell `SY-1`'s
`spec_sha`, the sha256 of its file's text. Read the repo id from the
ledger's `repos` table. Add a second task row for `SY-2` at its own
`spec_sha`, and set it `REVIEWING` through `ledger.set_task_state`. Call
`saffron.reconcile.reconcile` with `stamp_orphaned=True` and a `gh` that
raises when called. Assert `result.orphaned` is exactly the second row's
id, and assert both rows' states. Then call `scheduler.build_queue` on the
directory. Assert its candidates are exactly `SY-2`, resuming the second
row's `task_id`. Without the second row, a reconcile that reads no rows
passes.

**At base each new witness fails in its body.** Neither imports a name this
change adds. Both fail on the state `review_state` returns.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** A prototype measured 337 changed tokens with `size_gate`'s
counter, against the `bug` ceiling of 1300. It held the source edit, the
docstring update, both assertion updates and the two new witnesses.
`estimated_lines` is that count over four, plus a margin.
