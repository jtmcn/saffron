---
id: b-d22c5a
title: "`DESIGN.md` and `CONTEXT.md` name no `saffron migrate`, and `suite_drift` still says reconstruction is unbuilt"
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§10]
related: [170]
---

## Problem

Found by the PR seats in the spec loop's run 30. Each file sat in its spec's
`forbidden` list, so no cell could fix it.

- `DESIGN.md` §10's `cli.py` layout line names neither `fold` nor `migrate`.
- `CONTEXT.md`'s **Ledger** entry names `saffron fold` and not `saffron migrate`.
- `saffron/gates/baseline.py`'s `suite_drift` docstring says rebuilding the
  drift check from a recorded run is not implemented. `SA-0223`'s
  `migrate._gate_result_facts` now does it.

## Done looks like

All three name what the migration built, by hand in one pull request.

## Record

- 2026-10-07: filed from the spec loop's run 30 (#733, #735).
