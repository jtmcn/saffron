---
id: b-00f151
title: "`saffron draft` takes no decisions, parent or pre-flight, so the spec chain still runs by hand"
status: open
tier: 3
filed: 2026-11-09
specs: []
prs: []
commits: []
cites: [§3.4]
related: [b-98a3be, b-ff3141]
---

## Problem

`saffron draft` runs a writer, up to two reviews and one revision. Its route
is fixed: `spec_review_route` revises, escalates or runs from each finding's
severity and tag. That is the deterministic stop rule the spec chain wants.
No chain record after 2026-10-07 uses it, and the delegate still drives each
agent by hand.

The command takes one item file and nothing else. The hand chain depends on
four inputs that `draft` has no place for.

- The operator's `decisions:`, which settle a design arm before the writer
  reads. Every item of the 2026-11-07 chain needed one.
- A base and parent. A child spec needs its parent's branch and prototype diff.
- The pre-flight. `driver.py check`, `cite` and `enumerators` run between the
  draft and the first review.
- The protected hand edits that land between the prototype and the review.

Its revision prompt also names a file that is not there (b-ff3141).

## Done looks like

1. `saffron draft` takes decisions and a parent spec, and hands both to the
   writer session.
2. The pre-flight runs between the draft and the first review, and a blocker
   there routes the draft as a review blocker would.
3. A chain record states the wall time of one item run through `draft`
   against the hand chain.

## Record

- 2026-11-09: filed from the spec chain speed review, after reading
  `saffron/draft.py`, `spec_review_route` and the chain records from
  2026-10-07 to 2026-11-07.
