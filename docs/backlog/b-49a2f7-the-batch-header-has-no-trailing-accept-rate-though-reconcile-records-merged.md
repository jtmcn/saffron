---
id: b-49a2f7
title: The batch header shows no trailing accept rate, though `reconcile` now records `MERGED`
status: open
filed: 2026-10-02
specs: []
prs: []
commits: []
cites: [§6, §8]
related: [52, 164]
---

## Problem

Found on 2026-10-02 while asking how to see the queue beyond a single task.

§6 names the trailing accept rate as the one header number that says whether
Saffron works. §6 says it had no source because nothing recorded a merge. Item 52
gave it one, and `saffron reconcile` is now the writer of `MERGED`.

`saffron/replay.py` is the only code that names the field. It passes the literal
`"—"`. `run_task` and PACKAGE pass no header field for it at all, so the rendered
page omits the number.

## Done looks like

The header of `index.html` shows the accept rate over the last twenty settled
tasks, read from the ledger. §6 defines settled, as the operator decided on
2026-10-02. The header says how many tasks the window holds when that is fewer
than twenty.

## Record

- 2026-10-02: filed from a session that surveyed the operator's views of the queue.
