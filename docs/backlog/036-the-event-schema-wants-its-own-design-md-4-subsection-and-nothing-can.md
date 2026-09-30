---
id: 36
title: The event schema wants its own `DESIGN.md` §4 subsection, and nothing can write one
status: done
closed: 2026-09-29
tier: 2
by_hand: true
specs: [SA-0040]
prs: []
commits: []
cites: [§4, §4.7]
related: []
---

## Problem

`saffron/events.py` fixes the kinds, the `kind` discriminator and the
timestamp representation, and `DESIGN.md` carries no event schema at all.
`DESIGN.md` is `protected`, so no cell can add one.

The count is now **ten**: `Ceilings` was added by hand with `saffron/task.py`,
so a §4.x written against "nine" would be stale before it landed. Stated as a
count that moves, rather than a number to correct again.

## Done looks like

a new §4.x naming the kinds, the wire discriminator and
`events.jsonl`'s one-file-per-task, no-rotation ceiling — by hand, after
`SA-0040`, when the shape has stopped moving.

## Record

- 2026-09-29: §4.7 landed by hand. It names the `Event` union as the list of kinds,
  the `kind` discriminator, the epoch-seconds `timestamp` and the one-file,
  no-rotation ceiling. It states no count, so a new kind leaves it true.
