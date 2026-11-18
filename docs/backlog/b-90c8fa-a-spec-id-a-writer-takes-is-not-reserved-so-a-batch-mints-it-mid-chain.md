---
id: b-90c8fa
title: A spec id a writer takes is not reserved, so a batch's follow-up can mint the same id mid-chain
status: open
tier: 2
filed: 2026-11-17
closed:
specs: []
prs: []
commits: []
cites: [§3.4]
related: [b-589cf6]
---

## Problem

Found in the spec loop's run 78. The `b-cafacd` writer took `SA-0412`
from `saffron next-id`. Batch 95's finish then minted a follow-up as
`SA-0412`. The writer moved to `SA-0413`, and the finish minted a second
follow-up there before the spec was committed. The spec landed as
`SA-0414` (#1253).

`next-id` reads the spec files and the home ledger (`SA-0300`). A spec a
writer is still drafting sits in neither, so nothing holds its id.

## Done looks like

`next-id` can reserve an id for a draft, and a follow-up mint skips a
reserved id. A test mints a follow-up while a reservation is held, and the
follow-up takes the next id.

## Record

- 2026-11-17: filed from the spec loop's run 78.
