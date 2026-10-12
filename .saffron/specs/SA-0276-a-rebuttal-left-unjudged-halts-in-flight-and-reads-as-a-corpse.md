---
id: SA-0276
title: A rebuttal left unjudged halts its task at `REBUTTING`, so a stamping scan reads the halt as a crash
type: bug
priority: 2
depends_on: [SA-0271, SA-0262]
estimated_lines: 140
estimate_measured: true
touches:
  - saffron/phases/rebut.py
  - saffron/cell/session.py
  - tests/test_rebut.py
  - tests/test_session.py
  - tests/test_agent_runner.py
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
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/review.py
  - saffron/phases/package.py
  - tests/test_scheduler.py
  - tests/test_reconcile.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_report.py
  - tests/test_accept_rate.py
  - tests/test_spec_loop_driver.py
budget_usd: 25
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      `run_rebut` ends `REBUTTAL_UNJUDGED` when HEAD did not move and the
      rebuttal argued nothing. The witness drives four rebuttal turns. One
      claims a fix, one records no rebuttal, one fails, and one answers
      outside the schema. Each ends that state with no verdict run, and its
      line still says the rebuttal moved no commit and made no argument.
    witness: tests/test_rebut.py::test_a_rebuttal_that_neither_moved_nor_argued_ends_rebuttal_unjudged
    mutant:
      file: saffron/phases/rebut.py
      find: |-
        "REBUTTAL_UNJUDGED",
                    f"the rebuttal moved no commit
      replace: |-
        "REBUTTING",
                    f"the rebuttal moved no commit
    wrong_versions:
      - The new state returned only when the turn claimed a fix, so a turn that recorded nothing or failed still ends `REBUTTING`.
      - The new state returned only when the rebuttal turn carries no error, so a failed turn or one outside the schema still ends `REBUTTING`.
      - The new state returned only when the turn claimed a fix or failed, so a turn that recorded no rebuttal still ends `REBUTTING`.
  - claim: >-
      `rebut_state` ends `REBUTTAL_UNJUDGED` when a lens that started gave
      no verdict. The witness drives that lens alone and beside a lens with
      a clean verdict. It does so once with HEAD moved and once with HEAD
      unmoved and an argument recorded. Beside both, a lens that never
      started still ends `GATE_ERROR`.
    witness: tests/test_rebut.py::test_a_lens_that_started_and_gave_no_verdict_ends_rebuttal_unjudged
    mutant:
      file: saffron/phases/rebut.py
      find: |-
        "REBUTTAL_UNJUDGED",
                    f"{errored} produced no verdict
      replace: |-
        "REBUTTING",
                    f"{errored} produced no verdict
    wrong_versions:
      - The new state returned only when every lens errored, so an errored lens beside a clean one reads as judged.
      - The started-but-silent check run before the never-started check, so a lens that never started ends `REBUTTAL_UNJUDGED` instead of `GATE_ERROR`.
      - The new state returned only when HEAD moved, so an argued rebuttal with an errored lens still ends `REBUTTING`.
  - claim: >-
      `run_one_cell` returns `REBUTTAL_UNJUDGED` and writes it to the task
      row, for a silent rebuttal and for a lens that gave no verdict. A
      reconcile that stamps orphans then leaves that row as it is, while it
      stamps a `REBUTTING` row beside it `ORPHANED`. It asks GitHub nothing.
    witness: tests/test_session.py::test_a_rebuttal_left_unjudged_ends_its_task_in_a_state_no_scan_stamps
    mutant:
      file: saffron/cell/session.py
      find: ledger.set_task_state(task_id, outcome)
      replace: ledger.set_task_state(task_id, "REBUTTING" if outcome == "REBUTTAL_UNJUDGED" else outcome)
    wrong_versions:
      - The cell returns the new state but writes `REBUTTING` to the row, so the row stays in flight.
      - The new state joins the in-flight set, so a stamping reconcile stamps the row `ORPHANED`.
      - Only the silent rebuttal reaches the new state, so a lens with no verdict leaves the row `REBUTTING`.
      - A reconcile that reads no rows, so it stamps nothing whatever the row's state.
  - claim: >-
      A REBUT its cap cut short still ends `EXHAUSTED` with its blockers
      standing and its line saying REBUT ran out of its budget, as it does
      today.
    witness: tests/test_session.py::test_a_rebuttal_the_cap_cut_reads_as_out_of_budget_not_as_silence
    preserves: true
    mutant:
      file: saffron/cell/session.py
      find: cut = cap.refused and result.state == "REBUTTAL_UNJUDGED"
      replace: cut = cap.refused and result.state == "REBUTTING"
    wrong_versions:
      - The cut check left comparing against the in-flight state, so a REBUT the cap cut short ends `REBUTTAL_UNJUDGED` instead of `EXHAUSTED`.
