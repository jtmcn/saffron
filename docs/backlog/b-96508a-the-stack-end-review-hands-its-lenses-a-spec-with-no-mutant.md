---
id: b-96508a
title: The stack's end review hands its lenses a spec with no mutant from the ref, so it judges a witness the cell set aside
status: open
tier: 2
filed: 2026-11-10
specs: []
prs: []
commits: []
cites: [§5.4.1, §4.2.1]
related: [b-c5da95, 80]
---

## Problem

Found by the Spec seat reviewing `SA-0363` (#1135) in the spec loop's run 60.

`SA-0363` attached the ref's mutants in `regate`, `package` and `review`
through `mutants.attach_mutants_at`. The stack's end review was left out. Its
specs are parsed from the recorded text or a stored payload
(`saffron/batch.py` near line 1002, `saffron/cli.py` near line 2790). So
`end_review._review_one_layer` hands its lenses a spec whose criteria carry
no mutant. Read from the code and not run.

## Done looks like

The end review's lenses read each layer's spec with its pinned mutants
attached, as `run_task` does. A witness drives one layer whose mutant lives
only on the ref.

## Record

- 2026-11-10: filed from the spec loop's run 60.
