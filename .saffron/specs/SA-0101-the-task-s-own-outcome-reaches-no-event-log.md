---
id: SA-0101
title: the task's own terminal announcement is a bare print, so its event log ends before the outcome and emit is not the whole seam
type: bug
priority: 2
depends_on:
  - SA-0099
  - SA-0098
touches:
  - saffron/events.py
  - saffron/cell/session.py
  - tests/test_events.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/watch.py
budget_usd: 14
max_turns: 90
acceptance:
  - claim: >-
      A caller that supplies its own emit receives the task's terminal
      announcement through it, and nothing the supervisor writes reaches process
      stdout without passing through that emit. Today the announcement is a
      direct print, so a caller supplying emit never receives it and cannot
      redirect it.
    witness: tests/test_session.py::test_the_terminal_announcement_reaches_emit_and_not_stdout
  - claim: >-
      The rate-limit rejection behaves the same way through the RateLimited
      path. It reaches the caller's own emit, it names the reopening time when
      one is known, and it reaches process stdout only through that emit.
    witness: tests/test_session.py::test_the_rate_limit_rejection_reaches_emit_and_not_stdout
  - claim: >-
      The outcome the cell ended on reaches events.jsonl, so reading the log
      back and describing it reproduces the same line the print wrote, with the
      same state, the same spend and the same session id. Today the log's last
      event is PACKAGE's, and the cell's outcome appears nowhere in it.
    witness: tests/test_session.py::test_the_outcome_event_round_trips_and_describes_as_its_old_line
  - claim: >-
      A rate-limited outcome reaches events.jsonl whatever reopen time the cell
      reported. A string, a list and NaN each leave an event that reading the
      log back keeps, with no reopen time and a mark that one was reported and
      could not be read. An integer past time_t's range is kept as it came.
      Describing any of the four renders the reopen time as unknown, as the
      print does today. An event whose field has the wrong shape is dropped on
      read, so storing the value as reported would lose the task's terminal
      record.
    witness: tests/test_session.py::test_a_rate_limited_outcome_survives_the_log_whatever_reopen_time_was_reported
  - claim: >-
      Every kind still round-trips through the log and still has its wire keys
      pinned, the new one included.
    witness: tests/test_events.py::test_every_kind_is_round_tripped_and_its_wire_keys_pinned
    preserves: true
---

## Context

Backlog item **43**, filed as `partial` and left half open by `SA-0030`.

`saffron/events.py` says what the module is for. Its docstring counts 64 call
sites that "author prose straight into `watch()`, and the structure behind each
line dies with the terminal scroll". Ten frozen kinds and a durable log are the
fix. `FINDINGS` in that file is the honest record of what would not fit, and
its first entry is this defect.

Two lines never became events. Both are in `_drive_cell`.

- `saffron/cell/session.py:2283` prints the task's terminal announcement:
  `f"{outcome}: ${spent:.2f} spent, session {session_id}"`. Its comment at
  `:2277-2282` gives the reason. A `Terminal` is scoped to the five zero-commit
  IMPLEMENT endings, and a `Budget` carries a ceiling, a value and a limit.
  Neither fits an arbitrary outcome word with a session id.
- `saffron/cell/session.py:2305-2312`, inside `except RateLimited`, prints
  `rate limit: rejected` and the reopening time. Its comment at `:2303-2304`
  says it shares the exemption above.

Two consequences, and the second was not disclosed until a review found it.

**The event log ends before the outcome.** Measured 2026-09-17 against
`~/.saffron/batches/v0/SA-0095/events.jsonl`: the last event is PACKAGE's, and
no line in the file names `READY_FOR_REVIEW`, the spend or the session id.
`saffron watch` renders the log through `describe`, so it shows a task's whole
run and never how it ended. Across the 54 event logs on that host, `Terminal`
appears twice and no kind carries an outcome.

**`emit` is not the supervisor's whole output seam.** Both lines go to process
stdout whatever the caller passed. So a caller supplying its own `emit` still
gets two lines it cannot redirect, and the one it most wants is the outcome.
The test harness hides this: `tests/test_session.py:1072` patches
`session.print` with `raising=False`, so the leak is invisible unless a test
opts out through the `use_default_emit` seam its fixture documents at `:984`.

**Two comments about the same decision disagree, and one is stale.**
`saffron/cell/session.py:2280` calls the missing kind "a tenth kind".
`events.FINDINGS[0]` calls it "a eleventh kind". `Event` in
`saffron/events.py` unions ten kinds, and `_KINDS` maps ten names. So eleventh
is right, and the `session.py` comment counts from a draft that had nine.

## Problem

- **A task's log cannot answer how its cell ended.** That is the first question
  anyone reads a log to answer.
