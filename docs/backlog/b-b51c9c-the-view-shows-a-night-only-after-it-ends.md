---
id: b-b51c9c
title: "The view shows a night only after it ends"
status: open
tier: 3
filed: 2026-10-05
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

`saffron serve` builds its graph once at start (ADR 9). A night that is
running shows the state it had when the server started.

## Done looks like

ADR 9 measured a full rebuild at 3.4 s over the real ledger. So the server
rebuilds when `ledger.db` changes, and it keeps the last good graph with a
stale banner when a rebuild fails the shapes. Spec it once the operator reads
one night in the history view.
