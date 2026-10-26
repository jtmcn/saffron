---
id: SA-0322
title: A host-filed survivor is a blocker though the whole suite kills its edit, so a witness that never reaches the file files a false blocker
type: bug
priority: 2
estimated_lines: 114
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
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
  - hooks/**
  - saffron/probe.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/record/**
  - saffron/report/**
  - saffron/phases/rebut.py
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
      cell. When that suite answers `fail`, every other declared gate is asked
      under the same edit too. A kill is a new failure against the head's own
      `tests` result. It is confirmed when no other gate gains a failure over
      the head's own result for it, and when the killing tests pass, asked
      alone after the edit is restored. A confirmed kill files the survivor as
      a `concern` with `filed_severity` `blocker`. Its claim says the whole
      `tests` gate killed the edit, names every killing test, and keeps the
      host's mark and the witness at its start. REBUT does not run on it. The
      witness drives both edit forms. Two tests kill the criterion's own edit,
      and a third kills the wrong version.
    witness: tests/test_session.py::test_a_survivor_the_whole_suite_kills_is_filed_as_a_concern_not_a_blocker
    wrong_versions:
      - The second run asks the criterion's own witness again rather than the whole suite, so nothing new is learned and the survivor stays a blocker.
      - The concern keeps the old claim, which says only the witness ran under the edit and names no failing test.
      - The second run enters a fresh Gate-only cell of its own rather than the cell the witness ran in.
      - Only the criterion's own edit is run again, so a wrong version's survivor stays a blocker whatever the suite says.
      - The concern's claim names only the first killing test.
      - The concern's claim says the suite killed the edit and names no test that failed.
      - The killing tests are never asked again without the edit, so a kill that recurs on the clean tree still files a concern.
  - claim: >-
      A survivor the whole `tests` gate does not kill stays a `blocker`, and
      still reaches REBUT. Its claim says the whole `tests` gate ran under the
      edit and no longer says only the witness ran. It still starts with the
      host's mark, the witness and ` stayed green with `, so REBUT's
      `preserves` guard still reads it. The witness drives both edit forms. The
      criterion's own edit meets a suite that passes. The wrong version meets
      a suite whose only failure is a test the head already failed, which is
      no kill.
    witness: tests/test_session.py::test_a_survivor_the_whole_suite_also_misses_stays_a_blocker_naming_the_suite
    wrong_versions:
      - Any failure in the second run counts as a kill, including a test the head already failed, so the wrong version's survivor becomes a concern.
      - The blocker keeps the old claim, which says only the witness ran under the edit.
      - The new claim reorders its opening, so the host's mark is no longer followed by the witness and ` stayed green with `.
  - claim: >-
      A second run that cannot answer keeps today's blocker with today's
      claim, word for word, and no `filed_severity`. The witness drives five
      such runs. The first is a whole `tests` gate that answers `error`. In
      the second the mutator declines to apply the edit again. In the third
      the suite kills the edit and the `format` gate, which passed at head,
      fails under it. In the fourth the suite kills the edit and the killing
      test still fails when asked alone without it. In the fifth the cell
      stops, as a `CellRuntimeError` out of the gate call. Each survivor still
      reaches REBUT as a blocker. After the stop, the next entry is `unproven`
      and its edit is never applied.
    witness: tests/test_session.py::test_a_survivor_whose_whole_suite_cannot_answer_keeps_todays_blocker
    wrong_versions:
      - A whole `tests` gate that answers `error` is read as a kill, so the survivor becomes a concern.
      - A cell that stops during the second run drops the survivor, so no blocker reaches REBUT.
      - A mutator that declines the second application is read as a suite that passed, so the claim says the whole suite ran.
      - After the cell stops, the loop goes on and applies the next entry's edit.
      - The other declared gates are never asked, so a kill that only broke formatting files a concern.
      - The other declared gates are asked and their answers ignored, so a kill beside a new `format` failure files a concern.
      - Only a killing test that answers `error` without the edit is a non-answer, so one that still fails is read as a confirmed kill.
  - claim: >-
      An edit its witness kills, and one under which the witness run answers
      `error`, gets no second run and files nothing.
    witness: tests/test_session.py::test_a_killed_or_errored_criterion_probe_files_nothing_and_stops_nothing
    preserves: true
    wrong_versions:
      - The whole suite runs for every entry whose edit applied, killed and errored entries included, and any raise out of it is swallowed.
  - claim: >-
      An entry nothing could answer gets no second run and files nothing. The
      witness drives five such entries. One names no edit, one edits a declared
      test path, and one edits outside the tree. The mutator refuses one, and
      the `tests` gate never collected the witness of the last.
    witness: tests/test_session.py::test_a_criterion_probe_nothing_could_answer_is_unproven_and_files_nothing
    preserves: true
    wrong_versions:
      - The whole suite runs for every entry that names an edit, whatever its witness answered, and any raise out of it is swallowed.
---

## Context

Backlog item **b-b9365d**, which cites `DESIGN.md` §5.5. The change also
touches what §5.4.1 says of a survivor. Line numbers below were read at
`91a0f216`.

**Measured on `SA-0313`**, in the spec loop's run 48. The record is
`~/.saffron/batches/v0/SA-0313/findings.json`. Its first host-filed
`adequacy` finding is a `blocker` at `saffron/cli.py:2884`, anchored, with
`probe_verdict: survived`. Its witness is
`tests/test_reconcile.py::test_a_not_implemented_task_with_an_adopted_pull_request_moves_only_on_a_merge`.
The criterion's own edit drops the re-gate's exit code and its new-failure
count from the check `adopt` makes before it moves a task to
`READY_FOR_REVIEW`. That line number is the record's, at `SA-0313`'s head.
The item records that the implementer argued it. The delegate then ran
the same edit under `tests/test_cli.py -k adopt`, and three assertions
failed. So the suite noticed the edit, and the one witness that was asked
could not.

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
(`saffron/phases/review.py:750-759`).

**Where a blocker and a concern go.** `anchored_blockers` keeps a host-filed
finding only when its severity is `blocker` (`saffron/phases/review.py:787-803`).
`review_state` routes to REBUT on that list alone
(`saffron/phases/review.py:872-890`). So a host-filed `concern` never
reaches REBUT. `anchored_concerns` counts it when it anchors
(`saffron/phases/review.py:863-870`). The pull request's findings table
renders every finding with its severity, anchored or not
(`saffron/report/pr_body.py:387-414`). It adds "(filed `blocker`)" when
`filed_severity` differs from `severity` (`saffron/report/pr_body.py:398-403`).
After REBUT, `_rebut_gates` asks each surviving blocker's probe again and
reads blockers alone (`saffron/cell/session.py:3461-3465`).

**What the head's suite already says.** `collected` is read from the
`tests` result of the lens table's own Gate-only cell
(`saffron/cell/session.py:2007-2009`). That cell's suite runs every
declared gate (`saffron/gates/suite.py:170-176`), and its results are kept
unsubtracted (`SuiteRun.results`, `saffron/gates/suite.py:100-105`). So
the head's own result for each declared gate is already in hand.

**Why a suite kill alone is not enough.** This repo's suite runs its
`format` and `lint` gates over the whole tree as tests
(`tests/test_saffron_gates.py:237-257`). A wrong version that only reflows
a line fails one of those tests. Read alone, that is a kill, and it would
turn a real blocker into a concern. Item b-19b255 measured this shape on
`SA-0127`, and §5.5.1 keeps it out of a vacuity probe's kill
(`DESIGN.md:1249`). Core cannot tell a lint test from any other test
(§2.1). It can ask the declared gates themselves.

**A whole-suite question already has an answer.** `probe.check_probe`
applies one edit through an injected `mutate` (`saffron/probe.py:170-290`).
It asks the whole suite through the `run_tests` it is handed, with an
empty subset, then subtracts a baseline (`saffron/probe.py:213`, `:243`).
It reads a run whose collected names shrank as `unproven`
(`saffron/probe.py:230-241`). A gate that answers other than `pass` or
`fail` is `unproven` as well. `probe_findings` already calls it in a
Gate-only cell (`saffron/cell/session.py:1877-1884`).

## Problem

A survivor's blocker says nothing guards the claim. When the whole suite
kills the same edit, something does guard it. The spec named the wrong
witness, or its wrong version broke a different property than its claim
names. That mismatch is worth a person's eye, and it is no blocker. The
operator settled the rule.

1. **The second run.** Apply a survivor's edit again and ask the whole
   `tests` gate. Use the Gate-only cell its witness ran in. Do it once per
   survivor and never for any other outcome.
2. **The other gates.** Ask every other declared gate under the same
   application of the edit. Do it only for a whole suite that answers
   `fail`.
3. **The verdict.** A kill is a new failure among the head's collected
   tests, against the head's `tests` result from `gate_comparison`. It is
   confirmed when two things hold. No other gate gains a failure over the
   head's own result for that gate. The killing tests pass when asked
   alone, in the same cell, after the edit is restored.
4. **The severity.** A confirmed kill files the survivor as a `concern`,
   with `filed_severity` set to `blocker`. Its claim says the whole `tests`
   gate killed the edit and names every killing test. It says the witness
   does not reach what the edit breaks. A run that does not kill keeps the
   `blocker`, and its claim says the whole `tests` gate ran under the
   edit.
5. **No downgrade on a non-answer.** Each non-answer keeps today's blocker
   and its claim, word for word. A run can answer `error` or `skip`. The
   mutator can decline the edit. The collection can shrink. The head can
   carry no `tests` result. Another gate can gain a failure, answer
   `error`, or have no head result. The killing tests can fail again
   without the edit. A cell that stops keeps the blocker too, then ends
   the loop as today's `stopped` path does.
6. **The record.** The entry's own `outcome` stays `survived`. It reports
   the witness, and the finding reports the suite.
7. **The prose that turns false.** `anchored_blockers`'s first line says
   it selects every host-filed survivor (`saffron/phases/review.py:788`).
   `review_state`'s docstring says a host-filed survivor routes to REBUT
   (`saffron/phases/review.py:876-877`). Both now hold for a host-filed
   blocker alone. `survivor_finding`'s docstring calls its result "The
   blocker" (`saffron/phases/review.py:739`). `_apply_criterion_probes`'s
   docstring names no second run (`saffron/cell/session.py:1959-1968`).
8. **The existing tests.** Four tests script one `tests` answer per
   survivor and run out under the second run. Criterion 4's witness gains
   two assertions. The notes name each change.

## Out of scope

- **Which tests reach a file.** Core does not know that. It is language
  knowledge, and §2.1 keeps it in the repo's `.saffron/`. The host asks the
  declared gates instead.
- **An unanchored host-filed concern.** It renders in the findings table
  and the `Not covered` line (`saffron/report/pr_body.py:611-627`).
  `anchored_concerns` leaves it out of the queue line's count, as it does
  every unanchored concern. Changing that count is not this spec's.
- **Stack qualification of a downgraded concern.** A stack batch reads a
  layer's concerns back from the ledger with no probe
  (`saffron/qualify.py:81-96`). An anchored one from the `adequacy` lens is
  pooled as `unverified`, with the reason "its REVIEW probe did not
  survive" (`saffron/qualify.py:176-182`). A host-filed concern is that
  case. `unverified` neither drops it nor promotes it, so the operator
  still reads it. Its reason names the lens's own probe and not the
  host's, which is a wording gap. `saffron/qualify.py` stays forbidden.
- **A field in `criterion-probes.json` or `wrong-versions.json`** for the
  second run. The finding's claim carries it. A record field would reach
  every reader of those files.
- **A lens's own vacuity probe.** `probe_findings` keeps its counted set
  (`saffron/probe.py:302-316`).
- **The design record and the vocabulary.** The operator edited them by
  hand in this spec's pull request. That covers `DESIGN.md` §5.4.1 and
  §5.5 (`DESIGN.md:1125`, `:1137`, `:1205`). It covers `CONTEXT.md`'s
  criterion probe and wrong version entries (`CONTEXT.md:521`, `:533`).

## Notes for the agent

**New code, so no mutants.** The second run, its verdict and the new
claim tails do not exist at base. Their spelling is yours. So each
criterion declares a witness and wrong versions, and no mutant. The
`witness` gate reports `skip` for this spec, and that is expected.

**A lead for the second run.** `probe.check_probe` asks whether anything
in the whole suite notices one edit. Pass it the edit, the head's `tests`
result as `baseline`, the loop's own `_mutate`, and the same `test_paths`.
Pass `counted` as the head result's collected names. Do not pass
`probe.added_tests(...)`. `SA-0313`'s killing tests predate its diff, so
a set of added tests reads that kill as no kill. Its `killed` is a kill
to confirm, its `survived` keeps the blocker, and its `unproven` is a
non-answer. `saffron/probe.py` is forbidden, since its contract does not
change.

**The other gates ride on `run_tests`.** `check_probe` calls `run_tests`
once, inside the edit's application. Hand it a function that asks the
whole `tests` gate and, when that answers `fail`, asks every other key
of `gates` too, keeping their results. Generalise `_run_tests` to take
the gate's name (`saffron/cell/session.py:2046-2059`), so a raise still
sets `stopped`. Compare each kept result with the head's result of the
same `gate` in `gate_comparison.run.results`. Use
`saffron.gates.baseline.subtract_baseline`, the rule the head's own
comparison uses. Then ask the `tests` gate over `check_probe`'s killing
`failures` as a subset. Anything but `pass` is a non-answer.

**Five non-answers are driven, and five are not.** Criterion 3 drives an
`error`, a declined edit and a new `format` failure. It also drives a kill
that recurs without the edit, and a stopped cell. Five more take the same path with
no witness. They are a `skip`, a shrunken collection, and a head with no
`tests` result. They are also another gate answering `error`, and a gate
with no head result.

**Keep the blocker's claim on a stop.** Build and anchor the finding
before the second run, as today. A stopped cell can no longer serve
`read_at_head`, and its error path files nothing
(`saffron/cell/session.py:2093-2096`). So a second run that raises must
still append the finding it already holds.

**Keep the opening of the claim.** `_guarded_blockers` keys a `preserves`
criterion's blocker on `HOST_FILED`, the witness, then ` stayed green with `
(`saffron/phases/rebut.py:455-473`). Change only what follows the claim.
`survivor_finding` with no second-run answer keeps today's text, so
`tests/test_review.py`'s tests of it stay green
(`tests/test_review.py:2088-2256`). Set `filed_severity` only on a
downgrade. A blocker that stays keeps `None`, as `rebuttal.json`
records it today (`tests/test_session.py:12298`).

**What each survivor costs.** Each survivor adds one whole `tests` run,
which took 6.5 to 7 minutes for this repo's suite on the host. A failing
run adds the other declared gates, about 11 seconds on the host, and one
subset run.

**One stub for the three new witnesses.** Write a helper beside them that
replaces `saffron.gates.runner.run_gate` for the `saffron-gate-` container
alone. It records each call as `(gate, subset)` and answers from a script,
raising an answer that is an exception. Past the script it answers `pass`
for the gate it was asked, collecting every name the head collected.
`_stub_probe_gates` raises `StopIteration` past its script
(`tests/test_session.py:5732`). A wrong build then fails on the stub
rather than on an assertion, so do not use it for the script. Declare the
`format` gate in the policy and in `gates=` where a witness needs it, and
give the lens table a `format` result that passes.

**Criterion 1's witness.** Write it in `tests/test_session.py` after
`test_a_survivor_outside_the_diff_still_reaches_rebut`
(`tests/test_session.py:12309`), and take that test's shape. Declare one
criterion with one wrong version, the `tests` and `format` gates, and
drive the lenses with `_probe_turns`. Give the head's `tests` result four
collected names. Script four answers for the own edit. They are the witness
passing, a whole suite failing on two other tests, and `format` passing.
The fourth is those two tests passing as a subset. Script the wrong
version the same way with the third test.
Each whole-suite answer must collect all four names. A shorter list reads
as a shrunken collection, which is `unproven`. Assert the calls in order,
and that `cell.mutated` holds each edit twice. Spy on `critic_cell` as
`test_criterion_probes_and_wrong_versions_share_one_gate_only_cell_and_the_spend`
does (`tests/test_session.py:12677`), and assert three entries. Assert the
state is `READY_FOR_REVIEW` and that no `rebuttal.json` exists. Assert
each finding's severity, `filed_severity`, opening, and every killing
test's name.

**Criterion 2's witness.** The same shape, after criterion 1's, with the
`tests` gate alone. Give the head's `tests` result one failure. The own
edit meets a whole suite that passes. The wrong version meets one that
fails on that same old test alone. Drive the two rebuttal turns with
`_rebuttable(..., rebut_commits=0)` and `_CLAIMED_FIX`. The state is
`REBUTTAL_UNJUDGED`. Assert the first four calls, then both blockers in
`rebuttal.json` in order, with severity, opening and the whole-suite
sentence.

**Criterion 3's witness.** Six criteria, each with its own edit, and the
`tests` and `format` gates. Stub `worktree.source_mutated` to decline the
second criterion's edit on its second application. Script, in order:
1. The first witness passes, then a whole suite answers `error`.
2. The second witness passes.
3. The third witness passes, a whole suite fails on one test, then
   `format` fails.
4. The fourth witness passes, the same suite kill follows, and `format`
   passes. That test then fails again as a subset.
5. The fifth witness passes, then a `CellRuntimeError` is raised.

Assert the calls and the applied edits in order. Assert five `survived`
outcomes and one `unproven`. Assert the five blocker claims in
`rebuttal.json` equal today's text exactly, each with no `filed_severity`.

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
  (`tests/test_session.py:12291-12296`) takes your whole-suite sentence.
- `test_a_survivor_outside_the_diff_still_reaches_rebut`
  (`tests/test_session.py:12309`). Its subsets assertion
  (`tests/test_session.py:12396`) gains a `[]` after each witness.

Criterion 4's witness,
`test_a_killed_or_errored_criterion_probe_files_nothing_and_stops_nothing`
(`tests/test_session.py:12057`), asserts no call today. Pass
`subsets=` to its `_stub_probe_gates` call. After its state assertion,
assert the subsets are each witness alone, in order, and that
`cell.mutated` holds its three edits once each. Both hold at base, so it
stays a `preserves` witness. Keep its name.

**Measured on a prototype over `91a0f216`.** The source came to 453
changed tokens by the `size` gate's counter. Like the gate, that count
leaves out `tests/**`. That is 35% of the `bug` ceiling of 1300. The
tests carried 1193 more. The whole suite passed. Each new witness failed
with the source reverted. Each wrong version above, applied as an edit,
failed its criterion's witness on an assertion. The three new witnesses
take under a second together.

Commit after each witness passes. Uncommitted work dies with the cell.
