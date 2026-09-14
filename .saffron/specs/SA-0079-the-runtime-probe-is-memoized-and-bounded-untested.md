---
id: SA-0079
title: nothing tests that the cell runtime is asked once per process, or that a runtime hung on its version query is given up on within seconds
type: test
priority: 3
depends_on: []
touches:
  - tests/test_runtime.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - spikes/**
  - saffron/**
  - tests/conftest.py
budget_usd: 4
max_attempts: 3
max_turns: 30
acceptance:
  - claim: >-
      The cell runtime is asked for its version once per process, however many
      times a test session asks whether it is present. Asked once per
      `cell`-marked test instead, it would start one process per test, and
      there can be dozens.
    witness: tests/test_runtime.py::test_the_runtime_is_asked_once_however_often_it_is_probed
    mutant:
      file: saffron/cell/runtime.py
      find: _probed = True
      replace: _probed = False
  - claim: >-
      A runtime that hangs when asked for its version reports as absent once the
      probe's own timeout passes, and that timeout is short: a hung runtime
      costs a test session seconds, not minutes.
    witness: tests/test_runtime.py::test_a_runtime_that_hangs_reports_as_absent_within_seconds
    mutant:
      file: saffron/cell/runtime.py
      find: '"--version"], timeout_s=10)'
      replace: '"--version"], timeout_s=120)'
  - claim: >-
      A runtime that is missing, or present but unrunnable, still reports as
      absent, as it does today.
    witness: tests/test_runtime.py::test_a_runtime_that_cannot_be_executed_reports_as_absent
    preserves: true
  - claim: >-
      A runtime that runs still reports the version it printed, as it does
      today.
    witness: tests/test_runtime.py::test_a_runtime_that_runs_reports_the_version_it_printed
    preserves: true
---

## Context

`docs/BACKLOG.md` item **111**, found reviewing `SA-0077` (PR #232), 2026-09-12.

`runtime.probe()` (`saffron/cell/runtime.py`) answers whether the selected cell
runtime can run by running its `--version`. `SA-0077` wired it into
`pytest_runtest_setup`, so a `cell`-marked test on a machine with no runtime is
skipped instead of failing. `probe()` does two things nothing tests. Deleting
either one leaves the whole suite green, which that review measured:

- It remembers its answer for the life of the process, so a session with dozens
  of `cell`-marked tests starts the runtime once, not once per test.
- It gives the runtime a short timeout. The same review measured that a runtime
  hanging on `--version` reports absent after 10.0s. Without the timeout, one
  hung runtime would stall the test session.

## Problem

Both properties are true today and nothing guards either. The next edit to
`probe()` can remove one and every test will still pass.

## Out of scope

**Whether an installed runtime whose service is stopped still reports present.**
`container --version` looks like a client-side call, so it may. That is
unverified, and `SA-0077` also put it out of scope.

**The length of `probe()`'s and `pytest_runtest_setup`'s docstrings.** The same
review found both longer than this repo keeps comments. `saffron/**` and
`tests/conftest.py` are forbidden here, so that is done by hand.

**Any change to `probe()` itself.** This spec adds tests and nothing else.

## Notes for the agent

**The criteria declare mutants because the code already exists.** Its text is
fixed, so a mutant can target it honestly. `revert` will report `skip` on this
spec, and that is expected: the diff has no source outside the test paths, so
there is nothing to revert. `witness` is the gate that judges these tests.

**Reset the probe's memo around each test,** with `monkeypatch`, the way the
neighbouring `probe()` tests do. Otherwise the first test to probe decides the
answer for every test after it, and the order of the suite becomes part of the
result.

**Drive a real process,** a shell-script stub in `tmp_path`, as
`test_a_runtime_that_runs_reports_the_version_it_printed` does. A stubbed
`_call` shows only that the plumbing forwards a value it was handed. To count
how many times the runtime was asked, have the stub record each invocation
somewhere the test can read, such as a file under `tmp_path`.

**Do not name the stub after a runtime's own binary.** The tripwire in
`tests/conftest.py` refuses to let an unmarked test run any runtime's binary or
`gh`, bare or as a path.

**The second claim is about how long, not only whether.** A test that shows only
that *some* timeout ends the wait does not witness it. A test that waits out the
real timeout costs the default suite that many seconds on every run. So scale
the value `probe()` hands to `_call` inside the test, by wrapping `_call` and
dividing what it is given, rather than replacing it with a small constant. That
way the test still depends on the value `probe()` chose.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and `integrity` fails that suppression
even inside `touches`.
