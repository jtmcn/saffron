---
id: 160
title: The Gate-only cell's suite belongs to no attempt and no run, so no ledger row fits it
status: open
tier: 2
filed: 2026-09-17
by_hand: true
specs: []
prs: [307]
commits: []
cites: [§4.1, §5.5]
related: [141]
---

## Problem

**Tier 2.** What item 141's close left, 2026-09-17.

Item 141 offered the file or the ledger row. `SA-0095` (PR #307) took the file:
the Gate-only cell's results land in `task_dir/lens-gates.json` before any lens.
The row was left out because the schema has nowhere to put it.

§4.1 sets exactly one of `attempt_id` and `run_id`. The null is the point: a
gate result belongs to an attempt, and the baseline suite is the one exception
(§4.4). The Gate-only cell's suite is neither of those. REVIEW has no attempt
row, and the suite is judged with no agent and no session. The run's baseline is
measured at `base_sha`, while this suite runs at head in its own cell. So
`record_gate_result` would take two null ids, which that sentence forbids. The
alternative is a borrowed id, which credits the suite to work that did not
produce it.

The cost of the file-only answer is narrow and real. `lens-gates.json` lives in
the batch tree, so nothing in the ledger joins the table the lenses read to the
task that showed it. No query can ask how often REVIEW judged a drifted suite
across tasks. `harness/lens_scoring.py` reads the ledger.

## Done looks like

REVIEW's gate suite is queryable in the ledger, joined to its task. That first
needs a decision about what it belongs to. Either REVIEW gains an attempt row of
its own, with no session and no cost. Or `gate_results` gains a third nullable
owner, and §4.1's sentence names it. `CONTEXT.md`'s count of "the gate suites
judged in a task" then agrees with the answer.

## Record

**Filed 2026-09-17 by hand**, from item 141's close. By hand because the change
spans `DESIGN.md` §4.1, `ontology/factory.ttl` and the `CONTEXT.md` generated
from it. A cell cannot move the generated half with the vocabulary in one task.