---

## Context

Backlog item **120**, the part `SA-0231` left open. It cites `DESIGN.md`
§3.3, §4.2 and §5.6. Every line number below was read at `bc879e2c`, with
this spec's own commit applied.

**REBUT halts its task in an in-flight state.** `rebut_state` returns
`REBUTTING` in two places. One is a rebuttal that neither moved HEAD nor
argued (`saffron/phases/rebut.py:501-510`). The other is a lens that started
and gave no verdict (`:517-518`). A lens that never started returns
`GATE_ERROR` first (`:511-516`). `run_rebut` reaches the first through its
early exit (`:711-715`) and the second after the verdict sessions
(`:780-782`). The cell writes `REBUTTING` to the row as REBUT starts
(`saffron/cell/session.py:3081-3082`). It writes the outcome again at the end
(`:3242-3243`), so the row keeps `REBUTTING` after the cell exits.

**Each reader takes that row for a live cell or a corpse.** `REBUTTING` is in
`IN_FLIGHT_STATES` (`saffron/reconcile.py:49-60`). A reconcile that stamps
orphans sets every such row `ORPHANED` (`:195-199`). `saffron batch` passes
`stamp_orphaned=True` (`saffron/cli.py:1903-1910`), and `ORPHANED` re-queues the spec. `saffron batch`
also ends a night `INCOMPLETE` when a task returns in an in-flight state
(`saffron/batch.py:332-337`, `:864-867`). A child cannot stack on the row, because
`REBUTTING` is in no waiting state. PACKAGE never runs on it. `run_task`
pushes the cell's branch through `push_unpackaged_work` and opens no pull
request (`saffron/task.py:715-727`).

**This spec's own commit adds the state.** `REBUTTAL_UNJUDGED` is a terminal
state in `ontology/factory.ttl`, `CONTEXT.md` §6 and `DESIGN.md` §3.3. It is
in `ledger.TaskState` (`saffron/ledger.py:63`) and in `DONE_STATES`
(`saffron/scheduler.py:69-85`). It is in `DEPENDENCY_WAITING_STATES` (`:97-99`),
so a child stacks on the pushed branch. The morning queue ranks it with the
states that need you (`saffron/report/index.py:52-53`). It is not in
`IN_FLIGHT_STATES`, so no reader above takes it for a live cell. Nothing
writes it yet.

**The cap's cut reads the halt.** `SA-0231` ends a REBUT its cap cut short
`EXHAUSTED`. It decides the cut by comparing `result.state` with
`REBUTTING` (`saffron/cell/session.py:3172`).

## Problem

Make REBUT's halt write `REBUTTAL_UNJUDGED`.

Return `REBUTTAL_UNJUDGED` from both `REBUTTING` returns in `rebut_state`.
Keep each return's own line of text. Keep the never-started check ahead of
the errored one. Then make the cut check at `saffron/cell/session.py:3172`
compare against the new state, so a REBUT the cap cut short still ends
`EXHAUSTED`. Leave the write that marks REBUT live
(`saffron/cell/session.py:3081-3082`) as it is: `REBUTTING` stays the state
while REBUT runs.

Update the two docstrings that describe the halt.
`rebut_state`'s says §3.3 has no state for it (`saffron/phases/rebut.py:488-498`).
`unkept_fixes`'s says the task reaches the queue as `REBUTTING` and ranks
with elevated risk (`:616-622`). It now ranks with the states that need you.

Then update every existing assertion of `REBUTTING` as a halt's outcome to the
new state. Twenty such assertions sit in eighteen tests, one per test except
where noted. Keep each test's name.

- `tests/test_rebut.py`:
  `test_a_claimed_fix_with_no_commit_and_no_argument_does_not_advance`,
  `test_a_lens_that_leaves_a_blocker_unverdicted_has_not_withdrawn_it`,
  `test_a_verdict_that_is_not_the_schema_is_not_a_clean_verdict`,
  `test_a_rebuttal_turn_that_failed_charges_what_it_spent_and_buys_no_extraction`,
  `test_an_empty_argument_is_not_an_argument`,
  `test_a_rebuttal_turn_without_a_valid_structured_output_is_not_the_schema`,
  `test_a_verdict_session_without_a_valid_structured_output_is_not_the_schema`
  and
  `test_a_contradicted_verdict_missing_a_quote_is_read_as_confirmed_and_recorded`.
