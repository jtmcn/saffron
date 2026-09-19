---
id: b-a8270f
title: A change whose subject is history never runs against a real ledger in the cell, and #355 left out 75 of 76 merged tasks
status: open
tier: 1
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.1, §5.4]
related: [b-2750d5, b-952c34, b-946f03, 97]
---

## Problem

Found in the spec loop's run 8, 2026-09-19, reviewing #355 (`SA-0107`).

`SA-0107`'s projection looked up each task's spec under `.saffron/specs/` and
missed `.saffron/specs/done/`, where every merged spec lives. Over a copy of
the real ledger it left out 75 of 76 merged tasks. Every witness in the cell
passed.

Four spec reviews and three lenses missed it. The loop's Spec seat found it by
running the module over a backup of `~/.saffron/ledger.db`. The review commit
`5bce64a` fixed the lookup, and 38 merged tasks were then kept.
#366's own real-data run is the source of item b-952c34.

A cell has no ledger but the one its own task writes. Projection, reporting,
`reconcile`, `watch` and the index all read history, and no gate executes them
over any.

## Done looks like

A spec can declare that its subject is history. For such a spec, a host-side
step runs the named command over a read-only copy of the ledger and batch tree.
It records what the command printed. The critic reads that output. A spec
that cites `.saffron/specs/` paths gets a step 1b question: does the code need
`done/`?

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353). Ranked second in
  `docs/evidence/2026-09-19-spec-loop-skill-feedback-run-8.md`.
