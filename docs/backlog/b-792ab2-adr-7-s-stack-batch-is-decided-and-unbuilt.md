---
id: b-792ab2
title: ADR 7's stack batch is decided and unbuilt, so the spec loop still runs each spec by hand
status: open
tier: 1
filed: 2026-09-23
closed:
specs: [SA-0142, SA-0143, SA-0144, SA-0145, SA-0146]
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
2. Folded into step 7.
3. The Spec and Standards end-review lenses, and the join lens.
4. Qualification of end-review findings in host code.
5. A rate limit waits in a stack batch.
6. Spec review inside the batch.
7. Spec writing, and follow-up specs. Gate 0's open pull request check
   exempts the batch's own tasks when it plans them.
8. The finishing layer.
9. The stack view on the queue page.

The spec loop skill then shrinks to starting a stack batch and answering its
escalations.

## Record

- 2026-09-23: filed with ADR 7 (#496). The build specs follow on the next
  layer of that stack.
- 2026-09-23: step 1 came to about 4300 changed tokens against the
  `feature` ceiling of 3000, so it splits in three. `SA-0142` builds the
  stack order in `build_queue`. The handoff and the layers' record follow
  as two more specs.
- 2026-09-23: the rest of step 1 splits in two. `SA-0143` hands each task
  its predecessor's branch in `run_stack_batch`. `SA-0144` adds the
  `--stack` flags on `saffron batch` and `saffron queue`. `SA-0142` now
  stacks on `SA-0136`, so one chain carries all three. The layers' record
  becomes `SA-0145`, and build steps 2 to 9 take `SA-0146` to `SA-0153`.
- 2026-09-23: `SA-0145` records each layer in a `stack_layers` table,
  keyed on record keys so a fold rebuilds it. It depends on `SA-0144`.
- 2026-09-23: step 2 folds into step 7. A stack batch plans once, before
  any of its own pull requests exist, so only follow-ups meet the check.
  Steps 3 to 9 take `SA-0146` to `SA-0152`.
- 2026-09-23: step 3 came to about 5000 changed tokens against the
  `feature` ceiling of 3000, so it splits in three. `SA-0146` builds the
  Spec and Standards end-review lenses and fills their fields from the
  ledger. `SA-0153` runs them over a stack and records each layer's end
  review. `SA-0154` adds the join lens and the critic cell, and wires the
  end review into `saffron batch --stack`. Step 6's session and facts take
  `SA-0155`. The chain runs `SA-0145`, `SA-0146`, `SA-0153`, `SA-0154`,
  `SA-0147`, `SA-0148`, `SA-0149`, `SA-0155`, `SA-0150`, `SA-0151`,
  `SA-0152`.
