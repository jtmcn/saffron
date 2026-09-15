---
id: 63
title: '`describe` renders three agent payload fields unclipped, straight to a terminal'
status: done
tier: 1
closed: 2026-09-12
specs: [SA-0029, SA-0053, SA-0070, SA-0080, SA-0084]
prs: [119, 221, 249]
commits: []
cites: []
related: [61]
---

## Problem

**Status: done for the `Agent` event, with item 61 — `SA-0070`, PR #221, merged
2026-09-12.** It covers the `Agent` event only. `Terminal.detail` on a rejected plan and
`PhaseStart.detail` also carry paths an agent wrote, and they render unclipped
and unstripped. That is the follow-up, found reviewing `SA-0070` (2026-09-11).
Merged, 2026-09-14 — `SA-0084`, PR #249, stacked on `SA-0080`, in stack
#251. It also cleans `ended_without_finishing`'s `subtype` and
`terminal_reason`. `Preflight`, `Teardown` and `Agent.detail` still render raw; the
spec deferred them, and a proxy denial naming a host the cell asked for is the likely
way cell text reaches the first two.

**Tier 3.** Found reviewing `SA-0053` (PR #119). Not a regression — the
attended terminal has had this exposure since `SA-0029` — but that PR added a
*second* consumer, which is what makes it worth filing.

`_describe_agent_event` clips `text` at 160 characters and `tool_use` at 120.
Its `error`, `rate_limit` and fallback branches clip nothing and strip nothing.
An `Agent` event carrying `{"type": "error", "error": "\x1b[2J\x1b]0;…\x07" +
"A"*5000}` renders with the escape bytes intact, which reaches the operator's
terminal as a screen clear and a title change. The content is authored inside a
cell, and CLAUDE.md's governing line is that a cell is untrusted.

`saffron watch` makes it worse in one specific way: it can replay a finished
cell's output into a fresh terminal, long after the run, for an operator who
was not watching when it happened.

**Done looks like** the three unclipped branches clipped like the other two,
and C0 control characters other than nothing at all stripped in `describe` —
once, where the single renderer is, not in each caller.

**Not** escaping in `watch.py`. That is a second renderer by another name, and
it would leave the attended terminal — the one that reads this output during a
live run — still exposed.
