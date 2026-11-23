---
id: SA-0424
title: "`EventLog` has no public path, and one `failed` bit stands for a refused write and an event it could not serialize"
type: bug
priority: 3
depends_on: [SA-0423]
estimated_lines: 110
estimate_measured: true
touches:
  - saffron/events.py
  - saffron/task.py
  - saffron/cell/session.py
  - saffron/phases/package.py
  - saffron/cli.py
  - tests/test_events.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_package.py
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
  - hooks/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/ledger.py
  - saffron/batch.py
  - saffron/credentials.py
  - saffron/watch.py
  - tests/test_cli.py
  - tests/test_credentials.py
  - tests/test_watch.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 62
max_attempts: 3
max_turns: 290
acceptance:
  - claim: >-
      `EventLog` gains a `path`, the file `append` writes, and two flags.
      `write_refused` holds once a fault raised while `append` made the
      task directory, opened the file or wrote to it. `unserializable`
      holds once a fault raised before that, while `append` bounded or
      serialized one event, and the next event still lands. `failed` is
      true once either holds, and both can hold together. A raise of a
      kind `append` does not catch still leaves it. The witness reads a
      clean log's `path`, appends one event, and reads it back from that
      file with neither flag set. Five events each fail in a fresh log
      before the write. Three are `Agent` events whose `event` holds a set
      (`TypeError`) or a 5001-digit integer (`ValueError`), which the size
      bound's `json.dumps` meets, or a list nested 1000 deep
      (`RecursionError`), which `asdict` meets. Two are `Agent` events with
      no `event` whose `usage` holds a set or that integer, which only the
      payload's `json.dumps` meets. Each sets `unserializable` and `failed`
      and not `write_refused`, and a later event reads back. Three logs
      fail the write: `events.jsonl` is a directory, the task directory is
      a regular file, and the task directory's name holds a NUL byte. Each
      sets `write_refused` and `failed` and not `unserializable`, and so
      does a fourth whose `Path.open` hands back a file whose `write`
      raises a full disk's `OSError`. One log takes an unserializable
      event, then a refused write, and another log takes a refused write,
      then an unserializable event. Each holds both flags. A test-local
      `Exception` subclass raised from `asdict`, then from `Path.open`,
      leaves `append` each time, and `failed` stays false.
    witness: tests/test_events.py::test_a_log_tells_a_write_it_could_not_make_from_an_event_it_could_not_serialize
    positive_case: >-
      The nine fault cases each see the flags move through the same
      reads, so the test-local subclass's false `failed` is the reading of
      flags that do move. The clean log's event reads back from `path`, so
      the write the flags stay clear for is seen landing.
    wrong_versions:
      - "`path` returns the task directory rather than the file."
      - "The fault is told by its exception type: an `OSError` sets `write_refused`, and any other sets `unserializable`."
      - "The payload is still serialized inside the `write` call after `open`, as at your base, so a `usage` that cannot serialize sets `write_refused`."
      - "The write is marked as begun before the payload's `json.dumps`, so a `usage` that cannot serialize sets `write_refused`."
      - "The write is marked as begun after `mkdir`, so a task directory that is a file sets `unserializable`."
      - "The write is marked as begun after `open`, so a directory at `events.jsonl` sets `unserializable`."
      - "Every fault sets `write_refused`."
      - "Every fault sets `unserializable`."
      - "`failed` reads `write_refused` alone."
      - "`failed` reads `unserializable` alone."
      - "Each fault clears the other flag, so a log that met both holds one."
      - "`append` returns early once `write_refused` holds, so a later unserializable event sets nothing."
      - "A `ValueError` from the write is re-raised, so a NUL byte in the path leaves `append`."
      - "A `ValueError` from before the write is re-raised, so the 5001-digit integer leaves `append`."
      - "A `RecursionError` from before the write is re-raised."
      - "A `TypeError` from before the write is re-raised."
      - "An unserializable event stops every later write."
      - "A fault before the write sets neither flag."
      - "`write` and `flush` move out of the `try`, so a `write` that raises leaves `append`."
      - "`append` catches `Exception`."
      - "`append` catches `Exception` but re-raises one from before the write."
      - "`append` catches `Exception` but re-raises one from the write."
    covers:
      - set: the file `path` names
        members:
          - member: "`events.jsonl` in the task directory, where the event lands"
            driven_by: "`path` returns the task directory rather than the file."
      - set: the statement a fault raises from
        members:
          - member: the size bound's `json.dumps`, or `asdict`
            driven_by: "Every fault sets `write_refused`."
          - member: the payload's `json.dumps`, moved ahead of `mkdir`
            driven_by: "The payload is still serialized inside the `write` call after `open`, as at your base, so a `usage` that cannot serialize sets `write_refused`."
          - member: the payload's `json.dumps`, before the write is marked
            driven_by: "The write is marked as begun before the payload's `json.dumps`, so a `usage` that cannot serialize sets `write_refused`."
          - member: "`mkdir`"
            driven_by: "The write is marked as begun after `mkdir`, so a task directory that is a file sets `unserializable`."
          - member: "`open`"
            driven_by: "The write is marked as begun after `open`, so a directory at `events.jsonl` sets `unserializable`."
          - member: "`write`, on a full disk"
            driven_by: "`write` and `flush` move out of the `try`, so a `write` that raises leaves `append`."
      - set: the kinds a fault before the write raises
        members:
          - member: "`TypeError`"
            driven_by: "A `TypeError` from before the write is re-raised."
          - member: "`ValueError`"
            driven_by: "A `ValueError` from before the write is re-raised, so the 5001-digit integer leaves `append`."
          - member: "`RecursionError`"
            driven_by: "A `RecursionError` from before the write is re-raised."
          - member: any fault before the write, marked at all
            driven_by: "A fault before the write sets neither flag."
      - set: the kinds a fault in the write raises
        members:
          - member: "`OSError`, caught and marked as the write's"
            driven_by: "Every fault sets `unserializable`."
          - member: "`ValueError`, from a NUL byte in the path"
            driven_by: "The fault is told by its exception type: an `OSError` sets `write_refused`, and any other sets `unserializable`."
          - member: "`ValueError` from the write, caught at all"
            driven_by: "A `ValueError` from the write is re-raised, so a NUL byte in the path leaves `append`."
      - set: what holds after a fault
        members:
          - member: "`failed`, after a fault before the write"
            driven_by: "`failed` reads `write_refused` alone."
          - member: "`failed`, after a fault in the write"
            driven_by: "`failed` reads `unserializable` alone."
          - member: the next event landing, after a fault before the write
            driven_by: "An unserializable event stops every later write."
          - member: both flags, unserializable first
            driven_by: "Each fault clears the other flag, so a log that met both holds one."
          - member: both flags, refused first
            driven_by: "`append` returns early once `write_refused` holds, so a later unserializable event sets nothing."
      - set: the upper edge, a kind `append` does not catch
        members:
          - member: raised before the write, from `asdict`
            driven_by: "`append` catches `Exception` but re-raises one from the write."
          - member: raised in the write, from `Path.open`
            driven_by: "`append` catches `Exception` but re-raises one from before the write."
          - member: raised either way
            driven_by: "`append` catches `Exception`."
  - claim: >-
      Handed no `emit`, `run_task` names its log in each warning by the
      `path` of the `EventLog` it built, never by a path it derives from
      `out_dir` and the spec id. A refused write prints `warning: <path>
      refused a write; events may be missing`. An unserializable event
      prints `warning: <path> could not serialize an event and left it
      out`. Each prints once per log, on the line right after the event
      that raised it, the last event the task emits included. The
      serialize warning is not appended, and the refusal's cannot land.
      The witness replaces `saffron.task.EventLog` with a subclass that
      writes one directory below the task's own. In a first task the
      `run_one_cell` double emits a raw `Agent` line `one` whose `event`
      holds a set, a raw line `two` whose `event` holds a 5001-digit
      integer, and a `PhaseStart`. Its `on_cell` reads the log back, puts a
      directory where `events.jsonl` was, and emits one more `PhaseStart`,
      the task's last event. The printed lines run `one`, the serialize
      warning, `two`, the first `PhaseStart`, the last, and the refusal.
      Each warning prints once, and no warning names another path. The
      log read back holds the task's `Ceilings` and the first `PhaseStart`,
      and nothing else. In a second task the double emits a `PhaseStart`,
      then a raw line whose `event` holds a set as the task's last event,
      and the serialize warning prints right after that line. In a third
      task a directory sits at `events.jsonl` before the task starts, so
      its `Ceilings` line is refused and the refusal follows it. The
      double then emits one raw line whose `event` holds a set, and only
      the serialize warning follows that line.
    witness: tests/test_task.py::test_run_tasks_log_warnings_name_its_path_and_say_which_fault
    positive_case: >-
      The log read back holds the `Ceilings` and the `PhaseStart` the task
      emitted, so the read that finds no warning in it sees what was
      appended. Both warnings name the moved path, so the check that no
      warning names another path reads warnings that carry one.
    wrong_versions:
      - "The warning names `out_dir / spec.id / \"events.jsonl\"`, as at your base."
      - "One warning, the refusal's, prints when `failed` first turns true, as at your base."
      - "Each warning prints on every append while its flag holds."
      - "Each warning prints before the line of the event that raised it."
      - "The serialize warning is also appended to the log."
      - "No warning prints at all."
      - "The serialize warning prints when `unserializable` turns true, and the refusal's when `failed` does."
      - "Each warning prints one event late: the flags are read before `append`, and a fault's warning prints ahead of the next event's line."
      - "The refusal prints when `write_refused` turns true, and the serialize warning when `failed` does."
    covers:
      - set: the faults that warn
        members:
          - member: a refused write
            driven_by: "The serialize warning prints when `unserializable` turns true, and the refusal's when `failed` does."
          - member: an unserializable event
            driven_by: "One warning, the refusal's, prints when `failed` first turns true, as at your base."
          - member: an unserializable event after a refused write
            driven_by: "The refusal prints when `write_refused` turns true, and the serialize warning when `failed` does."
          - member: any fault at all
            driven_by: "No warning prints at all."
      - set: the path a warning names
        members:
          - member: "the `EventLog`'s own `path`"
            driven_by: "The warning names `out_dir / spec.id / \"events.jsonl\"`, as at your base."
      - set: how a warning prints
        members:
          - member: once per log
            driven_by: "Each warning prints on every append while its flag holds."
          - member: after the event's own line
            driven_by: "Each warning prints before the line of the event that raised it."
          - member: after the line of the last event the task emits
            driven_by: "Each warning prints one event late: the flags are read before `append`, and a fault's warning prints ahead of the next event's line."
          - member: never appended
            driven_by: "The serialize warning is also appended to the log."
  - claim: >-
      `session._default_emit` prints the same two warnings as `run_task`,
      each naming its log's `path`, once per log, on the line right after
      the event that raised it, the last event a log is handed included.
      It does not append the serialize warning. The witness hands it a
      real `EventLog` and emits a `PhaseStart`, a raw `Agent` line `one`
      whose `event` holds a set, a raw line `two` whose `event` holds a
      5001-digit integer, and a second `PhaseStart`. It reads the log back,
      puts a directory where `events.jsonl` was, and emits two more
      `PhaseStart` events. The printed lines are exactly the six events'
      lines, with the serialize warning after `one` and the refusal after
      the first `PhaseStart` emitted after the directory went in. The log
      read back holds the first two `PhaseStart` events, and nothing else.
      Then a log refusing from its start is handed one `PhaseStart`, and a
      fresh log one raw line whose `event` holds a set. Each prints its one
      line and then its warning.
    witness: tests/test_session.py::test_the_default_emitter_warns_once_for_each_fault_its_log_raised
    positive_case: >-
      The first `PhaseStart` prints with no warning after it, so a clean
      write is seen printing none. The log read back holds both
      `PhaseStart` events written before the refusal, so the read that
      finds no warning in it sees what was appended.
    wrong_versions:
      - "`_default_emit` prints the event's line and no warning, as at your base."
      - "`_default_emit` prints one warning, the refusal's, when `failed` first turns true."
      - "`_default_emit` prints each warning on every append while its flag holds."
      - "`_default_emit` prints each warning before the event's line."
      - "`_default_emit` appends the serialize warning to the log."
      - "`_default_emit` prints the serialize warning when `unserializable` turns true, and the refusal's when `failed` does."
      - "`_default_emit` prints each warning one event late, ahead of the next event's line."
    covers:
      - set: the faults that warn
        members:
          - member: a refused write
            driven_by: "`_default_emit` prints the serialize warning when `unserializable` turns true, and the refusal's when `failed` does."
          - member: an unserializable event
            driven_by: "`_default_emit` prints one warning, the refusal's, when `failed` first turns true."
          - member: any fault at all
            driven_by: "`_default_emit` prints the event's line and no warning, as at your base."
      - set: how a warning prints
        members:
          - member: once per log
            driven_by: "`_default_emit` prints each warning on every append while its flag holds."
          - member: after the event's own line
            driven_by: "`_default_emit` prints each warning before the event's line."
          - member: after the line of the last event a log is handed
            driven_by: "`_default_emit` prints each warning one event late, ahead of the next event's line."
          - member: never appended
            driven_by: "`_default_emit` appends the serialize warning to the log."
  - claim: >-
      Handed no `emit`, `package()` and `push_unpackaged_work()` each print
      the refusal's warning, naming the `path` of the `EventLog` they
      built, once per log, on the line right after the event its refused
      write raised, a log's last line included. A log that takes every
      write prints no warning. The witness replaces
      `saffron.phases.package.EventLog` with a subclass that writes one
      directory below the task's own, and makes `mirror_ops.diff_stat`
      raise, so a push emits two lines. A first `push_unpackaged_work`
      writes both lines and prints them alone. With a directory where
      `events.jsonl` was, a second push prints its first line, the warning
      and its second line. Then `package()` opens a pull request with
      `append_queue_line` raising, so it emits two lines. Into a clean log
      it prints exactly those two lines. With a directory where
      `events.jsonl` was, it prints its first line, the warning and its
      second line. Last, a credential in
      the patch makes `package()` and then `push_unpackaged_work()` each
      emit one refusal line, and each prints that line and then the
      warning.
    witness: tests/test_package.py::test_packages_default_emitters_warn_naming_their_logs_own_path
    positive_case: >-
      The first push's two lines read back from the log, so the clean
      half's missing warning is seen beside a write that landed. The clean
      `package()` call prints both its lines, so its missing warning is
      read from output that holds lines.
    wrong_versions:
      - "`package()`'s default prints no warning, as at your base."
      - "`push_unpackaged_work()`'s default prints no warning, as at your base."
      - "`package()`'s warning names `outcome.task_dir / \"events.jsonl\"`."
      - "`push_unpackaged_work()`'s warning names `outcome.task_dir / \"events.jsonl\"`."
      - "`package()`'s default prints the warning on every append once the write is refused."
      - "`push_unpackaged_work()`'s default prints the warning on every append once the write is refused."
      - "`package()`'s default prints the warning before the event's line."
      - "`push_unpackaged_work()`'s default prints the warning before the event's line."
      - "`package()`'s default prints the warning one event late, ahead of the next event's line."
      - "`push_unpackaged_work()`'s default prints the warning one event late, ahead of the next event's line."
      - "`package()`'s default prints the warning once per log after its first line, refused or not."
      - "`push_unpackaged_work()`'s default prints the warning once per log after its first line, refused or not."
    covers:
      - set: the PACKAGE defaults that build a log
        members:
          - member: "`package()`"
            driven_by: "`package()`'s default prints no warning, as at your base."
          - member: "`push_unpackaged_work()`"
            driven_by: "`push_unpackaged_work()`'s default prints no warning, as at your base."
      - set: a log that takes every write
        members:
          - member: "`package()`, printing no warning"
            driven_by: "`package()`'s default prints the warning once per log after its first line, refused or not."
          - member: "`push_unpackaged_work()`, printing no warning"
            driven_by: "`push_unpackaged_work()`'s default prints the warning once per log after its first line, refused or not."
      - set: the path a warning names
        members:
          - member: "`package()`'s log's own `path`"
            driven_by: "`package()`'s warning names `outcome.task_dir / \"events.jsonl\"`."
          - member: "`push_unpackaged_work()`'s log's own `path`"
            driven_by: "`push_unpackaged_work()`'s warning names `outcome.task_dir / \"events.jsonl\"`."
      - set: how a warning prints
        members:
          - member: once per log, in `package()`
            driven_by: "`package()`'s default prints the warning on every append once the write is refused."
          - member: once per log, in `push_unpackaged_work()`
            driven_by: "`push_unpackaged_work()`'s default prints the warning on every append once the write is refused."
          - member: after the event's own line, in `package()`
            driven_by: "`package()`'s default prints the warning before the event's line."
          - member: after the event's own line, in `push_unpackaged_work()`
            driven_by: "`push_unpackaged_work()`'s default prints the warning before the event's line."
          - member: after a log's last line, in `package()`
            driven_by: "`package()`'s default prints the warning one event late, ahead of the next event's line."
          - member: after a log's last line, in `push_unpackaged_work()`
            driven_by: "`push_unpackaged_work()`'s default prints the warning one event late, ahead of the next event's line."
