---
id: b-cc8099
title: "`_stack_finish`'s narrow commit `except` has no witness, so widening it to `Exception` passes"
status: open
tier: 3
filed: 2026-10-03
specs: [SA-0151, SA-0170]
prs: [647]
commits: []
cites: [§4.3]
related: [b-792ab2]
---

## Problem

Found by #647's Spec seat in the spec loop's run 26.

`cli._stack_finish` catches only `GitError` and `ValueError` from
`finish.commit_finish`. Its docstring says any other raise reaches `main`,
which exits 2. That is `SA-0151`'s claim. The seat widened the `except` to
`Exception`, and all four `_stack_finish` tests still passed. A wider catch
would turn an infrastructure failure into a quiet night.

## Done looks like

A test drives a raise other than `GitError` or `ValueError` from the
commit and asserts it reaches `main` with exit 2.

## Record

- 2026-10-03: filed from the spec loop's run 26.
