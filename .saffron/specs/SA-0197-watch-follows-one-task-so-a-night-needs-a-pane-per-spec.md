---
id: SA-0197
title: watch follows one task, so a night of several tasks needs one pane per spec id
type: feature
priority: 3
depends_on: [SA-0152]
touches:
  - saffron/watch.py
  - saffron/cli.py
  - tests/test_watch.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - saffron/events.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/replay.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_events.py
  - tests/test_scheduler.py
budget_usd: 20
max_attempts: 3
max_turns: 150
estimated_lines: 380
acceptance:
  - claim: >-
      `watch.follow_every_task(root, *, verbose=False, interval=1.0,
      sleep=...)` follows every task directory directly under `root` at
      once. It yields only lines appended after it starts. Each line is the
      task directory's name, one space, then what `render_line` returns for
      the event. Within one poll the directories go in name order, and each
      log's lines in file order. A plain file under `root` is passed over.
      The witness starts with three task directories created in the order
      `SY-3`, `SY-1`, `SY-2`. Two of them hold a log of two events, and
      `SY-2` holds no log yet. `root` also holds `index.html` and
      `queue.json`. Before the second poll it appends two events to each
      log and writes the first two into `SY-2`. It asserts the exact list
      of six prefixed lines.
    witness: tests/test_watch.py::test_following_every_task_prints_only_lines_appended_after_it_starts
    wrong_versions:
      - A first poll that reads each log from byte 0, which replays every event already on disk.
      - One offset shared by every log in place of one offset per log.
      - Directories taken in the order the filesystem lists them.
      - The prefix on the first line of each poll alone, or no prefix.
      - A starting offset read from a stat of each child, which raises on `index.html`.
  - claim: >-
      A task directory created after the follower starts joins on the next
      poll, from its first line, without a restart. Its log is then read past
      its own offset, so no line renders twice. The witness creates `SY-9`
      with two events during the first sleep. It appends a third during the
      second sleep and stops after the third poll. It asserts the three
      prefixed lines, each once, in order.
    witness: tests/test_watch.py::test_a_task_directory_created_after_the_start_joins_from_its_first_line
    wrong_versions:
      - The set of directories listed once, at the start, and never again.
      - A directory first seen on a later poll started at its size then, which drops its first two lines.
      - A new directory read from byte 0 on every poll, which repeats its first two lines.
  - claim: >-
      The follower filters each line as `follow` does. By default the token
      counter and the bare tool acknowledgement are dropped and the agent's
      own text is kept. With `verbose=True` all three render. The witness
      appends the three events to a log present at the start and to a
      directory created after it, and drives both values of `verbose`.
    witness: tests/test_watch.py::test_following_every_task_filters_each_line_as_one_task_does
    wrong_versions:
      - A `verbose` accepted and never passed to `render_line`.
      - The filter applied to logs present at the start and not to a directory that joins later.
  - claim: >-
      Starting parses no line a log held before the start. The witness fills
      two logs with three events each, starts the follower, appends one
      event to one log during the first sleep, and stops after the second
      poll. It counts calls to `saffron.events._parse_line` across the whole
      follow and asserts exactly one.
    witness: tests/test_watch.py::test_following_every_task_parses_no_line_written_before_it_started
    wrong_versions:
      - Each starting offset found by a `read_log_since` from byte 0 whose events are discarded.
      - A follower that reads each log with `read_log` and keeps the lines past a count.
  - claim: >-
      `saffron watch` with no spec id follows the batch tree `main` already
      computes, `out_dir`, through `follow_every_task`. It passes `--all` as
      `verbose` and `--interval` as `interval`. It prints each yielded line.
      The witness stubs `cli.follow_every_task` with a function that takes
      `verbose` and `interval` without defaults and yields two lines. It
      runs `--all --interval 0.25` and then no flag. It asserts the root,
      both values of each argument, and the two printed lines.
    witness: tests/test_cli.py::test_watch_with_no_spec_id_follows_the_batch_tree_with_its_flags
    wrong_versions:
      - "`verbose=True` or `interval=1.0` passed whatever the flags say."
      - A root read from `--home` a second time, such as `args.home / "batches"`.
      - The lines yielded and never printed.
  - claim: >-
      `saffron watch` with no spec id exits 1 when `out_dir` is not a
      directory. It prints `watch: no batch tree at <out_dir>` and never
      calls the follower. The witness runs it under a `--home` with no
      `batches` directory, through a stub that records any call.
    witness: tests/test_cli.py::test_watch_with_no_spec_id_exits_one_without_a_batch_tree
    wrong_versions:
      - A missing batch tree left to `main`'s catch-all, which returns 2.
      - The message printed with exit 0.
  - claim: >-
      `saffron watch` with no spec id refuses `--whole-log` and refuses
      `--no-follow`, each at parse time with argparse's usage exit. The last
      line on stderr names the refused flag, and the follower is never
      called. The witness drives each flag alone.
    witness: tests/test_cli.py::test_watch_with_no_spec_id_refuses_the_flags_that_read_one_log
    wrong_versions:
      - One of the two flags refused and the other accepted and ignored.
      - The refusal printed to stdout with exit 1, which the usage exit is not.
  - claim: >-
      `saffron watch <spec id>` still prints the lines its one task's log
      holds, as it does today.
    witness: tests/test_cli.py::test_watch_prints_the_lines_the_follower_yields
    preserves: true
  - claim: >-
      `saffron watch <spec id>` still reads `out_dir / <spec id>`, as it
      does today.
    witness: tests/test_cli.py::test_watch_reads_the_batch_tree_the_cli_already_computes
    preserves: true
