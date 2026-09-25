---
id: b-1e5572
title: "`run_task` catches `UnicodeDecodeError` around the whole reader call, so a decode failure in git's own output can become a refusal"
status: open
tier: 3
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§4.2]
related: [b-602d00]
---

## Problem

Found in the review of #514 (`SA-0136`), 2026-09-24. Not reproduced.

`run_task` catches `UnicodeDecodeError` around each `unresolved_consumes`
call and counts the entry unresolved (`saffron/task.py:354-357` on
`SA-0136`'s branch). `mirror._run` decodes every git output with `text=True`
(`saffron/repos/mirror.py:52-55`).

So a decode failure in `ls-tree` output or in a git error message is caught
too. A broken mirror then reads as an unresolved name and refuses the task.
It is not charged as infrastructure.

## Done looks like

The catch covers the file's own bytes only. A test feeds undecodable git
output and reads an error, not a refusal.

## Record

- 2026-09-25: filed from the spec loop's run 16.
