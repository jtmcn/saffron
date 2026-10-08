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
