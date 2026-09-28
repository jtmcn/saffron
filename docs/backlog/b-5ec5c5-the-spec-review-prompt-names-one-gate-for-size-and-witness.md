---
id: b-5ec5c5
title: The spec review prompt names one gate for size and witness, the wording #563 fixed in the writer prompt
status: open
tier: 3
filed: 2026-09-28
closed:
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, by #563's Standards seat
(`SA-0176`).

`saffron/agents/prompts/spec-review.md:35-37` asks "Does the gate that checks
size and witness block here". It came from `SA-0175`. `CONTEXT.md` names two
gates the risk tier moves, `size` and `witness`. The same lines then say "one of
the paths named below". Three lists follow, so a protected path reads as one
that raises the tier.

#563 fixed the same wording in `spec-writer.md:27-29` (at `89a244a6`). The seat
also said the review prompt omits `risk: elevated`. That part is false: line 36
names it. `spec-review.md` was forbidden to `SA-0176`.

## Done looks like

`spec-review.md` names both gates, and names the risk tier list as the one that
raises the tier. It matches `spec-writer.md`'s wording.

## Record

- 2026-09-28: filed from the spec loop's run 20.
