---
id: b-038aef
title: An EXHAUSTED task whose gates went green opens no pull request
status: open
tier: 1
filed: 2026-10-01
specs: [SA-0162, SA-0151]
prs: [626, 628]
commits: []
cites: [§5.7]
related: [b-4c5dc7]
---

## Problem

Found in the spec loop's run 24, 2026-10-01.

PACKAGE pushed `saffron/SA-0162` and `saffron/SA-0151` and opened no pull
request, because each task ended `EXHAUSTED`. Both branches carried a green
gate suite, a findings file and a patch. The delegate opened #626 and #628 by
hand, from the ledger's facts, and wrote each body without
`saffron/report/pr_body.py`.

## Done looks like

A task that ends `EXHAUSTED` in REVIEW or REBUT with green gates still opens
a draft pull request. Its body names the unanswered blockers.

## Record

- 2026-10-01: filed from the spec loop's run 24.
