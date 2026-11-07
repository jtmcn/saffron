---
id: b-d5db52
title: The loop's driver refuses an EXHAUSTED task that PACKAGE published as a pull request
status: superseded
tier: 3
filed: 2026-10-14
closed: 2026-11-07
specs: [SA-0272]
prs: [875, 881]
commits: ["ae5bb327"]
cites: [§5.7]
related: [b-4901d2]
superseded_by: b-2247dd
---

## Problem

Found in the spec loop's run 39.

`SA-0272` ended `EXHAUSTED`, and PACKAGE still opened draft #875. The
operator chose to review it. `driver.py size` and `driver.py stack` both
refused, saying the task "is not reviewable, so it has no stack to sit in".
The delegate measured the size by calling the driver's `_size` by hand, and
marked the PR ready with `gh pr ready`.

## Done looks like

`record` names a decided task that has an open pull request. Once the
operator chooses to review one, `size` and `stack` take it as a layer.

## Record

- 2026-10-14: filed from the spec loop's run 39.
- 2026-10-15: again in run 40. `SA-0273` ended `EXHAUSTED` with draft #881, and
  the delegate measured its size through `_size` by hand.
- 2026-11-07: superseded in grooming by b-2247dd, filed in ae5bb327. That item names the same refusal, `reviewable` requiring `READY_FOR_REVIEW` (`driver.py:158`), across `stack`, `size` and `rebase`, and asks for a test. `record` already stores an `EXHAUSTED` task's state and pull request, since `EXHAUSTED` is in `DONE_STATES`. The spec loop run 39 and spec loop run 40 sightings here belong to b-2247dd.
