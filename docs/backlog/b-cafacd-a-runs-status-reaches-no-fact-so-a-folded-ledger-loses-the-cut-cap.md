---
id: b-cafacd
title: A run's status reaches no fact, so a ledger folded from the record loses SA-0126's cap on cut retries
status: open
tier: 2
filed: 2026-09-22
specs: []
prs: []
commits: []
cites: [§4.1, §4.2.1]
related: [170, b-36b551, b-149df3]
---

## Problem

Found 2026-09-22, revising `SA-0126` against its review.

`SA-0126` lets a spec retry once after a cut with nothing committed. The
first cut at a `spec_sha` ends `ORPHANED`, and the second ends
`NOT_IMPLEMENTED`. To find the first, it looks for an earlier `ORPHANED` task
at the same `spec_sha`. That task's run finished `COMPLETE`, and its attempts
are all in phase `IMPLEMENTING`. The run's status is what tells a cut apart.
A kill finishes its run `ABORTED`, and a scan's stamp leaves it `RUNNING`.

No fact carries a run's status. `saffron/record/contract.py:32-33` declares
`run_created` and `run_finished`, and nothing appends either.
`saffron/record/fold.py:8-12` says `create_run` and `finish_run` append no
fact, so a rebuild leaves `runs.status` unset. `_run_for` inserts each folded
run as `RUNNING` (`saffron/ledger.py:486-489`). In a folded ledger no earlier
cut matches, so every cut re-queues, every night.

The task facts cannot stand in. Take a wall cut that leaves one commit, then
a kill during the first gate suite. Gate results are recorded only after the
suite returns. That task's facts are `task_created`, `task_state`
`IMPLEMENTING`, two closed attempts in phase `IMPLEMENTING`, the second with
subtype `error`, and `task_state` `ORPHANED`. A wall cut that stops with
nothing committed and no budget to salvage writes the same facts.

Nothing live uses a folded ledger yet. Item 170 makes the record
authoritative, and this is one more thing a fold would lose.

## Done looks like

`finish_run` appends a `run_finished` fact carrying the status, and the fold
rebuilds `runs.status` from it. Then `SA-0126`'s cap reads the same answer
from a folded ledger as from the live one. Or a task fact carries why a task
ended `ORPHANED`, and the cap keys on that instead.
