---
id: SA-0272
title: A change whose subject is history never runs against a real ledger, so a projection that drops 75 of 76 merged tasks passes every witness
type: feature
priority: 2
depends_on: [SA-0285, SA-0262, SA-0271]
consumes:
  - saffron/ledger.py:snapshot
  - saffron/cell/worktree.py:extra_mounts
  - saffron/intake.py:History
estimated_lines: 394
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/cell/worktree.py
  - tests/test_history_run.py
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
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/cell/runtime.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/scheduler.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_cli.py
budget_usd: 36
max_attempts: 3
max_turns: 190
acceptance:
  - claim: >-
      `session.run_history` enters a Gate-only cell through `critic_cell`,
      with `network=None`, the repo's `thread_env` alone as its env, and
      read-only bind mounts as its `extra_mounts`. One sits at
      `worktree.HISTORY_MOUNT`. Its source is
      `session.HISTORY_SOURCE_ROOT` joined with the spec id, a directory
      that holds the ledger's snapshot and is never the live ledger's
      directory. With `batches: true` a second sits at
      `worktree.BATCHES_MOUNT`, and its source is `out_dir` itself, never a
      copy. With `batches` false there is no second mount. Both execs in the
      cell go through `runtime.exec_`, from `worktree.WORKTREE_MOUNT`, with a
      timeout of 600 seconds. The command sees `SAFFRON_HISTORY_HOME`
      naming a home under `worktree.STATE_MOUNT`. That home holds a
      writable copy of the mount's `ledger.db`, with the batch tree linked
      read-only as `v0` under `batches` when it is mounted. A command that
      writes to its ledger leaves every file of both mount sources
      unchanged. The result carries the exit code, stdout and stderr. The
      snapshot's directory is gone once `run_history` returns, and also
      after `critic_cell` raises. The witness drives `batches` true and
      false, and a `critic_cell` that raises.
    witness: tests/test_history_run.py::test_the_history_command_reads_a_writable_copy_and_never_writes_the_mount
    wrong_versions:
      - The live ledger's own directory bind-mounted read-only, with no snapshot.
      - The snapshot kept under `out_dir`, beside the task's gates.
      - "`SAFFRON_HISTORY_HOME` names the mount itself, so the command's first write lands in the mount's source."
      - The history mount declared without `readonly`.
      - "`batches` ignored, so the batch tree is never mounted."
      - The batch tree mounted whatever `batches` says.
      - The batch tree copied on the host and the copy mounted.
      - The snapshot removed after the cell closes but outside a `finally`, so a raise leaks it.
      - The command's exec left at `exec_`'s default timeout of 900 seconds.
      - The cell's env built with `cell_env`, so it carries a proxy address.
      - The result's stderr dropped.
  - claim: >-
      Each of the result's two streams keeps its first
      `session.HISTORY_OUTPUT_CHARS` characters. Past that, it ends with a
      note naming how many characters were cut. A stream within the bound
      is kept whole. The witness drives stdout and stderr over the bound by
      different counts, and both within it.
    witness: tests/test_history_run.py::test_each_history_stream_is_cut_at_the_bound_and_says_how_much_it_cut
    wrong_versions:
      - The last characters kept instead of the first.
      - The stream cut with no note of how much went.
      - Only stdout bounded.
      - The note names the stream's whole length rather than the count cut.
  - claim: >-
      For a spec declaring `history`, REVIEW runs the in-cell copy and then
      the command, each once, in the Gate-only cell that carries the history
      mount, before any lens. Every lens's system prompt carries the
      command, both streams, and either `exited` with the exit code or
      `timed out`. `history.json` in the task directory records the
      command, the exit code, `timed_out` and both streams. A spec declaring
      no `history` gets no history mount, no `history.json` and no
      `History run` text in any lens prompt. The witness drives a run that
      exits 3, a run that times out, and a spec with no `history`.
    witness: tests/test_history_run.py::test_every_lens_reads_the_history_run_and_the_task_dir_records_it
    wrong_versions:
      - The history run reaches only the first lens's prompt.
      - The lens prompt names the exit code of a timed-out run and never says it timed out.
      - No `history.json` written.
      - "`critic_cell` takes `extra_mounts` and never passes it to `prepare_worktree`."
  - claim: >-
      The in-cell copy runs as its own exec, before the command's. When it
      exits non-zero or times out, the command never runs. `history.json`
      then records `started` as false and the copy's stderr. Every lens's
      prompt says the history run did not start and carries that stderr,
      and none says `exited`. The witness drives a copy that exits 1 with
      `no space left on device` on stderr.
    witness: tests/test_history_run.py::test_a_history_run_whose_copy_fails_never_runs_the_command_and_says_so
    wrong_versions:
      - The command runs after a failed copy.
      - The lens section reads `exited 1` for a run whose copy failed.
      - The copy's stderr dropped from the result.
