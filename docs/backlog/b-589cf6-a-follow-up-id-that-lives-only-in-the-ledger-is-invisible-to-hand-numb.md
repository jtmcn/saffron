---
id: b-589cf6
title: A follow-up id that lives only in the ledger is invisible to hand numbering
status: open
tier: 3
filed: 2026-09-25
closed:
specs: []
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
