---
id: b-fdbedc
title: Retiring a spec and closing its item stay a hand step, because the finish cannot write a repo's records
status: open
tier: 2
filed: 2026-10-08
specs: []
prs: []
commits: []
cites: [§2.1, §4.2.1]
related: [b-fe82d9, b-b0cd68, b-a63235]
---

## Problem

Measured on batch 19's finishing commit `ecf59477`, in the spec loop's run 31.

The finish once moved each layer's spec to `.saffron/specs/done/`. This
repo's records rule refuses a spec in `done/` whose backlog item is still
`open` (`tests/records/check.py:494`). The finish can write spec files only,
and core knows nothing of `docs/backlog/`. So every finish with an open item
failed its own gate suite. b-a63235 took the move out of the finish. The
delegate now retires each spec and closes its item by hand, in the step-5
pull request above the stack.

That is the second repo rule a finish's retirement broke. b-b0cd68 was the
first.

## Done looks like

A repo declares a retirement step in `.saffron/`. The finish runs it on its
own commit, from the repo's trusted copy and never from the stack's tree.
The step retires each shipped spec and closes the items it names, so the
finishing layer's suite stays green. A stack batch then needs no hand commit
for retirement.

## Record

- 2026-10-08: filed while diagnosing b-fe82d9, after b-a63235 removed the
  finish's own retirement.
