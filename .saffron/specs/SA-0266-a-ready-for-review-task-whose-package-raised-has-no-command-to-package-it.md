---
id: SA-0266
title: "A `READY_FOR_REVIEW` task whose PACKAGE raised has no command to package it, so its green patch is packaged by hand or paid for again"
type: feature
priority: 2
depends_on: [SA-0264]
estimated_lines: 575
estimate_measured: true
touches:
  - saffron/cli.py
  - saffron/task.py
  - tests/test_cli.py
  - CLAUDE.md
  - README.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/record/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/view/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/repos/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 40
max_attempts: 3
max_turns: 200
risk: standard
acceptance:
  - claim: >-
      `saffron package <spec id> --repo <path>` takes the spec's newest task
      in the repo's ledger when that task is `READY_FOR_REVIEW` with no pull
      request. It calls `package()` once and never reaches `run_one_cell`.
      The outcome it hands over is rebuilt from the ledger and the spec's
      task directory in the batch tree. It carries every field `package()`
      reads before overwriting it, but the agent's commit subjects. Those are
      the task id, the task
      directory, the cell's head sha from `patch.json`, no new failures,
      REVIEW's lens reviews from `findings.json`, REBUT's result from
      `rebuttal.json`, the wrong versions and the notes. The spend is the sum
      over the task's attempts in `IMPLEMENTING`, `REPAIRING`, `REVIEWING`
      and `REBUTTING`. The attempt count is the number of `IMPLEMENTING` and
      `REPAIRING` attempts the ledger holds gate results for. The risk is the
      `earned_risk` of the newest attempt that carries one. `package()` also
      gets the spec, the resolved checkout, the mirror `prepare_mirror`
      returned, the tag `build_cell_image` returned, the `out_dir` that
      `saffron cell` uses, the `CLAUDE_CODE_OAUTH_TOKEN` value and no parent
      branch. The command
      prints the pull request's URL and exits 0. The witness seeds a spec
      review turn, a spec writer turn, a plan turn with no suite and a
      rebuttal suite, and a lens review that errored.
    witness: tests/test_cli.py::test_package_rebuilds_the_cells_outcome_and_runs_package_on_it
    wrong_versions:
      - A version whose spend is `Ledger.task_spend`, which counts the spec review and spec writer turns.
      - A version that counts every `IMPLEMENTING` and `REPAIRING` attempt, the plan turn included.
      - A version that counts every attempt with gate results, the rebuttal's re-run included.
      - A version whose risk is the spec's own `risk`.
      - A version whose risk is the oldest suite's `earned_risk`.
      - A version that passes `cell_tag(repo)` without building the image.
      - A version that leaves `rebut_result` unset.
      - A version that drops a lens review whose `error` is set.
      - A version that passes no token.
  - claim: >-
      A patch whose `patch.json` `tree_base` differs from its `base_sha` was
      stacked. `package()` then gets as its parent branch the `branch` of the
      repo's newest task whose `pushed_sha` equals that `tree_base`, of any
      spec. The witness's spec declares no `depends_on`, and a newer task of
      another spec carries another pushed sha.
    witness: tests/test_cli.py::test_package_stacks_on_the_branch_of_the_task_that_pushed_its_tree_base
    wrong_versions:
      - A version that passes no parent branch for a stacked patch.
      - A version that takes the newest task with any pushed sha.
  - claim: >-
      The spec `package()` gets is the task's newest recorded spec text when
      the task holds one. Otherwise it is the file named for the spec id
      under `.saffron/specs/` or `.saffron/specs/done/` whose bytes hash to
      the task's `spec_sha`. The witness drives a task whose file sits in
      `done/` beside a same-id file in `.saffron/specs/` with other bytes. It
      drives a newer task whose file is that one in `.saffron/specs/`, and a
      newer task still that holds a recorded text.
    witness: tests/test_cli.py::test_package_reads_the_spec_text_the_task_ran
    wrong_versions:
      - A version that reads the spec file even when the task holds a recorded text.
      - A version that never looks in `done/`.
      - A version that never looks in `.saffron/specs/` itself.
      - A version that takes the first file named for the spec id without checking its hash.
  - claim: >-
      `rebuttal.json`, `wrong-versions.json` and `notes.json` are each read
      only when present and no older than the task directory's
      `baseline.json`. One older than it was left by an earlier cell of the
      spec. The outcome then carries no REBUT result, no wrong versions and
      no notes, as it does when the three are absent. The witness drives
      all three stale, and then all three absent.
    witness: tests/test_cli.py::test_package_reads_a_record_older_than_the_cells_baseline_as_absent
    wrong_versions:
      - A version that reads the three files whatever their age.
      - A version that reads a file without checking it exists.
  - claim: >-
      The command exits 1, prints `package:` and a line naming its reason,
      and takes no other step when it refuses. It fetches no mirror, builds
      no image, calls no `package()` and writes no task row. It refuses a
      spec with no task in the repo's ledger, and a checkout whose origin the
      ledger lacks. It refuses a newest task in any state but
      `READY_FOR_REVIEW`, and the line names the state. The witness drives
      every other member of `saffron.ledger.TaskState`, each above an older
      `READY_FOR_REVIEW` task of the same spec. It refuses a newest task that
      carries a pull request, and the line names its URL. It refuses a task
      directory with no `baseline.json`. It refuses one whose `patch.diff`,
      `patch.json` or `findings.json` is missing or older than
      `baseline.json`, and the line names the file. The witness drives all
      six. It refuses a task no spec text hashes to, and the line names the
      sha's first twelve characters. It refuses a stacked patch whose
      `tree_base` no task in the repo pushed, and the line names its first
      twelve characters.
    witness: tests/test_cli.py::test_package_refuses_with_exit_one_and_takes_no_step
    wrong_versions:
      - A version that packages a task in any state.
      - A version that falls back to an older `READY_FOR_REVIEW` task when the newest task is in another state.
      - A version that packages a task that already carries a pull request.
      - A version that checks the three required files for presence and not age.
      - A version that does not require `findings.json`.
      - A version that fetches the mirror before it reads the ledger.
      - A version that packages a stacked patch with an unknown parent against the default branch.
  - claim: >-
      An unset or blank `CLAUDE_CODE_OAUTH_TOKEN` exits 2 before the command
      reads the ledger. A `package()` that returns `MERGE_FAILED` exits 1 and
      prints its note. A `package()` that raises exits 2 and leaves the task
      `READY_FOR_REVIEW` with no pull request, so the command takes it
      again.
    witness: tests/test_cli.py::test_package_exits_by_what_package_returned_or_raised
    wrong_versions:
      - A version that runs without the token.
      - A version that takes a token of spaces as set.
      - A version that exits 0 whatever `package()` returned.
      - A version that catches the raise and exits 1.
      - A version that records `MERGE_FAILED` on the task when `package()` raises.
