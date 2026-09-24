---
id: b-1adb50
title: Two DESIGN.md sentences go false once a stack batch lands, and no cell may edit DESIGN.md
status: open
tier: 2
by_hand: true
filed: 2026-09-23
closed:
specs: []
prs: []
commits: []
cites: [§4.2.1, §6]
related: [b-792ab2, b-466005]
---

## Problem

Found 2026-09-23 in the spec reviews of `SA-0149` and `SA-0152`. Both specs
forbid `DESIGN.md`, which is protected.

- §4.2.1 enumerates what counts toward the breaker. `SA-0149` makes an
  errored spec review in a stack batch count as an abort, as `GATE_ERROR`
  does, and the list will not say so.
- §6 says the morning queue reads `queue.json`. `SA-0152`'s stack view reads
  the ledger's `stack_layers` table.

## Done looks like

Once `SA-0149` and `SA-0152` merge, §4.2.1 names the errored spec review
among the aborts, and §6 names the stack view's source. Both cite ADR 7.

## Record

- 2026-09-23: filed from the spec reviews of `SA-0149` and `SA-0152`.