---

## Context

Backlog item **b-a8270f**, which cites `DESIGN.md` §4.1 and §5.4. Found in
the spec loop's run 8 on 2026-09-19, reviewing #355 (`SA-0107`). That
projection looked up each task's spec under `.saffron/specs/` and missed
`.saffron/specs/done/`. Over a copy of the real ledger it left out 75 of 76
merged tasks, and every witness in the cell passed. Four spec reviews and
three lenses missed it. A person found it by running the module over a
backup of `~/.saffron/ledger.db`. That lookup is fixed now
(`saffron/projection.py:144`). The class of defect is not. A cell has no
ledger but the one its own task writes, so projection, reporting,
`reconcile` and `watch` meet no real history in any gate.

**What the parent leaves for you.** `SA-0285` adds the `History` model and
`Spec.history`, `CellSpec.history`, `Ledger.snapshot`, and `extra_mounts`
on `prepare_worktree`. Read each at the tree base before you start.

Every line number below was read at `bc879e2c`. `SA-0262` and `SA-0271`
edit `saffron/cell/session.py` first, so read it at the tree base too.

**The Gate-only cell is `critic_cell` with `network=None`.** It is defined at
`saffron/cell/session.py:1335`. With no network it makes its own, named
`saffron-gate-net-<spec>` (`:1386-1393`). It seeds the worktree through
`worktree.prepare_worktree` (`:1419`), then calls
`_apply_and_commit_patch(container, patch)` (`:1432`).
`_gate_cell_suite` (`:1452`) and `probe_findings` (`:1506`) enter it with
`env=dict(thread_env)`, the repo's gate env and nothing else.

**`runtime.exec_` defaults its timeout.** Its `timeout_s` defaults to 900
seconds (`saffron/cell/runtime.py:470`).

**REVIEW builds every lens prompt from one body.** In `_drive_cell`, REVIEW
first computes the gate table in a Gate-only cell, through
`_gate_cell_suite` (`saffron/cell/session.py:2808`).
For a clean comparison it sets the probe budget (`:2869`). It then enters
the critic cell inside a `try`. Its handler
`except CriticPatchRejected as rejected:` (`:2948`) ends the task on a
rejected patch. `review.run_review` gets
`spec_body=spec.body` (`:2900`) with the criteria appended, and
`lens_prompt` (`saffron/phases/review.py:191`) puts that body in every
lens's system prompt. The gate table is
written beside it as `lens-gates.json` (`saffron/cell/session.py:2844`).

**The task's bind sources sit under `out_dir`.** `task_dir.mkdir` makes the
task directory (`saffron/cell/session.py:1915`).
`export_saffron_dir` writes the gates under it (`:1916`). So `out_dir` holds the task's own directory. A copy of
`out_dir` placed under it would copy into itself.

