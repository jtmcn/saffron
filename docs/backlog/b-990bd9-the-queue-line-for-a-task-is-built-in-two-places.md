---
id: b-990bd9
title: A task's queue line is built in two places, so a new field must be added twice
status: open
tier: 3
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§6]
related: [165]
---

## Problem

Found in the spec loop's run 7, 2026-09-18, reviewing #339 (`SA-0100`).

At `origin/saffron/SA-0100`, two sites construct a `QueueLine` for a task.
`saffron/task.py:357-374` writes the row for a task that never reached PACKAGE.
`_finish` in `saffron/phases/package.py:955-983` writes the row for a packaged
one. Both pass the same 13 fields and repeat the same three derivations:
`anchored_concerns`, `sustained_blockers` and `unkept_fixes`. They differ only in
`state`, the diff stat, `link` and `note`.

A new `QueueLine` field must be added at both sites, and nothing fails when one
is missed. The field defaults in `saffron/report/index.py` make a missed site
silent rather than a `TypeError`.

A shared builder was out of reach for `SA-0100`. Its `forbidden:` list names
`saffron/phases/**` and `saffron/report/**`.

## Done looks like

One function builds a task's `QueueLine` from its outcome, and both sites call
it with what differs. A test adds nothing new but asserts both rows agree on
every field the two paths share.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by #339.
