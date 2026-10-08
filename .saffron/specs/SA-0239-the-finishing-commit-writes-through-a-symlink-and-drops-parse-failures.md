---
id: SA-0239
title: The finishing commit writes through a symlink the tree holds and drops the specs it cannot parse
type: bug
priority: 2
estimated_lines: 168
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
budget_usd: 14
max_attempts: 3
max_turns: 90
acceptance:
  - claim: >-
      `commit_finish` raises `ValueError` before it writes, creates or
      renames through a symlink in the worktree it checked out. It reads
      each component of the path below the worktree with `lstat`, and the
      message names the symlinked component's path from the tree's root. No
      file or directory outside the worktree is created or changed, nothing
      is committed, and the worktree is removed. The witness drives nine
      cases. A text write meets a symlink at `.saffron`, at
      `.saffron/specs`, at a layer's spec file, and at an unrun task's
      dangling spec file. The `done/` mkdir meets one at `.saffron`, at
      `.saffron/specs` and at `done` itself. A retirement's source is a
      layer's spec file symlinked to a file inside the worktree. Its
      destination is a symlink already in `done` under that spec's name. The
      same witness
      then finishes a batch with no symlink in the tree, from a worktree
      path whose own parent is a symlink, and gets a commit.
    witness: tests/test_finish.py::test_the_finish_refuses_a_symlink_on_any_path_it_writes_creates_or_renames
    wrong_versions:
      - The check guards the text writes alone, so a symlinked `done` takes every retirement.
      - The check guards the writes and the mkdir but neither end of a rename.
      - The rename's destination is checked and its source is not.
      - The rename's source is checked and its destination is not.
      - The mkdir is left unchecked, so a tree with no `done/` under a symlinked `.saffron/specs` gets one made outside.
      - Only the last component of each path is checked, as `Path.is_symlink()` on the whole path does.
      - The path is resolved and compared with the resolved worktree, which lets a symlink pointing inside the worktree through.
      - Every component of the absolute path is checked, so a worktree under a symlinked directory is refused.
      - A component that `Path.exists()` calls missing is skipped, so a dangling symlink at an unrun task's path creates a file outside.
      - The refusal raises `OSError`, which `_stack_finish` does not catch.
      - The check runs after the write, so the file outside is already changed.
  - claim: >-
      `commit_finish` emits one line per spec in `.saffron/specs/` that
      `discover_specs` could not parse at the finishing tree. Each line goes
      through `emit` and names the file's path from the tree's root, with
      the reason `discover_specs` gave. The worktree's own path appears
      nowhere in a line, its reason included. The witness drives six such
      files. Two are layers' texts the finish wrote, one refused as a shape
      error and one as a disclosed mutant. One is an unrun task's text the
      finish wrote. One is a layer's spec already in the tree with no text
      of its own. One is a spec in the tree that is no layer's. One is a
      dangling symlink in the tree that cannot be read. Every spec that
      parses gets no line.
    witness: tests/test_finish.py::test_the_finish_emits_one_line_per_spec_it_cannot_parse
    wrong_versions:
      - Only the first failure is emitted.
      - A failure that carries a parsed spec, the disclosed mutant, is skipped.
      - Only a failure on a path the finish wrote is emitted, which drops the three files already in the tree.
      - The lines go to `print` and not to `emit`.
      - A line names the path and leaves out the reason.
      - A line names the absolute path inside the worktree, which is gone once the finish returns.
      - The worktree's path is stripped from the file's name and left in the reason, which the unreadable file's reason names twice.
  - claim: >-
      `_stack_finish` still prints a `ValueError` from `commit_finish` as
      one line and the night still exits 0, which is how a symlink refusal
      reaches the operator.
    witness: tests/test_cli.py::test_a_stack_batch_commits_its_finish_and_survives_a_raise
    preserves: true
  - claim: >-
      A finish over a tree with no symlink and no spec that fails to parse
      still writes each text, retires each layer's spec, and emits only the
      line for an unrun task with no text.
    witness: tests/test_finish.py::test_the_finishing_commit_writes_each_layers_and_unrun_texts_and_retires_each_layers_spec
    preserves: true
