---
id: b-1adb50
title: Sentences in DESIGN.md and CLAUDE.md go false once a stack batch lands, and no cell may edit either
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
- `CLAUDE.md` says `--until` ends a night at the deadline plus at most one
  task. A stack batch's end review runs after an `UNTIL` stop, paid from its
  reserve (`SA-0153`, the operator's decision of 2026-09-23). §4.2.1's
  wording of the bound needs the same change, and so does `README.md`'s
  at lines 123-124.
- §3.3's terminal list and §4.2.1's done list lack `SPEC_WITHHELD`, which
  `ccfa1553` added to the ontology for `SA-0155`. §3.3's `GATE_ERROR` line
  does not say that an errored spec review in a stack batch ends there.

## Done looks like

Once `SA-0149` and `SA-0152` merge, §4.2.1 names the errored spec review
among the aborts, and §6 names the stack view's source. Once `SA-0154`
wires the end review, `CLAUDE.md` and §4.2.1 say a stack night ends at the
deadline plus one task plus its end review. Each cites ADR 7.

## Record

- 2026-09-23: filed from the spec reviews of `SA-0149` and `SA-0152`.
