---
id: b-a90136
title: '`size` has no builder for its failure message, so the plan checkpoint restates it'
status: open
tier: 3
filed: 2026-09-23
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-408cf5, b-89ec93]
---

## Problem

Found in the spec loop's run 15, 2026-09-23, on `SA-0125` (#473) and
`SA-0128` (#483).

`judge_estimate` in `saffron/agents/artifacts.py` rebuilds `size_gate`'s
failure text, `{n} changed tokens exceeds the {type} ceiling of {ceiling}`,
because `size.py` exposes no function for it and both specs forbade editing
`size.py` from the checkpoint's side. `size.py` itself writes the text twice.
A witness catches drift today. Both Standards seats called it a second
source.

## Done looks like

`size.py` exports one function that builds the message, `size_gate` and
`judge_estimate` both call it, and no copy of the format string remains.

## Record

- 2026-09-23: filed from the spec loop's run 15 (#473, #483).
