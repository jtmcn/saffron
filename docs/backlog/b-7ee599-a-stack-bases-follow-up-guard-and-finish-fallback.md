---
id: b-7ee599
title: "A stack batch's `not is_follow_up` guard has no witness, and a finish with no stack-base row expects the default branch"
status: open
tier: 2
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-e0e1cf]
---

## Problem

Found by the Spec seat on #844 (`SA-0265`), in the spec loop's run 35.

`saffron/batch.py:545` asks whether the stack base is alive only for a
spec that is not a follow-up. Dropping `not is_follow_up` survives the
whole default suite. A follow-up on a gone stack base would then reach the
runner's fetch and raise `ParentGone`, an abort, instead of a refusal.

`saffron/finish.py:403` reads the stack base's task row. When the row is
missing, it expects the default branch instead of escalating.

## Done looks like

- A test drives a follow-up on a gone stack base and asserts the outcome
  the operator chooses.
- A finish whose stack-base row is missing escalates and names the row.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#844).
