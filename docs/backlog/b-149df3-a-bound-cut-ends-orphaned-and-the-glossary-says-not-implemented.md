---
id: b-149df3
title: A bound cut with nothing committed ends `ORPHANED` once SA-0126 lands, and the glossary and §4.5 still say otherwise
status: open
tier: 1
by_hand: true
filed: 2026-09-22
specs: [SA-0126]
prs: []
commits: []
cites: [§4.5]
related: [b-36b551]
---

## Problem

Found 2026-09-22, writing `SA-0126`.

`SA-0126` gives a wall-clock cut the salvage turn a turn-ceiling cut gets. An
implement turn that either bound cuts with nothing committed then ends
`ORPHANED`, so the next scan re-queues it. Three sentences no cell can edit
become incomplete.

- `CONTEXT.md` §6 says each `TerminalEvent` reason ends the task in
  `PLAN_REJECTED` or `NOT_IMPLEMENTED`. The two cut-off reasons now end in
  `ORPHANED`.
- `CONTEXT.md` §6 defines `ORPHANED` as a task whose cell was killed or
  crashed. A turn ceiling ends a turn without killing anything.
- `DESIGN.md` §4.5 says the supervisor stamps `ORPHANED` on kill, on crash,
  and on `--until`. It does not name a bound cut with nothing committed.

Both files are `protected`, so the cell cannot change either.

## Done looks like

The `ORPHANED` entry and the `TerminalEvent` paragraph in `CONTEXT.md` name a
turn cut by its turn ceiling or its wall clock with nothing committed.
`DESIGN.md` §4.5 names the same case beside kill, crash and `--until`. Both
land after `SA-0126` merges, not before.
