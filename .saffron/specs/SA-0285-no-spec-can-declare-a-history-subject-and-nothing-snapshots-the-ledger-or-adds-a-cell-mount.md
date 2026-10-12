---
id: SA-0285
title: No spec can declare that its subject is history, and nothing snapshots the ledger or adds a mount to a cell
type: feature
priority: 2
depends_on: [SA-0262, SA-0268, SA-0271]
estimated_lines: 156
estimate_measured: true
touches:
  - saffron/intake.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/cell/session.py
  - saffron/cell/worktree.py
  - tests/test_intake.py
  - tests/test_task.py
  - tests/test_ledger.py
  - tests/test_worktree.py
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
pending_symbols:
  - saffron/ledger.py::snapshot
budget_usd: 28
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      A spec's frontmatter can declare `history`, with a `command` and a
      `batches` flag. `batches` is false unless declared, and a spec with no
      `history` parses with `None` there. Intake refuses each of these: a
      blank `command`, a missing one, `batches` given as the quoted string
      `'yes'`, `batches` given as the integer `1`, and an unknown key under
      `history`.
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
---

## Context

Backlog item **b-a8270f**, which cites `DESIGN.md` §4.1 and §5.4. A change
whose subject is history never meets a real ledger in a cell. `SA-0107`'s
projection left out 75 of 76 merged tasks over a copy of the real ledger,
and every witness in its cell passed. `SA-0272`, this spec's child, runs a
spec's declared history command in a Gate-only cell over a read-only
snapshot of the ledger. This spec builds the four pieces it stands on. It
was split from `SA-0272` on size.

Every line number below was read at `bc879e2c`. `SA-0262` and `SA-0271`
edit `saffron/cell/session.py`. `SA-0268` and its parent `SA-0266` edit
`saffron/task.py`. `SA-0264`, an ancestor of `SA-0268`, edits
`saffron/ledger.py`. All of them land first, so read each file at the tree
base before you start.

**The spec model refuses unknown keys.** `Spec` sets `extra="forbid"`
(`saffron/intake.py:157`, `:160`). Its fields end with `risk`
(`:199`), and `body` follows (`:201`). The nested models `Mutant` (`:72`)
and `Criterion` (`:110`) refuse unknown keys the same way. `parse_spec`
reads the frontmatter with `yaml.safe_load` (`:264`), which reads a bare
`yes` as true. Only a quoted `'yes'` reaches the model as a string.

**`CellSpec` is built in one place.** `run_task` builds it at
`saffron/task.py:533`, passing `declared_risk` at `:544`. `class CellSpec`
is at `saffron/cell/session.py:315`, and its last field is `task_id`
(`:350`). `saffron/qualify.py:131` builds one too, by keyword, so a new
field with a default needs nothing there.

**`Ledger` keeps its database in WAL mode.** `Ledger.__init__` runs
`PRAGMA journal_mode=WAL` (`saffron/ledger.py:393`). A committed row can
sit in the `-wal` file until a checkpoint, so a copy of `ledger.db` alone
can miss it.

**A cell's mounts come from one function.** `worktree.mounts`
(`saffron/cell/worktree.py:35`) returns the worktree volume, the state
volume and the read-only gates bind. `prepare_worktree` (`:94`) starts the
cell with `mounts(volume, state, gates_dir)` (`:169`) and nothing else.
The seed container mounts the mirror and the worktree volume alone
(`:80-91`). `runtime.Mount` has a `readonly` flag
(`saffron/cell/runtime.py:212-220`).

## Problem

1. **The field.** Add a `History` model to `saffron/intake.py`. It takes a
   `command` string and a `batches` boolean, strict and false by default,
   and refuses unknown keys. A `command` that is blank once stripped is
   refused. Add `history: History | None`, `None` by default, to `Spec`.
2. **The cell's copy.** Give `CellSpec` a `history` field, `None` by
   default, and have `run_task` pass the spec's.
3. **The snapshot.** Add `Ledger.snapshot(dest)`. It writes a consistent
   copy with sqlite's backup API and leaves it in rollback-journal mode, so
   a reader needs nothing beside the file. The live ledger is being written
   by the task that calls it, so a file copy is not enough.
4. **The mount.** Add `extra_mounts`, a sequence of `runtime.Mount` empty
   by default, to `prepare_worktree`. It appends them after `mounts()`'
   three, on the cell alone and never on the seed container.

## Out of scope

- Running anything over the snapshot, adding `extra_mounts` to
  `critic_cell`, and every lens prompt. `SA-0272` does all three.
- `DESIGN.md` §3.2 and §5.5, `CONTEXT.md` and
  `docs/agents/issue-tracker.md`. They
  are written by hand on this spec's own branch.
- Any spec declaring `history`. None can until this lands
  (`DESIGN.md` §3.2, "A spec cannot introduce the frontmatter it is written
  in").

## Notes for the agent

Every criterion here witnesses new code, so none declares a `mutant`, and
the `witness` gate will report `skip` for each. That is honest, not
missing.

Nothing calls `Ledger.snapshot` until `SA-0272` lands, so
`pending_symbols` defers it for the `dead` gate.

Import `History` inside each test body, never at module scope. `revert`
re-runs the witnesses with your source files reverted. A module-scope
import of a name you add makes that run a collection error, which `revert`
reads as `skip`.

The intake witness quotes `'yes'` in its YAML. A bare `yes` is already
`True` once `yaml.safe_load` reads it, so it would test nothing.

The snapshot witness uses `tests/test_ledger.py`'s `ledger` and `task`
fixtures. The task row is committed and not yet checkpointed, so a copy
of the main file alone misses it. It then writes to the live ledger and
reads the copy through a `mode=ro` URI.

The worktree witness stubs `runtime.run_ephemeral` and
`runtime.run_detached` to record their `mounts`, as
`test_prepare_worktree_checks_out_exactly_the_base_it_is_given` does.

`estimated_lines` is a prototype's measured diff: 624 changed tokens over
the five source files and four test files in `touches`. It holds every
criterion's code and witness. It holds none of `SA-0272`'s work.
