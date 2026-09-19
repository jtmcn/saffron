---
id: b-e9db0e
title: The projection and the checked walk read the ledger's private `_db` connection
status: open
tier: 3
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.1]
related: [b-0281e4]
---

## Problem

Found in the spec loop's run 8, 2026-09-19, reviewing #355 (`SA-0107`) and
#366 (`SA-0108`).

Both new modules query SQLite through `ledger._db`, the `Ledger`'s private
connection: `saffron/projection.py:287` on `origin/saffron/SA-0108`, and
`saffron/chain_walk.py:54` and `:64`. Each writes its own join of `tasks` to
`runs`. `saffron/ledger.py` was forbidden to
both specs, so neither could add a read method.

A schema change in `ledger.py` now breaks two modules its own tests never load.

## Done looks like

`Ledger` has public read methods for the rows the projection and the walk need,
and neither module names `_db`. A `structure` rule refuses `._db` outside
`saffron/ledger.py`, with the mutant that proves it fires.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
