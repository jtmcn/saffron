---
id: SA-0272
title: A change whose subject is history never runs against a real ledger, so a projection that drops 75 of 76 merged tasks passes every witness
type: feature
priority: 2
depends_on: [SA-0262, SA-0268, SA-0271]
estimated_lines: 472
estimate_measured: true
touches:
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/cell/session.py
  - saffron/cell/worktree.py
  - tests/test_intake.py
  - tests/test_ledger.py
  - tests/test_task.py
  - tests/test_worktree.py
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
  - saffron/cli.py
  - saffron/scheduler.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_cli.py
budget_usd: 39
max_attempts: 3
max_turns: 190
acceptance:
  - claim: >-
      A spec's frontmatter can declare `history`, with a `command` and a
      `batches` flag. `batches` is false unless declared, and a spec with no
      `history` parses with `None` there. Intake refuses each of these: a
      blank `command`, a missing one, `batches` given as the string `'yes'`,
      `batches` given as the integer `1`, and an unknown key under `history`.
    witness: tests/test_intake.py::test_a_history_declaration_parses_and_a_malformed_one_is_refused
    wrong_versions:
      - A lax boolean for `batches`, so `'yes'` and `1` both parse as true.
      - A `command` check that refuses only the empty string and lets one of spaces through.
      - A `history` model that ignores an unknown key instead of refusing it.
  - claim: >-
      `run_task` hands `run_one_cell` a `CellSpec` whose `history` is the
      spec's, its command and `batches` alike. The witness drives a spec with
      `batches: true`, one with `batches` left out, and one with no
      `history`, which gets `None`.
    witness: tests/test_task.py::test_the_cell_spec_carries_the_specs_history_declaration
    wrong_versions:
      - "`run_task` builds the `CellSpec` without `history`, so every cell sees `None`."
  - claim: >-
      `Ledger.snapshot` writes a copy of the ledger at the path it is given.
      The copy holds every committed row, rows still in the write-ahead log
      included. It is in rollback-journal mode, and no other file lands
      beside it. A write to the ledger after the snapshot never reaches it.
    witness: tests/test_ledger.py::test_a_snapshot_is_a_rollback_journal_copy_carrying_every_committed_row
    wrong_versions:
      - A file copy of `ledger.db` alone, which misses rows still in the write-ahead log and keeps WAL mode.
      - The backup API with no switch out of WAL mode, so the copy still reads as WAL.
      - A symlink or hard link to the live file, so a later write reaches the copy.
  - claim: >-
      `prepare_worktree` takes `extra_mounts`. The container it starts
      carries the three mounts `mounts()` returns, then each extra mount in
      the order given. The seed container carries none of the extra mounts.
      The witness passes a read-only bind mount and a volume mount.
    witness: tests/test_worktree.py::test_prepare_worktree_keeps_every_extra_mount_beside_its_own_three
    wrong_versions:
      - The extra mounts replace the three `mounts()` returns.
      - Only the first extra mount is kept.
      - The extra mounts also reach the seed container.
  - claim: >-
      `session.run_history` enters a Gate-only cell through `critic_cell`,
      with `network=None`, the repo's `thread_env` alone as its env, and a
      read-only bind mount at `worktree.HISTORY_MOUNT` among its
      `extra_mounts`. The mount's source holds a copy of the ledger and is
      never the live ledger's directory. With `batches: true` it also holds
      a copy of the batch tree, `v0` under `batches`, and with `batches` false it
      holds none. The command runs through `runtime.exec_` in that cell,
      from `worktree.WORKTREE_MOUNT`. It sees `SAFFRON_HISTORY_HOME` naming
      a writable copy of the mount under `worktree.STATE_MOUNT`. So a
      command that writes to its ledger leaves every file of the mount's
      source unchanged. The result carries the command's exit code, its
      stdout and its stderr. The mount's source no longer exists once
      `run_history` returns. The witness drives `batches` true and false.
    witness: tests/test_history_run.py::test_the_history_command_reads_a_writable_copy_and_never_writes_the_mount
    wrong_versions:
      - The live ledger's own directory bind-mounted read-only, with no copy.
      - "`SAFFRON_HISTORY_HOME` names the mount itself, so the command's first write lands in the mount's source."
      - The history mount declared without `readonly`.
      - "`batches` ignored, so the batch tree is never copied."
      - The batch tree copied whatever `batches` says.
      - The copy left on the host after the run.
      - The cell's env built with `cell_env`, so it carries a proxy address.
      - The result's stderr dropped.
      - The command run on the host with `subprocess`, so no cell runs it.
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
      For a spec declaring `history`, REVIEW runs the command once, in the
      Gate-only cell that carries the history mount, before any lens. Every
      lens's system prompt carries the command, both streams, and either
      `exited` with the exit code or `timed out`. `history.json` in the task
      directory records the command, the exit code, `timed_out` and both
      streams. A spec declaring no `history` gets no history mount, no
      `history.json` and no history text in any lens prompt. The witness
      drives a run that exits 3, a run that times out, and a spec with no
      `history`.
    witness: tests/test_history_run.py::test_every_lens_reads_the_history_run_and_the_task_dir_records_it
    wrong_versions:
      - The history run reaches only the first lens's prompt.
      - The history command run in the critic cell, on the critic network.
      - The lens prompt names the exit code of a timed-out run and never says it timed out.
      - No `history.json` written.
      - "`critic_cell` takes `extra_mounts` and never passes it to `prepare_worktree`."
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

