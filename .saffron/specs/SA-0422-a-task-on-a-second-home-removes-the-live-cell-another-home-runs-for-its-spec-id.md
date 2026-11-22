---
id: SA-0422
title: "A task on a second home removes the live cell another home runs for its spec id"
type: bug
priority: 2
depends_on: [SA-0421]
estimated_lines: 136
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
      pid nor home B's tree. The root then lists one file, `sy-1.lock`.
      `sy-1` under home B is refused too. The spy records nothing. Beside the
      same holder, `SY-2` under home B reaches the spy first with
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
      - "The lock file keeps the spec id's case, so `SY-1` and `sy-1` hold two locks on a case-sensitive file system."
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
          - member: the same spec id lowercased
            driven_by: "The lock file keeps the spec id's case, so `SY-1` and `sy-1` hold two locks on a case-sensitive file system."
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
      lets it go once the cell returns or raises, before PACKAGE. The witness
      replaces `run_one_cell`. Inside it, a second take of `SY-1` in this
      process is refused, naming this process's pid and the batch tree
      `run_task` was handed. After `run_task` returns a `NOT_IMPLEMENTED`
      outcome, a take succeeds. The same holds when the cell raises
      `RuntimeError`, which `run_task` re-raises. A third cell returns
      `READY_FOR_REVIEW`, and `package_phase.package` is replaced with a
      probe. That probe's take succeeds.
    witness: tests/test_cell_name_lock.py::test_run_task_holds_the_spec_ids_lock_until_its_cell_returns_or_raises
    wrong_versions:
      - "`run_task` takes the lock and lets it go before `run_one_cell` starts."
      - "The lock's handle is kept in a module-level dict and closed only after the cell returns, so a raise leaves it held."
      - "The lock's handle is kept in a module-level dict and never closed."
      - "`run_task` holds the lock until it returns, so PACKAGE runs under it."
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
          - member: while PACKAGE runs
            driven_by: "`run_task` holds the lock until it returns, so PACKAGE runs under it."
  - claim: >-
      Every home of one user meets at one lock for a spec id, whatever
      `HOME`, `TMPDIR` or the batch tree says. The witness starts a holder
      and a contender in two processes on the module's own default root,
      never a test's. Each process has its own `HOME`, `TMPDIR` and batch
      tree. The contender's `run_task` returns `Refused`, and its cell never
      starts. Once the holder is reaped, the witness removes its own lock
      file from that root.
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
  - claim: >-
      A lock root that is not this user's own directory raises out of
      `run_task`, before any runtime call, and is never a refusal. So does
      a lock file that is a symlink, and its target keeps its text. A root
      `run_task` creates has mode `0700`. The witness points the root at
      four paths in turn, each with the spy at `runtime._call`. A fresh path,
      under a umask of `0o022` restored in a `finally`, reaches the spy, and
      the root it makes has mode `0700`. A symlink to a directory raises,
      and the directory stays empty. A directory whose owner differs from
      `os.getuid()` raises, with `os.getuid` replaced to return another uid.
      It raises the same way while this process holds `SY-1`'s lock there.
      A symlink in place of `sy-1.lock` raises `OSError`. Only the fresh
      path reaches the spy.
    witness: tests/test_cell_name_lock.py::test_a_lock_root_that_is_unsafe_raises_before_any_runtime_call
    positive_case: >-
      The fresh root reaches the spy with `rm -f saffron-cell-SY-1`, so the
      spy sees a task that gets past the lock.
    wrong_versions:
      - "The root is read with `os.stat`, which follows a symlink to a directory."
      - "The root is never checked to be a directory."
      - "The root's owner is never compared with `os.getuid()`."
      - "The lock file is opened without `O_NOFOLLOW`, so a symlink there is followed and written."
      - "The root is made without a mode, so it takes the umask's `0755`."
      - "`run_task` turns an unsafe root into `Refused`."
      - "The root's owner is checked after the `flock`, so another user's root whose lock is held returns `Refused`."
    covers:
      - set: what is unsafe about the root
        members:
          - member: a symlink to a directory
            driven_by: "The root is read with `os.stat`, which follows a symlink to a directory."
          - member: another user's directory
            driven_by: "The root's owner is never compared with `os.getuid()`."
          - member: another user's directory whose lock is held
            driven_by: "The root's owner is checked after the `flock`, so another user's root whose lock is held returns `Refused`."
          - member: a symlink as the lock file
            driven_by: "The lock file is opened without `O_NOFOLLOW`, so a symlink there is followed and written."
      - set: how an unsafe root ends the task
        members:
          - member: a raise, never `Refused`
            driven_by: "`run_task` turns an unsafe root into `Refused`."
      - set: the root's mode when `run_task` makes it
        members:
          - member: "`0700`"
            driven_by: "The root is made without a mode, so it takes the umask's `0755`."
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
is documented at `saffron/task.py:608-618`. The module docstring lists the
refusals made in this module (`saffron/task.py:16-34`). `run_task`'s own
docstring lists them too (`saffron/task.py:760-769`).

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

