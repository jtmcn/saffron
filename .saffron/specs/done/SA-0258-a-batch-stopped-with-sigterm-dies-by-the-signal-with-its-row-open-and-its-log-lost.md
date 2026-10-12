---
id: SA-0258
title: A batch stopped with SIGTERM dies by the signal, with its row open and its log lost
type: bug
priority: 2
depends_on: [SA-0245]
estimated_lines: 117
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
max_turns: 120
risk: standard
acceptance:
  - claim: >-
      A `saffron batch` process, with stdout piped and no
      `PYTHONUNBUFFERED`, is sent SIGTERM from outside while its first task
      holds a live child process, its stdout and stderr both discarded,
      inside a `with subprocess.Popen` block.
      It exits 143 within ten seconds. The last line on its stdout is the
      one its first task printed before the signal. No second task starts,
      and its batch row closes with an `ended_at` and the stop reason
      `INFRASTRUCTURE`.
    witness: tests/test_sigterm.py::test_a_batch_sent_sigterm_exits_143_with_its_log_flushed
    wrong_versions:
      - The handler raises `SystemExit(143)`, so `Popen.__exit__` waits out the live child past the ten seconds.
      - The handler raises a subclass of `KeyboardInterrupt`, which `Popen.__exit__` also waits on, since it compares the exact class.
      - The handler raises an `Exception` subclass, so `Popen.__exit__` waits out the live child past the ten seconds.
      - The handler ends the process with `os._exit(143)`, so the buffered line and the row's close are both lost.
      - The handler is installed for `cell` only, so the batch process dies by the signal with its stdout lost.
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
`DESIGN.md` §4.5. Every line number below was read at `3983d5a5`, which
is before `SA-0245`. Lines in `saffron/cli.py` move once it lands.

**This spec is the second of two.** `SA-0245` makes SIGTERM to `saffron
cell` raise `KeyboardInterrupt` and return 143 from `main`. It leaves
`saffron batch` alone. This spec wraps `batch` in the same handler. It
adds the witness that starts a real process, and the prose that the
flushed log makes true.

**What a batch does with the signal today.** `main` calls `_batch`
directly (`saffron/cli.py:275-276`). SIGTERM's default action ends the
process without raising. A batch under launchd writes its stdout to a
file, which Python block-buffers. So the buffered lines are lost, and the
batch row stays open.

**What `KeyboardInterrupt` reaches in a batch.** A batch catches
`Exception` per task and moves on to the next (`saffron/batch.py:269`).
`run_batch`'s `finally` closes the row `INFRASTRUCTURE` when nothing else
did (`saffron/batch.py:173-181`). The stack batch's own `finally` does
the same (`saffron/batch.py:843-845`). So a `KeyboardInterrupt` passes
the per-task catch, closes the row, and reaches `SA-0245`'s 143 return.

**Why the exact class matters here.** An agent turn runs inside
`with proc:` (`saffron/cell/runtime.py:550`). `Popen.__exit__` skips its
wait for the child only when the exception's class `==`
`KeyboardInterrupt`. Read in CPython 3.12.14 and 3.14.7 on this host,
2026-10-10. Any other class, a subclass included, waits for the child.
`SA-0245`'s in-process witnesses run no child, so none of them sees
this. This spec's witness does.

**What run 32 measured.** Its cell wrote a process witness whose fake
task opened `with subprocess.Popen(...)` and did nothing in the body.
The child wrote the marker. So the signal landed inside `__exit__`'s own
`wait()`, and the exception never reached `__exit__`'s class check.
Under `SystemExit(143)` and under a `KeyboardInterrupt` subclass the
witness stayed green. Re-run on 2026-10-10 under 3.12.14 and 3.14.7, both
still passed. Two of the four blockers that ended that cell were these.

**The prose.** `CLAUDE.md:74-76` says a batch under launchd needs
`PYTHONUNBUFFERED=1`, "or SIGTERM discards the log". `README.md:139-140`,
`docs/HOST-HARDENING.md:205-210` and the plist comment at
`docs/host/dev.saffron.batch.plist:35-39` say the same. Python flushes
stdout when it exits normally, so after this change each is false. The
exit code lists at `CLAUDE.md:91-92` and `README.md:146-150` name no
143.

## Problem

