---
id: SA-0388
title: "A reset stamp becomes text in `events.when` and again in the batch's wait, while `when`'s docstring calls itself the one place"
type: refactor
priority: 3
estimated_lines: 160
estimate_measured: true
touches:
  - saffron/events.py
  - saffron/batch.py
  - tests/test_events.py
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
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/view/**
  - saffron/cli.py
  - saffron/spec_review.py
  - saffron/task.py
  - saffron/watch.py
  - tests/fixtures/**
  - tests/test_session.py
  - tests/test_spec_review.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 22
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `events.when` takes a keyword-only `now`, a `datetime` that defaults to
      `None`. Called without it, `when` renders a stamp as base did: the
      host's zone, the day dropped when it is today, and a trailing ` local`.
      Called with it, `when` renders the stamp as `_wait_out_rate_limit`
      did at base: `%a %d %b %H:%M` in `now`'s own `tzinfo`, a naive `now`
      reading the host's zone, always with the day and never with a suffix.
      Each form keeps its own conversion, so `10**12` renders a date in the
      first and `unknown` in the second. The witness pins the host's zone to
      UTC+9 and renders each stamp in four forms: no `now`, a naive `now`,
      and aware ones at minus seven hours and plus five hours 45 minutes.
      Each `now` falls on the stamp's own calendar day in its zone. The
      stamps are `1755800000`, `1755800000.0`, `10**12`, `None`, `True`,
      `False`, `"soon"`, `[1]`, NaN, `10**17`, `10**20` and `10**400`. Every
      one but the first three renders `unknown` in all four forms. The
      witness also renders noon today with no `now` as `12:00 local`.
    witness: tests/test_events.py::test_when_renders_each_reset_stamp_in_both_forms
    wrong_versions:
      - "The `now` form renders in the host's zone, ignoring `now.tzinfo`."
      - "The `now` form ends with ` local`."
      - "The `now` form drops the day when the stamp falls on `now`'s own day."
      - "The `now` form converts with `time.localtime`, so `10**12` renders a date."
      - "The form without `now` converts with `datetime.fromtimestamp`, so `10**12` renders `unknown`."
      - "The form without `now` always names the day, so noon today reads with its weekday."
      - "The form without `now` drops ` local`, or converts with `time.gmtime`."
      - "A bool is no longer refused, so `True` renders 1 January 1970."
      - "Only a bool is refused, so `None`, a string or a list raises."
      - "Only `OverflowError` and `ValueError` are caught, so `10**17` raises `OSError`."
  - claim: >-
      `_wait_out_rate_limit` takes its reset text from `events.when`, handing
      it the very object its one clock read returned. It calls
      `when` only for a reset after the clock. A missing reset, one equal to
      the clock, one before it, NaN and `True` read `unknown` with no call.
      The witness replaces `when` with a spy that records each call and
      returns a sentinel. It sets the spy on `saffron.events` and, where the
      name exists, on `saffron.batch`, so either spelling of the import
      reaches it. It drives one stack batch on an aware clock at minus seven
      hours, from 16:39 on 1 January 2030. The resets are 18:00 that day,
      `10**12`, a missing one, one equal to the clock, one 60 seconds before
      it, NaN and `True`. It asserts each wait line exactly. It also asserts
      the spy saw two calls, each with its reset and a `now` that equals the
      clock's and is that object by identity.
    witness: tests/test_batch.py::test_a_rate_limit_wait_line_reads_its_reset_through_events_when
    wrong_versions:
      - "`_wait_out_rate_limit` keeps its own `datetime.fromtimestamp` render."
      - "`_wait_out_rate_limit` calls `when` without `now`, so its line gains ` local`."
      - "`_wait_out_rate_limit` hands `when` the clock's `now` converted to UTC."
      - "`_wait_out_rate_limit` hands `when` a copy of `now` with its microseconds cleared."
      - "`_wait_out_rate_limit` hands `when` a new `datetime` built from `now`'s timestamp in `now`'s own zone."
      - "`_wait_out_rate_limit` reads the clock a second time for `when`."
      - "`_wait_out_rate_limit` calls `when` for every reset and drops its own `unknown`."
  - claim: >-
      Each line a stack batch's wait prints is byte-identical to base. The
      existing witness drives a naive clock and aware clocks at minus seven
      hours and plus five hours 45 minutes. Under each it pins the line for
      a reset past the cap, one inside it, a missing one, one equal to the
      clock, one 60 seconds before it, `10**12`, `10**20`, `10**17` and
      `10**400`.
    witness: tests/test_batch.py::test_a_rate_limit_wait_line_names_the_providers_reset_beside_the_retry_hour
    preserves: true
    wrong_versions:
      - "The batch's reset is rendered in the host's zone."
      - "The batch's reset carries ` local`."
      - "A reset that raises `OSError` ends the batch."
  - claim: >-
      The wait's own bounds do not move, for the resets the existing witness
      drives. A reset six hours and one second or more after the clock waits
      the six-hour cap, `10**12`, `10**20`, `10**17` and `10**400` included.
      A reset inside the cap, 4860 seconds on, is waited in full. A missing
      reset, one equal to the clock and one before it each wait one hour.
    witness: tests/test_batch.py::test_a_stack_batch_waits_six_hours_for_a_reset_past_the_cap
    preserves: true
    wrong_versions:
      - "The batch treats a reset `when` renders `unknown` as not after the clock, so `10**12` waits one hour."
  - claim: >-
      `describe`'s rendering of a stamp without `now` is unchanged. A stamp
      on another day reads in the host's zone with its day and ` local`.
    witness: tests/test_events.py::test_when_renders_a_readable_reset_time_in_local_time
    preserves: true
    wrong_versions:
      - "The form without `now` drops ` local`."
      - "The form without `now` converts with `time.gmtime`."
  - claim: >-
      A `rate_limit` agent event whose `resets_at` is a string, a list,
      `10**20` or NaN still describes as `resets unknown`, never a raise.
    witness: tests/test_events.py::test_describe_renders_whatever_it_is_handed
    preserves: true
    wrong_versions:
      - "Only a bool is refused, so a string raises."
---

## Context

Backlog item **b-e11fb7**, filed 2026-11-13 from the spec loop's review of
`SA-0385` (#1189). It cites `DESIGN.md` §5.1. Item 104 merged the last
pair of reset renderers. Every line number below was read at `2b093e64`.

**The first renderer.** `events.when` (`saffron/events.py:753`) refuses a
bool or a non-number (`saffron/events.py:774-775`). It converts with
`time.localtime` and reads today the same way, catching `OverflowError`,
`OSError` and `ValueError` (`saffron/events.py:776-780`). It drops the day
when the stamp falls today, and ends ` local` (`saffron/events.py:781-782`).
Its docstring calls it "the one place a unix reset time becomes something
an operator can act on" and names a single caller
(`saffron/events.py:754-758`). `_describe_agent_event` calls it for a
`rate_limit` event (`saffron/events.py:843`). `describe` calls it for a
`RATE_LIMITED` `TaskOutcome` (`saffron/events.py:999`). No other module
imports `when`.

**The second renderer.** `SA-0385` added one to `_wait_out_rate_limit`
(`saffron/batch.py:411`). The wait trusts a reset only after the clock
(`saffron/batch.py:430`). It renders such a reset with
`datetime.fromtimestamp(resets_at, now.tzinfo)` as `%a %d %b %H:%M`,
catching the same three exceptions (`saffron/batch.py:436-442`). Any other
reset reads `unknown` (`saffron/batch.py:443-444`). The line is printed at
`saffron/batch.py:445-448`. `SA-0385` could not call `when`. The two
render differently, and `saffron/events.py` was in its `forbidden`.

**Why the two forms keep their own conversion.** The two conversions part
on one stamp. This was measured under `TZ=XXX-9` with the macOS host's
Python and with Python 3.12.15 in `saffron/cell-base:python`, and both
printed the same. `time.localtime(10**12)` gives a date in the year 33658,
which `when` prints as `Fri 27 Sep 10:46 local`. `datetime.fromtimestamp`
raises `ValueError` for it, so the batch prints `unknown`. On every other
number the criteria name, both conversions succeed or both raise.
`10**17` raises `OSError` on macOS in `time.localtime` and in the
timestamp constructor, naive or aware. `10**20`, `10**400` and NaN raise
too.

## Problem

Two functions turn the same untrusted stamp into text. Each catches the same
three exceptions, and `when`'s docstring names a caller list that is no
longer whole.

1. **`saffron/events.py`, `when`.** Add a keyword-only `now`, a `datetime`
   defaulting to `None`. `saffron/events.py` imports no `datetime` at base,
   so the annotation needs one, at runtime or under `TYPE_CHECKING`. The
   `now` form converts at runtime, so it needs the real import. Widen
   `stamp`'s annotation to `object`, since a cell sends any JSON value. Keep
   the type refusal first, for both forms. With `now` set, convert through
   `datetime`'s own timestamp constructor in `now`'s zone and format
   `%a %d %b %H:%M`, inside the same `try` and the same three exceptions.
   Without `now`, the body stays as it is. Rewrite the
   docstring to name both callers and both forms, within the `prose` gate's
   ten lines.
2. **`saffron/batch.py`, `_wait_out_rate_limit`.** Replace the render at
   `saffron/batch.py:436-444` with a call to `events.when` for a reset after
   the clock. Hand it the clock read the function already holds. The
   `after_clock`, cap and `until` lines above it stay exactly as they are, and so does the `unknown` for any
   other reset.
3. **`tests/test_events.py`, `tests/test_batch.py`.** Add the two new
   witnesses. Leave every existing test unedited.

## Out of scope

- **Converging the two forms.** Showing the batch's reset with ` local`, or
  dropping its day, changes an operator's line. So does rendering
  `10**12` as a date in one place or `unknown` in the other. Each wants its
  own item.
- **The spec review's wait.** `_drive` hands its reset to the same wait
  function (`saffron/batch.py:320-323`), so the call reaches it. No witness
  drives that route.
- **A clock before 00:00:01 UTC on 1 January 1970.** Only there does a `True`
  reset lie after the clock. Base rendered it as a date, and the shared
  refusal renders `unknown`. No producer hands the wait a bool.
  `session._resets_at_fields` drops one (`saffron/cell/session.py:257`), and
  `spec_review._reset` floors to a positive `int` (`saffron/spec_review.py:296-298`).

## Notes for the agent

**This is a refactor.** Criteria 3 to 6 are `preserves`. Each names a test
that passes at base, and each must pass unedited. Criteria 1 and 2 are new
witnesses. At base, criterion 1 fails on its first `now=` call with
`TypeError`. Criterion 2 reads the batch's own date in place of its spy's
sentinel. Their subject is a parameter and a call that do not
exist at base, so they declare no mutant and `witness` reports `skip` for
them. `refs/saffron/mutants` is absent from origin
(`git ls-remote origin refs/saffron/mutants` prints nothing), so the
preserves criteria carry none either. The wrong versions under each
criterion are what its witness must kill. Do not run them yourself.

**How byte-identity is proven.** `describe`'s two branches keep calling
`when` with no `now`, and their code does not change. So their lines stay
the same exactly when the form without `now` does. Criterion 1 pins that
form for every stamp it names, and criteria 5 and 6 pin it as base did.
The batch's lines are pinned by criterion 3 across three zones and nine
resets, and by criterion 2 for NaN and `True`. A string reset raises at
the untouched comparison on `saffron/batch.py:430`, as at base.

**Criterion 1's witness.** Set `TZ` with `monkeypatch.setenv("TZ",
"XXX-9")` and call `time.tzset()`, then undo both in a `finally`, as
`test_when_renders_a_readable_reset_time_in_local_time` does. Put the
four forms of each stamp in one tuple and compare it with the expected
tuple. The clocks are `datetime(2025, 8, 22, 1, 0)` naive,
`datetime(2025, 8, 21, 9, 0)` at minus seven hours and
`datetime(2025, 8, 21, 20, 0)` at plus five hours 45 minutes. Each lies on
the stamp's own day in its zone. For `1755800000` and `1755800000.0` the
four texts are `Fri 22 Aug 03:13 local`, `Fri 22 Aug 03:13`,
`Thu 21 Aug 11:13` and `Thu 21 Aug 23:58`. For `10**12` they are
`Fri 27 Sep 10:46 local` and three `unknown`. Build noon today from
`time.localtime()` with `time.mktime`. Import `datetime` inside the test.

**Criterion 2's witness.** Drive `run_stack_batch` with `AdvancingClock`,
`RateLimitScript` and `_raise_on_real_sleep`, as
`test_a_rate_limit_wait_line_names_the_providers_reset_beside_the_retry_hour`
does. Give the spy the signature `(stamp, *, now=None)`. Set it with
`monkeypatch.setattr(events, "when", spy)` and
`monkeypatch.setattr(batch, "when", spy, raising=False)`, both modules
imported inside the test. The lines retry at 18:00, 00:00, 01:00, 02:00,
03:00, 04:00 and 05:00. The first two read the sentinel and the rest read
`unknown`. Record each call as its stamp, its `now`, and whether that `now`
is the clock's own object by identity. Inside the spy, compare with `is`
against a fresh read of `clock()`. A read of `AdvancingClock` returns the
object it holds, and only a sleep or an advance of it replaces that
(`tests/test_batch.py:237-253`). So a copy fails, though it compares
equal: one with its microseconds cleared, one rebuilt in the same zone, or
one converted to UTC.

**Docstrings and comments.** The `prose` gate reads each one. `when`'s
docstring at base runs past ten lines, and every line past ten in a
rewritten one is a new hit.
