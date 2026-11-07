---
id: b-22ed54
title: "`session.py` writes the host checkpoint after a failed turn in four places"
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§5.5]
related: []
---

## Problem

Found in the spec loop's run 47, by the Standards seat on `SA-0311` (#955).

`SA-0311`'s repair turn added a fifth copy of the block that writes a host checkpoint after
a failed agent turn. Each copy floors the cost and records the error its own way.

## Done looks like

One helper writes the checkpoint after a failed turn, and every turn site calls it.

## Record

- 2026-10-24: filed from the spec loop's run 47.
- 2026-11-07: retitled in grooming. The title's five places are four, both now and at 61ef7c78.
