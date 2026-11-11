---
id: SA-0375
title: REVIEW records no diff, so the finish cannot rebuild the tree its lenses cited
type: bug
priority: 2
estimated_lines: 13
estimate_measured: true
touches:
  - saffron/cell/session.py
  - tests/test_session.py
  - tests/test_events.py
  - tests/fixtures/watch-golden.txt
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
  - saffron/qualify.py
  - saffron/finish.py
  - saffron/end_review.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/cell/worktree.py
  - tests/test_qualify.py
  - tests/test_finish.py
  - tests/test_task.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
budget_usd: 40
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      A task whose critic cell applies the patch writes `reviewed-diff.json`
      in its task directory. It is a JSON object with three keys. `raw` is
      the critic cell's own export, the diff every lens session was handed.
      `sha256` is the hex sha256 of `raw` encoded as UTF-8, and `tree_base`
      is the spec's `tree_base`. A REVIEW phase line names the full
      64-character `sha256`. The witness drives a stacked spec whose
      `tree_base` differs from its `base_sha`. Its implementer's export, the
      critic cell's export and the export after the rebuttal are three
      different diffs, and the critic cell's holds a character outside
      ASCII. REBUT moves HEAD, and `patch.diff` then holds the
      post-rebuttal export while the record still holds the critic cell's.
      The witness also checks that each lens prompt holds `raw`.
    witness: tests/test_session.py::test_review_records_the_diff_its_lenses_read_with_its_hash_and_tree_base
    wrong_versions:
      - The implementer's export, `patch_to_review`, recorded instead of the critic cell's.
      - The record rewritten after REBUT with the post-rebuttal export.
      - "`tree_base` written as the spec's `base_sha`."
      - The sha256 taken over something other than `raw`, such as `tree_base` joined to it.
      - The sha256 taken over `raw` encoded as Latin-1.
      - A phase line that names only the first 12 characters of the hash.
  - claim: >-
      The record is written as the critic cell's export returns, before the
      first lens session is asked. The witness reads `reviewed-diff.json`
      at the moment the first lens session is requested, and finds the
      critic cell's export there. That lens session then raises, and the
      task ends `REVIEW_INCOMPLETE`.
    witness: tests/test_session.py::test_the_lenses_diff_is_recorded_before_the_first_lens_session
    wrong_versions:
      - The record written beside `findings.json`, after every lens session returns.
      - The record written once REVIEW's branch ends, from `reviewed_diff` whatever it holds.
  - claim: >-
      A task whose lenses are handed no diff writes no `reviewed-diff.json`.
      The witness drives three such tasks, and first a clean REVIEW that
      writes the file through the same helpers. The three are a task that
      ends `PROVIDER_UNREACHABLE` before REVIEW, and one whose Gate-only
      cell suite aborts and ends `GATE_ERROR`. The third is one whose
      Gate-only cell applies the patch while its critic cell refuses it,
      ending `EXHAUSTED`. The clean REVIEW's spec is not stacked, and its
      file's `tree_base` is that spec's `base_sha`.
    witness: tests/test_session.py::test_a_task_whose_lenses_are_handed_no_diff_records_none
    wrong_versions:
      - The record written as `patch_to_review` is exported, before the Gate-only cell.
      - The record written once REVIEW's branch ends, from `reviewed_diff` whatever it holds.
      - An empty record written when the critic cell refuses the patch.
      - "`tree_base` written as the spec's `stacked_on`, which is null for a spec that is not stacked."
---

## Context

Backlog item **b-1b05be**, the open half its Record line of 2026-11-11
names. It cites `DESIGN.md` §5.7. This spec is the first of two that
close it. Every line number below was read at `b9908405`.

**The incident.** Finish 80 graded `SA-0369`'s two in-cell concerns as
live. REBUT had changed the cited line, and shifted the lines below it,
before PACKAGE pushed. For a concern, `_qualify_range` reads the diff
from the packaged head to the graded head (`saffron/qualify.py:144-148`).
It files the concern `unverified` only when its line sits in a hunk of
that diff (`saffron/qualify.py:192-197`). A line
REBUT moved before PACKAGE never reaches that diff.

**Which tree a concern cites.** An in-cell concern is a REVIEW lens's
finding. `_in_cell_concerns` reads it from the `findings` table
(`saffron/qualify.py:90-104`). REVIEW records each finding there
(`saffron/cell/session.py:3566-3571`), and REBUT records none, only a
verdict onto REVIEW's rows. The lens read its lines in the critic cell.
That cell's worktree is `tree_base` with the exported patch applied and
committed by its own git (`DESIGN.md` §5.5). `critic_cell` calls
`_apply_and_commit_patch` to do it (`saffron/cell/session.py:1608`,
`saffron/cell/session.py:1441-1510`).

