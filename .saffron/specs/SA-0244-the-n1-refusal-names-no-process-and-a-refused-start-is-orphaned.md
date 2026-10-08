---
id: SA-0244
title: The N1 refusal names ports and not the processes behind them, and a start that preflight refuses leaves an `ORPHANED` task row
type: bug
priority: 2
depends_on: [SA-0243]
estimated_lines: 188
estimate_measured: true
touches:
  - saffron/preflight.py
  - saffron/cell/session.py
  - saffron/ledger.py
  - tests/test_preflight.py
  - tests/test_session.py
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
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/events.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/cell/worktree.py
  - saffron/cell/runtimes/**
budget_usd: 20
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      The N1 refusal names, after each answering address, every command lsof
      listed on that address's port, spelled as lsof printed it. The names
      come from the one listing the probed ports came from. A port that
      listing does not hold is named `no known process`. The witness brings
      `cell_up` up against one lsof listing, and a different listing for any
      later lsof call. Four addresses answer. The gateway and the LAN address
      answer on a port that one truncated command holds. The gateway answers
      on a port two commands hold, one of them holding a space. The gateway
      answers on a port the listing lacks.
    witness: tests/test_session.py::test_the_n1_refusal_names_the_processes_behind_each_answering_port
    wrong_versions:
      - A refusal that reads lsof again when the probe answers, so it names the second listing's process.
      - One command named per port, so the second command on a shared port is lost.
      - A port the listing lacks left bare, or dropped from the refusal.
      - Only the first answering address named, the rest left as bare addresses.
      - '`cell_up` handing the probe no listing, so every address reads `no known process`.'
  - claim: >-
      Each of the seven refusals `saffron/preflight.py` raises under
      `cell_up` raises `PreflightFailed`, a subclass of
      `runtime.CellRuntimeError`. The seven are the two lsof refusals in
      `host_probe_ports`, the LAN address refusal, the host-binding probe
      that did not run, the N1 refusal, and the upstream probe that did not
      run or could not reach. The witness drives each one. A
      `CellRuntimeError` that `runtime.run_ephemeral` raises under the
      upstream probe still reaches the caller as a plain `CellRuntimeError`.
    witness: tests/test_preflight.py::test_each_refusal_cell_up_can_reach_is_a_preflight_failure
    wrong_versions:
      - The new class raised at the N1 refusal alone, the other six left plain.
      - The LAN address refusal left plain, since `cell_up` reaches it through `probe_addresses`.
      - A class that subclasses `RuntimeError` alone, so every `except runtime.CellRuntimeError` stops catching it.
      - A probe that turns the runtime's own `CellRuntimeError` into the new class, so a dead runtime reads as a refusal.
      - The host-binding probe's "did not run" refusal left plain.
  - claim: >-
      When `cell_up` raises `PreflightFailed`, the task ends
      `PREFLIGHT_FAILED` and nothing is raised. The returned outcome and the
      task row both say so. The run row reads preflight `FAILED` and status
      `COMPLETE`. The last preflight event carries the refusal's own text.
      The witness raises it from each of the four preflight calls `cell_up`
      makes. A plain `CellRuntimeError` from the image build, or from the
      host probe's call, still raises. It leaves the task `ORPHANED` and the
      run `ABORTED` with no preflight outcome.
    witness: tests/test_session.py::test_a_refused_start_ends_preflight_failed_and_a_runtime_failure_orphaned
    wrong_versions:
      - Every `CellRuntimeError` from `cell_up` caught as a refusal, so a dead runtime ends `PREFLIGHT_FAILED`.
      - Only a refusal whose text names the N1 probe caught, so a dead proxy route still ends `ORPHANED`.
      - The run row closed `ABORTED` on a refusal.
      - The task row set without the run's preflight outcome.
      - The refusal's text never emitted, so the operator sees the state and not why.
      - The refusal raised again after the rows are written, so `saffron cell` prints a traceback.
---

## Context

Backlog item **b-e0cd57**, filed from the spec loop's run 16. It cites
`DESIGN.md` §5.1 and §4.1. Every line number below was read at `958db033`.

**What happened.** Runs 16 and 18 each failed a start on the N1 refusal.
The host listeners were RAATServer on port 9200 and limactl on port 53.
The refusal named the addresses alone, and the operator found the processes
by hand with lsof. `SAFFRON_ALLOW_HOST_PROCESS` needed lsof's truncated
spelling, `RAATServe`. Each refused start also left an `ORPHANED` task row
for a task that never started.

**The refusal today.** `assert_host_is_unreachable` joins the answering
addresses with `", "` into its message, and nothing else
(`saffron/preflight.py:208-221`). The data to name them is already read.
`listening_sockets` turns lsof's listing into `(command, port)` pairs, with
COMMAND spelled as lsof prints it (`saffron/preflight.py:67-85`).
`host_probe_ports` runs lsof once and returns only the ports to probe and
the tolerated listeners (`saffron/preflight.py:105-130`). The allowlist
matches that COMMAND column (`saffron/preflight.py:49-52`).

**One enumeration per run.** `cell_up` calls `host_probe_ports` once
(`saffron/cell/session.py:1063`). It hands those ports to
`assert_host_is_unreachable` on each network
(`saffron/cell/session.py:1076-1077`). The probe must not take a second
listing, by the rule `test_the_probe_checks_the_ports_it_was_given` states
(`tests/test_preflight.py:136-154`).

**The seven refusals.** `saffron/preflight.py` raises
`runtime.CellRuntimeError` at seven places `cell_up` reaches. Two are lsof
failing to run (`:120`) and lsof printing no listing (`:125`). One is the
LAN address (`:145`). Two are the host-binding probe not running (`:201`)
and the N1 refusal (`:216`). Two are the upstream probe not running
(`:265`) or not reaching (`:269`). `cell_up` reaches them through four calls:
`assert_proxy_reaches_upstream` (`saffron/cell/session.py:1044-1046`),
`host_probe_ports` (`:1063`), `probe_addresses` (`:1066`) and
`assert_host_is_unreachable` (`:1077`). `disk_headroom_ok` raises
`RuntimeError`, and only `check_readiness` calls it
(`saffron/preflight.py:382-397`, `:513-514`).

**Other `CellRuntimeError`s under `cell_up`.** The runtime's own calls raise
the same class. `runtime.call` raises it when the binary will not run
(`saffron/cell/runtime.py:289`, `:307`). The proxy raises it when it starts
with no address (`saffron/cell/proxy.py:74`). `proxy_address` raises it too
(`saffron/cell/session.py:960-967`). The item names no call for its stopped
container apiserver, and each call above is the runtime's own.

**How a start fails today.** In `_drive_cell`, `create_run` and
`create_task` mint the run and the task row before any cell exists
(`saffron/cell/session.py:1960-1974`). It then calls `cell_up` inside its
`try` (`saffron/cell/session.py:1997-2013`). Any raise
there reaches `except BaseException`. That handler finishes the run
`ABORTED`, sets the task `ORPHANED` and re-raises
(`saffron/cell/session.py:3218-3228`). The CLI prints the exception and
exits 2 (`saffron/cli.py:290-297`).

**What `PREFLIGHT_FAILED` gets.** A baseline that aborts writes the run's
preflight `FAILED` and the task `PREFLIGHT_FAILED`. It finishes the run
`COMPLETE` and returns an outcome (`saffron/cell/session.py:2056-2069`).
The CLI's exit map gives `PREFLIGHT_FAILED` 2 (`saffron/cli.py:89`). The
batch loop counts it through `ABORT_STATES` toward the breaker
(`saffron/batch.py:61-63`, `:311`). The scheduler
re-queues it, as it does `ORPHANED` (`saffron/scheduler.py:111-120`).
`run_task` sends any state other than `READY_FOR_REVIEW` and an exhausted
package to `push_unpackaged_work` (`saffron/task.py:706-720`). That returns
at once when the task has no `patch.diff` (`saffron/phases/package.py:1112-1119`).

**The other caller.** `end_review.py` calls `cell_up` twice and handles
neither raise itself (`saffron/end_review.py:597`, `:615`). A subclass of
`CellRuntimeError` reaches it unchanged.

## Problem

A refused start must say which host process answered, and must not leave a
row that says a cell died. Make these changes.

1. **The class.** Add `PreflightFailed` to `saffron/preflight.py`, as a
   subclass of `runtime.CellRuntimeError`. Raise it at each of the seven
   refusals above, in place of the plain class. Leave every runtime call
   under them raising what it raises today.
2. **The names.** The N1 refusal names, after each answering address, every
   command the run's one lsof listing holds on that address's port. Use
   the spelling `listening_sockets` returns. Name a port the listing lacks
   `no known process`. Carry the listing from the one enumeration to the
   probe. Do not run lsof again when the probe answers.
3. **The state.** In `_drive_cell`, a `PreflightFailed` from `cell_up`
   writes what the baseline abort writes. Set the run's preflight `FAILED`
   and the task `PREFLIGHT_FAILED`, finish the run `COMPLETE`, and return a
   `PREFLIGHT_FAILED` outcome. Emit one `Preflight` event first, whose
   detail is the refusal's own text. Any other exception keeps today's
   handling.

## Out of scope

- **A runtime that fails before a cell exists.** A stopped apiserver, or a
  binary that will not run, still leaves `ORPHANED`. The item asks for that
  half too. The operator scoped this spec to preflight's own refusals.
- **The refusal's advice.** It still says to bind the service to
  `127.0.0.1`. It does not name `SAFFRON_ALLOW_HOST_PROCESS`.
- **`saffron/task.py`, `saffron/batch.py` and `saffron/cli.py`.** Each
  already handles a returned `PREFLIGHT_FAILED`, as the Context shows.
- **A `patch.diff` an earlier cell of the same spec left.** `run_task` would
  pass it to `push_unpackaged_work` after a refusal. The baseline abort has
  the same exposure at your base.
- **`DESIGN.md` §3.3 and `CONTEXT.md`.** Both say only a baseline abort
  writes `PREFLIGHT_FAILED`. The operator edits them by hand.

## Notes for the agent

**Your base.** This spec stacks on `SA-0243`, the last of a chain that
edits `saffron/cell/session.py`. Read each file at your base before you edit
it, since the line numbers above move with each of them. Keep your hunks
away from theirs. `SA-0243` moves the final state write into
`saffron/task.py`. At `958db033` the baseline abort and the `ORPHANED`
handler each write the task row inside `_drive_cell`. If your base moved
either write, write the refusal's rows where the baseline abort writes its
own. Then read them in criterion 3's witness through that same caller.
Put the new handler as an `except` clause beside
`except RateLimited`, before `except BaseException`. Do not wrap the
`cell_up(` call itself. Import `preflight` among `_drive_cell`'s own local
imports.

**Edit or new.** The class, the naming and the handler are new code. So
each criterion declares a witness and no mutant, and `witness` will report
`skip`.

**The refusal's shape.** Write each answering address, a space, then its
commands in parentheses, joined by `", "`. Order the commands as
`listening_sockets` orders them. The addresses stay joined by `", "`, and
the advice after them is unchanged. So the gateway on a port that
`limactl` and `Google Ch` share reads `10.88.0.1:53 (Google Ch, limactl)`.

**Criterion 1's witness.** Put it beside
`test_no_cell_is_created_until_the_host_probe_has_passed` in
`tests/test_session.py`, never at the end of the file. Call
`_stub_the_runtime`, then set `host_probe_ports` and
`assert_host_is_unreachable` back to the real functions. Stub
`preflight._lan_address` to return `192.168.1.5`. Fake `subprocess.run` to
return a `COMMAND` header and rows for `RAATServe` on 9200, and for
`limactl` and `Google Ch` on 53. Any later call returns a listing naming
another command on 9200. Fake `runtime.run_ephemeral` to answer at
`10.88.0.1:9200`, `192.168.1.5:9200`, `10.88.0.1:53` and `10.88.0.1:8000`.
Call `session.cell_up` as `test_cell_up_puts_the_proxy_on_the_critic_network_and_probes_it`
does. Assert each of the four named addresses in the message, and that the
second listing's command is absent.

**Criterion 2's witness.** Put it in `tests/test_preflight.py`, before
`test_any_http_status_from_the_upstream_is_reachability`. Drive each of the
seven refusals with `pytest.raises` on the new class and a `match` on its
own text. Fake `subprocess.run` for the two lsof refusals. Replace the
module's `socket` name for the LAN address. Script `runtime.run_ephemeral`
for the other four. Last, make `run_ephemeral` raise a plain
`CellRuntimeError` under `assert_proxy_reaches_upstream`, and assert the
caller does not get the new class.

**Criterion 3's witness.** Put it beside criterion 1's. Loop over the four
preflight calls. Each pass calls `monkeypatch.undo()`, then
`_stub_the_runtime`, then stubs that call to raise the new class with a text
naming the call. Drive it with `_drive` under its own `tmp_path`
subdirectory, with `capture` set. Read the run and task rows from the
returned ledger. Then loop over `image.build_cell_image` and
`preflight.assert_host_is_unreachable` raising a plain `CellRuntimeError`.
Use a second subdirectory, since one name repeats. Reopen
`Ledger(<dir> / "ledger.db")` after the raise to read the rows. Bind any
loop variable a stub reads as a default argument, since `ruff`'s `B` rules
are on.

**Name the new class through the module.** Write
`preflight.PreflightFailed` inside each test body, never a module-scope
import. A reverted run then fails each witness, where a module-scope import
would make a collection error that `revert` reads as `skip`.

**Two stubs move with the change.** If `host_probe_ports` returns the
listing as well, update `_stub_the_runtime`'s `enumerate` stub
(`tests/test_session.py:1113-1116`). The `_host` stub in
`test_cell_up_puts_the_proxy_on_the_critic_network_and_probes_it` must
accept any new argument the probe call passes (`tests/test_session.py:6203`).

**Two comments go stale.** The comment over `except BaseException` calls
preflight raising the path an operator hits first
(`saffron/cell/session.py:3218-3223`). A refusal no longer reaches it, so
reword that block in two lines. The `runs` table's comment says the
preflight outcome is read off the baseline suite, and that NULL means the
run never reached it (`saffron/ledger.py:111-113`). Reword its two lines
to name the refusal too. Change nothing else in `saffron/ledger.py`.

**Measured on a prototype, 2026-10-07.** All three witnesses were written
against `958db033` with the three changes above, and passed. The whole
suite passed, 3834 tests. Each witness failed with `saffron/preflight.py` and
`saffron/cell/session.py` reverted, on an assertion or an `AttributeError`, never at collection.
Each wrong version listed above was applied to the prototype and failed its
own criterion's witness.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. Keep each docstring within ten lines and each comment within two.
An edited comment counts as new. The prototype's first five-line reword of
the stale block failed it, and a two-line one passed.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks. The
prototype counted 751 changed tokens by `size_gate`, against the `bug`
ceiling of 1300. `estimated_lines` is those tokens over four. Keep comments
short and the tests close to the shapes above.
