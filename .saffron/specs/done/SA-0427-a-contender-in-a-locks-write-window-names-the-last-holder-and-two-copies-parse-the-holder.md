---
id: SA-0427
title: "A contender in a lock's write window names the last holder, and two copies parse the holder's line"
type: bug
priority: 3
estimated_lines: 29
estimate_measured: true
touches:
  - saffron/cell_name_lock.py
  - saffron/home_lock.py
  - tests/test_cell_name_lock.py
  - tests/test_home_lock.py
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
  - saffron/cell/**
  - saffron/gates/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - tests/conftest.py
  - tests/test_cli.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 56
max_attempts: 3
max_turns: 210
acceptance:
  - claim: >-
      One holder parser serves both locks. `cell_name_lock` keeps no copy of
      its own: its `_read_holder` is the very function `home_lock` defines,
      and each lock's refusal reads the holder's line through the
      `_read_holder` its own module binds. The witness asserts the two names
      are one object. It then spies on each module's `_read_holder`, refuses
      a contender on each lock, and sees each spy called once, in order, and
      each refusal name the holder's pid and text.
    witness: tests/test_cell_name_lock.py::test_both_locks_read_their_holder_with_one_parser
    positive_case: >-
      Each refusal names the live holder's pid and text, read through the
      spied parser, so the spy sees a call it records.
    wrong_versions:
      - "`cell_name_lock` restates the parser, so the two modules hold two functions that read the line alike."
      - "`cell_name_lock` binds `home_lock`'s parser but its `lock` parses the holder's line inline."
      - "A new shared module holds the parser, and only `cell_name_lock` imports it while `home_lock` keeps its own copy."
    covers:
      - set: the locks whose refusal reads the holder's line
        members:
          - member: "`cell_name_lock`"
            driven_by: "`cell_name_lock` binds `home_lock`'s parser but its `lock` parses the holder's line inline."
          - member: "`home_lock`"
            driven_by: tests/test_cell_name_lock.py::test_both_locks_read_their_holder_with_one_parser
  - claim: >-
      `cell_name_lock.lock` empties its file when the block it guards ends,
      by return or by raise, and leaves the file in place. So a contender
      refused by a holder that has taken the `flock` and not yet written
      names `unknown` for its pid and text. It never names the last holder
      once that holder's block returned or raised. A
      contender refused while the holder's block runs still names that
      holder's pid and text, and a second such refusal does too. The witness
      takes the lock under a `tmp_path` root three times, with a block that
      returns, one that raises a `RuntimeError` and one that raises a
      `KeyboardInterrupt` subclass. Inside each block two contenders are
      refused, each naming the holder. After each block the file reads
      empty. A raw `flock` of the test's own then holds the file, and a
      contender is refused with no pid and no text, its message
      `SY-1's cell is held by pid unknown's unknown`.
    witness: tests/test_cell_name_lock.py::test_a_contender_in_a_holders_write_window_names_no_stale_holder
    positive_case: >-
      Inside each block both refusals carry the holder's own pid and text, in
      the same `LockHeld` attributes and message the window's refusal leaves
      empty.
    wrong_versions:
      - "Release leaves the file as your base does, holding the last holder's line."
      - "Release empties the file after a block that returns, and not after one that raises."
      - "Release empties the file after a return or an `Exception`, and not after a `KeyboardInterrupt`."
      - "Release unlinks the lock file instead of emptying it."
      - "A refused contender empties the file on its way out, so the live holder's line is gone for the next contender."
    covers:
      - set: how the block a holder guards ends
        members:
          - member: it returns
            driven_by: "Release leaves the file as your base does, holding the last holder's line."
          - member: it raises an `Exception`
            driven_by: "Release empties the file after a block that returns, and not after one that raises."
          - member: it raises a `BaseException` that is no `Exception`
            driven_by: "Release empties the file after a return or an `Exception`, and not after a `KeyboardInterrupt`."
      - set: when a contender is refused
        members:
          - member: in the window between a holder's `flock` and its write
            driven_by: tests/test_cell_name_lock.py::test_a_contender_in_a_holders_write_window_names_no_stale_holder
          - member: while the holder's block runs, the first refusal
            driven_by: tests/test_cell_name_lock.py::test_a_contender_in_a_holders_write_window_names_no_stale_holder
          - member: while the holder's block runs, a second refusal
            driven_by: "A refused contender empties the file on its way out, so the live holder's line is gone for the next contender."
      - set: what release leaves at the lock's path
        members:
          - member: the file, still there and empty
            driven_by: "Release unlinks the lock file instead of emptying it."
  - claim: >-
      `home_lock.lock` empties its file when the block it guards ends, by
      return or by raise, and leaves the file in place. So `cli.main`
      refusing a contender while a holder has taken the `flock` and not yet
      written prints `saffron: held by pid unknown running unknown`. It
      never names the last holder once that holder's block returned or
      raised. A contender refused while the holder's block runs
      still prints that holder's pid and command, and a second such
      refusal does too. The witness drives `cli.main` alone, on a home under
      `tmp_path`. A `saffron cell` holder's command returns, raises a
      `RuntimeError`, or raises a `KeyboardInterrupt` subclass. Inside it
      two `saffron batch` contenders each exit 2, printing one line that
      names the holder. After each holder the home's lock file reads empty.
      A raw `flock` of the test's own then holds the file, and a `saffron
      batch` contender exits 2 printing the `unknown` line, starting no
      work.
    witness: tests/test_home_lock.py::test_a_contender_in_a_holders_write_window_names_no_stale_holder
    positive_case: >-
      Inside each holder both contenders print `saffron: held by pid <pid>
      running saffron cell`, with this process's pid, through the same
      `cli.main` refusal that prints the `unknown` line in the window.
    wrong_versions:
      - "Release leaves the file as your base does, holding the last holder's line."
      - "Release empties the file after a block that returns, and not after one that raises."
      - "Release empties the file after a return or an `Exception`, and not after a `KeyboardInterrupt`."
      - "Release unlinks the lock file instead of emptying it."
      - "A refused contender empties the file on its way out, so the live holder's line is gone for the next contender."
    covers:
      - set: how the block a holder guards ends
        members:
          - member: it returns
            driven_by: "Release leaves the file as your base does, holding the last holder's line."
          - member: it raises an `Exception`
            driven_by: "Release empties the file after a block that returns, and not after one that raises."
          - member: it raises a `BaseException` that is no `Exception`
            driven_by: "Release empties the file after a return or an `Exception`, and not after a `KeyboardInterrupt`."
      - set: when a contender is refused
        members:
          - member: in the window between a holder's `flock` and its write
            driven_by: tests/test_home_lock.py::test_a_contender_in_a_holders_write_window_names_no_stale_holder
          - member: while the holder's block runs, the first refusal
            driven_by: tests/test_home_lock.py::test_a_contender_in_a_holders_write_window_names_no_stale_holder
          - member: while the holder's block runs, a second refusal
            driven_by: "A refused contender empties the file on its way out, so the live holder's line is gone for the next contender."
      - set: what release leaves at the lock's path
        members:
          - member: the file, still there and empty
            driven_by: "Release unlinks the lock file instead of emptying it."
  - claim: >-
      `cell_name_lock.lock` empties its file while it still holds the `flock`,
      before it lets the lock go by an unlock or by its handle's close, on
      return and on raise. So a holder that takes the lock the instant this
      one lets go keeps the line it wrote. The witness takes the lock under a `tmp_path` root three times,
      with a block that returns, one that raises a `RuntimeError` and one that
      raises a `KeyboardInterrupt` subclass. A probe patches `os.fdopen` and
      `fcntl.flock` for that call alone. When the lock's handle unlocks or
      closes, the probe reads the file, then a successor opens it with
      `O_TRUNC`, takes a raw `flock` and writes `4242 next`. The probe knows
      an unlock whether `fcntl.flock` is handed the file object or its
      descriptor number. The witness asserts the probe saw a release, the
      file read empty at that release, and after the block it reads
      `4242 next`.
    witness: tests/test_cell_name_lock.py::test_the_spec_id_lock_empties_its_file_before_it_lets_go
    positive_case: >-
      The probe records a release and its successor's `flock` is granted,
      through the same patched close or unlock whose reading must be empty.
    wrong_versions:
      - "`cell_name_lock` empties its file by path after its handle closes."
      - "`cell_name_lock` unlocks with `LOCK_UN` on its handle, then empties its file, then closes."
      - "`cell_name_lock` unlocks with `LOCK_UN` on its handle's descriptor number, then empties its file, then closes."
      - "`cell_name_lock` empties its file before its close after a block that returns, and not after one that raises."
      - "`cell_name_lock` truncates through its handle for a return or an `Exception`, and by path after its close otherwise."
    covers:
      - set: how cell_name_lock lets the lock go
        members:
          - member: by its handle's close
            driven_by: "`cell_name_lock` empties its file by path after its handle closes."
          - member: by an explicit unlock handed the file object
            driven_by: "`cell_name_lock` unlocks with `LOCK_UN` on its handle, then empties its file, then closes."
          - member: by an explicit unlock handed the descriptor number
            driven_by: "`cell_name_lock` unlocks with `LOCK_UN` on its handle's descriptor number, then empties its file, then closes."
      - set: how the block it guards ends
        members:
          - member: it returns
            driven_by: tests/test_cell_name_lock.py::test_the_spec_id_lock_empties_its_file_before_it_lets_go
          - member: it raises an `Exception`
            driven_by: "`cell_name_lock` empties its file before its close after a block that returns, and not after one that raises."
          - member: it raises a `BaseException` that is no `Exception`
            driven_by: "`cell_name_lock` truncates through its handle for a return or an `Exception`, and by path after its close otherwise."
  - claim: >-
      `home_lock.lock` empties its file while it still holds the `flock`,
      before it lets the lock go by an unlock or by its handle's close, on
      return and on raise. So a holder that takes the lock the instant this
      one lets go keeps the line it wrote. The witness drives `cli.main` for `saffron cell` on a home under `tmp_path` three times,
      with a command that returns, one that raises a `RuntimeError`, so
      `cli.main` exits 2, and one that raises a `KeyboardInterrupt` subclass,
      which `cli.main` lets through. A probe patches `os.fdopen` and
      `fcntl.flock` for that call alone. When the lock's handle unlocks or
      closes, the probe reads the file, then a successor opens it with
      `O_TRUNC`, takes a raw `flock` and writes `4242 next`. The probe knows
      an unlock whether `fcntl.flock` is handed the file object or its
      descriptor number. The witness asserts the probe saw a release, the
      file read empty at that release, and after the block it reads
      `4242 next`.
    witness: tests/test_home_lock.py::test_the_home_lock_empties_its_file_before_it_lets_go
    positive_case: >-
      The probe records a release and its successor's `flock` is granted,
      through the same patched close or unlock whose reading must be empty.
    wrong_versions:
      - "`home_lock` empties its file by path after its handle closes."
      - "`home_lock` unlocks with `LOCK_UN` on its handle, then empties its file, then closes."
      - "`home_lock` unlocks with `LOCK_UN` on its handle's descriptor number, then empties its file, then closes."
      - "`home_lock` empties its file before its close after a block that returns, and not after one that raises."
      - "`home_lock` truncates through its handle for a return or an `Exception`, and by path after its close otherwise."
    covers:
      - set: how home_lock lets the lock go
        members:
          - member: by its handle's close
            driven_by: "`home_lock` empties its file by path after its handle closes."
          - member: by an explicit unlock handed the file object
            driven_by: "`home_lock` unlocks with `LOCK_UN` on its handle, then empties its file, then closes."
          - member: by an explicit unlock handed the descriptor number
            driven_by: "`home_lock` unlocks with `LOCK_UN` on its handle's descriptor number, then empties its file, then closes."
      - set: how the block it guards ends
        members:
          - member: it returns
            driven_by: tests/test_home_lock.py::test_the_home_lock_empties_its_file_before_it_lets_go
          - member: it raises an `Exception`
            driven_by: "`home_lock` empties its file before its close after a block that returns, and not after one that raises."
          - member: it raises a `BaseException` that is no `Exception`
            driven_by: "`home_lock` truncates through its handle for a return or an `Exception`, and by path after its close otherwise."
---

## Context

Backlog item **b-708b05**, tier 3. It cites `DESIGN.md` §5.1, and its
related item is **b-d9ed45**. Finish 103's end review of `SA-0422` found
both halves (#1299). Every line below was read at `9ae03eda`.

**Two copies of one parser.** `saffron/home_lock.py:45-53` defines
`_read_holder(handle)`. It seeks to 0, reads one line, splits it at the
first space, reads the pid with `int`, and returns `(pid, text or None)`.
`saffron/cell_name_lock.py:77-85` restates it line for line, with
`holder_text` where `home_lock` says `command`. Each lock's refusal calls
its own copy (`saffron/cell_name_lock.py:108`, `saffron/home_lock.py:74`).
The item says the two copies drifted once, on `-1` against `unknown`,
before a review commit matched them.

**The write window.** Each `lock` opens its file without `O_TRUNC`, wraps
the descriptor with `os.fdopen`, and enters `with handle`
(`saffron/cell_name_lock.py:102-104`, `saffron/home_lock.py:68-70`). It
takes `flock` with `LOCK_EX | LOCK_NB`. A refused contender reads the line
and raises (`saffron/cell_name_lock.py:105-109`,
`saffron/home_lock.py:71-75`). Once the lock is granted, `lock` seeks to 0,
truncates, writes `<pid> <text>` and flushes, then yields
(`saffron/cell_name_lock.py:110-114`, `saffron/home_lock.py:76-80`).
No statement follows the yield. The file keeps the holder's line once the
handle closes and the kernel drops the `flock`.

So the next holder's `flock` is granted while the file still names the
last one. A contender refused before that holder truncates reads the stale
line. It names a pid that holds nothing. Both exceptions say `None` means
a holder "between its truncate and its write"
(`saffron/cell_name_lock.py:53`, `saffron/home_lock.py:33`). That window
reads empty already. The one before the truncate does not.

**Who holds each lock.** `run_task` holds `cell_name_lock.lock` around
`run_one_cell` and returns `Refused` with the raise's text
(`saffron/task.py:974`, `:1017-1020`). `cli._locked_dispatch` holds
`home_lock.lock` for `cell`, `batch`, `draft`, `package` and `finish`, and
prints `saffron: <the raise's text>` and exits 2 on a refusal
(`saffron/cli.py:630-646`). `cli.main` turns an `Exception` from the
command into exit 2 (`saffron/cli.py:456-463`). `_guarding_sigterm`
re-raises a `KeyboardInterrupt` it did not raise itself
(`saffron/cli.py:666-670`).

**The settled decisions.** The operator settled these. One parser serves
both locks. Each `lock` empties its file while it still holds it, on return
and on raise. A contender in the window then names `unknown`, and one
refused outside it still names the live holder.

## Problem

A contender refused in a holder's write window names the holder before it,
and the holder's line is parsed by two copies of one function. Make these
changes.

1. **One parser.** Delete `cell_name_lock`'s `_read_holder`, and import the
   one in `saffron/home_lock.py` by its own name. Keep its return contract,
   `(int | None, str | None)`. `cell_name_lock`'s refusal keeps calling the
   name its module binds.
2. **Each lock empties its file on release.** Guard the yield in both
   `lock`s, after the holder's line is written. Truncate the file to empty
   however the block ends. That covers a return, an `Exception` and a
   `BaseException` such as `KeyboardInterrupt`. Truncate through the open
   handle, before it closes, while the `flock` is still held. Unlock by
   the close alone, or by an explicit unlock after the truncate. Never
   unlink the file. Never truncate on the refusal path, where the contender holds
   no lock and the line is the live holder's.
3. **Two stale sentences.** Each exception's comment or docstring says
   `None` means a holder between its truncate and its write. Say instead
   that it means a holder "between its flock and its write, or between its
   release truncate and its close". Add to each `lock`'s docstring that
   release empties the file before the lock goes. The `prose` gate holds a
   docstring to ten lines, and `cell_name_lock.lock`'s is at ten already at
   your base. So fold the sentence into an existing line there, or trim
   another, and count the lines of both docstrings after.

## Out of scope

- **A killed holder still leaves its line.** A SIGKILL skips every `finally`, so
  the file keeps the dead holder's line. The next holder's window then
  names that pid, as today. SIGTERM does the same for `draft` and
  `package`, which `cli.main` does not wrap in `_guarding_sigterm`
  (`saffron/cli.py:416`, `:434`). Each claim here is about a holder whose
  block ended by return or raise.
- **The release window reads empty.** A contender refused between the
  release truncate and the close reads an empty line and names `unknown`.
  That is the intended answer for a holder about to let go.
- **The refusal text.** `LockHeld` and `HomeLocked` keep their messages
  and their `unknown` fallback (`saffron/cell_name_lock.py:53-56`,
  `saffron/home_lock.py:38-42`).
- **The callers.** `saffron/task.py` and `saffron/cli.py` stay as they are.

## Notes for the agent

**Edit or new.** Each criterion edits code that exists, so each has a
mutant on `refs/saffron/mutants`. Each mutant pins text your base already
determines and that the change leaves alone.

**Why `home_lock` keeps the parser.** Importing its `_read_holder` into
`cell_name_lock` deletes one copy and adds one import line. A new shared
module adds a file and an import in both. A private import across modules
already stands here (`saffron/commit_review.py:35`). The name stays bound in
`cell_name_lock`, so no `removes` entry is needed.

**No `retired_first`.** The change adds no refusal and widens none.

**The witnesses.** Never take a lock under the host's real
`/tmp/saffron-cell-names-<uid>` or a real home. `tests/conftest.py`'s
autouse fixture points `task.CELL_NAME_LOCK_ROOT` at a fresh directory,
and each witness here takes its own root or home under `tmp_path` too.
`SA-0422`'s review found a witness that deleted live host locks.

- **The window, with no seam.** In one process, a second `os.open` of the
  file takes an `flock` that conflicts with the lock's own.
  `test_run_task_holds_the_spec_ids_lock_until_its_cell_returns_or_raises`
  already relies on this. So after a holder's block ends, the witness opens the
  lock file itself, takes `LOCK_EX | LOCK_NB` on it and writes nothing.
  That descriptor is a holder whose `flock` is granted and whose truncate
  and write have not happened. A contender then goes through the real `lock`.
  Close the raw descriptor in a `finally`.
- **The interrupt.** Raise a `KeyboardInterrupt` subclass, never a bare
  one, and catch it with `try`/`except`. `pytest.raises` lets one stop the
  whole session. `tests/test_cell_name_lock.py` already has `_SpyStop` and
  `_raised` for this.
- **`tests/test_cell_name_lock.py`.** Import `saffron.cell_name_lock` and
  `saffron.home_lock` inside each test body, as the file's docstring asks.
  The parser witness reads `_read_holder` from each module. It spies with
  `monkeypatch.setattr` on each module's name and calls the real function.
- **`tests/test_home_lock.py`.** Never import `saffron.home_lock` there, as
  its docstring says. Drive `cli.main` with `_argv`, and patch
  `cli._run_cell` for the holder. Patch `cli._batch` with a stub that
  appends to a list, and assert the list stays empty. A raise there would
  not fail the test, since `cli.main` turns an `Exception` into exit 2. Read each contender's
  output with `capsys.readouterr()` and compare whole strings. The home is
  a fresh directory under `tmp_path` for each of the three cases, passed as
  `--home`.
- **Before the lock goes.** One probe serves both witnesses. Define it in
  `tests/test_cell_name_lock.py`, and import it into
  `tests/test_home_lock.py` the way that file imports from
  `tests/test_cli.py`. Take the lock once before the probe, so the file
  exists and the probe can tell the lock's own descriptor by `os.fstat`.
  - The probe patches `os.fdopen` and `fcntl.flock` with
    `pytest.MonkeyPatch.context()`. Its `os.fdopen` calls the real one,
    then sets `close` on the lock's handle to a function of the test's own.
    That function calls the real close, then marks the release. Its
    `fcntl.flock` calls the real one, then marks the release on a
    `LOCK_UN` for the lock's descriptor. An `int` argument is the descriptor,
    and any other argument gives it through `fileno()`. The probe compares
    that descriptor with the lock file by `os.fstat`. So an
    unlock handed the file object and one handed its number both count.
  - The first release mark reads the file. Then a successor opens it with
    `O_TRUNC`, takes a raw `flock` with the real `fcntl.flock`, and writes
    `4242 next`. A successor that truncates leaves exactly its own line,
    so the reading after the block passes at your base. The reading at
    release is what fails your base.
  - Assert a release was seen, so a lock that never lets go through the
    probe fails rather than passing blind. Close the successor's
    descriptor in a `finally`.
  - Measured on a prototype, under the host's Python 3.14 and under
    Python 3.12.14 through `uv run --python 3.12`: `with handle` reaches the
    replaced `close` on its exit. Both witnesses pass with the change and
    fail with both lock modules at your base. The `types` gate, which
    checks for Python 3.12 (`pyproject.toml`), passes the plain assignment
    to `close`.
