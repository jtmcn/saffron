---
id: b-426db4
title: A spec's Problem-item obligation with no criterion is dropped by the cell, and no lens says so
status: open
tier: 2
filed: 2026-10-01
specs: [SA-0162, SA-0151]
prs: [626, 627]
commits: []
cites: []
related: [b-ef8543]
---

## Problem

Found in the spec loop's run 24, 2026-10-01.

`SA-0162`'s Problem item 4 said "Keep the unrun follow-ups' task ids, as
`int`s". No criterion drove it. The cell kept spec ids, and no lens or seat
raised it above a note. `SA-0151` assumed task ids. Its parent-branch review
caught the mismatch, and the fix went into `SA-0151` (#627).

## Done looks like

The spec-reviewer flags a Problem-item sentence whose shape no witness
reads. Or the contract lens checks Problem items as well as criteria.

## Record

- 2026-10-01: filed from the spec loop's run 24.
