---
id: SA-0127
title: A handed name the `tests` gate cannot collect buys `revert` a `skip`, because the contract has no field to say so
type: bug
priority: 1
depends_on: []
touches:
  - saffron/gates/contract.py
  - saffron/gates/core/revert.py
  - tests/test_contract.py
  - tests/test_revert.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/ledger.py
  - saffron/phases/**
  - saffron/cell/**
  - saffron/agents/**
  - saffron/gates/runner.py
  - saffron/gates/suite.py
  - saffron/gates/core/census.py
  - saffron/gates/core/criteria.py
  - saffron/gates/core/witness.py
  - tests/test_gates.py
  - tests/test_scheduler.py
budget_usd: 18
max_attempts: 3
max_turns: 100
risk: elevated
acceptance:
  - claim: >-
      A gate result carries an optional `uncollected` list of names, read from
      a gate's JSON. A gate that sends names, an empty list, or no key at all
      gives three different values, and no key gives `None`.
    witness: tests/test_contract.py::test_a_gate_may_report_the_names_it_could_not_collect
  - claim: >-
      When the reverted run reports `uncollected` and returns `pass` or `fail`
      with an enumeration, a handed name it neither collected nor listed makes
      `revert` report `error`, and the summary names that name. This holds for
      an empty `uncollected` and for a non-empty one. A reverted run that
      errored, or that did not enumerate, is still a `skip` whatever it
      reports.
    witness: tests/test_revert.py::test_a_handed_name_the_reverted_run_does_not_account_for_is_an_error
  - claim: >-
      A reverted run that lists every handed name as `uncollected` is a
      `pass`. One that lists one name while another ran and passed is a
      `fail`. The summary of each verdict names the listed test.
    witness: tests/test_revert.py::test_each_verdict_names_the_tests_the_reverted_run_could_not_collect
  - claim: >-
      A reverted run that errored and reports no `uncollected` is still a
      `skip` whose summary says it returned no readable verdict.
    witness: tests/test_revert.py::test_a_reverted_run_that_could_not_produce_a_result_is_a_skip_not_an_error
    preserves: true
    mutant:
      file: saffron/gates/core/revert.py
      find: 'if reverted_result.status not in ("pass", "fail"):'
      replace: 'if reverted_result.status not in ("pass", "fail", "error"):'
  - claim: >-
      A reverted run that reports no `uncollected` and enumerated none of the
      handed names is still a `pass`, as it is today.
    witness: tests/test_revert.py::test_a_reverted_run_that_enumerated_nothing_still_passes
    preserves: true
    mutant:
      file: saffron/gates/core/revert.py
      find: 'if reverted_result.collected is None:'
      replace: 'if not reverted_result.collected:'
---

## Context

Backlog items **50** and **51**, which close on one contract addition (their
Record lines of 2026-09-04). Item 49 is out of scope here.

`revert` hands the repo's `tests` gate a subset of names and reads what comes
back (`saffron/gates/suite.py:170-176`). A reverted run whose status is
neither `pass` nor `fail` is a `skip` (`saffron/gates/core/revert.py:272-295`).
So is one that did not enumerate (`saffron/gates/core/revert.py:313-318`). A
handed name missing from the run's enumeration counts as an acceptable answer
(`saffron/gates/core/revert.py:340-344`).

This repo's `tests` gate collects the whole subset in one pytest call
(`.saffron/gates/tests.py:36-48`) and runs it in one more
(`.saffron/gates/tests.py:50-54`). It reports `error` when pytest exits
non-zero and no failure line parses (`.saffron/gates/tests.py:96-104`).

**Measured 2026-09-22 on the host, pytest 9.1.1.** A fixture repo held one
passing test and one test importing a missing module. Collecting a real id
beside `zzz::bogus` prints `ERROR: file or directory not found: zzz::bogus`
and exits 4. Collecting the importing test exits 4 on the collection error.
The base `tests` gate, handed a real id and `zzz::bogus`, printed
`{"gate": "tests", "status": "error", ..., "summary": "pytest exited 4 with
no parsed failures"}`. So both items reach `revert` as the same `skip`.

**The contract today drops an unknown key.** `GateResult` sets no
`model_config` (`saffron/gates/contract.py:60-81`), and pydantic's default
ignores extra fields. Measured on this base: `parse_gate_json` given
`"uncollected": ["a::b"]` returns a result with no trace of it.

## Problem

Item 50: the spec shape `revert` was built for, a module landed with its
tests, gets no evidence. Reverting the module makes the new tests fail to
import, and the gate reports `skip`. Item 51: a cell buys the same `skip`
for one printed line. An `atexit` handler in a new test file prints a line
holding `::`. The collection calls it a name, and the reverted run errors
on it. Every real new test in that attempt then goes unjudged.

The fix is a contract field that says what became of each handed name. A
name the run could not collect then reads as a test that failed without its
source, which is the answer `revert` wants. The names the run did collect
stay judged.

## Out of scope

**This repo's `tests` gate.** `.saffron/**` is `protected`, so the operator
fills the new field in `.saffron/gates/tests.py` by hand after this spec
merges. Until then this repo's gate reports no `uncollected`, and `revert`
judges it exactly as today. Items 50 and 51 close `partial` on this spec and
close in full when that edit lands.

**`DESIGN.md` §5.4's contract text.** The operator writes it by hand.

**`census`, `criteria` and `witness`.** None of them reads the new field.

**Item 49**, a test whose body changed under the same name.

## Notes for the agent

**The field.** Add it to `GateResult` in `saffron/gates/contract.py`, beside
`collected` and typed the same way. `None` and `[]` are different facts, as
they are for `collected` (`saffron/gates/contract.py:71-77`). Its docstring
says what it holds and that only `revert` reads it, within ten lines.

**Where `revert` reads it.** After the status check at
`saffron/gates/core/revert.py:272` and the enumeration check at
`saffron/gates/core/revert.py:313`, and before the readability guard at
`saffron/gates/core/revert.py:330`. Leave those two checks as they stand.
Criteria 4 and 5 put a mutant on each. When the field is `None`, nothing
this spec adds runs. That path stays today's, byte for byte.

**Why `error` for an unaccounted name.** A runner that reports what became
of each handed name and leaves one out breaks its own contract. `error`
means the gate broke (`CLAUDE.md`'s invariant that `error` ≠ `fail`).
`aborted_gates` ends the attempt on it (`saffron/gates/suite.py:33-36`).
A `skip` here would be the silence items 50 and 51 exist to remove.

**Where the summary note goes.** Carry the `uncollected` names on the verdict
summaries the way `note` carries dropped names now
(`saffron/gates/core/revert.py:135-141`). Both the `pass` and the `fail`
verdicts carry it.

**Comments that go stale.** `_argv_safe`'s docstring
(`saffron/gates/core/revert.py:65-72`) says no name filter closes item 51.
The comment at `saffron/gates/core/revert.py:273-286` describes this repo's
gate reporting `error` on a collection error. Say in each that a runner
filling `uncollected` avoids the trap, and keep what is still true for one
that does not. Keep the `ponytail:` at `saffron/gates/core/revert.py:325-329`.

**Witnesses.** Criteria 1 to 3 are new code, so they declare a witness and
no mutant. Build each reverted run as a `GateResult` in the test, as
`tests/test_revert.py` already does. Criterion 2's witness drives an empty
and a non-empty `uncollected`, a `pass` and a `fail` status, and the two
earlier skips. Criterion 3's witness drives a `pass` and a `fail` verdict.
Criteria 4 and 5 are `preserves`: their witnesses exist and pass now, and a
mutant on existing text kills each (measured on a prototype of this change).

**Every test you add must fail with this diff's source reverted.** `revert`
runs every new test on this spec's own diff. A test that builds a
`GateResult` with the new field still collects at base. Pydantic drops the
unknown keyword there, so the test fails by assertion. Import nothing
new at module scope. Ask for no test that passes at base.

**Size.** A `bug` gets 300 changed lines. A prototype of criteria 1 to 3 and
their witnesses ran to 91 changed lines. Allow about 150 with docstrings and
the stale comments.

**Commit as each witness passes**, before the full suite runs.
