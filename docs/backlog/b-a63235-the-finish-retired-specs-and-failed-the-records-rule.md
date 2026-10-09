---
id: b-a63235
title: The finishing layer retired each layer's spec, so every finish with an open item failed this repo's records rule
status: done
tier: 2
filed: 2026-10-08
closed: 2026-10-08
specs: []
prs: []
commits: [14cfda1d6be547fcdd603744286e55819247e212]
cites: [§4.2.1]
related: [b-fe82d9, b-b0cd68, b-fdbedc]
---

## Problem

Measured on batch 19's finishing commit `ecf59477`, in the spec loop's run 31.

That commit only moved SA-0225 and SA-0228 into `.saffron/specs/done/`.
`test_the_backlog_records_hold` refuses a spec in `done/` whose item is still
`open`, and both items were. The finish can write spec files only, so it could
never close them. Every finish whose specs had open items failed its own
suite and pushed nothing.

## Done looks like

The finishing commit writes spec texts and moves no spec. `FINISH_TOUCHES`
names the spec directory alone. ADR 7 says the operator retires each spec with
the item it closes.

## Record

- 2026-10-08: filed and done in one commit, before the 25-spec stack runs as a
  batch.
