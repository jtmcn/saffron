---
id: 146
title: The per-turn token counts ride on the one event most likely to be dropped from the log
status: open
tier: 2
filed: 2026-09-16
by_hand: false
specs: [SA-0090]
prs: [278]
commits: []
cites: [§7.1]
related: [126]
---

## Problem

**Tier 2.** Found reviewing `SA-0090` (PR #278), by reading the two call paths;
not measured.

`SA-0090` attaches the per-turn counts to `evts[0]` — the first event an
assistant message produces. For a text block that event carries the message text
**unclipped**: `_clip` is applied to tool input, not to text.

`saffron/events.py` replaces any `Agent.event` whose `json.dumps` exceeds
`BOUND_CHARS` (8192) with `event=None` plus a truncated line. So a long assistant
message's token counts never reach the log as data — and a long assistant message
is exactly the turn whose counts are most worth having.

The `result` event is unaffected: it is always small, so the session totals
survive. What is lost is the per-turn series, on precisely its most interesting
points.

`saffron/**` is `forbidden` in `SA-0090`, so the cell could not have placed them
elsewhere.

## Done looks like

The counts carried somewhere the bound cannot drop them — their own small event,
or a field on the envelope rather than inside `event` — with a test that a
message over `BOUND_CHARS` still reports its counts.
