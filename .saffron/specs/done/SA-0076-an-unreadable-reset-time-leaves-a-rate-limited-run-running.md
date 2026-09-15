---
id: SA-0076
title: a reset time the host cannot read crashes the rate-limit handler and leaves the run reading as still going
type: bug
priority: 2
depends_on: []
touches:
  - saffron/phases/implement.py
  - saffron/cell/session.py
  - saffron/events.py
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
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/repos/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
budget_usd: 6
max_attempts: 3
max_turns: 50
risk: elevated
acceptance:
  - claim: >-
      A rejected rate limit whose `resets_at` cannot be read as a time (a
      string, a list, an integer past the platform's `time_t`, or NaN) still
      ends the task `RATE_LIMITED`, closes its run row `COMPLETE`, and prints
      none of the value's text. Today the handler's own announcement raises
      inside `except RateLimited`, the raise escapes the function, and the run
      row is left `RUNNING`: a run that reads as still going, for a provider
      ceiling that should have told the operator when to retry.
    witness: tests/test_session.py::test_an_unreadable_reset_time_still_stops_rate_limited
  - claim: >-
      A readable reset time still ends the task `RATE_LIMITED` and says when
      the window reopens, in local time and not as the raw stamp, as it does
      today.
    witness: tests/test_session.py::test_a_wall_on_the_plan_turn_is_not_the_task_failing
    preserves: true
  - claim: >-
      The event log's renderer still reads each of those four values as an
      unknown reset time and never raises on them, as it does today.
    witness: tests/test_events.py::test_describe_renders_whatever_it_is_handed
    preserves: true
---

## Context

`docs/BACKLOG.md` item **104**, found reviewing `SA-0070` (PR #221) on
2026-09-12. `SA-0070` made `events._when` return `"unknown"` for a `resets_at`
it cannot read, because `rate_limit` events carrying such values reach the
renderer from a live cell. Its twin, `when` in `saffron/phases/implement.py`,
still calls `time.localtime` unguarded. Its one caller is the `except
RateLimited` handler in `saffron/cell/session.py`, on `stopped.resets_at`. That
value is the cell's own `rate_limit.get("resets_at")`, checked only for
truthiness, and `AttemptResult` is a plain dataclass that validates nothing.

**Measured 2026-09-12**, through `run_one_cell` with the stubs
`tests/test_session.py` already uses (`_stub_the_runtime`, `_drive`, and
`_rejected` on the plan turn):

| `resets_at` | what happened | `runs.status` |
|---|---|---|
| `"soon"` | `TypeError` raised out of the session | `RUNNING` |
| `[1]` | `TypeError` raised out of the session | `RUNNING` |
| `10**20` | `OverflowError` raised out of the session | `RUNNING` |
| NaN | `ValueError` raised out of the session | `RUNNING` |
| `1755800000` | `RATE_LIMITED` | `COMPLETE` |

The run row stays `RUNNING` because the raise happens inside one `except`
clause, and its sibling `except BaseException`, which exists to close the row
`ABORTED`, never sees it. So a provider ceiling reaches the batch loop as an
abort (§4.2.1), and the ledger records a run that never ended.

## Problem

`RATE_LIMITED` is not `EXHAUSTED`, and neither is an abort: a provider ceiling
and a broken task say different things to the operator (§3.3). A value an
untrusted cell chose decides which one the operator hears, and in the worst
case the operator hears nothing at all. Formatting a reset time is the
operator's convenience. It must never be what decides the outcome.

## Out of scope

**The two `print` calls in `session.py` that no event kind carries.** The
rate-limit line is one of them, and giving them an event kind is item **43**.
Keep it a `print` here.

**Any other field a cell's `rate_limit` event carries.** This spec is the reset
time.

## Notes for the agent

**Make it one function.** `events._when` is already guarded, and `SA-0070`
measured it against exactly these four values. `implement.when` is the
unguarded copy, and the handler is its only caller. The item's own done
condition is one function rather than two. Whether you delete the copy, have it
delegate, or rename the survivor is your call. Whichever you choose, correct
every docstring that names the function that no longer exists. `events._when`'s
docstring still says `SA-0031` will delete the other copy, and `SA-0031` merged
long ago.

**Decide the `None` case deliberately.** The two copies differ there:
`events._when(None)` returns `"unknown"`, and `time.localtime(None)` reads as
*now* and prints a reset time that has already passed. The handler never passes
`None` today, because it checks truthiness first. Keep it that way, or say in
the surviving docstring why it no longer matters.

**The criteria carry witnesses and no mutants.** The fix is an edit, but its
spelling is yours: deleting, delegating and guarding all satisfy it, so no text
exists yet that a mutant could pin honestly.

**Drive it the way `test_a_wall_on_the_plan_turn_is_not_the_task_failing`
does**: `_stub_the_runtime`, `_drive`, and `implement.AgentFailed` carrying
`_rejected(resets_at=...)` on the plan turn. Then read `tasks.state` and
`runs.status` back out of the ledger as that test does. Loop over the four
values inside one test rather than parametrizing. A parametrized test's
collected ids carry the parameter, and the witness names one id.

**The witness must fail with the source reverted, not merely be missing at
base.** Reverted, the session raises, so an honest test fails. Import nothing
new at module scope: a module-scope import of a name you add turns the reverted
run into a collection error, which `revert` reads as `skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. This is well inside that.
