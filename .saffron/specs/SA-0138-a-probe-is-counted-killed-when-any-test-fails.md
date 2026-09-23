---
id: SA-0138
title: A vacuity probe is counted killed when any test fails, so a probe that only broke the format test reads as caught
type: feature
priority: 1
depends_on: [SA-0133]
touches:
  - saffron/probe.py
  - saffron/cell/session.py
  - saffron/phases/rebut.py
  - docs/evidence/scripts/2026-09-08-lens-corpus.py
  - tests/test_probe_check.py
  - tests/test_session.py
  - tests/test_corpus.py
  - tests/test_probe_cell.py
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
  - docs/backlog/**
  - docs/appendices/**
  - docs/adr/**
  - docs/evidence/fixtures/**
  - docs/evidence/passes/**
  - harness/**
  - images/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/intake.py
  - saffron/phases/review.py
  - saffron/cell/worktree.py
  - tests/test_witness_gate.py
  - tests/test_review.py
budget_usd: 30
max_attempts: 3
max_turns: 190
risk: elevated
acceptance:
  - claim: >-
      `check_probe` counts a probe `killed` only when a new failure's `code`
      is one of the names its `counted` argument holds. The witness drives
      three runs of one probe, and in each the baseline and the probed run
      collect the format test's node id and an added test in the same file.
      When only the format test fails under the probe, the probe reads
      `survived`, with `failures` empty and `uncounted` holding the format
      test's node id. When the added test fails as well, it reads `killed`,
      with `failures` holding the added test alone and `uncounted` the format
      test. When the added test already failed at the baseline and both fail
      under the probe, it reads `survived`, with the format test in
      `uncounted`.
    witness: tests/test_probe_check.py::test_a_probe_only_an_unadded_test_notices_survives_with_that_failure_beside_it
  - claim: >-
      A probe with a new failure reads `unproven`, never `survived` or
      `killed`, when no failure can be matched to a counted test. That is
      `counted=None`, or no new failure's `code` is in `counted` or among the
      names the probed run collected. Each such result holds every new
      failure's `code` in `uncounted`. The witness drives four runs of this kind,
      and in each the baseline collected nothing the probed run lacks. The first
      passes `counted=None` with a failure whose `code` the probed run
      collected. The second passes a `counted` set that names a test, and a
      failure whose `code` is in neither `counted` nor the probed run's
      `collected` list. The third is the second with a probed `collected` of
      `None`. The fourth passes `counted=None` with no new failure, and reads
      `survived`. `counted` has no default. A fifth run shows that one
      unmatched failure does not decide a run alone. It passes a `counted`
      set and two new failures, neither in `counted`. One `code` is a name
      the probed run collected and the other is not. It reads `survived`,
      with both codes in `uncounted`.
    witness: tests/test_probe_check.py::test_a_new_failure_no_counted_test_can_be_matched_to_is_unproven
  - claim: >-
      `probe.added_tests(base, head)` returns, as a frozenset, the names
      `head` collected that the `tests` result in `base` did not. A name
      collected only at base is not in it. A base `tests` result that
      collected `[]` makes every head name added. A result in `base` from
      any other gate is not read. It returns `None` in three cases: `base`
      holds no `tests` result, that result's `collected` is `None`, or
      `head.collected` is `None`. The witness drives each case named here.
    witness: tests/test_probe_check.py::test_added_tests_are_the_names_collected_at_head_and_not_at_base
  - claim: >-
      In a task, each adequacy probe counts the tests the diff adds. Those
      are the names the probe cell's own baseline run collected that the
      task's pre-turn baseline did not. The witness's base collects
      `t.py::test_old`. Every attempt's suite and the probe cell collect it
      and `t.py::test_new`.
      Of two findings with distinct probes, the one under which only
      `t.py::test_old` fails reads `survived` and reaches REBUT as a
      blocker. Its `probes.json` entry holds `failures: []` and `uncounted:
      ["t.py::test_old"]`. The one under which both fail reads `killed` and
      becomes a `note`, with `failures: ["t.py::test_new"]` and `uncounted:
      ["t.py::test_old"]`. Both entries carry every key an entry had at base,
      plus `uncounted`. The REBUT prompt's line for the survivor shows its
      probe and does not say the tests stayed green.
    witness: tests/test_session.py::test_a_probe_only_a_test_the_diff_did_not_add_notices_is_rebutted_with_that_failure_recorded
  - claim: >-
      When the task's pre-turn baseline holds no `tests` result, an adequacy
      probe whose run has a new failure reads `unproven`. Its finding keeps
      the `concern` the lens filed, and its `probes.json` entry names the
      failure in `uncounted`. In the witness the probe cell's baseline and
      probed runs both collect the failing test's node id. That name is not
      one the diff adds, because the task's base holds no `tests` result to
      compare with.
    witness: tests/test_session.py::test_a_probe_with_no_readable_base_enumeration_is_unproven_and_left_as_filed
  - claim: >-
      A criterion probe still runs its own criterion's witness alone, so no
      other test's failure can decide it.
    witness: tests/test_session.py::test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker
    preserves: true
---

## Context

Backlog item **b-19b255** is
`docs/backlog/b-19b255-a-probe-is-counted-killed-when-any-test-fails.md`,
tier 1. It was found in the spec loop's run 15 on `SA-0127` (#476). Item 117
built the probe path, and `SA-0109` shipped it.

Every sentence below about current code was read at `55c6d41b` on
2026-09-23, and rechecked at `4d141879`. `SA-0133` lands first and moves line numbers in
`saffron/cell/session.py` and `tests/test_session.py`. Find each cited name
by its name at the base you are cut from.

**Any new failure kills a probe today.** `check_probe`
(`saffron/probe.py:157-244`) applies one probe and runs the whole suite,
`run_tests([])` (`:196`). It subtracts the baseline with
`subtract_baseline([mutated], [baseline])` (`:226`). Any failure left over
makes the probe `killed`, with every leftover code in `failures`
(`:236-244`). On `SA-0127` the probe lengthened a line past the
formatter's width. The one failure left was
`tests/test_saffron_gates.py::test_the_fast_gates_name_their_tool_and_pass_on_a_clean_tree[format]`.
No test of `SA-0127` failed, and the Spec seat's run of the same probe
against the criterion's witness survived. These `SA-0127` figures come from
item b-19b255's own record. No run record of them is in the tree.

**What core can read of a failure.** `Failure.code` holds, for a gate that
enumerates, the node id of the test that failed (`saffron/gates/contract.py:52-56`).
No field says whether a test failed by assertion or by an error inside it.
`criteria` meets the same limit and reads a side only when some failure's
`code` is a name the gate collected (`saffron/gates/core/criteria.py:31-58`).
Its docstring records why. This repo's gate reads node ids from the
`FAILED ` lines only when its `re.finditer` pass matched nothing
(`.saffron/gates/tests.py:81-95`).

**Who calls `check_probe`.** Two callers, and nothing else in `saffron/`:

- `_probe_adequacy` (`saffron/cell/session.py:1291`). It runs the `tests`
  gate once over the head tree in the probe cell, `baseline = run_tests([])`
  (`:1407`), then calls `check_probe` per distinct probe (`:1416-1422`).
  Its `decide` builds each entry from `probe_check.record_fields` plus
  `probe_verdict` and `findings` (`saffron/cell/session.py:1329-1345`). Its
  one caller is `probed = _probe_adequacy(` (`saffron/cell/session.py:2577-2589`).
  The task's pre-turn suite is `baseline = suite.baseline(tree)`
  (`saffron/cell/session.py:1745`), taken at base before any turn. A second
  suite is in scope there too. It starts as `latest = baseline`
  (`saffron/cell/session.py:1748`) and becomes each attempt's head suite,
  `latest = comparison.run` (`saffron/cell/session.py:2233`). Nothing passes it to
  `_probe_adequacy` today.
- The lens-corpus driver's `probe_check.check_probe(` call
  (`docs/evidence/scripts/2026-09-08-lens-corpus.py:245-251`).

`tests/test_probe_cell.py:117-128` calls `_probe_adequacy` directly in a
cell-marked test.

**A probe with a criterion is already decided by its witness alone.**
`_apply_criterion_probes` (`saffron/cell/session.py:1445`) runs each
criterion probe through `witness_gate` (`:1563`), which runs
`run_tests([criterion.witness])` (`saffron/gates/core/witness.py:175`). No
adequacy probe carries a criterion. `Finding` has no such field
(`saffron/agents/findings.py:29-53`).

**How the anti-theater gate finds the tests a diff adds.** It reads
`before = _collected(prior)` and `after = _collected(results)`
(`saffron/gates/core/revert.py:101-102`). It then takes
`candidates = ((set(after) - set(before)) | (declared & set(after))) - preserved`
(`saffron/gates/core/revert.py:130`). The first term is the set of tests the
diff adds. The rest adds declared witnesses and removes `preserves` ones.

**What the record says.** `record_fields` writes ten fields
(`saffron/probe.py:247-265`). REBUT shows a survived probe to the implementer
with the words "and the tests stayed green" (`saffron/phases/rebut.py:133-137`).

## Problem

A probe the tests the diff adds miss can read as caught whenever its text
breaks a formatting, lint or unrelated test. The finding then leaves REVIEW
as a `note` (§5.5.1), since `apply_probe_verdict` demotes a `killed` probe's
finding (`saffron/phases/review.py:574-584`). A note never reaches REBUT. So the one check that runs the
lens's own probe reports coverage the diff's tests do not give.

## Out of scope

**Assertion versus error.** The gate contract cannot tell an assertion
failure from an error inside a test. So any failure of a counted test counts,
and the `ponytail:` below names that ceiling.

**Declared witnesses that already existed at base.** A probe counts only the
names the diff adds. A spec's `preserves` witness, or an existing test the
diff edits, is not among them.

**A diff that adds no test.** Its counted set is empty, so every applied
probe reads `survived` or `unproven`. Each `survived` one becomes a REBUT
blocker. Such diffs are rare. All eight corpus fixtures add test functions
(`docs/evidence/fixtures/*/diff.patch`).

**Kills by the lint or format test become blockers.** Measured across the
three published corpus passes (`docs/evidence/passes/*corpus*/SA-*/probes.json`):
14 probes read `killed`. In 12 the only failure was
`test_the_fast_gates_name_their_tool_and_pass_on_a_clean_tree[lint]` or
`[format]` in `tests/test_saffron_gates.py`. The other 2, both on `SA-0063`,
were killed by a test that fixture's diff adds. Those 12 are the defect this
spec fixes. Each one turning into a REBUT blocker in a task is the intended
outcome.

**A new parametrize id counts as an added test.** `added_tests` compares
names, so a new case of an existing parametrized test is added. One example
is `tests/test_queued_specs.py:66`, parametrized over the queued spec files.
Whether the implementer's cell and the probe cell collect the same names is
unmeasured. The probe cell runs with `network=None`.

**The protected sentences.** `DESIGN.md` §5.5.1, `CONTEXT.md`'s
**Vacuity probe** entry and ADR 0003
(`docs/adr/0003-a-test-is-judged-by-an-edit-chosen-to-break-it.md`) already
state the new rule. This spec's own pull request rewrote them by hand, so
none of the three needs an edit.

**The corpus's own numbers.** The driver passes every name its baseline
collected, so any collected test still counts there. A published pass is
re-derived from its run JSON and is not re-probed.

**`criterion-probes.json`.** Nothing about criterion probes changes.

## Notes for the agent

**New code, so witnesses and no mutants.** The `counted` argument, the
`uncounted` field and `added_tests` do not exist at base. So there is no
text a mutant could name. Criterion 6 is `preserves` and names a test that
exists now.

**`saffron/probe.py`.**

- `check_probe` takes a required keyword `counted: Collection[str] | None`.
  Give it no default, for the reason its docstring gives `test_paths`.
- Past the existing `gone` check, split the subtraction's new failures. A
  failure whose `code` is in `counted` kills the probe. Every other new
  failure goes to `uncounted`. With no counted failure the verdict is
  `survived`, or `unproven` in the two cases criterion 2 names.
- `ProbeResult` gains `uncounted: tuple[str, ...]` with a default of `()`.
  `tests/test_corpus.py:365-366` builds a `ProbeResult` from positional
  values, and `tests/test_probe_check.py:539-548` pins that three still
  build one.
- `record_fields` writes `uncounted` as a list, beside every field it writes
  now. `failures` keeps its meaning: the codes behind a `killed`.
- Add `added_tests(base: Sequence[GateResult], head: GateResult) ->
  frozenset[str] | None`. `base` is a suite's results, and `head` is one
  `tests` result.
- Write two `ponytail:` comments. One says any failure of a counted test
  counts, because `Failure` has no field that tells an assertion from an
  error. The other says one matched code makes a run readable, as
  `criteria._side`'s own `ponytail:` says.
- Update the module and function docstrings the new rule makes false.

**`saffron/cell/session.py`.** `_probe_adequacy` takes a required keyword
`base_results: Sequence[GateResult]`. The call site passes the task's
pre-turn `baseline.results`. After the probe cell's own baseline run,
compute `added_tests(base_results, <that run>)` once and pass it to every
`check_probe` call as `counted`.

**`saffron/phases/rebut.py`.** Reword `_blocker_line`'s suffix so it no
longer says the tests stayed green. A criterion probe's survivor uses the
same line, so the words must hold for both. For example, say that no test
able to decide the probe failed.

**The corpus driver.** Pass `counted=baseline.collected` in `_apply_probes`,
with a one-line comment that the corpus asks whether any collected test
notices.

**Existing tests the change breaks, which you update:**

- Every `check_probe` call in `tests/test_probe_check.py` gains `counted`.
  Supply it in the `_check` helper or at each call. A test asserting
  `killed` names its failing codes in `counted`.
- In `tests/test_session.py`, three tests expect `killed` from a task whose
  pre-turn suite holds no `tests` result. They are
  `test_a_blocker_whose_probe_is_killed_is_demoted_to_a_note`,
  `test_two_findings_naming_one_probe_are_decided_by_a_single_suite_run` and
  `test_the_host_writes_each_probes_json_entry_from_the_shared_helper`. In
  each, the killing test must be absent from the task's base `tests` result
  and collected by the probe cell's own baseline run. Script a `tests`
  result for every attempt as well. `census_gate` answers `error` when base
  enumerated and head did not (`saffron/gates/core/census.py:58-66`). In the
  last test the killing `t.py::test_b` is collected only by the mutated run
  today, so its probe baseline gains it and `baseline_collected` becomes 2.
  Its `shared` key set gains `uncounted`.
- In `tests/test_corpus.py`,
  `test_the_driver_writes_each_probes_json_entry_from_the_shared_helper`'s
  `shared` set gains `uncounted`. Its new failure's `code` must then be a
  name its baseline collected.
- `tests/test_probe_cell.py` passes `base_results` to `_probe_adequacy`.

**The witnesses.**

- Criteria 1 to 3 live in `tests/test_probe_check.py`, which already
  imports `saffron.probe` as `probe_check`. Call `probe_check.added_tests`
  by attribute, inside the test. A module-scope import of a new name makes
  the reverted run a collection error, which `revert` reads as `skip`.
- Criteria 4 and 5 drive `_drive`. Script the task's own suites with
  `_stub_the_runtime(suites=...)`, as
  `test_the_criteria_gate_reads_both_suites_and_invokes_nothing` does. For
  criterion 4, give the base `t.py::test_old` alone and every attempt
  `t.py::test_old` and `t.py::test_new`. Script the probe cell's runs with
  `_stub_probe_gates(gate_results=...)`. The first entry is its own baseline
  run, and each later entry is one probe's run. Read the REBUT prompt from
  `cell.turns`.
- That arrangement was measured on a prototype, with `suites` holding the
  base and then three head suites. The attempts reported `revert=skip`, not
  an abort, and the task reached `REBUTTING` with `probes: 1 survived, 1
  killed, 0 unproven`.
- The prototype is outside the tree, at
  `/private/tmp/claude-502/-Users-jm-Code-saffron/bda640fb-4a55-472f-bdc2-c6b44e02d13f/scratchpad/proto`.
  Its `tests/test_session.py` ends with `test_proto_c4`, `test_proto_c5`
  and `test_proto_c5_uncollected`. `PROTO_WRONG` in the environment selects
  a wrong version. The rerun gave this table. Each cell is that test's
  result.

  | wrong version | c4 | c5 | c5, uncollected code |
  | --- | --- | --- | --- |
  | none (the design) | pass | pass | pass |
  | any new failure counts | fail | fail | fail |
  | every head name counted | fail | pass | pass |
  | probe cell's run against itself | fail | pass | pass |
  | `base_results` is `latest.results` | fail | pass | pass |
  | no base `tests` result read as `[]` | pass | fail | pass |
  | `None` from `added_tests` as `frozenset()` | pass | fail | pass |
  | `counted=None` read as empty | pass | fail | pass |
  | `uncounted` left out of `probes.json` | fail | fail | pass |

- The last column is why criterion 5 needs a collected code. With a failure
  whose code the probe cell's runs did not collect, both wrong versions
  criterion 5 exists for still read `unproven`.
- Criterion 5 uses `_drive`'s default suites, whose pre-turn baseline holds
  no `tests` result. File the finding as a `concern`, so the task reaches
  `READY_FOR_REVIEW` with no REBUT turn.

**Wrong versions the witnesses must kill:**

- Any new failure counts, as today.
- Counting a failure by its `file` rather than its `code`.
- `counted=None` read as an empty set, or as every name.
- A run whose failures match no collected name read as `survived`.
- The pre-existing failure checked against `counted` before the
  subtraction.
- `added_tests` computed from the probe cell's run against itself, or
  every head name passed as `counted`.
- `base_results` is `latest.results`, the last attempt's suite.
- A `None` from `added_tests` turned into `frozenset()` in the session.
- Any run with an unmatched failure read as `unproven`, or `uncounted`
  keeping only the first code.
- The REBUT line left saying the tests stayed green.
- A base with no `tests` result read as one that collected `[]`.
- `uncounted` kept on `ProbeResult` and left out of `probes.json`.
