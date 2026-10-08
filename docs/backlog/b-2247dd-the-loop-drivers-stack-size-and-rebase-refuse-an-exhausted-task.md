---
id: b-2247dd
title: The loop driver's `stack`, `size` and `rebase` refuse an `EXHAUSTED` task with a draft pull request
status: open
tier: 2
filed: 2026-10-05
specs: [SA-0204]
prs: [678]
commits: []
cites: [§5.7]
related: [b-038aef, b-8e30bd]
---

## Problem

Found in the spec loop's run 28.

`SA-0204`'s cell ended `EXHAUSTED`, and the delegate opened #678 as a draft.
The driver treats a task as reviewable only when its state is
`READY_FOR_REVIEW` (`.claude/skills/run-saffron-spec-loop/driver.py:154`). So
`stack` left #678 out, and the delegate linked it by hand. `size` refused it,
and the delegate measured it with `size._changed_lines` directly. `rebase`
would chain the next sibling onto `SA-0203`, not `SA-0204`.

`SA-0204` now opens such a draft without the delegate. Each one will need the
same three steps by hand.

## Done looks like

An `EXHAUSTED` task with a pull request counts as a stack layer in `stack`,
`size` and `rebase`. A test drives a stack with one such layer in the middle.

## Record

- 2026-10-05: filed from the spec loop's run 28.
- 2026-10-08: recurred in the spec loop's run 31 for a `READY_FOR_REVIEW`
  task with no recorded PR (b-883f74). `size` refused SA-0226 as not
  reviewable, and the delegate measured it with `_token_counts` by hand.
