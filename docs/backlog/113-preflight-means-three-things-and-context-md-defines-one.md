---
id: 113
title: '"Preflight" means three things, and `CONTEXT.md` defines one'
status: open
tier: 2
filed: 2026-09-13
by_hand: true
specs: []
prs: []
commits: []
cites: [§4.2.1, §5.1]
related: [37]
---

## Problem

**Tier 2.** Found 2026-09-13 trialling the spec loop's Standards review seat on
`SA-0029`'s packaged head (PR #91); both trial runs raised it on their own, and
it is on main unchanged.

- `CONTEXT.md`'s **Preflight** (`CONTEXT.md:488`) is "Per-repo readiness at
  batch start — mirror fetch, policy parse, image rebuild, baseline. A repo that
  fails preflight is skipped, not fatal." That is `preflight.check_readiness`
  (§4.2.1).
- `events.Preflight` (`saffron/events.py:110`) is "One step of standing the cell
  up … the proxy, the image build, the port probe, the worktree coming online",
  emitted from inside `run_one_cell` (`saffron/cell/session.py:988`) and by
  `task.py`'s stacking check (`step="unstacked"`).
- `PREFLIGHT_FAILED` is a task's terminal state, set when that task's baseline
  aborts inside its cell (`saffron/cell/session.py:1141`) — fatal to the task,
  where the glossary's preflight skips a repo.

It stays quiet for item 37's reason: the senses overlap where they happen to
agree — "image build" is in two of the three lists.

## Done looks like

`CONTEXT.md` naming the per-task sense beside the per-repo
one — a terminal state already carries the word, so the term cannot stay
batch-only — or `events.Preflight` renamed after §5.1's cell construction and
`PREFLIGHT_FAILED` defined. The **Preflight** entry is hand-written, outside
the first sentences `ontology.render` rewrites, and `CONTEXT.md` is `protected`,
so by hand, like 37 and 38.