**Two diffs, one of them read by lenses.** REVIEW exports
`patch_to_review` from the implementer's container
(`saffron/cell/session.py:3254`). It goes to the Gate-only cell
(`saffron/cell/session.py:3271`), the history cell
(`saffron/cell/session.py:3347`), the critic cell's `git apply`
(`saffron/cell/session.py:3365`), and the probe cells
(`saffron/cell/session.py:3472`, `saffron/cell/session.py:3518`). No lens
reads it. The critic cell then exports `reviewed_diff` from its own tree
(`saffron/cell/session.py:3375-3377`). Every lens session reads that one
through `review.run_review` (`saffron/cell/session.py:3391-3393`). So do
the criterion probe and wrong-version sessions
(`saffron/cell/session.py:3417-3419`, `saffron/cell/session.py:3432-3434`).
REBUT's verdict sessions are handed it as the diff their blockers were
filed against (`saffron/cell/session.py:3857-3858`). The two diffs are
equal when `git apply --index` reproduces the export exactly, but
`reviewed_diff` is the critic cell's own reading of the tree its lines
cite. So this spec records `reviewed_diff`.

**Nothing keeps it.** `reviewed_diff` is a local of `_drive_cell`
(`saffron/cell/session.py:3220`). The critic cell's volumes are removed
when REVIEW ends (`saffron/cell/session.py:1610-1615`). `patch.diff` is
written at teardown from the implementer's container, after REBUT
(`saffron/cell/session.py:1076`, `saffron/cell/session.py:1107`). Its
`patch.json` names `base_sha`, `tree_base`, `head_sha` and `files`
(`saffron/cell/session.py:934-946`). `rebuttal.json` carries a `head_moved`
flag and no tree (`saffron/phases/rebut.py:150-153`).

**Where a record can live.** A fact's kind must sit in `KINDS`
(`saffron/record/contract.py:19-47`, `saffron/record/contract.py:84-85`).
A test binds `KINDS` to `factory:FactKind` in the ontology
(`tests/ontology/test_vocabulary_agrees_with_code.py:181-182`), and
`CONTEXT.md` lists every kind (`CONTEXT.md:1034-1039`). `CONTEXT.md` is
`protected` (`.saffron/policy.yaml`, its `protected:` list). So a new kind
is a protected edit. A new key on an existing fact changes that fact's
shape, which the operator ruled out. So the diff goes into the task
directory, beside `findings.json`
(`saffron/cell/session.py:3558-3560`). A later `saffron finish` reaches
that directory: its `out_dir` is the batch tree's root
(`saffron/cli.py:351`, `saffron/cli.py:2735`), and a task's directory is
`out_dir / spec_id` (`saffron/cell/session.py:2321`). Its hash is carried
twice. The file holds it, as `scope_proposal.json` holds its own
(`saffron/cell/session.py:2630-2641`). And a REVIEW phase line names it, in
the task's existing `events.jsonl`
(`saffron/cell/session.py:1150-1152`, `saffron/events.py:503`). The notes
artifact is announced the same way (`saffron/cell/session.py:3201-3209`).

## Problem

The tree REVIEW's lenses cited cannot be rebuilt once the critic cell is
gone. Record the diff they read, so the second spec can rebuild that tree
as `tree_base` plus the diff.

In `saffron/cell/session.py`, right after `reviewed_diff` is exported at
lines 3375-3377 and before `review.run_review`, hash it with
`artifacts.hash_artifact`. Write `reviewed-diff.json` into `task_dir`, as
`json.dumps` of an object holding `tree_base` (`spec.tree_base`), `raw`
(the diff) and `sha256` (the hash), indented by 2. Then emit one
`_phase_start("REVIEW", "REVIEW", ...)` line naming the full hash.

The new phase line reaches `tests/fixtures/watch-golden.txt`, which
`test_watch_output_matches_the_golden_fixture` compares line for line
(`tests/test_events.py:1967-2007`). Add the line to the fixture, before
the first lens's line. `test_the_join_covers_every_captured_line_a_kind_renders`
then needs the line joined to a kind. Join it inline, the way that test
joins the conventions lens's line (`tests/test_events.py:2265-2275`).
Write the three tests the criteria name in `tests/test_session.py`.

## Out of scope

