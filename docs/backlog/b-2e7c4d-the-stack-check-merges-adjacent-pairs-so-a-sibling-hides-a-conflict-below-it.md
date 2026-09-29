---
id: b-2e7c4d
title: The stack check merges adjacent pairs, so a sibling cut from main hides a conflict below it
status: open
tier: 2
filed: 2026-09-28
closed:
specs: []
prs: []
commits: []
cites: []
related: [b-c07b92]
---

## Problem

Found in the spec loop's run 20, 2026-09-28. Ranked eighth in
`docs/evidence/2026-09-28-spec-loop-skill-feedback-run-20.md`, and filed after
the run.

`driver.py stack` runs `git merge-tree` on each adjacent pair of layers
(`.claude/skills/run-saffron-spec-loop/driver.py:641-655`, called at
`:1560-1583`). A sibling cut from `main` merges cleanly with the layer below
it, since both start from `main`. It can still conflict with the chain below
that layer.

`SA-0185` and `SA-0150` both added tests to `tests/test_task.py`. Each pair
merged cleanly off `main`, and `stack` printed "every adjacent pair merges
cleanly". The rebase onto `SA-0164` then conflicted. The bottom-up merge of
#564 conflicts the same way.

## Done looks like

`stack` merges each layer onto the result of merging every layer below it,
in order, the way the operator merges the stack. A conflict with any lower
layer names both branches. A test drives three layers where the top one
conflicts with the bottom one only.

## Record

- 2026-09-28: filed after the spec loop's run 20, at the operator's request.
