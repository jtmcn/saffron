---
id: SA-0148
title: A stack batch treats a rate limit as a missed layer, so it trips the breaker and refuses the spec's descendants on a window that reopens
type: feature
priority: 1
depends_on: [SA-0147]
touches:
  - saffron/batch.py
  - saffron/cell/session.py
  - tests/test_batch.py
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
  - saffron/task.py
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/cell/__init__.py
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_task.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_events.py
  - tests/test_implement.py
budget_usd: 27
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      When a task in `run_stack_batch` returns `RATE_LIMITED` with a reset
      time after the clock's now, by no more than six hours, and before
      `until`, the batch calls its `sleep` keyword once. It passes the
      seconds from the clock's now to that reset time. It then runs
      the same spec again, next, on the same predecessor. The rate-limited
      task adds no layer, and the batch refuses none of its spec's
      descendants for it, so no line names a refusal. Its run stays
      attached to the batch. The batch
      emits one line that starts with the spec id padded to ten, then
      `rate limited`, and names the wait's end as `HH:MM` in the clock's own
      zone. The witness drives a naive local clock and an aware clock at a
      fixed offset of minus seven hours.
    witness: tests/test_batch.py::test_a_stack_batch_waits_out_a_rate_limit_and_runs_the_same_spec_again
  - claim: >-
      In `run_stack_batch`, a `RATE_LIMITED` outcome leaves the breaker's
      count as it was. It neither adds one nor resets it. The witness drives
      a rate limit after an abort and two rate limits in a row. A spec
      whose second task misses after a rate limit is a miss, so the batch
      refuses its descendant. `run_batch`,
      given the abort and the rate limit, still counts both, runs neither
      spec again, never sleeps, and stops `INFRASTRUCTURE`.
    witness: tests/test_batch.py::test_a_rate_limit_in_a_stack_batch_neither_counts_toward_the_breaker_nor_resets_it
  - claim: >-
      The wait and the distance to `until` both come from one clock read,
      taken after the task returns. When a stack batch's wait would end at
      or past `until`, it stops `UNTIL` at once. It never calls `sleep`, it
      emits no `rate limited` line, it runs nothing more, and the
      rate-limited run stays attached. A wait that ends before `until` runs
      in full. Before the same spec runs
      again, the budget check runs as it does before any task, and a short
      budget stops it `BUDGET`. The witness drives a reset time past
      `until`, one exactly at `until`, and a missing reset time whose hour
      runs past `until`. It drives `until` passing during the task, a
      missing reset time whose hour ends before `until`, a task that runs
      an hour and resets 60 seconds after it returns, and a task that runs
      an hour and resets 90 minutes after it returns with `until` two hours
      from the start. It drives a budget the first run leaves short.
    witness: tests/test_batch.py::test_a_stack_batch_stops_at_until_rather_than_wait_past_it
  - claim: >-
      When the batch cannot read the reset time, it waits one hour, 3600
      seconds, and runs the same spec again. It cannot read `None`, a time
      not after the clock's now, or a time more than six hours after it. A
      reset time exactly six hours on is read, and waited in full. Each
      wait emits its own `rate limited` line. The
      witness drives `None`, `10**20`, `10**12`, a reset time equal to now,
      one a minute before it, one seven hours on, `10**400`, `-10**400` and
      one six hours on.
    witness: tests/test_batch.py::test_a_stack_batch_waits_an_hour_when_it_cannot_read_the_reset_time
  - claim: >-
      `run_one_cell`'s `RATE_LIMITED` outcome carries the reset time as
      `resets_at`: the integer the `TaskOutcome` event carries, or `None`
      where that event carries none. The witness drives `1755800000`,
      `10**20`, `None`, `"soon"`, `[1]` and `float("nan")`.
    witness: tests/test_session.py::test_a_rate_limited_outcome_carries_the_reset_time
  - claim: >-
      `run_batch` still starts a spec at most once a night, one whose task
      ended `RATE_LIMITED` included.
    witness: tests/test_batch.py::test_a_spec_the_rescan_requeues_is_not_started_twice_in_one_night
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 5 of its Done. It cites `DESIGN.md` §4.2.1.
ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. It leaves "what `RATE_LIMITED` does to the breaker
in a stack batch" to the specs that build it (`:256`). Section 4 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "A rate limit
waits", is the design (`:268-271`). In a stack batch `RATE_LIMITED` does
not count toward the breaker. The batch sleeps until the reset time or
`--until`, whichever comes first, then runs the same task again on the same
predecessor. The limit is the account's, so the next spec would meet it too.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from its head. That task is the next one's **predecessor**.

