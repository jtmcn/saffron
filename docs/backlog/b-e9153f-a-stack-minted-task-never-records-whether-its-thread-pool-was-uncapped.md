---
id: b-e9153f
title: "A task a `--stack` batch mints never records whether its thread pool was uncapped"
status: open
tier: 2
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§5.1]
related: [b-0569f7]
---

## Problem

Found reviewing `SA-0282`.

ADR 10's principle 7 accepts an uncapped pool on a shared kernel because the
task records it. `SA-0282` records it as `thread_pool_uncapped` on the
`task_created` fact, which `_drive_cell` writes when it mints the task.

A `--stack` batch mints its tasks in `_stack_mint` (`saffron/cli.py:1108-1131`)
before any policy is read. Its `create_task` call passes no value, so the fact
carries `None`. The cell still warns when it loads the policy, but the record
never says the pool was uncapped. A `--stack` night is the default way the
operator runs the queue.

## Done looks like

A task a `--stack` batch mints records whether its pool was uncapped, and a
test drives `_stack_mint` and reads the value from the task's facts.

## Record

- 2026-10-11: filed from the review of `SA-0282`.
