---
id: b-2d2014
title: The cell-watch mod follows the last task before the new one writes its log, and its stop re-attaches
status: done
tier: 3
filed: 2026-10-24
closed: 2026-11-08
by_hand: true
specs: []
prs: [1072]
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
- 2026-10-27: in the spec loop's run 49 the hand-over wake-ups for four tasks arrived hours late, in one burst, after the delegate's review turns ended.
- 2026-11-08: done by hand. Run 49's late wake-ups are left open. They read as the
  session holding each prompt until its turn ends, which nobody measured.
