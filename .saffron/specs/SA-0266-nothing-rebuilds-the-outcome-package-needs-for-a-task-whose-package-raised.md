---
id: SA-0266
title: "Nothing rebuilds the outcome PACKAGE needs for a `READY_FOR_REVIEW` task whose PACKAGE raised, so no command can package its green patch"
type: feature
priority: 2
depends_on: [SA-0264]
estimated_lines: 434
estimate_measured: true
pending_symbols:
  - saffron/task.py::ready_task
touches:
  - saffron/task.py
  - tests/test_task.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/preflight.py
  - saffron/record/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/view/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/repos/**
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 36
max_attempts: 3
max_turns: 180
risk: standard
acceptance:
  - claim: >-
      `ready_task(spec_id, *, repo, repo_id, ledger, out_dir)` in
      `saffron/task.py` takes the spec's newest task in the repo when that task
      is `READY_FOR_REVIEW` with no pull request. It returns a `ReadyTask`
      whose `outcome` carries every field `package()` reads before
      overwriting it, but the agent's commit subjects. Those are the task id,
      the task directory `out_dir / spec_id`, the cell's head sha from
      `patch.json`, no new failures, REVIEW's lens reviews from
      `findings.json`, REBUT's result from `rebuttal.json`, the wrong versions
      and the notes. Only the task's attempts whose `started_at` is at or
      after `baseline.json`'s mtime, truncated to the second, count as this
      cell's. The spend is their sum. The attempt count is the number of them
      in `IMPLEMENTING` or `REPAIRING` that the ledger holds gate results
      for. The risk is the `earned_risk` of the newest of them that carries
      one. Its `spec` is the spec the task ran, and its `parent_branch` is
      `None` for an unstacked patch. The witness seeds the current cell's
      plan turn with no suite, an implement turn and a repair turn with
      suites, a review turn and a rebuttal suite. It also seeds a spec review
      turn, a spec writer turn and an earlier dead cell's implement, repair
      and review turns, all started before `baseline.json`, and a lens review
      that errored.
    witness: tests/test_task.py::test_ready_task_rebuilds_every_field_package_reads_from_the_cells_record
    wrong_versions:
      - A version whose spend is `Ledger.task_spend`, which counts every turn of the task.
      - A version that leaves out the spec sessions' phases and counts every other turn of the task, the dead cell's included.
      - A version whose spend leaves out `REVIEWING` turns.
      - A version that counts `IMPLEMENTING` suites only.
      - A version that counts every `IMPLEMENTING` and `REPAIRING` attempt, the plan turn included.
      - A version that counts every attempt with gate results, the rebuttal's re-run included.
      - A version whose risk is the spec's own `risk`.
      - A version whose risk is the oldest suite's `earned_risk`.
      - A version that leaves `rebut_result` unset.
      - A version that drops a lens review whose `error` is set.
  - claim: >-
      A patch whose `patch.json` `tree_base` differs from its `base_sha` was
      stacked. Its `parent_branch` is then the `branch` of the repo's newest
      task whose `pushed_sha` equals that `tree_base`, of any spec. The
      witness's spec declares no `depends_on`, and a newer task of another
      spec carries another pushed sha.
    witness: tests/test_task.py::test_ready_task_stacks_on_the_branch_of_the_task_that_pushed_its_tree_base
    wrong_versions:
      - A version that returns no parent branch for a stacked patch.
      - A version that takes the newest task with any pushed sha.
  - claim: >-
      The `spec` is the task's newest recorded spec text when the task holds
      one. Otherwise it is the file named for the spec id under
      `.saffron/specs/` or `.saffron/specs/done/` whose bytes hash to the
      task's `spec_sha`. The witness drives a task whose file sits in
      `done/` beside a same-id file in `.saffron/specs/` with other bytes. It
      drives a newer task whose file is that one in `.saffron/specs/`, and a
      newer task still that holds a recorded text.
    witness: tests/test_task.py::test_ready_task_reads_the_spec_text_the_task_ran
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
    witness: tests/test_task.py::test_ready_task_reads_a_record_older_than_the_cells_baseline_as_absent
    wrong_versions:
      - A version that reads the three files whatever their age.
      - A version that reads a file without checking it exists.
  - claim: >-
      `ready_task` returns a `Refused` whose reason names why, and writes no
      task row, when it refuses. It refuses a spec with no task in the repo,
      and a `repo_id` of `None`, and the reason names the spec id. It refuses
      a newest task in any state but `READY_FOR_REVIEW`, and the reason names
      the state. The witness drives every other member of
      `saffron.ledger.TaskState`, each above an older `READY_FOR_REVIEW` task
      of the same spec. It refuses a newest task that carries a pull
      request, and the reason names its URL. It refuses a task directory with
      no `baseline.json`. It refuses one whose `patch.diff`, `patch.json` or
      `findings.json` is missing or older than `baseline.json`, and the
      reason names the file. The witness drives all six. It refuses a task
      no spec text hashes to, and the reason names the sha's first twelve
      characters. It refuses a stacked patch whose `tree_base` no task in
      the repo pushed, and the reason names its first twelve characters.
    witness: tests/test_task.py::test_ready_task_refuses_with_a_reason_and_writes_nothing
    wrong_versions:
      - A version that rebuilds a task in any state.
      - A version that falls back to an older `READY_FOR_REVIEW` task when the newest task is in another state.
      - A version that rebuilds a task that already carries a pull request.
      - A version that checks the three required files for presence and not age.
      - A version that does not require `findings.json`.
      - A version that treats a stacked patch with an unknown parent as unstacked.
---

## Context

Backlog item **b-883f74**, found in the spec loop's run 31 and again in run
32. It cites `DESIGN.md` §5.7. Its related items are b-6cd3c2 and b-2247dd.
Every line number below was read at `0def7c4d`. The prototype it was measured
against carried `SA-0264`'s prototype diff on top of `0a5e3e5c`, whose
`saffron/` and `tests/` match `0def7c4d`'s.

This is the first of two specs. It builds the rebuild. `SA-0268` builds the
`saffron package` command over it, with N1's host probe, and depends on this
spec.

**PACKAGE raised after the cell went green, twice.** `SA-0226`'s cell ended
`READY_FOR_REVIEW` at $13.29 and exported its patch. PACKAGE's re-verify seed
then raised. Task 240 in the operator's ledger still reads
`READY_FOR_REVIEW` with a NULL `pr_url` (read on 2026-10-10). `SA-0233` did
the same as task 249. The delegate packaged both by hand, as #745 and #780,
and PACKAGE's re-verification never judged either tree.

**`run_task` leaves exactly that row.** A `PackageError` or any other raise
out of `package()` writes `READY_FOR_REVIEW` and re-raises
(`saffron/task.py:654-668`). The cell has already written its record to the
task directory, `out_dir / spec.spec_id` (`saffron/cell/session.py:1905`).

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
| `task_dir` | `out_dir / spec_id` |
| `cell_head_sha` | `patch.json`'s `head_sha` (`saffron/cell/session.py:906-919`) |
| `new_failures` | empty: the loop returns `READY_FOR_REVIEW` only on `green`, which has none (`saffron/cell/session.py:815-816`) |
| `reviews` | `findings.json`, written by every path that stays `READY_FOR_REVIEW` (`saffron/cell/session.py:3056-3058`) through each lens review's `as_dict` (`saffron/phases/review.py:160-167`) |
| `rebut_result` | `rebuttal.json`, written when REBUT ran (`saffron/cell/session.py:3180-3181`) through the result's `as_dict` (`saffron/phases/rebut.py:134-160`) |
| `wrong_versions` | `wrong-versions.json`, written only when there are any (`saffron/cell/session.py:3038-3040`) |
| `notes` | `notes.json`'s `raw`, written only when there are any (`saffron/cell/session.py:2742-2745`) |
| `spent_usd` | the cell's attempts. Every agent turn of the cell opens one (`saffron/cell/session.py:251-275`) |
| `attempts` | the cell's attempts the ledger holds gate results for (`saffron/cell/session.py:2594-2619`) |
| `effective_risk` | the newest attempt's `earned_risk` (`saffron/cell/session.py:2617`) |
| `advisory_gates` | not needed: `package()` overwrites it before its only read (`saffron/phases/package.py:850`, `:902`) |
| `agent_subjects` | **nowhere** |

**`agent_subjects` cannot be rebuilt.** Teardown reads the subjects with
`commit_subjects` from the cell's own repository
(`saffron/cell/session.py:888-896`). `run_one_cell` stamps
`agent_subjects` on the outcome (`saffron/cell/session.py:972-973`).
`patch.json` carries `base_sha`, `tree_base`, `head_sha` and `files` and no
subjects (`saffron/cell/session.py:906-919`). The ledger has no column for
them. The squash commit's body lists them only `if agent_subjects:`
(`saffron/phases/package.py:346-348`). So PACKAGE already writes a commit
with none when teardown could not read them.

**A task can carry turns that are not this cell's.** A stack batch's spec sessions
open attempts on the task (`saffron/batch.py:595`, `:703`). A stack batch
reruns a cell after a `CellRuntimeError` (`saffron/batch.py:741`). The
rerun keeps the task in `task_ids` (`saffron/batch.py:468-470`).
That cell reads the task's run with `task_run`
(`saffron/cell/session.py:1962-1966`). The live outcome counts this cell's
turns alone (`saffron/cell/session.py:3242-3249`). Every cell writes
`baseline.json` (`saffron/cell/session.py:2068-2070`) before
`plan_checkpoint` opens its first turn (`saffron/cell/session.py:2154`).

**The spend was measured against the cell's own figure.** Take the
attempts started at or after `baseline.json`'s mtime, truncated to the
second. Their sum matched each task's `TaskOutcome` `spent_usd_est` in
`events.jsonl`.
It was $13.2889788 for task 240 and $8.36478 for task 249. Truncation
matters: task 240's plan turn opened at 02:49:42, the second
`baseline.json` was written in. `task_spend` read $15.77 for task 240, the
spec review's $2.48 included. The suite count was 2 for both, which matches
each log's two `GATE` attempts. The counter counts the loop's suites and
never the rebuttal's re-run (`saffron/cell/session.py:2596-2599`).

**A task directory is shared by every task of a spec.** Nothing clears it
at cell start (`saffron/cell/session.py:1905-1916`). So a `rebuttal.json`
from an earlier task survives a cell whose REBUT never ran. In tasks 240's
and 249's directories every record a later phase wrote is newer than
`baseline.json`. `plan.json` was 3 and 5 minutes newer, and `patch.diff` 51
and 35.

**`SA-0233`'s patch was stacked.** Its `patch.json` names `tree_base`
`81246c79`, not its `base_sha`. `SA-0233` declares `depends_on: [SA-0231]`,
but it stacked on the batch's previous layer. That was `SA-0232`'s task
248, whose `pushed_sha` is `81246c79`. So `depends_on`, which
`_resolve_stacked_on` reads (`saffron/task.py:180-324`), names the wrong
parent here. The stack batch recorded no layer for it, so `stack_layers`
does not either.

## Problem

A green, reviewed patch is stranded when PACKAGE raises after the cell.
Nothing can hand `package()` that task again, because the outcome it takes
lived only in the process that raised.

Add `ready_task(spec_id, *, repo, repo_id, ledger, out_dir)` to
`saffron/task.py`. It returns a `ReadyTask`, a frozen dataclass with
`outcome`, `spec` and `parent_branch`, or a `Refused`. It takes the spec's
newest task in the repo (`Ledger.tasks_by_repo`,
`saffron/ledger.py:1060-1077`), and it writes nothing.

**How each field is rebuilt** is the table above. The required records are
`baseline.json`, `patch.diff`, `patch.json` and `findings.json`. Refuse a
task missing one, or holding a patch or findings older than
`baseline.json`, since the patch is then another cell's. `rebuttal.json`,
`wrong-versions.json` and `notes.json` count only when no older than
`baseline.json`, and are otherwise absent. Rebuild each `LensReview` and
`RebutResult` from the dict its `as_dict` wrote. `RebuttalTurn`'s
`cost_usd` and `session_id` are not in `rebuttal.json`. No reader of the
result reads either (`saffron/phases/rebut.py:590-626`,
`saffron/report/pr_body.py:249-342`). Leave `agent_subjects` empty.

**This cell's turns** are the task's attempts whose `started_at` is at or
after `baseline.json`'s mtime truncated to the second. `started_at` is
SQLite's UTC `datetime('now')` text (`saffron/ledger.py:165`). With the
turns scoped by time, no phase list is needed for the spend: the spec
sessions run before the cell. The attempt count still needs one, since
REBUT's re-run records a suite on a `REBUTTING` attempt.

**When no attempt carries an `earned_risk`**, the risk is the spec's own
`risk`. Re-verification's tier replaces `effective_risk`
(`saffron/phases/package.py:849`). Only `_finish`'s queue line on a return
before re-verification reads the rebuilt `effective_risk`
(`saffron/phases/package.py:1024`).

**The spec text is the one the task ran.** `run_task` runs a task's newest
recorded text in place of its file (`saffron/task.py:434-471`). Otherwise
the task's `spec_sha` is `load_spec`'s hash of the file's bytes
(`saffron/intake.py:348-359`).

**The parent branch comes from the pushed sha.** For an unstacked patch it
is `None`. For a stacked one, find the repo's newest task whose
`pushed_sha` equals `tree_base` in `tasks_by_repo`. Its `branch` is in
`tasks_by_spec_id` (`saffron/ledger.py:1079-1113`). `package()` itself then
asks the mirror whether that parent merged, and `fetch_parent_branch`
whether it is gone (`saffron/phases/package.py:695-726`).

## Out of scope

- **The command.** `SA-0268` adds `saffron package`, the host steps, N1's
  probe and the `package()` call. Nothing here calls `ready_task` in
  production, which is why it is a `pending_symbols` entry.
- **b-f582ee's second half, in part.** That item asks for two things. A
  task ended by a seed failure after IMPLEMENT keeps its green patch for a
  later command, and the task says which command. These two specs package a
  task that reached `READY_FOR_REVIEW`. A seed failure inside the cell,
  before REVIEW, ends the task `ORPHANED` (`saffron/cell/session.py:3301-3307`),
  and `ready_task` refuses it. Nothing prints the command's name when
  PACKAGE raises. So that half stays open.
- **Persisting the agent's commit subjects.** It needs a new record, and
  `saffron/cell/**` is `forbidden`.
- **An `EXHAUSTED` task with a standing blocker.** `run_task` packages it in
  PACKAGE's exhausted mode. A raise there pushes it as unpackaged work
  (`saffron/task.py:672-713`). `ready_task` refuses it by state.
- **A cell stacked on a parent head no task pushed.** A hand-committed fix
  on the parent's branch is such a head. `ready_task` refuses it rather
  than guess the branch.
- **`driver.py`'s `size` and `stack`** (b-2247dd). The operator edits them
  by hand.

## Notes for the agent

**Every criterion is new code.** `ready_task` does not exist at base. So
each criterion declares a witness and no mutant, and `witness` reports
`skip` for each.

**Where the witnesses live.** `tests/test_task.py` holds the tests for
`saffron/task.py` and already imports it as `task_module`. Call
`task_module.ready_task(...)` through that module. At base the attribute is
missing, so every witness fails. Import nothing at the module's top that
the change adds, or the reverted run is a collection error, which `revert`
reads as `skip`.

**Every ledger read exists:** `tasks_by_repo`, `tasks_by_spec_id`,
`spec_text`, `attempts`, `attempt_results` and `task_run`.
`saffron/ledger.py` is `forbidden`, and so is `saffron/phases/**`.

**The `dead` gate.** Nothing in `saffron/` calls `ready_task` until
`SA-0268`, so it is this spec's `pending_symbols` entry. `ReadyTask` and the
rebuild's helpers are reached through it.

**Seeding a task.** Seed the repo row with `ledger.upsert_repo`. Create the
run and task with `create_run` and `create_task`, and set its state with
`set_task_state`. Open each turn with `open_attempt(task_id, phase=...)`
and close it with `close_attempt` and a cost. Record a suite with
`record_gate_result(..., attempt_id=..., baseline=[], earned_risk=...)`.
Give a parent its branch and pushed sha with `set_task_package`. Date an
earlier cell's turns with an `UPDATE` of `attempts.started_at`, as tests
here already update rows directly. Choose costs that sum exactly in binary,
such as 1, 2, 0.5, 0.25 and 0.125.

**Writing the task directory.** Write `findings.json` from
`LensReview.as_dict` and `rebuttal.json` from `RebutResult.as_dict` over
`review.anchored_blockers(reviews)`, the way the cell does. Construct the
`RebuttalTurn` with no cost and no session id, so the rebuilt result equals
the one written. Date each file with `os.utime`, after every seeded earlier
turn and before every turn seeded now. Put `baseline.json` first, every
other record after it, and a stale record before it.

**Criterion 5's states.** Take them from `typing.get_args(TaskState)` inside
the test, minus `READY_FOR_REVIEW`. Read the whole `tasks` table before and
after, and assert it unchanged.

**Wrong versions.** Each criterion lists the ones its witness must kill. A
prototype's witnesses killed all 24 on 2026-10-10 and passed with the
change. Do not run them yourself.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** No path in `touches` is in `elevate_on`, so the diff is
`standard` and `size` is advisory. The prototype measured 1733 tokens with
`size_gate`'s counter against the `feature` ceiling of 3000. The tests were
1179 of them. `estimated_lines` is that count over four.
