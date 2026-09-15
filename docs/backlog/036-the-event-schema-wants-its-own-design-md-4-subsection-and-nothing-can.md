---
id: 36
title: The event schema wants its own `DESIGN.md` §4 subsection, and nothing can write one
status: open
tier: 2
specs: [SA-0040]
prs: []
commits: []
cites: [§4]
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

Done looks like: a new §4.x naming the kinds, the wire discriminator and
`events.jsonl`'s one-file-per-task, no-rotation ceiling — by hand, after
`SA-0040`, when the shape has stopped moving.
