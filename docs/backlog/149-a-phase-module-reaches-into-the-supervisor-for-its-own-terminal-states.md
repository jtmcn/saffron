---
id: 149
title: A phase module reaches into the supervisor for the exceptions that decide its own terminal states
status: open
tier: 2
filed: 2026-09-16
by_hand: false
specs: [SA-0088]
prs: [277]
commits: []
cites: [§5.5, §5.6]
related: [118, 140]
---

## Problem

**Tier 2.** Found reviewing `SA-0088` (PR #277); the implementer flagged it in
the pull request body too.

`run_rebut` must turn a patch that will not apply into a `RebutResult` carrying
`EXHAUSTED` or `GATE_ERROR`, rather than letting an exception escape and be
charged to nobody. The two exception types live in `saffron/cell/session.py`, and
`session.py` imports `saffron.phases.rebut` at module scope — so a module-scope
import in `rebut.py` would cycle. The cell wrote a function-local import instead,
which works and is house style for deferred `cell` imports.

What is new is the direction: a phase module now depends, at call time, on the
supervisor that drives it, for a control-flow contract. `saffron/phases/` reaching
`saffron.cell.runtime` and `saffron.cell.worktree` is established; reaching
`session.py` is not.

Nothing in `SA-0088`'s `touches` offered a shared home — `worktree.py` is
`forbidden` — so the cell had no other move.

## Done looks like

`CriticPatchRejected` and `CriticPatchUnrepresentable` moved to a lower
`saffron/cell/` module both files can import at module scope, and the local
import deleted.
