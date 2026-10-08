---
id: SA-0240
title: The PR body says every failure at head was at base, though an advisory gate's new failure was dropped before it counted
type: bug
priority: 2
depends_on: [SA-0225]
estimated_lines: 191
estimate_measured: true
touches:
  - saffron/gates/suite.py
  - saffron/report/pr_body.py
  - saffron/phases/package.py
  - tests/test_suite.py
  - tests/test_report.py
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
  - .github/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/gates/baseline.py
  - saffron/gates/contract.py
  - saffron/gates/core/**
  - saffron/cell/**
  - saffron/view/**
  - saffron/replay.py
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/events.py
  - saffron/task.py
  - tests/test_session.py
  - tests/test_replay.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 18
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      A suite comparison carries the new failures of every gate in its head
      run's `advisory_gates` as `advisory_failures`, apart from
      `new_failures`, which never holds them. They are counted against the
      baseline exactly as `new_failures` are. An aborted or drifted
      comparison carries none. The witness drives each of the three ways a
      gate is held advisory. They are a gate declared `blocking: false`,
      `size` at `standard` and `witness` at `standard`. It drives a
      blocking `tests` failure beside them, a baseline failure that cancels
      one of two identical head failures, a head elevated by `elevate_on`
      whose `size` failure blocks, and a drifted and an aborted head.
    witness: tests/test_suite.py::test_a_new_failure_in_an_advisory_gate_is_carried_apart_and_blocks_nothing
    wrong_versions:
      - The advisory failures are read off the head results with no baseline subtraction, so a failure present at base is carried too.
      - The advisory failures are a set difference against the baseline, so one baseline failure cancels both identical head failures.
      - The advisory set is read from the baseline run, so an elevated head's blocking `size` failure is carried as advisory too.
      - Only `size` failures are carried.
      - Only gates the policy declares non-blocking are carried, so `size` and `witness` are dropped.
      - The advisory failures stay in `new_failures` as well.
      - A drifted comparison carries the advisory failures it would have subtracted.
      - An aborted comparison carries the advisory gates' failures at head.
  - claim: >-
      The pull request body's new-failure section renders four
      arrangements, each exactly as the notes give it. With no new failure of
      either kind it is unchanged. With blocking new failures alone it is
      unchanged. With advisory new failures alone its heading and sentence
      name blocking gates only, and a section of its own lists the advisory
      ones. With both, that advisory section follows the blocking table. Each
      advisory row goes through `_cell` as a blocking row does, so a pipe is
      escaped, a newline becomes a space and an `@` mention is defused. The
      witness renders all four arrangements with an advisory message holding
      all three, and compares the whole span between the verification
      sentence and the gate table.
    witness: tests/test_report.py::test_the_new_failures_section_names_advisory_new_failures_apart_from_blocking_ones
    wrong_versions:
      - With advisory failures alone, the section keeps the sentence saying every failure at head was at base.
      - The advisory section renders only when there is no blocking new failure.
      - The advisory failures are added to the blocking table under its heading.
      - The advisory section renders before the blocking table.
      - An advisory row's message is written without the table-cell escape, so its pipe splits the row.
      - The arrangement with no new failure takes the blocking-gates-only wording.
      - The advisory row is built with a bare pipe replace and no `_cell`, so its newline and its mention reach the body.
  - claim: >-
      PACKAGE renders the body with the verifying suite's advisory new
      failures. A packaged head whose re-verification carries one new
      advisory `size` failure and no blocking one is `READY_FOR_REVIEW`, and
      its body lists that failure under the advisory heading and no longer
      says every failure at head was at base.
    witness: tests/test_package.py::test_a_packaged_body_names_the_verifying_suites_new_advisory_failure
    wrong_versions:
      - PACKAGE passes no advisory failures to the renderer, so the body keeps the old sentence.
      - PACKAGE passes the comparison's blocking `new_failures` as the advisory ones, which are empty here.
      - PACKAGE treats an advisory new failure as blocking and ends the task `MERGE_FAILED`.
      - PACKAGE reads the advisory failures off `comparison.run.results` with no subtraction, so the run's own `size` failure is listed instead.
      - PACKAGE appends `comparison.advisory_failures` to the positional blocking list, so the row renders under `### New failures`.
---

## Context

Backlog item **b-04a5d9**, which cites `DESIGN.md` §5.4 and §5.7. Line
numbers below were read at `958db033`.

**What the comparison keeps.** `_compare` returns early on an aborted or a
drifted head (`saffron/gates/suite.py:231-237`). Otherwise it builds
`new_failures` from `subtract_baseline` and keeps only gates outside the
head run's `advisory_gates` (`saffron/gates/suite.py:238-245`). The rest
are dropped. `SuiteComparison` has four fields, `run`, `aborted`, `drift`
and `new_failures` (`saffron/gates/suite.py:111-119`). `_advisory` builds
the advisory set three ways (`saffron/gates/suite.py:220-228`). A gate
declared `blocking: false` is advisory at every tier. `size` and `witness`
are advisory unless the tier is `elevated`.

**What the body says.** `_new_failures` prints a fixed sentence whenever
its list is empty (`saffron/report/pr_body.py:254-258`). The sentence says
every failure at head was already present at base. `render_pr_body` calls
it with `new_failures` alone (`saffron/report/pr_body.py:117`). The gate
table marks an advisory `fail` row `(advisory)`
(`saffron/report/pr_body.py:483-484`). `## Not covered` lists each such
gate after `Failed without blocking` (`saffron/report/pr_body.py:553-559`).
Neither says whether that failure was new.

**Where PACKAGE gets them.** `reverify` returns the verifying suite's
comparison (`saffron/phases/package.py:834`). Its run supplies the gate
table and the advisory set (`saffron/phases/package.py:843` and `:850`). A
blocking new failure there ends the task `MERGE_FAILED`
(`saffron/phases/package.py:851-871`). The body is rendered with the cell's
`outcome.new_failures` (`saffron/phases/package.py:883-886`).

**Measured on `SA-0140`** (#501), from the item. `size` failed at head
only, as advisory, at 1651 tokens over a 1300 ceiling. The body still said
every failure at head was at base.

## Problem

`_compare` drops a new failure in an advisory gate before the body sees
it. So the body's "no new failures" sentence is false whenever an advisory
gate failed at head and not at base.

The item accepts two fixes. Either the body names new advisory failures in
their own section, or the sentence says blocking gates only. This spec
takes the first, for the reason the notes give. Which gates block does not
change.

1. **The comparison.** Add `advisory_failures`, a tuple of `NewFailure`
   defaulting to empty, as the last field of `SuiteComparison`. In
   `_compare`, call `subtract_baseline` once. Split its result on the head
   run's `advisory_gates` into `new_failures` and `advisory_failures`.
   Leave both early returns as they are. Say in the class docstring that
   `advisory_failures` is not a fourth outcome and blocks nothing.
2. **The renderer.** Give `render_pr_body` a keyword `advisory_failures`,
   a sequence of `NewFailure` defaulting to empty. Pass it to
   `_new_failures`, which renders the four arrangements in the notes. Build
   both tables with one helper, so an advisory row is escaped by `_cell`
   exactly as a blocking row is.
3. **PACKAGE.** Pass `comparison.advisory_failures` to `render_pr_body`
   beside `outcome.new_failures`.

## Out of scope

- **Which gates block.** `_advisory`, `size_blocks` and `witness_blocking`
  stay as they are.
- **The repair loop and the events.** `saffron/cell/session.py` reads only
  `new_failures`, and an advisory failure is no reason to repair. No event
  gains a field.
- **`saffron replay`.** It builds its list with `subtract_baseline` and no
  advisory set (`saffron/replay.py:102`). It hands that whole list to
  `render_pr_body` as new failures (`saffron/replay.py:116-119`). It is v0
  only.
- **`## Not covered`.** Its "Failed without blocking" line stays keyed on
  status, new or not.
- **The `## Problem` extractor.** `SA-0225` renames `_problem` and edits
  its one caller (`saffron/report/pr_body.py:182` and `:187-210`). This
  spec changes neither hunk.

## Notes for the agent

**Why this arm.** Carrying the advisory failures through
`SuiteComparison` costs one field and a split of the `advisory_gates`
filter at `saffron/gates/suite.py:240-244`. On the prototype that was 6
added and 6 removed lines in `suite.py` and 1 added in `package.py`. The
renderer took 26 added and 11 removed lines. The other arm would leave a
new `size` failure unnamed anywhere in the body. The gate table's
`(advisory)` mark says nothing about base. The cost is small, so the body names them.

**Every criterion is new code.** The field, the keyword, the advisory
section and the call in PACKAGE do not exist at base. So each criterion
declares a witness and no mutant, and `witness` will report `skip` for
them. The wrong versions under each criterion are what its witness must
kill. Do not run them yourself.

**The four arrangements.** Each block below is the exact string
`_new_failures` returns. A row's cells are built exactly as the blocking
table builds them now (`saffron/report/pr_body.py:266-275`). The fixtures
are a blocking failure `NewFailure("tests", Failure(file="tests/test_a.py",
code="failed", message="assert 1 == 2"))`, and an advisory one shaped as
the `size` gate writes it (`saffron/gates/core/size.py:285-296`). That is
`NewFailure("size", Failure(file="", code="diff-too-large", message="1651
changed tokens | over 1300\nping @org"))`. Its pipe, newline and mention
prove `_cell`. In the row below, a zero-width space follows the `@`, written by
`neutralize`. It renders invisibly. Write it as the escape `\u200b` in the
expected string.

No new failure, unchanged from base:

```
### No new failures

Every failure at head was already present at base.
```

Blocking new failures alone, unchanged from base:

```
### New failures

| gate | where | code | message |
|---|---|---|---|
| `tests` | tests/test_a.py | `failed` | assert 1 == 2 |
```

Advisory new failures alone:

```
### No new blocking failures

Every failure at head in a blocking gate was already present at base.

### New advisory failures

New at head, in gates held advisory at this risk tier, so none blocks.

| gate | where | code | message |
|---|---|---|---|
| `size` |  | `diff-too-large` | 1651 changed tokens \| over 1300 ping @​org |
```

Both: the blocking block above, one empty line, then the advisory section
from `### New advisory failures` on. Each block ends in one newline.

**Criterion 1's witness.** Write it in `tests/test_suite.py` with the
file's `_Tree`, `_WitnessTree`, `_suite`, `_lint` and `_WITNESS`. Five
legs, in one test.

- A policy with `lint` declared `blocking: false`. The baseline's `lint`
  fails once on `a.py`. The head's `lint` fails twice on `a.py` and once on
  `b.py`, and its `tests` fails once. `new_failures` is that `tests`
  failure alone. `advisory_failures` is `lint` on `a.py`, then on `b.py`.
- `size` at `standard`. A head whose patch adds more lines than the
  `feature` ceiling under `src/`, as
  `test_the_head_runs_tier_decides_what_blocks_not_the_baselines` builds
  one. `new_failures` is empty and `advisory_failures` is one `size`
  failure coded `diff-too-large`.
- The same patch under `infra/` with `elevate_on: ["infra/**"]`.
  `new_failures` is that `size` failure and `advisory_failures` is empty.
- `witness` at `standard`. A spec whose one criterion declares a mutant
  and `preserves=True`, as the file's witness test builds it
  (`tests/test_suite.py:277-282`). Without it the witness gate judges the
  criterion green at base. Run it on a `_WitnessTree` with `killed=False` at both sides. `new_failures` is
  empty and `advisory_failures` is one `witness` failure coded
  `survived-mutant`.
- The `lint` policy again, with an advisory `lint` failure at head. Its
  `tests` is `skip` in one head and broken (`None`) in another. Each is
  drifted or aborted, and `advisory_failures` is empty.

**Criterion 2's witness.** Render each arrangement with `render_pr_body`
and the file's `SPEC`, one passing `lint` result and `advisory_failures`
given. Take the text after the sentence under `## Verification` and before
`### Gates`. Compare it with `==` to the arrangement's block plus one
newline, the separator `render_pr_body` adds.

**Criterion 3's witness.** Use the `packageable` fixture. Patch
`saffron.phases.package.reverify` to return a `SuiteComparison`. Its run
holds one `size` result at `fail`, with `size` in its advisory set. That
result carries its own failure, with a message other than the advisory
one. Its `advisory_failures` holds one `size` failure, and its
`new_failures` is empty. Build the comparison inside the test, since
`_reverified` takes no advisory failures. Then read `pr_body.md` as
`test_a_re_verified_body_marks_the_verifying_suites_advisory_gates` does.
Assert the advisory row is there and the run's own message is not. Assert `### New advisory failures` comes before the row, and that
`### New failures` is absent.

**Two limits, both accepted.** A `witness` failure coded
`survived-mutant` is never cancelled by the baseline
(`saffron/gates/baseline.py:24-31`). So at `standard` a survivor present at
base is listed under the advisory heading as new, as §5.4.1 counts it. In
PACKAGE the blocking list stays the cell's `outcome.new_failures`
(`saffron/phases/package.py:886`). A blocking failure in re-verification
ends the task `MERGE_FAILED` first (`saffron/phases/package.py:851-871`),
so PACKAGE never renders the arrangement with both.

**Tests already in the files stay as they are.** Every arrangement but
the advisory ones renders as at base, so no existing assertion changes.

**Docstrings.** `render_pr_body`'s docstring is past the ten-line limit
already. A longer one is a new `prose` hit, measured on the prototype. So
leave it as it is and describe the keyword in `_new_failures`'s docstring.

**Measured on a prototype over `958db033`.** The diff was 762 changed
tokens by the `size` gate's counter, against the `bug` ceiling of 1300.
`tests/test_suite.py`, `tests/test_report.py`, `tests/test_package.py`,
`tests/test_replay.py` and `tests/test_session.py` passed, 515 tests.
Each of the three witnesses failed with the source reverted. Each of the
19 wrong versions above, applied as an edit, failed its own witness on an
assertion. The prose limit counted no new hit in any of the six files.

Commit after each witness passes. Uncommitted work dies with the cell.