SIGTERM to `saffron batch` must unwind the way Ctrl-C does.

1. **The handler.** In `main`, run the `batch` command inside the same
   SIGTERM handler `SA-0245` put around `cell`. Read it at your base and
   reuse it. Change nothing in how it behaves.
2. **The prose the change falsifies.** Rewrite the clause in `CLAUDE.md`,
   `README.md`, `docs/HOST-HARDENING.md` and the plist comment that says
   SIGTERM discards the log. Name `143` in the exit code lists in
   `CLAUDE.md` and `README.md`. The replacements are in the notes.

## Out of scope

- **SIGTERM under launchd.** The plist runs `exec ... uv run saffron
  batch` (`docs/host/dev.saffron.batch.plist:29`). Whether `uv` forwards
  SIGTERM to Python is unmeasured. Whether teardown finishes inside
  launchd's exit timeout is unmeasured too. So the docs speak of a
  SIGTERM that reaches the Python process.
- **A stack batch.** `saffron batch --stack` runs through the same
  `_batch` frame and its own `finally` (`saffron/batch.py:843-845`). No
  witness drives it.
- **An agent turn's piped child.** A real turn pipes the agent's stdout
  to a reader thread (`saffron/cell/runtime.py:538-543`). That thread
  reads inside `with proc:` (`saffron/cell/runtime.py:550`). `Popen.__exit__` closes
  that pipe before its class check, and the close waits on the blocked
  reader. Measured on macOS, 2026-10-10, that stop waited until the child
  exited. The witness's child discards its output, so it drives none of
  this, and this spec changes none of it. Backlog `item b-52e670` holds
  it.
- **A `saffron cell` process.** `SA-0245`'s witnesses drive `cell`
  in-process. No witness here starts a `cell` process.
- **The batch's spend.** A run unwound by the exception is never attached
  to the batch (`saffron/batch.py:269-300`), so the row misses its
  spend. Ctrl-C does the same at base.
- **`DESIGN.md:484`** (§4.2.1) already says a batch stopped by SIGTERM
  exits 143, and credits `SA-0245` and `SA-0258`. This spec is what makes
  the batch half true. `DESIGN.md` is protected, and it needs no edit.

## Notes for the agent

**Your base.** This spec follows `SA-0245`, which adds the handler and
the 143 return to `saffron/cli.py`. Read `main` at your base before you
edit it.

**Edit or new.** The handler's spelling is `SA-0245`'s, which did not
exist when this spec was written. So criterion 1 declares a witness and
no mutant. Criteria 2 and 3 name tests that exist at your base and must
stay green. They call `main` with `batch` in-process, so they run through
the new wrap.

**The witness.** Add it to `tests/test_sigterm.py`. Start
`sys.executable -c` with a script string, and pipe its stdout only. Set
`cwd` to the repo root, as the cell installs the project with
`--no-install-project` and imports `saffron` from `/work`. Pass `--home`
under `tmp_path`, so no run writes `~/.saffron/ledger.db`. Build its
environment with `dict(os.environ, CLAUDE_CODE_OAUTH_TOKEN="sk-test")`.
Measured: `{**os.environ, ...}` fails `ty`'s `Popen` overload. Drop
`PYTHONUNBUFFERED` and `SAFFRON_CELL_RUNTIME` from it. Under podman,
`unattended_refusal` refuses the night (`saffron/cli.py:1730-1733`).

The script replaces `preflight.check_readiness`, `cli._resolve_queue`,
`cli._protected_paths_at`, `cli._retirement_markers_at` and
`cli.run_task` by assignment. Then it calls `sys.exit(cli.main(...))`.
The queue resolves two candidates. Its `run_task` prints a line naming
the spec. It then opens `with subprocess.Popen(...)` on a Python child
that sleeps twenty seconds, with stdout and stderr both to `DEVNULL`.

**Where the signal lands.** Inside that `with` body, the parent writes a
marker file and then sleeps sixty seconds. The parent writes the marker,
never the child, so the signal arrives while the parent sleeps in the
body. Then the handler's exception reaches `Popen.__exit__`, whose class
check decides whether it waits twenty seconds. A body that does nothing
lets the signal land in `__exit__`'s own wait instead, and run 32's
witness survived both wrong versions that way.

