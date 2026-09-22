---
id: b-07f694
title: Whether a risk tier gates a lens has no open record, because item 6 closed without settling it
status: open
tier: 3
filed: 2026-09-22
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.5.1, §5.6]
related: [6]
---

## Problem

Found reviewing ADR 4, 2026-09-22.

§5.5.1 says whether `adequacy` is what a tier gates "is backlog item 6's
remaining half". Item 6 is `done`. §5.6 says tier-gating a lens "is still an
open question". So the question is named open in two sections, and no open
record holds it.

§5.5.1's measurement stands: 28 of this repo's 34 specs declared `elevated`
then, so gating would exclude few tasks.

## Done looks like

The question is answered in §5.5.1 or §5.6, or a record holds it open, and
§5.5.1 stops pointing at a closed item.

## Record

- 2026-09-22: filed from ADR 4's review. ADR 4's Consequences records it.
