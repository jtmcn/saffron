---
id: SA-0404
title: "`saffron regate` never asks the killed wrong versions a review commit puts back in play"
type: feature
priority: 3
risk: standard
estimated_lines: 464
estimate_measured: true
depends_on: [SA-0403]
consumes:
  - saffron/parent_versions.py:own_version_pairs
  - saffron/regate.py:review_commit_diff
touches:
  - saffron/regate.py
  - tests/test_regate.py
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
  - saffron/parent_versions.py
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/commit_review.py
  - saffron/end_review.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/repos/**
  - saffron/task.py
  - saffron/cli.py
  - tests/test_parent_versions.py
  - tests/test_session.py
  - tests/test_cli.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 46
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      After `reverify`, `run_regate` asks the task's own chosen pairs and
      then each parent's in one `session._apply_criterion_probes` call. It
      reads `pushed_sha` from the task's row and passes it to
      `review_commit_diff` with the mirror, the baseline and `head`. It hands that
      diff to `own_version_pairs`, and to `parent_version_pairs` with the
      spec's `depends_on` and the export's `.saffron/specs`. The call's
      `CellSpec` holds the task's spec id and the baseline as `base_sha`.
      Its patch is `git diff` from the baseline to `head` with
      `--binary` and `--full-index` besides `DIFF_FLAGS`. Its gates are the
      exported policy's executables under `GATES_MOUNT`, and its
      `gates_dir` is the export. Its test paths, gate env and inert
      patterns are the exported policy's own. Its `gate_comparison` is
      the comparison `reverify` returned. The witness's task `SA-0005`
      depends on `SA-0003`. Its base commit holds both specs and a policy
      declaring `tests/**` as test paths, one inert pattern and one gate
      env entry. `main` then moves one commit. The packaged commit edits src/a.py, tests/test_w.py,
      tests/test_p.py and tests/test_x.py, and adds a binary file. The
      review commit edits tests/test_w.py and tests/test_p.py again.
      `main` then moves again, editing tests/test_m.py, which a declared
      witness names and the task never changes. The head merges `main`
      as GitHub's update branch does. So the baseline is `main`'s second
      head, not the task's `base_sha`. The checkout `saffron regate` is
      given is a transport clone of `main` alone, holding no commit of
      the task's branch. The own record kills two versions under a tests/test_w.py witness, the
      first killed again and the second surviving. It kills one under a
      second tests/test_w.py witness that the head's `tests` result does
      not collect. It kills one under a tests/test_x.py witness, and one
      under the tests/test_m.py witness, which that result collects. The
      parent's record kills three under a tests/test_p.py witness. They
      are one that survives, one the inert pattern refuses, and one under
      which the `tests` gate errors. The witness stubs the cell at
      `session.critic_cell`, `runner.run_gate`, `worktree.source_mutated`
      and `worktree.read_at_head`, so the real `_apply_criterion_probes`
      decides each outcome. It asserts exactly one cell is entered, with
      the spec id, the baseline as `tree_base`, the mirror, the export
      and the policy's gate env. It asserts the patch equals its own such diff. It
      asserts every `tests` gate executable is the one
      `gate_executables` maps under `GATES_MOUNT`. It asserts the edits applied, in
      order, are the own killed version, the own survivor twice, the
      parent survivor twice and the parent's errored version.
    witness: tests/test_regate.py::test_regate_asks_the_tasks_own_and_each_parents_killed_versions_in_one_probe_cell
    wrong_versions:
      - The `CellSpec` built on the task's own `base_sha`, so `tree_base` is not the baseline.
      - The review diff read from the task's `base_sha` rather than the baseline, so the tests/test_m.py version is applied.
      - The review diff read from the checkout rather than the mirror, so no pair is chosen and no cell is entered.
      - The patch read from `pushed_sha` to `head`, so it lacks src/a.py's packaged edit.
      - The patch read without `--binary`, so the binary file arrives as a stub.
      - The patch read without `--full-index`, so each `index` line is abbreviated.
      - The gates read from the host export rather than `GATES_MOUNT`, so the executable is a host path.
      - Own and parent pairs asked in two calls, so two cells are entered.
      - Parent pairs placed before the task's own, so the parent survivor is applied first.
      - The parents read from the export's root rather than its `.saffron/specs`, so no parent version is applied.
      - The gate env passed empty, so the cell's env lacks the declared entry.
      - The test paths passed empty, so every pair is refused and nothing is applied.
      - The inert patterns passed empty, so the inert version is applied.
      - A fresh comparison passed rather than `reverify`'s, so the uncollected witness's version is applied.
      - The reviews passed as an empty list, so the call raises before any cell is entered.
  - claim: >-
      `run_regate` prints one line for each chosen pair whose outcome is
      not `killed`, in pair order. The line begins `regate: <spec id> wrong
      version <outcome>: <version>`, and the entry's summary follows in
      parentheses. The spec id is the entry's `parent`
      key, the task's own id for its own pairs. Each `survived` pair adds
      one to the new-failure count. That count is the one `run_regate`
      prints in its last line and passes to `record_regate`. An
      `unproven` or `error` pair adds nothing. The witness reads criterion 1's fixture, with `reverify`
      returning one new failure. It asserts the text before ` (` of each
      line starting `regate: SA-` is exactly these, in order. They are
      `SA-0005`'s survivor and its uncollected version (`unproven`), then
      `SA-0003`'s survivor, its inert version (`unproven`) and its errored
      version (`error`). It asserts each such line ends `)`. It asserts
      the gate failure's own line, the last
      line's `3 new failures`, a recorded row naming `head` with
      `new_failures` 3, and exit 1.
    witness: tests/test_regate.py::test_regate_counts_each_surviving_wrong_version_as_a_new_failure_and_names_its_spec
    wrong_versions:
      - Survivors replacing the gate count, so the count is 2.
      - Survivors printed but not counted, so the count is 1.
      - The row recorded before the pairs are asked, so it holds 1.
      - Every pair that was not killed counted, so the count is 6.
      - A parent's survivor printed under the task's own id, so its line names `SA-0005`.
      - Only survivors printed, so the `unproven` and `error` lines are missing.
      - The line ending at the version, so no line ends `)`.
      - The pairs chosen from the baseline-to-head diff, so tests/test_x.py's version gets a line too.
  - claim: >-
      `run_regate` prints `regate: no wrong-version record read for <id>`
      for the task's own record when `own_version_pairs` reports it
      unreadable, and then for each parent `parent_version_pairs` names
      unread. Neither fails the re-gate, and either side's readable pairs
      are still asked. A survivor makes the exit 1 with no gate failure.
      With no pair to ask, no probe cell is entered. The
      witness reads criterion 1's fixture and invokes `saffron regate`
      four times, counting cells through one `session.critic_cell` stub.
      First the own record is broken JSON. The own line prints and the
      parent's does not, the parent survivor's line prints, one cell is
      entered and the exit is 1. Then the own record is restored and the parent's is
      deleted. The parent line prints and the own does not, the own
      survivor's line prints, a second cell is entered and the exit is 1.
      Then the own record is broken again. Both lines print, the own
      line first, no pair line prints, no
      cell is entered, the last line says `green` and the exit is 0.
      Last, both records are restored and the task's `pushed_sha` is
      recorded as `head`. No record line and no pair line print, no cell
      is entered, the exit is 0 and the recorded row holds 0.
    witness: tests/test_regate.py::test_regate_prints_each_record_it_cannot_read_and_enters_no_cell_without_a_pair
    wrong_versions:
      - The own record's line never printed, so the first and third invocations lack it.
      - The unread parent's line never printed, so the second and third invocations lack it.
      - An unreadable record counted as a new failure, so the third invocation exits 1.
      - The exit read from the gate failures alone, so the first invocation exits 0.
      - The parent lines printed before the own line, so the third invocation prints them out of order.
      - Any unreadable record ending the ask, so the first invocation enters no cell.
      - The pairs chosen from the baseline-to-head diff, so the last invocation enters a cell.
---

## Context

Backlog item **b-d9a027**, left by b-9efbe2. It cites `DESIGN.md` §5.4
and §5.5. `SA-0401` and `SA-0402` ask a parent's killed wrong versions in
REVIEW. A review commit reaches no REVIEW. In the spec loop's 70th pass a
review commit on #1202 rewrote `SA-0389`'s clause, and the spec's own
wrong version 8 then passed the witness. This spec is the second of two.
`SA-0403` chooses the pairs. This spec asks them from `saffron regate`.
Every line number below was read at `264299a4`, which carries
`SA-0403`'s spec but not its code.

**What `SA-0403` adds**. `parent_versions.own_version_pairs(*, spec,
out_dir, diff)` returns the task's own pairs and a boolean that is true
when its record could not be read. `regate.review_commit_diff(mirror,
pushed_sha, baseline_sha, head)` returns the diff the head's review
commits make, kept to the paths the baseline-to-head diff changes too. It
returns empty for a `pushed_sha` that is `None`, empty, forty zeros or on
no head. Both are `consumes` entries here. `parent_version_pairs` returns
each parent's pairs and the names it could not read
(`saffron/parent_versions.py:124`). Each pair's entry names its spec in
`parent` (`saffron/parent_versions.py:113`).

**What `run_regate` reads now**. `_TASK_ROW` selects no `pushed_sha`
(`saffron/regate.py:24-25`). The baseline is the merge base of the base
branch and `head` (`saffron/regate.py:146`). The export is read at the
task's `base_sha` (`saffron/regate.py:148`), and the policy from it
(`saffron/regate.py:168`). `reverify` returns the comparison
(`saffron/regate.py:180`). Each new failure prints, and the count is
their number (`saffron/regate.py:191-193`). `record_regate` stores it
(`saffron/regate.py:194`), and the exit is 1 for any
(`saffron/regate.py:201`). `saffron adopt` moves a task on only when the
row's `new_failures` is 0 (`saffron/cli.py:3282`). `reconcile` prints the
same count (`saffron/cli.py:3487`).

**What `_apply_criterion_probes` needs**. Its keywords are at
`saffron/cell/session.py:2076`. It refuses a pair before any cell when
`probe_refusal` refuses the edit's file (`saffron/cell/session.py:2122`).
`probe_refusal` refuses every file when no test path is declared
(`saffron/probe.py:166`). It refuses an inert edit after reading the edited
file through `mirror_ops.files_after`, at the tree base with the patch
applied (`saffron/cell/session.py:2144`). It reads the head's `tests` result
from `gate_comparison` (`saffron/cell/session.py:2172`). It needs an
`adequacy` review in `reviews` (`saffron/cell/session.py:2176`).
`critic_cell` builds its worktree at `spec.tree_base`
(`saffron/cell/session.py:1608`) and applies `patch` there
(`saffron/cell/session.py:1619`). `CellSpec.tree_base` is `base_sha`
when `stacked_on` is `None` (`saffron/cell/session.py:413`).
`gate_executables` maps each gate to `<dir>/.saffron/gates/<name>`
(`saffron/repos/policy.py:262`), and `GATES_MOUNT` is `/gates`
(`saffron/cell/worktree.py:25`). `DIFF_FLAGS` carries no `--binary`
(`saffron/cell/worktree.py:195`). A binary change then reaches
`_apply_and_commit_patch` as a stub it refuses
(`saffron/cell/session.py:1502-1503`).

**Why the private call is sound**. `session.py` imports no `regate`.
`spec_review.py` already calls `session._resets_at_fields`
(`saffron/spec_review.py:295`). `qualify.py` already builds a bare
`session.CellSpec` to ask probes host-side (`saffron/qualify.py:224`).
In the prototype, `regate.py` imported `session` at module scope and
`saffron.cli` still imported clean (measured).

## Problem

Wire the asking into `run_regate`, as the criteria state.

- Add `t.pushed_sha` to `_TASK_ROW`.
- After `reverify`, read `review_commit_diff`, then the task's own pairs
  and each parent's. Print each record line. With no pair, ask nothing.
- Otherwise build the patch with `git_mirror._git(..., strip=False)`, and
  a `CellSpec` from the spec. Pass `reviews=[review.LensReview(lens=
  "adequacy")]` and drop it afterwards. Pass a fresh `created` set and a
  `note` that prints `regate: <detail>`.
- Print each pair line after the call. Add the survivors to the count
  before `record_regate`, so `reconcile` reads the re-gate as failed.

No agent session runs and no token is read, as before.
`tests/test_regate.py:41`'s autouse fixture already makes an agent path
raise in every witness.

## Out of scope

- **A probe cell named like another**. With no network, `critic_cell`
  names its container `saffron-gate-<spec id>`
  (`saffron/cell/session.py:1579`). It removes any container of that name
  first. A cell of the same spec running at once collides with the
  re-gate's probe cell.
- **A patch the probe cell refuses**. `CriticPatchRejected` and
  `CriticPatchUnrepresentable` are not `CellRuntimeError`s
  (`saffron/cell/worktree.py:377`, `saffron/cell/worktree.py:397`). They
  leave `_apply_criterion_probes` and `run_regate` alike. The caller exits
  2 and no row is recorded. No witness drives it.
- **An `error` or `unproven` pair**. It prints and does not fail the
  re-gate. A probe cell that cannot be entered twice turns every pair
  `error`. The re-gate then records a green row and exits 0 with no
  version asked.
- **`saffron adopt`'s re-gate**. `adopt` records `head` as the pushed sha
  (`saffron/cli.py:3264`) before it calls `run_regate`
  (`saffron/cli.py:3268`). `review_commit_diff` is then empty, so that
  re-gate asks nothing.
- **The `note` callback**. It fires only when a removal leaves something
  behind. No witness drives it.
- **A record of the outcomes**. The re-gate writes no wrong-version file
  and files no finding. The survivor lines are its only record.
- **A second parent**. `parent_version_pairs` reads every `depends_on`
  entry (`saffron/parent_versions.py:124`). The witnesses' task names one
  parent, so no witness drives a second.
- **The line's summary**. Criterion 2's witness checks each line ends
  `)`, and no witness pins the summary's text.
- **`DIFF_FLAGS` in the patch**. The fixture holds no rename, so a patch
  read without `DIFF_FLAGS` equals the witness's own. No witness drives it.
- **What `reconcile` prints**. Its count includes survivors and names
  none.
- **A withdrawn parent survivor in REBUT**. That is `SA-0405`.
- **Which pairs are chosen**. That is `SA-0403`'s, and this spec forbids
  its files.
- **A `retired_first`**. This spec adds no refusal of a spec.
- **Hand edits, made in this spec's own pull request**. `DESIGN.md`
  §6.1's paragraph on `saffron regate` gains one sentence after the one
  ending `leaves the state alone.`

  > It also asks the task's own killed wrong versions and each parent's
  > of every witness a review commit edits. A survivor counts as a new
  > failure (`SA-0403`, `SA-0404`).

  `CONTEXT.md`'s Re-gate entry gains one sentence after the one ending
  `the count of new failures.`

  > A killed wrong version whose witness a review commit edits is asked
  > again, and a survivor counts as one new failure (`SA-0404`).

## Notes for the agent

**The behaviour is new code**, so each criterion declares a witness and no
mutant, and `witness` will report `skip`. Every witness drives
`cli.main`, so no witness imports a name this spec adds.

**The existing witnesses keep passing**. `_build_fixture`'s review commit
only merges `main`. Against `main` the review diff is empty. Against
`parent` it shares only `.saffron/policy.yaml`, and no spec there
declares a wrong version. So none of them asks a pair or enters a cell.

**The fixture needs four things the module lacks**. `_write_policy`
declares no test paths (`tests/test_regate.py:95-103`), and the new
policy must. `_fake_reverify` returns no `tests` result
(`tests/test_regate.py:333`), and the new fake must carry one that
collects every witness but one. A survivor needs `read_at_head` to return
text holding its edit's `find`, or its outcome turns `error`. Each
version's `replace` decides what the stubbed `tests` gate says under it.
`tests/test_session.py:15916` stubs the same four names. Criterion 3's
last step records the push through `_seeding_ledger`, as `_seed_task`'s
callers do, so the fold `saffron regate` reads holds it. The `types`
gate reads a stub's status as a `GateStatus`, so annotate it. A plain
`git clone` of a local path copies every object, so the checkout needs
`--no-local` to lack the task's branch (measured).

**The `prose` gate** counts each new comment and docstring from zero.
Write none with an em dash, a semicolon, a contraction, the perfect tense
or a sentence over 25 words. `run_regate`'s docstring sits at ten lines
already, so a line added there is a hit.

**Size**. A prototype on `SA-0403`'s diff changed 464 lines, 110 in
`saffron/regate.py` and 354 in `tests/test_regate.py`. The `size` gate
counts only the 247 changed tokens outside `tests/`.
