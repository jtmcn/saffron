---
id: b-c5da95
title: "`regate`, `adopt`, `package` and `review` read no mutant from the ref, so they judge a witness the cell set aside"
status: open
tier: 2
filed: 2026-11-07
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [80]
---

## Problem

Found reviewing `SA-0338`, 2026-11-07.

`SA-0338` moves each criterion's mutant onto `refs/saffron/mutants`, and
`run_task` attaches them at the commit the task's row records. Four commands
load a spec's text without `run_task`: `saffron regate` (`saffron/regate.py:91`),
`saffron adopt` through its automatic regate (`saffron/cli.py:2984-2999`),
`saffron package` through `ready_task`, and `saffron review`
(`saffron/commit_review.py:138`). None of them sees a mutant.

`revert` sets a witness aside only through `c.mutant`
(`saffron/gates/core/revert.py:186-200`). So a regate can judge a witness the
cell's own `revert` set aside, and report it as a new failure. `adopt` moves a
task to `READY_FOR_REVIEW` only when the regate finds none.

## Done looks like

Each of the four commands attaches the mutants the ref held at the task's
recorded `mutants_commit`, as `run_task` does. A test regates a task whose
witness the cell set aside and finds no new failure.

## Record

- 2026-11-07: filed with `SA-0338`, from its first spec review.
