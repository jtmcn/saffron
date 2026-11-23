---
id: b-0f5493
title: "An event's terminal line prints before its log redacts it, so the cell's token reaches the launchd log file"
status: done
closed: 2026-11-22
tier: 2
filed: 2026-11-20
specs: [SA-0421]
prs: [1296]
commits: []
cites: [§5.7]
related: [b-3a3081, 46]
---
## Problem

Found by `SA-0417`'s first spec review, in the spec loop's run 80.

Both emit paths print `describe(event)` before `log.append` redacts the event
(`saffron/cell/session.py:135-138`, and `saffron/task.py`'s emit closure at
`:803-806`). `describe` renders an `Agent` event's `detail` and `line` as they
came (`saffron/events.py:957-967`). Under `launchd`, stdout goes to
`~/.saffron/batch.out.log` (`docs/host/dev.saffron.batch.plist:58-59`). So the
cell's own token and every listed credential shape reach a host file.
`DESIGN.md` §5.7 names this as residual risk once `SA-0417` lands.

## Done looks like

Each emit path redacts an event with the token it holds before it prints the
event's line. A test prints an `Agent` event that carries the token and a
listed shape, and asserts that neither reaches stdout.

## Record

- 2026-11-20: filed from `SA-0417`'s first spec review. The spec kept it out
  of scope to stay inside its size ceiling.
- 2026-11-22: done. `SA-0421` (#1296) redacts each event with the
  token its emit path holds before it prints the event's line.