---

## Context

Backlog item **b-9eceda**, tier 3. It cites `DESIGN.md` §4.1, and the log
is §4.7's. Every line below was read at `b8f4a4f3`. This spec depends on
`SA-0423`, and on `SA-0422` and `SA-0421` before it. `SA-0421` changes
`EventLog.append` to return the event it redacted, and changes the two
emitters below to print that event. So find each cited line by the function
named beside it.

**The path.** `EventLog.__init__` keeps the file in `self._path`
(`saffron/events.py:459`), and nothing exposes it. Handed no `emit`,
`run_task` builds a log, then re-derives the same path under a `ponytail:`
(`saffron/task.py:799-801`). Its warning names that copy
(`saffron/task.py:812`).

**The one bit.** `append` catches four kinds in one clause
(`saffron/events.py:520`) and sets `failed` for each (`:523`). The clause
wraps one `try` (`saffron/events.py:478-519`). In order it redacts, bounds
an oversized `event` with a `json.dumps` (`:502-512`) and calls `asdict`
(`:515`). Then it calls `mkdir` (`:516`) and `open` (`:517`). The
payload's own `json.dumps` runs last, inside the `write` call, after
`open` (`:518`). A fault before the write belongs to one event, and the
next event can still land. A fault in the write belongs to the log, and
the next one meets it too. Measured on the host's CPython 3.14: a set in
an `event` raises `TypeError` and a 5001-digit integer `ValueError`, both
in the size bound's `json.dumps`. A list nested 1000 deep raises
`RecursionError` in `asdict`. Redaction raised for none of them. A
directory at `events.jsonl` makes `open` raise `IsADirectoryError`. Two
more were measured on the host alone, never in the `python:3.12` cell
image. A task directory that is a regular file makes `mkdir` raise
`FileExistsError`, and a NUL byte in its name makes `mkdir` raise
`ValueError`. `run_task`'s warning reads `failed`
alone, so it says "refused a write" for either fault
(`saffron/task.py:809-812`).

