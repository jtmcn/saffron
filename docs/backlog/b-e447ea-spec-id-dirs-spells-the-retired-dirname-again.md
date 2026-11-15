---
id: b-e447ea
title: "`SPEC_ID_DIRS` spells `done` again, because `RETIRED_DIRNAME` sits in a module `worktree` cannot import"
status: open
tier: 3
filed: 2026-11-15
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-249808]
---

## Problem

Found reviewing #1214 (`SA-0393`) in the spec loop's run 72.

`saffron/cell/worktree.py` names `.saffron/specs/done` as a literal in
`SPEC_ID_DIRS`. The one name for that directory is `RETIRED_DIRNAME`, in
`saffron/scheduler.py`. `worktree` cannot import it, because `scheduler`
imports `session`, which imports `worktree`. So a rename of the directory
moves three readers and misses this one.

## Done looks like

`RETIRED_DIRNAME` lives in a module both can import, such as
`saffron/intake.py`. `scheduler`, `draft`, `follow_up`, `cli` and
`worktree` all read it from there.

## Record

- 2026-11-15: filed from the spec loop's run 72, #1214.
