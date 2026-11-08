---
id: b-31e3c8
title: REBUT answers only blockers, so every in-cell concern reaches the review seats unanswered
status: open
tier: 2
filed: 2026-11-08
specs: []
prs: []
commits: []
cites: [§5.6]
related: [b-1e9a7a]
---

## Problem

Found in the spec loop's run 55.

REBUT is handed no REVIEW concern or note, and each of batch 72's three
cells had one. `SA-0340` had two conventions concerns, `SA-0350` one conventions note,
and `SA-0352` a contract and a conventions concern. Every one recurred in both
PR seats, and every one was a true one-line comment fix inside `touches`.
The delegate fixed all five by hand. One of `SA-0352`'s, an exit-code claim,
needed a second fix after the end review.

## Done looks like

REBUT's fixer turn receives each anchored concern beside the blockers. It
fixes it or argues it, and the PR body shows the answer. A test drives a
concern through REBUT and asserts its answer is recorded.

## Record

- 2026-11-08: filed from the spec loop's run 55.
