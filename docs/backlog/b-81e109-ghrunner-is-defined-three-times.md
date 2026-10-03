---
id: b-81e109
title: "`GhRunner` is defined three times, word for word"
status: open
tier: 3
filed: 2026-10-03
specs: []
prs: [647]
commits: []
cites: []
related: []
---

## Problem

Found by #647's Standards seat in the spec loop's run 26.

The `GhRunner` alias appears with identical text in `saffron/reconcile.py`,
`saffron/scheduler.py` and `saffron/phases/package.py`. `CLAUDE.md` asks
for one source. `cli.py` and `finish.py` each import a different copy.

## Done looks like

One module defines `GhRunner`, and every other module imports it from
there.

## Record

- 2026-10-03: filed from the spec loop's run 26.