---

## Context

Backlog item **b-883f74**, found in the spec loop's run 31 and again in run
32. It cites `DESIGN.md` §5.7. Its related items are b-6cd3c2 and b-2247dd.
Every line number below was read at `0a5e3e5c`, and the prototype it was
measured against carried `SA-0264`'s prototype diff on top.

**PACKAGE raised after the cell went green, twice.** `SA-0226`'s cell ended
`READY_FOR_REVIEW` at $13.29 and exported its patch. PACKAGE's re-verify seed
then raised. Task 240 in the operator's ledger still reads
`READY_FOR_REVIEW` with a NULL `pr_url` (read on 2026-10-10). `SA-0233` did
the same as task 249. The delegate packaged both by hand, as #745 and #780,
and PACKAGE's re-verification never judged either tree.

**`run_task` leaves exactly that row.** A `PackageError` or any other raise
out of `package()` writes `READY_FOR_REVIEW` and re-raises
(`saffron/task.py:654-668`). Under `saffron cell`, `main` then exits 2
(`saffron/cli.py:302-309`). The cell has already written its record to the
task directory, `out_dir / spec.spec_id` (`saffron/cell/session.py:1905`).
`out_dir` is `<home>/batches/v0` for every command but a `replay` given
`--out` (`saffron/cli.py:244-245`).

**No subcommand runs PACKAGE.** The subcommands are `replay`, `cell`,
`queue`, `batch`, `draft`, `reconcile`, `watch`, `fold`, `migrate`, `chains`
and `serve` (`saffron/cli.py:110-236`). `SA-0264` adds `adopt`, which names a
pull request opened by hand.

