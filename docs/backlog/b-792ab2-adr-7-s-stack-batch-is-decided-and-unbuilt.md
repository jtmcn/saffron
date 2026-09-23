---
id: b-792ab2
title: ADR 7's stack batch is decided and unbuilt, so the spec loop still runs each spec by hand
status: open
tier: 1
filed: 2026-09-23
closed:
specs: []
prs: []
commits: []
cites: [§1.4, §4.2, §4.2.1, §4.4, §5.5, §6]
related: [40, 59, 97, 170, b-e1afbb]
---

## Problem

ADR 7 decides a stack batch. It runs the spec DAG into one pull request stack,
reviews each spec before its cell, and runs one end review over the stack.
Findings the host qualifies become follow-up specs, one generation deep.

None of it is built. The spec loop skill still runs each spec as an attended
cell, and the delegate still reviews and chains the pull requests by hand. The
operator asked for a loop that needs little of either.

## Done looks like

A merged spec covers each step of the build order in
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`.

1. The handoff, and the record of the stack's layers.
2. Gate 0's open pull request check exempts the batch's own tasks.
3. The Spec and Standards end-review lenses, and the join lens.
4. Qualification of end-review findings in host code.
5. A rate limit waits in a stack batch.
6. Spec review inside the batch.
7. Spec writing, and follow-up specs.
8. The finishing layer.
9. The stack view on the queue page.

The spec loop skill then shrinks to starting a stack batch and answering its
escalations.

## Record

- 2026-09-23: filed with ADR 7 (#496). The build specs follow on the next
  layer of that stack.
