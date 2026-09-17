---
id: 141
title: The gate-only cell's suite is the one judged gate suite that lands in no record
status: done
tier: 1
filed: 2026-09-16
closed: 2026-09-17
by_hand: false
specs: [SA-0089, SA-0095]
prs: [282, 307]
commits: []
cites: [§5.4, §5.5]
related: [118, 140, 160]
---

## Problem

**Tier 1.** Found reviewing `SA-0089` (PR #282).

Every other judged suite lands somewhere: `_judge` writes each implementer suite
with `ledger.record_gate_result`, the pre-turn baseline is written to
`task_dir/baseline.json`, and `repair_loop` and `_rebut_gates` each emit an
attempt event. The gate-only cell's comparison is emitted nowhere, recorded
nowhere, and written to no file — it is rendered into a lens prompt and
discarded.

`CONTEXT.md` ("A gate suite's number … counts the gate suites judged in a task")
and `DESIGN.md` §5.4's rule that a gate result belongs to an attempt both assume a
judged suite lands somewhere. This one does not, so **nothing in the ledger
distinguishes a run whose lenses saw an honest gate table from one where they saw
a forged one** — which is the exact property `SA-0089` exists to establish. The
spec establishes it and keeps no evidence that it held.

The spec's "print nothing new on the green path" is a bar on stdout, for the
`watch-golden.txt` fixture. A ledger row or a file prints nothing.

## Done looks like

The gate-only cell's results written to `task_dir/lens-gates.json` beside
`baseline.json`, or recorded against the REVIEW attempt — so a reader can tell,
after the fact, which table the lenses were shown.

## Record

**Closed 2026-09-17 by PR #307**, `SA-0095` in the spec loop's run 5 (stack
#308): the Gate-only cell's results land in `lens-gates.json`, for clean,
aborted and drifted suites, before any lens. That is the first of the two arms this
item offered, and it is the arm that buys the property. A reader can now tell,
after the fact, which table the lenses were shown.

The ledger row was the other arm of an `or`, not a second thing owed. It is not
taken. Taking it first needs an answer to what the suite belongs to. §4.1 sets
exactly one of `attempt_id` and `run_id`. The Gate-only cell's suite is neither
an implementer attempt nor the run's baseline, so no row shape fits it yet.
Item 160 carries that question.