---

## Context

Backlog item **b-8d654b**, with **b-3d2aa1** in the same spec, since both
edit `commit_finish`. The first cites `DESIGN.md` §2. ADR 7 decides the
finishing layer this function writes.

**What the finish writes today.** `commit_finish` checks the top layer's
`pushed_sha` out into `workdir` with `git_mirror.add_worktree`
(`saffron/finish.py:147`). That is a tree a cell committed. It writes each
pending text with `(workdir / path).write_text(text)`
(`saffron/finish.py:149-150`). It parses the spec directory with
`discover_specs` and binds the failures to `_failures`, which nothing reads
(`saffron/finish.py:151-152`). It makes `done/` with
`done_dir.mkdir(exist_ok=True)` (`saffron/finish.py:154-155`). It retires
each layer's spec with `found.rename(done_dir / found.name)`
(`saffron/finish.py:156-159`). The `finally` removes the worktree
(`saffron/finish.py:180-181`). No line reads a symlink. `write_text` and
`mkdir` follow one at any component. So a cell that commits
`.saffron/specs` as a symlink to a host directory gets the host's write
there. `_checked` refuses a bad text path before the worktree exists
(`saffron/finish.py:101-111`), but it reads the string and never the tree.

**What the finish already emits.** `commit_finish` takes `emit`, which
defaults to `print` (`saffron/finish.py:121`). It emits one line for an
unrun task with no spec text (`saffron/finish.py:143`). The night's call
is `finish.commit_finish(` with `workdir=workdir` as its last argument
(`saffron/cli.py:814-816`). It passes no emitter, so each line reaches the
night's stdout beside the other finish lines.

**What a parse failure carries.** `discover_specs` returns the specs it
parsed and one `DiscoveryFailure` per file it could not
(`saffron/intake.py:396-435`). A failure carries `path`, `reason`, and a
`spec` set only for a disclosed mutant (`saffron/intake.py:381-393`). A
file that does not parse declares no id. So the finish cannot tell a
layer's unparseable spec from any other, and that layer stays unretired
with nothing said.

**What catches a refusal.** `_stack_finish` catches `GitError` and
`ValueError` from `commit_finish`, prints one line, and returns
(`saffron/cli.py:817-820`). Its docstring says any other raise reaches
`main` (`saffron/cli.py:795-797`). The operator kept that catch narrow.

## Problem

A cell can commit a symlink at `.saffron`, `.saffron/specs`, a spec file
or `done/`. The host's finish then writes through it, or renames a spec
into the directory it names, outside the worktree. That holds on any repo
whose policy leaves `.saffron/**` writable. A rename follows a symlink at
neither end of its own path, so a link at the source or destination file
moves or is replaced. The finish refuses both ends all the same.
Separately, a spec the finish cannot parse is skipped in silence. A layer
whose spec is that file stays in the spec directory, and the night's log
never says why.

## Out of scope

- **The exit code on an `OSError`.** b-3d2aa1's second half leaves to the
  operator whether `_stack_finish` keeps the night's exit code on any raise.
  The operator decided to keep the catch narrow, and `saffron/cli.py` is
  forbidden here. That decision closes the half, so b-3d2aa1 closes as done
  when this spec merges.
- **Reads through a symlink.** `discover_specs` reads each spec file it
  globs, a symlinked one included. This spec refuses writes, creates and
  renames, as b-8d654b's Done asks.
- **A layer whose spec file is missing from the tree.** It yields no
  failure and no `by_id` entry. It stays as it is today.
- **A spec directory that is a dangling symlink.** `discover_specs` raises
  `SpecError`, a `ValueError`, before the mkdir (`saffron/intake.py:416-417`).
  Nothing is written, and its message keeps the worktree's path.
