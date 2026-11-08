---
id: SA-0352
title: "A second batch stamps a live task `ORPHANED`, because nothing holds one batch at a time"
type: feature
priority: 2
depends_on: [SA-0339]
estimated_lines: 360
touches:
  - saffron/home_lock.py
  - saffron/cli.py
  - saffron/reconcile.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/draft.py
  - saffron/cell/**
  - saffron/record/**
  - saffron/report/**
  - tests/test_cli.py
  - tests/test_reconcile.py
  - tests/test_sigterm.py
budget_usd: 56
max_attempts: 3
max_turns: 230
risk: standard
acceptance:
  - claim: >-
      `saffron batch`, `saffron cell` and `saffron draft` each refuse to start
      while one of the three runs on the same `--home`. The refused command
      exits 2, and its own work never starts. The witness drives all nine
      pairs of holder and contender. A batch started on another home beside
      each holder still starts its work.
    witness: tests/test_home_lock.py::test_a_batch_cell_or_draft_beside_another_on_one_home_is_refused
    wrong_versions:
      - Only `saffron batch` takes the lock, so a batch beside a running cell starts.
      - "`saffron draft` takes no lock, so a batch beside a running draft starts."
      - A cell takes a shared lock and a batch an exclusive one, so a cell beside a running cell starts.
      - The lock is taken inside `_batch`, after its scan, rather than in `main` before the dispatch.
      - The lock file sits at one fixed path outside the home, so a batch on another home is refused.
      - A refused command exits 1, the code for a task that did not make it.
  - claim: >-
      A batch started beside a live task leaves that task in its in-flight
      state, and stamps nothing `ORPHANED`. The witness drives one live task
      per holder. A running batch holds a task in `REVIEWING`, a running cell
      one in `IMPLEMENTING`, and a running draft one in `QUEUED`. The second
      batch is the real `_batch`, whose scan would stamp each one.
    witness: tests/test_home_lock.py::test_a_batch_beside_a_live_task_leaves_it_in_its_state
    wrong_versions:
      - The second batch scans before it tries the lock, so it stamps the live task and then refuses.
      - The lock is held by a batch and a cell alone, so a draft's `QUEUED` row is stamped.
  - claim: >-
      A refused batch prints one line naming the holder's pid and the command
      it runs, and a holder that died frees the home. The witness drives a
      holder of each kind, `batch`, `cell` and `draft`, in its own process.
      Each holder starts a child process of its own that outlives it. While
      the holder runs, a batch in a third process exits 2 within 30 seconds
      and names that pid and command. After the holder is killed with
      SIGKILL, its child still alive, a batch on that home starts its work.
      Its scan stamps the in-flight row the dead holder left `ORPHANED`.
    witness: tests/test_home_lock.py::test_a_killed_holder_frees_the_home_and_its_row_is_stamped_orphaned
    wrong_versions:
      - The refusal names the contender's own pid rather than the holder's.
      - The refusal names the pid and never the holder's command.
      - The contender waits for the lock rather than refusing at once.
      - A pid file created with `O_EXCL` stands in for the lock, so a killed holder's file refuses every later batch.
      - The lock file's descriptor is inheritable, so the holder's surviving child keeps the lock.
      - A contender opens the lock file with mode `w`, so it truncates the holder's pid and command before its flock is refused.
  - claim: >-
      The lock lasts exactly as long as its holder's command. The witness
      drives each of `saffron batch`, `saffron cell` and `saffron draft` as
      the holder, twice. The first time the command returns, and the second
      time it raises. While each runs, a batch on the same home is refused. After
      each ends, a batch on the same home starts its work.
    witness: tests/test_home_lock.py::test_the_home_is_freed_when_its_holder_returns_or_raises
    wrong_versions:
      - The lock is a raw `os.open` descriptor closed after a normal return alone, so a holder that raised keeps it.
      - The lock file is opened once at import and never closed.
---

## Context

Backlog item **b-a714d2**, tier 2 in `docs/backlog/PRIORITY.md`. It also
meets the second exit of **b-615466**, "a lock holds one batch per ledger, and
a test shows a second refused". Every line cited below was read at
`c8e8f6e6`, SA-0339's packaged head.

**Cited lines move on the cell's base.** `SA-0338` and `SA-0339` edit
`saffron/cli.py`, and this spec depends on them. Find each cited line by the
function or text named beside it.

**What the batch scan assumes.** §4.2.1 says the in-flight states at scan
time mean a corpse. "One batch runs at a time, so nothing is legitimately in
flight when a scan happens" (`DESIGN.md:483`). `_batch` resolves its queue
with `stamp_orphaned=True` (`saffron/cli.py:2318`). `reconcile` then sets
every row in `IN_FLIGHT_STATES` to `ORPHANED` (`saffron/reconcile.py:222-226`).
`IN_FLIGHT_STATES` holds `DRAFT`, `QUEUED` and the six phase states
(`saffron/reconcile.py:53-64`). `ORPHANED` is in `REQUEUE_STATES`
(`saffron/scheduler.py:149-158`). So the second batch can start a second cell
on the live task's spec.

**Nothing holds the premise.** No lock, lease or process check guards it in
`saffron/`. Four commands leave a live row in flight. `saffron cell` and
`saffron batch` reach `run_one_cell`, whose `_drive_cell` creates the row
(`saffron/cell/session.py:1034`, `:2256`). `saffron draft` creates a row
(`saffron/cli.py:1641`), and a new row starts `QUEUED`
(`saffron/ledger.py:823`). It stays there while the writer cell runs, until
`saffron/draft.py` sets an end state, as `_stop` and `_end` do
(`saffron/draft.py:158-171`). v0's `saffron replay` creates one too, then
runs two gate suites (`saffron/replay.py:54-74`).

**Where the three commands start.** `main` opens the home `Ledger` at
`args.home / "ledger.db"` (`saffron/cli.py:394-396`). It then dispatches
`cell` through `_cell_guarding_sigterm`, `batch` through
`_guarding_sigterm(lambda: _batch(...))`, and `draft` to `_draft`
(`saffron/cli.py:398-405`). The `try` around the dispatch prints any
exception and returns 2 (`saffron/cli.py:443-450`). `Ledger.__init__`
creates the home directory before it connects (`saffron/ledger.py:416-417`).

**A lock the tree already uses.** `saffron/report/index.py`'s `_locked` takes
`fcntl.flock` on a sibling lock file (`saffron/report/index.py:355-366`).
`tests/test_report.py:1992-1996` relies on a second `open()` in one process
being refused by a held lock.

**What the lock does, measured.** The host ran Darwin 27 with Python 3.12.
There a second descriptor in the same process got `EWOULDBLOCK` from
`LOCK_EX | LOCK_NB` on a held file. A child process took the lock, started a
grandchild and was killed with SIGKILL. The lock was free at once, the
grandchild still alive. Python opens a descriptor non-inheritable by default.
`tests/test_report.py:1992-1996` already runs the in-process refusal on Linux.
The cross-process release under SIGKILL is not measured on Linux.

**A docstring the change makes false.** `saffron/reconcile.py`'s module
docstring names "a stamping scan that marks a live cell's row `ORPHANED`" as
the gap left (`saffron/reconcile.py:15-20`).

**How tests drive the commands.** `tests/test_sigterm.py:275-341` runs
`cli.main` in a child process from a script that replaces `cli`'s functions
first. `tests/test_sigterm.py:344-405` waits on a marker file and signals that
child. `tests/test_cli.py:3598-3628` holds `_seed_repo`, `_seed_task` and
`_task_state`.
`_fake_batch_resolution` sits at `tests/test_cli.py:6855-6871`.
`tests/test_consumes.py:35` imports from
`tests.test_cli`.

## Problem

A batch started while another batch, a by-hand `saffron cell` or a
`saffron draft` runs on the same home stamps the live task `ORPHANED`. It
can then pick the same spec and start a second cell on it.

Hold one exclusive lock per home:

1. **A new module, `saffron/home_lock.py`.** A context manager takes the home
   directory and the command's name. It opens a lock file beside
   `ledger.db` in that home without truncating it, as
   `os.open(path, os.O_RDWR | os.O_CREAT)` or mode `a+` does, never mode `w`.
   The descriptor stays close-on-exec, so no child the command starts
   inherits the lock. It then takes `fcntl.flock` with `LOCK_EX | LOCK_NB`.
   Only once the lock is taken does it truncate the file and write its own
   pid and the command's name. It holds the lock until the block exits, by
   return or by raise. When the lock is held, it raises an exception carrying the pid
   and command the file names. It never waits.
2. **`main` takes it.** After the home `Ledger` opens, `main` wraps the
   dispatch of `cell`, `batch` and `draft` in that context manager. The
   lock then covers the whole command, SIGTERM teardown included. A refusal
   prints one line naming the holder's pid and command, and `main` returns
   2. It writes nothing to the ledger. No other command takes the lock.
3. **The docstring.** Rewrite the sentence in `saffron/reconcile.py`'s module
   docstring that names the stamping scan as the gap left. Say that the home
   lock `cli.main` takes keeps a batch scan from running beside a live
   `cell`, `batch` or `draft`.

## Out of scope

- A pid or heartbeat column on the task row. The lock covers every case the
  item names, and a holder that died frees it at once.
- `saffron finish`, `package`, `regate`, `review`, `adopt` and `replay`. None
  of them scans with `stamp_orphaned=True`. `replay` leaves a row in flight,
  and a batch beside it still stamps that row. v1 deletes `replay`.
- A second run of one spec removing the first run's container (b-d9ed45). The
  lock refuses a second `saffron cell` on the same home, and a cell on another
  home still shares the cell runtime's names.
- `latest_batch_id` and the stack view's read of it. b-615466's first exit
  stays open.
- `DESIGN.md` §4.2.1's sentence on the premise. It stays true.

## Notes for the agent

**Mutants and new code.** The lock and its use in `main` are new code. So no
criterion declares a mutant, and `witness` reports `skip` for all four.

**Placement.** Take the lock in `main`, around the three dispatches, never
inside `_batch`, `_run_cell` or `_draft`. The witnesses replace those three
functions on `cli` and expect the lock to hold all the same. Name the lock
file `ledger.lock`. Write the pid and command after the lock is taken, then
flush. A contender that reads an empty file names the pid as unknown.

**The witnesses.** One new file, `tests/test_home_lock.py`. Drive every
command through `saffron.cli.main` with `--home` under `tmp_path`. Never
import `saffron.home_lock` in the test file, so the reverted run fails on an
assertion rather than a collection error. Reuse `_seed_repo`, `_seed_task`,
`_task_state` and `_fake_batch_resolution` from `tests.test_cli`.

- Criteria 1, 2 and 4 run in one process. Replace `cli._batch`, `cli._run_cell`
  and `cli._draft` with stubs. The holder's stub calls `cli.main` again for
  the contender and records what it returned. Any other call records that the
  contender's work started. A second `open()` of the lock file in the same
  process is refused, as measured above.
- Criterion 2's contender is the real `_batch`. Its stubs are
  `preflight.check_readiness` and `cli._resolve_queue`. The first returns a
  passing `Readiness`, as `tests/test_sigterm.py:293-296` does. The second
  calls the real `reconcile` on the ledger it gets, the seeded repo's id and
  the `stamp_orphaned` it gets. `cli.run_batch` returns `"DRAINED"`. The
  holder's stub seeds the live row before it starts the contender. Where the
  holder is a batch, its `_batch` stub hands the contender's call to the real
  `_batch`, kept before the replacement.
- Criterion 3 runs each holder from a child script, in the shape of
  `tests/test_sigterm.py:275-341`. Its stub starts a grandchild that sleeps
  300 seconds. Start it with `close_fds=False`, and its stdout and stderr on
  `subprocess.DEVNULL`. Popen's default `close_fds=True` closes an
  inheritable descriptor too, so the inheritable wrong version would pass.
  The stub then writes the grandchild's pid into a marker file and sleeps.
  The test waits for the marker under its own 30 second deadline. Each
  child script's environment drops `SAFFRON_CELL_RUNTIME`, as
  `tests/test_sigterm.py:361` does. The contender is a second child script,
  a batch whose `_batch` stub prints a marker line. Run it with a 30 second
  timeout. Seed the dead holder's row before the holder starts, then run the
  last batch in the test's own process as in criterion 2. Reap the killed
  holder with `wait()`, and check the grandchild is alive with
  `os.kill(pid, 0)`, before that batch starts. Kill the holder and the
  grandchild in a `finally`.
- Criterion 4 runs each holder twice. Its stub runs a contender batch, then
  returns 0 or raises `RuntimeError`. A flag the test sets tells the stub
  it is the holder. Call depth does not, because the batch after a holder
  ends is a first call again.
- In criteria 1 and 4, the holder's stub reads and clears the flag before
  it calls the contender. At revert the contender then records its work
  rather than recursing through `cli.main`.

**What a prototype measured.** A throwaway `home_lock.py` and witnesses for
criteria 3 and 4 ran on the host at `8b93875c`. Both witnesses failed with
`cli.py`'s change reverted.

- Criterion 3 passed on the correct build. With the descriptor made
  inheritable by `os.set_inheritable`, it failed, because the last batch was
  refused and exited 2. With the grandchild on Popen's default
  `close_fds=True`, that wrong version passed.
- A contender that opened the lock file with `O_TRUNC` failed criterion 3.
  Its refusal read the pid as unknown.
- Criterion 4 passed on the correct build. A file-object lock closed only
  after a normal return passed it too, since the object is closed by
  refcount once the raise unwinds. The raw `os.open` form of that wrong
  version failed on the raise case. So that is the wrong version listed.

**Every new test must fail with the source reverted.** At base no lock
exists, so each contender starts its work. Each witness asserts that the
contender beside a live holder did not.
