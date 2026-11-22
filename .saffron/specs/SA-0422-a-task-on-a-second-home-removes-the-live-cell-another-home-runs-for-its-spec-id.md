---
id: SA-0422
title: "A task on a second home removes the live cell another home runs for its spec id"
type: bug
priority: 2
depends_on: [SA-0421]
estimated_lines: 110
estimate_measured: true
touches:
  - saffron/cell_name_lock.py
  - saffron/task.py
  - tests/conftest.py
  - tests/test_cell_name_lock.py
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
  - saffron/home_lock.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/regate.py
  - saffron/qualify.py
  - saffron/end_review.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_home_lock.py
  - tests/test_cli.py
budget_usd: 60
max_attempts: 3
max_turns: 260
acceptance:
  - claim: >-
      `run_task` refuses a task whose spec id another process holds, before
      `run_one_cell` makes any runtime call. It returns `Refused` and prints
      its refused line. The reason names the holder's pid and the batch tree
      the holder's `run_task` was handed. The witness holds `SY-1` from a
      second process, a real `run_task` under home A's batch tree whose cell
      waits. A `run_task` for `SY-1` under home B returns within 30 seconds,
      with the real `run_one_cell` and a spy at `runtime._call`. Its reason
      names the holder's pid and home A's tree, and neither this process's
      pid nor home B's tree. The spy records nothing. Beside the same
      holder, `SY-2` under home B reaches the spy first with
      `rm -f saffron-cell-SY-2`. Once the holder is killed with SIGKILL,
      `SY-1` under home B reaches the spy first with `rm -f saffron-cell-SY-1`.
    witness: tests/test_cell_name_lock.py::test_a_task_whose_spec_id_another_process_holds_is_refused_before_any_runtime_call
    positive_case: >-
      Through the same spy, `SY-2` beside the live holder, and `SY-1` after
      the holder is killed, each record `rm -f` of their own cell's
      container as their first runtime call.
    wrong_versions:
      - "`run_task` takes no lock, as at your base, so home B's task removes home A's live container."
      - "`run_task` removes the cell's container by name before it takes the lock."
      - "The lock sits under the batch tree `run_task` is handed, so each home holds its own."
      - "One lock file serves every spec id, so `SY-2` is refused beside a holder of `SY-1`."
      - "A pid file created with `O_EXCL` stands in for the lock, so a holder killed with SIGKILL refuses every later task."
      - "The contender waits for the lock rather than refusing at once."
      - "The refusal names the contender's own pid and batch tree."
      - "The holder writes its pid alone, so the refusal names no batch tree."
      - "The contender truncates the lock file before it tries the lock, so the refusal reads no holder."
      - "A held lock raises out of `run_task` rather than returning `Refused`."
      - "`run_task` returns `Refused` and prints no refused line."
    covers:
      - set: the spec ids a holder's lock reaches
        members:
          - member: the spec id it holds
            driven_by: tests/test_cell_name_lock.py::test_a_task_whose_spec_id_another_process_holds_is_refused_before_any_runtime_call
          - member: another spec id
            driven_by: "One lock file serves every spec id, so `SY-2` is refused beside a holder of `SY-1`."
      - set: the holder's state
        members:
          - member: alive
            driven_by: "`run_task` takes no lock, as at your base, so home B's task removes home A's live container."
          - member: killed with SIGKILL
            driven_by: "A pid file created with `O_EXCL` stands in for the lock, so a holder killed with SIGKILL refuses every later task."
      - set: what the refusal names
        members:
          - member: the holder's pid
            driven_by: "The refusal names the contender's own pid and batch tree."
          - member: the holder's batch tree
            driven_by: "The holder writes its pid alone, so the refusal names no batch tree."
      - set: where the refusal shows
        members:
          - member: the `Refused` reason
            driven_by: "A held lock raises out of `run_task` rather than returning `Refused`."
          - member: the printed refused line
            driven_by: "`run_task` returns `Refused` and prints no refused line."
  - claim: >-
      `run_task` holds the spec id's lock while `run_one_cell` runs, and
      lets it go once the cell returns or raises. The witness replaces
      `run_one_cell`. Inside it, a second take of `SY-1` in this process is
      refused, naming this process's pid and the batch tree `run_task` was
      handed. After `run_task` returns a `NOT_IMPLEMENTED` outcome, a take
      succeeds. The same holds when the cell raises `RuntimeError`, which
      `run_task` re-raises.
    witness: tests/test_cell_name_lock.py::test_run_task_holds_the_spec_ids_lock_until_its_cell_returns_or_raises
    wrong_versions:
      - "`run_task` takes the lock and lets it go before `run_one_cell` starts."
      - "The lock's handle is kept in a module-level dict and closed only after the cell returns, so a raise leaves it held."
      - "The lock's handle is kept in a module-level dict and never closed."
      - "`run_task` writes the spec id into the lock file in place of its batch tree."
    covers:
      - set: when the lock is read
        members:
          - member: while the cell runs
            driven_by: "`run_task` takes the lock and lets it go before `run_one_cell` starts."
          - member: after the cell returns
            driven_by: "The lock's handle is kept in a module-level dict and never closed."
          - member: after the cell raises
            driven_by: "The lock's handle is kept in a module-level dict and closed only after the cell returns, so a raise leaves it held."
  - claim: >-
      Every home on the host meets at one lock for a spec id, whatever
      `HOME`, `TMPDIR` or the batch tree says. The witness starts a holder
      and a contender in two processes on the module's own default root,
      never a test's. Each process has its own `HOME`, `TMPDIR` and batch
      tree. The contender's `run_task` returns `Refused`, and its cell never
      starts.
    witness: tests/test_cell_name_lock.py::test_the_lock_is_one_file_whatever_home_or_tmpdir_says
    positive_case: >-
      The contender's replaced cell prints a line when it starts, and the
      witness reads that process's output for it.
    wrong_versions:
      - "The default root sits under `Path.home()`."
      - "The default root sits under `tempfile.gettempdir()`."
      - "The lock sits under the batch tree `run_task` is handed."
    covers:
      - set: what could move the lock's root
        members:
          - member: "`HOME`"
            driven_by: "The default root sits under `Path.home()`."
          - member: "`TMPDIR`"
            driven_by: "The default root sits under `tempfile.gettempdir()`."
          - member: the batch tree, so `--home`
            driven_by: "The lock sits under the batch tree `run_task` is handed."
