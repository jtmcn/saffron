---
id: 67
title: '`--until` does not stop a running cell, and §4.5 says it does'
status: open
tier: 2
specs: [SA-0054]
prs: [123]
commits: []
cites: [§4.5]
related: []
---

## Problem

**Tier 2.** Found reviewing `SA-0054` (PR #123).

`run_batch` checks the deadline between candidates, and `run_one_cell` takes no
deadline argument at all — so a cell already running at 06:30 runs to its own
`max_turns` and `max_attempts`. The wall-clock end of a night is therefore the
deadline plus at most one task, which can be hours.

`DESIGN.md` §4.5 states the opposite: *"The supervisor sets [`ORPHANED`] on
kill, on crash, and on `--until`."* Two documents now disagree in writing, and
the code matches the weaker one.

`docs/HOST-HARDENING.md` §4a was amended to describe the real behaviour — a
"start no new task after" bound — so an operator reading the setup guide is not
misled today. That is a patch over the gap, not the gap closed.

**Done looks like** one of two decisions taken deliberately and written down:
either the supervisor gains a deadline and stamps `ORPHANED` when it passes, and
§4.5 stands; or §4.5 is amended to say the bound is between tasks, and the
budget is named as the ceiling that actually holds unattended. The second is
cheaper and defensible — a killed cell mid-REBUT wastes everything it spent —
but it should be a decision, not a drift.
