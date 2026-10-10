---
id: b-9b94c9
title: "Five glossary entries describe only the stack batch or the old comparison, though run 32 widened each"
status: open
tier: 3
by_hand: true
filed: 2026-10-09
specs: []
prs: [781, 782, 787]
commits: []
cites: []
related: [b-466005, b-98a3be]
---

## Problem

Found by the Standards seats of #781, #782 and #787 in the spec loop's run 32.
Each sentence sits in `CONTEXT.md`, which every spec of that run forbade.

- **Review round** says a round "happens outside any task, so it is never an
  attempt" (`CONTEXT.md:844-850`). `saffron draft` now charges each review as
  a `SPEC_REVIEW` attempt inside a task, and `DESIGN.md` §3.4 calls them
  review rounds.
- **Mint**, **Escalation** and **`SPEC_WITHHELD`** name only a stack batch.
  `draft_spec` mints through its caller, escalates and withholds outside one.
- **Suite comparison** lists three outcomes (`CONTEXT.md:379-383`). After
  `SA-0240` a comparison also carries the advisory gates' new failures beside
  them, and `SuiteComparison`'s docstring says so.

## Done looks like

Each entry names what a draft does, or what an advisory new failure is, in
the operator's words. `uv run python -m ontology.render` leaves the tree
unchanged afterwards.

## Record

- 2026-10-09: filed from the spec loop's run 32.