**`Ledger` writes when it opens.** `Ledger.__init__` makes the parent
directory, runs `PRAGMA journal_mode=WAL` (`saffron/ledger.py:393`) and
runs the schema script. Measured on the host on 2026-10-11: opening a
`Ledger` on a read-only file in rollback-journal mode raises
`attempt to write a readonly database`. So a command cannot open the
read-only mount's ledger itself. It needs a writable copy.

**The CLI finds history under `--home`.** `--home` (`saffron/cli.py:101`)
defaults to `DEFAULT_HOME` (`:74`), the `.saffron` directory in the
user's home. The ledger is `ledger.db` under it (`:268`). The batch tree is
`batches`, then `v0` (`:243`). The cell image syncs with `--no-install-project`
(`.saffron/Dockerfile:25`), so no `saffron` script is expected there. That
is reasoned, not measured. `python -m saffron.cli` from the worktree needs
no script.

**Gate-only, never host-side.** `reverify`'s docstring states the rule as
`Never host-side` (`saffron/phases/package.py:497`). Exec'ing
model-authored code on the host is the one thing the control plane never
does. A history command is the patch's own code.

## Problem

A spec can say its subject is history, and nothing runs it against any.
Build that path, from the parent's field to every lens.

1. **The mounts.** Add `extra_mounts`, empty by default, to `critic_cell`,
   and pass it to `prepare_worktree`. Add `worktree.HISTORY_MOUNT`,
   `"/history"`, and `worktree.BATCHES_MOUNT`, `"/history-batches"`.
2. **The run.** Add `session.run_history`, keyword-only: `spec`, `repo`,
   `mirror`, `gates_dir`, `thread_env`, `patch`, `ledger`, `out_dir`,
   `created` and `note`. Add `session.HISTORY_SOURCE_ROOT`, set to
   `Path.home() / ".saffron" / "history"`. The source directory is that
   root joined with the spec id, outside `out_dir` and outside TMPDIR. A
   bind from TMPDIR is unmeasured on apple/container.
   - On the host, write `ledger.db` into the source with `Ledger.snapshot`.
   - Enter `critic_cell` with `network=None` and `env=dict(thread_env)`.
     Bind the source read-only at `HISTORY_MOUNT`. With `batches`, also
     bind `out_dir` itself read-only at `BATCHES_MOUNT`. Never copy the
     batch tree.
   - In the cell, run two execs through `runtime.exec_` from
     `WORKTREE_MOUNT`, each with a timeout of 600 seconds. The first copies
     the mount's `ledger.db` to a writable home under
     `worktree.STATE_MOUNT`. When the batch tree is mounted, it also links
     it into the home as `v0` under `batches`. The second runs only when
     the first exited 0 and did not time out. It runs the command with
     `SAFFRON_HISTORY_HOME` naming that home.
   - Remove the source in a `finally`.
   - Return a dict with `command`, `batches`, `started`, `exit_code`,
     `timed_out`, `stdout` and `stderr`. When the copy failed, `started` is
     false and the other fields are the copy's. Bound each stream at
     `HISTORY_OUTPUT_CHARS`, 20000. Keep the first characters, and end a
     cut one with a note naming how many went.
3. **The lenses.** REVIEW calls `run_history` for a spec whose `history`
   is set. The call comes after a clean gate comparison and before the lens
   critic cell, inside the same `try` as that critic cell. Write its result
   to `history.json` in the task directory. Append a `## History run`
   section to the `spec_body` every lens gets. It names the command and
   says `exited <code>`, `timed out`, or that the history run did not
   start. It then gives stdout and stderr. A spec with no `history` gets
   no history text in the body at all, and no history cell.

## Out of scope

- The spec loop's step 1b question, "does the code need `done/`?". That
  half of the item is skill text and lands by hand.
- `DESIGN.md` §3.2 and §5.5, `CONTEXT.md`'s History run entry and
  `docs/agents/issue-tracker.md`. They are written by hand on this spec's
  own branch.
- REBUT's prompt (`saffron/cell/session.py:3146`), the PR body and the
  events log. They do not show the history run.
