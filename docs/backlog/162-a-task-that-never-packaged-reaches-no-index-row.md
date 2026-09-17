---
id: 162
title: A task that never reached PACKAGE reaches no index row, so the page ranks ten states it can never show
status: open
filed: 2026-09-17
specs: [SA-0100]
prs: []
commits: []
cites: [§6, §5.7]
related: [45]
---

## Problem

Found 2026-09-17, reading what a single execution can be seen through.

§6 makes the index the page an operator reads first. Its level 2 holds "every
state that needs you and is not a reviewable diff", and names eight of them:
`MERGE_FAILED`, `PLAN_REJECTED`, `PREFLIGHT_FAILED`, `GATE_ERROR`,
`NOT_IMPLEMENTED`, `EXHAUSTED`, `ORPHANED` and `RATE_LIMITED`.
`saffron/report/index.py` implements that in `_STATE_RANK`, which ranks twelve
states, adding `REVIEWING` and `REBUTTING` at the elevated-risk level.

Ten of those twelve can never appear on the page.

`append_queue_line` has exactly two callers. `saffron/replay.py:143` is v0 and
agent-free. `saffron/phases/package.py:966` sits inside `_finish`, which a task
reaches only by reaching PACKAGE. `saffron/task.py:316` gates that on
`outcome.state == "READY_FOR_REVIEW"`. Every other outcome takes the branch at
`saffron/task.py:331`, prints one line at `:352`, and returns at `:353`. No row
is written.

Measured against `~/.saffron/ledger.db` and
`~/.saffron/batches/v0/queue.json`: the ledger holds 99 tasks and the store holds
68 rows. The 68 are 65 `MERGED` tasks and 3 at `READY_FOR_REVIEW`. The missing 31
are `EXHAUSTED` 9, `NOT_IMPLEMENTED` 8, `ORPHANED` 7, `PLAN_REJECTED` 3,
`REBUTTING` 1, `RATE_LIMITED` 1, `PREFLIGHT_FAILED` 1 and `GATE_ERROR` 1.

Two nearby omissions are deliberate, and neither covers this one. `_finish` at
`saffron/phases/package.py:955-958` writes no row for a PACKAGE that raises. Its
reason is that a link pointing at a pull request that was never opened is worse
than no line. That is about a link that would be wrong. A task that never entered
PACKAGE has no link at all, and `QueueLine.link` is a plain string.

`PushResult` is "Deliberately not `PackageResult`", because that type feeds
`_finish` and "neither happens here (§0's own boundary: this is not packaging)".
That boundary is correct, and it is why the fix does not belong in PACKAGE.
Packaging is not what produced an `EXHAUSTED` task.

The header undercounts with the rows. `tasks` and `spend` are computed from the
stored rows inside `append_queue_line`, so both report a night smaller and
cheaper than it was.

## Done looks like

Every task a cell drives reaches the index with a row carrying its own terminal
state. `saffron/task.py` writes it, as the one module that drives a task end to
end. The row for an unpackaged task carries an empty link rather than a branch
name. A spec that fails once and packages later leaves one row, holding the
packaged outcome. A PACKAGE that raises still writes nothing.

## Record

**Filed 2026-09-17**, from an inventory of what one execution can be seen
through. `SA-0100` carries it.
