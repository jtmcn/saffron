---
id: SA-0235
title: A first call the provider never served leaves no record of the proxy's state and log, or of the cell's resolver and route
type: feature
priority: 2
depends_on: [SA-0233]
estimated_lines: 290
estimate_measured: true
touches:
  - saffron/cell/runtime.py
  - saffron/cell/egress_report.py
  - saffron/cell/session.py
  - saffron/events.py
  - tests/test_runtime.py
  - tests/test_session.py
  - tests/test_events.py
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
  - saffron/preflight.py
  - saffron/cell/proxy.py
  - saffron/cell/worktree.py
  - saffron/cell/runtimes/**
  - saffron/phases/**
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/record/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/agents/**
  - tests/test_proxy.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 27
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      When the plan turn's first call fails and the provider served it
      nothing, teardown makes four reads before it removes the cell's
      container or stops the proxy. It reads the proxy container's state
      with the runtime's `inspect`, and its whole log with the runtime's
      `logs`, both of that command's streams. It reads the cell's resolver
      file and the kernel's IPv4 route table, each by an exec in the task's
      own cell. That exec runs the cell's own `head`, capped at 65536
      bytes, with a timeout of at most 30 seconds. Each read is one `Teardown` event with
      `ok` true. Its detail starts with the read's label, `proxy state`,
      `proxy log`, `cell resolver` or `cell route`, and carries what the
      read returned. The witness scripts a 60-line log with lines on both
      streams and checks every line arrives. It then drives six other
      cells, and none of the four reads runs in any. They are a green cell, a first
      call that failed with tokens served, a first call refused on a
      `rejected` window, a schema re-prompt and a scope re-prompt each
      served nothing after a completed first call, and an implement turn
      served nothing after a completed plan turn.
    witness: tests/test_session.py::test_a_first_call_the_provider_never_served_reports_the_proxy_and_the_cell_before_teardown
    wrong_versions:
      - The reads placed after `cell_down`, or inside it after the container's removal, so the cell and the proxy are gone.
      - The log read through `proxy.denied_egress` or `proxy.failed_egress`, so only DENIED and FAILED rows arrive, ten at most.
      - The log read from the command's stdout alone, so a runtime that writes the container's stderr to its own stderr loses those lines.
      - The resolver and the route read from the proxy container rather than the task's cell.
      - The route read with `ip route`, which the cell base image does not carry.
      - The cell's two files read with `cat`, so the argv carries no byte cap at all.
      - The two execs left at `exec_`'s default timeout of 900 seconds.
      - The state read through `container_ip`, so only the proxy's address is kept.
      - The reads run on every `AgentFailed` the plan turn raises, so a first call that was served reads them too.
      - The reads keyed on the attempt's spend being $0.00, so a re-prompt that failed after a free first call reads them.
      - The reads run on every teardown, a green cell's included.
      - The reads run on a `rejected` window as well, since its attempt also says the provider served nothing.
  - claim: >-
      A read that fails is reported as failed and changes nothing else. The
      witness fails each of the four reads in turn, in three ways. Its
      runtime call exits non-zero, raises `CellRuntimeError`, or times out.
      In each of the twelve cells, that read is one `Teardown` event with
      `ok` false. Its detail starts with the read's label and carries the
      failure's text, which for a timeout says `timed out`. The other three reads are still reported with `ok`
      true. The outcome and the task row still say `PROVIDER_UNREACHABLE`,
      the run row reads `COMPLETE`, the proxy is still stopped and the
      cell's container is still removed.
    witness: tests/test_session.py::test_a_read_that_fails_is_reported_and_masks_neither_the_outcome_nor_teardown
    wrong_versions:
      - A failed read skipped with no event.
      - A failed read reported with `ok` true.
      - A failed read whose detail drops the runtime's stderr or the exception's text.
      - A timed-out read whose detail is its label alone, since a timeout's stderr can be empty.
      - One try around all four reads, so the first failure hides the reads after it.
      - A raise let out of the reads, so `run_one_cell` raises instead of returning, and `cell_down` never runs.
  - claim: >-
      `runtime` reads a container's state and its log through the selected
      runtime's own binary, as `<binary> inspect <name>` and `<binary> logs
      <name>` with nothing else on either argv. Each passes a timeout of at
      most 30 seconds and returns the call's outcome without raising, a
      non-zero exit included. The witness drives both reads under the
      `apple` dialect and the `podman` dialect, each with a zero and a
      non-zero exit.
    witness: tests/test_runtime.py::test_a_containers_state_and_log_are_read_through_the_selected_runtime
    wrong_versions:
      - The binary spelled as a literal rather than read from the selected dialect.
      - A read built on `_must`, so a non-zero exit raises.
      - The log read with a follow flag, so it waits out its timeout.
      - A read built on `call` with no timeout, so it waits `call`'s default of 120 seconds.
---

## Context

Backlog item **b-a6bfb0**, filed from the spec loop's run 22. It cites
`DESIGN.md` §5.1.1. Every line number below was read at `958db033`.

**What happened.** In run 22 the agent's calls were refused on two of five
agent starts. Each time, preflight had printed `proxy reaches
api.anthropic.com (401)` about five minutes earlier. The first time, a
host process held port 53. The second time nothing did, and the cause was never found, because
nothing on this path keeps the proxy's log or reads the cell's network.

**Preflight's egress probe.** `cell_up` (`saffron/cell/session.py:971`)
brings a cell up. It calls `proxy.start_proxy`
(`saffron/cell/session.py:1040`). It then asks
`preflight.assert_proxy_reaches_upstream` once per leg and prints the
status it got (`saffron/cell/session.py:1042-1047`). That probe runs in an
ephemeral sibling, before the cell exists.

**What teardown reads today.** `_drive_cell`'s `finally` emits
`Teardown("start")`, exports the patch while the cell is still up, then
calls `cell_down` (`saffron/cell/session.py:3229-3259`). `cell_down`
(`saffron/cell/session.py:1102`) takes the cell down. It removes the cell's
container first, with `runtime.remove_container`
(`saffron/cell/session.py:1132`). It then
reads `proxy.denied_egress()` and `proxy.failed_egress()` and stops the
proxy (`saffron/cell/session.py:1134-1140`). Those two keep only squid's
`TCP_DENIED` rows and its 5xx or `000` rows, ten of each at most
(`saffron/cell/proxy.py:80-99`). The log they read is `<binary> logs
saffron-proxy` through `runtime.call`. A failure returns an empty list, so a
log that could not be read looks like a clean one
(`saffron/cell/proxy.py:102-113`). A connection that never reached squid
leaves no row at all, and nothing reads the proxy container's state or the
cell's resolver or route.

**The path this spec reports on.** `_drive_cell`
(`saffron/cell/session.py:1852`) drives the cell. Its `except
implement.AgentFailed` catches the plan turn's failure
(`saffron/cell/session.py:2229`). There
`provider_served_nothing` on the failed attempt picks `PROVIDER_UNREACHABLE`
over `NOT_IMPLEMENTED` (`saffron/cell/session.py:2235-2238`).
`plan_checkpoint` (`saffron/cell/session.py:538`) runs the plan turn. It
clears `provider_served_nothing` when a re-prompt failed after a completed
first call (`saffron/cell/session.py:678-681`). A failed turn on a
`rejected` window never reaches that catch. `stop_on_rejected`
(`saffron/cell/session.py:217-237`) turns it into `RateLimited` first.
So reaching the catch with the flag set means the plan turn's first call was not served.

**The runtime's view.** `runtime.py` names no product. Its argvs start
with `dialect().binary` (`saffron/cell/runtime.py:237`, `:456`, `:619`). `container_ip`
already runs `<binary> inspect <name>` (`saffron/cell/runtime.py:618-622`)
and `_proxy_log` already runs the runtime's `logs`
(`saffron/cell/proxy.py:102-113`), under either dialect. `exec_` runs a command
in a container and defaults to a 900-second timeout
(`saffron/cell/runtime.py:465-472`). `_call` returns a non-zero exit or a
timeout as a `Completed`. It raises `CellRuntimeError` only when the binary
cannot be executed (`saffron/cell/runtime.py:273-292`).

**Measured on this host, 2026-10-07, `container` CLI 1.3.0.**
`saffron/cell-base:python` (Debian trixie) has no `ip` binary. `command -v
ip` exited 127. Under `--cap-drop ALL`, `cat /etc/resolv.conf
/proc/net/route` printed the resolver and the kernel's IPv4 route table, and
`head -c 65536 /proc/net/route` printed the same table.
`container inspect saffron-proxy` printed 3,266 bytes of JSON carrying
`"state" : "running"` and each network's address and gateway. `container
logs` and `container inspect` on a name that does not exist each exited 1
with the reason on stderr.

## Problem

When the plan turn's first call was not served, read the proxy and the
cell before teardown removes either, and report each read. Make these
changes.

1. **Two runtime reads.** Add `inspect_container(name)` and
   `container_logs(name)` to `saffron/cell/runtime.py`. Each runs
   `[dialect().binary, "inspect" | "logs", name]` through `_call` and
   returns the `Completed`. Each owns its timeout, a `timeout_s` defaulting
   to 30 seconds, and `egress_report.py` passes none. Add no `Dialect`
   member. Both verbs are already spelled the same under both dialects at
   base, by `container_ip` and `_proxy_log`. Podman's `logs` was never
   measured, since the 2026-09-11 evidence measured only `inspect`. A
   runtime that spells it otherwise shows up as a failed read.
2. **The four reads.** Write `saffron/cell/egress_report.py` with one
   function taking the cell's container name. It makes the four reads in
   order. The proxy's state is `runtime.inspect_container(proxy.PROXY_NAME)`
   and its log is `runtime.container_logs(proxy.PROXY_NAME)`, stdout then
   stderr. The cell's resolver is `runtime.exec_(container, ["head", "-c",
   "65536", "/etc/resolv.conf"], ...)`. Its route is the same exec of
   `/proc/net/route`. Each passes `timeout_s=30` to `exec_`. The byte cap
   is the cell's own `head`, so a cell that replaced `head` is not held to
   it. The host's only bound is that timeout. Its `subprocess.run` with
   `capture_output` holds both streams in memory until the process ends
   (`saffron/cell/runtime.py:279`).
   It returns one `(ok, detail)` pair per read. A read is failed when its
   call exits non-zero, times out or raises `CellRuntimeError`. Then `ok` is
   false. The detail says `timed out` for a timeout, and otherwise carries
   the stderr or the exception's text. Each read has its own
   try, so a failure never stops the next read. Each detail starts with
   its read's label from criterion 1.
3. **When they run.** In `_drive_cell`, bind a flag false before the `try`,
   beside `spent` (`saffron/cell/session.py:1996`). Set it in the plan
   turn's `AgentFailed` catch when `served_nothing` is true. In the
   `finally`, straight after `_teardown("start")`, run the four reads when
   the flag is set and emit each pair as a `Teardown` event. That is before
   the export and before `cell_down`, so the cell and the proxy are both up.
4. **The event table.** Add one `FAMILIES` row in `saffron/events.py` for
   the four reads' rendered shape, citing `cell/session.py:_drive_cell` with
   kind `Teardown`. Name the four reads in `Teardown`'s docstring. Move
   `tests/test_events.py`'s row count by one from what it is at your base,
   and add one sentence to that test's docstring saying `SA-0235` moved it.

## Out of scope

- **Preflight probing from a cell started the way the agent's is.** That
  is the item's second "Done" paragraph. It conflicts with `DESIGN.md`
  §5.1, where a network probe runs in an ephemeral sibling because no cell
  exists yet. It waits on an operator decision, and the item stays open for it.
- **Any other failure path.** A turn after the plan turn's first call
  reads nothing new. Nor does a salvage, repair, review or rebuttal turn,
  or a cell that never came up.
- **Squid's `cache.log`.** It is a file inside the proxy container and not
  its container log, so `logs` does not carry it. Reading it is a later
  item.
- **A repo image with no `head`.** Core needs nothing in the repo's image
  for this, since a missing binary is a read reported as failed. Both cell
  reads fail on such an image, and the two proxy reads still land.
- **The IPv6 route table** and any resolver test such as a lookup from
  inside the cell. Both change what the cell does rather than what the host
  reads.
- **`proxy.denied_egress` and `proxy.failed_egress`.** They stay as they
  are, and `proxy.py` is forbidden here.

## Notes for the agent

**Your base.** This spec stacks on `SA-0233`, which follows `SA-0231` and
`SA-0230`. All three edit `saffron/cell/session.py`, so the line numbers
above were read before their edits. Read the file at your base before you
edit it. In `session.py`, edit only the three places step 3 names.

**Edit or new.** The two runtime functions, the new module and the flag are
new code, so every criterion declares a witness and no mutant.

**Call the runtime through its module.** Write `runtime.inspect_container`,
`runtime.container_logs` and `runtime.exec_` in `egress_report.py`, never a
name imported from `runtime`. The session tests patch the module's
attribute, and an imported name keeps the real function.

**The stub.** `_stub_the_runtime` in `tests/test_session.py` stubs every
runtime call a cell makes. Add `inspect_container` and `container_logs`
there, each returning `runtime.Completed(0, "", "")` by default. Without
them the two `PROVIDER_UNREACHABLE` tests already in that file run the
host's real runtime binary.

**Criterion 1's witness.** Use `_stub_the_runtime` and `_drive` with
`capture`, as `test_a_plan_turn_the_provider_served_nothing_ends_provider_unreachable`
does, and script its `_served_nothing()` failure. Override the two new
stubs and `exec_` so each returns its own content, and record each call's
container name, command and `timeout_s`. Have each append to `cell.order`
and `cell.preflight`. Assert each read's detail starts with its label and
holds its content. Assert the proxy reads named `proxy.PROXY_NAME`. Assert
the execs ran in `saffron-cell-<spec id>` with the exact argv step 2 gives. Assert each
read precedes `"stop"` in `cell.preflight`, and precedes the container's
removal after the turn in `cell.order`. In each served case, assert no
call reached the two new stubs and no exec named either file. The green
case scripts `[_turn(_block(_PLAN)), _turn()]`. The other five copy the
turns of `test_a_turn_that_fails_after_a_completed_turn_keeps_not_implemented`
and of `test_a_plan_turn_the_provider_served_nothing_ends_provider_unreachable`'s
second half. Run each under its own `tmp_path` subdirectory.

**Criterion 2's witness.** One plain `def` looping over the four reads and
the three failure forms. Make the failing read's stub return
`runtime.Completed(1, "", <sentinel>)`, raise
`runtime.CellRuntimeError(<sentinel>)`, or return
`runtime.Completed(124, "", "", timed_out=True, bound="wall")`. The other
three succeed.

**Where the operator reads it.** The terminal line passes a teardown
detail through `_clean` with `_DETAIL_BOUND`, 500 characters, and turns
control characters to spaces (`saffron/events.py:864`). So the terminal shows the start of each read,
and the whole log reaches the operator only in `events.jsonl`.

**Criterion 3's witness.** Copy `_as_podman`'s shape in
`tests/test_runtime.py`. Set `runtime._selected` to each of
`apple.DIALECT` and `podman.DIALECT`, and patch `runtime._call` to record
its argv and `timeout_s`. Assert the exact argv, the timeout, and that the
returned `Completed` is the one `_call` gave back.

**Witnesses red at base.** Each witness calls or stubs a function this
change adds, and criterion 1 also observes reads only the change makes.
Each fails at base and with the source reverted.

**The `prose` gate** reads every new comment and docstring, and the new
module starts at zero. Write none with an em dash, a semicolon, a
contraction, the perfect tense or a sentence over 25 words. Keep each
docstring within ten lines.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens. A prototype of this spec at `f0f7b61e`
counted 1161 changed tokens by `size_gate`, and `estimated_lines` is those
tokens over four. Its three witnesses passed, and each failed with the
source reverted. Keep comments to one or two lines and the tests close to
the shapes above.
