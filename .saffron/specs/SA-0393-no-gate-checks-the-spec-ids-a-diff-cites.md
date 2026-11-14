---
id: SA-0393
title: "No gate checks the spec ids a diff cites, so a cell can cite a spec that does not exist"
type: feature
priority: 3
risk: elevated
estimated_lines: 294
estimate_measured: true
touches:
  - saffron/gates/core/integrity.py
  - saffron/gates/suite.py
  - saffron/cell/worktree.py
  - saffron/intake.py
  - tests/test_integrity.py
  - tests/test_worktree.py
  - tests/test_suite.py
  - tests/test_constant_mutants.py
  - tests/test_package.py
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
  - saffron/gates/core/census.py
  - saffron/gates/core/revert.py
  - saffron/gates/core/scope.py
  - saffron/gates/core/size.py
  - saffron/gates/contract.py
  - saffron/gates/runner.py
  - saffron/gates/baseline.py
  - saffron/cell/session.py
  - saffron/phases/**
  - saffron/report/**
  - saffron/finish.py
  - saffron/follow_up.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/cli.py
  - tests/test_finish.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      `integrity_gate` takes the task's spec id and the paths of its spec
      files as two keywords. It fails each id an added line cites that is
      neither the task's own id nor the id of a spec file it was handed. Each
      such id is its own failure. It carries the diff's file and the line's
      number in the post-image, and its message names the id. A spec file is
      a path whose name ends `.md` and starts with the task's prefix, `-`
      and digits, and its id is that start with the digits taken whole. The
      witness drives one diff with two hunks. It cites the own id, a queued
      spec's id and a retired spec's id, which pass. It cites an unknown id,
      a short id that a spec file's name starts with, the id of a `.txt`
      file in the list, and two unknown ids on one line, which fail. A
      context line and a removed line each carry an unknown id, and neither
      fails. A `README.md` and a `done` entry in the list name no id. It
      asserts the exact list of file, line and ids-named triples.
    witness: tests/test_integrity.py::test_an_added_line_citing_an_id_no_spec_file_holds_fails_at_its_file_and_line
    wrong_versions:
      - A scan that also reads context lines, so an id the diff left alone fails.
      - A scan that also reads removed lines, so an id the diff took out fails.
      - A spec file's id matched by prefix or substring of its name, so a short id such as `SA-000` resolves against `SA-0005-queued.md`.
      - A spec file counted whatever its extension, so an id whose only file is `.txt` resolves.
      - The task's own id left out of the known set, so the task citing itself fails.
      - One failure per line rather than per id, so the second unknown id on a line goes unreported.
      - The failure's line taken from the hunk header rather than counted, so the second hunk's line is wrong.
      - A failure whose message omits the id.
  - claim: >-
      A cited id is the task's prefix, `-` and a string of digits taken whole,
      matched case-sensitively. It is judged unless the character before it
      is a letter, a digit, `_`, `-`, a double or single quote, or `/`. It
      is also not judged when the text after it starts with a letter, a
      digit, `_`, `-`, or a `.` followed by a letter, a digit or `_`. So a
      quoted fixture value and a file name are not citations. The witness
      drives seven judged spellings and twelve left alone, one per line,
      with one spec file `SA-0398` known. Judged, each failing: `SA-03981`,
      the unpadded `SA-398`, and `SA-0399` in parentheses, in backticks, at
      a sentence's end before `.`, before `:`, and in a list beside the
      known `SA-0398`. Left alone: `SA-0399` after a letter, a digit, `_`,
      `-`, a double quote, a single quote and `/`, then before `-slug.md`,
      `.yaml`, a letter and `_`, and the lowercase `sa-0399`. It asserts
      the exact list of failing lines and the id each names.
    witness: tests/test_integrity.py::test_a_cited_id_is_bounded_so_fixture_values_and_file_names_are_not_citations
    wrong_versions:
      - A match bounded by the regex word boundary alone, so `"SA-0399"`, `SA-0399.yaml` and `SA-0399-slug.md` fail.
      - A match taking exactly four digits, so `SA-03981` is read as `SA-0398` and passes.
      - A right bound that refuses only a following digit, so `SA-0399x` and `SA-0399_` fail.
      - A right bound that refuses any following `.`, so `SA-0399.` at a sentence's end passes.
      - A left bound that refuses only a letter, so `9SA-0399`, `_SA-0399` and `/SA-0399` fail.
      - A case-insensitive match, so `sa-0399` fails.
      - Ids compared after stripping leading zeros, so `SA-398` resolves against `SA-0398`.
  - claim: >-
      Only ids of the task's own prefix are judged, the prefix being the
      part of its spec id before the last `-`. One diff is judged three
      times, with spec files `SY-2` and `B2-10` known. Task `SY-7` fails only
      `SY-9` and leaves `SY-2`, `SA-0398`, the lowercase `sy-9` and the `B2`
      ids alone. Task `B2-3` fails only `B2-11`, a prefix holding a digit.
      Task `SA-0007` fails only `SA-0398` and leaves every `SY` and `B2` id
      alone.
    witness: tests/test_integrity.py::test_only_ids_of_the_tasks_own_prefix_are_judged
    wrong_versions:
      - A prefix fixed to `SA`, so task `SY-7` passes `SY-9`.
      - A prefix pattern of letters only, so task `B2-3` judges nothing.
      - Every prefix judged, so task `SA-0007` fails `SY-9`.
  - claim: >-
      The gate suite hands `integrity_gate` the spec's own id and the paths
      `CellTree` lists directly in `.saffron/specs/` and in
      `.saffron/specs/done/` at the worktree's HEAD. The witness drives a
      real git repo through `CellTree`, with baselines taken at the base
      commit. Its head commit adds one spec file, deletes another, and adds
      lines citing seven ids. A `CellSpec` and an `intake.Spec`, both
      `SA-0007`, each yield exactly three new `integrity` failures. They
      fall on the deleted spec's id, on an id whose file lies in a nested
      directory under `.saffron/specs/`, and on one whose file lies outside
      it. The retired, queued, added and own ids pass.
    witness: tests/test_worktree.py::test_the_suite_judges_cited_ids_against_the_spec_files_at_head
    wrong_versions:
      - The listing read at the diff base rather than HEAD, so the added spec's id fails and the deleted one's passes.
      - A recursive listing of `.saffron/specs/`, so the nested file's id resolves.
      - A listing of `.saffron/specs/` alone, so the retired spec's id fails.
      - The suite passing no spec id, so `integrity` judges nothing.
      - The suite reading `intake.Spec`'s `id` and `CellSpec`'s `spec_id` by two paths, so one spec type passes no id.
---

## Context

Backlog item **b-249808**, filed from the spec loop's run 53. It cites
`DESIGN.md` §5.4. Every line number below was read at `dffa5474`.

**Twice so far**. In the spec loop's run 53, `SA-0330`'s cell cited `SA-0332` at 20
sites in seven files, and `SA-0330` at none. `SA-0332` was a different
draft. Every gate passed it, and a review commit on its pull request
fixed it. In the spec loop's run 70 on 2026-11-14, `SA-0389`'s cell wrote `SA-0398` in a
witness docstring in `tests/test_revert.py`. No spec `SA-0398` exists.
Both review seats found it, and a review commit on that pull request fixed
it.

**What a fixture looks like, measured**. The 80 newest `saffron SA-NNNN:`
cell commits before `dffa5474` were read. 15 add an `SA-` id that no spec
file at `dffa5474` names, other than their own. Two are the cases above.
The other 13 add only fixtures and examples, such as `"SA-9001"`,
`f"{first}:SA-1.yaml"` and `SA-0400.yaml`. `SA-0330` adds fixtures too,
beside its defect. The second criterion's bounds were applied to the same
added lines in all 80. They hit nothing but `SA-0389`'s one site and
`SA-0330`'s 20. The known set was today's spec files, so an id
cited before its spec was filed is undercounted.

**Where it lives: `integrity`, not a new gate**. `integrity_gate`
(`saffron/gates/core/integrity.py:201`) already walks every added line
with its post-image number. Its suppression scan skips every line whose
kind is not `+`, and reports `file` and `line` (`saffron/gates/core/integrity.py:262-276`). A
new gate would need a vocabulary entry in `ontology/factory.ttl` and a
blocking level in `factory:CoreGateBlockingShape`. It would also need a new
place in the suite's fixed order, which
`tests/test_suite.py::test_the_core_gates_run_around_the_declared_ones_in_a_fixed_order`
pins. The rule is a question about diff text, like the two `integrity`
already asks, so it joins them.

**What the gate is handed today**. The suite calls
`integrity_gate(diff, policy.integrity, spec.touches)`
(`saffron/gates/suite.py:216`). It skips when the repo declares neither
suppressions nor gate config (`saffron/gates/core/integrity.py:211-216`).
`SuiteSpec` names no id (`saffron/gates/suite.py:40-54`). `CellSpec`
carries one as `spec_id` (`saffron/cell/session.py:352`). `intake.Spec`
carries it as `id` (`saffron/intake.py:240`), and PACKAGE builds the
suite with one (`saffron/phases/package.py:559-566`). `intake.Spec`
already exposes `type` under the suite's name `spec_type`
(`saffron/intake.py:293-296`).

**What the tree can say**. `Tree` reads the worktree through
`changed_files`, `patch` and `dirty_paths` (`saffron/gates/suite.py:57-70`).
`CellTree` answers each through `saffron/cell/worktree.py`
(`saffron/gates/suite.py:74-98`). There, `changed_files` runs git in the
cell and raises `CellRuntimeError` on a non-zero exit
(`saffron/cell/worktree.py:827-836`). The patch is
`base..HEAD`, so HEAD is the tree it ends at
(`saffron/cell/worktree.py:344-374`).

**How a spec file's id is read elsewhere**. `next_spec_id` reads each
`*.md` name in `.saffron/specs/` and its `done/` against
`^{prefix}-([0-9]+)` (`saffron/follow_up.py:109-118`). `done` is
`RETIRED_DIRNAME` (`saffron/scheduler.py:628`).

**The finishing layer**. Its suite runs under the spec `FINISH-0`
(`saffron/finish.py:110-115`). Its prefix is `FINISH`, so no `SA-` id in a
finishing commit is judged.

## Problem

Give `integrity_gate` two keyword-only parameters: the task's spec id,
defaulting to none, and the paths of its spec files, defaulting to empty.
With no spec id the gate behaves as at base. With one, it reads every added
line for ids of the task's prefix. It fails each that is neither the task's
id nor a spec file's id. A failure carries the file and the post-image line
number, and its message names the id. Leave the early skip
(`saffron/gates/core/integrity.py:211`) as it is.

Bound a match as the second criterion says. A quote or `/` before an id,
or a `-` or a file extension after it, marks a fixture value or a file
name. A backtick, a parenthesis, a space or a line's start marks a
citation.

Read each spec file's id from its name as `next_spec_id` does, with the
digits taken whole, so `SA-0398-x.md` is `SA-0398` and never `SA-039`.
Compare ids as whole strings.

Add `spec_id` to `SuiteSpec`, and give `intake.Spec` a `spec_id`
property returning its `id`, beside `spec_type`. Add a method to `Tree`
listing the paths directly in `.saffron/specs/` and `.saffron/specs/done/`
at HEAD. `CellTree` answers it through a new function in
`saffron/cell/worktree.py`. It runs `git ls-tree` over HEAD in the cell, and
raises `CellRuntimeError` on a non-zero exit as `changed_files` does. Hand
both to `integrity_gate` from `GateSuite._run`. The baseline call hands them
too, and at the base the diff is empty, so it fails nothing.

Update `integrity.py`'s module docstring and `integrity_gate`'s docstring
to name the third question. Give the test trees the listing method. They are
`_Tree` (`tests/test_suite.py:21`) and `_GitTree`
(`tests/test_constant_mutants.py:54`). Give each file's `_Spec` a
`spec_id` (`tests/test_suite.py:101`, `tests/test_constant_mutants.py:90`).
An empty listing and the id `SA-0001` keep every existing verdict there.

Stub the new `worktree` function beside `dirty_paths` wherever a test
stubs that one and still drives a `CellTree`. Otherwise the listing
reaches the cell runtime. A prototype found four such sites. One is in
`_stub_the_runtime` (`tests/test_session.py:1379`), and three are in
`tests/test_package.py`. They sit in `_stub_package_cells`
(`tests/test_package.py:262`), in
`test_two_reverify_runs_at_once_hold_disjoint_networks_and_neither_removes_the_other`
(`tests/test_package.py:378`) and in
`test_reverification_runs_the_same_suite_shape_the_session_ran`
(`tests/test_package.py:3414`). Without them, seven
`tests/test_package.py` tests shell out to the runtime and fail. So does
`tests/test_session.py::test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs`,
whose exact list of gate-cell commands gains the listing.

## Out of scope

- **A citation the bounds leave alone**. An id right after a quote is not
  judged, so a docstring that opens `"""SA-0398` passes.
- **A fixture the bounds judge**. An id in a YAML fixture inside a string,
  such as `id: SA-9001`, is judged and fails. A cell repairs that by quoting
  the value or by using a spec that exists.
- **A repo that declares no integrity patterns**. The gate still skips
  there, so its cited ids are not judged. A prototype that applied the check
  past the skip turned eight more tests in `tests/test_session.py` red. Each
  pins `integrity`'s `skip` under a policy with no patterns. This repo declares
  both lists.
- **A spec file left uncommitted**. The listing reads HEAD, the tree the
  patch ends at, and `committed` already fails a dirty tree.
- **An id the ledger knows but no spec file holds**, such as a refused
  follow-up's. It fails, as the item asks.
- **Hand edits, made in the spec's own pull request**. `DESIGN.md` §2.1's
  table row for `integrity` names the third question. §5.4's `integrity`
  paragraph says it fails an added line citing an unknown spec id. Such an
  id has the task's prefix, and is neither the task's own nor a spec file's
  at head.

## Notes for the agent

**Every criterion is new code**, so each declares a witness and no
mutant, and `witness` will report `skip`. The keywords, the bounds and the
listing do not exist at base. Their spelling is yours.

**At base each witness fails in its body**. The three `integrity` witnesses
call `integrity_gate` with keywords it lacks, so each raises `TypeError`.
The suite witness finds no `integrity` failure, because nothing at base
reads a cited id. No witness imports a name the change adds at module
scope.

**The `integrity` witnesses** build their diffs with `_repo` and `_diff`
(`tests/test_integrity.py:23`, `:37`). Read each failure as its file, its
line, and the ids its message names, found with a regex for the prefix.
Compare the whole sorted list against a literal, so a missing or an extra
failure both fail. Give the first witness about twenty lines, with its
second hunk far enough down that a hunk-header line number is wrong. Put
the context line's id within three lines of a change, or no hunk carries
it and the member drives nothing. A prototype placed it five lines away,
and a scan reading context lines passed.

**The suite witness** belongs in `tests/test_worktree.py`, beside
`_host_git` (`tests/test_worktree.py:1191`) and `_commit` (`:1207`).
`_host_git` points `worktree.runtime.exec_` at a real repo, so `CellTree`
reaches real git. Take each baseline before the head commit exists. A
baseline taken at HEAD already holds the head's failures and cancels them.
Use `gates={}` and a `Policy` declaring one suppression token, since a
policy with none skips `integrity`. Pick a token no line in the diff holds.
Avoid this repo's own tokens too, since its `integrity` scan reads the
test file. Import `CellSpec`, `CellTree`, `GateSuite` and `parse_spec` inside the
test.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. A docstring stays within ten lines.

**Size**. A prototype measured 294 changed lines, its docstring updates
and test stubs included. `size_gate` counted 352 tokens outside `tests/`
against the `feature` ceiling of 3000, with 589 more under the test paths.
