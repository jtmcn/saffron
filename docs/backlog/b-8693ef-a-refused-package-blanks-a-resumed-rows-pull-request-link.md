---
id: b-8693ef
title: A refused PACKAGE blanks a resumed row's pull request link, so no merge moves that row
status: open
tier: 3
filed: 2026-10-30
specs: []
prs: []
commits: []
cites: [§5.7]
related: [b-af24d1, b-223244]
---

## Problem

Found while writing `SA-0331`, and measured on a prototype at `f596e814`.

A later trace undercut this item's premise. A rerun runs on a fresh row (b-223244).
Only a by-hand `saffron adopt` race now reaches this case (`SA-0331`). As filed: a
`CHANGES_REQUESTED` row re-queues on its own task and keeps its pull request link. When PACKAGE then refuses, `_finish` (`saffron/phases/package.py:998-1005`)
writes the result's empty `pr_url` and `pushed_sha` over the row.

The row loses its link, so `reconcile` skips it (`saffron/reconcile.py:178`). A
merge of that pull request never moves it to `MERGED`. `SA-0331`'s guard also
reads the link, so this row gets only the branch check. That check held in the
measured case, because the row's own sha was blanked and no other row recorded
the head. An absent branch, or another row recording that head, would let the
push land. That part is reasoned and not measured.

## Done looks like

A refused PACKAGE keeps the pull request link a resumed row carried. A merge of
that pull request moves the row to `MERGED`, and the push guard refuses.
`SA-0331`'s criterion 2 asserts that this row names no pull request, so that
assertion changes with this fix.

## Record

- 2026-10-30: filed from `SA-0331`, whose guard covers rows that still carry a
  link.
