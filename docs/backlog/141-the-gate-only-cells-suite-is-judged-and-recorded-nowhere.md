---
id: 141
title: The gate-only cell's suite is the one judged gate suite that lands in no record
status: open
tier: 1
filed: 2026-09-16
by_hand: false
specs: [SA-0089]
prs: [282]
commits: []
cites: [§5.4, §5.5]
related: [118, 140]
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
