---
id: b-7338e7
title: "Two repo rows that share one mirror with different origins prune each other's fetched refs in `saffron migrate`"
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: []
related: [170]
---

## Problem

Reasoned from the code, not measured, in the spec loop's run 30.
`migrate_and_push` fetches every repo row's origin into that row's mirror
with `--prune` before it writes. Two rows on one mirror with different
origins each fetch into the same `refs/saffron/*`. The second fetch prunes
the task refs the first origin supplied, so the first repo's migration starts
from an empty record.

`SA-0224`'s fourth witness builds two rows on one mirror only to make a fetch
fail. The live ledger has one repo row, so no run has met this.

## Done looks like

A test drives two rows on one mirror with two origins and shows each repo's
tasks reach its own origin. Or `migrate` refuses two rows sharing a mirror.

## Record

- 2026-10-07: filed from the spec loop's run 30 (#735).
