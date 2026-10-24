---
id: b-589cf6
title: A follow-up id that lives only in the ledger is invisible to hand numbering
status: done
tier: 3
filed: 2026-09-25
closed: 2026-10-23
specs: [SA-0300]
prs: [930]
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
- 2026-10-23: #930 (`SA-0300`) makes `saffron next-id` read the home ledger as well as the spec files. Batch 40's follow-ups `SA-0307` to `SA-0309` and batch 47's `SA-0310` live only in the ledger, and `next-id` skips them.
