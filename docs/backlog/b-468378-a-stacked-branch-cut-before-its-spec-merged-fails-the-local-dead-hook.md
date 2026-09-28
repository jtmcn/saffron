---
id: b-468378
title: A stacked branch cut before its own spec merged lacks the spec, so the local `dead` hook fails
status: done
tier: 2
filed: 2026-09-27
closed: 2026-09-27
by_hand: true
specs: []
prs: []
commits: [d5ab8aa2]
cites: []
related: [b-6518ba]
---

## Problem

Found in the spec loop's run 19, 2026-09-27, committing review fixes on #549.

The `dead` gate defers each `pending_symbols` entry of an open spec under
`.saffron/specs/`. A stack branch cut from `main` before the spec's own pull
request merged holds no copy of that spec. So the `dead` prek hook on the
host defers nothing and fails on the spec's own pending symbols.

The delegate worked around it with an untracked copy of the spec during the
commit. A cell reads the spec the host hands it, so cells pass.

## Done looks like

The hook reads the pending symbols a cell would read, or the loop's branches
carry their specs. A test holds a branch with no spec file and a declared
pending symbol.

## Record

- 2026-09-27: filed from the spec loop's run 19.
- 2026-09-27: fixed by hand. The prek hook reads a loop branch's own spec from git when its tree lacks it.
