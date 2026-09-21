---
id: b-36b551
title: The per-turn wall clock has no salvage turn, and a `NOT_IMPLEMENTED` it caused settles the spec
status: open
tier: 1
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.2.1, §4.3]
related: [119, 34, 4]
---

## Problem

Found in the spec loop's run 8, 2026-09-18.

Every turn runs under `TURN_TIMEOUT_S = 900.0` (`saffron/cell/session.py:58`,
bound at `:1470`). The salvage turn fires only when `cut_off_at_turn_ceiling`
is true (`saffron/cell/session.py:370-389`), which reads `max_turns`. A wall
cut carries no `terminal_reason`, so it gets no salvage turn.

`SA-0107`'s first cell was cut by the wall in IMPLEMENT while it formatted
files it had not committed. It ended `ended_without_finishing`, with 0 commits,
`NOT_IMPLEMENTED` and $5.07 spent (`~/.saffron/batches/v0/SA-0107/events.jsonl`,
lines 1127-1129). All of the work died with the cell. `SA-0106` hit its
100-turn ceiling with 0 commits, and the salvage turn recovered one commit
(`~/.saffron/batches/v0/SA-0106/events.jsonl`, line 829).

`NOT_IMPLEMENTED` is in `DONE_STATES` (`saffron/scheduler.py:63-76`), so the
scheduler and the loop's `record` treat the spec as decided. Nothing decided
it: a ceiling fired.

The implement prompt already asks for a commit after each coherent step
(`saffron/agents/prompts/implement.md:50-55`, item 18). Four of run 8's six
cells still hit a turn or wall bound in IMPLEMENT, and two had nothing
committed. `SA-0107`'s second cell and `SA-0108` carried a spec note asking for
a commit per criterion. The second `SA-0107` cell hit the wall again with two
commits kept, and `SA-0108` hit no bound.

## Done looks like

A wall cut with nothing committed gets the same salvage turn as a turn-ceiling
cut, inside the same budget check. A wall or turn cut with no commits ends in a
halt that the next scan re-queues. It is not recorded as a `NOT_IMPLEMENTED`
verdict. The implement prompt names the unit of a commit (one criterion),
so no spec has to repeat it.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
- 2026-09-21: a recurrence in the spec loop's run 11. `SA-0116`'s implement turn
  made 11 `pytest` calls and no commit, and its last message says its three
  witnesses pass. The 900s turn wall cut it during a final full-suite run.
  Teardown reported "no commits, nothing to export", and it ended
  `NOT_IMPLEMENTED` at $6.63 (task 124). Its spec said "Commit after each coherent
  step", and that did not stop it. The ledger records the cut turn as zero turns.
- 2026-09-21: two more in the spec loop's run 12. `SA-0116` was out of the
  queue with no refusal line, because run 11's `NOT_IMPLEMENTED` settled its
  `spec_sha`. The operator asked where it went. A spec edit (#413) gave it a new
  `spec_sha` and told the cell to commit before any full-suite run. The rerun
  committed twice and reached `READY_FOR_REVIEW` (#416). `SA-0117`'s cell was then
  cut by the wall in both IMPLEMENT and REPAIR. It had committed once before the
  first cut, and the host checkpointed the second. The cut IMPLEMENT turn reports
  $1.52, and the cell's total was $30.70, so the cut turn's spend looks lost.