**The owners.** Six sites build an `EventLog`.

- `run_task`, handed no `emit` (`saffron/task.py:799`). It reads `failed`.
- `run_one_cell`, handed no `emit` (`saffron/cell/session.py:1164`), hands
  its log to `_default_emit` (`:128-139`). So does `cli.py`'s
  `_spec_session_emit` (`saffron/cli.py:1370-1375`), for every spec
  review, spec writer, end review and follow-up writer.
  `_default_emit` never reads `failed`.
- `package()` and `push_unpackaged_work()`, each handed no `emit`
  (`saffron/phases/package.py:691`, `:1171`). Neither reads `failed`.
  `saffron package` reaches `package_ready_task`, whose
  `package_phase.package` call passes no emitter (`saffron/task.py:1579`).
- `cli.py`'s `_record_events` builds one log per fact the ledger appends
  and drops it after one `append` (`saffron/cli.py:116-125`).

**Two stale comments.** `_default_emit`'s docstring names `cli.py` as a
caller of `run_one_cell` that passes no `emit`
(`saffron/cell/session.py:129-131`). The docstring of `_drive` in
`tests/test_session.py` says it calls `run_one_cell` "exactly as `cli.py`
does" (`tests/test_session.py:1593`). `run_task` is the one caller of
`run_one_cell`, and it passes its `emit` (`saffron/task.py:963-972`). A
third names `cli.py` as forbidden "to this spec" in `run_one_cell`'s
docstring (`saffron/cell/session.py:1151`).

