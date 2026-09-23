---
id: b-032c3e
title: A lens that errors halts the task at REVIEWING, which the reconciler reads as in flight, so a deliberate halt is re-queued as a crash
status: open
tier: 3
filed: 2026-09-22
specs: []
prs: []
commits: []
cites: [§4.2.1, §5.5]
related: [120]
---

## Problem

Found reviewing ADR 4, 2026-09-22.

A lens that errors stops the task at `REVIEWING` on purpose, so an unrun lens
never reads as a clean review (`saffron/phases/review.py`). `REVIEWING` is in
`reconcile.IN_FLIGHT_STATES`, and §4.2.1's scan stamps an in-flight task
`ORPHANED` before re-queueing it. The next queue then treats the halt as a
crash and hands the task back out.

Item 120 records the same defect for `REBUTTING`. Nothing records it for
`REVIEWING`.

## Done looks like

A task halted at `REVIEWING` by a lens error is told apart from one whose
process died, and a witness covers the scan's choice.

## Record

- 2026-09-22: filed from ADR 4's review. ADR 4's principle 55 records it.
