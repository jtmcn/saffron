---
id: b-980fbd
title: "The record append event's sink skips redaction, and `watch` still says `Ceilings` comes first"
status: open
tier: 3
filed: 2026-11-06
specs: [SA-0336]
prs: []
commits: []
cites: [§4.3]
related: [b-6677b6]
---

## Problem

Found by the review seats on #1026 (`SA-0336`), in the spec loop's run 54.

- `_record_events` builds `EventLog` with no token (`saffron/cli.py:121`), so
  its lines skip credential redaction. `RecordAppend` carries only a spec id,
  a fact kind and a key today, so nothing leaks yet.
- `saffron/watch.py:26-28` and `:120-121` still say `Ceilings` is a task log's
  first line. A `RecordAppend` line now comes first. The spec named this out
  of scope.
- A fact whose key no `tasks` row carries makes `row["spec_id"]` raise a bare
  `TypeError`. No write method reaches it today.

## Done looks like

The sink redacts as every other `EventLog` does. `watch` names the first line
a task log holds. A missing row raises the named error `_build_fact` raises.

## Record

- 2026-11-06: filed from the spec loop's run 54.
