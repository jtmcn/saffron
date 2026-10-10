---
id: b-b94076
title: "A closed `EXHAUSTED` draft whose head moved is reported as `head_moved` on every reconcile"
status: open
tier: 3
filed: 2026-10-10
specs: []
prs: [798]
commits: []
cites: []
related: []
---

## Problem

Found by both seats on #798 in the spec loop's run 33.

`SA-0251` made reconcile ask about non-merged `EXHAUSTED` rows
(`saffron/reconcile.py:175`). A closed draft whose head differs from the
row's head is reported in `head_moved` every scan, forever. No witness
drives the case, and the spec's out-of-scope note on repeated asks does not
name it.

## Done looks like

- A closed, non-merged `EXHAUSTED` row is reported once, or the report says
  that it repeats.
- A test runs two scans over one such row.

## Record

- 2026-10-10: filed from the spec loop's run 33.
