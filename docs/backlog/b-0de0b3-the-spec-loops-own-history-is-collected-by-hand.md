---
id: b-0de0b3
title: The spec loop's own history is collected by hand, so its report cannot be generated
status: open
tier: 2
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: []
related: [b-a4df62]
---

## Problem

Decided by the operator in the spec loop's run 11, 2026-09-20. Every loop ends
with an HTML report of each task and of the loop as a whole. Saffron is to
collect that data itself, in core, and not the delegate by hand.

An audit at `4e0d5f2d` found the per-task half already automatic. The ledger's
`tasks`, `attempts`, `gate_results`, `failures` and `findings` tables hold it.
Each task's batch directory holds `events.jsonl`, the plan, the patch, the notes,
the probes and the rebuttal.

The loop-level half is captured nowhere.

- `.saffron-loop/order.json` holds current state, and `snapshot --force`
  rewrites it. Holds, drops and edits are overwritten.
- Spec review rounds, the review seats' findings, the operator's decisions and
  the loop's timeline exist only in the delegate's notes.

Three vocabulary facts bound the design. `CONTEXT.md` has no term for the spec
loop, and "batch" is the wrong word for it (`CONTEXT.md:132` reads "One night's
execution"). In core these would be facts in the record and never events, since
`events.py` owns that word. The record is keyed per task, and a loop spans tasks.

## Done looks like

Loop-level facts land in core as record facts under a key for the loop. The
loop's report renders from them and from the per-task data. A `DESIGN.md`
subsection and an ontology term come before any spec.

## Record

- 2026-09-21: filed from the spec loop's run 11, on the operator's decision.
