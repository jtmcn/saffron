---
id: SA-0245
title: A cell stopped with SIGTERM leaves its containers and its task in flight
type: bug
priority: 2
depends_on: [SA-0229, SA-0218]
estimated_lines: 242
estimate_measured: true
touches:
  - saffron/cli.py
  - tests/test_sigterm.py
  - CLAUDE.md
  - README.md
  - docs/HOST-HARDENING.md
  - docs/host/dev.saffron.batch.plist
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/adr/**
  - docs/appendices/**
  - docs/backlog/**
  - docs/evidence/**
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
budget_usd: 23
max_attempts: 3
max_turns: 130
risk: standard
acceptance:
  - claim: >-
      `saffron cell` sent a real SIGTERM mid-IMPLEMENT, and again mid-REVIEW,
      exits 143. Its run reads `ABORTED`, its task reads `ORPHANED`, and its
      patch is exported to the task directory. No agent turn starts after
      the signal. The teardown that follows removes the critic cell's
      container and two volumes when REVIEW was running. It then removes the
      cell's own container, both its networks and both its volumes, and
      stops the proxy. After `main` returns, the SIGTERM handler is the one
      `main` found, and that handler heard nothing. A `KeyboardInterrupt`
      with no SIGTERM behind it still propagates out of `main`.
    witness: tests/test_sigterm.py::test_a_cell_sent_sigterm_tears_down_and_closes_its_task
    wrong_versions:
      - The handler raises an `Exception` subclass, which `main`'s catch-all turns into exit 2.
      - The handler only records the signal and returns, so the cell runs on to its end.
      - The handler raises `SystemExit(143)`, which escapes `main` rather than returning 143.
      - '`main` returns 143 for every `KeyboardInterrupt`, so a Ctrl-C with no SIGTERM reads as one.'
      - '`main` returns 130, the status Python gives an unhandled Ctrl-C.'
      - The handler raises, but `main` re-raises the `KeyboardInterrupt` rather than returning 143.
      - The handler is installed for `batch` only.
      - The handler is installed and never put back, so the disposition after `main` is still its own.
  - claim: >-
      A second SIGTERM, sent while the first one's teardown removes the
      cell's own container, cuts nothing short. Every removal the first
      claim names still runs in the same order, `main` exits 143, and the
      handler `main` found hears neither signal.
    witness: tests/test_sigterm.py::test_a_second_sigterm_does_not_cut_the_teardown_short
    wrong_versions:
      - The handler stays installed after its first delivery and raises again, so the networks and volumes are left.
      - The first delivery puts back the handler `main` found, so the second signal reaches it, which in production is the default and ends the process.
  - claim: >-
      A `saffron cell` process and a `saffron batch` process, each with stdout
      piped and a child process of its own still running, are sent SIGTERM
      from outside. Each exits 143 within ten seconds, and its stdout still
      holds the line it printed before the signal. The batch starts no
      second task, and its batch row closes with an `ended_at` and the stop
      reason `INFRASTRUCTURE`.
    witness: tests/test_sigterm.py::test_a_process_sent_sigterm_exits_143_with_its_log_flushed
    wrong_versions:
      - The handler raises `SystemExit(143)`, so `Popen.__exit__` waits out the live child past the ten seconds.
      - The handler raises a subclass of `KeyboardInterrupt`, which `Popen.__exit__` also waits on, since it compares the exact class.
      - The handler is installed for `cell` only, so the batch process dies by the signal with its stdout lost.
      - The handler raises an `Exception` subclass, so the batch's per-task catch starts the second task.
  - claim: >-
      A `saffron cell` that SIGTERM never reaches keeps its exit codes. A
      reviewable task exits 0, a task that did not make it exits 1, an
      infrastructure state exits 2, and a driver crash exits 2.
    witness: tests/test_cli.py::test_the_exit_code_distinguishes_the_terminal_states
    preserves: true
  - claim: >-
      A `saffron batch` that SIGTERM never reaches still exits 0 for
      `DRAINED`, `BUDGET` and `UNTIL`.
    witness: tests/test_cli.py::test_the_three_ordinary_stop_reasons_all_exit_zero
    preserves: true
  - claim: >-
      A `saffron batch` that SIGTERM never reaches still exits 2 for
      `INFRASTRUCTURE` and for a readiness failure.
    witness: tests/test_cli.py::test_infrastructure_and_a_failed_readiness_both_exit_two
    preserves: true
---

## Context

Backlog item **b-5df2a7**, placed in tier 2 on 2026-10-06. It cites
`DESIGN.md` §4.5. Every line number below was read at `958db033`.

**What happened.** The operator stopped `SA-0218`'s first cell mid-REVIEW
with SIGTERM. The process exited 143 and printed no teardown line. Three
containers kept running until they were removed by hand. Task 232 stayed
`REVIEWING`, its run was never closed, and its patch was never exported.

**The cleanup that exists.** `run_one_cell` catches `BaseException`, closes
the run `ABORTED`, stamps the task `ORPHANED` and re-raises
(`saffron/cell/session.py:3218-3227`). Its `finally` exports the patch and
calls `cell_down` (`saffron/cell/session.py:3229-3259`). `cell_down` removes
the cell's container, stops the proxy, then removes both networks and both
volumes (`saffron/cell/session.py:1102-1148`). A critic cell is a context
manager whose own `finally` removes its container and volumes
(`saffron/cell/session.py:1428-1437`). `run_task` also catches
`BaseException` and re-raises (`saffron/task.py:611`).

**Why SIGTERM skips it.** Ctrl-C raises `KeyboardInterrupt`, so all of the
above runs. SIGTERM's default action ends the process without raising, so
none of it does. The only `import signal` under `saffron/` is
`saffron/gates/runner.py:12`, and it sends SIGKILL to a gate's process
group. Nothing installs a handler.

**What each exception reaches.** `main` catches `Exception` around every
command and returns 2 (`saffron/cli.py:290-297`). Its `finally` closes the
ledger (`saffron/cli.py:298-299`). A batch catches `Exception` per task and
moves on to the next (`saffron/batch.py:268`). `run_batch`'s `finally`
closes the batch row `INFRASTRUCTURE` when nothing else did
(`saffron/batch.py:172-180`). The stack batch's own `finally` does the same
(`saffron/batch.py:834-836`). So `KeyboardInterrupt` and `SystemExit` both
pass every one of those catches and reach every `finally`.

**Why `KeyboardInterrupt` and not `SystemExit`.** The agent's turn runs in
`stream_exec`, inside a `with proc:` block over the exec process
(`saffron/cell/runtime.py:550`). On the way out, `Popen.__exit__` waits a
quarter second when the exception is exactly `KeyboardInterrupt`. For any
other exception it waits for the child to exit, read in CPython 3.14.7's
`subprocess` module. Measured on this host, 2026-10-07: a child
holding the pipe open let `KeyboardInterrupt` unwind 0.27 seconds after
the signal took effect. `SystemExit` waited until the child died. A
subclass of `KeyboardInterrupt` waited too, because that comparison is by
`==`.

**What the shell sees.** The console script is `saffron.cli:main`
(`pyproject.toml:21`). An unhandled `KeyboardInterrupt` makes Python print
a traceback and end itself by SIGINT, which reads as 130. Today a SIGTERM
reads as 143, the shell's 128 plus 15. The cell above exited 143. So `main`
keeps that number, now returned after the teardown. `DESIGN.md` §4.2.1 names
a batch's exit codes. This spec's pull request adds the SIGTERM case there
by hand, since `DESIGN.md` is protected.

**The log.** `CLAUDE.md:74-76` says a batch under launchd needs
`PYTHONUNBUFFERED=1`, "or SIGTERM discards the log". Python flushes stdout
when it exits normally, so after this change that clause is false.

## Problem

SIGTERM to `saffron cell` or `saffron batch` must unwind the way Ctrl-C
does, so the cleanup above runs. Make these changes in `saffron/cli.py`.

1. **The handler.** While `main` runs the `cell` or `batch` command,
   SIGTERM raises `KeyboardInterrupt`, that exact class. Install it around
   those two commands only, and put back the handler `main` found when the
   command returns or raises.
2. **A second SIGTERM.** On its first delivery the handler sets SIGTERM to
   be ignored, so a second signal during teardown does nothing. The handler
   `main` found comes back once the command unwinds.
3. **The exit code.** A `KeyboardInterrupt` that unwinds out of the command
   because of SIGTERM makes `main` return 143. One raised with no SIGTERM
   behind it still propagates out of `main`, as today.
4. **The prose the change falsifies.** Rewrite the clause in `CLAUDE.md`,
   `README.md`, `docs/HOST-HARDENING.md` and the plist comment that says
   SIGTERM discards the log. Name `143` in the exit code lists at
   `README.md:146-150`, `CLAUDE.md:91-92` and `saffron/cli.py:71-72`. The
   replacements are in the notes.

## Out of scope

- **A SIGTERM during a silent turn.** The handler runs at the main thread's
  next Python instruction. Measured on this host, a main thread waiting in
  `stream_exec`'s `lines.get` ran it only when the next line arrived. So a
  signal sent while the agent prints nothing waits for its next line or
  bound.
- **SIGKILL.** Nothing can catch it. The next cell of the same spec
  pre-cleans what one leaves (`saffron/cell/session.py:1393-1397`,
  `:1898-1901`).
- **PACKAGE.** A SIGTERM during PACKAGE unwinds as a Ctrl-C there does
  today. This spec changes nothing about it.
- **The Gate-only cell.** Its container is removed by the same `finally`
  in `critic_cell` as the critic cell's. No witness sends the signal while
  it runs.
- **A stack batch.** `saffron batch --stack` runs through the same `_batch`
  frame and its own `finally` (`saffron/batch.py:834-836`). No witness
  drives it.
- **SIGTERM under launchd.** The plist runs `exec ... uv run saffron batch`
  (`docs/host/dev.saffron.batch.plist:29`). Whether `uv` forwards SIGTERM to
  Python is unmeasured. Whether teardown finishes inside launchd's exit
  timeout is unmeasured too. So the docs speak of a SIGTERM that reaches the
  Python process.
- **Auto-clean on abort.** `DESIGN.md:502` (§4.3) says never auto-clean on
  failure. The Ctrl-C path at base already calls `export_patch` and then
  removes both volumes (`saffron/cell/session.py:3229-3259`), as Appendix J
  principle 42 moved the artifact into the patch. This spec changes no
  behaviour there. That §4.3 sentence is stale against this path, for the
  operator to settle.
- **The ignored disposition.** Teardown's child processes inherit the
  ignored SIGTERM. Each is a short runtime call, so nothing depends on it.
- **The batch's spend.** A run unwound by the exception is never attached
  to the batch (`saffron/batch.py:268-287`), so the row misses its spend.
  Ctrl-C does the same at base.
- **The Python version.** The cell runs CPython 3.12. Its `Popen.__exit__`
  holds the same exact-class test, read in 3.12.14 on this host.

## Notes for the agent

**Your base.** This spec follows `SA-0229` and `SA-0218`, which both edit
`saffron/cli.py`. Read `main` at your base before you edit it.

**Edit or new.** The handler and the 143 return are new code, so criteria
1 to 3 declare a witness and no mutant. Criteria 4 to 6 name tests that
exist at your base and must stay green.

**Witnesses red at base.** At base no handler is installed. Each in-process
witness installs its own SIGTERM handler first, which only records, so the
base run continues and fails on the exit code. Restore it in a `finally`.
Call `cli.main` inside `try` with `except BaseException` that fails the
test, so a leaked `KeyboardInterrupt` fails one test, not the session. The
process witness fails at base because the child dies by the signal, with
return code -15 and empty stdout. The witness module imports nothing the
change adds, so `revert` collects it with the source reverted.

**Criteria 1 and 2.** Call `cli.main` with a `cell` argv in-process.
Replace `task.run_one_cell` with a function that runs `_drive` from
`tests/test_session.py` over `_stub_the_runtime`, and returns its outcome.
Feed `_drive` a generator of turns: the plan turn, the implement turn and a
clean lens turn. Before the turn at the chosen index, the generator sends
SIGTERM to this process with `os.kill`. The handler raises at once, from
inside the generator. Measured: a self-sent SIGTERM raises before the next
statement. Index 1 lands mid-IMPLEMENT and index 2 lands on REVIEW's first
lens turn. Assert the slice of the stub's `order` list from the last `turn:`
entry on. Mid-REVIEW it holds `turn:saffron-critic-SY-1`, then the three
critic removals, then `cell_down`'s five. Assert that the stub's `turns`
list holds one more entry than the index, so no later turn started. Assert
the proxy's `stop` entry and `patch.diff` under `_drive`'s out directory.
Read the run and task states from `_drive`'s own ledger. Stub
`ensure_mirror`, `real_remote`, `fetch_default_branch` and `package` as
`test_the_exit_code_distinguishes_the_terminal_states` does. For criterion
2, wrap `runtime.remove_container` after `_stub_the_runtime`. Send the
second SIGTERM on the first call for `saffron-cell-SY-1` after the first
signal.

**Criterion 3.** Start `sys.executable -c` with a script string and stdout
piped. Its environment sets `CLAUDE_CODE_OAUTH_TOKEN` to a dummy and drops
`PYTHONUNBUFFERED` and `SAFFRON_CELL_RUNTIME`. Without the token `_run_cell`
raises (`saffron/cli.py:441-449`). Under podman `unattended_refusal` refuses
the night (`saffron/cli.py:1549-1552`). The script
replaces `cli.run_task`, `preflight.prepare_mirror`,
`preflight.check_readiness`, `cli._resolve_queue`, `cli._protected_paths_at`
and `cli._retirement_markers_at` by assignment. Then it calls
`sys.exit(cli.main(...))`. Its `run_task` prints a line naming the spec. It
starts a Python child that sleeps twenty seconds, with stdout to
`DEVNULL`, inside `with subprocess.Popen(...)`. There it writes a marker
file and sleeps. The batch resolves two candidates. Wait for the marker
with a thirty-second deadline, failing as soon as `poll()` shows the child
exited. Then send SIGTERM and `communicate` with a ten-second timeout.

**The prose replacements.** Edit only the words named, and keep the rest.

- In the sentence on `PYTHONUNBUFFERED=1` at `CLAUDE.md:74-76`, "or
  SIGTERM discards the log" becomes "or a SIGKILL discards the log".

- In `CLAUDE.md:91-92`, "`2` infrastructure failed" becomes "`2`
  infrastructure failed, `143` stopped by SIGTERM after teardown".

- In the comment above `CELL_EXIT` at `saffron/cli.py:71-79`, "(§3.3)."
  becomes "(§3.3), 143 SIGTERM." Rewrap it to the line length.

- In the sentence on `PYTHONUNBUFFERED=1` at `README.md:139-140`, "without
  it SIGTERM discards the log" becomes "without it a SIGKILL discards the
  log".

- After the `RATE_LIMITED` row at `README.md:150`, add a row for 143. Both
  cells read "stopped by SIGTERM, after its teardown".

- Rewrite the paragraph on `launchctl unload` at
  `docs/HOST-HARDENING.md:205-210` from "Measured:" on. It becomes
  "Measured before b-5df2a7, a process killed that way left a **0-byte**
  log. One that reaches Python now unwinds and flushes, exiting 143.
  Forwarding by uv run and launchd's exit timeout are unmeasured, and a
  silent agent turn delays the stop until its next line. A SIGKILL still
  discards the buffer." Backtick uv run.

- In the comment on `unload` at `docs/host/dev.saffron.batch.plist:35-39`,
  the text from the dash to "done." becomes ". Measured before b-5df2a7, a
  night killed that way left a 0-byte log. A SIGKILL still does."

**Measured on a prototype, 2026-10-07.** All three new witnesses were
written against `958db033` with this change, and passed. Each fails with
`saffron/cli.py` reverted. Every wrong version listed above was applied
and failed its own criterion's witness. `tests/test_cli.py` passed whole,
and `ty` passed on both files. Re-run at `a746f35d` with
`CLAUDE_CODE_OAUTH_TOKEN` unset and `SAFFRON_CELL_RUNTIME=podman` in the
host shell, all three passed. With `main` re-raising rather than returning
143, all three reported `FAILED` and the session ran to its end. By
`size_gate`, the code and tests counted 841 changed tokens and the prose
edits above 125.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. Keep each docstring within ten lines. A comment on the handler
names the `Popen.__exit__` reason in one or two lines.

**Size.** The `bug` ceiling is 1300 changed tokens. Nothing here is in
`elevate_on`, so `size` reports and does not block. Keep the test helpers
shared between criteria 1 and 2.
