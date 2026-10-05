---
id: b-86fa07
title: 'The `prose` gate reports every hit in the repo, so one result carries some 12,400 failures the baseline cancels'
status: open
tier: 3
filed: 2026-10-04
specs: []
prs: []
commits: []
cites: [§5.4]
related: [170]
---

## Problem

`.saffron/gates/prose.py` emits one failure per hit in every file in scope. The
ratchet happens in core, where `subtract_baseline` cancels each hit the base
already had. So a typical result lists some 12,400 failures and a handful are
new.

Measured 2026-10-04 over a copy of the ledger: `prose` wrote 2,948,560 of the
2,949,389 stored failure rows. Across every gate, 1,820,645 attempt failures at
head left 668 new (`docs/evidence/2026-10-04-fold-rebuild-time-at-223.md`).

The record no longer pays for this. Item 170's design keeps new failures only in
a gate-result fact. The ledger, each attempt's memory and the subtraction itself
still do.

## Done looks like

Either the gate reports only what the ratchet counts against its base, or this
item records why the full list is the right shape. The first moves a baseline
into a repo gate. Ask first whether §2.1's boundary allows that.

## Record

**Filed 2026-10-04 by hand**, while settling how a gate-result fact holds
failures for item 170.
