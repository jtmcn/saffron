---
id: SA-0006
title: a -diff gitattribute zeroes the size gate at the tier where it blocks
type: bug
priority: 2
depends_on:
  - SA-0005
touches:
  - saffron/gates/core/size.py
  - saffron/cell/session.py
  - tests/test_size.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
budget_usd: 8
max_attempts: 4
max_turns: 60
risk: elevated
---

## Context
`size` counts added plus removed lines out of hunk content, keyed on a file
block's first `@@`. A file git renders as `Binary files a/x and b/x differ` has
no `@@` at all.

## Problem
Such a block contributes **0**. Measured: a repo committing `*.py -diff` in
`.gitattributes` and rewriting 2000 lines of `a.py` reports **1** changed line
— the `.gitattributes` addition — and the gate passes. `SA-0005` makes `size`
blocking at `elevated`, so this is a one-line route past the gate at the only
tier where it blocks.

`integrity` already meets the same shape and answers it correctly: an
unreadable section is `error` when the file is inside `touches`, and `error` is
charged to nobody (§5.4). `size` has neither the rule nor the `touches` to
apply it to.

## Acceptance criteria
- [ ] `size_gate` takes the task's `touches` and returns `error` for a diff
      carrying an unreadable section for a file inside them
- [ ] An unreadable section for a file *outside* `touches` is not an error —
      `scope` already fails that diff, and a genuine binary asset must not make
      every task error
- [ ] `pass`/`fail` semantics are unchanged for every diff `size` can read:
      `error` is the gate saying it cannot measure, never a verdict on the task
- [ ] The `_suite` call site passes `touches`
- [ ] A test built from a real `git diff` over a repo with `*.py -diff`, not a
      hand-written fixture — the string git actually emits is the thing under
      test

## Out of scope
The `--numstat` cross-check as a second opinion on the line count. It means a
second git call in the cell for a diff the host already holds, and the rule
above closes the escape this gate can actually be gamed with.

## Notes for the agent
Read `integrity`'s unreadable-section handling before writing a second one, and
make the two agree — two rules for one shape is how they drift.

`ponytail:` comments mark deliberate simplifications and name their ceiling.
`size.py` carries one naming exactly this defect; it goes when the defect does.

Commit after each coherent step. Uncommitted work dies with the cell.
