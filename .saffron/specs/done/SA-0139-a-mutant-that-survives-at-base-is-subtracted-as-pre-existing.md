---
id: SA-0139
title: A mutant its witness survives at base is subtracted as pre-existing, so `witness` never asks the cell to kill it
type: bug
priority: 2
depends_on: []
touches:
  - saffron/gates/baseline.py
  - saffron/phases/implement.py
  - tests/test_baseline.py
  - tests/test_suite.py
  - tests/test_implement.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - saffron/gates/suite.py
  - saffron/gates/runner.py
  - saffron/gates/contract.py
  - saffron/gates/core/**
  - saffron/cell/**
  - saffron/phases/package.py
  - saffron/phases/rebut.py
  - saffron/phases/review.py
  - saffron/agents/**
  - saffron/report/**
  - saffron/probe.py
  - saffron/replay.py
  - tests/test_witness_gate.py
  - tests/test_scheduler.py
budget_usd: 20
max_attempts: 3
max_turns: 160
risk: elevated
acceptance:
  - claim: >-
      `subtract_baseline` no longer lets a baseline `witness` failure coded
      `survived-mutant` cancel a head failure, so every such head failure is
      new. With one survivor at base and that survivor plus a second one at
      head, both head survivors are new. Three baseline failures still cancel
      their match: a `witness` failure coded `unproven`, a `survived-mutant`
      failure under `tests`, and a `lint` failure.
    witness: tests/test_baseline.py::test_a_witness_mutant_that_survived_at_base_is_still_new_at_head
  - claim: >-
      Through `GateSuite.against`, a criterion whose witness survives its
      mutant at base and again at head is one blocking new `witness` failure
      at the elevated tier. That holds when the spec declares `elevated` and
      when an `elevate_on` path elevates a `standard` spec. At `standard` it
      stays advisory, so the head `witness` result is `fail` and no new
      failure is reported. At declared `elevated`, a mutant that survived at
      base and is killed at head reports no new failure. A `lint` failure on
      both sides cancels in all four cases.
    witness: tests/test_suite.py::test_a_witness_left_unstrengthened_blocks_when_elevated_and_a_killed_mutant_reports_nothing
    mutant:
      file: saffron/gates/core/witness.py
      find: 'code="survived-mutant",'
      replace: 'code="survived",'
  - claim: >-
      `repair_prompt` opens with one fixed preamble that stays true when a
      survivor the base already had is listed. It no longer says every listed
      failure is new since the base commit. A list of one `types` failure and
      a list adding a `witness` survivor get the same preamble.
    witness: tests/test_implement.py::test_the_repair_preamble_stays_true_when_a_base_survivor_is_listed
---

## Context

Backlog item **b-6377cf**, found in the spec loop's run 15 on `SA-0127`
(#476).

A `preserves` criterion names a test that exists at base, and its mutant can
survive there. That is the case a spec writes when it asks the cell to
strengthen an existing witness. The `witness` gate then reports the survivor
at base and again at head, if the cell never strengthened the test.

**Where `witness` runs.** `GateSuite.baseline` and `GateSuite.against` both
call `_run` (`saffron/gates/suite.py:132-138`). `_run` hands
`runner.run_suite` the tree's mutator (`saffron/gates/suite.py:150-156`).
`run_suite` places the result of `run_witness` right after `tests`
(`saffron/gates/runner.py:328-345`), and `run_witness` calls `witness_gate`
(`saffron/gates/runner.py:294-299`). So the baseline suite and every head
suite carry a `witness` result built the same way. A task's cell builds
its `GateSuite` and calls `baseline` (`saffron/cell/session.py:1742-1745`),
then calls `against` on each attempt (`saffron/cell/session.py:2229`).
PACKAGE's `reverify` (`saffron/phases/package.py:466`) does the same. It
builds a `GateSuite` (`saffron/phases/package.py:499`), calls `baseline`
(`saffron/phases/package.py:557`) and calls `against`
(`saffron/phases/package.py:564`).

**The survivor's identity.** `witness_gate` records a survivor as a
`Failure` whose `file` is the criterion's witness and whose `code` is
`survived-mutant`. The message names the mutant's file and the claim
(`saffron/gates/core/witness.py:244-258`). None of those differ between base
and head for a witness that exists at base and is left unchanged.

**The subtraction.** `subtract_baseline` counts the baseline's failures by
`identity` and lets each one cancel one head failure with the same identity
(`saffron/gates/baseline.py:46-55`). `identity` is `(gate, file, code,
normalized message)` (`saffron/gates/contract.py:98-109`). So the head
survivor cancels against the base survivor and is never new.

**What each tier does with a new `witness` failure.** `_compare` drops every
new failure whose gate is advisory (`saffron/gates/suite.py:231-245`).
`_advisory` puts `witness` in that set unless the tier is
`elevated` (`saffron/gates/suite.py:220-228`). The tier comes from the head's
own changed files through `effective_risk` (`saffron/gates/suite.py:145`).

- At `elevated` the survivor at head is cancelled today, so the attempt is
  green and REPAIR never hears of it. After this change it is a new failure,
  so the cell gets a repair turn and ends `EXHAUSTED` if it never kills the
  mutant. `repair_prompt` hands it over under a preamble saying every listed
  failure is new since the base commit (`saffron/phases/implement.py:141-160`).
  `tests/test_implement.py:551-555` pins that preamble. It turns false for a
  survivor the base already had, so criterion 3 replaces it.
- At `standard` nothing changes in the comparison. `witness` is advisory
  there, so a new survivor was dropped before and is dropped after. The
  gate table already marks the head's `fail` as `(advisory)`
  (`saffron/report/pr_body.py:465-466`), and the not-covered list names it
  (`saffron/report/pr_body.py:519-525`). This repo elevates any diff under
  `saffron/gates/**` and `saffron/cell/**`, which is where `SA-0127` worked.

## Problem

`witness` exists to fail a claim nothing guards (§5.4.1). Baseline
subtraction exists to spare a task the failures it inherited (§5.4). A
survivor at base is not inherited in that sense. The spec declared the
mutant, and the cell was asked to kill it. The subtraction reads it as a
flaky test the repo already had, and the claim reaches the pull request
unguarded. On `SA-0127` the delegate had to rerun both mutants by hand at
head and at base to show the cell had strengthened its witnesses.

The carve-out also fires for a survivor nobody asked the cell to kill. A
spec writer can declare a `preserves` mutant believing the existing witness
already kills it. At `elevated` that task now ends `EXHAUSTED`, and that is
intended. The defect is the spec's, and the outcome surfaces it.

## Out of scope

**Every other gate and every other `witness` failure.** Only a `witness`
failure coded `survived-mutant` changes. `witness_gate` emits no other
failure code at base, so the other-code half of criterion 1 is driven by a
hand-built `Failure`.

**The advisory level.** `witness` stays advisory at `standard` (§5.4.1).
Making a survivor block there is a different decision.

**Drift.** A mutant that survived at base and does not apply at head leaves
`witness` at `skip` there. `suite_drift` reports that as drift
(`saffron/gates/baseline.py:58-100`), and this spec leaves it so.

**The written rules.** They land by hand in this spec's own pull request,
before any cell runs, and already state the carve-out. The design edits are
§5.4's two bullets (`DESIGN.md:779`, `DESIGN.md:925`) and §5.4.1's blocking
level (`DESIGN.md:1017-1022`). The table row on cancelled failures is the
fourth (`DESIGN.md:1306`). The glossary edits are the two failure entries
(`CONTEXT.md:330-341`). Both files are protected and stay forbidden here.

**`is_no_progress`, `probe.py` and `replay.py`.** `is_no_progress` compares
two attempts' new failures, never the baseline. `saffron/probe.py:226` and
`saffron/replay.py:102` call `subtract_baseline` too. Neither builds a
`witness` result: `probe.py` subtracts one `tests` result, and `replay.py`
calls `run_suite` with no mutator (`saffron/replay.py:164`). So the change is
inert on both paths.

## Notes for the agent

**Where it lives.** In `subtract_baseline`, the one function every suite
comparison reaches. `saffron/gates/suite.py` is forbidden, so the carve-out
cannot move into `_compare`. Leave `is_no_progress` and `suite_drift` alone.
Rewrite the docstring's first sentence and the module docstring's claim that
base failures are never the task's problem, since both become false.

**Which kind of change.** An edit to existing code whose new text does not
exist yet. Criteria 1 and 3 declare a witness and no mutant. The witness
gate's `declared` list leaves them out (`saffron/gates/core/witness.py:130`),
and `revert` drives them. Criterion 2's mutant renames the code `witness_gate` already writes,
which is why `saffron/gates/core/**` is forbidden. Key the carve-out on the
gate name and the code together.

**Criterion 1's witness** builds `GateResult`s by hand, in the style of
`test_extra_failures_sharing_one_baseline_identity_are_new`
(`tests/test_baseline.py:117`). Give the baseline a `witness` survivor A, a
`witness` failure coded `unproven`, a `survived-mutant` failure under
`tests`, and a `lint` failure. Give the head all four plus a second
`witness` survivor B. Assert the new failures are exactly A and B, in head
order, compared as `(gate, file, code)`.

**Criterion 2's witness** drives `GateSuite.against`. Subclass `_Tree`
(`tests/test_suite.py:19-61`) rather than writing a second tree, and reuse
`_suite`, `_Spec`, `_lint` and `FAIL`. `_Tree.mutated` yields a reason
(`tests/test_suite.py:58-60`), so the witness gate always skips there. The
subclass overrides it to apply, and answers `tests` per call.

1. The spec carries one `Criterion` with `preserves: true`, a witness id W
   and a `Mutant` against `src/a.py`.
2. A `tests` call with no subset passes and reports `collected` as `[W]`.
3. A subset call with no mutant live passes and reports `collected` as the
   subset, because the probe refuses any other names
   (`saffron/gates/runner.py:282-292`).
4. A subset call with the mutant live passes on a surviving tree and fails
   on a killing one.
5. Every tree carries one `lint` failure. Keep every `tool` equal, or drift
   passes the test for the wrong reason (`tests/test_suite.py:81-90`).

Run four legs, each against a baseline from a surviving tree. At declared
`elevated`, a surviving head reports one `("witness", W, "survived-mutant")`
new failure and nothing else. A `standard` spec whose head changes an
`elevate_on` path reports the same. At `standard`, a surviving head reports
no new failure while its `witness` result is `fail`. At declared `elevated`,
a killing head reports no new failure. The elevate-by-path leg can follow
`test_the_head_runs_tier_decides_what_blocks_not_the_baselines`
(`tests/test_suite.py:196-218`). Keep all four legs in one `def`, because
the last two pass at base and `revert` blocks a new test that does.

Import `Criterion` and `Mutant` from `saffron.intake`, which exists at base.
Add no import of a name the change creates at module scope.

**Criterion 3, the preamble.** Replace the whole preamble with this text,
word for word, as one fixed string for every list:

```
These failures are yours to fix. A failure the base commit already had is
left out, unless it is a witness that survived its mutant and blocks this
task. Fix these and commit.
```

The last clause keeps it true at `standard`, where no survivor is listed.

It is one line in the code, wrapped here.
Update the pinned preamble in
`test_repair_text_carries_failures_and_never_a_gate_status`
(`tests/test_implement.py:541-555`) to match. The witness calls
`repair_prompt` twice. The first list holds one `types` failure. The second
adds a `witness` failure coded `survived-mutant`. Each preamble must equal
the full new text.

**Two repair-turn checks read the old wording.**
`test_a_size_failure_at_standard_does_not_enter_the_repair_loop`
(`tests/test_session.py:2472-2489`) and
`test_a_declared_gate_with_blocking_false_does_not_repair`
(`tests/test_session.py:2650-2671`) assert no turn contains "These failures are
new". Both run through `_drive` (`tests/test_session.py:1214`). Its stub
answers any unscripted turn with a default one
(`tests/test_session.py:1296-1299`). So that check is the only one that sees
a repair turn. With the new preamble it passes whatever happens. Replace both
with a check that no turn starts with `implement.repair_prompt([])`, which
holds whatever the preamble says. `SA-0133` also touches
`tests/test_session.py`, and its repair-turn test must not match on
preamble text either.

**Wrong versions the witnesses must kill:**

- A carve-out keyed on the code alone, which stops the `tests` failure with
  that code from cancelling.
- A carve-out keyed on the gate alone, which stops the `unproven` `witness`
  failure from cancelling.
- One that drops survivors from the head as well, so nothing is reported.
- One that exempts the whole baseline once any survivor is present, so the
  `lint` failure turns new.
- The old preamble left in place.
- A preamble rewritten for the survivor case alone.

**The `size` gate blocks at `elevated`**, and a `bug` gets 1300 changed
tokens. Keep each new docstring to one or two lines, and keep the legs of
criterion 2 compact.