**What `SA-0423` adds that the fourth witness uses.** It makes
`push_unpackaged_work` read the pushed branch's diff stat after the push,
with `mirror_ops.diff_stat`. A failed read goes to `_say`. It also makes
`_finish` hand a raise out of its queue line write to a new `say`
parameter, which `package()` fills with `_emit_package`. Neither exists at
`b8f4a4f3`. There `_finish` guards nothing
(`saffron/phases/package.py:1094-1107`). So each path the witness drives
emits two lines only on `SA-0423`.

**Who sets `failed` today.** Two doubles in `tests/test_task.py` subclass
`EventLog` and set it by hand: `_FailFirst` (`tests/test_task.py:625-639`)
and `_FailAfterTwo` (`:674-689`). `test_events.py` asserts it after an
unserializable event (`tests/test_events.py:840`) and reads it false twice
(`:1054`, `:2894`). `SA-0421`'s
`test_the_default_emitters_line_carries_no_credential` reads it after
`_default_emit` drives a log with a directory at `events.jsonl`. That test
keeps only the printed lines that start with `agent: `, so a warning line
leaves it unchanged.

## Problem

`EventLog` names its file to nobody, `failed` cannot say which fault it
saw, and four of the emitters that build a log never read it. Make these
changes.

1. **`path`.** Add a `path` property returning the file `append`
   writes.
