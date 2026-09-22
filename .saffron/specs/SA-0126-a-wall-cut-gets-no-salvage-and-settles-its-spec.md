---
id: SA-0126
title: An implement turn the wall clock cuts gets no salvage turn, and a cut that leaves nothing committed settles its spec as `NOT_IMPLEMENTED`
type: feature
priority: 1
depends_on: [SA-0125]
touches:
  - saffron/cell/session.py
  - saffron/events.py
  - saffron/phases/implement.py
  - tests/test_session.py
  - tests/test_events.py
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
  - saffron/agents/**
  - saffron/phases/package.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/reconcile.py
  - saffron/cli.py
  - saffron/task.py
  - tests/test_scheduler.py
  - tests/test_batch.py
  - tests/test_implement.py
  - tests/test_ledger.py
  - tests/test_fold.py
  - tests/test_package.py
  - tests/test_spec_loop_driver.py
budget_usd: 24
max_attempts: 3
max_turns: 160
risk: elevated
acceptance:
  - claim: >-
      An IMPLEMENT turn that the wall clock cuts with nothing committed gets
      the salvage turn when the budget has room for it. The salvage turn
      resumes the plan turn's session, carries the salvage prompt, and runs
      under `SALVAGE_MAX_TURNS`. The watch line that announces it names the
      wall clock, contains "wall", and does not contain "turn ceiling". A
      commit the salvage turn makes carries the task on to
      `READY_FOR_REVIEW`. The witness drives one cell whose implement turn
      raises `AgentFailed` shaped as `run_agent` raises it for a wall cut.
      Today that cell ends `NOT_IMPLEMENTED` after two turns.
    witness: tests/test_session.py::test_a_turn_cut_by_the_wall_with_nothing_committed_is_salvaged
  - claim: >-
      The first IMPLEMENT turn at a `spec_sha` that the turn ceiling or the
      wall clock cuts with nothing committed ends `ORPHANED`, in the returned
      outcome and on the task's ledger row. The witness drives all four such
      paths, each in its own cell and ledger: a turn cut and a wall cut whose
      salvage turn recovers nothing, and a turn cut and a wall cut with no
      budget left for one. On each, the watch line that announces the salvage
      turn or refuses it for budget names the bound that cut the turn, "turn
      ceiling" or "wall", and not the other. `ORPHANED` is in
      `scheduler.REQUEUE_STATES` and not in `scheduler.DONE_STATES`, so the
      next scan re-queues the spec. A fifth cell, whose implement turn the
      idle bound cuts with nothing committed, still ends `NOT_IMPLEMENTED`
      after two turns. Today all four cut paths end `NOT_IMPLEMENTED`.
    witness: tests/test_session.py::test_every_cut_that_leaves_nothing_committed_halts_for_the_next_scan
    mutant:
      file: saffron/cell/session.py
      find: 'attempt.terminal_reason == "max_turns" or attempt.subtype == "error_max_turns"'
      replace: 'attempt.terminal_reason == "max_turns" and attempt.subtype == "no-such"'
  - claim: >-
      A spec retries a cut once per `spec_sha`. When an earlier task at the
      same repo, spec id and `spec_sha` already ended `ORPHANED` by such a
      cut, the next cut with nothing committed ends `NOT_IMPLEMENTED`. Its
      salvage turn still runs first. One watch line says the turn was cut
      again at this `spec_sha` and names the earlier task by id. The witness
      drives three cells in turn against one ledger. The first is a turn cut
      at another `spec_sha`, and ends `ORPHANED`. The second is a wall cut at
      the spec's own `spec_sha`, and ends `ORPHANED`, since a cut at another
      `spec_sha` does not count. The third is a turn cut at that same
      `spec_sha`. It runs three turns, ends `NOT_IMPLEMENTED` in its outcome
      and its row, and its line names task 2. Neither earlier cell prints
      that line.
    witness: tests/test_session.py::test_a_second_cut_at_one_spec_sha_settles_the_spec
  - claim: >-
      A task `ORPHANED` by anything but a cut does not use up the retry. The
      witness puts four such tasks at the spec's `spec_sha` in one ledger
      first. One is a real cell killed by a raise out of its implement turn,
      whose run ends `ABORTED`. The other three are built through `Ledger`'s
      own methods, each with closed attempts, then stamped `ORPHANED`. One
      holds one `IMPLEMENTING` attempt, and its run stays `RUNNING`, as a
      scan's stamp leaves it. One holds an `IMPLEMENTING` attempt and then a
      `REVIEWING` one, and its run ends `COMPLETE`. One holds `IMPLEMENTING`,
      `REBUTTING` and `IMPLEMENTING` attempts in that order, and its run ends
      `COMPLETE`. A wall cut with nothing committed then ends `ORPHANED`, and
      prints no cut-again line.
    witness: tests/test_session.py::test_a_task_orphaned_by_anything_but_a_cut_leaves_the_retry
  - claim: >-
      An implement turn that crashes with nothing committed still gets no
      salvage turn and still ends `NOT_IMPLEMENTED`.
    witness: tests/test_session.py::test_a_turn_that_crashed_is_not_reported_as_having_finished
    preserves: true
  - claim: >-
      An implement turn that finishes on its own with nothing committed still
      gets no salvage turn and still ends `NOT_IMPLEMENTED`.
    witness: tests/test_session.py::test_no_commit_is_not_implemented
    preserves: true
  - claim: >-
      A turn-ceiling cut whose salvage turn commits still carries the task on
      to `READY_FOR_REVIEW`, resumed on the same session and charged for every
      turn.
    witness: tests/test_session.py::test_a_turn_cut_off_at_the_ceiling_with_nothing_committed_is_salvaged
    preserves: true
---

## Context

Backlog item **b-36b551**, found in the spec loop's run 8 and seen again in
runs 11 and 12. Tier 1 in `docs/backlog/PRIORITY.md`. This spec is the code
half of the item's *Done looks like*. The prompt half is out of scope, below.
The operator chose the halt: `ORPHANED` on the first cut, and
`NOT_IMPLEMENTED` on the second at one `spec_sha`.

**Stacked on `SA-0125`.** Every line number below was read at `46d2cd56`,
whose source files match `5edfefef`. `SA-0125` lands first and edits four of
this spec's five files. Its changes, and where they meet this one, are in
the notes under **Where `SA-0125` meets this spec**. Where a line moves,
find it by the name beside it.

Every turn runs under a 900s wall clock. `TURN_TIMEOUT_S` is set at
`saffron/cell/session.py:63` and bound onto the agent callable at `:1783`.

What happens today when that wall fires in IMPLEMENT:

- Before a result event arrives, `exec_stream` names the wall deadline's
  wait `"wall"` (`saffron/cell/runtime.py:549-552`). It kills the process
  (`:557-559`) and returns that bound with `timed_out` set (`:577-578`).
- `run_agent` then raises `AgentFailed` from its no-result branch
  (`saffron/phases/implement.py:301-319`). The attempt it carries has
  `session_id=None`, `subtype="error"`, `terminal_reason=None`, `num_turns=0`,
  the previous turn's cost, and `bound` set to the runtime's `"wall"`.
- `_drive_cell` catches it and keeps the attempt (`saffron/cell/session.py:1963-1972`).
  The session id falls back to the plan turn's (`:1973`).
- `cut_off_at_turn_ceiling` alone opens the salvage branch (`:1991`).
  That predicate reads `terminal_reason` and `subtype` alone
  (`:366-385`), so a wall cut never reaches it.
- The wall cut falls to `ended_without_finishing` (`:2105-2119`), and every
  zero-commit path ends `NOT_IMPLEMENTED` at `:2134-2145`.

`NOT_IMPLEMENTED` is in `DONE_STATES` (`saffron/scheduler.py:63-76`), so the
next scan treats the spec as decided at that `spec_sha`. `SA-0107`'s first
cell lost its work this way at $5.07. `SA-0116` did the same at $6.63 and then
dropped out of the queue with no refusal line.

The turn-ceiling salvage exists (`SA-0028`). It checks the budget first
(`saffron/cell/session.py:1998-2007`) and announces itself (`:2009-2014`).
It clamps its turns (`:2018`) and checkpoints dirty work (`:2067-2086`). It
re-measures commits from the plan turn's head (`:2089`). A turn-ceiling cut
whose salvage recovers nothing, or that has no budget for one, still ends
`NOT_IMPLEMENTED`.

**The halt state is `ORPHANED`.** `DESIGN.md` §4.2.1 re-queues on five
states. They are `CHANGES_REQUESTED`, `RATE_LIMITED`, `GATE_ERROR`,
`PREFLIGHT_FAILED` and `ORPHANED`. The rule is "re-queue when nothing was
learned about the spec" (`DESIGN.md:386`). The same five are `REQUEUE_STATES`
(`saffron/scheduler.py:103-112`). Four of them name a different cause. The
operator sends a task back as `CHANGES_REQUESTED`. `RATE_LIMITED` is the
provider's ceiling, and `CLAUDE.md` keeps it apart from a task's own
outcome. `GATE_ERROR` and `PREFLIGHT_FAILED` are breaker aborts
(`saffron/batch.py:49`). `ORPHANED` is what the supervisor stamps "on kill,
on crash, and on `--until`" (`DESIGN.md` §4.5, `DESIGN.md:492`). A wall cut is
that kill, and `run_one_cell` already stamps `ORPHANED` on a raise
(`saffron/cell/session.py:2762-2765`).

What `ORPHANED` does downstream, read at this base:

- `saffron cell` exits 1 for it, as for `NOT_IMPLEMENTED`. `CELL_EXIT` names
  neither, and the default is 1 (`saffron/cli.py:51-65`, `:416`).
- `saffron batch` resets its breaker on it, since it is not in
  `ABORT_STATES` (`saffron/batch.py:49`). It is not in `IN_FLIGHT_STATES`
  either (`saffron/reconcile.py:55-66`), so the night does not end
  `INCOMPLETE`. A batch starts each spec once a night, by id
  (`saffron/batch.py:171`, `:177`, `:204`). A re-queued spec runs again the
  next night, not the same one.
- The morning queue ranks it level 2, beside `NOT_IMPLEMENTED`
  (`saffron/report/index.py:32`).
- With no patch on disk, `push_unpackaged_work` returns "no commits,
  nothing to push", whatever the state (`saffron/phases/package.py:1068-1071`).
- `record` in the spec loop's driver leaves a state outside `DONE_STATES`
  pending (`.claude/skills/run-saffron-spec-loop/driver.py:1078-1089`).

**Where "already `ORPHANED` by a cut" can be read.** Each cell mints its own
task. `_drive_cell` calls `ledger.create_task` at
`saffron/cell/session.py:1640`, after `upsert_repo` returns the repo's id at
`:1638`. So an earlier cut is an earlier task row at the same repo, spec id
and `spec_sha`. The state alone does not say which path wrote `ORPHANED`.
Three other paths write it, and the run and the attempts tell them apart:

- A raise out of `run_one_cell` finishes the run `ABORTED` and stamps the
  task `ORPHANED` (`saffron/cell/session.py:2762-2765`).
- A batch scan stamps a task left in flight `ORPHANED` and touches no run
  (`saffron/reconcile.py:174-177`). `create_run` opens every run as
  `RUNNING` (`saffron/ledger.py:739-753`).
- A cell can return with its task in `REBUTTING` and its run `COMPLETE`
  (`saffron/cell/session.py:2579-2580`, `:2709-2710`, and
  `test_a_rebuttal_that_claims_a_fix_and_commits_nothing_stops_at_rebutting`).
  A later scan stamps that task `ORPHANED` too.
- The cut path this spec adds finishes the run `COMPLETE`, as every
  zero-commit return does now (`saffron/cell/session.py:2136`). Its task
  never leaves `IMPLEMENTING` before that, which the task enters at `:1772`,
  before the plan turn. `open_attempt` files each attempt under the task's
  state at that time (`saffron/ledger.py:991-1010`). So every attempt a cut
  task holds is in phase `IMPLEMENTING`.

- An errored lens sends a task to `REVIEWING`
  (`saffron/phases/review.py:616`), and the cell returns with its run
  `COMPLETE`. A later scan
  stamps that task `ORPHANED` as well.

So a task `ORPHANED` by a cut is one whose run finished `COMPLETE` and whose
attempts are all in phase `IMPLEMENTING`. `saffron/ledger.py` has no public
method returning a run's status, and this spec forbids that file, which
`SA-0123` and `SA-0124` both edit. `saffron/chain_walk.py:54` and
`saffron/projection.py:287` read the ledger's tables through `ledger._db`
already, and this spec does the same.

**No fact carries the difference.** The record declares `run_created` and
`run_finished` (`saffron/record/contract.py:32-33`), and nothing appends
either. `saffron/record/fold.py:8-12` says a rebuild leaves `runs.status`
unset. The task facts cannot stand in. Take a wall cut that leaves one
commit, then a kill during the first gate suite. `_judge` records gate
results only after the suite returns (`saffron/cell/session.py:2149-2162`).
That task's facts are `task_created`, `task_state` `IMPLEMENTING`, two closed
attempts in phase `IMPLEMENTING`, the second with subtype `error`, and
`task_state` `ORPHANED`. A wall cut that stops with nothing committed and no
budget to salvage writes the same facts. So the cap keys on `runs.status`, and
backlog item b-cafacd owns a fact that would carry it.

**Measured, not reasoned:** a session cut by the wall resumes. In `SA-0117`'s
cell (`~/.saffron/batches/v0/SA-0117/events.jsonl`), line 806 reaps the cell
after a wall cut in IMPLEMENT. Session `8bb7393a` carries events from line 27
before the cut to line 3491 after it, the REPAIR turns included.

## Problem

A bound cutting a turn is a fact about the turn, not about the spec (§4.3: "A
timeout must never discard committed work"). Today the wall clock throws away
uncommitted work that the turn ceiling saves. And a cut by either bound that
leaves nothing committed settles the spec, as a tried and failed one.

Re-queueing every cut has its own cost. A spec whose turns always outrun the
wall would spend a cell every night. So the first cut at a `spec_sha`
re-queues, and the second settles it. Editing the spec gives it a new
`spec_sha`, and with it one more retry.

## Out of scope

- **The implement prompt.** The item also asks that
  `saffron/agents/prompts/implement.md` name the unit of a commit. A prompt
  change needs a measured pass (`.github/pull_request_template.md`), so the
  item closes partial and that half stays open on it.
- **The idle bound.** An idle cut is a stall, not a turn that ran out of
  time. It keeps ending `ended_without_finishing` and `NOT_IMPLEMENTED`, with
  no salvage turn. Criterion 2's fifth cell pins that. One stall reads as the
  wall. `exec_stream` names the bound `"wall"` once the wall is nearer than
  the idle window (`saffron/cell/runtime.py:549-552`, `IDLE_TIMEOUT_S` at
  `:176`). So a stall in a turn's last 300 seconds is a wall cut, and gets
  the salvage turn, capped at `SALVAGE_MAX_TURNS`.
- **The plan turn.** A plan turn that any bound cuts still ends
  `NOT_IMPLEMENTED` at `saffron/cell/session.py:1876-1897`. It has no salvage
  turn, and nothing is committed before a plan exists.
- **REPAIR and REBUT turns.** Their own host checkpoint keeps dirty work
  already (`saffron/cell/session.py:2209-2230`).
- **The cut turn's spend.** Item b-36b551's record says `SA-0117`'s cut turn
  reports $1.52 and the ledger books it as zero turns. That accounting is
  another item.
- **A public ledger method for the cap's read.** It belongs in
  `saffron/ledger.py`, which this spec forbids. Moving the query there is a
  follow-up once `SA-0123` lands.
- **A ledger folded from the record.** `_run_for` inserts each folded run as
  `RUNNING` (`saffron/ledger.py:486-489`). In a folded ledger no earlier cut
  matches, so the cap never fires and every cut re-queues, every night.
  Nothing live uses a folded ledger yet. Backlog item b-cafacd owns the
  `run_finished` fact that would fix it.
- **A re-queue that resumes the old task row.** The cap rests on each cell
  minting its own task (`saffron/cell/session.py:1640`). `DESIGN.md` §4.2.1
  says a re-queued spec resumes its task row (`DESIGN.md:384`), and
  `saffron/scheduler.py:779-780` computes which one. Nothing passes that row
  to a cell yet. If a re-queue ever resumes it, the cap's "an earlier task"
  excludes the first cut's own row, and the cap stops firing with no error.
  That change must re-key the cap, and revisit the every-attempt rule. A
  resumed row cut after REBUT ends on an `IMPLEMENTING` attempt, and that
  rule would miss it. Backlog item b-149df3 records both.
- **`CONTEXT.md`, `DESIGN.md` and the spec loop's gotchas.** `CONTEXT.md` §6
  says each `TerminalEvent` reason ends in `PLAN_REJECTED` or
  `NOT_IMPLEMENTED`. It defines `ORPHANED` as a cell killed or crashed.
  `DESIGN.md` §4.5 lists when the supervisor stamps `ORPHANED`.
  `.claude/skills/run-saffron-spec-loop/GOTCHAS.md:57-59` and `:65` say a cut
  with no room to salvage ends `NOT_IMPLEMENTED`. All become incomplete here,
  and none names the one retry. The first two are protected, this spec
  forbids the third, and backlog item b-149df3 owns all of them, by hand.
- **The spec loop's watch pattern**
  (`.claude/skills/run-saffron-spec-loop/driver.py:810-818`) anchors only
  terminal states, and `ORPHANED` is not one. A change there belongs to
  the loop, not to this spec.

## Notes for the agent

**Which criteria carry mutants.** This change edits existing code, but the
text the fix lands in is not forced. No spelling of the salvage branch's
condition is forced, and none of the zero-commit return's state or of the
cap's query. So criteria 1, 3 and 4 declare a witness alone, and `witness`
reports `skip` for them. Criterion 2's mutant pins `cut_off_at_turn_ceiling`'s
own expression, which this spec keeps. Leave that function's body and name
as they are. Its four unit tests (`tests/test_session.py:72-123`) and the loop
driver's copy of its rule (`.claude/skills/run-saffron-spec-loop/driver.py:1646-1653`)
both read it.

**Where the change goes.** The salvage and the halt are in `_drive_cell`'s
zero-commit block, `saffron/cell/session.py:1977-2145`. Decide once, from the
implement turn's attempt, whether a bound cut it and which one. The turn
ceiling is `cut_off_at_turn_ceiling`. The wall clock is the attempt's `bound`
reading `"wall"`. Only these two earn the salvage turn. Use that one decision
for the salvage branch and for the state the zero-commit return writes.

**The cap.** Put its read in one module-level function in
`saffron/cell/session.py`, beside `cut_off_at_turn_ceiling` (`:366-385`).
`SA-0125` does not edit that stretch. It takes the ledger, the repo id, the
spec and the current task id, and returns the earlier task's id or `None`.
One query over `ledger._db` joins `tasks` to `runs`, as
`saffron/chain_walk.py:54` does. It matches the repo id, spec id and
`spec_sha`, excludes the current task, and needs all three of these:

- the task's state is `ORPHANED`
- its run's status is `COMPLETE`
- no attempt of the task has a phase other than `IMPLEMENTING`

Call it only when a bound cut the turn and nothing is committed after the
salvage. Where it finds a task, emit one `_phase_start` line with label
`IMPLEMENT`. It says the turn was cut again at this `spec_sha`, and names
the earlier task as `task <id>`. Then end `NOT_IMPLEMENTED`. Emit nothing new
where it finds none.

**The two salvage watch lines.** The salvage announcement is `_phase_start`'s detail
at `saffron/cell/session.py:2009-2014`. The budget refusal renders `Terminal`'s
`cut_off_no_salvage_room` in `saffron/events.py:812-816`, and its fixed text
says "turn ceiling" today. Carry the bound through `detail`, and keep
`Terminal`'s fields as they are. Two tests pin the rendered text:
`tests/test_events.py:1076-1086` and `:1585-1597`. Update both. The first is
a case of `test_describe_renders_every_kind_and_variant`, whose ids are the
expected line's first 24 characters (`tests/test_events.py:1151-1153`). Keep
those 24 characters as they are, or the case's id changes and `census` reads
a test as removed.

**The new line is a new family.** Add one `_Family` row for it to
`FAMILIES` in `saffron/events.py`, beside
`"IMPLEMENT: cut off … spending one turn"` (`saffron/events.py:914`), citing
`_S`. Its prefix must differ from every other row's.
`test_the_table_did_not_quietly_lose_a_row` pins the count. `SA-0125` moves
it from 63 to 64, and this spec moves it from 64 to 65. That test's
docstring (`tests/test_events.py:1207-1216`) is ten lines already, and
`prose` blocks a docstring over ten (`.saffron/gates/prose.py:63`). So
rewrite it within ten lines, naming this spec where `SA-0085` is named.

**Comments that become false.** `TerminalReason`'s comments
(`saffron/events.py:91-104`) and `Terminal`'s docstring (`:310-320`) say each
cut-off reason is the turn ceiling's and ends in `NOT_IMPLEMENTED`. The
comments at `saffron/cell/session.py:1991-1997` and `:2105-2109` say the
same. The comment over `SALVAGE_MAX_TURNS` (`saffron/phases/implement.py:40-47`)
says the salvage is spent only at the turn ceiling. Correct each comment
in a line or two, and change nothing else in `saffron/phases/implement.py`.
`Terminal`'s docstring is ten lines already, the most `prose` allows, so
rewrite it within ten lines rather than adding one. Keep every docstring you
touch, the three tests' below included, within ten lines.

**Three existing tests assert the old state.** Each ends `NOT_IMPLEMENTED`
after a turn-ceiling cut with nothing committed:
`test_a_cut_off_turn_over_budget_is_not_salvaged` (`tests/test_session.py:1378`),
`test_a_salvage_turn_that_still_commits_nothing_is_not_implemented` (`:1401`)
and `test_a_checkpoint_the_repo_refuses_is_not_an_infrastructure_abort`
(`:1581`). Each runs in a fresh ledger, so each is a first cut. Change their
state assertions to `ORPHANED` and fix their docstrings. Keep every test's
name, since `census` fails a removed one.

**The witnesses.** Build all four on `_stub_the_runtime` (`tests/test_session.py:672`)
and `_drive` (`:966`), as the salvage tests at `:1336-1634` do.

- Add one helper beside `_cut_off_turn` (`tests/test_session.py:924`) that returns the
  `AgentFailed` `run_agent` raises for a wall cut, with the attempt fields
  the Context lists. Never set `terminal_reason` or `subtype` to a turn
  ceiling's values on it.
- Criterion 1 scripts the plan turn, the wall cut and a clean salvage turn,
  with `commits=[0, 1]`. Assert the outcome, the third prompt, the third
  turn's resume id and `max_turns`, and the one announcing line.
- Criterion 2 runs five cells in one `def`, each under its own subdirectory
  of `tmp_path`, so each has its own ledger. Use
  `commits=0`. Leave budget for the salvage turn on two cells, and give the
  other two a budget their cut turn's cost reaches. Read the state from the
  ledger's `tasks` table, as `tests/test_session.py:3602` does. Check the turn
  count: three where the salvage ran, two where it did not. Select the one
  announcing or refusing line per cell and assert on its bound. The fifth
  cell's idle cut is the wall helper's attempt with `bound="idle"`.
- Criteria 3 and 4 call `_drive` more than once on one `tmp_path`, so the
  cells share `tmp_path / "ledger.db"` and the repo's origin. `_drive`
  creates its gates directory with a bare `mkdir` (`tests/test_session.py:999`),
  which raises the second time. Pass `exist_ok=True` there. Give the cells
  their `spec_sha` through `_spec(spec_sha=...)`, and a fresh
  `_stub_the_runtime` each.
- Criterion 3 asserts the three outcomes, the three rows in task order, the
  third cell's turn count, and its one cut-again line naming `task 2`. It
  also asserts that neither earlier cell's watch lines hold that line.
- Criterion 4's killed cell scripts a `RuntimeError` as its implement turn,
  under `pytest.raises`. Build the other three tasks through `Ledger`'s own
  methods on the same file: `create_run`, `create_task`, one `open_attempt`
  with a `phase` and one `close_attempt` per attempt, then `set_task_state`
  and, for the last two only, `finish_run` with `COMPLETE`. Their attempt
  phases are exactly the ones the claim lists, in its order. Take the repo id
  from the killed cell's `repos` row. Close that `Ledger` before the next
  `_drive`. Assert each earlier row's state and run status, the last cell's
  `ORPHANED`, and no cut-again line.
- The fourth task's trailing `IMPLEMENTING` attempt is an order `_drive_cell`
  never writes. `saffron/cell/session.py:199` is the only caller of `open_attempt` a cell
  reaches, and it passes no phase, so each attempt takes the task's state
  (`saffron/ledger.py:995-1004`). `_drive_cell` never moves a task back to
  `IMPLEMENTING` after `saffron/cell/session.py:1772`. So on every ledger a cell writes, "every
  attempt is `IMPLEMENTING`" and "the last attempt is `IMPLEMENTING`" agree.
  The trailing attempt is there only so a cap reading the last attempt
  fails.
- Import `scheduler`'s two sets inside criterion 2's witness body. A
  module-scope import of a name the change adds makes the reverted run a
  collection error, which `revert` reads as `skip`. These two exist at base,
  but keep the habit.
- Each witness is a plain `def`, never parametrised.

**Wrong implementations the witnesses must fail.** A prototype ran each one
against the four witnesses and the three `preserves` ones. Each failed at
least one:

- Salvaging every failed turn: criterion 2's idle cell and the crash test in
  criterion 5 end with a third turn.
- Salvaging a wall cut and still ending it `NOT_IMPLEMENTED`: criterion 2.
- Ending `ORPHANED` on the salvage branch only: criterion 2's no-room cells.
- Returning `ORPHANED` without writing it to the ledger: criterion 2.
- A fixed "turn ceiling" in either line: criteria 1 and 2.
- No cap, or a cap with no cut-again line: criterion 3.
- A cap keyed on the spec id without its `spec_sha`: criterion 3.
- A cap on any earlier `ORPHANED` task, or one missing either the run's
  status or the attempts' phase: criterion 4.
- A cap needing only some attempt in `IMPLEMENTING`: criterion 4, through
  the `REVIEWING` and `REBUTTING` tasks.
- A cap reading only the last attempt's phase: criterion 4, through the
  `REBUTTING` task's trailing attempt. It passed every witness until that
  attempt was added.

One passes. Keying the wall on the exception's message passes, since the
helper's message is `run_agent`'s, and it reads the same fact in production.
Key on `bound` anyway, as the runtime sets it.

**Where `SA-0125` meets this spec.** Read `SA-0125` before starting. Its diff
is in your tree.

- `saffron/cell/session.py`: it edits `plan_checkpoint` (`:433-548` at this
  base) and the call in `_drive_cell` (`:1792-1799`). It also edits the
  `PLAN_REJECTED` branch's `effective_risk` (`:1873`), to read the tier
  `PlanRejected` carries on its instance. This spec edits none of them.
  Every line this spec cites past `:433` moves by what it adds.
- `saffron/agents/artifacts.py` and `tests/test_artifacts.py`: `SA-0125`
  sets the tier on `PlanRejected` and adds a behavioural half to its
  criterion 4 witness there. This spec touches neither file.
- `saffron/events.py`: both add a `FAMILIES` row, at different places. Keep
  both rows.
- `tests/test_events.py`: both move the count in
  `test_the_table_did_not_quietly_lose_a_row` (`:1217-1218` at this base).
  After `SA-0125` it reads 64. Set it to 65.
- `tests/test_session.py`: `SA-0125` edits ten `plan_checkpoint` calls from
  `:282` to `:3517` and adds three witnesses. Its criterion 3 witness drives
  `_drive` three times, each in its own subdirectory, so the `exist_ok` this
  spec adds to `_drive` changes nothing for it. This spec's cited lines past
  `:282` move. Find each test and helper by its name.

**Commit as each witness passes**, before any full-suite run. Two cells of
this item's own record lost everything to the wall during a final suite.

**Size.** A prototype of this change at `46d2cd56`, without `SA-0125`,
measured 285 changed lines. That is 65 in `session.py`, 19 in `events.py`,
191 in `tests/test_session.py` and 10 in `tests/test_events.py`, with short
docstrings. The one comment in `saffron/phases/implement.py` adds about 4.
The diff is measured from `SA-0125`'s head, so none of its lines count here.
The `size` gate blocks at `elevated`, and a `feature` gets 600. Keep new
docstrings to one or two lines.

**Why `feature`.** `SA-0028`, the salvage turn this extends, was one.
