---
id: b-1f1188
title: A spec revision can make a sibling spec's claim false with no check
status: partial
tier: 3
filed: 2026-09-29
specs: [SA-0167, SA-0177]
prs: []
commits: []
cites: []
related: [170]
---

## Problem

Found in the spec loop's run 22, 2026-09-29.

`SA-0177`'s revision made the finishing layer a record fact. `SA-0167`'s
out-of-scope bullet still said the row was the ledger's alone. The delegate
caught it by reading. No check compares one queued spec's claims with a
sibling's revision.

## Done looks like

A check runs over the queued specs that name a changed spec. It reports each
for a reread.

## Record

- 2026-09-29: filed from the spec loop's run 22.
- 2026-10-02: `SA-0177` and `SA-0167` retired as #636 and #638. No check yet compares a sibling spec's claims after a revision. Run 25's three revisions were checked by hand in parent-branch reviews.
