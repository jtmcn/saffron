---
id: b-466005
title: The glossary has no entry for a stack batch or its order, and SA-0142 uses both
status: open
tier: 2
by_hand: true
filed: 2026-09-23
specs: [SA-0142, SA-0143, SA-0144, SA-0145, SA-0146, SA-0153]
prs: []
commits: []
cites: [§4.2, §4.2.1]
related: [b-792ab2, 65, 72]
---

## Problem

Found 2026-09-23, writing `SA-0142`.

ADR 7 decides a stack batch. It runs the queued specs into one pull request
stack, in an order it fixes once at batch start. `SA-0142` adds that order
to `build_queue` as `stack=True`. A spec whose `depends_on` entry is
neither in the order nor on the default branch is refused.

`CONTEXT.md` has no entry for a stack batch or for its order. ADR 7's
Consequences name "predecessor" and "stack batch" among the terms it adds.
The next build spec uses "predecessor" for the task below in the stack.
`CONTEXT.md` is generated from `ontology/factory.ttl`, and both are
forbidden to the cell, so neither can add the entries.

## Done looks like

Six entries in `ontology/factory.ttl`, rendered into `CONTEXT.md` by
`uv run python -m ontology.render`.

- **Stack batch**: a batch run with `--stack`. It fixes its order once, and
  cuts each task from the head of the task below it.
- **Stack order**: that order. Each spec comes after every `depends_on`
  entry that is not on the default branch. Ties go to priority, then id.
- **Predecessor**: the last task below a task in the stack order to reach
  `READY_FOR_REVIEW`. **Parent** keeps its one referent, `depends_on[0]`.
- **Layer**: a task in a stack batch that reached `READY_FOR_REVIEW`. The
  next task is cut from its head. A task that misses adds no layer.
- **End review**: the one read of a stack batch's stack once its last
  queued task settles. End-review lenses read each layer, and the join
  lens reads the joins between layers.
- **End-review lens**: the Spec or the Standards session that reads one
  layer in the end review. Neither is one of ADR 4's declared lenses.

The **Refusal** entry names the stack order's refusal. This lands after
`SA-0142` merges.

## Record

- 2026-09-23: filed with `SA-0142`.
- 2026-09-23: `SA-0143` uses "predecessor" and "stack batch" in its
  claims. It names the pair it hands `run_task` a `Handoff`, a code name
  with no glossary entry. `SA-0144` adds the `--stack` flag.
- 2026-09-23: `SA-0145` names each layer's row in a `stack_layers` table.
  "Layer" joins the entries above.
- 2026-09-23: `SA-0146` builds the Spec and Standards end-review lenses.
  "End review" and "end-review lens" join the entries above.
- 2026-09-23: `SA-0153` holds a reserve for the end review and records a
  lens not reached. "End-review reserve" and a lens's end-review status
  join the entries above.
