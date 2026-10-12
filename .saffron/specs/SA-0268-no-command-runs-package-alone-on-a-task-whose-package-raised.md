---
id: SA-0268
title: "No command runs PACKAGE alone on a `READY_FOR_REVIEW` task whose PACKAGE raised, so its green patch is packaged by hand or paid for again"
type: feature
priority: 2
depends_on: [SA-0266]
estimated_lines: 304
estimate_measured: true
touches:
  - saffron/task.py
  - saffron/cli.py
  - tests/test_cli.py
  - CLAUDE.md
  - README.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
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
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/preflight.py
  - saffron/record/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/view/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/repos/**
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 45
max_attempts: 3
max_turns: 180
risk: standard
acceptance:
  - claim: >-
      `saffron package <spec id> --repo <path>` hands `ready_task` the spec id,
      the checkout resolved from a relative `--repo`, the repo's ledger id,
      the ledger and the `out_dir` `saffron cell` uses. On a `ReadyTask` it
      takes these steps in order. It prepares the mirror at the path
      `_run_cell` uses and builds the repo's cell image. It removes any
      leftover network named `saffron-hostprobe-<spec id>`, then creates it
      with `runtime.create_network` and no subnet argument, so on
      re-verification's subnet. It lists the host's ports with
      `preflight.host_probe_ports`. It prints the line `run_one_cell` prints:
      the port count, the gateway and LAN addresses, and `tolerating` with
      the tolerated listeners, or `tolerating nothing`. It runs
      `preflight.assert_host_is_unreachable` with the base image, that
      network, those ports, `runtime.GATEWAY` and those sockets, and removes
      the network. It then calls `package()` once, with the `ReadyTask`'s
      outcome, spec and parent branch beside the mirror, the built image, the
      ledger, the `out_dir` and the token. It never reaches `run_one_cell`.
      It prints the pull request's URL and exits 0. The witness tolerates one
      listener and passes `--repo` relative to the working directory.
    witness: tests/test_cli.py::test_package_probes_the_host_then_runs_package_on_the_rebuilt_task
    wrong_versions:
      - A version that passes `cell_tag(repo)` without building the image.
      - A version that passes no token.
      - A version that drops the `ReadyTask`'s parent branch.
      - A version that probes at another subnet's gateway.
      - A version that runs no probe.
      - A version that removes the probe's network after `package()` returns.
      - A version that prints no `tolerating` part.
      - A version that prints no ports line at all.
      - A version that never removes a leftover network before creating it.
      - A version that names the network with re-verification's `saffron-pkg-` prefix.
      - A version that never resolves `--repo`.
  - claim: >-
      A `Refused` from `ready_task` prints `package:` and its reason and exits
      1. The command fetches no mirror, builds no image, creates no network
      and calls no `package()`.
    witness: tests/test_cli.py::test_package_refused_by_ready_task_exits_one_and_takes_no_host_step
    wrong_versions:
      - A version that fetches the mirror before it calls `ready_task`.
      - A version that builds the image before it calls `ready_task`.
  - claim: >-
      An unset, empty or blank `CLAUDE_CODE_OAUTH_TOKEN` exits 2 before
      `ready_task` is called. A `package()` that returns `MERGE_FAILED` exits
      1 and prints its note. A `package()` that raises exits 2 and leaves the
      task `READY_FOR_REVIEW` with no pull request, so the command takes it
      again.
    witness: tests/test_cli.py::test_package_exits_by_the_token_and_by_what_package_returned_or_raised
    wrong_versions:
      - A version that runs without the token.
      - A version that takes a token of spaces as set.
      - A version that exits 0 whatever `package()` returned.
      - A version that catches the raise and exits 1.
      - A version that records `MERGE_FAILED` on the task when `package()` raises.
  - claim: >-
      A `PreflightFailed` from `host_probe_ports` or from
      `assert_host_is_unreachable` exits 2. A leftover network of the name
      was removed first, the scratch network was created with no subnet
      argument, and it is removed again. `package()` is never called. The
      witness drives both.
    witness: tests/test_cli.py::test_package_probes_the_host_before_package_and_exits_two_on_a_refusal
    wrong_versions:
      - A version that runs no probe.
      - A version that creates the scratch network on the gate subnet.
      - A version that leaves the network behind when the probe refuses.
      - A version that reads the probe's refusal as a refused task and exits 1.
      - A version that probes after `package()` returns.
      - A version that never removes a leftover network before creating it.
---

## Context

Backlog item **b-883f74**, found in the spec loop's run 31 and again in run
32. It cites `DESIGN.md` §5.7. Every line number below was read at
`0def7c4d`. `SA-0266` adds `ready_task`, `ReadyTask` and the rebuild of
a task's outcome to `saffron/task.py`, and this spec depends on it. The
prototype was measured on top of `SA-0266`'s prototype.

**PACKAGE raised after the cell went green, twice.** `SA-0226` and `SA-0233`
ended `READY_FOR_REVIEW` with a patch, and PACKAGE's re-verify seed raised.
Their tasks 240 and 249 still read `READY_FOR_REVIEW` with a NULL `pr_url`
(read on 2026-10-10). The delegate packaged both by hand, as #745 and #780,
and PACKAGE's re-verification never judged either tree. `run_task` writes
`READY_FOR_REVIEW` and re-raises on any raise out of `package()`
(`saffron/task.py:654-668`). Under `saffron cell`, the dispatch's
`except Exception` then exits 2 (`saffron/cli.py:302-309`).

**No subcommand runs PACKAGE.** The subcommands are `replay`, `cell`,
`queue`, `batch`, `draft`, `reconcile`, `watch`, `fold`, `migrate`, `chains`
and `serve` (`saffron/cli.py:110-236`). `SA-0264` adds `adopt`.

**`package()` has one production call.** It is
`package_phase.package` inside `run_task` (`saffron/task.py:638-639`). The `one-task-driver` rule's note sends
task-driving code into `saffron/task.py` (`.saffron/rules/one-task-driver.yml`).

**Re-verification starts cells, and N1's probe is what admits a cell.**
`reverify` creates a network per cell it starts with `runtime.create_network`
(`saffron/phases/package.py:534-539`). That call makes an `--internal`
network on the default subnet (`saffron/cell/runtime.py:311-320`), whose
gateway is `GATEWAY` (`saffron/cell/runtime.py:196`). An
`--internal` network still routes to the host gateway
(`saffron/preflight.py:8-10`, `DESIGN.md:1435`). Every run reports what it
tolerated, and the line ends `; tolerating nothing` when nothing is
(`docs/appendices/H-what-v0-found.md:181-185`). `DESIGN.md:649` says N1's
host-binding probe gates whether a cell is started at all. `run_one_cell`
runs it before any cell: it lists ports with `host_probe_ports` and asserts
with `assert_host_is_unreachable` per network (`saffron/cell/session.py:1095-1111`).
`run_task` reaches `package()` only after `run_one_cell` runs the probe. A
command that calls `package()` alone has had no probe in its invocation.

**The token.** `_run_cell` refuses an unset or blank
`CLAUDE_CODE_OAUTH_TOKEN` before anything else (`saffron/cli.py:457-461`).
PACKAGE's credential refusal scans the patch for that literal value
(`saffron/phases/package.py:278-294`).

**The mirror path.** `_run_cell` prepares the mirror at
`<home>/mirrors/<checkout name>-<digest>.git`, the digest being the first
twelve hex characters of the resolved checkout path's sha256
(`saffron/cli.py:453-476`).

**The exit code** for a task state is `CELL_EXIT`'s (`saffron/cli.py:78-97`).
The dispatch's `except Exception` turns any raise into exit 2
(`saffron/cli.py:302-309`).

## Problem

Add `saffron package <spec id> --repo <path>`, with `--repo` defaulting to
the working directory. It runs PACKAGE alone, re-verification included, on
the task `ready_task` rebuilds. It runs no agent and never reaches
`run_one_cell`. Re-verification's cells are the only cells it
starts, and N1's probe runs before them.

**`package_ready_task` in `saffron/task.py` takes every step.** It calls
`ready_task` and returns its `Refused` untouched. On a `ReadyTask` it
prepares the mirror with `preflight.prepare_mirror` and builds the image
with `repo_image.build_cell_image(repo)`. It then runs N1's probe and calls
`package_phase.package`, returning its result. `run_task` and it are then
`package()`'s only production callers, both in `saffron/task.py`.

**The probe** names its network `saffron-hostprobe-<spec id>`, a prefix no
other network uses. Re-verification's networks take `saffron-pkg-`
(`saffron/phases/package.py:530-532`). It first removes a leftover network
of that name. Cell setup calls `remove_network` the same way before it
creates its own networks (`saffron/cell/session.py:1057-1060`). A killed run leaves one, and
`create_network` then raises. Inside a `try`, it creates the network with
`runtime.create_network(name)` and no subnet argument, so on the subnet
re-verification's networks take. Its `finally` removes the network before
`package()` runs. A failed create is then safe to clean up, since
`remove_network` returns its result and raises nothing
(`saffron/cell/runtime.py:365-366`). Inside the `try`, it calls
`preflight.host_probe_ports()`. It prints `describe` of a `Preflight` with
step `ports`, whose detail is the one `run_one_cell` builds: the port count,
the gateway and `preflight.probe_addresses(runtime.GATEWAY)`, and
`tolerating` with the tolerated names or `nothing`
(`saffron/cell/session.py:1096-1106`). It then calls
`preflight.assert_host_is_unreachable(repo_image.BASE_TAG, name, ports,
runtime.GATEWAY, sockets)`. A `PreflightFailed` propagates, and `main` exits
2.

**`saffron/cli.py` only adapts.** It adds the parser and a handler. The
handler checks the token first, exactly as `_run_cell` does, and passes the
stripped value. It resolves `--repo`, reads the repo's ledger id from
`package_phase.real_remote`, and computes the mirror path with
`_mirror_path` (`saffron/cli.py:1611-1617`). It calls `package_ready_task` and prints `package:` and the reason on
a `Refused`, exiting 1, as `adopt`'s refusals do. Otherwise it prints the
spec id, the state and the URL or note, as the `print` after PACKAGE does
(`saffron/task.py:671`), and returns `CELL_EXIT`'s code.

**The documentation, as cell work.**

- `CLAUDE.md`'s command list: add one line for the command beside
  `reconcile` (`CLAUDE.md:62`).
- `CLAUDE.md:79`: the sentence naming `saffron cell` and `saffron batch` as
  needing `CLAUDE_CODE_OAUTH_TOKEN` names `saffron package` too.
- `README.md:71-72`: the token is needed by `cell`, `batch` and `package`.
- `README.md:91`: `saffron package` runs inside the two images as well.
- `README.md`'s usage: add a short paragraph and block beside
  `reconcile`'s (`README.md:131-137`), with the token scoped to the
  invocation as the `cell` block shows it.

## Out of scope

- **The rebuild.** `SA-0266` owns `ready_task`, its refusals and every field
  it rebuilds. Do not edit them here.
- **b-f582ee's second half.** A seed failure before REVIEW ends a task
  `ORPHANED`, which `ready_task` refuses. Nothing prints this command's name
  when PACKAGE raises. That half stays open.
- **The batch** offers a task whose PACKAGE raised a `CellRuntimeError` again
  and reruns the cell (`saffron/batch.py:286`, `:741`). Leave that.
- **`driver.py`'s `size` and `stack`** (b-2247dd). The operator edits them
  by hand.
- **Protected text.** The operator owns `DESIGN.md` §5.7's sentence on
  agent subjects and `CLAUDE.md`'s Layout line for `saffron/task.py`.

## Notes for the agent

**Every criterion is new code.** Neither `package_ready_task` nor the
subcommand exists at base. So each criterion declares a witness and no
mutant, and `witness` reports `skip` for each. At base `package` is not a
subcommand, so `main` raises `SystemExit` from argparse and every witness
fails.

**The seams the witnesses replace.** Call every host step through its
module, so a monkeypatch reaches it: `ready_task` as a global of
`saffron.task`, `preflight.prepare_mirror`, `preflight.host_probe_ports`,
`preflight.assert_host_is_unreachable`, `repo_image.build_cell_image`,
`runtime.create_network`, `runtime.remove_network` and
`package_phase.package`, and `preflight.probe_addresses`, which reads the
host's LAN address. The witnesses replace each of these and
`saffron.task.run_one_cell`, which raises. They replace `ready_task` with a
stub returning a real `ReadyTask`, so this spec's tests seed no task
directory. That is `SA-0266`'s. They `monkeypatch.chdir` to the checkout's
parent and pass `--repo` as a relative path.

**The checkout** is a `git init` directory whose `origin` is a GitHub URL
added with `git remote add`. `real_remote` reads it and nothing fetches it.
Seed the repo row with that URL through `_seed_repo` and one task through
`_seed_task` (`tests/test_cli.py:1969-1989`). Use the seeded task's id as the
stub outcome's `task_id`, so criterion 3's raise is checked against a real
row.

**Four residuals, one line each.**

- The literal-token scan uses this invocation's token. After a rotation it
  is not the cell's, and the `sk-ant-oat` shape still catches a leaked one
  (`saffron/phases/package.py:66`).
- `assert_base_objects` runs before any fetch (`saffron/phases/package.py:687`).
  A mirror garbage-collected since the cell, or made fresh for another checkout path,
  can lack a stacked `tree_base`. It raises, and the command exits 2.
- The probe adds one ephemeral container on the base image per invocation,
  as `run_one_cell`'s does.
- The scratch network shares `10.88.0.0/24` with `saffron-cells`
  (`saffron/cell/session.py:1897`). While a cell is up, its create raises and
  the command exits 2, as re-verification already does.

**Imports.** Import nothing at a witness module's top that the change adds.
The reverted run would then be a collection error, which `revert` reads as
`skip`.

**Wrong versions.** Each criterion lists the ones its witness must kill. A
prototype's witnesses killed all 24 on 2026-10-10 and passed with the
change. Do not run them yourself.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** No path in `touches` is in `elevate_on`, so the diff is
`standard` and `size` is advisory. The prototype measured 1215 tokens with
`size_gate`'s counter against the `feature` ceiling of 3000. The tests were
869 of them, and the documentation 63. `estimated_lines` is that count over
four.
