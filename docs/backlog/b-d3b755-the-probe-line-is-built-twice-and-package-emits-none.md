---
id: b-d3b755
title: "The host-probe line is built in two places, and `saffron package` prints it without emitting it to the task's event log"
status: open
tier: 3
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§5.1]
related: [b-883f74]
---

## Problem

Found by the Standards seat on #847 (`SA-0268`), in the spec loop's run 35.

`saffron/task.py:1040-1045` restates the `probing N host ports at ...;
tolerating ...` line that `saffron/cell/session.py:1124-1130` builds.
`SA-0268` could not share it, because both `saffron/cell/**` and
`saffron/preflight.py` were forbidden.

The cell path emits its preflight into `events.jsonl`. `saffron package`
only prints it, so `saffron watch` never shows what it tolerated.

## Done looks like

- One helper in `saffron/preflight.py` builds the line for both callers.
- `saffron package` emits its preflight into the task's event log.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#847).
