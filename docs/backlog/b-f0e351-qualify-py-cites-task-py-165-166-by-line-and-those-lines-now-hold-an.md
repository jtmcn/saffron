---
id: b-f0e351
title: "qualify.py cites task.py:165-166 by line, and those lines now hold an unrelated docstring"
status: open
tier: 3
filed: 2026-10-25
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 48, by #964's Standards seat.

`saffron/qualify.py:2` cites `saffron/task.py:165-166` as what makes the
tree it reads stacked. At `78f1453b` those lines sit inside the `Ceilings`
docstring.

## Done looks like

The comment names the function or constant it means, not a line range.

## Record

- 2026-10-25: filed from the spec loop's run 48.
