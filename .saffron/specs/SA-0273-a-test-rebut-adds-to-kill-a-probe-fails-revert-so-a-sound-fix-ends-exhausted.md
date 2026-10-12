---
id: SA-0273
title: A test REBUT adds to kill a surviving probe fails `revert`, so a sound fix ends `EXHAUSTED`
type: feature
priority: 1
depends_on: [SA-0262, SA-0271]
estimated_lines: 435
estimate_measured: true
touches:
  - saffron/gates/core/revert.py
  - saffron/gates/suite.py
  - saffron/cell/session.py
  - saffron/phases/package.py
  - tests/test_revert.py
  - tests/test_session.py
  - tests/test_package.py
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
  - saffron/phases/rebut.py
  - saffron/phases/review.py
  - saffron/agents/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/scheduler.py
  - saffron/record/**
  - saffron/report/**
  - saffron/gates/runner.py
  - saffron/gates/contract.py
  - saffron/gates/baseline.py
  - saffron/gates/core/criteria.py
  - saffron/gates/core/census.py
  - saffron/gates/core/witness.py
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - tests/test_scheduler.py
budget_usd: 36
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `revert_gate` takes an argument naming the tests to exempt. A new
      test it names is not handed to the reverted run. Every other new test
      still is. The gate's summary names each exempt test the gate would
      otherwise have handed to the run. An exempt name the gate would not
      have handed to the run, such as a test that existed at base, is
      neither handed nor named.
    witness: tests/test_revert.py::test_an_exempt_new_test_is_left_out_of_the_reverted_run_and_named
    wrong_versions:
      - The exempt names accepted and ignored, so every new test is still handed to the reverted run.
      - The exempt names dropped from the subset with nothing added to the summary.
      - The summary naming every exempt name, a test that existed at base included.
      - Any exempt name emptying the whole subset.
  - claim: >-
      After a rebuttal that moved HEAD, each blocker whose vacuity probe
      survived REVIEW has that probe asked again before the gates re-run.
      A blocker whose REVIEW probe ended `unproven` is not asked again. The
      probe runs in a gate-only cell built from the post-rebuttal patch,
      and each run is recorded in `rebut-probes.json`. A test the rebuttal
      added whose failure killed a probe there is exempt from `revert` at
      the re-run. `CellOutcome.revert_exempt` lists it, and so does
      `revert-exempt.json` in the task directory. So a task whose only red
      gate was that test reaches `READY_FOR_REVIEW`. Two tests are still
      handed to `revert` there. One is a test the rebuttal added that
      killed no probe. The other is a test from before REBUT that killed
      the probe. REBUT's blockers keep the probe verdict REVIEW gave them.
    witness: tests/test_session.py::test_a_test_rebut_added_that_kills_the_surviving_probe_reaches_ready_for_review
    wrong_versions:
      - The re-run judged with no exemption, so the task still ends `EXHAUSTED`.
      - Every test that killed the probe exempted, a test from before REBUT included.
      - Every test the rebuttal added exempted, whether or not it killed a probe.
      - The probe run deciding REBUT's own blocker objects in place, so `rebuttal.json` reads the probe `killed`.
      - No `rebut-probes.json` written.
      - No `revert-exempt.json` written.
      - The suite passing an empty exemption to `revert` whatever it was handed.
      - The probe asked over the patch REVIEW was shown rather than the post-rebuttal one.
      - The probe asked after the re-run, so the exemption arrives too late.
      - Blockers filtered on a probe being set alone, so a probe REVIEW left `unproven` is asked again.
  - claim: >-
      A rebuttal that moved no commit since the head it started at asks no
      probe again. It builds no gate-only cell after REBUT, writes neither
      `rebut-probes.json` nor `revert-exempt.json`, and leaves
      `CellOutcome.revert_exempt` empty.
    witness: tests/test_session.py::test_a_rebuttal_that_moved_no_commit_runs_no_probe_and_exempts_nothing
    wrong_versions:
      - The probe asked again whenever a blocker carries a surviving probe, whether or not HEAD moved.
      - Whether HEAD moved measured from the tree base rather than from the head the rebuttal started at.
  - claim: >-
      PACKAGE re-verifies the packaged commit with the cell's
      `revert_exempt`. Its head suite hands `revert` exactly those names.
    witness: tests/test_package.py::test_package_re_verifies_with_the_cells_revert_exemption
    wrong_versions:
      - "`package` calling `reverify` without the cell's exemption."
      - "`reverify` taking the exemption and running its head suite without it."
  - claim: >-
      When the probe cell after REBUT cannot apply the post-rebuttal patch,
      the task ends as REBUT's verdict cell would end it. A refused patch
      and an empty one end it `EXHAUSTED`, and a binary one `GATE_ERROR`.
      A REBUT line gives the reason, and the gates do not re-run.
    witness: tests/test_session.py::test_a_post_rebuttal_patch_the_probe_cell_cannot_apply_ends_the_task_as_rebut_does
    wrong_versions:
      - The probe cell's patch exceptions escape `_rebut_gates`, so the task ends `ORPHANED`.
      - A refused patch read as `GATE_ERROR`.
      - A binary patch read as `EXHAUSTED`.
      - A patch fault read as a probe that answered nothing, so the gates re-run and `revert` decides.
  - claim: >-
      When the probe cell after REBUT cannot be entered, or its baseline
      `tests` gate cannot run, and `revert` at the re-run then fails a test
      the rebuttal added, the task ends `GATE_ERROR`. A probe that ran and
      survived exempts nothing, and the same `revert` failure ends the task
      `EXHAUSTED`.
    witness: tests/test_session.py::test_a_probe_that_never_answered_after_rebut_ends_gate_error_not_exhausted
    wrong_versions:
      - A probe left `unproven` by infrastructure treated like any other, so the task ends `EXHAUSTED`.
      - Only a cell that never came up counted as infrastructure, so a lost baseline ends `EXHAUSTED`.
      - Every probe run after REBUT counted as infrastructure, so a survivor ends `GATE_ERROR`.
---

## Context

Backlog item **b-4a63b7**, found in the spec loop's run 13 on `SA-0118`.
It cites `DESIGN.md` §5.4. Every line number below was read at
`bc879e2c`.

**What happened.** The adequacy lens named a probe, and the probe
survived. REBUT added a test that kills it. That test guards a property
already true at base, so it passes with the source reverted. `revert`
failed it, and the task ended `EXHAUSTED` with a correct diff.

**Why `revert` fails such a test.** Its `candidates` are every test
the diff adds, plus every `declared` witness the head run collected
(`saffron/gates/core/revert.py:129-130`). Three kinds leave them. A
witness a criterion declares `preserves` is subtracted (`:114`).
A name that reads as a command-line option is dropped (`:131`). A
witness whose mutant names a file the diff left alone is exempt
(`:195-211`). A test REBUT adds belongs to no criterion and reads as no
option, so it stays a candidate.

**Why the task ends there.** After the rebuttal turn, `run_rebut` calls
`rerun_gates` (`saffron/phases/rebut.py:717`). A red re-run ends the task
`EXHAUSTED` (`:717-724`). In the cell, `_rebut_gates` is that callable
(`saffron/cell/session.py:3091-3108`). It calls `_judge`, which runs
`suite.against(tree, baseline)` (`:2590-2594`). That method takes no more
than the tree and the baseline (`saffron/gates/suite.py:143-144`). The
`revert_gate` call it reaches passes the spec's criteria and nothing that
names a test to spare (`:166-187`).

**How REBUT's verdict cell ends on a bad patch.** `run_rebut` builds the
verdict cell from the post-rebuttal patch. A `CriticPatchRejected`, which
`CriticPatchEmpty` subclasses, ends the task `EXHAUSTED`. A
`CriticPatchUnrepresentable` ends it `GATE_ERROR`
(`saffron/phases/rebut.py:729-741`). `rerun_gates` runs with no such guard
(`:717`). An exception escaping a cell ends the task `ORPHANED`
(`saffron/cell/session.py:3304-3310`).

**No probe runs after REBUT today.** REVIEW asks each anchored adequacy
finding's probe through `probe_findings`
(`saffron/cell/session.py:1506-1663`), through `_probe_adequacy` at
`:2966-2979`. That
function enters a gate-only cell from a patch, runs the `tests` gate once
as a baseline, then once per probe. A cell that cannot be entered, and a
baseline that cannot run, each leave every probe `unproven` with a reason
naming that (`:1618-1627`). Only `CellRuntimeError` is caught there, so a
patch the cell cannot apply escapes. A kill counts only for a test the
diff added. That set is `probe.added_tests` over the task's pre-turn
baseline and that cell's baseline (`saffron/probe.py:302-316`). A
`killed` result carries those tests' names (`:278-290`). Each entry
`probe_findings` returns carries them under `failures`. `probe_findings`
also decides each finding it is handed in place
(`saffron/phases/review.py:827-841`). A criterion-probe survivor and a
wrong-version survivor also carry a probe read `survived`
(`saffron/phases/review.py:736-770`).

**PACKAGE judges the same test again.** `package` calls `reverify` on
every packaged commit (`saffron/phases/package.py:834-842`). `reverify`
runs the whole suite at the packaged commit through `suite.against`
(`:482-491`, `:579-580`). Its `revert` sees the test REBUT added as new,
so it fails it again and the task ends `MERGE_FAILED`. That last step is
read from the code, not run.

**The decision.** The operator chose the arm where a probe run after REBUT
decides a test REBUT added. ADR 3 is amended by hand with this spec, and
`DESIGN.md` §5.4 and §5.6 too.

## Problem

Ask each surviving probe again after a rebuttal that moved HEAD. Exempt
from `revert` each test the rebuttal added that killed one. Carry the
exemption to PACKAGE.

**`revert`.** `revert_gate` takes a new required keyword argument: the
names to exempt. Remove them from the candidates as the `preserves`
witnesses are removed. Add to the summary note each exempt name that was
a candidate, as the `unreachable` witnesses are added. Every existing
call in `tests/test_revert.py` passes an empty one.

**The suite.** `GateSuite.against` takes the exemption as a keyword
argument that defaults to empty, and hands it to `revert_gate`.
`GateSuite.baseline` hands it an empty one.

**The cell.** `CellOutcome` gains `revert_exempt`, a list of node ids,
empty by default. Inside `_rebut_gates`, before `_judge` runs:

1. Take the blockers whose `probe_verdict` is `survived` and whose
   `probe` is set. Stop with no exemption if there are none.
2. When no commit landed since the head the rebuttal started at, stop
   with no exemption. That head is the `before` the `head_moved` lambda
   already measures from.
3. Hand copies of those blockers to `probe_findings`. Export the patch
   from the implementer's container against `spec.tree_base`, as
   `_rebut_critic_container` does. Pass the task's pre-turn
   `baseline.results`, as REVIEW's call does.
4. Map the probe cell's patch faults as `run_rebut` maps the verdict
   cell's. On `CriticPatchRejected`, emit a REBUT line carrying its
   `reason("the probe cell", "the post-rebuttal patch")` and return
   `EXHAUSTED`. On `CriticPatchUnrepresentable`, emit a REBUT line naming
   the binary change and return `GATE_ERROR`. Neither runs `_judge`.
5. Write the returned entries to `rebut-probes.json` in the task
   directory.
6. The exemption is every name under `failures` of a `killed` entry,
   minus what the `tests` result of the loop's last suite collected.
   With no such result, or none that collected, the exemption is empty.
   `latest` still holds that suite at this point. Write it, sorted, to
   `revert-exempt.json` in the task directory.
7. Note whether any entry is `unproven` for infrastructure. Its reason
   starts with one of the two prefixes its `unproven` calls write at
   `saffron/cell/session.py:1618-1627`. Make each prefix a module constant and use it at both
   places.
8. Pass the exemption to `_judge`, and from there to `suite.against`.
   Store it so the returned `CellOutcome` carries it, sorted.
9. After an aborted or drifted re-run, keep returning `GATE_ERROR`.
   Then check the entry step 7 looked for. If there was one, and a new
   `revert` failure names a test the loop's last `tests` result did not
   collect, return `GATE_ERROR`. Otherwise keep today's `EXHAUSTED` and
   `None`.

**PACKAGE.** `reverify` takes the exemption as a keyword argument that
defaults to empty, and passes it to its head suite's `suite.against`.
`package` passes the outcome's `revert_exempt`. The finishing suite's
`reverify` call in `saffron/cli.py:783-791` keeps the default. A
finishing commit touches only `.saffron/specs/*.md` (`saffron/finish.py:38`).

Two test stand-ins for `CellOutcome` gain `revert_exempt=[]`:
`_cell_outcome` in `tests/test_package.py:773-791`, and `pkg_outcome` in
`tests/test_session.py:10998`.

## Out of scope

- **A probe that ends `unproven` after REBUT for a reason other than
  infrastructure**, such as a refused edit. It exempts nothing, so a test
  REBUT added for it is still judged by `revert`.
- **Criterion-probe and wrong-version survivors.** Their blockers also
  carry a probe read `survived`, and step 1 takes them. No witness drives
  one. The witness drives a vacuity probe from the adequacy lens.
- **A stacked task.** Step 3 exports against `spec.tree_base`. The
  witnesses run unstacked, where it equals `spec.base_sha`.
- **The verdict session.** It is not shown the probe run's result.
- **PACKAGE run alone.** Queued `SA-0266` rebuilds a `CellOutcome` for a
  task whose PACKAGE raised. A rebuilt one must read `revert-exempt.json`,
  or re-verification ends `MERGE_FAILED`. Backlog item b-6b06e1 holds
  that, and `SA-0266` is not edited here.
- **A declared witness that existed at base and is exempt.** Criterion 1
  names it in the summary, since it is a candidate. No witness drives one.
- **`DESIGN.md` and ADR 3.** Both are edited by hand with this spec.

## Notes for the agent

**Every criterion is new code**, so each declares a witness and no mutant,
and `witness` will report `skip`. The exemption, the probe run after
REBUT, the fault mapping and the new field do not exist at base.

**At base every witness fails.** Criterion 1's call raises `TypeError` on
the new argument. Criterion 2's task ends `EXHAUSTED`. Criterion 3 and
criterion 6 read `outcome.revert_exempt`, which `CellOutcome` lacks at
base. Criterion 4's `reverify` hands its head suite no exemption.
Criterion 5's gates re-run at base. No witness imports a name the change
adds at module scope.

**Criterion 1.** Prior collects `t.py::test_a`. Head collects that,
`t.py::test_new` and `t.py::test_rebut`. Exempt `t.py::test_rebut` and
`t.py::test_a`. The reverted run fails every name it is handed. Assert it
was handed only `t.py::test_new`, the status is `pass`, and the summary
names `t.py::test_rebut` and not `t.py::test_a`.

**Criteria 2, 3, 5 and 6 share one drive of `_drive`.** Put it in a
helper. It uses fakes, and four of them hide a wrong build by default.
Build it from `_stub_the_runtime`, `_rebuttable`, `_adequacy_turns`,
`_adequacy_finding` and `_PROBE_POLICY`. The adequacy lens files two
findings. One is a concern whose probe edits `src/a.py`. The other is a
blocker whose probe edits `src/u.py`. Script the implementer's suites as
`_TASK_BASE`, `_TASK_HEAD`, then a green `tests` result collecting
`t.py::test_old`, `t.py::test_a`, `t.py::test_rebut` and
`t.py::test_rebut_other`. Once `suites` runs out, `_stub_the_runtime`
answers `[]`.

- Replace `run_gate`. A gate-only cell answers from a list in order,
  raising an entry that is an exception. REVIEW's probe cell gets a
  baseline and a green run, so `src/a.py`'s probe survives. The
  implementer's own calls are `revert`'s reverted run. Fail every handed
  name except `t.py::test_rebut`, and keep each handed subset.
- Replace `worktree.source_mutated`. Raise `CellRuntimeError` for
  `src/u.py`, so REVIEW leaves that blocker `unproven`. Record every other
  edit in `cell.mutated`. `_stub_probe_gates`' default accepts every edit,
  so an unasserted mutator would pass a build that never applied the probe.
- `_stub_the_runtime`'s `export_patch` returns one patch for every
  container and sha, so probing REVIEW's patch would pass. Return a grown
  patch once `_rebuttal_turn_has_run(cell)`.
- `_rebuttable`'s `commits_ahead` ignores the sha it is given, so a check
  measured from the tree base would pass. Criterion 3 asserts
  `cell.measured_from` is the stubbed head, `"c" * 40`.

Turns after the four lenses: the rebuttal, its extraction answering
finding 1, and the adequacy lens's verdict withdrawing both blockers.

**Criterion 2.** The probe run after REBUT gets a baseline collecting all
four names, then a run failing `t.py::test_a` and `t.py::test_rebut`.
Assert `READY_FOR_REVIEW`, and `revert_exempt` and `revert-exempt.json`
equal to `t.py::test_rebut` alone. Assert the last reverted subset is
`t.py::test_a` and `t.py::test_rebut_other`. Assert `rebut-probes.json`
holds one `killed` entry, for `src/a.py`, whose `failures` are
`t.py::test_a` and `t.py::test_rebut`. Assert `rebuttal.json`'s blockers
still read `survived` and `unproven`. Assert `cell.mutated` names
`src/a.py` twice, once for REVIEW and once after REBUT. Assert the last
patch applied into the gate-only container is the grown one.

**Criterion 3** uses `rebut_commits=0` and an `argued` answer, with only
REVIEW's two gate answers. Count the worktrees made for
`saffron-gate-SY-1`: REVIEW's gate table and its probe make two, and a
third is the defect.

**Criterion 5** drives three legs in one plain test, each under
`monkeypatch.context()` and its own `tmp_path` subdirectory. Refuse the
grown patch's apply into the gate-only container with a non-zero exit.
The binary leg's stderr carries `_NO_FULL_INDEX` from
`saffron/phases/package.py:59`. The empty leg exports an empty patch after
the rebuttal turn. Assert the state, one reverted run in all, the loop's,
and a watched line carrying the reason.

**Criterion 6** drives three legs the same way. In one, `critic_cell`
raises `CellRuntimeError` for the cell after the rebuttal turn whose
`network` is `None`, the probe cell. In one, the probe cell's baseline
raises `CellRuntimeError`. In one, its probe run is green, so the probe
survives. Assert the state, an empty `revert_exempt`, and
`t.py::test_rebut` in the last reverted subset.

**Criterion 4.** Use the `packageable` fixture and `_stub_package_cells`.
Put the real `reverify` back over the fixture's stub. Replace
`GateSuite.against` with a spy that keeps the `exempt` keyword it was
given, or `None` without one, and returns a green comparison. Set the
outcome's `revert_exempt`, run `package`, and assert the spy saw that set
once.

**`saffron/cell/**` and `saffron/gates/**` are in `elevate_on`,** so this
task runs `elevated` and `size` blocks.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each one to two lines naming the reason.

**Size.** A prototype measured 1740 tokens with `size_gate`'s counter,
against the `feature` ceiling of 3000. It held all nine steps above, the
24 `exempt` arguments in `tests/test_revert.py`, both stand-in edits and
the six witnesses. Its comments were one or two lines each.
