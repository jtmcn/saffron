---
id: b-a70ec1
title: The probe step's no-`tests`-gate path is unwitnessed, and without it the next line raises
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§5.5]
related: [117, b-ce93aa]
---

## Problem

Found by the spec loop's Spec seat reviewing #375, 2026-09-19, and verified by
the delegate.

`_probe_adequacy` returns every probe `unproven` when the repo declares no
`tests` gate (`saffron/cell/session.py`). Replacing that branch's condition
with `if False:` survives the whole default suite: no witness drives a probed
review in a repo with no `tests` gate. Without the branch the next line indexes
`gates["tests"]` and raises `KeyError`. Before the same review's `ExitStack`
fix, that ended the task with no state and no `findings.json`.

The spec named the behaviour in its body: "A repo that declares no `tests` gate
gets no probe cell". It declared no criterion for it, so `criteria` never
asked.

## Done looks like

A witness drives a probed review in a repo with no `tests` gate and asserts
every probe `unproven` with that reason.

## Record

- 2026-09-19: filed from the spec loop's run 9 (#375). Kept out of the review
  commit because #375 was already over its `size` ceiling.
