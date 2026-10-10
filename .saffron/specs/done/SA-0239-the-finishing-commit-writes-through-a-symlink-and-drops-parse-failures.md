---
id: SA-0239
title: The finishing commit writes through a symlink the tree holds
type: bug
priority: 2
estimated_lines: 90
estimate_measured: true
touches:
  - saffron/finish.py
  - tests/test_finish.py
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
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/repos/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - tests/test_cli.py
  - tests/test_intake.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 12
max_attempts: 3
max_turns: 90
acceptance:
  - claim: >-
      `commit_finish` raises `ValueError` before it writes a spec text through
      a symlink in the worktree it checked out. It reads each component of
      the path below the worktree with `lstat`. The message names the
      symlinked component's path from the tree's root, and never the
      worktree's own path. No file outside the worktree is created or
      changed, nothing is committed, and the worktree is removed. The witness
      drives four cases, one per component a write can meet. These are
      `.saffron`, `.saffron/specs`, a layer's spec file, and an unrun task's
      dangling spec file. The same witness then finishes the batch twice and
      gets a commit each time. The first run plants a symlink at
      `.saffron/specs/TE-1-one.md`, a path no pending text writes. The second
      plants none, from a worktree whose own parent is a symlink.
    witness: tests/test_finish.py::test_the_finish_refuses_a_symlink_on_any_path_it_writes
    wrong_versions:
      - Only the last component of each path is checked, as `Path.is_symlink()` on the whole path does.
      - The path is resolved and compared with the resolved worktree, which lets a symlink pointing inside the worktree through.
      - Every component of the absolute path is checked, so a worktree under a symlinked directory is refused.
      - A component that `Path.exists()` calls missing is skipped, so a dangling symlink at an unrun task's path creates a file outside.
      - The spec directory is checked once before the writes, and no file path is.
      - The layers' paths are checked and an unrun task's path is not.
      - The message names the path being written, not the symlinked component in it.
      - The message names the component by its absolute path inside the worktree.
      - The refusal raises `OSError`, which `_stack_finish` does not catch.
      - The check runs after the write, so the file outside is already changed.
      - Every symlink in the worktree is refused, so a link on a path no text writes blocks the finish.
  - claim: >-
      `_stack_finish` still prints a `ValueError` from `commit_finish` as
      one line and the night still exits 0, which is how a symlink refusal
      reaches the operator.
    witness: tests/test_cli.py::test_a_stack_batch_commits_its_finish_and_survives_a_raise
    preserves: true
  - claim: >-
      A finish over a tree with no symlink still writes each text, moves no
      spec, and emits only the line for an unrun task with no text.
    witness: tests/test_finish.py::test_the_finishing_commit_writes_each_layers_and_unrun_texts_and_moves_no_spec
    preserves: true
---

## Context

