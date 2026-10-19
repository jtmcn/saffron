---
id: b-e7898b
title: A spec that adds a refusal is never checked against the specs queued below it, so its cell spends its budget proving an impossibility
status: open
tier: 1
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-e773d9, b-e471bd, b-7d3810]
---

## Problem

Found in the spec loop's run 44.

`SA-0279` makes intake refuse a spec whose `touches` hold a `.claude`
component. `SA-0280`, `SA-0282` and `SA-0283` touch `.claude/` and sat below
it in the same stack, still queued. So the new rule refused them, and
`test_queued_specs` failed three times. The cell could fix none of that, since
`.saffron/**` and that test were forbidden. It ended `EXHAUSTED` at $17.26 of
$22. The delegate retired the three specs by hand, and the suite went green.

The spec's precondition said its three parents would sit in `done/` on its
base. That can never hold for a child in the same stack, where its parents
are open layers. The spec writer, both spec reviews and the loop's `check`
each missed it.

## Done looks like

Before a cell starts a spec that adds or widens a refusal, a check runs the
new rule over every spec queued at its base. A hit refuses the spec, or
orders it after the specs it refuses, and names each one.

## Record

- 2026-10-19: filed from the spec loop's run 44.
