---
id: b-d22c5a
title: "`DESIGN.md` §10 and `CONTEXT.md`'s Ledger entry name no `saffron migrate`, and `suite_drift` still says reconstruction is unbuilt"
status: done
tier: 3
closed: 2026-11-08
by_hand: true
filed: 2026-10-07
specs: []
prs: [1054]
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
- 2026-11-07: retitled in grooming. §4.6 and §10's `migrate.py` line now name the migration. §10's `cli.py` line, the Ledger entry and `suite_drift` still do not.
- 2026-11-08: done by hand in #1054.