Every line number below was read at `bc879e2c`. The three specs this one
depends on edit `saffron/cell/session.py`, `saffron/task.py` and
`saffron/ledger.py` first, so read each at the tree base before you start.

**The spec model refuses unknown keys.** `Spec` sets `extra="forbid"`
(`saffron/intake.py:157`, `:160`). Its fields end with `risk`
(`:199`), and `body` follows (`:201`). The nested models `Mutant` (`:72`) and
`Criterion` (`:110`) refuse unknown keys the same way.

**`CellSpec` is built in one place.** `run_task` builds it at
`saffron/task.py:533`, passing `declared_risk` at `:544`. `class CellSpec`
is at `saffron/cell/session.py:315`, and its last field is `task_id`
(`:350`). `saffron/qualify.py:131` builds one too, by keyword, so a new
field with a default needs nothing there.

**The Gate-only cell is `critic_cell` with `network=None`.** It is defined at
`saffron/cell/session.py:1335`. With no network it makes its own, named
`saffron-gate-net-<spec>` (`:1386-1393`). It seeds the worktree through
`worktree.prepare_worktree` (`:1419`), then calls
`_apply_and_commit_patch(container, patch)` (`:1432`).
`_gate_cell_suite` (`:1452`) and `probe_findings` (`:1506`) enter it with
`env=dict(thread_env)`, the repo's gate env and nothing else.

**A cell's mounts come from one function.** `worktree.mounts`
(`saffron/cell/worktree.py:35`) returns the worktree volume, the state
volume and the read-only gates bind. `prepare_worktree` (`:94`) starts the
cell with `mounts(volume, state, gates_dir)` (`:169`) and nothing else.
The seed container mounts the mirror and the worktree volume alone
(`:80-91`). `runtime.Mount` has a `readonly` flag
(`saffron/cell/runtime.py:212-220`).

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
Build that path, from frontmatter to every lens.

1. **The field.** Add `history` to `Spec`, `None` by default. Its model takes
   a `command` string and a `batches` boolean, strict and false by default,
   and refuses unknown keys. A `command` that is blank once stripped is
   refused. Give `CellSpec` a `history` field, `None` by default, and have
   `run_task` pass the spec's.
2. **The snapshot.** Add `Ledger.snapshot(dest)`. It writes a consistent
   copy with sqlite's backup API and leaves it in rollback-journal mode, so
   a reader needs nothing beside the file. The live ledger is being written
   by the task that calls it, so a file copy is not enough.
3. **The mount.** Add `extra_mounts`, a sequence of `runtime.Mount` empty by
   default, to `prepare_worktree` and to `critic_cell`. `critic_cell` passes
   it through. `prepare_worktree` appends it after `mounts()`' three, on the
   cell alone. Add `worktree.HISTORY_MOUNT`, `"/history"`.
4. **The run.** Add `session.run_history`, keyword-only: `spec`, `repo`,
   `mirror`, `gates_dir`, `thread_env`, `patch`, `ledger`, `out_dir`,
   `created` and `note`. On the host it builds a source directory holding
   `ledger.db` from `Ledger.snapshot`. With `batches`, it also holds a copy
   of `out_dir` as `v0` under `batches`, so the source reads as a
   `--home`. It enters `critic_cell` with `network=None`, `env=dict(thread_env)` and the
   source bind-mounted read-only at `HISTORY_MOUNT`. In the cell it runs one
   `runtime.exec_` from `WORKTREE_MOUNT`. That exec copies the ledger to a
   writable home under `worktree.STATE_MOUNT` and links the batch tree in
   when it is there. It then runs the command with `SAFFRON_HISTORY_HOME`
   naming that home. Bound it with a timeout of 600 seconds. Remove the
   source in a `finally`. Return a dict with `command`, `batches`,
   `exit_code`, `timed_out`, `stdout` and `stderr`. Bound each stream at
   `HISTORY_OUTPUT_CHARS`, 20000. Keep the first characters, and end a cut
   one with a note naming how many went.