- **`saffron watch` shows everything except the cell's outcome.** It follows the
  log and adds no second source, so a finished cell's outcome never reaches the
  screen.
- **A caller cannot capture the supervisor's whole output.** Two lines bypass
  `emit`, which is the seam every other line goes through.
- **The gap is worst where nobody is watching.** Under `saffron batch` the
  terminal scroll is the night's record, and `CLAUDE.md` notes SIGTERM discards
  it. The durable log is what survives, and it omits the outcome.

## Out of scope

**The `re-verify` line.** `events.FINDINGS[1]` names it and
`saffron/phases/package.py` is forbidden. Its problem is a `LineLabel` casing
rule, not a missing kind, and it stays item 43's.

**The `stacked on` line.** `saffron/task.py:301` prints it under a
`ponytail:` comment citing item 43, and `saffron/task.py` is forbidden. No kind
carries `CellSpec.stacked_on` at all, which is a wider change than this one.

**The packaged state, and the endings that return early.** PACKAGE runs after
the announcement. The state a packaged task ends on is printed by `run_task`
(`saffron/task.py:343` and `:382`), which is forbidden. So a
packaged task's log still ends on PACKAGE's events. The cell's endings that
return before `_drive_cell`'s announcement (`PREFLIGHT_FAILED`,
`SCOPE_REVIEW`, `PLAN_REJECTED`, `NOT_IMPLEMENTED`, and the early `EXHAUSTED`)
also stay as they are. This spec moves the two lines named above and nothing
else.

**Item 43's close.** Two of its four lines stay after this spec, so the item
stays `partial`. Do not mark it done.

**`saffron/watch.py`.** It renders through `describe` already and needs no
change to show a kind that exists. It is forbidden, and a new filter for the
new kind would be the wrong answer.

**Widening `Terminal`.** Its five reasons are the zero-commit IMPLEMENT endings
and backlog item 37 already disputes its name against `CONTEXT.md`. Adding an
outcome word to it makes that worse.

**The vocabulary entry.** A new kind is a new term, and `CONTEXT.md` is
generated from `ontology/factory.ttl`, so a cell cannot move both halves. The
follow-up record is filed by hand with this spec.

## Notes for the agent

**This spec's change is mostly new code.** Four criteria declare a witness and
no mutant. The kind does not exist, so its field spellings are yours.
Expect `witness` to report `skip` for those four. The fifth is `preserves`
over `tests/test_events.py:1143`, a plain test function that must keep passing
once the new kind joins whatever list it walks.

**One kind covers both lines, and that is the design.** Both are the task's own
terminal announcement. The rate-limit rejection is the outcome `RATE_LIMITED`
plus a reopening time, so a single kind with an optional reopening field carries
both. Two kinds for one fact is the shape `events.py` exists to refuse.

**`RATE_LIMITED` is not `EXHAUSTED`.** A provider ceiling and a task that could
not pass its gates are different outcomes and say different things. Whatever
field carries the state must keep them apart, and the rendered line for each
must stay distinguishable.

**The rate-limit path has no session id, and reading one there raises.**
`session_id` is first bound at `saffron/cell/session.py:1599`, inside the `try:`
at `:1369`. `except RateLimited` at `:2302` catches a raise from anywhere in that
body, and a wall on the plan turn unwinds before `:1599` runs. The code already
pre-binds `spent` at `:1367` for that reason. Make the session id optional on
the new kind, and pre-bind it beside `spent`.
`test_a_wall_on_the_plan_turn_is_not_the_task_failing`
(`tests/test_session.py:2884`) drives a wall on the plan turn, and
`test_an_unreadable_reset_time_still_stops_rate_limited` (`:2906`) drives four
junk reopen values. Both must stay green.

**Store the reopen time only when it is an `int`.** A pre-rendered string
field is the `message: str` hatch this vocabulary exists to refuse. But
`RateLimited.resets_at` comes from the cell unchecked. And `_parse_line` drops a
whole event when a field fails `_shape_ok` (`saffron/events.py:518-520`). So keep the value only when it is an `int` and
not a `bool`. Otherwise record that one was reported and could not be read, in a
field whose shape always passes. `describe` renders that case as
`window reopens unknown`, which is what `when()` (`saffron/events.py:596`)
prints for it today. An `int` past `time_t` is kept, and `when()` already
renders it as unknown. Criterion 4's witness drives all four values from
`test_an_unreadable_reset_time_still_stops_rate_limited` through the log. It
asserts the read-back field, not only the rendered line. So a field typed wide
enough to hold the value as reported fails it.

