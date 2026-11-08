---
id: b-86d716
title: cell-watch reads any new task directory as a hand-over, so an end review or a refused spec wakes the delegate falsely
status: open
tier: 3
filed: 2026-11-08
specs: []
prs: []
commits: []
cites: []
related: [b-2d2014, b-036cc5]
---

## Problem

Found in the spec loop's run 55.

`.claude/skills/cell-watch/hooks/register.tsx:101-103` reads a newer spec's
log as proof the last task packaged. Finish 72's end review wrote a
directory per layer. That gave three false "has packaged" wake-ups in a
row. A spec refused or orphaned before its cell does the same.

## Done looks like

The hand-over milestone reads a fact the batch writes, such as the
previous task's `PACKAGE` line or its terminal event, never a directory's
birth. A test feeds an end review's directories and asserts no hand-over.

## Record

- 2026-11-08: filed from the spec loop's run 55.
