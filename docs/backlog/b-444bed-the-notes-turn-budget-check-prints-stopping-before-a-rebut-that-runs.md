---
id: b-444bed
title: The notes turn's budget check prints a stop before a REBUT that then runs past the budget
status: open
tier: 3
filed: 2026-10-05
specs: [SA-0203]
prs: [676]
commits: []
cites: [§4.3, §5.5]
related: [b-4c5dc7]
---

## Problem

Found reviewing #676, in the spec loop's run 28.

`SA-0203` lets REBUT run past the budget on its own cap. The notes turn
still asks `_over_budget()` first (`saffron/cell/session.py:2641`). That call
emits a `Budget` event, and the log prints `budget: $X of $Y, stopping`
(`saffron/events.py:808`). REBUT then
runs. One log reads stop, then run.

`SA-0203` saw this and read the budget directly at REBUT for that reason
(`saffron/cell/session.py:3001`). It left the notes turn's call as it was.

## Done looks like

A log past the budget prints no stopping line before a REBUT that runs. A
test drives a task past the budget with a blocker and reads the emitted
events in order.

## Record

- 2026-10-05: filed from the spec loop's run 28.