2. **Two flags.** Add `write_refused` and `unserializable`, both false at
   construction. A fault that raises while `append` makes the directory,
   opens the file or writes sets `write_refused`. A fault before that sets
   `unserializable`. Keep `append`'s one `try` and its one existing
   `except` line exactly as your base spells it, the same four kinds in
   the same order. Add no second clause. Tell the two faults apart inside
   the `try`. Serialize the payload into a local before
   `mkdir`, rather than inside the `write` call. Then set a local flag
   right before `mkdir`, and read it in the existing handler. Make
   `failed` a property, true when either flag is. `append` still never
   raises one of the four.
3. **One warning per fault, printed by every emitter that holds a log.**
   After its `append`, an emitter prints the event's line. Then it prints a
   warning for each flag this same append turned true, read before and
   after the call, in this wording:
   `warning: <path> refused a write; events may be missing` and
   `warning: <path> could not serialize an event and left it out`. Each
   names the log's `path`. Neither is appended. Do this in `run_task`'s
   closure, in `_default_emit`, and in `package()`'s and
   `push_unpackaged_work()`'s defaults. One function in
   `saffron/events.py` that all four call is the short route. Drop
   `run_task`'s `log_path` and its `ponytail:`.
4. **The owner that does not read it.** At `_record_events` in
   `saffron/cli.py`, add a comment saying why its log's `failed` goes
   unread: the record holds the fact, and the line only names it for a
   person reading the log.
