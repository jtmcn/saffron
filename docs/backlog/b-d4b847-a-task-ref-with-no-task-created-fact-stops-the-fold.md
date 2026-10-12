---
id: b-d4b847
title: "A task ref that holds no `task_created` fact stops the fold, and the wiring can write one"
status: open
tier: 1
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: []
related: [170]
---

## Problem

Found by the spec review of `SA-0278`, the spec that wires the record in.

A mirror's fetch prunes every ref the checkout lacks (`saffron/repos/mirror.py:72`).
On 2026-10-12 no mirror under `~/.saffron/mirrors/` held a `refs/saffron/*`
ref. Once `SA-0278` lands, a fact written for a task whose ref the mirror lacks
starts a new ref. `reconcile`'s `MERGED` and a scan's `ORPHANED` stamp do this
for every task that ran before the wiring. A mirror made fresh, or one for
another checkout path, does it for any task.

That ref holds no `task_created` fact. `_facts_of` refuses it
(`saffron/record/fold.py:76-79`). A strict `saffron fold` then raises
`UnreadableTask`, and `--skip-unreadable` folds the task to no rows. Its push is
refused as stale, since the origin holds another history for the key.

`SA-0278` names a cutover step: run `saffron migrate` before the first wired
night. That covers the tasks the ledger holds then, in the mirror each repo row
names. It covers no later mirror.

## Done looks like

No ref is written without a `task_created` fact. Either the writer reads the
task's ref from the origin first, or the fold places a lone fact on the task the
origin holds. A test drives both a pruned mirror and a fresh one.

## Record

- 2026-10-12: filed from `SA-0278`'s spec review, round 1.
