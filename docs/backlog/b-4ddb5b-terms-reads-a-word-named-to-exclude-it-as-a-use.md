---
id: b-4ddb5b
title: "`terms` reads a word named to exclude it as a use, so it fails at base in every cell"
status: done
tier: 3
filed: 2026-09-30
closed: 2026-11-07
specs: []
prs: [720]
commits: ["9823f95f"]
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
- 2026-10-05: every cell of run 28 read `terms=fail` at base on
  `saffron/intake.py:156`, the same docstring after it moved.
- 2026-11-07: closed in grooming. The sentence was reworded in `557c1ab8` (#720), so the `Spec` docstring names no avoided term. `.saffron/gates/terms` passes on HEAD, 0 failures in 959 files. The `terms` prek hook from `SA-0255`'s review (`9823f95f`) runs the gate over the whole tree in `make check`, so a new hit at base fails before it merges.
