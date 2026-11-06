---
id: b-0add4c
title: "The record's git calls can prompt for credentials, and a refused write drops git's reason"
status: open
tier: 2
filed: 2026-11-06
specs: [SA-0334]
prs: []
commits: []
cites: [§2.1]
related: [b-d4b847]
---

## Problem

Found by both review seats on #1024 (`SA-0334`), in the spec loop's run 54.

- `RefsRecord.fetch` and `_push` run git with no `GIT_TERMINAL_PROMPT=0`
  (`saffron/record/refs.py:142-152`). The new `_fetch_one` sets it. A routed
  push to an origin that wants credentials can still prompt and hang.
- `GIT_TERMINAL_PROMPT=0` stops only git's own prompt. An ssh origin can
  still prompt unless `GIT_SSH_COMMAND` carries `-o BatchMode=yes`.
  Unverified.
- `_recover` wraps its fetch in `contextlib.suppress(RecordError)`. The
  refusal then says "is absent here" even when the origin was unreachable.
  A stopped `reconcile` then gives no hint that the forge was the cause.

## Done looks like

Every git call the record makes sets both guards, and a test drives each
one against an origin that would prompt. A refused write chains the fetch's
own error, so its text names git's reason.

## Record

- 2026-11-06: filed from the spec loop's run 54.