---

## Context

Backlog item **b-d9ed45**, tier 2, status `partial`. It cites `DESIGN.md`
§5.1. Every line below was read at `6f17cbf7`. This spec depends on
`SA-0421`, which edits `saffron/task.py` too. Find each cited line by the
function named beside it.

**One name per spec id.** `_drive_cell` names the cell's container
`saffron-cell-<SPEC>`, and its two volumes `saffron-wt-<SPEC>` and
`saffron-st-<SPEC>` (`saffron/cell/session.py:2370-2372`). Its networks and
proxy carry the spec id too (`:2367-2369`). `critic_cell` names the critic
and Gate-only cells the same way (`saffron/cell/session.py:1581-1591`).
`DESIGN.md` §5.1 says so: "A task's networks and proxy carry its spec id"
(`DESIGN.md:693`).

**Each name is removed before it is created.** `_drive_cell` removes the
container before anything else (`saffron/cell/session.py:2380`).
`cell_up` removes the networks and both volumes before it creates them
(`saffron/cell/session.py:1250-1253`), and `critic_cell` pre-cleans its own
four names (`:1597-1601`). So a leftover from a killed process never blocks
the next task. Nothing tells that leftover from a live cell.

**What `SA-0352` already holds.** `cli._locked_dispatch` takes one lock per
`--home` before `cell`, `batch`, `draft`, `package` or `finish`
(`saffron/cli.py:630-646`, `saffron/home_lock.py:57`). So a second task on
the same home is refused. Two homes hold two locks, though. A task on home
B starts beside home A's live cell for the same spec id. Its pre-clean then
removes that cell's container and volumes. The spec ids of two target repos
collide the same way, since the runtime knows no repo.

**Where a task starts.** `run_task` is the one caller of `run_one_cell`
(`saffron/task.py:963`), for `saffron cell` and `saffron batch` alike.
`run_task` already refuses a task before any cell, printing
`f"{spec.id:<10} refused  {reason}"` (`saffron/task.py:893-894`). `Refused`
is documented at `saffron/task.py:608-618`. `saffron cell` exits 1 on one
(`saffron/cli.py:795-798`). In a plain batch's loop, `_drive`, the
breaker's count stands and the loop goes on (`saffron/batch.py:358-361`).
On a `--stack` night `_is_layer` reads a `Refused` as a miss
(`saffron/batch.py:445-455`).

**What `run_task` does after a cell raises.** `run_task` writes an
`ORPHANED` live row when it wrote one before. For an `Exception` it asks
whether `saffron package` could still take the task
(`saffron/task.py:973-1002`). A refusal before the cell reaches neither.

**The settled scope.** The operator settled these. A live task on another
home can hold a task's container and volume names. That task is refused
before any container or volume is touched, and the refusal names the
holder. A leftover from a dead process is still removed.

## Problem

A task on a second home removes the live cell another home runs for the
same spec id. Make these changes.

1. **A lock per spec id, shared by every home.** Add
   `saffron/cell_name_lock.py`. It takes an exclusive, non-blocking `flock`
   on one file per spec id under a root directory it is handed. A held lock
   raises at once, never waits. The raise names the holder's pid and the
   text the holder wrote. The holder writes its own pid and that text into
   the file after it takes the lock. Open the file without truncating it,
   so a refused contender still reads the holder's line. The kernel drops
   an `flock` when its holder dies, so a SIGKILL frees the spec id.
2. **The default root is fixed per user.** Add a module attribute to
   `saffron/task.py` naming the root: `/tmp/saffron-cell-names-<uid>`, from
   `os.getuid()`. Read neither `HOME`, `TMPDIR` nor the batch tree. The
   runtime's names are per user, so two homes of one user must meet here.
