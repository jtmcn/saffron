---
id: SA-0385
title: "A rate-limit reset past six hours is waited as an unknown hour, so batch 84 started `SA-0380` nine times before its window reopened"
type: bug
priority: 2
estimated_lines: 14
estimate_measured: true
touches:
  - saffron/batch.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/agents/**
  - saffron/cli.py
  - saffron/events.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/task.py
  - saffron/follow_up.py
  - saffron/finish.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - tests/test_cli.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 26
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      When a stack batch's `RATE_LIMITED` task names a reset more than six
      hours after the clock, `_wait_out_rate_limit` sleeps six hours, the
      cap, and the batch starts the same spec again. A reset at most six
      hours on is still waited in full. A missing reset, or one at or before
      the clock, still sleeps one hour. The witness drives one batch. It
      meets a reset at 06:00 the next day three times, at 16:39, 22:39 and
      04:39, so the first two lie past the cap and the third inside it.
      Its other past-cap resets are six hours and one second on, seven
      hours on, `10**12`, `10**20`, `10**17` and `10**400`. It then meets a missing
      reset, one equal to the clock and one 60 seconds before it.
    witness: tests/test_batch.py::test_a_stack_batch_waits_six_hours_for_a_reset_past_the_cap
    wrong_versions:
      - A reset past the cap still sleeps one hour, as at base.
      - The full-wait bound widens to seven hours, so the reset six hours and one second on sleeps that long.
      - A reset past the cap sleeps the cap only when it renders as a date, so `10**12`, `10**20`, `10**17` and `10**400` sleep one hour.
      - Every reset the wait cannot read sleeps the cap, so the missing reset sleeps six hours.
      - A reset at or before the clock sleeps the cap.
      - A reset equal to the clock counts as ahead of it.
      - A reset past the cap sleeps its own distance, so `10**400` raises in the subtraction.
  - claim: >-
      The capped wait meets `--until` the way any wait meets it at base.
      The six-hour wait is compared with the time left to `until`. A wait
      at or past `until` stops the batch `UNTIL` at once, with no sleep and
      no line. A wait short of it sleeps, and the spec starts again before
      `until`. The witness drives a reset 13 hours 21 minutes on in two
      batches, one with `until` six hours away and one with it eight hours
      away. The second starts the spec at the clock's start and again six
      hours later, then stops `UNTIL` on the next rejection.
    witness: tests/test_batch.py::test_a_reset_past_the_cap_stops_at_until_rather_than_wait_past_it
    wrong_versions:
      - "`until` is compared with the provider's reset rather than the wait, so the eight-hour deadline stops the batch with no sleep."
      - A reset past the cap skips the `until` comparison, so the six-hour deadline still sleeps.
      - The comparison is strict, so a wait equal to the time left still sleeps.
      - The wait is cut to the time left to `until`, slept, and only then stops the batch.
  - claim: >-
      Each wait's line reads `<spec id padded to 10> rate limited, window
      reopens <reset>, retrying <HH:MM>`. `<HH:MM>` is the hour the batch
      starts the spec again, as base prints it. `<reset>` is the provider's
      own reset as `%a %d %b %H:%M` in the clock's own zone, read from the
      clock's `tzinfo`. It reads `unknown` for a missing reset, one at or
      before the clock, and one no date can hold. The witness drives a
      naive clock and aware clocks at minus seven hours and plus five hours
      45 minutes. Under each it drives a reset past the cap, one inside it,
      a missing one, one equal to the clock, one 60 seconds before it, and
      `10**12`, `10**20`, `10**17` and `10**400`.
    witness: tests/test_batch.py::test_a_rate_limit_wait_line_names_the_providers_reset_beside_the_retry_hour
    wrong_versions:
      - The reset is rendered in the host's zone, so an aware clock's line names another hour.
      - A reset before the clock is named as its own date rather than `unknown`.
      - A reset equal to the clock is named as its own date, while the wait still reads it as not ahead.
      - "The reset carries `events.when`'s ` local` suffix."
      - The reset part repeats the retry hour.
      - The line drops the retry hour.
      - A reset no date can hold raises rather than reading `unknown`.
      - Only ValueError and OverflowError are caught, so a reset that raises OSError ends the batch.
---

## Context

Backlog item **b-45783e**, filed 2026-11-13. It cites `DESIGN.md` §5.1.
§4.2.1 says a `RATE_LIMITED` task waits for its window to reopen and is not
counted by the breaker. Every line number below was read at `cb4ad504`.

**How the wait reads a reset now.** `_drive` calls `_wait_out_rate_limit`
for a `RATE_LIMITED` outcome when `sleep` is set
(`saffron/batch.py:373-380`). It calls it for a `SpecReviewWait` too
(`saffron/batch.py:317-325`). The function reads the clock once
(`saffron/batch.py:427-428`). It trusts a reset only when it lies after
the clock and at most 21600 seconds on (`saffron/batch.py:429`). Any other
value waits 3600 seconds (`saffron/batch.py:430`). A wait at or past the
time left to `until` returns `UNTIL` before any line or sleep
(`saffron/batch.py:431-432`). Otherwise the line names the clock plus the
wait as `%H:%M`, and the function sleeps (`saffron/batch.py:433-435`).

**What a reset can be.** `resets_at` reaches the wait as an `int` or
`None`. `_resets_at_fields` passes a clean `int` and turns any other value
into `None` (`saffron/cell/session.py:249-255`). A spec review floors an
unreadable reset, 0 and a negative one to `UNREADABLE_RESET`, which is 1
(`saffron/spec_review.py:65`, `saffron/spec_review.py:291-298`). The
function's docstring warns that a cell's `resets_at` can be too large for a
plain subtraction (`saffron/batch.py:425-426`).

**What pins it now.**
`test_a_stack_batch_waits_an_hour_when_it_cannot_read_the_reset_time`
drives nine resets and expects eight one-hour sleeps
(`tests/test_batch.py:2976-3022`). Four of them lie past the cap: `10**20`,
`10**12`, seven hours on and `10**400` (`tests/test_batch.py:2989-2994`).
`test_a_stack_batch_waits_out_a_rate_limit_and_runs_the_same_spec_again`
reads `"03:05"` in its line (`tests/test_batch.py:2611`).

## Problem

Batch 84 met the weekly limit on `SA-0380` at $22.90. The cell's own line
said `window reopens Fri 13 Nov 06:00 local`, about thirteen hours away.
That reset lay past the cap, so the batch waited one hour and started
`SA-0380` again. It did so nine times overnight. Each start built the
cell image and booted the proxy, and each was rejected at $0. Each wait's
line named a new reopen hour, such as 22:00, 23:04 and 00:08, none of them
the provider's.

1. **`saffron/batch.py`, `_wait_out_rate_limit`.** A reset after the clock
   and more than 21600 seconds on waits 21600 seconds. Compare before any
   subtraction, as the docstring says. A missing reset, or one at or before
   the clock, still waits 3600 seconds. The `until` comparison stays as it
   is, against the wait. The line becomes
   `rate limited, window reopens <reset>, retrying <HH:MM>`. `<HH:MM>` is
   today's clock plus the wait. `<reset>` renders a reset after the clock
   with `datetime.fromtimestamp(resets_at, now.tzinfo)` as `%a %d %b
   %H:%M`. A naive clock then reads local time, as `datetime.now` does. A
   reset that raises `OverflowError`, `OSError` or `ValueError` there reads
   `unknown`, and so does a missing or past one. Add one sentence to the
   docstring.
2. **`tests/test_batch.py`.** In
   `test_a_stack_batch_waits_an_hour_when_it_cannot_read_the_reset_time`,
   drop the four past-cap steps. Its counts become six calls, the sleeps
   `[3600.0] * 4 + [21600.0]`, and five lines. Its docstring's first
   sentence then says that a missing reset, or one at or before now, waits
   an hour. Its second reads "Only a value strictly after now and no more
   than six hours on is waited in full." Add the three witnesses.

## Out of scope

- **A stop at once for a reset beyond `until`.** Take a reset 13 hours on
  and `until` eight hours away. The batch still sleeps six hours and starts
  the spec once more. The decision kept today's `until` comparison.
- **The `SpecReviewWait` route.** It calls the same function, so the cap
  and the line reach it. No witness drives it.
- **Plain `run_batch`.** Its wait needs a `sleep` from its caller, and
  `saffron/cli.py` passes none (`saffron/cli.py:2705-2714`).
- **A cap other than six hours.** SA-0148 chose it, and this spec keeps it.
- **The cell's own line** in `saffron/events.py`. It already names the
  provider's reset.

## Notes for the agent

**The criteria are new behaviour on edited code.** None declares a mutant,
because the head spelling of the cap branch is the cell's to choose.
`witness` will report `skip`. The wrong versions under each criterion name
what its witness must still catch. `refs/saffron/mutants` is absent from
origin today. Criterion 2's code is the one an operator could pin with
`saffron mutant`, as the `until` comparison at `saffron/batch.py:431`
turned strict. This spec quotes no text of it, since intake refuses a
mutant whose text the body spells.

**At base each witness fails in its body.** The first sees one-hour sleeps.
The second sees a sleep under the six-hour deadline. The third sees the old
line. Import nothing the change adds at module scope.

**Seeding the witnesses.** Each drives `run_stack_batch` with
`AdvancingClock`, `RateLimitScript` and `_raise_on_real_sleep`, as
`test_a_stack_batch_stops_at_until_rather_than_wait_past_it` does. Start
the clock at 2030-01-01 16:39. Build the 13-hour reset as
`datetime(2030, 1, 2, 6, 0).timestamp()` in the clock's own zone.

- **Criterion 1.** Pass the steps in the claim's order, then
  `READY_FOR_REVIEW`. The prototype saw thirteen calls and the sleeps
  `[21600.0, 21600.0, 4860.0] + [21600.0] * 6 + [3600.0] * 3`. The third
  13-hour step meets the clock at 04:39, so its reset lies inside the cap.
- **Criterion 2.** Queue three 13-hour steps. Wrap the runner so each call
  records the clock. With `until` six hours on, expect one start, no sleep
  and no `rate limited` line. With it eight hours on, expect starts at the
  clock's start and six hours later, `[21600.0]`, and one line.
- **Criterion 3.** Loop over the three zones. Build each reset with the
  loop's `tzinfo`. The inside-cap reset is 2030-01-02 00:00, met at 22:39.
  Compare the `rate limited` lines with `==` against the whole list. The
  prototype's list read `Wed 02 Jan 06:00, retrying 22:39`, then `Wed 02
  Jan 00:00, retrying 00:00`, then `unknown` with `01:00`, `02:00`,
  `03:00`, `09:00`, `15:00`, `21:00` and `03:00`. The step equal to the clock is
  `{"offset": 0}`, because every wait ends on a whole minute.

**Where the render raises.** `datetime.fromtimestamp` raised `ValueError`
for `10**12`, `OSError` for `10**17` and `OverflowError` for `10**20` and
`10**400`. That held on macOS with Python 3.14 and on Linux glibc 2.41 with
Python 3.12, naive and aware alike (measured). Each of the three types has
a driven reset, and all three sit in the caught set.

**Each negative clause has its positive case in the same instrument.** The
first witness's one sleep list holds the six-hour sleeps and the one-hour
ones. The second witness's start list and sleep list each see a sleep at
eight hours before they see none at six. The third witness's one list holds
named resets beside `unknown` ones.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**No `depends_on`.** The one queued spec, `SA-0381`, touches
`saffron/follow_up.py` and `tests/test_follow_up.py`. This change refuses
nothing new, so no `retired_first` entry applies.

**Size.** A prototype measured 53 changed tokens with `size_gate`, against
the `bug` ceiling of 1300, with 601 more under the test paths. It held the
cap, the line, the docstring sentence, the three witnesses and the trimmed
pin. Every test in `tests/test_batch.py` passed on it.
