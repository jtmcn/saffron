---
id: b-c7858c
title: '`driver.py cite` reads a plain line citation as ok after the code it named moved'
status: open
tier: 2
filed: 2026-11-08
specs: []
prs: []
commits: []
cites: []
related: [b-d31930, b-2da959]
---

## Problem

Found in the spec loop's run 55.

Batch 72 refused `SA-0341` on citations into code `SA-0340` rewrote, and
`SA-0353` and `SA-0354` on citations into `saffron/cli.py` that the
`SA-0350` and `SA-0352` layers moved. `cite` passes a plain `file:line`
citation whenever the line still exists. A difflib old-to-new line map over
the parent's diff found all 13 of `SA-0341`'s moved citations in seconds.

## Done looks like

When a spec's parent has a branch, `cite` maps each citation through the
parent's diff and reports every one that moved or whose text changed. A test
shifts a cited line in a parent branch and asserts `cite` names it.

## Record

- 2026-11-08: filed from the spec loop's run 55.
