---
id: SA-0126
title: An implement turn the wall clock cuts gets no salvage turn, and a cut that leaves nothing committed settles its spec as `NOT_IMPLEMENTED`
type: feature
priority: 1
depends_on: []
touches:
  - saffron/cell/session.py
  - saffron/events.py
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
  - saffron/phases/**
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
budget_usd: 22
max_attempts: 3
max_turns: 130
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
      An IMPLEMENT turn cut by the turn ceiling or by the wall clock that
      leaves nothing committed ends `ORPHANED`, in the returned outcome and on
      the task's ledger row. The witness drives all four such paths, each in
      its own cell: a turn cut and a wall cut whose salvage turn recovers
      nothing, and a turn cut and a wall cut with no budget left for one. On
      each, the watch line that announces the salvage turn or refuses it for
      budget names the bound that cut the turn, "turn ceiling" or "wall", and
      not the other. `ORPHANED` is in `scheduler.REQUEUE_STATES` and not in
      `scheduler.DONE_STATES`, so the next scan re-queues the task. A fifth
      cell, whose implement turn the idle bound cuts with nothing committed,
      still ends `NOT_IMPLEMENTED` after two turns. Today all four cut paths
      end `NOT_IMPLEMENTED`.
    witness: tests/test_session.py::test_every_cut_that_leaves_nothing_committed_halts_for_the_next_scan
    mutant:
      file: saffron/cell/session.py
      find: 'attempt.terminal_reason == "max_turns" or attempt.subtype == "error_max_turns"'
      replace: 'attempt.terminal_reason == "max_turns" and attempt.subtype == "no-such"'
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
re-measures commits from the plan turn's head (`:2089`). A turn-ceiling cut whose salvage recovers nothing, or
that has no budget for one, still ends `NOT_IMPLEMENTED`.

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
(`saffron/cell/session.py:2763-2765`).

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

**Measured, not reasoned:** a session cut by the wall resumes. In `SA-0117`'s
cell (`~/.saffron/batches/v0/SA-0117/events.jsonl`), line 806 reaps the cell
after a wall cut in IMPLEMENT. Session `8bb7393a` carries events from line 27
before the cut to line 3491 after it, the REPAIR turns included.

## Problem

A bound cutting a turn is a fact about the turn, not about the spec (§4.3: "A
timeout must never discard committed work"). Today the wall clock throws away
uncommitted work that the turn ceiling saves. And a cut by either bound that
leaves nothing committed settles the spec, as a tried and failed one.

## Out of scope

- **The implement prompt.** The item also asks that
  `saffron/agents/prompts/implement.md` name the unit of a commit. A prompt
  change needs a measured pass (`.github/pull_request_template.md`), so the
  item closes partial and that half stays open on it.
- **The idle bound.** An idle cut is a stall, not a turn that ran out of
  time. It keeps ending `ended_without_finishing` and `NOT_IMPLEMENTED`, with
  no salvage turn. Criterion 2's fifth cell pins that.
- **The plan turn.** A plan turn that any bound cuts still ends
  `NOT_IMPLEMENTED` at `saffron/cell/session.py:1876-1897`. It has no salvage
  turn, and nothing is committed before a plan exists.
- **REPAIR and REBUT turns.** Their own host checkpoint keeps dirty work
  already (`saffron/cell/session.py:2209-2230`).
- **The cut turn's spend.** Item b-36b551's record says `SA-0117`'s cut turn
  reports $1.52 and the ledger books it as zero turns. That accounting is
  another item.
- **The comment over `SALVAGE_MAX_TURNS`** (`saffron/phases/implement.py:40-47`)
  still says only the turn ceiling earns a salvage. `SA-0125`, drafted in
  parallel, can edit that file. So this spec forbids it, and the operator
  corrects the comment by hand.
- **`CONTEXT.md` and `DESIGN.md`.** `CONTEXT.md` §6 says each `TerminalEvent`
  reason ends in `PLAN_REJECTED` or `NOT_IMPLEMENTED`, and defines `ORPHANED`
  as a cell killed or crashed. `DESIGN.md` §4.5 lists when the supervisor
  stamps `ORPHANED`. All three become incomplete here. Both files are
  protected, and backlog item b-149df3 owns them, by hand.
- **The spec loop's watch pattern**
  (`.claude/skills/run-saffron-spec-loop/driver.py:810-818`) anchors only
  terminal states, and `ORPHANED` is not one. A change there belongs to
  the loop, not to this spec.

## Notes for the agent

**Which criteria carry mutants.** This change edits existing code, but the
text the fix lands in is not forced. No spelling of the salvage branch's
condition is forced, and none of the zero-commit return's state. So
criterion 1 declares a witness alone, and `witness` reports `skip` for it.
Criterion 2's mutant pins `cut_off_at_turn_ceiling`'s own expression, which
this spec keeps. Leave that function's body and name as they are. Its four
unit tests (`tests/test_session.py:72-123`) and the loop driver's copy of its
rule (`.claude/skills/run-saffron-spec-loop/driver.py:1646-1653`) both read it.

**Where the change goes.** All of it is in `_drive_cell`'s zero-commit block,
`saffron/cell/session.py:1977-2145`. Decide once, from the implement turn's
attempt, whether a bound cut it and which one. The turn ceiling is
`cut_off_at_turn_ceiling`. The wall clock is the attempt's `bound` reading
`"wall"`. Only these two earn the salvage turn. Use that one decision for the
salvage branch and for the state the zero-commit return writes.

**The two watch lines.** The salvage announcement is `_phase_start`'s detail
at `saffron/cell/session.py:2009-2014`. The budget refusal renders `Terminal`'s
`cut_off_no_salvage_room` in `saffron/events.py:812-816`, and its fixed text
says "turn ceiling" today. Carry the bound through `detail`, and keep
`Terminal`'s fields as they are. Two tests pin the rendered text:
`tests/test_events.py:1076-1086` and `:1585-1597`. Update both. The first is
a case of `test_describe_renders_every_kind_and_variant`, whose ids are the
expected line's first 24 characters (`tests/test_events.py:1151-1153`). Keep
those 24 characters as they are, or the case's id changes and `census` reads
a test as removed.

**Comments that become false.** `TerminalReason`'s comments
(`saffron/events.py:91-104`) and `Terminal`'s docstring (`:310-320`) say each
cut-off reason is the turn ceiling's and ends in `NOT_IMPLEMENTED`. The
comments at `saffron/cell/session.py:1991-1997` and `:2105-2109` say the
same. Correct each one in a line or two.

**Three existing tests assert the old state.** Each ends `NOT_IMPLEMENTED`
after a turn-ceiling cut with nothing committed:
`test_a_cut_off_turn_over_budget_is_not_salvaged` (`tests/test_session.py:1378`),
`test_a_salvage_turn_that_still_commits_nothing_is_not_implemented` (`:1401`)
and `test_a_checkpoint_the_repo_refuses_is_not_an_infrastructure_abort`
(`:1581`). Change their state assertions to `ORPHANED` and fix their
docstrings. Keep every test's name, since `census` fails a removed one.

**The witnesses.** Build both on `_stub_the_runtime` (`tests/test_session.py:672`)
and `_drive` (`:966`), as the salvage tests at `:1336-1634` do.

- Add one helper beside `_cut_off_turn` (`tests/test_session.py:924`) that returns the
  `AgentFailed` `run_agent` raises for a wall cut, with the attempt fields
  the Context lists. Never set `terminal_reason` or `subtype` to a turn
  ceiling's values on it.
- Criterion 1 scripts the plan turn, the wall cut and a clean salvage turn,
  with `commits=[0, 1]`. Assert the outcome, the third prompt, the third
  turn's resume id and `max_turns`, and the one announcing line.
- Criterion 2 runs five cells in one `def`, each under its own subdirectory
  of `tmp_path`, since `_drive` creates `tmp_path / "repo"`. Use
  `commits=0`. Leave budget for the salvage turn on two cells, and give the
  other two a budget their cut turn's cost reaches. Read the state from the
  ledger's `tasks` table, as `tests/test_session.py:3602` does. Check the turn
  count: three where the salvage ran, two where it did not. Select the one
  announcing or refusing line per cell and assert on its bound. The fifth
  cell's idle cut is the wall helper's attempt with `bound="idle"`.
- Import `scheduler`'s two sets inside the witness body. A module-scope
  import of a name the change adds makes the reverted run a collection error,
  which `revert` reads as `skip`. These two exist at base, but keep the habit.
- Each witness is a plain `def`, never parametrised.

**Wrong implementations the witnesses must fail.**

- Salvaging every failed turn: criterion 2's idle cell and the crash test in
  criterion 3 end with a third turn.
- Salvaging a wall cut and still ending it `NOT_IMPLEMENTED`: criterion 2's
  wall cells.
- Ending `ORPHANED` on the salvage branch only: criterion 2's two no-room
  cells.
- Returning `ORPHANED` without writing it to the ledger: criterion 2 reads
  the row.
- A fixed "turn ceiling" in either line: criterion 2's wall cells, and
  criterion 1.
- Keying the wall on the exception's message: the witness helper's message
  is `run_agent`'s, so this passes. It also reads the same fact in
  production. Key on `bound` anyway, as the runtime sets it.

**Commit as each witness passes**, before any full-suite run. Two cells of
this item's own record lost everything to the wall during a final suite.

**Size.** A prototype of this change measured 163 changed lines: 36 in
`session.py`, 18 in `events.py`, 103 in `tests/test_session.py` and 6 in
`tests/test_events.py`. The `size` gate blocks at `elevated`, and a
`feature` gets 600. Keep new docstrings to one or two lines.

**Why `feature`.** `SA-0028`, the salvage turn this extends, was one.