**A falsy reopen time changes its line, and that is intended.** The old print
skipped one (`if stopped.resets_at`, `saffron/cell/session.py:2309`). Keep `0`
as an `int` and render it. An empty string or list is unreadable like any other.

**An eleventh kind moves six more things in `tests/test_events.py`.** Each is in
`touches`, and each is real work. Three counts: the kinds at `:574`, `FAMILIES` at
`:1199`, `FINDINGS` at `:1680`. Three tables: `_ONE_OF_EACH` at `:74`, `_CASES`
at `:903` and `_JOINED` at `:1810`. And
`test_events_jsonl_reproduces_what_the_terminal_printed` at `:2023`. The last
one fails by construction once the outcome reaches the log, because it strips the
outcome from the printed side before comparing.

**The spend field is `spent_usd_est`.**
`test_the_wire_keys_are_pinned_for_every_kind` (`tests/test_events.py:568`)
rejects any other spelling of a spend.

**`size` blocks at 300 changed lines here.** Touching `saffron/cell/**` raises
the tier to elevated (`.saffron/policy.yaml`'s `elevate_on`, and `_advisory` in
`saffron/gates/suite.py`). Write one shared helper for the four new witnesses.
Criterion 5 needs the new kind only in `_ONE_OF_EACH` and in `_CASES`, which
`test_every_family_has_a_kind_and_renders` requires. Entries in `_JOINED` for the
outcome lines are optional, since nothing forces them.

**Append any new `_JOINED` entry at the end.** `_JOINED` has no ids, so an
insertion renumbers the cases after it (`tests/test_events.py:1948-1953`).
`census` reads each renumbered case as a removed test.

**`FINDINGS[0]` is deleted, and its shape becomes a `FAMILIES` row.** That
shifts three prose citations of `FINDINGS[1]`: `tests/test_package.py:1177`,
`tests/test_package_cell.py:28` and `saffron/phases/package.py:538`. It also
leaves `package.py:542` citing a `FINDINGS[0]` exemption that no longer
exists. All are comments, none of those files is in `touches`, and no test
fails. Leave them, and name all four in the pull request body. The citations of
`FINDINGS[0]` in `tests/test_session.py:1066` and `tests/test_events.py:1808`
and `:2028` are in `touches`: correct them.

**Criterion 1's wrong implementation is an event beside the print.** The seam
stays broken. Adding the emit and leaving the print still satisfies "the caller
receives it".

**Neither existing fixture mode can observe criterion 1, so add a third.**
`tests/test_session.py:1056` is the `use_default_emit` mode. It passes no
`emit`, so `_default_emit` prints the line at `saffron/cell/session.py:80-82`.
That print is correct and stays, and
`test_run_one_cell_with_no_emit_argument_still_prints` (`tests/test_events.py:2005`)
pins it, so a
witness asserting absence from stdout fails at head on that path. The other mode
patches `session.print` away at `tests/test_session.py:1072`. The line is
therefore already missing from real stdout at base, and the same witness is green
there.
Add a mode that passes a custom `emit` and leaves `session.print` alone. Under it,
assert the announcement is among the captured events, and assert through `capsys`
that stdout carries no copy. Criterion 2 needs that mode too.

**Criterion 3's wrong implementation is a kind that renders differently.** An
operator learned the old line. `saffron watch` also replays old logs beside new
ones. Read the format string at `saffron/cell/session.py:2283`. Make `describe`
reproduce it exactly, the two-decimal spend included. Assert against the whole
text, never a substring.

**`spent` is read back from the ledger on the rate-limit path, and that is
deliberate.** The comment at `saffron/cell/session.py:2315-2319` says why: the
local tally loses the walled turn. Take the figure that path already computes
rather than the local variable.

**Correct the stale comment while you are in it.** `saffron/cell/session.py:2280`
says "a tenth kind" and there are ten kinds today. Once this spec lands the
count changes again, so leave no sentence claiming a count.

**`census` compares test names, so rename nothing.** `SA-0102` also names
`tests/test_session.py` and `tests/test_events.py`, and runs on this branch. Keep the diff to
the new tests plus the call sites this spec replaces.

**Import anything new inside the test body.** `tests/test_events.py` is the
exception. A module-scope import of a name this change adds turns `revert`'s
reverted run into a collection error. `revert` reads that as `skip`. That is why the four
new witnesses live in `tests/test_session.py`, with their imports in the body.
`tests/test_events.py` cannot follow the rule: `_ONE_OF_EACH`, `_CASES` and
`_JOINED` are module-scope parametrize lists, and criterion 5 needs the new kind
in them. Import it at module scope there. `revert` will then report `skip`, and
that is accepted. Do not work around it.

Commit after each coherent step. Uncommitted work dies with the cell.