**What the tree base holds.** This spec's tree base is `SA-0147`'s head.
The chain `SA-0142` to `SA-0145` puts `run_stack_batch`, its runner of a
candidate and a predecessor, and `Refused` there. `SA-0143` names
`run_stack_batch`'s keywords `readiness_check`, `clock` and `emit`, as
`run_batch` takes them. `SA-0143` also gives `tests/test_batch.py`'s
`_candidate` a `depends_on` keyword. That chain edits `saffron/batch.py`, so
its lines are cited by symbol. Every line number below was read at
`71140772`.

**What a rate limit does in a batch today.** `ABORT_STATES` holds
`RATE_LIMITED` (`saffron/batch.py:53`). `_drive` adds one to the breaker's
count for any state in it (`:244-245`), and two in a row stop the batch
(`:57`, `:202-203`). `_drive` starts a spec at most once, by spec id
(`:175`, `:181`, `:208`). `DESIGN.md` §4.2.1 gives the reason
(`DESIGN.md:414`). A provider ceiling "lets every remaining task start a
cell and run a baseline suite ... before dying of the same global
condition". The queue re-queues it tomorrow. In a stack batch `SA-0143`
also reads any state but `READY_FOR_REVIEW` as a miss, and refuses the
spec's descendants. So a closed window at 23:00 costs the stack every spec
that depends on the one it hit.