Wait for the marker with a thirty-second deadline, and fail as soon as
`poll()` shows the process exited. Then send SIGTERM and `communicate`
with a ten-second timeout. Catch `subprocess.TimeoutExpired` there and
let an assertion fail, not the exception. Kill and reap the process in a
`finally`. Read the batch row from the ledger under `--home`. The
twenty-second child is left to exit on its own, since it holds no pipe.

**No second task.** Every wrong version above fails on the exit code,
the last line or the ten seconds. None is caught by the clause that no
second task starts. It stays in the claim. The `Exception` subclass does
start one, and the witness fails it on the ten seconds.

**`SA-0245`'s `batch` assertion.** `SA-0245`'s criterion 1 witness ends
with a `batch` run. It asserts the handler during `_batch` equals the one
in place before `main`. Your wrap makes that false. Flip it to `!=` and
change its comment to say `batch` runs under the handler. No gate of this
spec judges that test, since it is neither added here nor declared here.

**Witness red at base.** At your base `batch` has no handler. The
process dies by the signal with return code -15 and empty stdout.

**The prose replacements.** Edit only the words named, and keep the
rest.

- In the sentence on `PYTHONUNBUFFERED=1` at `CLAUDE.md:74-76`, replace
  the text from "or SIGTERM" to the sentence's end with this.

  ```text
  or a SIGKILL loses whatever output is still buffered, and the
  log is the night's only human-readable record.
  ```

- In `CLAUDE.md:91-92`, "`2` infrastructure failed" becomes "`2`
  infrastructure failed, `143` stopped by SIGTERM after teardown".

- The sentence on `PYTHONUNBUFFERED=1` at `README.md:139-140` becomes
  this. It drops the dash the base line holds.

  ```text
  Under launchd, `batch` needs `PYTHONUNBUFFERED=1`. Without it, a SIGKILL loses whatever output
  is still buffered, and the log is the night's only human-readable record.
  ```

- After the `RATE_LIMITED` row at `README.md:150`, add a row for 143.
  Both cells read "stopped by SIGTERM, after its teardown".

- Rewrite the paragraph on `launchctl unload` at
  `docs/HOST-HARDENING.md:205-210` from "Measured:" on. It becomes
  "Measured before b-5df2a7, a process killed that way left a **0-byte**
  log. One that reaches Python now unwinds and flushes, exiting 143. Its
  log then ends with no `batch:` stop line, and its row closes
  `INFRASTRUCTURE`. Forwarding by `uv run` and launchd's exit timeout are
  unmeasured. On macOS, a stop during a silent agent turn waited until the
  agent's process exited. A SIGKILL still loses what is buffered."
  Measured on macOS, 2026-10-10: the handler ran at once, and
  `Popen.__exit__` then waited on the turn's blocked stdout reader until
  the child exited. The stop line is printed at `saffron/cli.py:1969`,
  only once the batch loop returns, which a SIGTERM never lets it do.

- In the comment on `unload` at `docs/host/dev.saffron.batch.plist:35-39`,
  replace the text from the space before the dash through "empty.". The
  comment's second line then ends "logout and shutdown. Measured before
  b-5df2a7, a" and the rest reads "night killed that way left a 0-byte
  log. A SIGKILL still loses what is buffered. -->"

**Measured on a prototype, 2026-10-10.** The witness was written over a
prototype of `SA-0245` at `6b033c04`. It passed under CPython 3.12.14 and
3.14.7 on macOS, and under 3.12.14 on Linux aarch64 in the `saffron/cell`
image. There the `SystemExit` and subclass wrong versions failed it too. It fails with `saffron/cli.py`
reverted to that prototype, returning -15 with empty stdout. Each of the
five wrong versions above was applied as one edit and failed the
witness on an assertion, under both versions. `ruff`, `ty`, `dead`,
`structure` and `prose` passed. `python3 hooks/prose_limit.py --file`
reported 0 new hits on `README.md`, `CLAUDE.md`, `saffron/cli.py` and
the test. It reads neither `docs/HOST-HARDENING.md` nor the plist. By
`size_gate`, the change counted 467 changed tokens, 285 of them in the
test.

**The `prose` gate** reads every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Size.** The `bug` ceiling is 1300 changed tokens. Nothing here is in
`elevate_on`, so `size` reports and does not block.