- **`qualify` and the finish.** Rebuilding the critic's tree and diffing
  it against the graded head is the second spec's work.
  `saffron/qualify.py` and `saffron/finish.py` stay as they are.
- **Any fact, table or existing file's shape.** No fact is appended and no
  payload gains a key. `findings.json`, `patch.diff`, `patch.json` and
  `rebuttal.json` are written as now.
- **REBUT's post-rebuttal diff.** The verdict sessions' second diff is
  exported in REBUT (`saffron/cell/session.py:3854`). No finding is filed
  against it, so it is not recorded.
- **A second task of the same spec.** A task directory is named by spec id
  and is never cleared. A later task of the spec that reaches REVIEW
  overwrites the file. One that stops before REVIEW leaves the earlier
  task's file in place. The second spec binds the file to its task, by
  the hash's phase line inside that task's span of `events.jsonl`.
- **Tasks that already ran.** Nothing backfills a record for them.

## Notes for the agent

**Every criterion is new code.** The record does not exist yet, so its
spelling is not forced by code. None declares a mutant, and `witness` will
report `skip` for each. The wrong versions under each criterion say what
its witness must still catch. The file name and its three keys are fixed
here because the second spec reads them.

**Seed each witness so its wrong version reaches its branch.**

- For criterion 1, start from
  `test_the_verdict_prompt_carries_the_diff_the_lenses_were_shown`
  (`tests/test_session.py:12349`). Its `export_patch` stub answers by
  container and by whether REBUT's rebuttal turn has run, so the three
  exports differ. Pass `spec=_spec(stacked_on="c" * 40)`, so `tree_base`
  differs from `base_sha` (`saffron/cell/session.py:401-410`). Pass
  `capture=` to `_drive` to read the phase lines. The lens prompts are
  the `system_prompts` after the plan and implement turns. Give the critic
  cell's export a character outside ASCII, such as `é` in an added line
  of `_ANCHORING_DIFF`, so a hash over another encoding differs. Keep its
  hunk on `src/x.py` line 1, where `_BLOCKER` anchors.
- For criterion 2, use a generator for `turns`, as
  `test_the_lens_gate_table_is_written_before_the_first_lens_runs` does
  (`tests/test_session.py:11270-11309`). Read the file after yielding the
  implement turn, then yield `implement.AgentFailed(...)` as the first
  lens turn. A lens session that raises ends the task
  `REVIEW_INCOMPLETE`, measured on a prototype.
- For criterion 3, drive each task under its own `tmp_path`
  subdirectory. `implement.AgentFailed("api_error",
  attempt=_served_nothing())` as the only turn ends `PROVIDER_UNREACHABLE`.
  An aborted Gate-only suite is `gate_cell_suite=` holding one `error`
  result, with `gates=("tests",)` and a policy declaring `tests`, as
  `_drive_gate_table_scenario` does (`tests/test_session.py:11188-11256`).
  For the refused critic cell, stub `saffron.cell.runtime.exec_stream` to
  return exit 1 only for `_CRITIC_CONTAINER`. The shared
  `_stub_critic_apply` (`tests/test_session.py:10340-10358`) refuses every
  container, so the Gate-only cell would refuse first and the critic cell
  never open. Assert the Gate-only container saw an exec, so the case
  reaches the critic cell. Read the clean case's file at the same
  `tmp_path / ... / "out" / "SY-1"` path the negative cases check, and
  assert its `tree_base` is `"b" * 40`, the default spec's `base_sha`.
- Criterion 3 names what its witness drives. Other tasks also end with no
  lens handed a diff: a drifted Gate-only suite, a patch the Gate-only
  cell refuses or cannot carry, a refused history cell, and a binary patch
  at the critic cell. So do a repair loop that ends `EXHAUSTED`, a plan
  rejected, a budget stop, `RATE_LIMITED`, and a critic export that
  raises. Each leaves REVIEW before the critic cell's export,
  as the three driven cases do. No witness drives them.

**At base each witness fails in its body.** No file is written there.
Import nothing the change adds at module scope.

**The golden line's hash is fixed.** The golden scenario's critic export
is `_stub_the_runtime`'s default `_DIFF`, so the line's hash is the same
on every pass. Copy the line `watch` prints into the fixture and into the
inline join.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype measured 50 changed tokens with `size_gate`, against
the `bug` ceiling of 1300, with 593 more under the test paths. It held the
write, the phase line, the fixture line, the inline join and the three
witnesses. Every test in `tests/test_session.py` and `tests/test_events.py`
passed on it.
