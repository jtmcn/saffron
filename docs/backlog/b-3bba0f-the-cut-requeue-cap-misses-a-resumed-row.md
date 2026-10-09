---
id: b-3bba0f
title: "The cut re-queue cap looks for an earlier row, and a batch resumes the same row, so a second cut re-queues again"
status: open
tier: 1
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§4.5, §4.2.1]
related: [119]
---

## Problem

Found by the first review of `SA-0230` on 2026-10-07.

§4.5 caps a bound cut's re-queue at one per `spec_sha`. The first cut ends
`ORPHANED` and the second ends `NOT_IMPLEMENTED`. The cap finds the first
cut as another task row at the same `spec_sha` (`previous_cut_orphan`,
`saffron/cell/session.py:456-490`). That query excludes the row it runs
for (`AND t.task_id != ?`, `saffron/cell/session.py:477`).

A batch already resumes the newest `ORPHANED` row for a spec
(`saffron/scheduler.py:909-910`, `saffron/cli.py:616`,
`saffron/task.py:549`, `saffron/cell/session.py:1953-1956`). The second cut
then runs on the first cut's own row, finds no earlier row, and ends
`ORPHANED` again. Each repeat costs a full budget. §4.5 names this re-key
as owed and says the cap stops firing in silence once a re-queue resumes
its row.

`SA-0230` widens what feeds the cap. A turn cut by its own budget cap now
counts as a bound cut too.

Whether the batch breaker or the night's re-scan stops the repeats is
unmeasured.

## Done looks like

The cap counts the earlier cut when the re-queue resumed its row, and a
witness drives a second cut on a resumed row to `NOT_IMPLEMENTED`.

## Record

- 2026-10-07: filed from `SA-0230`'s first review.
