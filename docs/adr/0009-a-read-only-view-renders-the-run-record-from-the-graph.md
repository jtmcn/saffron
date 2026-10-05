---
id: 9
title: "A read-only view renders the run record from the graph"
status: accepted
date: 2026-10-05
supersedes: []
superseded_by: []
appendices: [O, T]
principles: [25, 61]
---

## Context

The morning queue answers which tasks need the operator. It is an index, and
diffs are read on GitHub (§6). It does not answer why a task ended where it
did. That answer sits in the ledger as attempts, gate results and failure
lines. The operator reads it today with `sqlite3` and `saffron watch`.

Appendix T rebuilt a projection of the run record for Q4 alone. Coverage
follows readers, so the vocabulary states no batch window, no timestamp and
no gate outcome.

## Decision

A command, `saffron serve`, renders the run record as pages read from a view
projection. The projection is a second graph beside Q4's. It states every task
in every state, and it never decides whether a chain holds.

The graph holds structure. Failure lines stay in the ledger and are read by
gate result id. The ledger is opened read-only.

Nothing outside `saffron/cli.py` imports `saffron.view`, and a `structure`
rule says so. No page feeds a scheduler, a gate or a state change (ADR 5).

## Principles

- **25** upholds. Each new term keeps its place only while a view query or a
  shape reads it, and the dead-term test still governs.
- **61** upholds. The view queries run over the real ledger whenever a page is
  served. Their fixture results test the queries, and the pages test the
  record.

## Consequences

- Six terms join the vocabulary, and a view query reads each one.
- `GateShape` requires a blocking level only of a declared gate. A gate known
  only from its result carries none, because the ledger keeps the policy's
  hash and not its text.
- A full rebuild over the real ledger took 3.4 s on 2026-10-05, for about
  24,000 triples. SHACL validation was 2.4 s of it. So the live overlay
  rebuilds on each ledger change, and it needs no `events.jsonl` tail.
- The morning queue keeps its job and its sort. §6.2 places the view beside it.
