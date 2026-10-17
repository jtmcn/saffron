---
id: b-60317d
title: "`reconcile`'s `head_moved` comment says a moved head is not ours to judge, and a re-gate now judges one"
status: open
tier: 3
filed: 2026-10-16
specs: []
prs: []
commits: []
cites: []
related: [97]
---

## Problem

Found by the Standards seat on #893 (`SA-0275`).

`ReconcileResult.head_moved` carries the comment "`head_moved` is reported
only — the extra commits are not ours to judge" (`saffron/reconcile.py`).
`SA-0275` added the `regates` table, and `SA-0284` adds the command that
fills it. The comment is false once a re-gate exists. `SA-0275` was told to
leave it, and `SA-0284` does not touch `reconcile.py`.

## Done looks like

The comment says a moved head is reported, and that a re-gate at that head
is reported beside it. It carries no em dash.

## Record

- 2026-10-16: filed from the spec loop's run 42.
