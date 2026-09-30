---
id: b-c07b92
title: Scoping a spec loop takes one `drop` per spec left, and a drop reads as permanent
status: open
tier: 2
filed: 2026-09-28
closed:
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [172]
---

## Problem

Found in the spec loop's run 20, 2026-09-28.

The operator stopped run 20 after `SA-0164`. That took eleven `drop` calls
(`cmd_drop`, `.claude/skills/run-saffron-spec-loop/driver.py:1418`), one per
spec left. A drop reads as a verdict on the spec, not a scope for this loop.
Item 172 carries drops across `snapshot --force` (`_carried`, `:484`).

## Done looks like

One command stops a loop after a named spec and leaves the rest queued for the
next loop. No drop is recorded for them, and `snapshot --new` picks them up.

## Record

- 2026-09-28: filed from the spec loop's run 20.
- 2026-09-29: hit again in the spec loop's run 21. Scoping it to `SA-0187`'s
  chain of six took eleven `drop` calls.
- 2026-09-29: hit again in the spec loop's run 22. `snapshot` put nine chain
  specs before `SA-0193` by priority and offers no operator order. The
  delegate held `SA-0161` to run the four new specs first.
