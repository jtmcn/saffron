---
id: b-e4ab6f
title: The code and its tests call the subnet pool a bare pool, which CONTEXT.md keeps for a batch's concurrency pool
status: open
tier: 3
filed: 2026-10-13
specs: [SA-0271]
prs: [868]
commits: []
cites: [§5.1]
related: [b-1c4a14]
---

## Problem

Found by the Standards seat on #868 in the spec loop's run 37.

`CONTEXT.md` names the subnet pool and puts a bare "pool" on its _Avoid_
line. `SA-0271`'s own criteria said "from the pool", and its diff wrote the
word in two source comments and many test docstrings. Review fixed the two in
`saffron/` and kept the tests. The key is `SUBNETS["pool"]`, so the word
returns wherever the code is read aloud. The `terms` gate matches phrases, and
"pool" alone is also right for a batch, so no entry in its `AVOIDED` map can
decide it.

## Done looks like

The key is renamed so the code says "subnet pool", or `CONTEXT.md` settles
the two senses another way. The tests' docstrings follow.

## Record

- 2026-10-13: filed from the spec loop's run 37.