**`package()` takes the cell's live outcome.** Its first parameter,
`outcome`, is untyped (`saffron/phases/package.py:605-606`). Its one caller,
`run_task`, passes the `outcome` that `run_one_cell` returned
(`saffron/task.py:602`, `:638-639`). It and `_finish` read these fields of
it (`saffron/phases/package.py:646-1026`): `task_dir`,
`task_id`, `agent_subjects`, `cell_head_sha`, `attempts`, `spent_usd`,
`new_failures`, `reviews`, `rebut_result`, `effective_risk`,
`advisory_gates`, `notes` and `wrong_versions`. Each was measured at base for
whether the ledger or the task directory holds it.

| Field | Where it is held at base |
|---|---|
| `task_id` | the ledger's task row |
| `task_dir` | `<home>/batches/v0/<spec id>` |
| `cell_head_sha` | `patch.json`'s `head_sha` (`saffron/cell/session.py:906-919`) |
| `new_failures` | empty: the loop returns `READY_FOR_REVIEW` only on `green`, which has none (`saffron/cell/session.py:815-816`) |
| `reviews` | `findings.json`, written by every path that stays `READY_FOR_REVIEW` (`saffron/cell/session.py:3056-3058`) through each lens review's `as_dict` (`saffron/phases/review.py:160-167`) |
| `rebut_result` | `rebuttal.json`, written when REBUT ran (`saffron/cell/session.py:3180-3181`) through the result's `as_dict` (`saffron/phases/rebut.py:134-160`) |
| `wrong_versions` | `wrong-versions.json`, written only when there are any (`saffron/cell/session.py:3038-3040`) |
| `notes` | `notes.json`'s `raw`, written only when there are any (`saffron/cell/session.py:2742-2745`) |
| `spent_usd` | the task's attempts. Every agent turn of the cell opens one (`saffron/cell/session.py:251-275`) |
| `attempts` | the attempts the ledger holds gate results for (`saffron/cell/session.py:2594-2619`) |
| `effective_risk` | the newest attempt's `earned_risk` (`saffron/cell/session.py:2617`) |
| `advisory_gates` | not needed: `package()` overwrites it before its only read (`saffron/phases/package.py:850`, `:902`) |
| `agent_subjects` | **nowhere** |

**`agent_subjects` cannot be rebuilt.** Teardown reads the subjects with
`commit_subjects` from the cell's own repository
(`saffron/cell/session.py:888-896`). `run_one_cell` stamps
`agent_subjects` on the outcome (`saffron/cell/session.py:972-973`).
`patch.json` carries `base_sha`, `tree_base`, `head_sha` and `files` and no
subjects (`saffron/cell/session.py:906-919`). The ledger has no column for
them. The packaged commit therefore lists none. The squash commit's body lists
them only `if agent_subjects:` (`saffron/phases/package.py:346-348`). So
PACKAGE already writes such a commit when teardown could not read them.

**The spend was measured against the cell's own figure.** A task's
attempts can include a stack batch's spec review and spec writer turns
(`saffron/batch.py:595`, `:703`). The sum over the cell's four phases
matched each task's `TaskOutcome` `spent_usd_est` in `events.jsonl`. It
was $13.2889788 for task 240 and $8.36478 for task 249. `task_spend`
read $15.77 for task 240, the spec review's $2.48 included. The suite
count was 2 for both, which matches each log's two `GATE` attempts. The
counter counts the loop's suites and never the rebuttal's re-run
(`saffron/cell/session.py:2596-2599`).

**A task directory is shared by every task of a spec.** Nothing clears it
at cell start (`saffron/cell/session.py:1905-1916`). So a `rebuttal.json` from an earlier
task survives a cell whose REBUT never ran. Every cell that reaches its
baseline writes `baseline.json` first (`saffron/cell/session.py:2068-2070`). In tasks
240's and 249's directories every record a later phase wrote is newer than
it. `plan.json` was 3 and 5 minutes newer, and `patch.diff` 51 and 35.

