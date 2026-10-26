---
id: SA-0322
title: A host-filed survivor's blocker says only its witness was asked, so a witness that never reaches the edited file reads as an unguarded claim
type: bug
priority: 2
estimated_lines: 73
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - tests/test_session.py
  - tests/test_rebut.py
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
  - saffron/probe.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/record/**
  - saffron/report/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/task.py
  - saffron/ledger.py
  - saffron/qualify.py
  - saffron/cli.py
  - saffron/batch.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 25
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      When a criterion's witness survives an edit, the host applies that edit
      again and asks the whole `tests` gate once more, in the same Gate-only
      cell. A new failure there, against the head's own `tests` result, is a
      kill. A killed survivor stays a `blocker`, keeps no `filed_severity`,
      and still reaches REBUT. Its claim keeps today's text up to the quoted
      claim, so it opens with the host's mark, the witness and ` stayed green
      with `. It then ends ". Under the edit the whole `tests` gate failed",
      every killing node id joined by ", ", then ", and the criterion's
      witness did not fail." It draws no other conclusion. The witness drives
      both edit forms. Two tests kill the criterion's own edit, and a third
      kills the wrong version.
    witness: tests/test_session.py::test_a_survivor_the_whole_suite_kills_stays_a_blocker_naming_the_killing_tests
    wrong_versions:
      - The second ask names the criterion's own witness again rather than the whole suite.
      - The second ask enters a fresh Gate-only cell of its own rather than the cell the witness was asked in.
      - Only the criterion's own edit is asked again, so a wrong version's blocker keeps the old claim.
      - The claim names only the first killing test.
      - The claim says the suite killed the edit and names no test.
      - A kill leaves the old claim, which says only the witness was asked.
      - A kill files the survivor as a `concern`, so REBUT never sees it.
      - A kill-path claim with a fresh opening, so the host's mark is no longer followed by the witness and ` stayed green with `.
      - The kill claim adds that the witness never reaches the edited file.
      - The kill claim adds that the claim is guarded.
  - claim: >-
      A survivor the whole `tests` gate does not kill stays a `blocker`, and
      still reaches REBUT. Its claim keeps today's text up to the quoted
      claim, then ends ", and the whole `tests` gate stayed green under the
      edit too." It no longer says only the witness was asked. It still
      starts with the host's mark, the witness and ` stayed green with `, so
      REBUT's `preserves` guard still reads it. The witness drives both edit
      forms. The criterion's own edit meets a suite that passes. The wrong
      version meets a suite whose only failure is a test the head already
      failed, which is no kill and is not named.
    witness: tests/test_session.py::test_a_survivor_the_whole_suite_also_misses_says_the_suite_stayed_green
    wrong_versions:
      - Any failure in the second ask counts as a kill, including a test the head already failed, so the old test is named as a killer.
      - A suite with no kill leaves the old claim, which says only the witness was asked.
      - The new claim reorders its opening, so the host's mark is no longer followed by the witness and ` stayed green with `.
  - claim: >-
      A second ask that cannot answer keeps today's blocker with today's
      claim, word for word. The witness drives five of them. The whole `tests`
      gate answers `error` for the first and `skip` for the second, and
      neither is read as green. For the third the mutator declines to apply
      the edit again. For the fourth the cell stops, as a `CellRuntimeError`
      out of the gate call. Each survivor still reaches REBUT. After the stop,
      the next entry is `unproven` and its edit is never applied. In a second
      cell the head carries no `tests` result, so the whole suite is never
      asked.
    witness: tests/test_session.py::test_a_survivor_whose_whole_suite_cannot_answer_keeps_todays_blocker
    wrong_versions:
      - A whole `tests` gate that answers `error` or `skip` is read as one that stayed green.
      - A mutator that declines the second application is read as a suite that stayed green.
      - A cell that stops during the second ask drops the survivor, so no blocker reaches REBUT.
      - After the cell stops, the loop goes on and applies the next entry's edit.
      - A head with no `tests` result is read as a green baseline, so the whole suite is asked against nothing.
  - claim: >-
      An edit its witness kills, and one under which the witness ask answers
      `error`, gets no second ask and files nothing.
    witness: tests/test_session.py::test_a_killed_or_errored_criterion_probe_files_nothing_and_stops_nothing
    preserves: true
    wrong_versions:
      - The whole suite is asked for every entry whose edit applied, killed and errored entries included, and any raise out of it is swallowed.
  - claim: >-
      An entry nothing could answer gets no second ask and files nothing. The
      witness drives five such entries. One names no edit, one edits a declared
      test path, and one edits outside the tree. The mutator refuses one, and
      the `tests` gate never collected the witness of the last.
    witness: tests/test_session.py::test_a_criterion_probe_nothing_could_answer_is_unproven_and_files_nothing
    preserves: true
    wrong_versions:
      - The whole suite is asked for every entry that names an edit, whatever its witness answered, and any raise out of it is swallowed.
  - claim: >-
      REBUT's blocker line for a survived probe says no test able to decide
      the edit failed. It no longer says so for a host-filed survivor whose
      claim names the tests the whole `tests` gate failed. That line says the
      criterion's witness did not fail, and still shows the edit. The witness
      drives three survivors. The host-filed one with a kill loses the
      phrase. A lens's survivor keeps it, and so does a lens's survivor whose
      claim quotes the kill sentence mid-claim.
    witness: tests/test_rebut.py::test_a_survivor_whose_suite_failed_tests_is_not_shown_as_undecided
    wrong_versions:
      - The phrase is dropped for every survived blocker.
      - The phrase stays on a host-filed survivor whose claim names failing tests.
      - The kill sentence is matched anywhere in a claim, so a lens's survivor quoting it loses the phrase.
---

## Context

Backlog item **b-b9365d**, which cites `DESIGN.md` §5.5. The change also
touches what §5.4.1 says of a survivor. Line numbers below were read at
`61326e45`.

**Measured on `SA-0313`**, in the spec loop's run 48. The record is
`~/.saffron/batches/v0/SA-0313/findings.json`. Its first host-filed
`adequacy` finding is a `blocker` at `saffron/cli.py:2884`, anchored, with
`probe_verdict: survived`. Its witness is
`tests/test_reconcile.py::test_a_not_implemented_task_with_an_adopted_pull_request_moves_only_on_a_merge`.
The criterion's own edit drops the re-gate's exit code and its new-failure
count from the check `adopt` makes before it moves a task to
`READY_FOR_REVIEW`. That line number is the record's, at `SA-0313`'s head.
The item records that the implementer argued it. The delegate then asked
the same edit of `tests/test_cli.py -k adopt`, and three assertions
failed. So the suite noticed the edit, and the one witness that was asked
could not. The claim said nothing of that, so REBUT argued over a blocker
whose evidence was half missing.

**Why the blocker stays.** The operator measured that edit at `a0ec477e`.
`ruff format --check` fails on it, because ruff joins the `if (` it
leaves. This repo's suite holds its `format` and `lint` gates as tests
(`tests/test_saffron_gates.py:237-257`). So a suite kill can be a style
failure, and core cannot tell a style test from a behaviour test (§2.1).
A kill therefore informs the blocker and never downgrades it.

**How a survivor is filed today.** `_apply_criterion_probes` applies each
criterion probe's edit, then each wrong version's, in one Gate-only cell
(`saffron/cell/session.py:1942-2097`). For each it calls `witness_gate`
over that one criterion (`saffron/cell/session.py:2062-2071`). That gate
asks the `tests` gate over the witness alone
(`saffron/gates/core/witness.py:191`). On `survived` the host reads the
file at head, builds `review.survivor_finding`, anchors it and appends it
to the `adequacy` review (`saffron/cell/session.py:2078-2097`). The
finding is always `severity="blocker"` (`saffron/phases/review.py:763`).
Both claim forms end "and only that witness ran under the edit"
(`saffron/phases/review.py:750-759`). REBUT renders each blocker's claim
in the line its turns read (`saffron/phases/rebut.py:173`). For a survived
probe that line adds that no test able to decide the edit failed
(`saffron/phases/rebut.py:174-178`). A claim naming failing tests would
contradict it.

**What the head's suite already says.** `collected` is read from the
`tests` result of the lens table's own Gate-only cell
(`saffron/cell/session.py:2007-2009`). That result is the whole suite at
the reviewed head, unsubtracted (`SuiteRun.results`,
`saffron/gates/suite.py:100-105`).

**A whole-suite question already has an answer.** `probe.check_probe`
applies one edit through an injected `mutate` (`saffron/probe.py:170-290`).
It asks the whole suite with an empty subset, then subtracts a baseline
(`saffron/probe.py:213`, `:243`). It reads a run whose collected names
shrank as `unproven` (`saffron/probe.py:230-241`). A gate that answers
other than `pass` or `fail` is `unproven` as well (`saffron/probe.py:215-222`).
`probe_findings` already calls it in a Gate-only cell
(`saffron/cell/session.py:1877-1884`).

## Problem

A survivor's blocker says nothing guards the claim, and it says only the
witness was asked. When the whole suite catches the same edit, the claim
names the tests that failed. REBUT then reads which tests saw the edit
when the witness did not. When the suite misses it too, the claim says
that instead. The operator settled the rule.

1. **The second ask.** Apply a survivor's edit again and ask the whole
   `tests` gate once. Use the Gate-only cell its witness was asked in. Do
   it for a survivor alone, never for any other outcome.
2. **The verdict.** Judge that answer against the head's `tests` result
   from `gate_comparison`. A new failure among the head's collected tests
   is a kill.
3. **The claim.** The wording is settled here, not left to you. Keep
   today's text up to and including the quoted claim, written `<head>`
   below. A kill's claim lists every killing node id, joined by `, `. A
   suite with no new failure gets the second form.

   ```
   <head>. Under the edit the whole `tests` gate failed t.py::b, t.py::c, and the criterion's witness did not fail.
   <head>, and the whole `tests` gate stayed green under the edit too.
   ```

   A kill can be a style test failing, so the claim says nothing about
   reach or guarding. Either way the finding stays a `blocker`, and
   `filed_severity` stays unset.
4. **A non-answer keeps today's text.** Check for a head with no `tests`
   result before the second ask, and then make no ask. A run that answers
   `error` or `skip` is no evidence, and `error` is never `fail`. A
   declined edit and a shrunken collection are no evidence either. A
   failure the head collected no name for is none. A cell that
   stops keeps the blocker, then ends the loop as today's `stopped` path
   does.
5. **The record.** The entry's own `outcome` stays `survived`. It reports
   the witness, and the claim reports the suite.
6. **REBUT's line.** `_blocker_line` keeps its phrase for every survived
   probe but one. A host-filed claim holding the kill sentence instead says
   the criterion's witness did not fail. Recognise it by `HOST_FILED` at the
   start and the kill sentence in the claim, so a lens cannot forge it.
7. **The prose that turns false.** `survivor_finding`'s docstring names no
   second answer (`saffron/phases/review.py:739-746`). `_blocker_line`'s
   docstring says a survived verdict is the tests not noticing the edit
   (`saffron/phases/rebut.py:168-172`).
   `_apply_criterion_probes`'s docstring names no second ask
   (`saffron/cell/session.py:1959-1968`).
8. **The existing tests.** Four tests script one `tests` answer per
   survivor and run out under the second ask. Criterion 4's witness gains
   two assertions. The notes name each change.

## Out of scope

- **A downgrade.** A kill can be a style test failing (above). Core cannot
  tell, so the severity never moves.
- **Which tests reach a file.** Core does not know that. It is language
  knowledge, and §2.1 keeps it in the repo's `.saffron/`. The host asks the
  declared `tests` gate instead.
- **A field in `criterion-probes.json` or `wrong-versions.json`** for the
  second ask. The claim carries it. A record field would reach every
  reader of those files.
- **`Finding.probe`'s docstring.** It says the edit "would keep the
  tests green" (`saffron/agents/findings.py:103-104`). A killed survivor's
  edit does not. That file is forbidden, so the sentence stays stale.
- **A lens's own vacuity probe.** `probe_findings` keeps its counted set
  (`saffron/probe.py:302-316`).
- **The design record and the vocabulary.** The operator edited both by
  hand in this spec's pull request. `DESIGN.md` §5.4.1 and `CONTEXT.md`'s
  criterion probe entry each gained two sentences (`DESIGN.md:1125`,
  `CONTEXT.md:521`).

## Notes for the agent

**New code, so no mutants.** The second ask and the new claim tails do
not exist at base. Their spelling is yours. So each criterion declares a
witness and wrong versions, and no mutant. The `witness` gate reports
`skip` for this spec, and that is expected.

**A lead for the second ask.** `probe.check_probe` asks whether anything
in the whole suite notices one edit. Pass it the edit, the head's `tests`
result as `baseline`, the loop's own `_mutate` and `_run_tests`, and the
same `test_paths`. Pass `counted` as the head result's collected names.
Do not pass `probe.added_tests(...)`. `SA-0313`'s killing tests predate its
diff, so a set of added tests reads that kill as no kill. Its `killed`
carries the killing names in `failures`. Its `survived` is green only when
`uncounted` is empty. Read `unproven` as a non-answer. A
`CellRuntimeError` out of it is a stopped cell. `_run_tests` and `_mutate`
already record that in `stopped` (`saffron/cell/session.py:2031-2059`).
`saffron/probe.py` is forbidden, since its contract does not change.

**Five non-answers are driven, and three are not.** Criterion 3 drives an
`error`, a `skip`, a declined edit and a stopped cell. It also drives a
head with no `tests` result. `check_probe` cannot take a missing baseline
(`saffron/probe.py:191`), so check for one first. Three more take the
same path with no witness. They are a shrunken collection, a failure
outside the head's collected names, and a head that collected no names.

**Keep the blocker's claim on a stop.** Build and anchor the finding
before the second ask, as today. A stopped cell can no longer serve
`read_at_head`, and its error path files nothing
(`saffron/cell/session.py:2093-2096`). So a second ask that raises must
still append the finding it already holds. Change the anchored finding's
claim alone, since anchoring read the line already.

**Keep the opening of the claim.** `_guarded_blockers` keys a `preserves`
criterion's blocker on `HOST_FILED`, the witness, then ` stayed green with `
(`saffron/phases/rebut.py:455-473`). Change only what follows the claim.
`survivor_finding` with no second answer keeps today's text, so
`tests/test_review.py`'s tests of it stay green
(`tests/test_review.py:2088-2256`).

**What each survivor costs.** Each survivor adds one whole `tests` run,
which took 6.5 to 7 minutes for this repo's suite on the host.

**One stub for the three new witnesses.** Write a helper beside them that
replaces `saffron.gates.runner.run_gate` for the `saffron-gate-` container
alone. It records each call as `(gate, subset)` and answers from a script,
raising an answer that is an exception. Past the script it answers `pass`,
collecting every name the head collected. It also installs a
`worktree.source_mutated` that applies cleanly into `cell.mutated`, as
`_stub_probe_gates` does (`tests/test_session.py:5739-5746`).
`_stub_the_runtime`'s own yields a refusal, which leaves every edit
`unproven` (`tests/test_session.py:1216-1230`). Give every `Failure` a
full node id as its `code`, such as `t.py::b`, as the `tests` gate
writes them (`.saffron/gates/tests.py:150`). The existing tests use
`code="a"` (`tests/test_session.py:12083`). Copying that reads a kill as
`unproven`. `_stub_probe_gates` raises
`StopIteration` past its script (`tests/test_session.py:5732`). A wrong
build then fails on the stub rather than on an assertion, so do not use it
for the script.

**Criterion 1's witness.** Write it in `tests/test_session.py` after
`test_a_survivor_outside_the_diff_still_reaches_rebut`
(`tests/test_session.py:12309`), and take that test's shape. Declare one
criterion with one wrong version, and drive the lenses with
`_probe_turns`. Give the head's `tests` result four collected names.
Script the witness passing, then a whole suite failing on two other tests.
Script the wrong version the same way with the third test. Each
whole-suite answer must collect all four names. A shorter list reads as a
shrunken collection, which is `unproven`. Drive the two rebuttal turns
with `_rebuttable(..., rebut_commits=0)` and `_CLAIMED_FIX`. Assert the
first four calls, and that `cell.mutated` holds each edit twice. Spy on
`critic_cell` as
`test_criterion_probes_and_wrong_versions_share_one_gate_only_cell_and_the_spend`
does (`tests/test_session.py:12677`), and assert exactly three entries.
Assert the state is `REBUTTAL_UNJUDGED`. Assert both blockers'
severity, `filed_severity` and probe. Assert each claim starts with the
host's mark, the witness and ` stayed green with `. Then assert both
claims equal the settled text exactly.

**Criterion 2's witness.** The same shape, after criterion 1's. Give the
head's `tests` result one failure. The own edit meets a whole suite that
passes. The wrong version meets one that fails on that same old test
alone. Its `Failure` message must equal the head's, since
`subtract_baseline` compares on the normalised message
(`saffron/gates/baseline.py:44-64`). Assert both claims in
`rebuttal.json` equal the settled text exactly, in order.

**Criterion 3's witness.** Five criteria, each with its own edit. Stub
`worktree.source_mutated` to decline the third criterion's edit on its
second application. Script, in order:
1. The first witness passes, then a whole suite answers `error`.
2. The second witness passes, then a whole suite answers `skip`.
3. The third witness passes.
4. The fourth witness passes, then a `CellRuntimeError` is raised.

Assert the calls and the applied edits in order. Assert four `survived`
outcomes and one `unproven`. Assert the four blocker claims in
`rebuttal.json` equal today's text exactly. Then drive a second cell under
`tmp_path / "no-head"`, whose lens table holds no result at all. Call
`_stub_the_runtime` again, and patch `read_at_head` after it, since it
patches that too. One criterion's witness survives. Assert the only call
is its witness, and that its blocker's claim is today's text.

**Criterion 6's witness.** Write it in `tests/test_rebut.py` after
`test_a_blocker_whose_probe_survived_names_the_probe_to_the_implementer`
(`tests/test_rebut.py:131`). Build the host-filed survivor with
`review.survivor_finding` and a `killed` `probe.ProbeResult`, so the
claim is the one the host writes. Build a lens's survivor with `_blocker`,
and a copy whose claim quotes the kill sentence after other text. Assert
on `blocker_lines`' three lines.

**Item 8, the existing tests.** Each survivor test needs one more `tests`
answer per survivor. It is a whole suite that passes and collects what the
head collected. Keep each name, since `census` reads a renamed test as a
removed one.

- `test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker`
  (`tests/test_session.py:11846`). Its subsets assertion
  (`tests/test_session.py:11911`) gains a `[]` after each witness.
- `test_a_preserves_criterion_probe_argued_out_of_the_diff_is_kept_confirmed`
  (`tests/test_session.py:11966`) needs a second answer.
- `test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker`
  (`tests/test_session.py:12190`). Its subsets assertion
  (`tests/test_session.py:12259`) gains a `[]`. Its pinned claim
  (`tests/test_session.py:12291-12296`) takes your stayed-green sentence.
- `test_a_survivor_outside_the_diff_still_reaches_rebut`
  (`tests/test_session.py:12309`). Its subsets assertion
  (`tests/test_session.py:12396`) gains a `[]` after each witness.

Criterion 4's witness,
`test_a_killed_or_errored_criterion_probe_files_nothing_and_stops_nothing`
(`tests/test_session.py:12057`), asserts no call today. Pass `subsets=` to
its `_stub_probe_gates` call. After its state assertion, assert the
subsets are each witness alone, in order, and that `cell.mutated` holds
its three edits once each. Both hold at base, so it stays a `preserves`
witness. Keep its name.

**Measured on a prototype over `61326e45`.** The source came to 289
changed tokens by the `size` gate's counter. Like the gate, that count
leaves out `tests/**`. That is 22% of the `bug` ceiling of 1300. The
tests carried 1498 more. The whole suite passed. Each new witness failed
with the source reverted. Each of the 23 wrong versions above, applied as an
edit, failed its criterion's witness on an assertion. The four new witnesses
take under a second together.

Commit after each witness passes. Uncommitted work dies with the cell.
