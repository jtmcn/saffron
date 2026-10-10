---
id: SA-0245
title: A cell stopped with SIGTERM leaves its containers and its task in flight
type: bug
priority: 2
depends_on: []
estimated_lines: 194
estimate_measured: true
touches:
  - saffron/cli.py
  - tests/test_sigterm.py
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
  - saffron/cell/**
  - saffron/gates/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - tests/conftest.py
  - tests/test_cli.py
  - tests/test_session.py
  - tests/test_batch.py
budget_usd: 26
max_attempts: 3
max_turns: 140
risk: standard
acceptance:
  - claim: >-
      `saffron cell` sent a real SIGTERM mid-IMPLEMENT, and again mid-REVIEW,
      returns 143 from `main`. Each time the signal raises
      `KeyboardInterrupt` itself, not a subclass. Its run reads `ABORTED`, its task reads
      `ORPHANED`, and its patch is exported to the task directory. No agent
      turn starts after the signal. The teardown that follows removes the
      critic cell's container and two volumes when REVIEW was running. It
      then removes the cell's own container, both its networks and both its
      volumes, and stops the proxy. A `KeyboardInterrupt` with no SIGTERM
      behind it still propagates out of `main`. In all three runs, the
      SIGTERM handler in place once `main` returns or raises is the one
      installed when `main` was called, and that handler heard nothing.
      While `main` runs `batch`, the SIGTERM handler is still the one in
      place when `main` was called.
    witness: tests/test_sigterm.py::test_a_cell_sent_sigterm_tears_down_and_closes_its_task
    wrong_versions:
      - The handler raises an `Exception` subclass, which `main`'s catch-all turns into exit 2.
      - The handler only records the signal and returns, so the cell runs on to its end.
      - The handler raises `SystemExit(143)`, which escapes `main` rather than returning 143.
      - The handler raises a subclass of `KeyboardInterrupt`, which `main` still turns into 143.
      - '`main` returns 143 for every `KeyboardInterrupt`, so a Ctrl-C with no SIGTERM reads as one.'
      - '`main` returns 130, the status Python gives an unhandled Ctrl-C.'
      - The handler raises, but `main` re-raises the `KeyboardInterrupt` rather than returning 143.
      - The handler is installed and never put back, so the disposition after `main` is still its own.
      - The disposition is put back to SIGTERM's default rather than to the handler `main` found.
      - The handler calls the handler `main` found before it raises.
      - The mark that a SIGTERM arrived outlives the call, so a later bare `KeyboardInterrupt` in the same process returns 143.
      - The handler is installed around `batch` too.
  - claim: >-
      A second SIGTERM, sent mid-IMPLEMENT while the first one's teardown
      removes the cell's own container, cuts nothing short. Every removal
      the first claim names for that phase still runs in the same order,
      `main` returns 143, and the handler `main` found hears neither signal.
    witness: tests/test_sigterm.py::test_a_second_sigterm_does_not_cut_the_teardown_short
    wrong_versions:
      - The handler stays installed after its first delivery and raises again, so the networks and volumes are left.
      - The first delivery puts back the handler `main` found, so the second signal reaches it, which in production is the default and ends the process.
      - The first delivery sets SIGTERM to its default rather than to ignored, so a second signal ends the process mid-teardown.
  - claim: >-
      A `saffron cell` that SIGTERM never reaches keeps its exit codes. A
      reviewable task exits 0, a task that did not make it exits 1, an
      infrastructure state exits 2, and a driver crash exits 2.
    witness: tests/test_cli.py::test_the_exit_code_distinguishes_the_terminal_states
    preserves: true
---

## Context

Backlog item **b-5df2a7**, placed in tier 2 on 2026-10-06. It cites
`DESIGN.md` §4.5. Every line number below was read at `3983d5a5`.

**What happened.** The operator stopped `SA-0218`'s first cell mid-REVIEW
with SIGTERM. The process exited 143 and printed no teardown line. Three
containers kept running until they were removed by hand. Task 232 stayed
`REVIEWING`, its run was never closed, and its patch was never exported.
§4.5 says `ORPHANED` "is stamped when the cell dies" and that the
supervisor sets it "on kill" (`DESIGN.md:557`).

**This spec is the first of two.** Run 32's cell ran an earlier version
of it. That version also carried `saffron batch`, a witness that started
a real process, and four prose edits. It measured 2087 changed tokens
against the `bug` ceiling of 1300 and ended `EXHAUSTED`. This version
keeps `saffron cell` and its in-process witnesses. `SA-0258` follows it
with `saffron batch`, the process witness and the prose.

**The cleanup that exists.** `run_one_cell` catches `BaseException`,
closes the run `ABORTED`, stamps the task `ORPHANED` and re-raises
(`saffron/cell/session.py:3301-3308`). Its `finally` exports the patch
and calls `cell_down` (`saffron/cell/session.py:3309-3346`). `cell_down`
removes the cell's container, stops the proxy, then removes both
networks and both volumes (`saffron/cell/session.py:1136-1182`). A
critic cell's own `finally` removes its container and its two volumes
(`saffron/cell/session.py:1434-1439`). `run_task` catches
`BaseException` and re-raises (`saffron/task.py:611`).

**Why SIGTERM skips it.** Ctrl-C raises `KeyboardInterrupt`, so all of
the above runs. SIGTERM's default action ends the process without
raising, so none of it does. The only `import signal` under `saffron/`
is `saffron/gates/runner.py:12`, and nothing installs a handler.

**What each exception reaches.** `main` catches `Exception` around every
command and returns 2 (`saffron/cli.py:302-309`). Its `finally` closes
the ledger (`saffron/cli.py:310-311`). So a `KeyboardInterrupt` or a
`SystemExit` passes that catch and reaches the `finally`.

**Why `KeyboardInterrupt`, that exact class.** An agent turn runs in
`exec_stream`, inside `with proc:` (`saffron/cell/runtime.py:550`).
`Popen.__exit__` first closes the child's pipes. Then, when the
exception's class `==` `KeyboardInterrupt`, it waits at most 0.25
seconds for the child. It waits not at all if an interrupted `wait` or
`communicate` already spent that time. For any other class, a subclass
included, it calls `wait()` and blocks until the child exits. Read in
CPython 3.12.14 and 3.14.7 on this host, 2026-10-10. No witness in this
spec observes that wait. Criterion 1 observes the class the signal
raises, and `SA-0258`'s process witness observes the wait.

**What the shell sees.** The console script is `saffron.cli:main`
(`pyproject.toml:21`). An unhandled `KeyboardInterrupt` ends Python by
SIGINT, which reads as 130. A SIGTERM today reads as 143, the shell's
128 plus 15. So `main` keeps that number, now returned after the
teardown.

## Problem

SIGTERM to `saffron cell` must unwind the way Ctrl-C does, so the
cleanup above runs. Make these changes in `saffron/cli.py`.

1. **The handler.** While `main` runs the `cell` command, SIGTERM raises
   `KeyboardInterrupt`, that exact class. Install it around that command,
   and put back the handler `main` found when the command returns or
   raises. Leave `batch` as it is: `SA-0258` wraps it.
2. **A second SIGTERM.** On its first delivery the handler sets SIGTERM
   to be ignored, so a second signal during teardown does nothing. The
   handler `main` found comes back once the command unwinds.
3. **The exit code.** A `KeyboardInterrupt` that unwinds out of the
   command because of SIGTERM makes `main` return 143. One raised with no
   SIGTERM behind it still propagates out of `main`, as today. The mark
   that tells the two apart lives for one call of the command.
4. **The comment above `CELL_EXIT`** (`saffron/cli.py:72-80`) names the
   exit codes. Replace it with the two lines in the notes, which add 143.

## Out of scope

- **`saffron batch`, the process witness and the prose.** `SA-0258`
  takes all three. Until it lands, `CLAUDE.md:91-92` and
  `README.md:146-150` list no 143, and `CLAUDE.md:74-76` still says
  SIGTERM discards a batch's log.
- **A SIGTERM during a silent turn.** Measured on macOS, 2026-10-10, with
  `exec_stream`'s shape: a reader thread blocked on the child's stdout
  and the main thread in `lines.get`. The handler ran 0.51 seconds after
  the signal. Then `Popen.__exit__` closed stdout under the blocked
  reader, and that close waited until the child exited 30 seconds later.
  So a cell stopped while its agent prints nothing unwinds once the agent
  next writes or exits. This spec changes nothing there. Backlog
  `item b-52e670` holds it.
- **SIGKILL.** Nothing can catch it. The next cell of the same spec
  pre-cleans what one leaves (`saffron/cell/session.py:1399-1404`,
  `:1906-1909`).
- **PACKAGE and the Gate-only cell.** A SIGTERM during either unwinds as
  a Ctrl-C there does today. No witness sends the signal while they run.
- **Auto-clean on abort.** §4.3 says a failed or aborted task keeps its
  exported patch, not its volume (`DESIGN.md:506`). It says every exit
  from `run_one_cell` writes `patch.diff`, then removes the container and
  both volumes. It also says a SIGTERM takes that path from this spec on.
  The Ctrl-C path at base already does so
  (`saffron/cell/session.py:3330-3346`). This spec routes SIGTERM into it
  and changes nothing in it.
- **The ignored disposition.** Teardown's child processes inherit the
  ignored SIGTERM. Each is a short runtime call.

## Notes for the agent

**Your base.** `SA-0229` and `SA-0218` both edited `saffron/cli.py`, and
both are merged at `6b033c04`. Read `main` at your base before you edit
it.

**Edit or new.** The handler and the 143 return are new code, so
criteria 1 and 2 declare a witness and no mutant. Criterion 3 names a
test that exists at your base and must stay green.

**One helper for every run.** Put one helper in `tests/test_sigterm.py`
that runs `cli.main` in-process with a `cell` argv. Call it for every run
both criteria make. It does these things in order.

1. Call `monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-test")`. No
   conftest sets it, and `_run_cell` raises without it
   (`saffron/cli.py:453-461`). The autouse fixture that sets it lives in
   `tests/test_cli.py:56-59` and reaches no other module. Stub `ensure_mirror`, `real_remote` and
   `fetch_default_branch` as
   `test_the_exit_code_distinguishes_the_terminal_states` does
   (`tests/test_cli.py:124-131`).
2. Call `_stub_the_runtime` from `tests/test_session.py`, and let the
   caller wrap a runtime call after it. Replace `task.run_one_cell` with a
   function that runs `_drive` over that stub and returns its outcome.
   Give each run its own directory under `tmp_path`, and create it.
3. Install a handler that only appends the signal number to a list. This
   is the handler `main` finds. It keeps a build with no handler of its
   own from ending pytest.
4. Call `cli.main` inside `try` with `except BaseException`, and keep
   what it returned or raised as the result. A leaked exception then fails
   one test, not the session.
5. In the `finally`, read `signal.getsignal(signal.SIGTERM)` first. Only
   then put back the handler from before step 3. The witness compares
   that reading to step 3's handler with `==`, which for a function is
identity. Read after the restore,
   it would hide a `main` that never put its own handler back. Run 32's
   cell did exactly that, and the wrong version survived.

Each criterion asserts on the result, the reading and the list.

**Sending the signal.** Feed `_drive` a generator of turns: the plan
turn, the implement turn and a clean lens turn. Before the turn at the
chosen index, it sends SIGTERM to this process with `os.kill`. The
handler raises at once, from inside the generator. Wrap that `os.kill`
in `try` with `except BaseException`, record the exception's class in a
list, and re-raise. Each signalled run asserts the list is exactly
`[KeyboardInterrupt]`, compared as classes. `result == 143` alone passes
a subclass, since `except KeyboardInterrupt` catches it too. The agent stub inside `_drive` (`tests/test_session.py:1350`) works that
way. It records the turn (`tests/test_session.py:1431`) before it asks
the generator for the next step (`tests/test_session.py:1445`). So index 1 lands mid-IMPLEMENT
with two turns recorded, and index 2 lands on REVIEW's first lens turn
with three. Assert the slice of the stub's `order` list after the last
`turn:` entry. Mid-REVIEW it holds the three critic removals, then
`cell_down`'s five. Assert the proxy's `stop` entry in the stub's
`preflight` list, and `patch.diff` under `_drive`'s out directory. Read
the run and task states from `_drive`'s own ledger. Run the bare
`KeyboardInterrupt` last, after both signalled runs, by scripting it as
the first turn. It must come back as the result, of type
`KeyboardInterrupt`.

**The `batch` run.** Last, replace `cli._batch` with a function that
records `signal.getsignal(signal.SIGTERM)` and returns 0. Call
`cli.main` with a `batch` argv, and assert the recorded handler equals
the one in place before the call. `SA-0258` wraps `batch` and flips this
assertion in its own change.

**Criterion 2.** Wrap `runtime.remove_container` after
`_stub_the_runtime`. On its first call for `saffron-cell-SY-1` after the
first signal, fail the test if `signal.getsignal(signal.SIGTERM)` is
`signal.SIG_DFL`. Only then send the second SIGTERM, so a build that set
the default cannot end pytest itself. The pre-clean also removes that
container before any turn (`saffron/cell/session.py:1909`). So key the
wrapper on a flag the generator sets as it sends the first signal. A
no-op Python handler in place of `SIG_IGN` is equivalent in-process, and
no witness tells the two apart.

**Witnesses red at base.** At base the record-only handler hears the
signal and the cell runs on. So each run returns 2, and the list holds
15. The witness module imports nothing the change adds, so `revert`
collects it with the source reverted.

**The comment above `CELL_EXIT`** becomes these two lines.

```text
# Exit codes (§3.3): 0 reviewable, 1 the task did not make it, 2 infrastructure,
# 143 SIGTERM. A crash or setup failure takes 2 from `main`'s handler, never 1.
```

Measured: any edit that keeps the block at eight lines changes the
identity of its existing `comment-block` hit, and the `prose` hook counts
a new hit.

**Measured on a prototype, 2026-10-10.** Both witnesses were written
against `6b033c04` with this change. They passed under CPython 3.12.14
and 3.14.7 on macOS, and under 3.12.14 on Linux aarch64 in the
`saffron/cell` image. Both fail with `saffron/cli.py` reverted. Each of the
fifteen wrong versions above was applied as one edit and failed its own
criterion's witness on an assertion, under both versions.
`tests/test_cli.py` passed whole, and `ruff`, `ty`, `dead`, `structure`
and `prose` passed on both files. By `size_gate`, the change counted 776
changed tokens: 215 in `saffron/cli.py` and 561 in the test.

**The `prose` gate** reads every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines. A comment
on the handler names the `Popen.__exit__` reason in one or two lines.

**Size.** The `bug` ceiling is 1300 changed tokens. Nothing here is in
`elevate_on`, so `size` reports and does not block. Keep the helper
shared, and keep docstrings short: the test file is most of the count.
