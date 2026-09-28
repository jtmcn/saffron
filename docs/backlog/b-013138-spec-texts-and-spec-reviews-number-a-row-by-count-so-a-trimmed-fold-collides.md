---
id: b-013138
title: A spec text or spec review row is numbered by its count, so the write after a trimmed fold collides
status: open
tier: 3
filed: 2026-09-28
closed:
specs: []
prs: []
commits: []
cites: [§4.1]
related: [b-792ab2, 170]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, by #559's Spec seat (`SA-0182`).

`record_spec_text` numbers its row `1 + COUNT(*)` over the task's `spec_texts`
rows (`saffron/ledger.py:1466-1472` at `f682d58f`). `record_spec_review` does the
same over `spec_reviews` (`:1411-1418`). Both tables key on `(task_key, n)`
(`:231-252`).

Fold a fact list with `n=1` trimmed, and the next write computes `n=2` again.
It raises `IntegrityError: UNIQUE constraint failed: spec_texts.task_key,
spec_texts.n`. The seat measured this with a script. A record is append-only, so
no production path folds a trimmed list today. `SA-0182`'s criterion 1 asked
for the count rule, so review kept it.

## Done looks like

Both writes number a row one past the task's `MAX(n)`, or from 1. A test folds a
trimmed fact list, writes once more, and reads back the new row.

## Record

- 2026-09-28: filed from the spec loop's run 20.
