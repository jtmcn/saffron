---
id: 164
title: EventLog.failed is the breadcrumb for a log that stopped writing and nothing reads it
status: open
filed: 2026-09-17
specs: [SA-0103]
prs: []
commits: []
cites: [§4.1]
related: [46]
---

## Problem

Found 2026-09-17, reading what a single execution can be seen through.

`EventLog` was built with this failure in mind, and its comments say so twice.
`saffron/events.py` sets the flag in the constructor. Its comment there says "A
disk-full night must not render as a night in which nothing happened". It adds
that `append` "never raises", which is "how anyone can tell". The `except` clause
in `append` catches `OSError`, `RecursionError`, `TypeError` and `ValueError`,
sets the flag, and returns. Its comment reads "`self.failed` is the breadcrumb".

`saffron/cell/session.py:76-83` repeats the reasoning for `_default_emit`. A
disk-full night "just stops growing `events.jsonl`, which `EventLog.failed` is
the breadcrumb for".

Nothing reads it. Searching `saffron/` and `tests/` for the attribute finds the
two comments above, an unrelated `proxy.failed_egress` at
`saffron/cell/session.py:959`, and a test double's own list.

Four places own a log: `saffron/task.py:251`, `saffron/cell/session.py:798`, and
`saffron/phases/package.py:624` and `:1046`. The production one is the first.
`saffron/task.py:247-256` builds the log and a closure `emit` for a caller that
passed none, then hands that closure down. So `session._default_emit` is not the
seam a driven cell uses.

A night where the disk fills therefore produces a task that reaches its terminal
state with a truncated log and says nothing about the truncation. `CLAUDE.md`
names the stake. Under launchd the terminal scroll is "the night's only
human-readable record", and the log is what survives a SIGTERM. When both are
short, nothing distinguishes a quiet night from a lost one.

Item 46 is the neighbour, and `PRIORITY.md` places it in tier 1 as "the only
account of a night nobody watched". Item 46 bounds and scans what the log holds.
This item is about the log that holds nothing and does not say so.

## Done looks like

A task whose log stops accepting writes says so on the terminal, naming the log
that stopped growing. It warns once for the run rather than once per lost event.
A task whose log wrote cleanly says nothing. The warning does not travel through the
log, because the log is what failed. `append` still raises nothing, and a failed
log still changes no task state and no exit code.

## Record

**Filed 2026-09-17**, from an inventory of what one execution can be seen
through. `SA-0103` carries it.