**`SA-0233`'s patch was stacked.** Its `patch.json` names `tree_base`
`81246c79`, not its `base_sha`. `SA-0233` declares `depends_on: [SA-0231]`,
but it stacked on the batch's previous layer. That was `SA-0232`'s task
248, whose `pushed_sha` is `81246c79`. So `depends_on`, which
`_resolve_stacked_on` reads (`saffron/task.py:180-324`), names the wrong
parent here. The stack batch recorded no layer for it, so `stack_layers`
does not either.

## Problem

A green, reviewed patch is stranded when PACKAGE raises after the cell. The
operator's choices are to package it by hand, with no re-verification, or to
run the whole cell again and pay for it twice.

Add `saffron package <spec id> --repo <path>`. It takes the spec's newest
task when that task is `READY_FOR_REVIEW` with no pull request. It rebuilds
the outcome `package()` needs from the ledger and the task directory, then
runs PACKAGE on it, re-verification included. It runs no agent and never
reaches `run_one_cell`. PACKAGE's own Gate-only cells are the only cells it
starts.

**The order is the token, the ledger, then the host steps.** Check
`CLAUDE_CODE_OAUTH_TOKEN` first, exactly as `_run_cell` does
(`saffron/cli.py:457-461`): PACKAGE's credential refusal scans the patch for
that literal value (`saffron/phases/package.py:278-294`). Then read the ledger and the task
directory, and refuse there. Only a task that passes gets the mirror
`preflight.prepare_mirror` prepares, at the path `_run_cell` uses
(`saffron/cli.py:463-474`). It then gets the image
`repo_image.build_cell_image(repo)` builds, which the re-verify cells run
(`saffron/phases/package.py:482-590`).

**How each field is rebuilt** is the table above. Required records are
`baseline.json`, `patch.diff`, `patch.json` and `findings.json`. The command
refuses a task missing one, or holding a patch or findings older than
`baseline.json`. Then the patch is another cell's. `rebuttal.json`,
`wrong-versions.json` and `notes.json` count only when no older than
`baseline.json`, and are otherwise absent. Rebuild each `LensReview` and
`RebutResult` from the dict its `as_dict` wrote. `RebuttalTurn`'s
`cost_usd` and `session_id` are not in `rebuttal.json`. No reader of the
result reads either (`saffron/phases/rebut.py:590-626`, `saffron/report/pr_body.py:249-342`).
Pass `agent_subjects` as nothing.

**The spec text is the one the task ran.** `run_task` runs a task's newest
recorded text in place of its file (`saffron/task.py:434-471`). Otherwise
the task's `spec_sha` is `load_spec`'s hash of the file's bytes
(`saffron/intake.py:348-359`).

**The parent branch comes from the pushed sha.** For an unstacked patch it
is none. For a stacked one, find the repo's newest task whose `pushed_sha`
equals `tree_base` (`Ledger.tasks_by_repo`, `saffron/ledger.py:1060-1077`).
Its `branch` is in `tasks_by_spec_id` (`saffron/ledger.py:1079-1113`).
`package()` itself then asks the mirror whether that parent merged, and
`fetch_parent_branch` whether it is gone (`saffron/phases/package.py:695-726`).

**The exit code is `CELL_EXIT`'s for `package()`'s state**
(`saffron/cli.py:78-97`). A refusal exits 1, as `adopt`'s does. A raise
reaches `main`'s handler and exits 2, and the task row is left as it was.

Add the command to `CLAUDE.md`'s command list, one line beside
`reconcile`. Add it to `README.md`'s usage, with the token scoped to the
invocation as `saffron cell`'s line shows it.

## Out of scope

- **b-f582ee's second half, in part.** That item asks for two things. A
  task ended by a seed failure after IMPLEMENT keeps its green patch for a
  later command, and the task says which command. This spec packages a task
  that reached `READY_FOR_REVIEW`. A seed failure inside the cell, before
  REVIEW, ends the task `ORPHANED` (`saffron/cell/session.py:3301-3307`).
  This command refuses that task. Nothing here prints the command's name
  when PACKAGE raises. So that half stays open.
- **Persisting the agent's commit subjects.** It needs a new record, and
  `saffron/cell/**` is `forbidden`.
