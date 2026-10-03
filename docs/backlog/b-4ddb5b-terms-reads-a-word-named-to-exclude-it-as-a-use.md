---
id: b-4ddb5b
title: "`terms` reads a word named to exclude it as a use, so it fails at base in every cell"
status: open
tier: 3
filed: 2026-09-30
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

Found in the spec loop's run 23, 2026-09-30.

Every run-23 cell's baseline read `terms=fail`. The one hit is
`saffron/intake.py:158`, the docstring "The unit of work. Never a ticket, an
issue, or a prompt." It names "ticket" to rule the word out.
`.saffron/gates/prose.py`'s `terms` table cannot tell a disavowal from a use.

`terms` is advisory (`.saffron/policy.yaml`), so no cell pays. But a gate
that fails at base on a correct sentence teaches every reader to ignore it.
The loop's skill also treats any base `fail` other than `prose` as red on
`main`.

## Done looks like

`terms` passes at base. Either the gate exempts a disavowal it can
recognise, or the sentence is reworded. A test pins whichever it is.

## Record

- 2026-09-30: filed from the spec loop's run 23.
- 2026-10-03: all three of run 26's cells read `terms=fail` at base on
  `saffron/intake.py:158` again.
