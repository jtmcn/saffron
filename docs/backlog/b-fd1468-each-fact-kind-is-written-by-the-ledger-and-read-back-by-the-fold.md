---
id: b-fd1468
title: Each fact kind is written by the ledger and read back by the fold, and nothing makes the two halves agree
status: open
tier: 1
filed: 2026-09-20
specs: []
prs: []
commits: []
cites: [§4.1, §4.6]
related: [170, 177, b-25766a, b-e9db0e]
---

## Problem

Found 2026-09-20 in an architecture review of the record and the fold.

`saffron/ledger.py` builds each fact's payload as keyword arguments in its
write methods. `saffron/record/fold.py` reads the same keys back by string and
calls those write methods again. So each of the eleven task kinds lives in two
modules. A key renamed in one half fails only when a test folds that kind.

The fold also reaches into `ledger._db` fourteen times, to undo three things the
ledger's writes do.

- Every write stamps `datetime('now')`, so `_retime` rewrites each timestamp
  from `fact.at`.
- `create_task` mints a `record_key` only when a record is attached, so
  `_upsert_task` patches the key in after the insert.
- Every write method commits on its own, so a `with` block cannot roll a task
  back. `_discard_task` deletes the rows instead. That is measured in
  `docs/evidence/2026-09-20-fold-rebuild-time.md`.

Facts also carry the source ledger's `attempt_id` and `finding_id`. The fold
mints new ids and keeps a map from old to new, which is why a rebuttal can
arrive with nothing to attach to.

Item 170 asks that deleting the ledger and rebuilding it give the same rows.
Today that holds only as far as a test drives each kind.

## Done looks like

One private `Ledger._apply(fact)` is the only code that turns a task fact into
rows. It raises on a kind it cannot place.

- Each write method builds its fact, applies it, commits once, then appends it.
- `Ledger.fold_task(facts)` drops a task's rows, applies every fact and commits
  once. It is the only ledger method the fold calls.
- `fold()` keeps creation order, unreadable tasks and strict or skip, and names
  no `_db`.
- Timestamps come from `fact.at`. Every task carries a `record_key`, and a
  `NULL` key is backfilled when the ledger opens.
- An attempt is named by `(phase, n)` and a finding by its position in the task,
  so the fold keeps no map. A rebuttal with no finding raises.
- One round-trip test per kind writes through a `MemoryRecord`, folds into a
  fresh ledger and compares rows. It is run against a mutant that drops a
  column.

The run and batch kinds stay out, with item 177. So do the projection's reads
(item b-e9db0e) and the vocabulary entry (item b-25766a).

## Record

**Filed 2026-09-20 by hand**, from candidate C1 of an architecture review.
The decisions above were settled with the operator before filing. It sits in
tier 1 beside item 170. It makes 170's rebuild test hold for every task kind,
not only for the kinds a test drives.

`saffron/ledger.py` must sit in the spec's `touches`. Item b-e9db0e records the
cost of forbidding it: two modules wrote their own joins over `_db` instead.
