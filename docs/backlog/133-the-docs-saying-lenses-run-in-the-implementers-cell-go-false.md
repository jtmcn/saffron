---
id: 133
title: Three live surfaces say the lenses still run in the implementer's cell, and go false as SA-0087 merges
status: done
closed: 2026-09-29
tier: 3
filed: 2026-09-15
by_hand: true
specs: [SA-0087, SA-0088, SA-0089]
prs: [274]
commits: [8c6f7357]
cites: [§5.5]
related: [118]
---

## Problem

**Tier 3.** Found reviewing `SA-0087` (PR #274).

Three sentences describe the pre-`SA-0087` world as current:

- `DESIGN.md` §5.5 — *"Until they land, the lenses still run in the implementer's
  cell and read its gate results"*
- `CONTEXT.md` §5's **Critic cell** entry, the same claim
- `DESIGN.md` §5.5's closing sentence

Each is scoped to all of `SA-0087`, `SA-0088` and `SA-0089`, so none is wholly
false when the first merges — which is why no single spec's `scope` gate catches
it, and why all three files are `forbidden` in every one of those specs. The
result is that the sentences go from true, to half-true, to false across three
merges with nothing tracking the transition.

This is the same shape as the earlier pass that found every live surface citing
the backlog by a path about to disappear: a claim that is accurate when written
and decays on a schedule nobody owns.

## Done looks like

the three sentences rewritten once the last of `SA-0087`–`SA-0089` merges, in a
doc pull request that names which spec made each one false.

## Record

- 2026-09-29: closed on a check. `8c6f7357` rewrote all three sentences when `SA-0088` to `SA-0092` retired, and this record stayed open.
