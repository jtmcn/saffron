---
id: b-f603c9
title: A `REBUTTAL_UNJUDGED` parent whose push was refused still admits its child, which is then cut from `base_sha` without the parent's code
status: open
tier: 1
filed: 2026-10-11
specs: [SA-0330]
prs: []
commits: []
cites: [§4.2, §5.6]
related: [120]
---

## Problem

Found by the spec review of `SA-0276`, 2026-10-11. Every line below was read
at `b7d99716`.

`REBUTTAL_UNJUDGED` is in `DEPENDENCY_WAITING_STATES`
(`saffron/scheduler.py:97-99`). So `_dependency_refusal` admits a child of a
parent in that state, whatever the parent's row records
(`saffron/scheduler.py:631-632`).

The parent opens no pull request. `run_task` pushes its branch through
`push_unpackaged_work` (`saffron/task.py:715-727`). That push can refuse
(`saffron/phases/package.py:1122-1164`). The refusals named here are
examples, not a complete list. It refuses a credential in the patch or in a
commit subject. It refuses when `patch.json` or the remote cannot be read.
It refuses when another task of the spec awaits review, and when the branch
points at a commit the spec never pushed. A refused push records no new
`pushed_sha`.

`_resolve_stacked_on` then takes the newest waiting row. Without a `gh` it
reads `DEPENDENCY_WAITING_STATES` (`saffron/task.py:248-251`). On a batch it
reads `_STACKABLE_ON_RECONCILE` instead (`saffron/task.py:262`). Either way
the row's `pushed_sha` decides the result, in one of two shapes.

- **No push recorded.** A row with no `pushed_sha` unstacks the cell
  (`saffron/task.py:299-308`). The child is cut from `base_sha` without the
  parent's code, and it fails its own gates against code that does not
  exist. §4.2 calls ordering without stacking "a version that lies".
- **A stale push.** A resumed row keeps the `pushed_sha` an earlier run
  recorded. When the latest run's push is refused, the child stacks on that
  older branch head, without the latest run's work.

An `EXHAUSTED` parent does not reach this path. It is in
`DEPENDENCY_DEAD_STATES` (`saffron/scheduler.py:105`), so the scheduler
refuses its child unless another row of the parent still waits.

## Done looks like

A child of a `REBUTTAL_UNJUDGED` parent is admitted only when that parent's
latest run pushed. Otherwise its refusal names the parent's refused push.
