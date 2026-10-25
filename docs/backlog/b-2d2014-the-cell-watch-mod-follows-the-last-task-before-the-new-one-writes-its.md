---
id: b-2d2014
title: The cell-watch mod follows the last task before the new one writes its log, and its stop re-attaches
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 47.

Called with `{}` before `SA-0311` had an `events.jsonl`, the watch followed run 46's
`SA-0305`. The delegate armed a Monitor until the new log appeared. Called with
`{stop: true}`, the watch answered "Watching the newest task" and kept running.

## Done looks like

The watch waits for a task the batch names, and a stop ends it.

## Record

- 2026-10-24: filed from the spec loop's run 47.
- 2026-10-25: recurred three times in the spec loop's run 48. Each time the watch
  attached to a new task, it first reported the previous task as packaged and the new
  one as started.
