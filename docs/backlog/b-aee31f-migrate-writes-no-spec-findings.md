---
id: b-aee31f
title: "`migrate` writes no `spec_findings`, so a ledger migrated after SA-0226 loses each spec review's findings"
status: superseded
tier: 2
filed: 2026-10-08
closed: 2026-11-07
specs: [SA-0226]
prs: [745]
commits: ["1634a961"]
cites: [§3.4]
related: [b-d28fd8]
superseded_by: b-d28fd8
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
- 2026-11-07: superseded in grooming by b-d28fd8, filed a day earlier in
  1634a961 for the same gap. Its exit says more: each fact lands after its
  round's `spec_review` fact, and each value keeps its type. Its record also
  carries the later cutover evidence. `migrate` still writes no
  `spec_finding` fact (`saffron/record/migrate.py` names none).
