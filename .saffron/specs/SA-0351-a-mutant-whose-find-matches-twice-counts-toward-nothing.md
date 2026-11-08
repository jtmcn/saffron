---
id: SA-0351
title: A declared mutant whose find matches other than once counts toward nothing, so a diff that repeats the line escapes the witness gate
type: bug
priority: 2
depends_on: [SA-0342]
estimated_lines: 90
touches:
  - saffron/gates/core/witness.py
  - saffron/gates/runner.py
  - saffron/gates/suite.py
  - saffron/cell/worktree.py
  - tests/mutation.py
  - tests/test_witness_gate.py
  - tests/test_gates.py
  - tests/test_constant_mutants.py
  - tests/test_worktree.py
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
  - saffron/gates/baseline.py
  - saffron/gates/contract.py
  - saffron/gates/core/revert.py
  - saffron/cell/session.py
  - saffron/probe.py
  - saffron/phases/**
  - saffron/intake.py
  - saffron/mutants.py
  - saffron/task.py
budget_usd: 60
max_attempts: 3
max_turns: 240
risk: standard
acceptance:
  - claim: >-
      A declared mutant whose `find` matches its file zero, two or three times
      fails the `witness` gate, and the `tests` gate never runs for it. Each
      such criterion adds one failure. Its `file` is the criterion's witness,
      and its code is `mutant-find-absent` for zero matches and
      `mutant-find-repeated` for two or more. Its message ends with the
      criterion's claim, and the rest of it carries the count as its only
      number. The summary says how many of the declared mutants did not match
      once, and it names no survival when no witness survived. A mutant that matches once beside them is still applied and run.
      The witness drives the counts 0, 1, 2 and 3 in one call through
      `tests.mutation.host_mutator`. It then drives the counts 0, 2 and 3 as a
      criterion probe and as a wrong version, and each of those is still
      `skip`, named in the summary, with no failure.
    witness: tests/test_witness_gate.py::test_a_declared_find_that_matches_other_than_once_fails_naming_its_criterion_and_count
    wrong_versions:
      - A find that matches zero times stays unproven, as at base, so only two or more fails.
      - Only a count of exactly two fails, so a find matching three times stays unproven.
      - The failure's `file` is the mutant's file rather than the criterion's witness.
      - The message says the find matched more than once and carries no count.
      - Zero matches and two or more share one code.
      - The `tests` gate is run for a criterion whose find did not match once.
      - A criterion probe or a wrong version whose find does not match once fails too, so REVIEW files it as a survivor.
      - The failures are recorded and the status stays `skip`.
      - The summary keeps the base wording and does not say how many mutants did not match once.
      - The new failures join the survivors, so the summary says they survived.
  - claim: >-
      A failure for a find that did not match once withholds the edit
      (§5.4.1). Neither the `find` nor the `replace` text appears in the
      serialized gate result, and neither appears in the table
      `saffron.phases.review.gate_summary` renders from it. The witness drives
      the counts 0, 2 and 3, with a find and a replace that share a
      distinctive token.
    witness: tests/test_witness_gate.py::test_a_find_count_failure_names_neither_half_of_its_edit
    wrong_versions:
      - The message quotes the find text, so the cell can locate the line.
      - The message quotes the replace text.
      - The summary appends the find text to each criterion it names.
  - claim: >-
      `saffron.gates.baseline.subtract_baseline` returns a head failure for a
      find matching twice as new when the base run applied the mutant, and
      when the base run found the find absent. It cancels it when the base
      run reported the find matching two or three times. Every result is
      built by `witness_gate` through `host_mutator`, over one criterion
      whose witness, claim and mutant file do not change between base and
      head. The witness rewrites that one file's contents before each run.
    witness: tests/test_witness_gate.py::test_a_find_count_failure_is_new_unless_the_base_reported_its_own
    wrong_versions:
      - A find-count failure is never subtracted, as a `survived-mutant` failure is not, so a base that reported the same failure still leaves it new.
      - Zero matches and two or more share one code, so a base whose find was absent cancels a head whose find matches twice.
  - claim: >-
      A constant mutant whose find matches its file twice stays unproven. The
      witness runs one `GateSuite._run` over a real git tree and a real
      `tests` gate. The diff gives one constant twice in one file. One
      criterion's witness reads that constant back, and another declares a
      mutant whose find matches the same file twice. The gate fails with
      exactly one failure, the declared criterion's `mutant-find-repeated`.
      The first witness is named in the summary, and the tree is clean after.
    witness: tests/test_constant_mutants.py::test_a_constant_mutant_whose_find_matches_twice_stays_unproven
    wrong_versions:
      - "`GateSuite` still hands the constant mutants to `run_suite` inside `acceptance`, so a constant mutant whose find matches twice fails."
      - A constant mutant whose find matches twice is left out of the summary.
      - The declared mutant beside it stays unproven too.
  - claim: >-
      The cell's mutator hands the gate its count.
      `witness_gate` over `saffron.cell.worktree.source_mutated`, on a
      committed host git repo, fails with `mutant-find-absent` for a find
      matching zero times and `mutant-find-repeated` for two and for three.
      Each message carries its count spelled as digits, as a whole word. A find matching once
      is applied, and only its witness reaches the `tests` gate. The tree is
      clean after.
    witness: tests/test_worktree.py::test_the_cell_mutator_hands_the_gate_its_find_count
    wrong_versions:
      - Only `tests.mutation.host_mutator` reports its count, so a cell's gate still reads `skip`.
      - "`source_mutated` reports a count only for two or more, so a find absent in a cell stays unproven."
      - "`source_mutated` writes the first match before it yields the count."
  - claim: >-
      A find-count failure at head against a base whose witness died is a new
      failure and never drift. A `fail` whose subset runs set no tool names
      the head `tests` result's tool, which `run_witness` already holds. The
      witness runs `GateSuite.baseline` then `GateSuite.against` over a real
      git tree and a real `tests` gate, with two `preserves` criteria. The
      first declares a mutant whose find matches once at the tree base, where
      its witness dies. At head the same file holds the find twice. The
      second declares a mutant naming a file that does not exist, so it stays
      unproven on both sides and no subset run sets a tool. The comparison
      has no drift and exactly one new failure, the witness gate's
      `mutant-find-repeated` on the first criterion.
    witness: tests/test_constant_mutants.py::test_a_find_repeated_at_head_is_one_new_failure_and_no_drift
    wrong_versions:
      - A `fail` holding only find-count failures carries `tool=None`, so `suite_drift` reads a tool change and the attempt ends `GATE_ERROR`.
      - The head tool is used only when every declared criterion miscounted, so a fail beside an unproven criterion carries `tool=None`.
---

## Context

Backlog item **b-a68b24**. It cites `DESIGN.md` §5.4. Every line below was
read at `30c851cb`.

**What the gate does today.** `witness_gate` hands each declared criterion's
mutant to `mutate` (`saffron/gates/core/witness.py:179`). A reason yielded
back is appended to `unproven` and the loop moves on
(`saffron/gates/core/witness.py:180-182`). A result with no survivor and no
death is `skip` (`saffron/gates/core/witness.py:309-313`). The module
docstring calls a find that is absent or ambiguous the ordinary case,
counted toward nothing (`saffron/gates/core/witness.py:31-34`).

Both mutators count the find and refuse zero and two or more alike, by a
yielded text reason. The host one is `tests/mutation.py:150-163`. The cell
one is `source_mutated` (`saffron/cell/worktree.py:738-745`). The gate never
sees the count as data. So a zero-match find is not handled apart from a
repeated one at base. Both are unproven, and this spec makes both fail.

On `SA-0312` (#957) the cell copied a function tail into a new helper.
Criterion 5's declared find then matched three times in `saffron/task.py`.
The gate passed the criterion with no mutant run.

**The operator-side precedent.** `driver.py probe` refuses a find whose count
is not one and names the count
(`.claude/skills/run-saffron-spec-loop/driver.py:1563-1567`).

**Who else calls the gate.** REVIEW runs each criterion probe and each wrong
version through `witness_gate` with `edit_noun` set
(`saffron/cell/session.py:2064-2071`). It reads a `fail` there as `survived`
(`saffron/phases/review.py:790-795`). So the new failure must not reach those
two nouns. `GateSuite._run` derives the constant mutants and hands them to
`run_suite` inside `acceptance` (`saffron/gates/suite.py:164-176`). From
there `run_witness` passes them to `witness_gate`
(`saffron/gates/runner.py:294-299`). The gate cannot tell a constant mutant
from a declared one there.

**Baseline subtraction.** `normalize_message` replaces every run of digits
(`saffron/gates/contract.py:105-111`), and `identity` keys on gate, file,
code and that message (`saffron/gates/contract.py:114-125`). Only a
`survived-mutant` failure escapes subtraction
(`saffron/gates/baseline.py:24-32`). So one code for every count would let a
base whose find was absent cancel a head whose find matches twice.

**Drift.** `suite_drift` compares each gate's `tool` when the gate reported
`pass` or `fail` on both sides (`saffron/gates/baseline.py:101-106`). A
drifted comparison ends the attempt `GATE_ERROR`
(`saffron/cell/session.py:865-871`). `witness_gate` sets its `tool` only from
a subset run that died or survived (`saffron/gates/core/witness.py:258`,
`:273`). A `fail` built from find-count failures alone would carry `None`
against a base whose witness died. On a prototype that left it `None`,
criterion 6's arrangement reported `witness: tool 'pytest 9.1.1' -> None`.
`run_witness` holds the head `tests` result as `tests_result`
(`saffron/gates/runner.py:180`).

**`DESIGN.md` §5.4.1.** Amended by hand at this spec's base, in the paragraph
that starts "A declared mutant that does not apply fails".

## Problem

1. **The count reaches the gate as data.** Each mutator keeps its text
   reason for a find that matched zero times or more than once. The yielded value also carries the count, which the gate reads
   without parsing text. `witness.Mutated` stays a context manager yielding
   `str | None` (`saffron/gates/core/witness.py:100`). So
   `saffron/probe.py:207-210` and the REVIEW wrapper at
   `saffron/cell/session.py:2038-2046` pass it through unedited.
2. **A declared mutant fails.** Under `edit_noun="mutant"`, a declared
   criterion whose mutant did not match once adds a `Failure`. Its `file` is
   the witness. Its code is `mutant-find-absent` for zero matches and
   `mutant-find-repeated` for more. Its message names `mutant.file` and the
   count, and ends with the claim, as the `survived-mutant` message does
   (`saffron/gates/core/witness.py:263-272`). Any such failure makes the
   status `fail`, beside any survivor. The summary counts these failures
   apart from the survivors, and names no survival when none survived. With
   none, every summary keeps its base wording. A `fail` whose subset runs set
   no tool carries the head `tests` result's tool, which `run_witness` hands
   the gate.
3. **Everything else stays unproven.** A criterion probe, a wrong version and
   a constant mutant keep the base behaviour. `GateSuite._run` hands the
   constant mutants to the gate apart from `spec.acceptance`, through
   `run_suite` and `run_witness`. `run_witness`'s subset probe still counts
   them as mutants to verify (`saffron/gates/runner.py:234`).
4. **Prose that turns false.** Rewrite `saffron/gates/core/witness.py:31-34`,
   the comment at `saffron/gates/core/witness.py:76-81`, and the `skip`
   sentences of `witness_gate`'s docstring
   (`saffron/gates/core/witness.py:122-126`). Name the yielded count in
   `source_mutated`'s docstring (`saffron/cell/worktree.py:673-678`). In
   `tests/mutation.py`, the docstrings at `:41-47`, `:117-121` and `:233-238`
   call a find that does not match once the ordinary case. Keep each new
   comment to two lines.

## Out of scope

- A mutant whose file is absent, untracked, unreadable, dirty, or outside the
  tree. It stays unproven. Only the find count fails.
- Exempting the new failures from subtraction. A base run that reports the
  same failure cancels it, since the diff did not cause it.
- A witness collected at base whose find is absent at base and at head. The
  two failures cancel, so the gate still says nothing there. A witness new at
  head is unproven at base, before `mutate`
  (`saffron/gates/core/witness.py:163-165`). So its head failure is always
  new.
- An inner `error` after a find-count failure. It ends the gate as `error`
  and drops the failure, as it drops a survivor today
  (`saffron/gates/core/witness.py:244-255`).
- Filing a criterion probe or a wrong version that does not apply. Each
  stays unproven.

## Notes for the agent

**`SA-0342`, the parent.** It edits `revert_gate`'s call in
`saffron/gates/suite.py:180-200`. This spec edits the `run_suite` call before
it (`saffron/gates/suite.py:170-176`). Find each line by its text, not
its number. `SA-0338`, `SA-0340` and `SA-0341` edit `tests/test_session.py`,
and `SA-0338` edits `tests/test_worktree.py`. Find every line this spec cites
in those two files by its text too. `SA-0338`, earlier in the chain, moves a criterion's mutant onto
`refs/saffron/mutants`. `witness_gate` still reads it from `Criterion.mutant`.

**A find absent at head fails, by intent.** A witness new at head never
reaches `mutate` at base, so its head failure is always new. That holds for a
find absent at head as well. With `SA-0338`, a mutant on the ref is written
against what the diff writes. So a find absent at head means the claim's code
is not where the spec says it is, and the cell is told so.

**Edit or new.** The failure branch, the count's carrier and the separate
constant-mutant argument are new code. So no criterion declares a mutant,
and `witness` reports an honest `skip` on each. A queued spec carries no
inline mutant once `SA-0338` lands in any case.

**A shape that worked.** A prototype yielded a `str` subclass defined in
`saffron/gates/core/witness.py` with an `int` count attribute. Both mutators
imported it, and nothing that passes a reason through needed an edit.
`saffron/cell/worktree.py` importing `saffron.gates.core.witness` made no
cycle. The gate counted a failure only for a criterion from `acceptance`
under `edit_noun == "mutant"`. It took constant mutants in a new
keyword-only `derived` argument, `()` by default. It took the head tool in a
keyword-only `tests_tool`, which `run_witness` filled from `tests_result`.

**The witnesses.** Plain `def`s, never a parametrised test.

- In `tests/test_witness_gate.py`, write four files whose one find occurs 0,
  1, 2 and 3 times, each with a line of padding. Give each criterion a claim
  holding no digit, so the count is the message's only number once the claim
  is removed. Criterion 3 keeps one criterion and one mutant file, and
  rewrites that file with the base's count, then the head's, before each run.
  Distinct names such as `a.py` and `b.py` would put different text in each
  message. Then no base would cancel, and a version sharing one code for 0
  and 2 would pass the absent-base case.
- In `tests/test_constant_mutants.py`, follow
  `test_a_witness_reading_its_constant_back_survives_a_constant_mutant`
  (`tests/test_constant_mutants.py:132`). A head file of `LIMIT = 3` twice,
  then a function returning `LIMIT`, gives a constant mutant whose find
  matches twice. A witness reading `LIMIT` back is the constant mutant's. A
  second witness asserting the literal carries the declared mutant.
- Criterion 6 uses the same harness. Commit the tree base, set `diff_base` to
  it, and run `suite.baseline`. Then commit the head and run
  `suite.against(tree, baseline)`. Mark both criteria `preserves`, since each
  witness exists and passes at base. Give the second its own witness, a
  second test in the same file. Give the policy no `witness:` patterns, so no
  constant mutant joins them. On the prototype, a version using the head tool
  only when every declared criterion miscounted drifted as
  `witness: tool 'pytest 9.1.1' -> None` here.
- In `tests/test_worktree.py`, use `_repo_with_a_file` and `_commit`
  (`tests/test_worktree.py:1397`, `:1136`). Pass
  `partial(worktree.source_mutated, "c")` as `mutate`.
- Import any name this spec adds inside the test body. A module-scope import
  makes `revert`'s reverted run a collection error.

**Every new test fails with the source reverted.** On the prototype, all six
witnesses failed with `saffron/` and `tests/mutation.py` reverted. Five
assert a `fail` the base gate reports as `skip`. At base, criterion 6's
comparison drifts as `witness: pass at baseline, skip at head`.

**Existing tests this changes.** A full suite run over the prototype failed
five, beside one `format` failure from its own unformatted tests. Two drive a
find absent from its file to show an unapplied mutant. Point each at a file
that does not exist instead, which stays unproven, and keep its name and
intent.

- `tests/test_witness_gate.py::test_a_mutant_that_did_not_apply_is_named_not_counted`
  (`tests/test_witness_gate.py:208`).
- `tests/test_gates.py::test_the_result_names_each_criterion_not_a_count`
  (`tests/test_gates.py:213`).

Three replace `runner.run_suite` with a fake that takes no `derived`
keyword, and `GateSuite._run` then raised `TypeError`. Give each fake the
keyword, defaulting to `()`, and make no other edit to them. All three then
passed on the prototype.

- `tests/test_session.py::test_a_cell_run_produces_a_witness_result`
  (`tests/test_session.py:11283`).
- `tests/test_session.py::test_a_cell_run_supplies_the_real_mutator`
  (`tests/test_session.py:11348`).
- `tests/test_session.py::test_a_skipped_witness_blocks_nothing_at_either_tier`
  (`tests/test_session.py:11460`).

`test_the_tree_is_unchanged_however_the_gate_ends` drives an absent find too
(`tests/test_witness_gate.py:196-204`). It asserts only the bytes, so it
still passes.

**Size.** The prototype measured 290 changed tokens by `size_gate`, against
the `bug` ceiling of 1300, without the `worktree.py` and `runner.py`
docstring edits. It measured 782 more under the test paths.
`estimated_lines` adds about 60 tokens for those docstrings to the measured
figure, over four.
