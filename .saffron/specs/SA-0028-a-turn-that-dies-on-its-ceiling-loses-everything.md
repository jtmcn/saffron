---
id: SA-0028
title: an implement turn that dies on its own turn ceiling with nothing committed loses the whole run, and the host has both facts
type: feature
priority: 1
touches:
  - saffron/cell/session.py
  - saffron/phases/implement.py
  - tests/test_session.py
  - tests/test_implement.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/gates/**
  - saffron/report/**
  - saffron/scheduler.py
  - saffron/cli.py
  - saffron/reconcile.py
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
A cell's commits are the run. `export_patch` diffs `tree_base..HEAD`, so
uncommitted work is invisible to the record and dies with the volume (§5.1);
`patch.diff` is the only thing that survives teardown. The gates, meanwhile,
run against `/work`, where uncommitted work is fully live — the gap the
`committed` core gate closed on 2026-08-23.

`committed` runs at GATE. A run that dies inside IMPLEMENT never reaches it,
and there is no control at all for a cell that never produces a commit to gate.

## Problem
**Measured, once, and it cost a whole task.** Ledger task 24, `SA-0025`,
2026-09-01, `NOT_IMPLEMENTED` at $14.61 — the first zero-commit run of the
eight logged. Its two attempt rows say precisely what happened:

| n | turns | cost | subtype | terminal_reason |
|---|---|---|---|---|
| 1 | 36 | $2.93 | `success` | `completed` |
| 2 | 141 | $11.68 | `error_max_turns` | `max_turns` |

The plan was accepted and was good; the implement turn ran to its ceiling while
trimming the diff to fit `size`, having committed nothing. `teardown: no
commits, nothing to export`, and $5.39 of the budget was still unspent — **the
turn ceiling bound, not the dollars.**

- **The host holds both facts at the moment it gives up.**
  `session.py` reads `terminal_reason` off the turn and `commits_ahead` off the
  worktree, and the two together are unambiguous: the agent did not decide it
  was finished, it was cut off, and everything it did is still in `/work`. The
  code sets `NOT_IMPLEMENTED` and returns. Nothing tries.
- **The session is still alive and the work is still there.** `session_id` is
  in hand, the container is up, the worktree is intact, and the budget has room
  — every precondition for one more turn is already satisfied. The cost of the
  attempt is one turn; the cost of not making it is everything the run did.
- **A turn ceiling is not a verdict.** `RATE_LIMITED` is not `EXHAUSTED` for
  the same reason: a provider ceiling and a task that could not pass its gates
  are different outcomes and must say different things. A task cut off
  mid-implementation and a task whose agent finished and produced nothing are
  likewise different, and today both are `NOT_IMPLEMENTED`.

## Acceptance criteria
- [ ] When an implement turn ends on its turn ceiling **and** the worktree is
      zero commits ahead, the host spends one more turn — resumed on the same
      `session_id`, so the agent keeps the work it has — whose only instruction
      is to commit what exists now
- [ ] That turn is bounded far below the implement turn's own ceiling: it is a
      salvage, not a second implementation, and a salvage that can itself run
      to 140 turns is the defect again
- [ ] The turn is spent **only** on that pair of conditions. A turn that
      completed on its own and produced no commits gets no second chance: the
      agent decided it was done, and §4.3's "doneness is measured, never
      reported" is not weakened into "measured, then argued with"
- [ ] It is charged like any other turn — the cost is added to `spent`, and the
      budget ceiling is honoured before it is spent, never after
- [ ] If the budget cannot afford it, the task ends as it does today and the
      watch line says which ceiling stopped it — `SA-0005`'s lesson, that a run
      stopped by one of three ceilings must say which
- [ ] Commits after the salvage turn are measured the same way as before, from
      the plan turn's head: a salvage that produces a commit is an ordinary
      run continuing into GATE, not a special state
- [ ] A salvage that produces nothing still ends `NOT_IMPLEMENTED`, and the
      watch line distinguishes "was cut off and could not be salvaged" from
      "finished and produced nothing" — the two facts this spec exists to stop
      collapsing
- [ ] The three paths are covered by tests that drive `session.py`'s own logic
      with real attempt results — cut-off-and-salvaged, cut-off-and-not,
      completed-with-nothing — and none of them starts a cell
- [ ] `docs/BACKLOG.md` records the measurement above, what this control does
      not cover, and the decision below about uncommitted work at teardown

## Out of scope
**Salvaging the worktree at teardown.** The tempting second half — when there
are no commits but `/work` is dirty, export the working-tree diff anyway — is
**not** this spec, and the reason is an invariant: control artifacts are
extracted the moment they are produced, and *a file left in the workspace is a
claim, not a record*. A working-tree diff that reaches `patch.diff` would be
packaged as though it had passed gates it never faced. If it is worth having,
it is a diagnostic under its own name that PACKAGE never reads, and it is worth
its own spec. Record the decision under criterion 9; do not build it.

**Steering a turn while it runs.** The host streams the agent's events and
could count turns live, but it cannot inject an instruction mid-turn — the
session takes one prompt. The control belongs at the turn boundary, which is
where the host already owns one (the plan checkpoint, §5.3). Do not add a
second channel into a running turn.

**Raising the turn ceiling, or spending the leftover budget on more
implementation.** The failed run did not need more turns; it needed to have
committed at turn 20. A control that answers "cut off" with "keep going"
converts one wasted task into a more expensive one.

**The repair loop, GATE, and everything after.** `committed` already governs a
dirty tree at gate time and is correct. This spec is only the gap before it.

## Notes for the agent
**Commit after every coherent step, before you run anything by hand.** This is
not the usual closing line — it is the defect. The run this spec is written
from made zero commits across 141 turns and lost all of it at teardown, $14.61
for nothing. You are working in the module that failed to save it.

**Your budget is the turn ceiling, not the dollars.** That same run stopped at
141 turns with $5.39 unspent. Reading a file twice costs a turn as surely as
writing one.

**`session.py` is the most delicate module in the repository, and its shape is
load-bearing.** `commits_ahead(container, planned_sha)` measures from the plan
turn's head, not `base_sha`, because the plan turn holds Write and Edit and a
prompt is not a boundary (§4.3). `_failed_turn` exists because a bound firing
must never discard committed work. Read why each line is where it is before
moving any of them; several exist because a live run found something.

**`terminal_reason` is already recorded and already distinguishes this case.**
`close_attempt` writes it, and the failed run's row says `max_turns` against
`subtype: error_max_turns`. You are adding a branch on a fact the ledger has
been carrying all along, not a new measurement.

**A test that constructs the state it then asserts on proves nothing.** Drive
the real branch with a real `AttemptResult` carrying a real terminal reason and
a worktree stub that reports zero commits, and assert on the turn that was
actually requested — its prompt, its bound, and that it resumed the session
rather than starting one.

**The documentation half is by hand.** `DESIGN.md` §5.3's account of IMPLEMENT
describes one checkpoint; §4.3's "doneness is measured, never reported" gains a
qualification that is worth stating precisely rather than leaving implied. Both
are `forbidden` here, so an operator writes them.