3. **`run_task` holds it around the cell.** Take the lock for `spec.id`
   right before `run_one_cell`, after every refusal `run_task` already
   makes. Hand it `str(out_dir)` as the holder's text. On a held lock,
   print the refused line and return `Refused` with the raise's text as
   its reason. Let the lock go when `run_one_cell` returns or raises,
   before PACKAGE. Add one sentence to `Refused`'s docstring for this case.
4. **Each test takes the lock under its own directory.** Add an autouse
   fixture to `tests/conftest.py`. It points the root attribute at a fresh
   directory from `tmp_path_factory`, with `raising=False`. Otherwise two
   suites on one host refuse each other's `SY-1`. `raising=False` keeps the
   suite collecting with your source reverted.

## Out of scope

Each entry below still removes a spec-keyed name with no lock. This spec
cuts its scope to a task's own cell, and the critic and Gate-only cells
that task starts. So another home's `saffron regate` can still remove a
live task's Gate-only cell.

- **`saffron regate`.** `_apply_criterion_probes` reaches `critic_cell`'s
  Gate-only branch (`saffron/regate.py:285`,
  `saffron/cell/session.py:2295`). It runs outside `run_task`.
- **A stack batch's qualifying step.** `_qualify_range` probes a finding
  (`saffron/qualify.py:235`), and `probe_findings` enters a critic cell for
  it (`saffron/cell/session.py:1984`).
- **The end review's layer cell.** `layer_cell` names
  `saffron-endreview-<SPEC>` and removes it first
  (`saffron/end_review.py:781-788`).
- **`saffron package`'s host probe network**, `saffron-hostprobe-<SPEC>`
  (`saffron/task.py:1550`), and `saffron regate`'s probe network, keyed by
  a task id each home mints for itself (`saffron/regate.py:101`).
- **The batch tree.** The item names one `events.jsonl` for two tasks of a
  spec. Each home has its own batch tree, so two homes never share one.
- **One hand edit, landed in this spec's pull request.** `DESIGN.md` §4.2's
  gate 0 paragraph counts the refusals `run_task` makes after the scan. It
  now says five, and names this one. `DESIGN.md` is forbidden here.

## Notes for the agent

**Edit or new.** Each criterion's code is new: a module, an attribute and
a lock taken in `run_task`. No `find` written now pins its spelling, so no
mutant on the ref pins one. Each witness stands alone, and `witness`
reports `skip` for all three.

**No `retired_first`.** The new refusal reads a lock another process
holds while its cell runs. No queued spec is refused by it.

**`tests/test_cell_name_lock.py`.** Import `saffron.cell_name_lock` only
inside a test body, so a reverted source fails rather than skipping. Copy
the `run_task` call in `tests/test_task.py`'s `_drive`, with `repo_id=1` and a
`Ledger` under each batch tree.

- **The holder.** Start it with `subprocess.Popen` running `python -c`,
  with `cwd` at the repo root. Import a module-level function from the
  test file there. It replaces `run_one_cell` with
  `unittest.mock.patch.object`, since `ty` refuses a plain assignment.
  Its cell prints a marker line and reads stdin. `run_task` prints its
  `ceilings:` line first, so read lines until the marker. Kill it with
  `Popen.kill()`, which sends SIGKILL.
- **The spy.** Patch `runtime._call` to record its argv and raise a
  `KeyboardInterrupt` subclass. `run_task` re-raises that without asking
  `ready_task`. The first call the real `run_one_cell` makes is
  `[runtime.dialect().binary, "rm", "-f", "saffron-cell-<SPEC>"]`, measured.
- **The contender.** Run it in a thread joined with a 30-second timeout,
  then assert the thread finished. Match each pid with a word boundary.
- **The second witness.** Probe in this process. An `flock` on a second
  open of the same file refuses, measured on macOS. Linux's `flock(2)` man
  page says two opens are treated independently there too.
- **The third witness.** Pick a spec id no other suite holds, as
  `SY-<random digits>`, since a spec id must match `^[A-Za-z0-9]+-[0-9]+$`.
  It leaves one lock file under the real root.

**The `prose` gate.** `Refused`'s docstring is ten lines at your base
(`saffron/task.py:609-618`), the gate's limit. Shorten its last two
sentences as you add yours, so it stays within ten.

**Size.** A prototype on `SA-0421`'s diff at `6f17cbf7` measured 441
changed tokens outside the test paths with `size_gate`. `estimated_lines`
is that over four. It held all four steps and the three witnesses, and
`ty check` was clean. Each witness failed with the source reverted. Every
wrong version listed above failed its witness there, the waiting one after
30 seconds. Two `pytest` processes ran `tests/test_task.py` at once, and
both passed. The whole suite passed on the prototype, 5445 tests.

**The arms weighed.** A label on each container naming its home was the
other arm. No runtime call at your base sets or reads a label
(`saffron/cell/runtime.py`), so each dialect would need two new
spellings, measured on each runtime. A test could not drive it without a
runtime, and a dead home's lock says nothing of a live `regate`. The lock
needs no runtime at all.
