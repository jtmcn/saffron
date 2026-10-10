---
id: b-a33889
title: "A `CellRuntimeError` from a stack batch's mint or revision still marks the layer missed"
status: open
tier: 2
filed: 2026-10-09
specs: []
prs: [783]
commits: []
cites: [§4.4]
related: [b-60a399]
---

## Problem

Found by #783's seats in the spec loop's run 32.

`SA-0234` made a `CellRuntimeError` from `review` or `runner` offer the spec
again. A raise from `mint` or from a revision stays a miss in the order's
pass, whatever its type (`saffron/batch.py:535-542`). The spec put both out of
scope. A revision runs in a cell, so the same seed failure that b-60a399
measured refuses every descendant there.

## Done looks like

A `CellRuntimeError` from a revision offers the spec again, as one from
`review` does. A test raises it from the revision seat and reads the
descendant back as a candidate.

## Record

- 2026-10-09: filed from the spec loop's run 32.