1. **A lock per spec id, shared by every home of one user.** Add
   `saffron/cell_name_lock.py`. It takes an exclusive, non-blocking `flock`
   on one file per spec id under a root directory it is handed. Name the
   file from the spec id lowercased, as the networks and proxy are
   (`saffron/cell/session.py:2367-2368`, `saffron/cell/proxy.py:53`). A held
   lock raises at once, never waits. The raise names the holder's pid and
   the text the holder wrote. The holder writes its own pid and that text
   into the file after it takes the lock. Open the file without truncating
   it, so a refused contender still reads the holder's line. The kernel
   drops an `flock` when its holder dies, so a SIGKILL frees the spec id.
2. **The root is this user's own directory.** Make it with mode `0700`.
   Then `lstat` it, and raise when it is not a directory or its owner is
   not `os.getuid()`. Open the lock file with `O_NOFOLLOW`. Each of these
   raises, and none is a refusal: no holder exists to name.
3. **The default root is fixed per user.** Add a module attribute to
   `saffron/task.py` naming the root: `/tmp/saffron-cell-names-<uid>`, from
   `os.getuid()`. Read neither `HOME`, `TMPDIR` nor the batch tree, so
   every home of one user meets at one file.
4. **`run_task` holds it around the cell.** Take the lock for `spec.id`
   right before `run_one_cell`, after every refusal `run_task` already
   makes. Hand it `str(out_dir)` as the holder's text. On a held lock,
   print the refused line and return `Refused` with the raise's text as
   its reason. Let the lock go when `run_one_cell` returns or raises,
   before PACKAGE. Name this refusal in `Refused`'s docstring, the module
   docstring's list and `run_task`'s docstring.
5. **Each test takes the lock under its own directory.** Add an autouse
   fixture to `tests/conftest.py`. It points the root attribute at a fresh
   directory from `tmp_path_factory`, with `raising=False`. Otherwise two
   suites on one host refuse each other's `SY-1`. `raising=False` keeps the
   suite collecting with your source reverted.

## Out of scope

This spec cuts its scope to a task's own cell, and the critic and Gate-only
cells that task starts. Each entry below still removes a name with no
lock, in one direction or the other.

- **A locked task's own probes remove an unlocked cell.** `critic_cell`'s
  Gate-only branch names `saffron-gate-<SPEC>` and pre-cleans it
  (`saffron/cell/session.py:1582`, `:1597-1601`). A task reaches that
  branch through `_gate_cell_suite` (`:1868`) and `_probe_adequacy`
  (`:2063`). `_drive_cell` reaches it twice more, through its criterion
  probes (`:3598`) and its rebuttal's probes (`:3811`). So a locked task
  can remove the Gate-only cell of another home's `regate` or qualifying
  step.
- **`saffron regate` removes a locked task's cell.** `_apply_criterion_probes`
  reaches the same Gate-only branch outside `run_task`
  (`saffron/regate.py:285`, `saffron/cell/session.py:2295`).
- **A stack batch's qualifying step does the same.** `_qualify_range`
  probes a finding (`saffron/qualify.py:235`), and `probe_findings` enters
  `critic_cell` with `network=None`, the Gate-only branch
  (`saffron/cell/session.py:1984-1988`).
- **The end review's layer cell.** `layer_cell` names
  `saffron-endreview-<SPEC>` and removes it first
  (`saffron/end_review.py:781-788`).
- **Two probe networks.** `saffron package`'s host probe network is
  `saffron-hostprobe-<SPEC>` (`saffron/task.py:1550`). `saffron regate`'s
  probe network is keyed by task id, which each home mints for itself, so
  two homes can share one (`saffron/regate.py:101`).
- **What a refusal costs, in a rare two-home case.** `saffron cell` exits
  1 on `Refused` (`saffron/cli.py:795-798`). A plain batch marks the spec
  started before its runner (`saffron/batch.py:312`), and keeps it so on a
  `Refused` (`:358-361`). So it never offers the spec again that night. A
  `--stack` night runs its spec review first (`saffron/batch.py:773`), then
  the runner (`:957`). It records the `Refused` as a miss (`:975-979`).
