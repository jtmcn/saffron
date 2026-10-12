---
id: b-d7959f
title: "`CONTEXT.md`'s Mint entry says a spec is offered again after a wait, and two re-offers happen at once"
status: open
tier: 3
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-032c61]
---

## Problem

Found by the Standards seat on #829 (`SA-0261`), in the spec loop's run 35.

The Mint entry is at `CONTEXT.md:187`. It reads "A spec offered again after
a wait keeps the task it was minted." A `PROVIDER_UNREACHABLE` re-offer happens at once,
with no wait (`saffron/batch.py:331`). `SA-0261` added a `PREFLIGHT_FAILED`
re-offer that does the same. Each keeps its minted task.

## Done looks like

The entry says "offered again" with no wait, and still names the task the
spec keeps.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#829).
