---
id: b-792ab2
title: ADR 7's stack batch is decided and unbuilt, so the spec loop still runs each spec by hand
status: open
tier: 1
filed: 2026-09-23
closed:
specs: [SA-0142, SA-0143, SA-0144, SA-0145, SA-0146, SA-0147, SA-0148, SA-0149, SA-0150, SA-0151, SA-0152, SA-0153, SA-0154, SA-0155, SA-0156, SA-0157, SA-0159, SA-0160, SA-0161, SA-0162, SA-0164, SA-0165, SA-0167, SA-0168, SA-0169, SA-0170, SA-0173, SA-0174, SA-0175, SA-0176]
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
- 2026-09-23: `SA-0153` runs the Spec and Standards lenses over a stack,
  top down within a reserve held from the batch budget. It records each
  lens of each layer as reviewed, error or not reached, in an `end_reviews`
  table the fold rebuilds.
- 2026-09-23: `SA-0154` adds the join lens and a critic cell seeded at a
  layer's head. It wires the end review into `saffron batch --stack`, with
  a reserve of a quarter of `--budget`. Its `StackReview` hands `SA-0147`
  the join's review and each layer's.
- 2026-09-23: `SA-0147` qualifies the end review's findings in host code.
  It anchors each over its own layer's commit. It runs any probe in a
  Gate-only cell on that layer's tree, and groups the qualified ones by
  layer and file. Each outcome is a `qualification` fact.
- 2026-09-23: step 5 is `SA-0148`. A rate limit in a stack batch waits for
  the reset time or `--until`, then runs the same spec on the same
  predecessor. A reset time more than six hours on counts as unreadable.
- 2026-09-23: step 6 splits in two. `SA-0149` reads a spec review's
  findings block and routes each spec in `run_stack_batch` through an
  injected review, one at a time before its own cell. `SA-0155` runs the
  review session in a critic cell, records it as facts and passes it from
  `saffron batch --stack`.
- 2026-09-23: step 6's session and facts split in two. `SA-0155` mints
  each reviewed spec's task before its review. It records the review as an
  attempt and a `spec_review` fact, and ends a withheld spec's task
  `SPEC_WITHHELD`. `SA-0156` builds the review session, the mint, and the
  cell on the minted task. The chain runs `SA-0149`, `SA-0155`, `SA-0156`,
  `SA-0150`.
- 2026-09-23: `SA-0147` needs `SA-0138`'s kill rule, the operator's
  decision. `SA-0133` and `SA-0138` merge before the stack chain runs, so
  the previous queue lands first.
- 2026-09-23: `SA-0154` came to about 2500 changed tokens against the
  `feature` ceiling of 3000, so its command-line wiring splits out.
  `SA-0154` keeps the join lens, the critic cell and `run_end_review`.
  `SA-0157` wires them into `saffron batch --stack`, with a reserve of a
  quarter of `--budget` printed in the plan header.
- 2026-09-23: `SA-0147` came to about 2450 changed tokens with the
  baseline names it needs, so they split out as `SA-0159`. `SA-0159` keeps
  each run-level baseline result's `collected` in a `baseline_collected`
  table. `SA-0147` depends on it and on `SA-0138`. The chain runs
  `SA-0154`, `SA-0157`, `SA-0159`, `SA-0147`, `SA-0148`.
- 2026-09-23: `SA-0156` builds the spec review session in a critic cell at
  the predecessor's head, with `spec-reviewer.md` read at the pinned base.
  It builds the mint `saffron batch --stack` passes, and runs each cell on
  the task its review is recorded on, minted or resumed.
- 2026-09-25: build steps 6 to 9 are written, and `SA-0150` split into
  eleven specs past the size margin. The chain runs `SA-0155`, `SA-0168`,
  `SA-0169`, `SA-0156`, `SA-0150`, `SA-0160`, `SA-0164`, `SA-0161`,
  `SA-0173`, `SA-0165`, `SA-0162`, `SA-0151`, `SA-0174`, `SA-0167`,
  `SA-0170`, `SA-0152`.
- 2026-09-25: operator decisions. A stack batch mints a fresh task for
  each spec every night (`SA-0155`, `SA-0168`). The spec review and writer
  hold `Bash` in their critic cell, run as an unprivileged account whose
  cell alone gets `CAP_SETUID` and `CAP_SETGID` (`SA-0169`). Prompt paths
  are declared in `policy.yaml` (`SA-0156`, `SA-0160`).
- 2026-09-25: ADR 7's revision reverses the prompt-path decision. Core owns
  the spec review and spec writer prompts in `saffron/agents/prompts/`
  (`SA-0175`, `SA-0160`), and no policy key names them. `SA-0175` joins the
  chain between `SA-0169` and `SA-0156`.
- 2026-09-25: `SA-0160` came to about 2900 changed tokens with its re-ask
  and its cost rule. So core's writer prompt and its fill split out as
  `SA-0176`. `SA-0176` depends on `SA-0150`, and
  `SA-0160` on `SA-0176`.
