---
id: b-1fc93b
title: "`saffron package` on a task reviewed before `SA-0299` renders an unanchored survivor as a Disagreement that REBUT never answered"
status: open
tier: 3
filed: 2026-10-23
specs: []
prs: [928]
commits: []
cites: [§5.5, §5.7]
related: [b-e40d09, b-bff156]
---

## Problem

Found by the in-cell contract lens on `SA-0299` and confirmed by both seats
on #928, in the spec loop's run 46.

`ready_task` in `saffron/task.py` rebuilds a resumed task's outcome as
`READY_FOR_REVIEW` from its stored `findings.json`. After `SA-0299`,
`anchored_blockers` also matches a claim starting `HOST_FILED`. Older
`findings.json` files carry that marker. So re-packaging such a task renders
its survivor as a numbered Disagreement with no rebuttal. `task.py` was
forbidden to `SA-0299`, and no task is known to wait in that state.

## Done looks like

`ready_task` re-derives the review state from the stored findings, or the
pull request body skips a host-filed survivor that no REBUT answered.

## Record

- 2026-10-23: filed from the spec loop's run 46.