5. **The lenses.** REVIEW calls `run_history` for a spec whose `history`
   is set. The call comes after a clean gate comparison and before the lens
   critic cell, inside the same `try` as that critic cell. Write its result to
   `history.json` in the task directory. Append a `## History run` section
   to the `spec_body` every lens gets. It names the command and says
   `exited <code>` or `timed out`, then gives stdout and stderr. A spec with
   no `history` gets an empty section and no cell.

## Out of scope

- The spec loop's step 1b question, "does the code need `done/`?". That
  half of the item is skill text and lands by hand.
- `DESIGN.md` §3.2 and §5.5, `CONTEXT.md`'s History run entry and
  `docs/agents/issue-tracker.md`. They are written by hand on this spec's
  own branch.
- REBUT's prompt (`saffron/cell/session.py:3146`), the PR body and the
  events log. They do not show the history run.
- A history run that cannot start. `critic_cell` raising
  `CellRuntimeError` ends the task as `_gate_cell_suite`'s raise does today.
- Any spec declaring `history`. None can until this lands
  (`DESIGN.md` §3.2, "A spec cannot introduce the frontmatter it is written
  in").

## Notes for the agent

Every criterion here witnesses new code, so none declares a `mutant`, and
the `witness` gate will report `skip` for each. That is honest, not
missing.

Import `History`, `run_history` and `HISTORY_MOUNT` inside each test body,
never at module scope. `revert` re-runs the witnesses with your source
files reverted. A module-scope import of a name you add makes that run a
collection error, which `revert` reads as `skip`.

`tests/test_history_run.py` is a new file. It imports `_drive`,
`_stub_the_runtime`, `_spec`, `_turn`, `_block`, `_PLAN` and
`_GATE_CONTAINER` from `tests/test_session.py`, as
`tests/test_probe_findings.py` imports from it. Do not edit
`tests/test_session.py`.

**The unit witness for `run_history`** stubs `session.critic_cell` with a
context manager that records its keywords and yields a fixed container. It
stubs `runtime.exec_` to run the argv on the host. In one pass over each
argument, it rewrites `worktree.STATE_MOUNT` to a host directory for the
state volume. The same pass rewrites `worktree.HISTORY_MOUNT` to the
mount's own source. Use a fresh state directory per exec call. With no
`extra_mounts` keyword, the stub finds no history mount and the test fails,
which is the default it must not hide. The command is a Python script file
run with `sys.executable`. It reads `SAFFRON_HISTORY_HOME`, sets WAL mode on
its `ledger.db`, writes one table, and prints the task count. It prints one
batch-tree file's text or `None`, and the real path of its home, and exits
3 with a marker on stderr. The test hashes every file of the mount's source
before and after the command, inside the stub. `_gate_cell_suite`'s docstring says the tests in a gate cell execute as `root`
(`saffron/cell/session.py:1469`), so a `chmod` cannot stand in for a
read-only mount. The hash is what
catches a write.

**The wiring witness** drives `_drive` three times, under its own
`tmp_path` subdirectory each. It overrides `runtime.exec_` after
`_stub_the_runtime` to return a scripted `runtime.Completed` for the one exec
whose argv mentions the history command in any argument. Every other exec
gets a clean `runtime.Completed(0, "", "")`. The lens prompts are
`cell.system_prompts[2 : 2 + len(review.LENSES)]`, after the plan and
implement turns. The history mount is read from the `extra_mounts` keyword
of `cell.worktrees`.

`estimated_lines` is a prototype's measured diff: 1887 changed tokens
over the five source files and five test files in `touches`. It holds
every criterion's code and witness, with terse comments. It holds none of
the `DESIGN.md`, `CONTEXT.md` or backlog edits, which are not yours.

The in-cell copy of an 880 MB ledger onto the state volume is unmeasured in
a real cell. Mark it with a `ponytail:` comment naming that ceiling.