- A history cell that cannot start. `critic_cell` raising
  `CellRuntimeError` ends the task as `_gate_cell_suite`'s raise does today.
- Any spec declaring `history`. None can until this lands
  (`DESIGN.md` §3.2, "A spec cannot introduce the frontmatter it is written
  in").

## Notes for the agent

Every criterion here witnesses new code, so none declares a `mutant`, and
the `witness` gate will report `skip` for each. That is honest, not
missing.

Import `History` inside each test body, never at module scope. Reach
`run_history`, `HISTORY_MOUNT` and the other names you add through their
modules at call time. `revert` re-runs the witnesses with your source
files reverted. A module-scope import of a name you add makes that run a
collection error, which `revert` reads as `skip`.

Mark the 600-second and 20000-character bounds as reasoned, not measured,
in the comment beside each. No history command has run in a cell yet.

`tests/test_history_run.py` is a new file. It imports `_drive`,
`_stub_the_runtime`, `_spec`, `_turn`, `_block`, `_PLAN` and
`_GATE_CONTAINER` from `tests/test_session.py`, as
`tests/test_probe_findings.py` imports from it. Do not edit
`tests/test_session.py`.

**The unit witness for `run_history`** sets `session.HISTORY_SOURCE_ROOT`
to a directory under `tmp_path`. It stubs `session.critic_cell` with a
context manager that records its keywords and yields a fixed container,
or raises when the test asks it to. It stubs `runtime.exec_` to record
`workdir` and `timeout_s` and run the argv on the host. `/work` exists only
in a cell. So the stub runs every exec in one host directory whatever
`workdir` says. The test asserts the recorded `workdir` instead.
- The stub rewrites `worktree.STATE_MOUNT` to a host state directory, one
  per cell entered. It rewrites each mount's target to that mount's
  source. A target is rewritten only as a whole path, never inside a
  longer one, so `/history` inside a state path stays as it is.
- With no `extra_mounts` keyword, the stub finds no history mount and the
  test fails. That is the default it must not hide.
- The command is a Python script file run with `sys.executable`. It reads
  `SAFFRON_HISTORY_HOME`, sets WAL mode on its `ledger.db`, writes one
  table, and prints the task count. It prints one batch-tree file's text
  or `None`, and the real path of its home, and exits 3 with a marker on
  stderr.
- The stub hashes every file of every mount source before and after each
  exec. `_gate_cell_suite`'s docstring says the tests in a Gate-only cell
  execute as `root` (`saffron/cell/session.py:1469`), so a `chmod` cannot
  stand in for a read-only mount. The hash is what catches a write.

**The wiring witnesses** each drive `_drive` under their own `tmp_path`
subdirectory, with `session.HISTORY_SOURCE_ROOT` set under it. They
override `runtime.exec_` after `_stub_the_runtime`. The exec whose argv
mentions the history command in any argument returns a scripted
`runtime.Completed`. The one that mentions `worktree.HISTORY_MOUNT` and
not the command is the copy, and returns its own. Every other exec gets a
clean `runtime.Completed(0, "", "")`. The lens prompts are
`cell.system_prompts[2 : 2 + len(review.LENSES)]`, after the plan and
implement turns. The history mount is read from the `extra_mounts` keyword
of `cell.worktrees`.

`estimated_lines` is a prototype's measured diff over `SA-0285`'s: 1574
changed tokens over `saffron/cell/session.py`, `saffron/cell/worktree.py`
and `tests/test_history_run.py`. It holds every criterion's code and
witness. It holds none of `SA-0285`'s work and none of the `DESIGN.md`,
`CONTEXT.md` or backlog edits.

Both ledger copies are deliberate. The host snapshot is consistent while
the task writes the live ledger. The in-cell copy exists because
`Ledger.__init__` sets WAL mode on open. The in-cell copy of an 880 MB
ledger onto the state volume is unmeasured in a real cell. Mark it with a
`ponytail:` comment naming that ceiling.
