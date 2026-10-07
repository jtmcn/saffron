---
id: b-f6ebc2
title: "No attempt records the reasoning effort it ran at"
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§4.1, §6.2]
related: [b-5aa016]
---

## Problem

An attempt's cost and turns are in the ledger. The reasoning effort it ran at
is nowhere. The host builds every session's options in
`saffron/phases/implement.py:173`, and that dict sets no model and no effort.
Both fall to the agent SDK's defaults inside the cell image.

The model is recorded anyway. `images/agent_runner.py` reads it off each
assistant message and the host writes it to `attempts.model` (SA-0205). No
event carries effort, so nothing can write it, and no page or query can say
whether a task ran at low effort or high.

Without it, a cost or a quality difference between two nights has one
unrecorded cause the record cannot rule out.

## Done looks like

- A spike first: what the SDK in the cell image accepts for effort and
  whether any event it emits reports the effort a turn ran at. The answer
  decides whether the value is read from an event or taken from the options
  the host sent.
- Each attempt records its effort in the ledger, null for attempts that
  predate the writer.
- The run record view states it beside the model (b-5aa016).
