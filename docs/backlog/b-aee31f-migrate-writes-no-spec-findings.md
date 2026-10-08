---
id: b-aee31f
title: "`migrate` writes no `spec_findings`, so a ledger migrated after SA-0226 loses each spec review's findings"
status: open
tier: 2
filed: 2026-10-08
specs: [SA-0226]
prs: [745]
commits: []
cites: [§3.4]
related: []
---

## Problem

SA-0226 gives each spec review finding its own `spec_finding` fact and
`spec_findings` row. Its spec leaves the migration out of scope. `SA-0222` to
`SA-0224` write a stored ledger's rows into the record, and none of them reads
`spec_findings`. A ledger written after SA-0226 and then migrated drops those
rows. The spec asks the operator to file this before any cutover, and both
seats on #745 restated it.

## Done looks like

`migrate` writes each `spec_findings` row as its `spec_finding` fact, and a
migrated ledger folds back to the same rows.

## Record

- 2026-10-08: filed from the spec loop's run 31, as SA-0226's spec asks.