**What the hand loop does.** It waits and runs the same spec again. The
spec loop's `Recording` section says `RATE_LIMITED` leaves the spec
pending: "`next --again` once the window reopens — the cell's own `rate
limit: … window reopens HH:MM local` line says when"
(`.claude/skills/run-saffron-spec-loop/GOTCHAS.md:41-43`).

**Where the reset time is, and where it is not.** The cell's `rate_limit`
event carries `resets_at` (`images/agent_runner.py:117`), and
`AttemptResult.rate_limit_resets_at` holds it
(`saffron/phases/implement.py:95`). A rejected window raises
`RateLimited(resets_at)` (`saffron/cell/session.py:141-147`, `:232`).
`run_one_cell` catches it (`:2823`). `_resets_at_fields` shapes the value
into a clean `int` or `None` (`:150-156`). The handler emits a
`TaskOutcome` with that value (`:2829-2838`), then returns a `CellOutcome`
(`:2842-2850`). `CellOutcome` has no field for it (`:305-344`), so the
value reaches the event log and never the batch. `run_task` returns
`run_one_cell`'s own object (`saffron/task.py:363`, `:427`).

**What the reset time can hold.** It arrives from an untrusted cell.
Backlog item 104 measured four malformed values reaching the handler: a
string, a list, `10**20` and NaN. `_resets_at_fields` passes a clean `int`
and turns anything else into `None` (`saffron/cell/session.py:150-156`).
So `10**20` reaches the outcome as an `int`. `events.when` renders it
`"unknown"`. It catches `OverflowError`, `OSError` and `ValueError` from
`time.localtime` (`saffron/events.py:635-638`). On the host's Python 3.14,
on 2026-09-23, `datetime.fromtimestamp(10**20)` raised `OverflowError`.

**The clock is naive local time.** `run_batch`'s `clock` defaults to
`datetime.now` (`saffron/batch.py:68`). `cli._batch` resolves `--until` from
`datetime.now()` (`saffron/cli.py:794-796`) and passes no `clock`
(`:881-890`). `_drive` compares the two (`saffron/batch.py:195`). Nothing
stops a caller passing an aware clock and an aware `until`.

## Problem

Build two things.

1. **The reset time on the outcome.** Add `resets_at: int | None = None` to
   `CellOutcome` in `saffron/cell/session.py`. The `RateLimited` handler in
   `run_one_cell` sets it to the value it already hands the `TaskOutcome`
   event. Every other path leaves it `None`.
2. **The wait.** Add a keyword `sleep: Callable[[float], None]` to
   `run_stack_batch`, defaulting to `time.sleep`. When a task returns
   `RATE_LIMITED`, the stack batch does six things.
   - It leaves the breaker's count as it was.
   - It records the task as neither a layer nor a miss.
   - It computes the wait. Take `now = clock()` once, after the task
     returns, and `now_ts = now.timestamp()`. The reset time is readable
     when it is not `None` and `now_ts < resets_at <= now_ts + 21600`, six
     hours. Test those bounds before any subtraction. Only a readable reset
     time gives the wait `resets_at - now_ts` seconds. Otherwise the wait
     is 3600 seconds.
   - With `until` set and the wait at least
     `(until - now).total_seconds()`, from that same `now`, it stops
     `UNTIL` at once, with no sleep and no line.
   - Otherwise it emits one line and calls `sleep` once with the wait. The
     line starts with the spec id padded to ten, then `rate limited`. It
     names `now` plus the wait as `%H:%M`.
   - It offers the same spec as the next task, with the same predecessor.
     That task meets `--until`, the budget and the breaker, in that order,
     as every task does (`saffron/batch.py:195-203`). The rate-limited run
     stays attached to the batch, so its spend counts.

`run_batch` does none of this. A `RATE_LIMITED` task there still counts
toward the breaker, and its spec is not started again that night.

## Out of scope

- **`run_batch` without `--stack`.** It keeps §4.2.1's breaker. Tomorrow's
  queue re-queues the spec there (`DESIGN.md:390`).
- **`DESIGN.md` §4.2.1.** It describes `run_batch`'s breaker, and that stays
  true. No section of `DESIGN.md` describes a stack batch yet, and
  `DESIGN.md` is protected.
- **Resuming the rate-limited task's work.** The next task of the spec
  starts over from the predecessor's head, as the hand loop's next cell
  does. PACKAGE's push replaces any branch the first task left
  (`saffron/phases/package.py:372-381`). `SA-0143` assumed each spec runs
  once in a stack batch. A rate-limited task can push partial work through
  `push_unpackaged_work`, which reads this spec's other tasks
  (`saffron/phases/package.py:1097-1105`). The second task's PACKAGE
  lease then replaces that push, so nothing here changes it.
- **A bound on the number of waits.** With no `--until`, the batch waits as
  long as the provider keeps the window closed. Each new task still meets
  the budget check. An operator's Ctrl-C closes the row `INFRASTRUCTURE`
  (`saffron/batch.py:135-143`).
- **A longer wait for a longer limit.** A reset time more than six hours
  on gets the hour's default. A limit that lasts days costs one new task an
  hour, each rejected at its first turn.
- **`SA-0146` and `SA-0147`.** This spec consumes nothing either of them
  produces. `depends_on: [SA-0147]` keeps b-792ab2's build order as one
  chain, so this spec's tree holds theirs. `SA-0146`, committed at
  `4797e80e`, touches neither `saffron/batch.py` nor `tests/test_batch.py`.
  `SA-0147` is not written yet, so its effect on those two files is
  unverified.
- **`SA-0133`, `SA-0138` and `SA-0139`.** They are queued outside this
  chain and also touch `saffron/cell/session.py` or `tests/test_session.py`.
  If one's pull request is still open when this cell starts, gate 0's open
  pull request overlap refusal holds this spec back until it merges. So no
  `depends_on` names them.
- **The vocabulary.** "Stack batch", "predecessor" and "layer" are backlog
  item b-466005's, filed by hand. This spec adds no term.

## Notes for the agent

**Criteria 1 to 5 are new code.** No text at the tree base waits, and no
field carries the reset time. So they declare a witness and no mutant, and
`witness` reports `skip` for them. Criterion 6 is `preserves` and names a
test that passes now.

**Every witness fails with the source reverted.** Criteria 1 to 4 pass
`sleep=` to `run_stack_batch`, which the tree base does not take. Their
runners also build outcomes with `resets_at`, which `CellOutcome` lacks
there. Criterion 5 reads `outcome.resets_at`. Nothing new needs importing.

**Keep one loop.** `SA-0143`'s notes suggest `run_stack_batch` wraps
`run_batch` and `_drive`. Do not wait inside the runner and call it again
there. That skips `--until`, the budget and the breaker, and the first run
is never attached. One way is a keyword on `_drive` that `run_batch` leaves
unset. `_drive` then consults it for a `RATE_LIMITED` outcome in place of
the count, and takes the spec id back out of its started set. The first
candidate not yet started is then the same spec. Whatever `SA-0143` keeps
per result, a rate limit must record neither a layer nor a miss.

**Take the sleep with no default below `run_stack_batch`.** A default of
`time.sleep` on an inner function hides a missing pass-through. The
witness then hangs rather than fails. `run_stack_batch`'s own default is for
`SA-0144`'s caller, which passes none.

**Compute in seconds.** `clock().timestamp()` holds for a naive local clock
and an aware one. `datetime.fromtimestamp(resets_at)` gives a naive time,
and one with `UTC` gives an aware time. Comparing either with the other
clock raises `TypeError`. The six-hour cap also turns away `10**20` and
`10**12`, so the reset time never needs `fromtimestamp`. Called on either,
`fromtimestamp` raises.

**Compare before subtracting.** `_resets_at_fields` passes any `int`
through (`saffron/cell/session.py:154-155`), however large. Measured on the
host on 2026-09-23, `10**400 - time.time()` raises `OverflowError`.
Its message is "int too large to convert to float".
`now < 10**400 <= now + 21600` evaluates
`False` without raising, since Python compares an `int` with a `float`
exactly. A raise there escapes `_drive` and ends the night
`INFRASTRUCTURE`.

**Why six hours, and where this departs from the design.** The design
waits for "the reset time or `--until`" with no cap. This spec caps a
readable reset time at six hours. The reset time comes from an untrusted
cell, so an uncapped one lets a cell hold the batch as long as it likes. A
Claude usage window is five hours, the operator's figure on 2026-09-23, so
a genuine reset always fits under six.

**Why the batch stops at once.** A wait that ends at or past `until` ends
in the `UNTIL` stop anyway.
Sleeping first only delays the night's end. The operator decided this on
2026-09-23. The design's "whichever comes first" is read as the stop, not
a sleep.

**The witnesses' shared parts.** `tests/test_batch.py` gains a clock whose
`now` a fake `sleep` advances. The fake `sleep` records each call's seconds.
Each batch witness also replaces `time.sleep` with one that raises. The fake
runner takes `(candidate, predecessor)` and records `(spec id, predecessor's
spec id or None)`. Its predecessor defaults to `None`, because `run_batch`
calls `runner(candidate)` alone (`saffron/batch.py:212`). Each call mints its own run and a task for its spec id.
The task holds one closed attempt at $1 unless a row says otherwise.
That is `_spend`'s shape with the spec id in place of `TE-0001`. It can
advance the clock. It returns `_outcome(state=..., run_id=...,
task_id=...)` with that call's run and task, and `resets_at` set through
`dataclasses.replace`. `_outcome` defaults `task_id` to 1
(`tests/test_batch.py:43`). `SA-0145` keys `stack_layers` on the task's
record key, so two layers sharing task 1 collide there. SA-0145's own
runner mints a task per call for that reason. A reset time is written
relative to the clock when the runner returns, as `int(clock().timestamp()) + seconds`. Build
candidates with `_candidate`, with a budget of 100 unless a row says
otherwise. Use `_ready`, and the `ledger` and `repo_id` fixtures. The clock
starts at 02:00 on 1 January 2030. That date is later than the day any cell
runs this, so a wait read from the real clock is not the wait expected.

**Criterion 1's witness** runs this order twice. The first run uses a
naive clock. The second uses an aware clock at a fixed offset of minus
seven hours. `until` is four hours after the start.

| order | spec | `depends_on` | results in turn |
|---|---|---|---|
| 1 | `TE-1` | none | `READY_FOR_REVIEW` |
| 2 | `TE-2` | none | `RATE_LIMITED` resetting 3900 seconds on, then `READY_FOR_REVIEW` |
| 3 | `TE-3` | `TE-2` | `READY_FOR_REVIEW` |

Each run asserts the calls are `(TE-1, None)`, `(TE-2, TE-1)`,
`(TE-2, TE-1)` and `(TE-3, TE-2)`. The sleeps are exactly `[3900.0]`, and
the stop reason is `DRAINED`. `ledger.batch_spend` of that batch is 4.0.
Exactly one emitted line starts with `TE-2` padded to ten and holds both
`rate limited` and `03:05`, the wait's end. A build whose line names
`now` prints `02:00` and fails. No emitted line contains ` refused `.

**Criterion 2's witness** drives three arrangements.

- **After an abort.** `TE-1` returns `GATE_ERROR`. `TE-2` returns
  `RATE_LIMITED` resetting 60 seconds on, then `GATE_ERROR`. `TE-3`
  declares `depends_on: [TE-2]` and would return `READY_FOR_REVIEW`. The
  calls are `TE-1`, `TE-2` and `TE-2`, and the stop reason is
  `INFRASTRUCTURE`. Exactly one emitted line starts with `TE-3` padded to
  ten and contains ` refused `.
- **Two in a row.** `TE-4` returns `RATE_LIMITED` twice, each resetting 60
  seconds on, then `READY_FOR_REVIEW`. `TE-5` returns `READY_FOR_REVIEW`.
  The calls are `TE-4` three times with `None`, then `(TE-5, TE-4)`, and the
  stop reason is `DRAINED`.
- **`run_batch`.** The first arrangement through `run_batch`, with a rescan
  that returns the same order. The calls are `TE-1` and `TE-2`, no sleep is
  called, and the stop reason is `INFRASTRUCTURE`.

**Criterion 3's witness** drives eight one-spec arrangements. `TE-1`
returns `READY_FOR_REVIEW` second, if called again.

| case | `until` from start | first result | runner advances | calls | sleeps | stop |
|---|---|---|---|---|---|---|
| reset past `until` | 1 hour | `RATE_LIMITED`, resetting 3 hours on | nothing | 1 | `[]` | `UNTIL`, spend 1.0 |
| reset at `until` | 1 hour | `RATE_LIMITED`, resetting 1 hour on | nothing | 1 | `[]` | `UNTIL` |
| hour past `until` | 20 minutes | `RATE_LIMITED`, `resets_at=None` | nothing | 1 | `[]` | `UNTIL` |
| `until` passes in the task | 30 minutes | `RATE_LIMITED`, resetting 3 hours on | 1 hour | 1 | `[]` | `UNTIL` |
| hour inside `until` | 2 hours | `RATE_LIMITED`, `resets_at=None` | nothing | 2 | `[3600.0]` | `DRAINED` |
| a long task | none | `RATE_LIMITED`, resetting 60 seconds after it returns | 1 hour | 2 | `[60.0]` | `DRAINED` |
| a long task near `until` | 2 hours | `RATE_LIMITED`, resetting 90 minutes after it returns | 1 hour | 1 | `[]` | `UNTIL` |
| budget | none | `RATE_LIMITED` costing $6, resetting 60 seconds on | nothing | 1 | not asserted | `BUDGET` |

The first row also asserts `ledger.batch_spend(_latest_batch_id(ledger))`
is 1.0, and that no emitted line holds `rate limited`. Each long task's
reset time is written after its clock advance. A `now` read before the task
gives the first a wait of 3660 seconds. A distance to `until` read before
the task gives the second 7200 seconds, and it sleeps. The budget case
has a batch budget of 15 and a spec budget of 10. It leaves the sleeps
free, since a build is free to check the budget before it waits.

**Criterion 4's witness** runs `TE-1` alone with `until=None`. It returns
`RATE_LIMITED` nine times. The `resets_at` values are `None`, `10**20`,
`10**12`, the clock's now, a minute before it, seven hours on, `10**400`,
`-10**400` and six hours on. It then returns `READY_FOR_REVIEW`. The calls
are `TE-1` ten times with `None`. The sleeps are `[3600.0]` eight times,
then `[21600.0]`, and the stop reason is `DRAINED`. Exactly nine emitted
lines start with `TE-1` padded to ten and hold `rate limited`. The host measured
`datetime.fromtimestamp`
raising `OverflowError` on `10**20` and `ValueError` on `10**12` on
2026-09-23.

**Criterion 5's witness** follows
`test_an_unreadable_reset_time_still_stops_rate_limited`
(`tests/test_session.py:4433`), with `_stub_the_runtime`, `_drive` and
`_rejected`. For each of the six values it asserts `outcome.resets_at`.
`1755800000` and `10**20` stay themselves, asserted by type as `int` and by
value. The other four give `None`. These fail it:

- the raw value from `RateLimited`, which carries `"soon"` through
- `None` on every path
- `None` for a time `events.when` renders `"unknown"`, which drops `10**20`
- the reset time as a `float`

**The wrong versions these witnesses kill** were measured on 2026-09-23.
A throwaway model of the loop's rule ran them, not `run_stack_batch`,
which the tree at `4797e80e` lacks. It recomputes `SA-0143`'s refusals
after each task, and its runner can advance the clock. The model ran each
table above under
`TZ=America/Los_Angeles` and `TZ=UTC`. The right build passed all four
criteria. Each wrong build failed at least one, under both zones.

- a rate limit treated as `EXHAUSTED`: a miss, the breaker reset, no wait
- the spec run again after the rest of the order
- the rate-limited task made a layer, so its second task stacks on itself
- the wait taken, but the rate limit recorded as a miss, so `TE-3` is
  refused
- the rate limit recorded as a miss and cleared by the second task, under
  a refusal map `SA-0143` recomputes each rescan. The calls match, and a
  false refused line for `TE-3` is what fails it.
- the wait computed from the real clock
- the wait counted from a `now` read before the task ran
- the rate-limited run left unattached, so the spend is 3.0
- an `UNTIL` stop that returns before the attach, leaving the spend at 0.0
- a line naming `now` in place of the wait's end
- a line only for a readable reset time
- a line emitted before the `UNTIL` stop
- the distance to `until` taken from the clock read before the task
- the subtraction made before the bounds test, which raises on `10**400`
- a spec once rate-limited left out of the miss set for the night, so
  `TE-3` in criterion 2 is not refused
- `datetime.fromtimestamp(resets_at)` compared with the clock
- `datetime.fromtimestamp(resets_at, UTC)` compared with the clock
- `datetime.utcfromtimestamp(resets_at)` compared with the clock
- a wait always to `until`
- a full wait whatever `until` says
- a sleep until `until`, then the `UNTIL` stop
- the `UNTIL` stop for every rate limit whenever `until` is set
- the stop only for a wait strictly past `until`, so a wait ending at it
  sleeps
- a rate limit counted toward the breaker, or counted on its first
  occurrence only
- a rate limit that resets the breaker
- a wait and a second call inside the runner, past every check
- no cap on a readable reset time
- a reset time past the cap waited for six hours, not the hour
- a reset time exactly six hours on sent to the hour's default
- `fromtimestamp` called on the reset time with nothing caught
- only `OverflowError` caught, so `10**12` raises out of the loop
- a reset time equal to now read as readable
- the wait applied in `run_batch` too
- for a missing reset time, no wait at all

A build that calls `time.sleep` by its module attribute meets the raising
double and fails. One that binds `time.sleep` as an inner default would
sleep for real and hang the witness. That is why inner functions take no
default.

**What the witnesses leave undriven.** `cli._stack_runner` is `SA-0143`'s,
and its criterion 6 has it call `run_task`. Nothing here drives the
outcome from there to the loop. `saffron/cli.py` is forbidden here. If
`_stack_runner` returns anything but `run_task`'s own object, say so in
your notes.
Criterion 5 drives the handler in `run_one_cell` alone. A `Refused` or a
raise after a rate limit is not driven. A rate limit ends no layer, so each
is read as it is today.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/cell/session.py` is in `elevate_on`, so `size` blocks at
the `feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`).
About 45 changed lines in `batch.py` at 6.6 tokens a line and 5 in
`session.py` at 5 come to about 325 tokens. About 260 lines in
`tests/test_batch.py` at 3.5 and 20 in `tests/test_session.py` at 5.7 come
to about 1025. That is about 1350 tokens. Keep test docstrings short.
