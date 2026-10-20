---
id: b-589cf6
title: A follow-up id that lives only in the ledger is invisible to hand numbering
status: open
tier: 3
filed: 2026-09-25
closed:
specs: [SA-0300]
prs: []
commits: []
cites: [§4.2]
related: [b-792ab2]
---

## Problem

`SA-0161` gives a follow-up the next free id across both spec
directories and the ledger. A follow-up that ran and missed, or that gate 0
refused, is never committed (`SA-0151`). Its id then lives only in the
ledger. A hand-written spec takes the highest file id plus one
(`docs/agents/issue-tracker.md:10-11`), so it can reuse that id and share
its task rows.

## Done looks like

Hand numbering reads the ledger too, or an uncommitted follow-up's id is recorded where the convention looks.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
- 2026-10-20: batch 39 in the spec loop's run 45 took `SA-0297` for a refused follow-up. Its text is only in the ledger, so the next hand-numbered spec starts at `SA-0298`.
