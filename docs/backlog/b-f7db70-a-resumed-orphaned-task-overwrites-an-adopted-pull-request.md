---
id: b-f7db70
title: "A kept `ORPHANED` task is resumed past its adopted pull request, and a green cell force-pushes over the by-hand head"
status: open
tier: 2
filed: 2026-11-23
specs: [SA-0430]
prs: []
commits: []
cites: [§3.3, §5.7]
related: [b-619b7d, b-f582ee]
---

## Problem

Found by `SA-0429`'s writer, in the spec loop's run 85.

`ORPHANED` is in `scheduler.REQUEUE_STATES`, so a batch offers an orphaned
spec again on its own task. Gate 0 exempts a resumed task from the open
pull request on its branch (`saffron/scheduler.py:914-920`). If that cell
goes green, PACKAGE reads the remote head as its lease and force-pushes
(`saffron/phases/package.py:970-975`). That replaces the operator's by-hand
head on `saffron/<id>`. `open_draft_pr` then finds the by-hand pull request
and marks it a draft again (`saffron/phases/package.py:459-470`).

Part of this happens today. `SA-0429` makes it worse. A red re-gate under
`saffron adopt` keeps the task `ORPHANED` with the url on its row. Then
`saffron package` and `push_unpackaged_work` both refuse it.

## Done looks like

`build_queue` does not resume an `ORPHANED` task that carries a `pr_url`.
It refuses the spec as `open_pr_on_spec`, naming that url. A plain scan
over such a row, before and after the url is set, is the witness.

## Record

- 2026-11-23: filed from the spec loop's run 85.
- 2026-11-23: specced as `SA-0430`.
