---
id: SA-0081
title: a spec driven twice writes both tasks into one event log, and watch shows them as one
type: bug
priority: 3
depends_on: [SA-0080]
touches:
  - saffron/watch.py
  - saffron/cli.py
  - tests/test_watch.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - spikes/**
  - saffron/events.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/intake.py
  - saffron/replay.py
budget_usd: 6
max_attempts: 3
max_turns: 40
acceptance:
  - claim: >-
      By default, `watch` renders a task directory's log from the start of its
      newest task, so a log holding two tasks of one spec shows only the
      second. Today it shows both with nothing between them, and an operator
      watching a spec driven again reads the earlier task's rejected plan as
      the current one's.
    witness: tests/test_watch.py::test_the_default_view_starts_at_the_newest_task
  - claim: >-
      The whole log stays reachable behind a `watch` flag, every task in
      order, so nothing the default view skips is lost.
    witness: tests/test_watch.py::test_the_whole_log_is_still_reachable_behind_a_flag
  - claim: >-
      The command passes that flag through to the follower.
    witness: tests/test_cli.py::test_watch_passes_the_whole_log_flag_through_to_the_follower
  - claim: >-
      A log with no task boundary in it, written before tasks recorded their
      ceilings on the way in, still renders in full, as it does today.
    witness: tests/test_watch.py::test_a_log_renders_as_the_lines_its_terminal_printed
    preserves: true
  - claim: >-
      A follower still renders only the events that arrived since its last
      poll, as it does today.
    witness: tests/test_watch.py::test_following_emits_only_events_that_arrived_since_the_last_poll
    preserves: true
---

## Context

`docs/BACKLOG.md` item **64**, measured 2026-09-04 while reading `SA-0051`'s
second attempt with `watch`.

The batch tree keys a task directory by spec id
(`~/.saffron/batches/v0/<SPEC-ID>`), and `EventLog` appends. So a spec driven
twice writes both tasks into one `events.jsonl`, in order, with nothing between
them. `saffron watch SA-0051` opened on the previous task's
`PLAN: rejected, $1.80 spent` while the task being watched had been accepted at
300 lines and was in its repair turn. It is also how an old log reads as a live
one: `--no-follow` shows last week's `READY_FOR_REVIEW` above today's
preflight.

## Problem

An operator diagnosing a spec driven again reads the failure of a task that is
over and draws conclusions about the one that is running. That is worse than a
log that is merely large.

## Out of scope

**One directory per task.** The task directory's name is what `saffron watch
<spec-id>` resolves, what `patch.diff` and `plan.json` sit beside, and what the
batch index links to. Changing it changes four things to fix one. That
`plan.json` is overwritten when a spec is driven again is the same defect and is
left for the same reason.

**How the task boundary renders.** `describe` renders it, in
`saffron/events.py`, which is forbidden here. See the notes.

**`--no-follow` on a task that has not started yet.** It still shows the
previous task, because the new one has written nothing.

## Notes for the agent

**The boundary already exists.** `Ceilings` is the first event `run_task` writes
for every task. It is written before `_resolve_stacked_on` can emit anything,
and `run_task` is the only way to a cell for both `saffron cell` and `saffron
batch`. So the newest task starts at the last `Ceilings` in the log. This needs
no new event kind and no new writer, which is why `saffron/events.py` and
`saffron/task.py` are forbidden.

Two things in item 64 are out of date. First, it says the run id is minted
before the first event is written. It is not: the ledger mints the run and task
ids inside `run_one_cell`, after `Ceilings` and the cell's first `Preflight`
events are already in the log. Second, what it calls two runs are two
**tasks**. A **run** is one repo's slice of a batch (`CONTEXT.md`).

**Events PACKAGE or salvage append after the last `Ceilings` belong to that
task.** That is correct, not a leak.

**`--all` is taken.** It already means "keep the token counter and bare tool
acknowledgements". Pick another name for the whole-log flag, and make it work
alongside `--all` and `--no-follow`.

**The default view starts at the newest task as of when watching begins.** If
the spec is driven again while someone is following it, the new `Ceilings`
renders and following continues. It does not clear what came before.

**Build on `SA-0080`'s offset.** Finding the newest task means reading the whole
log once, on the first poll. After that the offset holds, and no poll re-reads
the file.

**Every fixture is a real `Event` appended through the real `EventLog`**, as
`tests/test_watch.py`'s module docstring requires. `Ceilings` takes all three
`*_source` labels as required fields. The witnesses must fail with the source
reverted, and a test that asserts the newest task alone does: reverted, the
whole file renders.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and `integrity` fails that suppression
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
