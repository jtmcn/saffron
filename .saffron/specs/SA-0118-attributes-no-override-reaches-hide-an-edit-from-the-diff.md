---
id: SA-0118
title: attributes in the cell's own git dir print an edit as binary, and no override on the command line reaches them
type: bug
priority: 2
depends_on: []
touches:
  - saffron/cell/worktree.py
  - tests/test_worktree.py
  - tests/test_package.py
  - harness/recovery.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/repos/**
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
  - tests/test_corpus.py
  - .git/**
budget_usd: 10
max_attempts: 3
max_turns: 60
risk: elevated
acceptance:
  - claim: >-
      `export_patch` prints an edited text file's hunks when the worktree's
      `.git/info/attributes` marks every path `-diff`. A genuinely binary file
      committed in the same range still reads as binary, and the attributes file
      is still in place after the read. Today the patch says only that the
      text file's binary content differs, so no lens reads the edit.
    witness: tests/test_worktree.py::test_export_patch_shows_hunks_under_the_git_dirs_own_attributes
  - claim: >-
      `export_patch` prints the hunks when an untracked `.gitattributes` marks
      every path `-diff` and a line in `.git/info/exclude` hides that file from
      `git status`. The file is still in place after the read. Today the patch
      hides the edit, and no commit shows why.
    witness: tests/test_worktree.py::test_export_patch_shows_hunks_under_an_excluded_gitattributes
  - claim: >-
      Two global settings that shape a new git dir do not reach the one
      `export_patch` reads from. An `init.templateDir` whose attributes file
      marks every path `-diff` does not hide the hunks, and an
      `init.defaultObjectFormat` of `sha256` does not stop the read. Today the
      worktree's own `.git/info/attributes` already hides them.
    witness: tests/test_worktree.py::test_export_patch_shows_hunks_when_global_config_shapes_a_new_git_dir
  - claim: >-
      `harness/recovery.py`'s `pinned_diff` takes its hunk context width from
      `worktree.DIFF_FLAGS` alone, and every shipped fixture still reproduces
      through it. Today its own copy of the flag follows `DIFF_FLAGS` and wins,
      so a change to the pin reaches no harness test.
    witness: tests/test_corpus.py::test_every_shipped_fixture_reproduces_its_own_declared_range
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--unified=3",'
      replace: '"--unified=4",'
  - claim: >-
      `pinned_diff` takes its `index` line abbreviation from
      `worktree.DIFF_FLAGS` alone, and every shipped fixture still reproduces
      through it.
    witness: tests/test_corpus.py::test_every_shipped_fixture_reproduces_its_own_declared_range
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--abbrev=7",'
      replace: '"--abbrev=9",'
  - claim: >-
      `pinned_diff` takes its diff algorithm from `worktree.DIFF_FLAGS` alone,
      and every shipped fixture still reproduces through it.
    witness: tests/test_corpus.py::test_every_shipped_fixture_reproduces_its_own_declared_range
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--diff-algorithm=myers",'
      replace: '"--diff-algorithm=histogram",'
  - claim: >-
      `tests/test_package.py`'s `cell_patch` fixture, which calls itself shaped
      exactly like `export_patch`'s output, builds its patch with
      `worktree.DIFF_FLAGS` rather than a copy holding five of its flags.
    witness: tests/test_package.py::test_a_patch_applies_onto_a_base_that_moved_elsewhere
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--no-color",'
      replace: '"--color=always",'
---

## Context

Backlog item **103**, with the remainder of item **89** folded in.

Item 103 lists settings a cell can write that make the pinned diff print
`Binary files a/f.py and b/f.py differ` with no hunks. `SA-0075` pinned the two
that a `-c` override reaches. Both now sit in `git_argv`
(`saffron/cell/worktree.py:168-204`), with the reason in its comment. Two
vectors are left, and no flag or override reaches either of them:

- `* -diff` in `.git/info/attributes`.
- An untracked `.gitattributes` holding `* -diff`, hidden by a line in
  `.git/info/exclude`. So `dirty_paths` (`saffron/cell/worktree.py:271`)
  never lists it, and `commit_dirty` (`saffron/cell/worktree.py:251`) never
  commits it.

Two reads carry a cell's diff to the host. `export_patch`
(`saffron/cell/worktree.py:235-239`) is the patch every lens, `integrity` and
`size` read, and PACKAGE applies. And `changed_files`
(`saffron/cell/worktree.py:651-662`) is the list `scope` judges. Both run
`_git` (`saffron/cell/worktree.py:207-208`), which is `git_argv` in the
worktree's own git dir.

**Measured 2026-09-21** by
`docs/evidence/scripts/2026-09-21-attributes-fresh-git-dir.sh`. It ran on the
host (git 2.54) and in `saffron/cell-base:python` (git 2.39.5), and both
printed the same table. The fresh git dir is a bare one whose
`objects/info/alternates` names the worktree's objects, read with
`--git-dir`.

| attribute source | worktree's git dir | fresh git dir |
|---|---|---|
| `* -diff` in `.git/info/attributes` | Binary files differ | hunks |
| untracked `.gitattributes`, excluded | Binary files differ | hunks |
| global `init.templateDir` seeding `info/attributes` | not probed | Binary files differ |
| the same, with `git init --bare --template=` | not probed | hunks |

**Measured 2026-09-21 on git 2.54 and git 2.39.5** by the four
`docs/evidence/scripts/2026-09-21-fresh-git-dir-*.sh` probes. Both gits printed
the same output except where the second bullet says:

- `git diff --name-only` lists the edited path under either vector. The
  listing `changed_files` returns does not move, which item 103's record also
  says.
- A global `init.defaultObjectFormat = sha256` makes git 2.54's
  `git init --bare` create a `sha256` dir, and the diff then fails with
  `unknown revision`. Git 2.39.5 ignores the key and creates a `sha1` dir.
  Passing `--object-format` with the value `git rev-parse --show-object-format`
  prints in the worktree restores the hunks on both.
- A fresh dir also ignores a *committed* `.gitattributes` marking `*.py -diff`.
  A file holding a NUL byte still prints `Binary files … differ` from it.
- From a fresh dir, `--name-only` still lists a gitlink that a committed
  `.gitmodules` marks `ignore = all`.

Item 89's remainder is two copies of `DIFF_FLAGS`
(`saffron/cell/worktree.py:131-166`):

- `pinned_diff` (`harness/recovery.py:70-106`) passes `--abbrev=7`,
  `--unified=3` and `--diff-algorithm=myers` after `*DIFF_FLAGS`. `SA-0072`
  added all three to `DIFF_FLAGS` (`saffron/cell/worktree.py:146-151`), so the
  copies win and hide any change to the pins. Its docstring
  (`harness/recovery.py:75-76`) still says `_git` carries "two `-c`
  overrides". `git_argv` now holds six.
- `tests/test_package.py:361-367` keeps five of the eleven flags as its own
  `DIFF_FLAGS`, under a `cell_patch` fixture (`:371-372`) that calls itself
  shaped exactly like `export_patch`'s output. The module uses that copy at
  fourteen sites.

## Problem

A cell is untrusted, and every control that matters lives outside it (§2). The
critic reads `export_patch`'s output (§5.5). A file the agent writes inside
its own git dir decides whether that output contains the edit at all. And
`integrity` then errors the attempt, which is charged to nobody (§5.4).

Both copies of the flags make a change to `DIFF_FLAGS` invisible to the tests
built on them.

## Out of scope

**Other mechanisms.** `--text` restores the hunks but renders every genuine
binary as text. That changes `integrity`'s binary check and PACKAGE's refusal of
a binary change with no full index line (item 103's record). `--attr-source` is
rejected by git 2.39.5 and does not override `info/attributes`. Bumping the
cell's git is backlog item b-b5f379, by hand. None of these is reopened here.

**Host-side reads** in `saffron/phases/package.py` and `saffron/repos/mirror.py`.
They run on repos the host built.

**Other in-cell reads.** `changed_files`, `read_at_head`, `commit_subjects`,
`head_sha`, `dirty_paths` and `commit_dirty` keep reading the worktree's own git
dir. Neither vector moves the `changed_files` listing (measured above), so
moving it would change code no failing witness could drive.

**A process still alive in the cell.** It could write into the fresh dir between
its creation and the diff. The reads already run inside the cell, under the same
trust.

**The comment over the unreadable-file check** in `integrity`
(`saffron/gates/core/integrity.py:233-240`). It names a committed
`.gitattributes` and a worktree setting as ways to hide a Python file. After this change neither reaches `export_patch`, so the operator
corrects that comment by hand beside this spec. `saffron/gates/**` is
forbidden here.

**A committed `.gitattributes`.** The fresh dir ignores it too (measured
above). So a target repo that commits `-diff` for a lock file now
sends that file's hunks to the lenses and to `size`. No criterion pins it.

**`pinned_diff`'s other pins.** It keeps its two `-c` overrides and takes none
of `git_argv`'s others.

## Notes for the agent

**Which criteria carry mutants.** The fresh git dir is new code, so criteria 1
to 3 declare witnesses and no mutant. A mutant would pin a spelling you have
not written yet. Criteria 4 to 7 are `preserves`, and each mutant edits a
`DIFF_FLAGS` entry that exists now. Each survives while a copy of the flag
stays. Measured on this base: each of the four mutants passes its witness with
the copies in place and fails it with them gone.

**One helper, one caller.** `export_patch` reads its diff through it, and
`changed_files` does not change. Per call, inside the cell:

1. Resolve HEAD to a sha in the worktree first. The fresh dir has no refs.
2. Read the worktree's object format and its object directory from the
   worktree. Derive the object directory from the exec's working directory,
   never a literal `/work`. `_host_git` (`tests/test_worktree.py:764`) runs
   every exec with `cwd=tmp_path`.
3. Create the dir with `mktemp -d`, then `git init -q --bare --template=`
   with `--object-format` set to the worktree's value.
4. Write the object directory into its `objects/info/alternates`.
5. Run the diff with `--git-dir` naming it, `base_sha` against the resolved
   sha, under `git_argv`'s env and every `-c` pin it holds now.
6. Remove the dir, whether the diff succeeded or not. On the host test seam
   it is created on the operator's machine.

Pass a path to a shell as a positional argument, never inside the script text.

**Prove the setting first.** Build criteria 1 to 3 on
`_isolated_repo_with_a_text_file` (`tests/test_worktree.py:1647`). Call
`_assert_bare_diff_is_binary` (`tests/test_worktree.py:1675`) before
`export_patch`, as the witnesses at `tests/test_worktree.py:1689` and
`tests/test_worktree.py:1705` do.

- Criterion 1 also commits a file holding a NUL byte in the same range. It
  asserts that file's block still reads `Binary files`, which is what refuses
  `--text`. Assert the attributes file still holds its line after the read.
  `_assert_bare_diff_is_binary` accepts any `Binary files` line, and the NUL
  file supplies one whether or not the setting bites. So check the bare diff
  and the patch per path, on `f.py`'s own block.
- Criterion 2 writes the exclude line before the file. After the commit it
  asserts `git status --porcelain` prints nothing.
- Criterion 3 plants `.git/info/attributes` as well, so the test fails at
  base. Point `GIT_CONFIG_GLOBAL` at a file under `tmp_path` and write the two
  settings there with `git config --file`. Keep the template dir outside the
  repo, as `tests/test_worktree.py:1712` keeps its attributes file, since
  `_commit` runs `add -A`. Prove the template bites: a plain `git init --bare`
  under that config creates `info/attributes`. Do not assert the object
  format bites. Git 2.39.5 ignores that key, and the cell executes its
  `tests` gate under that git.

**Never run `git config --global` in a test.** Write the file
`GIT_CONFIG_GLOBAL` names with `git config --file`, so the write lands where the
test pointed it and nowhere else.

**The copies.** In `tests/test_package.py`, import `DIFF_FLAGS` from
`saffron.cell.worktree` in place of the list, so no call site changes. The
comment at `tests/test_package.py:3077` and the explicit
`--ignore-submodules=none` after it describe the copy, so remove both. In `pinned_diff`, drop the three flags and
correct the docstring. Keep the measurement as provenance for the pins
`DIFF_FLAGS` now holds. A docstring stays within ten lines.

**Every new witness must fail with the source reverted.** Import nothing new at
module scope. A module-scope import of a name you add turns the reverted run
into a collection error, which `revert` reads as `skip`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines.