- **`publish_finish`'s worktree and `write_findings`.** Both write to paths
  the host chose, under `out_dir`, never a path the cell's tree holds.

## Notes for the agent

**Both new criteria are new code.** No refusal and no failure line exist
at base, and no text pins their spelling. So criteria 1 and 2 declare a
witness and no mutant. Expect `witness` to report `skip` for both.
Criteria 3 and 4 name tests that exist and pass at base.

**The check.** Read each component below `workdir` with `lstat`, from the
first part of the path to its last. A component that does not exist ends
the walk, since nothing below it can be a link. A dangling symlink is not
missing: `lstat` reads the link itself. Never walk above `workdir`. Raise
`ValueError` naming the symlinked component from the tree's root, such as
`.saffron/specs`. Run it before each write, before the mkdir, and on both
ends of each rename, each right before its own operation. The gap between
the `lstat` and the operation is safe. No cell runs by then, so the host
is the only writer of `workdir`.

**The failure lines.** Emit them after `discover_specs` and before the
renames, one per failure, through `emit`. Name the path relative to
`workdir` and give the failure's `reason`. A reason can name the absolute
path itself, as an unreadable file's does (`saffron/intake.py:357-358`).
So drop the worktree's path and its slash wherever the reason holds it.
Start each with `finish: `, as the line at `saffron/finish.py:143` does.

**The fixture.** Both witnesses use the `stack` fixture and batch B, with
TE-21 as the unrun task. Plant each symlink or broken file inside the
worktree once `add_worktree` returns. Patch `git_mirror.add_worktree` with
a wrapper that calls the real one and then plants. The mirror's history
then needs no new commit. Make an `outside` directory under `tmp_path` for
each symlink's target. Snapshot every path under it and its bytes (`lstat`
for a link) after the plant, and compare once `commit_finish` raises. A
write through the file link changes bytes and creates no path. Assert the
mirror's `for-each-ref` and `count-objects -v` output are unchanged, and that
`worktree list` prints one line.

**Criterion 1's nine cases.** Each runs in its own `monkeypatch.context()`
with its own `workdir`.

| operation | symlinked component | the plant |
| --- | --- | --- |
| write | `.saffron` | move `.saffron` outside, link it back |
| write | `.saffron/specs` | move `specs` outside, link it back |
| write | `.saffron/specs/TE-7-seven.md` | link it to an outside file |
| write | `.saffron/specs/TE-21-other.md` | link it to an outside path that does not exist |
| mkdir | `.saffron` | delete `done/`, move `.saffron` outside, link it back |
| mkdir | `.saffron/specs` | delete `done/`, move `specs` outside, link it back |
| mkdir | `.saffron/specs/done` | delete `ten.md` and `TE-7-seven.md`, move `done` outside, link it back |
| rename source | `.saffron/specs/ten.md` | move it to the tree's root, link it there relatively |
| rename destination | `.saffron/specs/done/ten.md` | link it to an outside file |

The three mkdir cases patch the ledger's `spec_text` to return `None`, so
no write runs first. The last mkdir case deletes both files so no rename
follows, and only the refusal tells the check apart from none. Assert
that each case's component appears in the message. The batch with no
symlink uses `tmp_path / "link" / "work"`, where `link` is a symlink to
another directory under `tmp_path`.

**Criterion 2's six files.** Record a revision for TE-7 at its own path
with text that has no frontmatter. Record one for TE-20 whose acceptance
mutant's `find` also appears in its body. Record one for TE-21 at
`.saffron/specs/TE-21-other.md` with no frontmatter. Plant `ten.md` and
`TE-1-one.md` with a frontmatter fence that never closes. Plant
`gone.md` as a relative symlink to a file that does not exist. Assert one
line names each of the six paths, that it carries the reason's text, and
that no line names `tmp_path / "work"`. Assert exactly six lines, and a
commit.

The host runs each wrong version listed under a criterion. Do not run them.

Commit after each witness passes. Uncommitted work dies with the cell.
