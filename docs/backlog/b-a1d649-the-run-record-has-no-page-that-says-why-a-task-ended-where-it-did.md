---
id: b-a1d649
title: "The run record has no page that says why a task ended where it did"
status: open
tier: 2
filed: 2026-10-05
specs: [SA-0215, SA-0216, SA-0217]
prs: [688]
commits: []
cites: [§6, §6.2]
related: [b-b51c9c]
---

## Problem

The morning queue says which task needs the operator, and §6 keeps it an
index. Why a task ended where it did sits in the ledger as attempts, gate
results and failure lines. The operator reads it with `sqlite3` and
`saffron watch`. ADR 9 decides a read-only view rendered from a second
projection of the ledger.

PR #688 landed the vocabulary, the shapes and the five view queries by hand.
No Python produces the graph or serves a page yet.

## Done looks like

`saffron serve` renders batches, tasks, phases, attempts, gate results and
findings from the view projection (`DESIGN.md` §6.2). The design is
`docs/superpowers/specs/2026-10-05-run-record-view-design.md`, and the plan is
`docs/superpowers/plans/2026-10-05-run-record-view.md`, Tasks 3 to 5.
`SA-0215` builds the view projection, and a second spec builds the server.
