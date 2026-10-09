---
id: b-fe82d9
title: A stack finish escalated on three new failures and recorded none of them where the operator can read them
status: open
tier: 2
filed: 2026-10-08
specs: [SA-0225, SA-0228]
prs: [746, 747]
commits: []
cites: [§4.2.1]
related: [b-3c7ce9]
---

## Problem

Measured in the spec loop's run 31, in batch 19.

The stack finish committed `ecf59477` on top of SA-0228. It re-verified that
commit and printed `finish: escalate: red suite, 3 new failures`, then
`linked nothing`. `~/.saffron/batches/v0/finish/19/` held `findings.json` and
an empty `gates` folder. The log names no test, and nothing pushed the
commit, so the operator cannot read the failures or the commit that caused
them.

## Done looks like

An escalated finish writes each failing gate result and the commit it
judged into its batch folder, and the log line names the failures.

## Record

- 2026-10-08: filed from the spec loop's run 31.
- 2026-10-08: diagnosed by rerunning the suite on `ecf59477`. The commit only
  moved SA-0225 and SA-0228 to `done/`. `test_the_backlog_records_hold`
  failed on two items still `open` (b-5aa016, b-98a3be). b-a63235 removes the
  move. The finish still names no failure, so this item stays open.
