---
id: b-2d09de
title: '`saffron watch` follows one task, so a night of several tasks needs one pane per spec id'
status: open
filed: 2026-10-02
specs: [SA-0197]
prs: []
commits: []
cites: [§6]
related: [62, 64]
---

## Problem

Found on 2026-10-02 while asking how to see the queue beyond a single task.

`saffron watch` takes one spec id and reads `<out_dir>/<spec id>/events.jsonl`
(`saffron/cli.py`, `_watch`). The docstring of `saffron/watch.py` leaves a night's
worth of tasks to the batch index. The index gets a row only when a task ends.
So an operator who wants to follow `saffron batch` live must know each spec id
in advance. They open one pane per id and guess which task the night starts next.

## Done looks like

One command follows every task a night runs, in one stream. Each line names its
spec id ahead of the text `describe` already prints. A task that starts after
the command begins joins the stream without a restart. The follower reads each
log past its own offset, as item 62 made `watch` do for one log.

## Record

- 2026-10-02: filed from a session that surveyed the operator's views of the queue.
