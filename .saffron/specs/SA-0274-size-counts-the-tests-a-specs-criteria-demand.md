---
id: SA-0274
title: The `size` gate counts the tests a spec's criteria demand against the same ceiling as its source
type: feature
priority: 2
depends_on: [SA-0273]
estimated_lines: 160
estimate_measured: true
touches:
  - saffron/gates/core/size.py
  - saffron/gates/suite.py
  - tests/test_size.py
  - tests/test_suite.py
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
  - saffron/agents/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/contract.py
  - saffron/gates/runner.py
  - saffron/gates/core/integrity.py
  - saffron/gates/core/scope.py
  - saffron/gates/core/revert.py
  - saffron/spec_review.py
  - tests/test_artifacts.py
  - tests/test_session.py
  - tests/test_spec_loop_driver.py
  - tests/test_scheduler.py
budget_usd: 22
max_attempts: 3
max_turns: 130
risk: elevated
acceptance:
  - claim: >-
      `size_gate` takes the repo's declared test paths, and a file whose
      path matches any one of them adds nothing to the count. The verdict,
      the pass summary, the fail summary and the failure message all use the
      count without them. When files under a test path carried tokens, the
      summary names how many tokens they carried. When none did, the pass and
      fail summaries are exactly what they are today, with a rewrapped test
      file that carries none. An estimated file under a test path is not
      named as estimated. A file hidden as binary under a test path and
      inside `touches` is refused or named exactly as today: `error` where
      the gate blocks, and named in the pass summary where it does not. The
      witness declares two globs, tests/** and *_test.go, and changes six
      files. It counts src/a.py, pkg/a_test.go
      and src/tests/util.py. It leaves out tests/unit/test_a.py, a_test.go
      and a tests/shared.py past the token-diff bound. A diff over the `bug`
      ceiling only with its test file passes with the paths declared and
      fails without them. One over it on source alone fails, and its fail
      summary and failure message both start with the source count.
    witness: tests/test_size.py::test_files_under_the_declared_test_paths_are_left_out_of_the_count
    wrong_versions:
      - The paths matched with `fnmatch`, whose `*` crosses a slash, so pkg/a_test.go is left out.
      - A pattern's text before its first `*` matched as a substring of the path, so src/tests/util.py is left out.
      - Only the first declared pattern read, so a_test.go is counted.
      - The verdict judged on the whole count while the summary prints the reduced one.
      - The failure message built from the whole count.
      - The fail summary built from the whole count.
      - The test-path note added to the pass summary alone, so the fail summary lacks it.
      - The test-path note printed when no test path changed, so the summary with nothing under a test path carries it.
      - The estimated-file note built from every file, so tests/shared.py is named.
      - The test-path note printed when any test-path file changed, so a rewrapped test file that carries no tokens adds it.
      - The fail summary carrying a zero test-path note when no test path carried tokens.
      - The unreadable paths filtered by the test paths, so a binary under tests/ is neither refused where the gate blocks nor named where it does not.
      - The test paths accepted and never read.
  - claim: >-
      The gate suite hands `size_gate` the test paths `policy.integrity`
      declares, the list it already hands `revert`. The witness runs a
      suite at `elevated` over a diff whose source is under the `feature`
      ceiling and whose test file takes it over. With tests/** declared,
      `size` passes and its summary starts with the source's count. With no
      test paths declared, the same diff is a blocking `size` new failure.
    witness: tests/test_suite.py::test_the_suite_leaves_the_policys_test_paths_out_of_size
    wrong_versions:
      - The suite hands `size_gate` the spec's `touches` as its test paths.
      - The suite hands `size_gate` no test paths, as at base.
---

## Context

Backlog item **40**, the second half of its finding. It cites `DESIGN.md`
§5.4. Every line number below was read at `bc879e2c`.

**`size` counts every changed file.** `size_gate` takes a diff, a spec
type and `touches` (`saffron/gates/core/size.py:202-204`). It looks up the
type's ceiling and sums `_changed_lines` over the whole diff
(`:259-260`). `_changed_lines` adds up every file block's count with no
filter on its path (`:155-158`). The ceilings are 1300 tokens for `bug`,
3000 for `feature` and 4200 for `refactor` (`:26`).

**A repo already declares its test paths.** `IntegrityPatterns` carries a
`test_paths` list, empty by default (`saffron/repos/policy.py:61`). This
repo declares `["tests/**"]` (`.saffron/policy.yaml:71`). The gate suite
already hands that list to `revert_gate` (`saffron/gates/suite.py:168-173`).
That gate tells source from test by matching each changed path against
the list (`saffron/gates/core/revert.py:166-168`).
The suite calls `size_gate` with the diff, the spec's type and its
`touches` alone (`saffron/gates/suite.py:199-201`).

**What the item found.** `SA-0029` left its cell at 548 changed lines and
merged at 863. `SA-0080` left at 294 against a `bug`'s 300 and merged at
367. Most of the growth in both was tests that review commits added. A
spec whose criteria demand tests is charged for writing them. At
`bc879e2c`, 71 merge commits on `main`'s first parent merge a
`saffron/SA-` branch. Measured with `size`'s own counter, a median
62% of each one's changed tokens are under `tests/**`, and 60% over all 71.

**One test pins today's summary.** `test_size_counts_a_branch_against_the_gates_own_ceiling`
asserts the summary `1 changed tokens within the <type> ceiling of <n>`
exactly (`tests/test_spec_loop_driver.py:175-186`). It reaches `size_gate`
through `driver._size`, which passes no test paths
(`.claude/skills/run-saffron-spec-loop/driver.py:655-658`).

## Problem

Leave the repo's declared test paths out of what `size` counts.

1. **`size_gate`** takes a keyword argument carrying the declared test
   paths. It defaults to an empty sequence, under which every file counts
   as it does today. Match each file block's path against each pattern
   with `scope.matches`, the function `revert` uses. A block that matches
   any pattern adds nothing to the count. The verdict, both summaries and
   the failure message use that count.
2. **Name what was left out.** The summary's caveat names the tokens the
   blocks under a test path carried. It sits beside the notes for an
   unreadable or estimated file. With no such tokens, add no note. An
   estimated block under a test path is left out of the estimated-file
   note as well.
3. **The suite** passes `policy.integrity.test_paths` to `size_gate`, as it
   does for `revert_gate`.

## Out of scope

- **Re-running gates on the branch after review commits.** That is the
  first half of item 40, and it folds into item 97 and `SA-0275`.
- **The ceilings.** They stay at 1300, 3000 and 4200. They were set
  against diffs that counted tests (`saffron/gates/core/size.py:24-25`).
  Of the 71 merges above, 27 are over 3000 tokens whole and 5 are over it
  without `tests/**`. Re-setting them is the operator's decision.
- **The plan checkpoint.** `judge_estimate` prices the plan's whole
  `estimated_lines` against the ceiling (`saffron/agents/artifacts.py:315`).
  The plan prompt asks for lines across the whole diff
  (`saffron/agents/prompts/implement.md:26-32`). At `elevated` a plan
  whose tests take it over the ceiling is still refused. Backlog item
  **b-15db6e** owns it, and `saffron/agents/**` is forbidden here.
- **Refusing or naming an unreadable file differently.** Criterion 1
  holds both as today under a test path. Its content stays uncounted.
- **`driver.py`.** Its `_size` and its `check` pricing keep counting every
  line. `.claude/**` changes by hand.
- **`DESIGN.md`.** §5.4's `size` row is edited by hand with this spec.

## Notes for the agent

**Both criteria are new code**, so each declares a witness and no mutant,
and `witness` will report `skip`. The exclusion does not exist at base.
The suite's new keyword argument would read the same text as the
`revert_gate` call's at `saffron/gates/suite.py:168-173`. A mutant's
`find` must match exactly once (§5.4.1), and that text would match twice.

**At base both witnesses fail.** Criterion 1's witness passes a keyword
`size_gate` does not take, so it raises `TypeError` in the test body.
Criterion 2's elevated suite reports `size` as a new failure. Neither
witness imports a name the change adds at module scope.
`IntegrityPatterns` exists at base. Import it in `tests/test_suite.py`
beside `Policy`.

**Criterion 1's witness.** Build each file with `_diff(added=n,
removed=0, path=...)` (`tests/test_size.py:14`). Use distinct counts, so a
sum names its members: 11, 13 and 17 counted, 19 and 23 left out. Build
the past-bound file with `_one_hunk` (`tests/test_size.py:171`), the
32,000 reversed tokens behind `FIRST` and `LAST` that
`test_a_file_past_the_token_diff_bound_is_estimated_from_its_changed_lines`
uses. It is estimated at 8 tokens. So the counted total is 41 and the
left-out total is 50. Assert the summary starts with
`41 changed tokens within the bug ceiling` and carries the 50. Assert
`tests/shared.py` appears nowhere in it. Build a rewrapped test file with
`_one_hunk(["-a b c d", "+a b", "+c d"], path=...)` under `tests/`. It
carries no tokens. Then assert `src/a.py` beside it, with the paths
declared, has the exact summary
`11 changed tokens within the bug ceiling of 1300`. For the verdict, take
the `bug` ceiling from `_CEILINGS`. A source file at the ceiling less 10
beside a 100-token test file passes declared and fails undeclared. A
source file at the ceiling plus 1 beside it fails declared. Assert its
failure message and its summary both start with the ceiling plus 1, and
that its summary carries the 100. Last, a source file at the ceiling plus 1
beside the rewrapped test file fails declared. Assert its summary equals
the fail summary today's tests pin, with no note. Then add a
`Binary files /dev/null and b/tests/logo.png differ` block, written by hand
under its `diff --git` header, beside `src/a.py`. Pass `touches` holding
`src/**` and `tests/**`. Assert `error` naming the path with
`blocking=True`. With `blocking=False`, assert `pass` and a summary
carrying `tests/logo.png unreadable, not counted`.

**Criterion 2's witness.** `_Tree` (`tests/test_suite.py:21`) returns
`""` from `patch` by default. Every `size` result passes on that, so a
suite handing `size_gate` nothing passes the declared leg. The undeclared
leg is what kills it. `_Spec`'s default `touches` is `src/**` and
`infra/**` (`tests/test_suite.py:103`). Add `tests/**` to it, or `scope`
fails the test file and the declared leg has a new failure for another
reason. The source count assertion kills a suite handing over `touches`,
which would leave `infra/x.tf` out and count 0. Elevate the run with
`elevate_on=["infra/**"]`, as
`test_the_head_runs_tier_decides_what_blocks_not_the_baselines` does.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. `size_gate`'s docstring is already past ten lines,
so every line it grows is a new hit. Put any reason in a one-line comment.

**`saffron/gates/**` is in `elevate_on`,** so this task runs `elevated`
and `size` blocks.

**Size.** A prototype held both witnesses, the `size_gate` change and the
suite's one argument. It measured 616 changed tokens with `size_gate`,
counting its tests, against the `feature` ceiling of 3000. With
`tests/**` left out it measured 72. `estimated_lines` is 616 over four,
plus a margin for one docstring sentence.