- `tests/test_session.py`:
  `test_a_cell_reports_each_phase_state_as_it_enters_it`,
  `test_a_rebut_the_cap_cut_short_ends_exhausted_with_its_blockers_standing`,
  `test_a_rebuttal_the_cap_cut_reads_as_out_of_budget_not_as_silence` (two),
  `test_a_rebuttal_that_claims_a_fix_and_commits_nothing_stops_at_rebutting`
  (two, the outcome and the queue row),
  `test_a_concern_whose_probe_survives_is_rebutted_as_a_blocker`,
  `test_a_probe_that_raises_stops_probing_and_keeps_the_verdicts_given`,
  `test_a_probe_only_a_test_the_diff_did_not_add_notices_is_rebutted_with_that_failure_recorded`,
  `test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker`
  and `test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker`.
- `tests/test_agent_runner.py`:
  `test_a_verdict_session_that_never_started_ends_rebut_gate_error`, its
  case B.

Leave every `REBUTTING` that names the live state or an attempt's phase.
`test_a_cell_reports_each_phase_state_as_it_enters_it` still hears
`REBUTTING` as REBUT starts, and an attempt row's phase stays `REBUTTING`.

## Out of scope

- **The state's vocabulary, its scheduler sets and its rank.** This spec's
  own commit lands them, with `DESIGN.md` and `CONTEXT.md`.
- **A stack batch's layer.** `_is_layer` admits only `READY_FOR_REVIEW`
  (`saffron/batch.py:371-378`). A `REBUTTAL_UNJUDGED` task stays a miss
  there, as `REBUTTING` is today.
- **The spec loop's own rules.** Its driver holds a child back unless the
  parent is `READY_FOR_REVIEW`
  (`.claude/skills/run-saffron-spec-loop/driver.py:1005-1009`). Its
  `GOTCHAS.md` still describes the halt as `REBUTTING`. Both are edited by
  hand once this lands.
- **Rows already left `REBUTTING`.** No migration rewrites them. A stamping
  scan still stamps them `ORPHANED`.
- **A parent whose push was refused.** `push_unpackaged_work` can refuse,
  and the row then records no push. The scheduler still admits the child,
  which is cut from `base_sha` without the parent's code. Backlog item
  b-f603c9 owns that. This spec adds no witness and no code for it.

## Notes for the agent

**Each criterion pins existing text.** Criteria 1 and 2 swap a literal
in place in a return that already exists. Criterion 3 mutates the end of the
cell, which this change leaves alone. Criterion 4 mutates the cut check this
change edits. So each declares a mutant.

**Criterion 2's return grows past the line limit.** `ruff format` then wraps
it into a parenthesised two-line tuple, as the first return already is.
Run `make fmt` before committing.

**Criterion 1** calls the `_run` helper (`tests/test_rebut.py:152-195`) with
`moved=False`, once per turn. The fake agent returns its scripted turns in
order and raises `StopIteration` when they run out. A claimed fix is `_rebuttals(_fixed())`.
No rebuttal is `_rebuttals()`. A failed turn is an `implement.AgentFailed`.
Text with no structured output is outside the schema.

**Criterion 2** calls `rebut.rebut_state` directly with `LensVerdicts`
(`saffron/phases/rebut.py:108-122`). Give the silent lens an `error` and
`never_started=False`, and the other lens one `withdrawn` verdict. Drive the
`GATE_ERROR` case with all three lenses, the never-started one last.

**Criterion 3** drives `_drive` (`tests/test_session.py:1350`) twice, each on
its own `tmp_path` subdirectory. Copy the silent form from
`test_a_rebuttal_that_claims_a_fix_and_commits_nothing_stops_at_rebutting`
(`tests/test_session.py:5009-5030`). For a lens with no verdict, use
`rebut_commits=1`, an argued rebuttal, and a verdict turn of plain text.
On each of the two ledgers, assert the outcome and the row are
`REBUTTAL_UNJUDGED`. Then add a second task row in the same repo, set it
`REBUTTING` through `ledger.set_task_state`, and call
`saffron.reconcile.reconcile` with `stamp_orphaned=True`. Pass a `gh` that
raises when called. A `gh` that returned an empty answer would hide a build
that asks GitHub about the row. Read the repo id from the ledger's `repos`
table. Assert `result.orphaned` is exactly the second row's id. Then assert
the cell's row is still `REBUTTAL_UNJUDGED` and the second row is
`ORPHANED`. Without the second row, a reconcile that reads no rows passes.

**Criterion 4's witness exists.** Its two silence cases, `silence` and
`spent-not-refused`, are two of the assertions to update. Its cut cases must
stay `EXHAUSTED` untouched.

**At base each new witness fails in its body.** None imports a name this
change adds.

**`saffron/cell/**` is in `elevate_on`**, so this task runs `elevated` and
`size` blocks.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** A prototype measured 523 changed tokens with `size_gate`'s counter,
against the `bug` ceiling of 1300. It held both source edits, both docstring
updates, all twenty assertion updates and the three new witnesses.
`estimated_lines` is that count over four, plus a margin.