- **The batch tree.** The item names one `events.jsonl` for two tasks of a
  spec. Each home has its own batch tree, so two homes never share one.
- **Two users on one host.** Each user has a root of their own. Whether
  their runtimes share container names is not measured here.
- **One hand edit, landed in this spec's pull request.** `DESIGN.md` §4.2's
  gate 0 paragraph counts the refusals `run_task` makes after the scan. It
  now says five, and names this one. `DESIGN.md` is forbidden here.

## Notes for the agent

**Edit or new.** Each criterion's code is new: a module, an attribute and
a lock taken in `run_task`. No `find` written now pins its spelling, so no
mutant on the ref pins one. Each witness stands alone, and `witness`
reports `skip` for all four.

**No `retired_first`.** The new refusal reads a lock another process
holds while its cell runs. No queued spec is refused by it.

**`tests/test_cell_name_lock.py`.** Import `saffron.cell_name_lock` only
inside a test body, so a reverted source fails rather than skipping. Copy
the `run_task` call in `tests/test_task.py`'s `_drive`, with `repo_id=1`
and a `Ledger` under each batch tree.

- **The holder.** Start it with `subprocess.Popen` running `python -c`,
  with `cwd` at the repo root. Import a module-level function from the
  test file there. It replaces `run_one_cell` with
  `unittest.mock.patch.object`, since `ty` refuses a plain assignment.
  Its cell prints a marker line with its lock root, then reads stdin.
  `run_task` prints its `ceilings:` line first, so read lines until the
  marker. Kill it with `Popen.kill()`, which sends SIGKILL.
- **The spy.** Patch `runtime._call` to record its argv and raise a
  `KeyboardInterrupt` subclass. `run_task` re-raises that without asking
  `ready_task`. The first call the real `run_one_cell` makes is
  `[runtime.dialect().binary, "rm", "-f", "saffron-cell-<SPEC>"]`, measured.
  Where a raise of another kind is expected, catch `BaseException` and
  assert its type. Otherwise a version that reaches the spy stops the
  whole session rather than failing the test.
- **The contender.** Run it in a thread joined with a 30-second timeout,
  then assert the thread finished. Match each pid with a word boundary.
- **The lowercased name.** List the root's entries by name. On a
  case-insensitive file system `sy-1.lock` and `SY-1.lock` open one file,
  so only the listing tells the two spellings apart. Measured on macOS.
- **The second witness.** Probe in this process. Replace
  `package_phase.package` with a probe returning an object with `state`
  and `pr_url`.
- **The third witness.** Pick a spec id no other suite holds, as
  `SY-<random digits>`, since a spec id must match `^[A-Za-z0-9]+-[0-9]+$`.
  Read the real root from the holder's marker line. Unlink that one file
  in a `finally`, once the holder is reaped.
- **The fourth witness.** Replace `os.getuid` with `monkeypatch` for the
  owner cases alone. No test can make a directory another user owns. Take
  the held lock with the real uid, then replace it, and unlink that lock
  file before the symlink case. One version survives every witness, and
  it stays off the list: an `lstat` of the lock file, then a plain open.
  It is racy, since the symlink can land between the two calls, and no
  test drives that race. `O_NOFOLLOW` is the one open that cannot race.

**Linux `flock` is not measured.** Every witness ran on macOS. Two
properties carry the lock on Linux, and both are read from `flock(2)`, not
measured. A lock belongs to an open file description, so a second
`open(2)` of one file in one process conflicts with the first. A lock is
dropped when every descriptor of its description closes, so a killed
holder frees it.

**The `prose` gate.** `Refused`'s docstring is ten lines at your base
(`saffron/task.py:609-618`), the gate's limit, and so is `run_task`'s
(`saffron/task.py:760-769`). Shorten each as you add this refusal, so
each stays within ten lines.

**Size.** A prototype on `SA-0421`'s diff at `6f17cbf7` measured 545
changed tokens outside the test paths with `size_gate`. `estimated_lines`
is that over four. It held all five steps and the four witnesses, and
`ty check`, ruff, `.saffron/gates/dead` and `.saffron/gates/structure`
were clean. Each witness failed with the source reverted. Every wrong
version listed above failed its witness there, the waiting one after 30
seconds. Two `pytest` processes ran `tests/test_task.py` at once, and both
passed.

**The arms weighed.** A label on each container naming its home was the
other arm. No runtime call at your base sets or reads a label
(`saffron/cell/runtime.py`), so each dialect would need two new
spellings, measured on each runtime. A test could not drive it without a
runtime, and a dead home's lock says nothing of a live `regate`. The lock
needs no runtime at all.
