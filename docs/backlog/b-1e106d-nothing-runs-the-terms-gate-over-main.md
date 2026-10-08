---
id: b-1e106d
title: "Nothing runs the `terms` gate over main, so main went red and only a cell's baseline line said so"
status: open
tier: 2
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-86fa07]
---

## Problem

Measured in the spec loop's run 30. The first cell's baseline line read
`terms=fail` on `main`. The hit was the `Spec` docstring at
`saffron/intake.py:158`, a line from 2026-08-19. The gate began reading
docstrings with `9ef9e7b2`, and from then on `main` failed `terms`.

`make check` passed on `main` the whole time. Its prek hook reads only the
staged index, so a gate rule that widens never runs over the files it now
reaches. Baseline subtraction then spared every cell, and hid any new hit in
that file from each of them. #720 fixed the line by hand.

## Done looks like

A change to the `prose` or `terms` rules runs the gate over the whole tree, and
fails where `main` would go red. Or `make check` runs both gates over the tree.

## Record

- 2026-10-07: filed from the spec loop's run 30. #720 reworded the docstring.