- **An `EXHAUSTED` task with a standing blocker.** `run_task` packages it in
  PACKAGE's exhausted mode. A raise there pushes it as unpackaged work
  (`saffron/task.py:672-713`). This command refuses it by state.
- **The batch.** It offers a task whose PACKAGE raised a `CellRuntimeError`
  again, and runs the whole cell (`saffron/batch.py:286`, `:741`). Leave
  that.
- **`driver.py`.** `.claude/skills/run-saffron-spec-loop/driver.py`'s
  `size` and `stack` (b-2247dd). The operator edits it by hand.
- **Protected text.** `DESIGN.md` §5.7 says the agent's own commit subjects
  are captured before teardown and carried in the commit body. That is
  false for a commit this command makes. The operator edits it in this
  spec's own pull request, with `CLAUDE.md`'s Layout line for
  `saffron/task.py`.
- **A cell stacked on a parent head no task pushed.** A hand-committed fix
  on the parent's branch is such a head. The command refuses it rather than
  guess the branch.

## Notes for the agent

**Every criterion is new code.** The command, the rebuild and the refusals
do not exist at base. So each criterion declares a witness and no mutant,
and `witness` reports `skip` for each.

**At base every witness fails.** `package` is not a subcommand, so `main`
raises `SystemExit` from argparse.

**Where it goes.** Put the rebuild in `saffron/task.py`, beside `run_task`.
The `one-task-driver` rule's own note sends task-driving code there
(`.saffron/rules/one-task-driver.yml`). Put the handler and the parser in
`saffron/cli.py`. Every ledger read it needs exists: `tasks_by_repo`,
`tasks_by_spec_id`, `spec_text`, `attempts`, `attempt_results` and
`task_run`. `saffron/ledger.py` is `forbidden`. `package()` is unchanged, and
`saffron/phases/**` is `forbidden`.

**The seams the witnesses replace.** Call `preflight.prepare_mirror`,
`repo_image.build_cell_image` and `package_phase.package` through their
modules, as `cli.py` already imports them. The witnesses replace
`saffron.preflight.prepare_mirror`, `saffron.repos.image.build_cell_image`,
`saffron.phases.package.package` and `saffron.task.run_one_cell` with
monkeypatch. The last raises, so a cell started anywhere fails the test.

**The checkout** is a `git init` directory whose `origin` is a GitHub URL
added with `git remote add`, holding spec files under `.saffron/specs/`.
`real_remote` reads it and nothing fetches it. Seed the repo row with that
URL through `_seed_repo` (`tests/test_cli.py:1969`).

**Seeding a task.** Create its run and task with `create_run` and
`create_task`, and set its state with `set_task_state`. Open each turn with
`open_attempt(task_id, phase=...)` and close it with `close_attempt` and a
cost. Record a suite with `record_gate_result(..., attempt_id=...,
baseline=[], earned_risk=...)`. Give a parent its branch and pushed sha with
`set_task_package`. Choose costs that sum exactly in binary, such as 1, 2,
0.5, 0.25 and 0.125.

**Writing the task directory.** Write `findings.json` from
`LensReview.as_dict` and `rebuttal.json` from `RebutResult.as_dict` over
`review.anchored_blockers(reviews)`, the way the cell does. Construct the
`RebuttalTurn` with no cost and no session id, so the rebuilt result equals
the one written. Date each file with `os.utime`. Put `baseline.json` first
and every other record after it, and put a stale record before it.

**Criterion 5's states.** Take them from `typing.get_args(TaskState)` inside
the test, minus `READY_FOR_REVIEW`. Read the whole `tasks` table before and
after, and assert it unchanged.

**Imports.** Import nothing at a witness module's top that the change adds.
The reverted run would then be a collection error, which `revert` reads as
`skip`.

**Wrong versions.** Each criterion lists the ones its witness must kill. A
prototype's witnesses killed all 29 on 2026-10-10 and passed with the
change. Do not run them yourself.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** No path in `touches` is in `elevate_on`, so the diff is
`standard` and `size` is advisory. The prototype measured 2298 tokens with
`size_gate`'s counter against the `feature` ceiling of 3000. The tests were
1548 of them, and the two documentation lines 46. `estimated_lines` is that
count over four.