---

## Context

Backlog item **b-2d09de**, which cites `DESIGN.md` §6. Items 62 and 64 shaped
`saffron/watch.py` and are done.

`saffron watch` takes one spec id as a required positional
(`saffron/cli.py:155`). `_watch` builds `task_dir = out_dir / args.task`
(`saffron/cli.py:1777`). `out_dir` defaults to `<home>/batches/v0`
(`saffron/cli.py:205`). Every task writes its log to `out_dir / spec.id`
(`saffron/task.py:478`). So that one root holds every task ever run. On
the operator's host on 2026-10-02 it held 169 directories, and 147 of them
held an `events.jsonl`.

`follow` reads one log past a byte offset through `read_log_since`
(`saffron/watch.py:212`). `read_log_since` returns `([], offset)` for a
directory with no `events.jsonl` (`saffron/events.py:591`). `render_line`
applies the noise filter and `verbose` (`saffron/watch.py:96`).

The module docstring says the module renders no night's worth of tasks
(`saffron/watch.py:13`). This spec makes that sentence false.

## Problem

An operator who wants to follow `saffron batch` live must know each spec id
in advance. They open one pane per id and guess which task the night starts
next. The batch index gets a row only when a task ends, so it cannot answer
what is running now.

## Out of scope

**A replay of what the logs already hold.** The follower prints only lines
appended after it starts. `--whole-log` and `--no-follow` read one log's
past, so the form with no spec id refuses them.

**The ledger and `batch_id`.** The follower reads the batch tree alone. It
filters by no batch and names no batch.

**A line caught mid-write at the start.** The starting offset is the log's
size then. The tail of a line half written at that moment parses as nothing
and is dropped. Every line after it renders.

**`saffron/events.py`.** `read_log_since`, `describe` and `_parse_line`
serve this as they stand.

## Notes for the agent

**The command's shape.** Make the spec id positional optional. `saffron watch
SA-0001` then parses exactly as it does today, so every existing watch test
stays as it is. A separate flag would also need a refusal for a flag given
beside a spec id. Pass a spec id and `_watch` calls `follow` as it does today.

**The refusal.** Raise it through the watch subparser's own `error`, the way
`_poll_interval` dies at parse time (`saffron/cli.py:1747`). The usage text
lists both flags at the tree base, measured on 2026-10-02. So criterion 7's
witness reads the last line of stderr, where argparse writes the message.

**Name order.** On the host, directories created as `SY-3`, `SY-1`, `SY-2`
listed as `SY-1`, `SY-3`, `SY-2` (measured 2026-10-02). Criterion 1's order
check kills a follower that keeps the listing order wherever the two differ.
A prototype of the follower passed criteria 1 to 4 on the host. Each wrong
version under them failed at least one, measured the same day.

**The follower.** Add `follow_every_task` to `saffron/watch.py` beside
`follow`. Reuse `read_log_since`, `render_line` and `_sleep_and_continue`.
Write no second parser and no second formatter. Record each directory's
starting offset from the size of its `events.jsonl`, or 0 when it has none.
List the root again on every poll. The prefix is the directory's name, which
`run_task` makes the spec id.

**All new code, so no mutant.** Each non-`preserves` criterion declares a
witness and no mutant, and `witness` reports `skip` for each. Criteria 8 and
9 name tests that pass now.

**Witnesses fail with the source reverted.** Call `watch.follow_every_task`
inside each test body, never through a module-scope import. Stub the CLI's
follower with `monkeypatch.setattr(cli, "follow_every_task", ...)`, which
raises at base. Criterion 6's witness gets usage exit 2 at base, since the
spec id is required there.

**Fixtures.** Every event is a real `Event` appended through the real
`EventLog`, as `tests/test_watch.py`'s module docstring requires. End each
follow with an injected `sleep`, as `test_following_emits_only_events_that_arrived_since_the_last_poll`
does. Criterion 4 counts parses the way
`test_a_poll_parses_only_the_lines_appended_since_the_last` does.

**Rewrite the module docstring in place.** Its second paragraph names
`SA-0053`'s scope, and its claim about a night's worth of tasks becomes
false. Replace that sentence in the paragraph. Add no paragraph after it.
Update `_watch`'s docstring and the help text of the subcommand and its
positional too. New prose takes no em-dash, semicolon, contraction or perfect
tense.

**Commit as each witness passes.** Write any helper as a `def`, not a
`lambda` bound to a name.
