---
id: b-8e30bd
title: "`reconcile` never reads an `EXHAUSTED` row, so a merged draft leaves its task `EXHAUSTED` and its dependents refused"
status: done
tier: 2
filed: 2026-10-05
closed: 2026-10-10
specs: [SA-0204, SA-0251]
prs: [678, 798]
commits: []
cites: [§4.2.1, §6.1]
related: [b-038aef]
---

## Problem

Raised by `SA-0204`'s writer and its reviewers in the spec loop's run 28,
and left out of its scope.

`SA-0204` opens a draft pull request for an `EXHAUSTED` task whose gates went
green. Its row keeps the state `EXHAUSTED`. `reconcile` asks GitHub only about
rows in `PR_PENDING_STATES` (`saffron/reconcile.py:49`): `READY_FOR_REVIEW`,
`APPROVED` and `CHANGES_REQUESTED`. So a merged draft never reaches `MERGED`
in the ledger. Every spec that depends on it stays refused, and the next night
skips them.

## Done looks like

`reconcile` reads a merged draft's row and moves it to `MERGED`. A test drives
an `EXHAUSTED` row with a pull request through a merged answer, and the
dependent spec is then a candidate.

## Record

- 2026-10-05: filed from the spec loop's run 28.
- 2026-10-10: done by `SA-0251` (#798), from the spec loop's run 33.
