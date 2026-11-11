---
id: SA-0362
title: A gate result counts its new failures and names none, so a red rebuttal is rebuilt by hand
type: bug
priority: 2
estimated_lines: 35
estimate_measured: true
touches:
  - saffron/events.py
  - saffron/cell/session.py
  - tests/test_session.py
  - tests/test_events.py
  - tests/fixtures/watch-golden.txt
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
  - saffron/ledger.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/watch.py
  - saffron/view/**
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_watch.py
  - tests/test_task.py
budget_usd: 32
max_attempts: 4
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      Each `GateResult` event of a counted suite carries `failures`, the new
      failures its `new_failures` counts, each as `baseline.render` writes
      it, in `comparison.new_failures` order. That holds for the loop's
      suites (`against` set to `attempt`) and for the re-run after REBUT
      (`rebuttal`). A blocking gate with two new failures lists both in
      order. A blocking gate whose head adds a second failure to the one it
      failed with at base lists only the second. One failing identically at base, and a passing one, carry
      an empty tuple. An advisory gate, failing or passing, and a skipped gate
      carry `None`, as their count is `None`. Every baseline event carries
      `None`. Read back from `events.jsonl` with `read_log`, each list is a
      tuple, and its length equals `new_failures`.
    witness: tests/test_session.py::test_each_counted_gate_result_names_the_new_failures_it_counts
    wrong_versions:
      - Each gate lists every failure in its own result, so a failure the baseline cancels is listed.
      - Each gate lists the whole suite's new failures rather than its own.
      - The list is sorted rather than kept in the comparison's order.
      - Only the loop's suites carry a list, and the re-run after REBUT carries `None`.
      - An advisory or skipped gate carries an empty tuple rather than `None`.
      - "`read_log` hands the field back as a list, because its tuple coercion skips a `tuple[str, ...] | None` hint."
      - A baseline event carries an empty tuple.
      - A failure is written in a format of its own, without `baseline.render`'s `[gate]` and `file:line`.
      - Only a gate's first new failure is listed.
  - claim: >-
      An aborted or drifted suite carries `None` in `failures` on every one
      of its `GateResult` events, as it carries `None` in `new_failures`.
      The witness drives four cells: an aborted and a drifted suite in the
      repair loop, and an aborted and a drifted re-run after REBUT. Each
      cell first logs a counted suite whose events carry a tuple, read back
      through the same `read_log`. In the two loop cells that suite's red
      gate lists its failure.
    witness: tests/test_session.py::test_an_aborted_or_drifted_suite_names_no_failure_on_any_gate
    wrong_versions:
      - The list is built from `comparison.new_failures` whatever the suite's outcome, so an aborted or drifted suite carries an empty tuple.
      - Only an aborted suite carries `None`, and a drifted one carries an empty tuple.
  - claim: >-
      Each counted `Attempt` carries `failures`, every new failure of its
      suite rendered by `baseline.render`, in `comparison.new_failures`
      order. That holds on the GATE line for each of the decisions `green`,
      `repair`, `no-progress` and `exhausted`, and on the REBUT line.
      `describe` prints each one beneath the count line, on its own line,
      after two spaces. Each control character in it becomes a space, the
      strip `_clean` applies, and nothing clips it, past 500 characters
      included. The green line prints nothing beneath. An aborted or drifted
      suite's line carries an empty tuple and prints one line.
    witness: tests/test_session.py::test_each_attempt_line_names_its_new_failures_beneath_its_count
    wrong_versions:
      - Only the REBUT line carries the failures, and every GATE line carries none.
      - Only the GATE lines carry the failures, and the REBUT line carries none.
      - "`describe` clips each failure at `_DETAIL_BOUND`."
      - "`describe` clips each failure at 160 characters."
      - "`describe` prints a failure's control characters as they are, so a newline in one splits it."
      - The failures are joined onto one line beneath the count.
      - Only the first failure is printed.
      - The `exhausted` line prints nothing beneath its count.
      - "`describe` sorts the failures before printing them."
  - claim: >-
      The lines `_default_emit` prints name each new failure beneath its
      count, and the `Attempt` events read back from `events.jsonl` carry
      the same tuple. The witness drives both GATE lines of a repair loop,
      `repair` then `no-progress`. It also drives both REBUT re-runs, the
      first red one and the one after the repair turn on form gates.
    witness: tests/test_session.py::test_the_printed_log_names_each_new_failure_beneath_its_count
    wrong_versions:
      - "`describe`'s branch for the red REBUT line, the one naming gates, prints nothing beneath."
      - The re-run after the repair turn on form gates emits an `Attempt` with no failures.
      - "`_default_emit` prints only the first line of what `describe` returns."
  - claim: >-
      A green re-run after REBUT still writes its `Attempt` line as
      `gates: 0 new failures after the rebuttal`, naming no gate.
    witness: tests/test_session.py::test_a_green_rebuttal_re_run_logs_each_gate_result_against_the_rebuttal
    preserves: true
---

## Context

Backlog item b-66e82d, from the spec loop's run 13. `SA-0242` closed half
of it: each gate result after REBUT is now a `GateResult` event, and the red
REBUT line names each gate. The item went `partial` again on 2026-11-09,
after spec loop run 56. `SA-0353`'s re-run after REBUT named `tests` with
`new_failures: 1` and no test. Spec loop run 58 met it on `SA-0360`. That
re-run left `types` and `tests` red. `events.jsonl` carried
`{"kind": "GateResult", "gate": "types", "status": "fail", "against":
"rebuttal", "attempt": 2, "new_failures": 1}`. The log printed
`gates: 2 new failures after the rebuttal — types, tests`. The delegate rebuilt
the patch and ran `ty` and the test suite again to learn which failures.

**The identities are already in hand.** `_judge` builds a `SuiteComparison`
(`saffron/cell/session.py:2890`). It counts per gate with
`Counter(nf.gate for nf in comparison.new_failures)` (`:2920-2924`). The
loop at `:2925-2944` emits one `GateResultEvent` per gate with
`new_failures=count`. `count` stays `None` for an aborted or drifted suite,
and for a gate whose status is `skip` or `error` or that sits in
`latest.advisory_gates` (`:2926-2932`). `comparison.new_failures` holds a
`NewFailure(gate, failure)` for each (`saffron/gates/suite.py:125`).
`render` (`saffron/gates/baseline.py:25-33`) writes one as
`[gate] file:line code: message`. It prints `?` for a missing line, and
drops the `file:line ` part for a failure with no file.

**The baseline's events count nothing.** The baseline loop emits one
`GateResultEvent` per gate with no `attempt` and no count
(`saffron/cell/session.py:2343-2355`).

**Every counted line goes through one builder.** `attempt_event`
(`saffron/cell/session.py:776-827`) builds the `Attempt` for a suite
comparison. Four calls reach it. `repair_loop` makes two, for an aborted or
drifted suite at `:861-865` and with a decision at `:871-879`. `_rebut_gates`
makes two, for the re-run after REBUT at `:3600-3607` and for the re-run
after the repair turn on form gates at `:3623-3630`. It sets
`new_failures=len(comparison.new_failures)` (`:824`). It names gates only when
`decision` is `None` (`:812-816`).

**`describe` prints the line.** Its `Attempt` branch is
`saffron/events.py:896-918`. A GATE line reads `gates: attempt N, K new
failures -> decision`. A REBUT line reads `gates: K new failures after the
rebuttal`, then ` — ` and the gates when there are any. Its
`GateResult` branch prints `gates: {gate}={status}` (`:920-923`). Two
printers call it. `_default_emit` prints `describe(event)` when the caller
passes no `emit` (`saffron/cell/session.py:118-129`). `run_task`'s default
`emit` does the same for `saffron batch` (`saffron/task.py:802-805`). So
`describe` is the site the batch's log and `saffron watch` share.

**An optional tuple reads back as a list.** `_parse_line` coerces a JSON list to a tuple only when
`typing.get_origin(hint) is tuple` (`saffron/events.py:652-654`). Every tuple
field in the module today has a bare `tuple[...]` hint. `_shape_ok` accepts a
list under a `tuple[...] | None` hint through its union arm (`:590-591`). So
such a field comes back a list, and `("a",) == ["a"]` is false.

**`describe` already has a strip that clips.** `_clean` replaces every
control character with a space through `_CONTROL_TRANSLATION`, then clips to
its `limit` (`saffron/events.py:768-782`). A failure's message is gate output
from inside the cell, so the strip applies here (item 63).

## Problem

- **A red re-run names no failure.** REBUT does not re-enter the repair
  loop (§5.6), so the red re-run ends the task. The
  failures it found are in the ledger's gate rows and nowhere a person reads.
- **The loop's red lines name none either.** `gates: attempt 1, 2 new
  failures -> repair` never says what the repair turn was sent to fix (the
  item's 2026-09-27 record).
- **`events.jsonl` is the log for a person (§4.7).** Its `GateResult` events
  carry the count the identities were folded into.

## Out of scope

**The ledger and the record.** `ledger.record_gate_result` already stores
each gate row (`saffron/cell/session.py:2911-2917`). `saffron/ledger.py` and
`saffron/record/**` are forbidden.

**A cap on the list.** No count limit and no truncation. A cap is a later
spec's question.

**`describe`'s `GateResult` branch.** It keeps printing `gates:
{gate}={status}` alone. The `Attempt` line beneath it prints the failures,
so printing them under each gate too would print each twice.

**The `Attempt` lines that count nothing.** An IMPLEMENT line, and an aborted
or drifted suite's line, print as they do at base.

**Redaction.** `EventLog.append` redacts only `Agent` events (§4.7). The new
`failures` text is a gate's message, as `PhaseStart.detail` and
`Terminal.detail` carry cell text unredacted today. Redacting every event
is a separate question.

**The cell-watch hook.** `.claude/skills/cell-watch/hooks/progress.ts` reads
`new_failures` from the log. It ignores a key it does not know, and
`.claude/**` is forbidden.

## Notes for the agent

**This change is new behaviour.** Criteria 1 to 4 declare a witness and no
mutant, so expect `witness` to report `skip` for them. Criterion 5 is
`preserves`, and its test exists at base.

**Both fields carry `baseline.render` strings.** Import `render` from
`saffron.gates.baseline`, where `NewFailure` already comes from
(`saffron/cell/session.py:50`). Name both fields `failures`. `Attempt.failures`
is `tuple[str, ...]` with a default of `()`, so an older log still parses.
`GateResult.failures` is `tuple[str, ...] | None` with a default of `None`.
Set it only where `_judge` sets `count`, from the same comparison, filtered to
the gate. Set `Attempt.failures` in `attempt_event`'s counted return, for
every decision.

**Teach `_parse_line` the optional tuple.** Coerce a list to a tuple when the
hint is `tuple[...]`, bare or inside `X | None`. `_shape_ok`'s union arm
already shows how to read a union's arms.

**Print beneath the line.** Each failure goes on its own line after the
count line, two spaces in. It passes through the `_CONTROL_TRANSLATION` strip
with no clip. `_clean` with a limit as long as the string does that.
The count line itself does not change. Add no `FAMILIES` row:
`tests/test_events.py:1397` pins 73, and a line beneath belongs to its count
line's family.

**Existing tests that change.** Three tests read lines this change extends,
so edit each in place. Rename none, since `census` compares test names.

- `tests/fixtures/watch-golden.txt:62` and `:70` are the golden cell's two red
  GATE lines. Beneath each goes the failing `lint` gate's one new failure,
  `  [lint] a.py:? E501: too long`.
  `tests/test_events.py::test_watch_output_matches_the_golden_fixture` then
  matches it.
- `tests/test_events.py::test_the_join_covers_every_captured_line_a_kind_renders`
  fails on that new fixture line. Accept it inside the test body, as the test
  already accepts `per_gate` and `conventions_line`. Build it there with
  `describe`. A new `_JOINED` or `_CASES` row would construct the new field at
  module scope, and `revert` reads the collection error as `skip`.
- `tests/test_session.py::test_a_red_rebuttal_line_names_each_gate_that_failed_anew`
  compares two REBUT lines whole, at `tests/test_session.py:7466-7468` and
  `tests/test_session.py:7503`. Extend each expected
  string with its failures beneath. Keep the comparison whole.

**Drive the whole-cell witnesses with `use_default_emit=True`.** That path
writes a real `events.jsonl` under `tmp_path / "out" / "SY-1"`, which
`read_log` reads back. It prints through the real `print`, so read the
printed lines with `capsys`, never `cell.watched`, which stays empty there.
`_rebuttal_log` and `_rebut_repair_drive` show the setup. Prefix every new
helper with `_`. Import `read_log` inside the test body, as `_rebuttal_log`
does. Construct no new field at module scope: the reverted test would be a
collection error, which `revert` reads as `skip`.

**Criterion 1's suites.** Declare an advisory gate with
`policy="gates:\n  dead: { blocking: false }\n"` and `gates=("dead",)`, the
way `test_a_declared_gate_with_blocking_false_does_not_repair` declares `lint`
(`tests/test_session.py:4094-4121`). Give it a failure at head. `size` is
advisory at `standard` too. Keep each gate's `tool` the same on every suite, or
the suites drift. Give the two-failure gate files whose sorted order differs
from their order in the result. Give one failure a line number, so `render`'s
`file:line` shows.

**Criterion 2's cells.** `test_an_aborted_or_drifted_suite_counts_nothing_on_any_gate`
(`tests/test_session.py:7985`) and
`test_an_errored_or_drifted_rebuttal_re_run_logs_each_gate_with_no_count`
(`:7832`) build the four suite shapes. Put a failing gate in each aborted or
drifted suite. In a loop cell, let attempt 1 count a red gate and attempt 2
abort or drift, with one repair turn between.

**Criterion 3 drives the builder directly.** `repair_loop` with a scripted
`judge` and `emit=list.append` reaches every decision, as `_loop` does
(`tests/test_session.py:980-991`). `max_attempts=2` with two different
failures reaches `exhausted`. Call `session.attempt_event` with
`phase="REBUT"` for the REBUT line. A message carrying an escape sequence, a
newline and over 500 characters drives the strip and the missing clip.

**Criterion 4's REBUT half.** `_rebut_repair_drive` with
`_through_rebut_repair` and the suites `_GREEN_FORM_SUITE`,
`_GREEN_FORM_SUITE`, `_red_form_suite("format", "lint")` and
`_red_form_suite("format")` reaches both REBUT re-runs, red, and ends
`EXHAUSTED`. The witness reads `_default_emit`'s lines alone. `run_task`'s
`emit` prints the same `describe(event)`, and `saffron/task.py` is forbidden.

**Measured on a prototype.** A diff built to this spec at base measured 138
changed tokens on `size_gate`, against the `bug` ceiling of 1300. Another 1213
under `tests/**` were not counted. Its four new witnesses failed with
`saffron/events.py` and `saffron/cell/session.py` reverted. Every wrong version
listed under criteria 1 to 4 ran against its witness, and each failed it.
`tests/test_session.py`, `tests/test_events.py`, `tests/test_watch.py` and
`tests/test_task.py` passed on it.

**`error` is not `fail`.** An errored gate's count is `None`, so its list is
too. Carry each gate's status through unchanged.

Commit after each coherent step. Uncommitted work dies with the cell.
