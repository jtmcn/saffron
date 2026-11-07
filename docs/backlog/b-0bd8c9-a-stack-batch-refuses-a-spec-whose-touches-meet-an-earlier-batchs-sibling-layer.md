---
id: b-0bd8c9
title: A stack batch refuses a spec whose touches meet an earlier batch's open layer that is not its ancestor
status: superseded
tier: 2
filed: 2026-10-29
closed: 2026-11-07
specs: []
prs: []
commits: ["c5e5deab"]
cites: [§4.2]
related: [b-e0e1cf, b-910cef]
superseded_by: b-910cef
---

## Problem

Found in the spec loop's run 50.

`SA-0327` declares `depends_on: [SA-0325]` and touches `saffron/cli.py`.
`SA-0326` declares no parent and changed `saffron/cli.py` in #990. In batch
60 they shared one order, so the overlap rule did not apply. Batch 60 then
refused `SA-0327` for stale citations. Once those were fixed, a new
`--stack` batch refused it for overlapping #990. The exemption at
`saffron/scheduler.py:874-889` covers only a candidate's ancestors.

A stack batch already cuts each layer from the one below. #990 was the top
layer, so a cell for `SA-0327` cut there starts from a tree that holds
#990's change. The operator chose to merge the stack first and run
`SA-0327` from `main`.

## Done looks like

A stack batch that cuts a candidate from the top of an earlier batch's open
layers exempts every layer below that top. Or the refusal names the merge
as the way out.

## Record

- 2026-10-29: filed from the spec loop's run 50.
- 2026-11-07: closed in grooming as superseded by b-910cef, filed in c5e5deab from run 32. Both name one root cause. `open_pr_refusal` exempts only a candidate's `depends_on` ancestors, never the open stack's recorded chain below the layer a cell is cut from. b-910cef asks for the chain to be read and names a test. This item's run 50 case is a second sighting of it. The exemption still reads `depends_on` alone (`_ancestor_branches`, `saffron/scheduler.py`).
