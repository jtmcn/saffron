---
id: 119
title: A turn ceiling reached before the first commit still loses the work when the budget is spent, and planning can spend half of it first
status: open
tier: 1
specs: [SA-0086, SA-0087]
prs: []
commits: []
cites: []
related: [18, 120]
---

## Problem

**Tier 1.** Found running the spec loop, 2026-09-14 (its second run). Item 18
closed "turn exhaustion is total loss" with a salvage turn and a prompt asking
for a commit per coherent step. Both cells of this run still reached their
IMPLEMENT turn ceiling with nothing committed:

| spec | plan checkpoint | IMPLEMENT session | at the ceiling | outcome |
|---|---|---|---|---|
| `SA-0086` | 20 turns, $1.82 | 41 turns, $2.33 | $4.15 of $6 | the salvage turn (3 turns, $0.17) committed it; `READY_FOR_REVIEW`, #255 |
| `SA-0087` | 47 turns, $3.79 | 61 turns, $4.59 | $8.39 of $8 | `cut_off_no_salvage_room`; `NOT_IMPLEMENTED`, nothing exported |

`SA-0087`'s last 30 turns ran the full suite, `ruff`, `types`, `ast-grep test`,
`structure` and a size check. Turn 61 was `git diff --stat`, and no `git commit`
ever ran (`~/.saffron/batches/v0/SA-0087/events.jsonl`). The salvage exists,
and it was refused for money, not turns (`saffron/cell/session.py`, the
`cut_off_no_salvage_room` branch). The plan checkpoint had spent 45% of the
budget before a line was written.

**Done looks like** the salvage turn's cost reserved out of IMPLEMENT's
`max_budget_usd`, so a turn ceiling can always be salvaged, and a measured
answer on whether the plan checkpoint's spend belongs in the budget IMPLEMENT is
judged against. Raising the spec's ceilings (#256) was the workaround, and it
moved the shortfall to REBUT (item 120).