5. **The stale comments.** Reword `_default_emit`'s docstring so it names
   no `cli.py` caller of `run_one_cell`, and says `cli.py` builds it for
   the spec sessions. Drop "(forbidden to this spec)" and the `cli.py`
   clause from `run_one_cell`'s docstring. In `tests/test_session.py`,
   reword the `use_default_emit` paragraph of `_drive`'s docstring so it
   names no `cli.py` caller.
6. **The doubles that set the old bit.** `_FailFirst` and
   `_FailAfterTwo` set `write_refused` rather than `failed`, since
   `failed` is now read from the flags.

## Out of scope

- **`_record_events` stays silent.** It builds a fresh log per fact, so a
  warning there would print once for every fact on a full disk.
- **PACKAGE's serialize warning.** `package.py` builds no `Agent` event, so
  no event it emits can fail before the write. The fourth claim drives the
  refusal alone.
- **`saffron review` and `saffron draft`.** Their emitters print only, and
  hold no log.
- **No hand edit.** `DESIGN.md` §4.7 says `append` "never raises, and sets
  `failed` instead" (`DESIGN.md:644`). That stays true with `failed` read
  from the two flags. §5.7 says an emitter that holds a log prints an
  `Agent` event's line from the event its log redacted
  (`DESIGN.md:1426-1428`). PACKAGE's emitters keep to it once they print
  what `append` returns.

