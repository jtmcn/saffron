---
id: b-62e00a
title: "`FAMILIES` claims to cover every event call site and has no row for three `Preflight` steps"
status: open
tier: 3
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§4.7]
related: []
---

## Problem

Found by the Standards seat on #910, in the spec loop's run 44, and verified
by the delegate.

`FAMILIES` in `saffron/events.py` is the table that proves the kinds cover
every call site (`tests/test_events.py:1375-1388`). `_drive_cell` emits three
`Preflight` steps it has no row for. They are `thread_env`, which `SA-0282`
(#910) added (`saffron/cell/session.py:2190`), `spec_drift` (`:2197`) and
`refused` (`:3708`). The tests check each row against the code, and the row
count. No test checks each call site against the rows.

## Done looks like

Each `Preflight` step has a row. A test finds every `_preflight(` call site
and fails on a step no row names.

## Record

- 2026-10-19: filed from the spec loop's run 44.
