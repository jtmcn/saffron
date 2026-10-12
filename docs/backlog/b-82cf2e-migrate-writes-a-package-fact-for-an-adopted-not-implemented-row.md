---
id: b-82cf2e
title: "`migrate` writes a `task_package` fact claiming `READY_FOR_REVIEW` for an adopted `NOT_IMPLEMENTED` row"
status: open
tier: 2
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§4.1]
related: [b-a7e5f3]
---

## Problem

Found by the contract lens and both seats on #830 (`SA-0264`), in the spec
loop's run 35.

`saffron adopt` lets a `NOT_IMPLEMENTED` task carry a `pr_url`. In
`saffron/record/migrate.py`, `_PACKAGED` (line 439) does not hold
`NOT_IMPLEMENTED`. So `_outcome_facts` writes such a row's `task_package`
fact with `state: "READY_FOR_REVIEW"` (lines 452-453). A later `task_state`
fact restores `NOT_IMPLEMENTED`, so the fold lands right. The record still
holds a fact for a PACKAGE run that never happened. `saffron/record/**`
was forbidden to `SA-0264`.

## Done looks like

- An adopted `NOT_IMPLEMENTED` row migrates to facts that name its own
  state at every step.
- A test migrates such a row and reads each fact's state.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#830).
