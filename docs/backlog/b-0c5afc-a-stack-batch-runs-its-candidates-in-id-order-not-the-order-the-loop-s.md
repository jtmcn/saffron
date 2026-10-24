---
id: b-0c5afc
title: A stack batch runs its candidates in id order, not the order the loop's snapshot wrote
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: []
---

## Problem

Found in the spec loop's run 47, in batch 51.

The snapshot's order was `SA-0312`, `SA-0313`, `SA-0315`, `SA-0311`, `SA-0314` and
`SA-0316`. Parents with the most descendants come first. The batch started `SA-0311`
instead, by id. So the chain's root ran second, and its children waited on it longer.

## Done looks like

A stack batch takes its candidates in the order `build_queue` returns. The loop's
snapshot and the batch agree, and a test pins one arrangement where id order differs.

## Record

- 2026-10-24: filed from the spec loop's run 47.
