---
id: b-f71105
title: "`prepare_worktree`'s retry pause reaches `time.sleep` by module attribute, not an injected `sleep`"
status: open
tier: 3
filed: 2026-10-09
specs: []
prs: [779]
commits: []
cites: []
related: [b-8a0c9a, b-f582ee]
---

## Problem

Found by batch 20's end review in the spec loop's run 32.

`SA-0232` added one retry to the seed, with a pause between the two runs.
The pause calls `time.sleep(_RETRY_PAUSE_S)` through the module
(`saffron/cell/worktree.py:151`), and the witness monkeypatches
`worktree.time.sleep`. `saffron/watch.py` and `saffron/batch.py` take
`sleep` as a parameter instead. The end review drafted `SA-0257` to inject
it. The cell ended `EXHAUSTED` at $2.96 with one new failure, and the batch
dropped it. Its spec text is under `follow_ups` in
`~/.saffron/batches/v0/finish/20/findings.json`.

## Done looks like

`prepare_worktree` takes `sleep` as a keyword argument, defaulting to
`time.sleep`, and the witness passes a fake rather than patching the module.

## Record

- 2026-10-09: filed from the spec loop's run 32.