## Notes for the agent

**Edit or new.** The first claim edits `append`'s existing body. The
second edits `run_task`'s existing `emit` closure, and the third and
fourth edit the existing default emitters. Their new spelling, a property,
two flags and one function the emitters share, is yours. No `find` written
now pins it, so the last three witnesses stand alone, and `witness`
reports `skip` for each.

**What the third witness leaves.** It calls `_default_emit` directly.
`run_one_cell`'s default and `cli.py`'s `_spec_session_emit` each build
one, and no witness here drives either.

**No `retired_first`.** Nothing here adds or widens a refusal.

**Import new names inside test bodies.** `logged_lines`, if you name the
shared function so, does not exist at your base. The witnesses read the
new flags as attributes, so a reverted source fails each test rather than
its collection.

**`tests/test_events.py`.** Build each case from a fresh `EventLog`. For
the regular-file case, write a file at the task directory's path. For the
NUL case, pass a task directory whose name holds `\x00`. For the upper
edge, replace `saffron.events.asdict`, then `pathlib.Path.open`, each
inside `monkeypatch.context()` around one `append`, so nothing else meets
the patch.

**Payloads carry no `type`.** `describe` reads a typed `event` dict and
fails on a set inside it. Give each unserializable `event` no `type` key.
Make it a raw `Agent` event with a `line`, so its printed line is that
`line` and two such events print apart.

**`tests/test_task.py`.** Drive the witness through `_drive` with
`on_cell`, which runs after the double's events and receives its keyword
arguments, `emit` among them. Use `_push` with `_NO_COMMITS`, and
`state="EXHAUSTED"`. Give each `PhaseStart` `phase="PACKAGE"` and
`label="PACKAGE"`, since `label` takes a `LineLabel`.

**`tests/test_session.py`.** Call `session._default_emit` directly with a
real `EventLog` under `tmp_path`.

**`tests/test_package.py`.** Use the `packageable` fixture, with `emit`
left out of `kwargs` and `unpackaged_kwargs`. Set the outcome's state to
`EXHAUSTED` for the pushes, and to `READY_FOR_REVIEW` before `package()`.
Replace `saffron.repos.mirror.diff_stat` for the pushes and restore it
before `package()`. Replace `append_queue_line` on
`package_phase.index_report` for `package()`, so `_finish` hands its
second line to `say`. Restore it before the credential refusals, so each
emits its one line alone. Commit the key as
`test_the_refusal_to_push_is_emitted_and_the_log_never_learns_the_leak`
does, and pass `_no_gh` to `package()`.

**Size.** The prototype sat at `5ce13547` on the diff of `SA-0421`'s
pull request branch, review commit included. `SA-0422`'s and `SA-0423`'s
prototype diffs sat above it. With `size_gate` it measured 438 changed
tokens outside the test paths, and 1451 under them. `estimated_lines` is
438 over four, rounded up. It held all six steps and the four witnesses.
`ty check`, ruff, `prose_limit --tree`, `.saffron/gates/structure` and the
dead gate were clean. Each witness failed with the source reverted. Every
wrong version listed above failed its witness there. The whole suite
passed on that stack, 5466 tests. The four witnesses also passed under the
host's CPython 3.12.14, a macOS build rather than the cell image.
