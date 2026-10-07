---
id: b-5aa016
title: "The task page shows no spec, no diff size and no model"
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§6.2, §4.1]
related: [b-cf50dc, b-d269f4]
---

## Problem

A task page in `saffron serve` names its spec by id alone. The operator who
wants to know what the task was for opens the pull request or the spec file.
The pull request body already says it: the spec's title, its type, its
`## Problem` section and the lines added and removed
(`saffron/report/pr_body.py:162`). The page says none of it.

The page lists each attempt but not the model that ran it. The ledger records
`attempts.model`, and on 2026-10-07 the operator's ledger held 222 of 2,061
attempts with a model. The rest predate the column's writer and read null.

The ledger keeps the spec's sha256 as `tasks.spec_sha` and not its text.
Measured on 2026-10-07 over the operator's ledger: 234 of 236 tasks' spec
files sit in the repo's mirror at the run's `base_sha` and hash to that
`spec_sha`. The two others are specs edited after the run pinned them.

## Done looks like

- The task page shows the spec's title, its type and its `## Problem`
  section, read from the mirror at `base_sha` and checked against `spec_sha`.
  A text that is absent or hashes to something else says so instead.
- The summary shows the lines the task added and removed, when the ledger
  holds them.
- The attempts table shows each attempt's model, blank where the ledger
  holds none.
