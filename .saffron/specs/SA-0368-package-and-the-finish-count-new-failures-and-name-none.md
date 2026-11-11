---
id: SA-0368
title: PACKAGE's re-verify and a stack finish count their new failures and name none of them
type: bug
priority: 2
estimated_lines: 42
estimate_measured: true
touches:
  - saffron/phases/package.py
  - saffron/events.py
  - saffron/finish.py
  - saffron/cli.py
  - tests/test_package.py
  - tests/test_events.py
  - tests/test_finish.py
  - tests/test_cli.py
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
  - saffron/cell/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/regate.py
  - saffron/spec_review.py
  - saffron/watch.py
  - saffron/view/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_session.py
  - tests/test_task.py
  - tests/test_watch.py
  - tests/fixtures/**
budget_usd: 52
max_attempts: 4
max_turns: 245
risk: standard
acceptance:
  - claim: >-
      When PACKAGE's re-verify finds new failures, it emits its count line
      `PACKAGE: N new failures against <branch>` as at base, then one
      `PhaseStart` event per new failure, labelled `PACKAGE`, whose detail
      is two spaces and `baseline.render` of that failure, in
      `comparison.new_failures` order. `package` with no `emit` prints those
      lines and writes the same events to `events.jsonl`, read back with
      `read_log`. The witness drives a failure with a file and a line and a
      failure with no file. It drives both notes: the base held still, then
      the default branch moved. Each package still ends `MERGE_FAILED`, and
      its note keeps the count and the wording it has at base.
    witness: tests/test_package.py::test_packages_re_verify_names_each_new_failure_it_counts
    wrong_versions:
      - The failures are joined into the count line's own detail, so `describe`'s 500-character clip cuts every name past the first few.
      - Each failure line carries the failure's `code` alone, without `baseline.render`'s `[gate]` and `file:line`.
      - Only the first new failure is named.
      - The failures are emitted only when the base held still, and a moved base names none.
      - The failure lines are printed with `print` and never reach `events.jsonl`.
      - The failure lines are emitted before the count line.
      - The note gains the names, so the queue line grows past its count.
  - claim: >-
      `finish.publish_finish`'s `verify` returns the new failures themselves.
      On a red suite its first line is still the escalation line it prints
      at base, `escalate: red suite, N new failures`. One line follows per new
      failure, in the order `verify` returned them. Each is exactly
      `"  " + events._clean(baseline.render(failure), events._DETAIL_BOUND)`:
      two spaces, then the rendering with every control character replaced
      by a space and clipped to 500 characters. The witness drives a failure with a file and a
      line, one with no file, and one whose message carries an escape
      sequence, a newline and a tab and runs past 2000 characters.
    witness: tests/test_finish.py::test_a_red_finish_names_each_new_failure_it_counts
    wrong_versions:
      - "`publish_finish` keeps reading a count, so the escalate line names no failure."
      - A failure's message is printed with its control characters, so an escape sequence reaches the terminal.
      - Only the escape character is replaced, so a newline in a message splits its line.
      - A failure line is not clipped, so a 2000-character message prints whole.
      - A failure line is clipped at 160 characters rather than `events._DETAIL_BOUND`.
      - The failures are joined onto the escalate line itself.
      - Only the first new failure is named.
      - The failure lines are sorted rather than kept in `verify`'s order.
  - claim: >-
      `cli._stack_finish` writes the finishing suite's comparison to a file
      named `verify.json`, in the batch tree's `finish` folder for that
      batch, beside `findings.json`. It writes one on every comparison the
      suite returns. The file holds the commit judged, the base it was
      judged against, the mirror that holds the commit, each new failure as
      its gate and its failure's fields, and each head gate result that
      carries a new failure, as `saffron.gates.contract.GateResult` dumps. A head gate result that
      fails with no new failure, and one that passes, are left out. A green
      comparison writes the file with both lists empty. `publish_finish` is
      handed a `verify` that returns the new failures themselves, and
      `_stack_finish` still prints each line it returns after `finish: `.
    witness: tests/test_cli.py::test_a_finish_writes_its_suite_comparison_beside_its_findings
    wrong_versions:
      - The file is written under `finish/<batch id>/gates`, the folder the finish exports `.saffron/` into.
      - Every head gate result is written, so a gate red only at base and a passing gate are listed.
      - The file is written only on a red suite, so a green finish leaves no file.
      - The file names the base and not the commit judged.
      - "`_stack_finish` still hands `publish_finish` a `verify` that returns a count."
      - The new failures are written as rendered strings, so a failure's line number is lost as a field.
---

## Context

Backlog item b-fe82d9, from the spec loop's run 31. A stack finish
escalated `red suite, 3 new failures` and recorded no failure anywhere.
Four more finishes did the same in runs 32, 44 and 46, and none left a gate
result under `finish/<batch id>/`. On 2026-11-10, in the spec loop's run
60, PACKAGE's re-verify did the same for `SA-0364`. It printed `2 new failures` and set `MERGE_FAILED`.
Neither the log nor `events.jsonl` named a test. The test suite, run
locally, named the clock flake #1112 fixes.

**PACKAGE counts and drops the rest.** `package` reads
`comparison.new_failures` (`saffron/phases/package.py:895`). Only
`len(new)` reaches the count line (`:896`) and the note (`:902-907`). The
state is `MERGE_FAILED` (`:915`). `_emit_package` emits a `PhaseStart` with
`label="PACKAGE"` (`:697-712`). `package` with no `emit` prints
`describe(event)` and appends the event to `EventLog(outcome.task_dir)`
(`:685-695`). `describe` renders a `PhaseStart` as `label: detail`, the
detail cleaned and clipped to `_DETAIL_BOUND` (`saffron/events.py:913-914`).
That bound is 500 (`:807`), and `_clean` replaces each control character
with a space before it clips (`:791-802`).

**The finish counts one step earlier.** `_finish_verify`'s `verify` returns
`comparison.new_failures` (`saffron/cli.py:1149-1166`). `_stack_finish`
hands `publish_finish` a lambda over its `len` (`:1309-1311`).
`publish_finish` declares `verify` as returning `int`
(`saffron/finish.py:447`). It returns the single line
`escalate: red suite, N new failures` (`:473-474`). `_stack_finish` prints
each returned line after `finish: ` (`saffron/cli.py:1320-1321`).

**The `gates` folder is the policy export, not a record.** `verify` exports
`.saffron/` at the pinned base into `gates_dir` (`saffron/cli.py:1150`).
`_stack_finish` passes `finish/<batch id>/gates` (`saffron/cli.py:1300`).
No line writes a gate result there or anywhere under `finish/<batch id>/`.
The finish's own file there is `findings.json` (`saffron/cli.py:1260`,
`saffron/finish.py:40`). The finishing commit is pushed only after a green
suite (`saffron/finish.py:553`), so a red one lives only in the pinned
mirror.

**The renderer exists.** `baseline.render` writes a `NewFailure` as
`[gate] file:line code: message` (`saffron/gates/baseline.py:25-33`). It
prints `?` for a missing line and drops `file:line ` for a failure with no
file. `finish.judge_draft` already renders `verify`'s failures with it
(`saffron/finish.py:288`). The cell's `Attempt` and `GateResult` events
carry the same strings (`saffron/events.py:249-250`, `:272-273`).

## Problem

- **A red finish leaves the operator nothing to read.** The escalate line
  counts, the `gates` folder holds no result, and the commit was never
  pushed. The delegate ran the test suite on the commit by hand.
- **PACKAGE's `MERGE_FAILED` says the same.** A task can go green in its
  cell and red at re-verify. It then names no failure in the log or in
  `events.jsonl` (§4.7). The operator cannot tell a flake from a defect
  without running the suite again.

## Out of scope

**Counts and states.** `MERGE_FAILED`, the note and the `escalate:` line
keep their meaning and their wording. This only adds the names.

**PACKAGE writes no gate result file.** Its task directory already carries
`events.jsonl`. A comparison file for PACKAGE is a later spec's question.

**A verify that raises.** A finishing suite that did not finish escalates
as at base and writes no file.

**The judges.** `_draft_faults` and the follow-up judge share
`_finish_verify` and pass it no file path. They write nothing new.

**`saffron regate`.** It prints its own line per failure
(`saffron/regate.py:185-186`). `saffron/regate.py` is forbidden.

**A cap on the count.** Every new failure is named, each on its own line.
Each line is bounded and the number of lines is not.

## Notes for the agent

**This change is new behaviour.** No criterion has a mutant on the ref,
since each witness reads lines and a file the base never writes. Expect
`witness` to report `skip` for all three.

**PACKAGE: one event per failure, after the count line.** Emit each through
`_emit_package`, so `describe` cleans and clips each name alone. Import
`render` from `saffron.gates.baseline`. Leave the note as it is. Add one
`FAMILIES` row in `saffron/events.py` for the new line, cited at
`phases/package.py:package` like its neighbours. `tests/test_events.py:1397`
pins the row count at 73. Make it 74, and name `SA-0368` in that test's
docstring the way it names the specs that moved it before.

**The finish: `publish_finish` reads `Sequence[NewFailure]`.** Clean and
clip each line with `events._clean` and `events._DETAIL_BOUND`, never a
copy of either. `finish.py` already imports a private name from
`saffron.ledger`. Change no other `escalate:` line.

**The finish: the comparison file.** Give `_finish_verify` an optional path
keyword that names where `verify` writes its comparison, and have only
`_stack_finish` pass one. Read `comparison.run` only when that path is
set. The `_draft_faults` witness's fake comparison
(`tests/test_cli.py:15576-15584`) carries `new_failures` alone. Name the
file with a module constant beside `FINDINGS_NAME`. Create its folder if it
is missing, since `write_findings` can fail before it.

**Two docstrings become false.** `_finish_verify`'s says `_stack_finish`
counts its result (`saffron/cli.py:1139-1140`). `publish_finish`'s says
each check returns one line (`saffron/finish.py:452-454`). Correct both,
and keep each within ten lines.

**Existing tests that change.** Rename none, since `census` compares test
names.

- `tests/test_finish.py`: every `verify` fake handed to `publish_finish`
  returns an `int` today, such as `lambda sha_arg, base_arg: 0` (`:1953`)
  and `-> int` fakes (`:1841`, `:2024`, `:2423`, `:2555`, `:2693`). Return
  `()` for green and real `NewFailure` tuples for red. The `types` gate reads
  `tests/**`. `test_each_escalation_leaves_the_stack_unpushed` asserts
  `len(lines) == 1` (`tests/test_finish.py:2439`). Its three red cases
  (`red`, `red-one`, `red-and-moved`) now return one line more per failure.
- `tests/test_cli.py::test_a_stack_batch_publishes_its_finish_through_the_finishing_suite`
  fakes a comparison with `new_failures = ("a", "b")`
  (`tests/test_cli.py:13342-13343`) and asserts a count of 2
  (`tests/test_cli.py:13392`). Give it real `NewFailure`s and a `SuiteRun`,
  and assert what `verify` returns.
- `tests/test_package.py::test_new_failures_after_the_rebase_are_the_tasks_failure`
  checks the count line by membership (`tests/test_package.py:1833`), so it
  holds unchanged.

**The witnesses.**

- Criterion 1: the `packageable` fixture with its `emit` dropped, as
  `test_package_with_no_emit_still_reaches_the_durable_log` does
  (`tests/test_package.py:1618-1639`). Override `reverify` with
  `_reverified(...)`. Package once, then push a commit to `main` the way
  `test_new_failures_after_the_rebase_are_the_tasks_failure` does and
  package again. Read the printed lines with `capsys`. Compare each note
  whole, with its twelve-character commit prefix matched as hex.
- Criterion 2: `_stack` and `_finishing_commit` from `tests/test_finish.py`,
  as `test_a_finishing_layers_fact_reaches_the_origin_at_exit` uses them.
  Compare each expected line whole.
- Criterion 3: `main(["--home", ..., "batch", "--stack"])` with the fakes the
  existing finish test uses (`tests/test_cli.py:13311-13338`). Use one home
  per comparison, red then green. Read the file with `json.loads` and compare
  each gate result through `saffron.gates.contract.GateResult.model_validate`.

Import every name the change adds inside a test body. A module-scope import
of one makes the reverted test a collection error, which `revert` reads as
`skip`.

**Measured on a prototype.** A diff built to this spec at base measured 167
changed tokens on `size_gate` outside `tests/**`, and 1095 with the tests.
The `bug` ceiling is 1300. Its three witnesses failed with the source
reverted. Each wrong version listed under the three criteria ran against its
witness, and each failed it. `tests/test_cli.py`, `tests/test_events.py`,
`tests/test_package.py`, `tests/test_finish.py`, `tests/test_draft.py` and
`tests/test_watch.py` passed on it.

**`error` is not `fail`.** A suite that errored raises out of `reverify`
before any line here runs. Keep it that way.

Commit after each coherent step. Uncommitted work dies with the cell.