Backlog item **b-8d654b**. It cites `DESIGN.md` §2. ADR 7 decides the
finishing layer this function writes, and since b-a63235 it moves no spec
into `done/` (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:117`).

**What the finish writes today.** `commit_finish` checks the top layer's
`pushed_sha` out into `workdir` with `git_mirror.add_worktree`
(`saffron/finish.py:146`). That is a tree a cell committed. It writes each
pending text with `(workdir / path).write_text(text)`
(`saffron/finish.py:148-149`). Then it stages with `git add -A` and commits
(`saffron/finish.py:151-169`). The `finally` removes the worktree
(`saffron/finish.py:170-171`). Those writes are the only files it writes
in the tree. No line reads a symlink, and `write_text` follows one at any
component. So a cell that commits `.saffron/specs` as a symlink to a host
directory gets the host's write there. `_checked` refuses a bad text path
before the worktree exists (`saffron/finish.py:100-110`). It reads the
string and never the tree.

**The order of the writes.** `pending` holds each layer's text in layer
order, then each unrun task's (`saffron/finish.py:134-144`). An unrun task
with no text gets one line through `emit` instead
(`saffron/finish.py:141-142`). `emit` defaults to `print`
(`saffron/finish.py:120`).

**What catches a refusal.** `_stack_finish` catches `GitError` and
`ValueError` from `commit_finish`, prints one line, and returns
(`saffron/cli.py:817-820`). Its docstring says any other raise reaches
`main` (`saffron/cli.py:794-797`). The operator kept that catch narrow.
The night's `workdir` is `out_dir / "finish" / str(batch_id) / "tree"`
(`saffron/cli.py:812`). Nothing stops a directory above it from being a
symlink.

## Problem

A cell can commit a symlink at `.saffron`, `.saffron/specs` or a spec
file. The host's finish then writes a spec text through it, outside the
worktree. A dangling link at a new text's path creates the file it names.
That holds on any repo whose policy leaves `.saffron/**` writable.

## Out of scope

- **The exit code on an `OSError`.** The operator decided `_stack_finish`
  keeps its catch narrow, and `saffron/cli.py` is forbidden here. A
  refusal is a `ValueError`, so it reaches the operator as one line.
- **Spec parse failures.** The finish no longer parses the spec directory,
  since b-a63235 took retirement out of it. b-3d2aa1 closes as superseded.
- **Reads through a symlink.** `commit_finish` reads no file of the tree
  itself. This spec refuses writes, as b-8d654b's Done asks.
- **`publish_finish`'s worktree and `write_findings`.** Both write to paths
  the host chose, under `out_dir`, never a path the cell's tree holds.

## Notes for the agent

**Criterion 1 is new code.** No refusal exists at base, and no text pins
its spelling. So it declares a witness and no mutant. Expect `witness` to
report `skip` for it. Criteria 2 and 3 name tests that exist and pass at
base.

**The check.** Read each component below `workdir` with `lstat`, from the
first part of the path to its last. A component that does not exist ends
the walk, since nothing below it can be a link. A dangling symlink is not
missing, because `lstat` reads the link itself. Never walk above
`workdir`. Raise `ValueError` naming the symlinked component from the
tree's root, such as `.saffron/specs`. Run it on each pending path, right
before its own write. The gap between the `lstat` and the write is safe.
No cell runs by then, so the host is the only writer of `workdir`.

**The fixture.** The witness uses the `stack` fixture and batch B, with
TE-24 and TE-21 as the unrun tasks. The first write is TE-7's, and TE-21's
is the last. Plant each symlink inside the worktree once `add_worktree`
returns. Patch `git_mirror.add_worktree` with a wrapper that calls the real
one and then plants. The mirror's history then needs no new commit. Give
each case its own `outside` directory under `tmp_path`. Snapshot every path
under it and its bytes after the plant, reading a link with `readlink`.
Compare once `commit_finish` raises. A write through the file link changes
bytes and creates no path. Assert the mirror's `for-each-ref` and
`count-objects -v` output are unchanged, and that `worktree list` prints
one line.

**Criterion 1's four cases.** Each runs in its own `monkeypatch.context()`
with its own `workdir`.

| symlinked component | the plant |
| --- | --- |
| `.saffron` | move `.saffron` outside, link it back |
| `.saffron/specs` | move `specs` to the tree's root under another name, link it back relatively |
| `.saffron/specs/TE-7-seven.md` | link it to an outside file |
| `.saffron/specs/TE-21-other.md` | link it to an outside path that does not exist |

The second case's link points inside the worktree. Only the refusal tells
the check apart from none there. For each case, assert that the component
appears in the message with no path character after it. Assert that the
case's `workdir` appears nowhere in it.

**The two runs that commit.** The first links `.saffron/specs/TE-1-one.md`
to an outside file. That file is in the base tree, and no pending row
writes it (`tests/test_finish.py:278`). Assert a sha and that the outside
file's bytes are unchanged. The second plants nothing and uses
`tmp_path / "link" / "work"`, where `link` is a symlink to another
directory under `tmp_path`.

**The docstrings.** The module docstring says the finish checks each text
before touching git (`saffron/finish.py:3-4`). The new check runs after
`add_worktree`, so say so there. Name the refusal in `commit_finish`'s
docstring too.

The host runs each wrong version listed under a criterion. Do not run them.

Commit after each witness passes. Uncommitted work dies with the cell.
