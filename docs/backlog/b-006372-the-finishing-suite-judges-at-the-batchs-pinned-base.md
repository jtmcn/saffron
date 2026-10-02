---
id: b-006372
title: 'The finishing suite judges the finish at the batch''s pinned base, while PACKAGE judges each layer at the live default branch'
status: open
tier: 3
filed: 2026-10-02
specs: [SA-0167]
prs: [638]
commits: []
cites: [§5.7]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 25, 2026-10-02.

`SA-0167`'s `_finish_verify` exports `.saffron/` from the pinned mirror at
the batch's pinned `base_sha` (`saffron/cli.py:692`). PACKAGE re-fetches the
live default branch for each layer. A policy or gate change during the night
reaches the layers and not the finish. The spec mandated the pinned base, and
the contract lens and the Spec seat each raised it as a concern.

## Done looks like

A design decision on which base judges the finish, recorded in ADR 7's
record or the stack batch design, and the code following it.

## Record

- 2026-10-02: filed from the spec loop's run 25.
