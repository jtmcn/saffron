---
id: b-d28fd8
title: A migration drops every spec finding row, so the record loses which round raised what
status: open
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: []
related: [b-98a3be]
---

## Problem

SA-0226 adds a `spec_findings` table and a `spec_finding` fact. SA-0224's
`migrate` writes six key-filed tables into the record, and `spec_findings` is
not one of them. Nothing constructs a record-backed `Ledger` yet, so a
migration is the only path from `ledger.db` into `refs/saffron/*`.

Every row written after SA-0226 merges is lost at the cutover. Nothing refuses
the loss or reports it. SA-0224's completeness claim stays true, because it
names the six tables it covers.

## Done looks like

1. `migrate` writes each `spec_findings` row as a `spec_finding` fact, after its
   round's `spec_review` fact.
2. A migrated ledger folds back to the same `spec_findings` rows, with each
   value's type kept.
3. This lands before any cutover to a record-backed ledger.

## Record

- 2026-10-07: filed from the first spec review of SA-0226.
