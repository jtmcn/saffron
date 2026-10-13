---
id: SA-0289
title: Preflight passes a cell runtime whose image store lacks the proxy or the base image, so a batch asks a registry for them and leaves a task row
type: bug
priority: 1
depends_on: [SA-0271, SA-0270]
estimated_lines: 225
estimate_measured: true
touches:
  - saffron/cell/runtime.py
  - saffron/preflight.py
  - tests/test_preflight.py
  - tests/test_cli.py
  - tests/test_runtime.py
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
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/cell/session.py
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - saffron/repos/**
  - tests/conftest.py
budget_usd: 24
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      `check_readiness` asks the selected cell runtime's image store for
      the proxy image, `proxy.PROXY_TAG`, and the base image,
      `image.BASE_TAG`. It runs `image inspect` once per tag and makes no
      other runtime call. It refuses at the step `images` when either
      answer is nonzero. A clean miss is a nonzero exit, not timed out,
      whose stderr holds `image not found`. For each clean miss, and for
      no other image, the detail names a build command. Each reads
      `<binary> build -t <tag> -f <file> .`, with the selected runtime's
      binary. The proxy's file is `images/proxy.Dockerfile`, and the
      base's is `images/cell-base.python.Dockerfile`. The detail names
      the Saffron checkout's absolute root as the directory to run them
      from. Any other nonzero answer refuses with no build command. Its
      detail carries the runtime's stderr, or says the ask timed out.
      The witness drives both runtimes over four stores of clean misses.
      One holds neither image, one the proxy alone, one the base alone
      and one both. It then drives a nonzero answer with other stderr, a
      timed out answer, a runtime that cannot be executed, and an
      unknown `SAFFRON_CELL_RUNTIME`. Each of the last two returns a named
      refusal and never raises.
    witness: tests/test_preflight.py::test_readiness_refuses_a_store_missing_the_proxy_or_the_base_and_names_each_build
    wrong_versions:
      - Only the proxy is asked for, so a store lacking the base passes.
      - The detail names only the first missing image, so a store holding neither names one command.
      - The build command spells apple's binary under podman.
      - A nonzero answer that is not a clean miss counts as present.
      - A `CellRuntimeError` from the runtime escapes `check_readiness` instead of returning a named refusal.
      - A pull of each tag runs beside its `image inspect`.
      - Every nonzero answer is told to build, so a stopped runtime prints build commands.
      - A timed out answer is read as a clean miss, or its detail does not say it timed out.
      - The detail gives the commands with no directory to run them from.
      - The selected runtime is read before the check's `try`, so an unknown `SAFFRON_CELL_RUNTIME` raises out of `check_readiness`.
  - claim: >-
      A batch that readiness refuses for a missing proxy image mints no
      task row. The witness runs `saffron batch` and `saffron batch
      --stack`, each with the real `check_readiness`, over a store lacking
      the proxy image alone. Its queue holds one spec. That spec's spec
      review and its task are stubbed to raise `CellRuntimeError`, as
      batch 23's proxy start did, and the task stub mints its row first.
      The stack form's mint is the real one. Each form exits 2,
      closes its batch row `INFRASTRUCTURE` and prints the proxy's build
      command. Neither writes a `tasks` row.
    witness: tests/test_cli.py::test_a_batch_whose_store_lacks_the_proxy_is_refused_and_mints_no_task_row
    wrong_versions:
      - Readiness passes on the missing proxy, so the stack batch mints the spec's task before its spec review raises.
      - The image check moved into the task after its mint, so the batch closes but leaves a `GATE_ERROR` or `ORPHANED` row.
      - The refusal is printed without the proxy's build command.
---

## Context

Backlog item **b-1c20da**, filed from the spec loop's run 35. It cites
`DESIGN.md` §5.1.2. Every line number below was read at `cf3db797`.

**Batch 23 met an empty image store.** Preflight passed. The proxy's
start then asked Docker Hub for `saffron/proxy` and got a 401. The batch
exited 2 at $0, and left a `GATE_ERROR` task row for `SA-0260`.

**Readiness asks nothing about images.** `check_readiness` runs auth,
mirror, origin, default branch, policy and disk, in that order
(`saffron/preflight.py:456-546`). Its one success return is at
`saffron/preflight.py:546`.

**The proxy is never built by a task.** `PROXY_TAG` is
`saffron/proxy` (`saffron/cell/proxy.py:14`). `start_proxy` hands
`PROXY_TAG` to `runtime.run_detached` (`saffron/cell/proxy.py:59-64`).
No other module in `saffron/` names that tag, and none builds it.
CLAUDE.md names the hand build.

**The base image is built, but only after its first use.** Inside
`cell_up`, `proxy.start_proxy` runs at `saffron/cell/session.py:1095`.
The upstream probe then runs from `image.BASE_TAG` at `:1098-1100`.
Only after that does `build_cell_image` rebuild the base, at `:1107`.
`BASE_TAG` is `saffron/cell-base:python` (`saffron/repos/image.py:17`).
`build_base_image` builds that tag (`saffron/repos/image.py:61-66`).
`build_base_image()` is the first call in `build_cell_image`
(`saffron/repos/image.py:78`). So on an empty store the first cell
fails at the probe too, even with the proxy present. A spec review's cell and a draft's cell both go
through `cell_up` (`saffron/end_review.py:597`, `:615`).

**Where `SA-0260`'s row came from.** The ledger holds task 278 for
`SA-0260` in run 278, on batch 23, at `GATE_ERROR`. Its two
`spec_reviews` rows are both `error`, each carrying the proxy's
`CellRuntimeError` and the registry's 401. The stack batch minted that
task at `saffron/batch.py:571`. The call `review(candidate, pred,
**kwargs)` raised (`saffron/batch.py:601`). The handler set the row
`GATE_ERROR` (`saffron/batch.py:611`). A batch builds `stack_mint` and its
runner only once `readiness.ok` holds (`saffron/cli.py:1965`, `:2049`).
So a readiness refusal reaches neither, and closes the path.

**A refused batch prints its step and detail.**
`batch: readiness failed at {step}: {detail}` (`saffron/cli.py:2156`).
A refused draft prints `draft: readiness failed at` the same way
(`saffron/cli.py:1318`).

**The runtime seam names no product.** `runtime.py` reaches each binary
through `dialect().binary`. `inspect_container` and `container_logs`
each build one argv and return `_call`'s `Completed`
(`saffron/cell/runtime.py:625-635`). The runtimes package docstring
admits only what the two runtimes were measured to spell differently
(`saffron/cell/runtimes/__init__.py:1-17`).

**What the delegate measured, on apple/container 1.3.0.**
`container image inspect saffron/proxy` exits 0 and prints JSON when the
image is present. `container image inspect saffron/no-such-image:latest`
exits 1 and prints `Error: image not found: saffron/no-such-image:latest`
on stderr. Podman is not installed on that host, so its spelling is
unmeasured.

## Problem

Add a readiness check named `images`. It runs last, after disk headroom.
It asks the store for `saffron/proxy` and `saffron/cell-base:python`,
read from `proxy.PROXY_TAG` and `image.BASE_TAG`. Exit 0 means present.
When either answer is nonzero, return `Readiness(False, "images",
detail)`.

Tell a clean miss from a store that could not answer. A clean miss is a
nonzero exit, not `timed_out`, whose stderr holds `image not found`. That
is apple's measured text. A clean miss gets a build command, with the
binary spelled from the selected runtime. The detail names the directory
to run the commands from. That is the Saffron checkout's absolute root,
which `saffron/repos/image.py:18` already holds as `_SAFFRON_ROOT`. A
batch's `--repo` can be any target repo, so a relative command alone
would send the operator to the wrong tree.

Any other nonzero answer gets no build command. A timeout from `_call`
returns 124 with `timed_out` set (`saffron/cell/runtime.py:280-287`).
Its detail says the ask timed out. Every other answer's detail carries
the runtime's stderr, such as a stopped runtime's error.

Ask through `runtime.py`. Add one function beside `inspect_container`
that runs `image inspect <tag>` through `_call` and returns its
`Completed`. Build the argv from `dialect().binary`, as its neighbours
do. Add no `Dialect` member. Its comment says the apple spelling is
measured and the podman spelling is inferred and unmeasured.

A `CellRuntimeError` from that call becomes a refusal at `images`
carrying its text. So does one from `dialect()`. For an unknown
runtime name, `raise CellRuntimeError(` runs at
`saffron/cell/runtime.py:63`.
So the check reads the selected runtime only inside its `try`. A batch
meets that raise earlier, in `runtime.unattended_refusal`
(`saffron/cli.py:1901`). The draft path calls
`preflight.check_readiness(` with no such guard (`saffron/cli.py:1310`). The disk check does the same with
`except RuntimeError as exc:` (`saffron/preflight.py:537-538`).

Update the two docstrings that list readiness's order
(`saffron/preflight.py:15-17`, `:465-467`) to name the image check last.

Three tests in `tests/test_preflight.py` reach the success return. They
are `test_readiness_runs_its_checks_in_the_order_4_2_1_gives` (`:510`),
`test_readiness_and_prepare_mirror_run_the_same_three_steps_in_the_same_order`
(`:823`) and `test_a_passing_readiness_carries_the_base_it_pinned`
(`:881`). Make each stub the new check. The first then asserts it runs
after disk.

## Out of scope

- **`saffron cell`.** It calls `prepare_mirror` alone, never
  `check_readiness` (`saffron/preflight.py:15-22`). An attended cell meets
  the same 401.
- **The `--build-arg BASE_IMAGE=...` form.** A host with no registry adds
  it by hand, as CLAUDE.md says (§5.1.2). The printed command is the
  default form.
- **The repo's cell image.** `build_cell_image` builds it from the
  repo's `.saffron/Dockerfile` (`saffron/cell/session.py:1107`). No cell
  runs it before that line.
- **A task row left by any later infrastructure failure.** A spec review
  that raises after its mint still sets `GATE_ERROR`, as §4.2.1 says. This
  spec stops the image case before the mint.
- **Building a missing image.** Readiness names the command and builds
  nothing.

## Notes for the agent

**Both criteria are new code**, so each declares a witness and no mutant,
and `witness` will report `skip`. No readiness check for images exists at
base.

**At base each witness fails in its body.** Neither imports a name the
change adds. The readiness witness sees no `image inspect` call. The
batch witness finds one `tasks` row per form, measured on a prototype.

**Answer every runtime call through `runtime._call`.** It is the one
choke point, so a stub there sees the argv and decides each answer. Set
`runtime._selected` per runtime, as
`test_a_containers_state_and_log_are_read_through_the_selected_runtime`
does (`tests/test_runtime.py:461-482`). An unmarked test that execs a
runtime binary raises `HostToolExecInTest`, a `BaseException`
(`tests/conftest.py:16`, `:64-92`). So every test reaching the new check
must stub it.

**The readiness witness** reuses `_stub_prepare`
(`tests/test_preflight.py:409`) and stubs `disk_headroom_ok` to pass. For
each runtime and store it asserts the recorded argvs equal exactly the
two `image inspect` argvs. It asserts `ok`, `step` and which build
commands the detail holds. It asserts the detail holds the root, read in
the test as `image.BASE_DOCKERFILE.parents[1]`. Then it drives three
answers that are not clean misses. One is exit 1 with other stderr. One
is `Completed(124, "", "", timed_out=True)`. One is a `_call` raising
`CellRuntimeError`. The first two hold no `build -t`. Last, it sets
`runtime._selected` to `None` and `SAFFRON_CELL_RUNTIME` to an unknown
name with `monkeypatch.setenv`.

**The batch witness** runs `main` once per form, each with its own
`--home`. It sets `CLAUDE_CODE_OAUTH_TOKEN` with `monkeypatch.setenv`.
The batch passes `token=os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")`
(`saffron/cli.py:1929`). An unset token refuses at auth, before the
image check (`saffron/preflight.py:484-486`). The default `validate_token: Callable[[str], TokenCheck] =
validate_claude_token` is bound at definition
(`saffron/preflight.py:463`). So wrap the real function in a
lambda that passes a valid `validate_token`, and set that as
`cli.preflight.check_readiness`. Stub the steps before disk as
`_stub_prepare` does. Fake `_resolve_queue` with `_fake_batch_resolution`
holding one candidate (`tests/test_cli.py:4274`). Stub `cli._stack_review`
to return a review that raises `CellRuntimeError`. Stub `cli.run_task` to
mint a run and a task on the ledger it is handed, then raise
`CellRuntimeError`. Leave `cli._stack_mint` real. That reproduces batch
23 on both forms. Read the `tasks` count and the latest
`batches.status` from each ledger.

**The batch witness drives the proxy alone.** A missing base reaches the
batch through the same refusal, and only the readiness witness drives
it.

**Two parents land first.** `SA-0270` and `SA-0271` share
`saffron/cell/runtime.py` with this spec, and `SA-0271` shares
`saffron/preflight.py` too. `SA-0271` lands last, so it leads
`depends_on`. Read both files at your base. `SA-0275`, `SA-0278`,
`SA-0279` and `SA-0282` overlap only in `tests/test_cli.py` or
`tests/test_runtime.py`. Those are left to the scheduler's refusal of a
spec that overlaps an open pull request. The line numbers
above are `cf3db797`'s, not your base's. Neither parent names
`check_readiness` or `proxy.PROXY_TAG`.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**`saffron/cell/**` is in `elevate_on`,** so this task runs `elevated`
and `size` blocks.

**Podman's miss text is unmeasured.** If it lacks `image not found`,
a podman miss refuses with its stderr instead of a build command. It
still refuses.

**Size.** A prototype measured 857 changed tokens with `size_gate`,
against the `bug` ceiling of 1300. It held the runtime function, the
readiness check, both witnesses and the three test stubs. Those suites
passed on it. It did not hold the docstring edits. `estimated_lines` is
that count over four, plus a margin for those.
