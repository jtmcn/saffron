---
id: SA-0105
title: mirror.diff_stat reads a bare --shortstat, so the operator's git config moves the counts a queue line and a pull request show
type: bug
priority: 3
depends_on: []
touches:
  - saffron/repos/mirror.py
  - tests/test_mirror.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/replay.py
  - saffron/task.py
  - saffron/cli.py
budget_usd: 10
max_turns: 60
acceptance:
  - claim: >-
      `mirror.diff_stat` takes its flags from `worktree.DIFF_FLAGS` and counts
      only its own summary line. When the global git config sets
      `diff.ignoreSubmodules = all`, a range that adds a submodule and a file
      whose one line reads like a deletion count reports the submodule's line
      and the file's line as added, and nothing removed. Today the setting
      drops the submodule, so the added count is one short.
    witness: tests/test_mirror.py::test_diff_stat_counts_a_submodule_the_git_config_ignores
    mutant:
      file: saffron/cell/worktree.py
      find: '"--ignore-submodules=none",'
      replace: ''
  - claim: >-
      `mirror.diff_stat` counts a renamed file as its lines removed and its
      lines added, as the patch the gates judge carries it, whatever the git
      config says about renames. Today git's default rename detection counts a
      pure rename as nothing.
    witness: tests/test_mirror.py::test_diff_stat_counts_a_rename_as_the_patch_carries_it
    mutant:
      file: saffron/cell/worktree.py
      find: '"--no-renames",'
      replace: ''
  - claim: >-
      `mirror.diff_stat` still counts the added and removed lines of a merged
      pull request, as it does today.
    witness: tests/test_mirror.py::test_diff_stat_counts_lines
    preserves: true
---

## Context

Backlog item **176**, found by both seats reviewing `SA-0097` (PR #321) on
2026-09-17.

`SA-0097` made `mirror.changed_files` take its flags from
`saffron.cell.worktree.DIFF_FLAGS` (`saffron/repos/mirror.py:127-149`, import
at `:17`). `diff_stat` in the same file (`:152-165`) still runs a bare
`git diff --shortstat base..head` and reads two counts out of it with `_ADDED`
and `_REMOVED` (`:19-20`). Its callers are PACKAGE, for the pull request's
line counts (`saffron/phases/package.py:792`), and `replay`
(`saffron/replay.py:49`).

The `size` gate counts the patch, and the patch is exported with `DIFF_FLAGS`
(`saffron/cell/worktree.py:131`). So the counts a queue line shows and the
lines `size` judged can disagree for the same diff.

Measured on git 2.54 on 2026-09-17, against a bare clone, as
`mirror.diff_stat`'s callers use it:

- **A submodule.** A commit that adds only a gitlink gives
  `1 file changed, 1 insertion(+)`. With `diff.ignoreSubmodules = all` in
  the global config (`GIT_CONFIG_GLOBAL`), the bare read gives nothing, and
  the read with `DIFF_FLAGS` gives the line back.
- **A rename.** A commit that renames a 20-line file unchanged gives
  `1 file changed, 0 insertions(+), 0 deletions(-)` under git's defaults, and
  20 and 20 under `diff.renames = false`. With `DIFF_FLAGS` it gives 20 and 20
  under every setting, because `DIFF_FLAGS` carries `--no-renames`.

## Problem

An operator's git config changes the `+N/−M` a queue line and a pull request
body show. A rename reads as no change at all, though `size` counted every
line of it.

## Out of scope

**`saffron/cell/worktree.py`.** Both mutants are applied there, which needs no
`touches` entry, and the file is forbidden. Do not edit `DIFF_FLAGS`.

**The callers.** PACKAGE and `replay` pass the counts through unchanged.

**Matching GitHub's rename detection.** GitHub shows a pure rename as no
change. This spec makes the counts agree with the patch the gates judged
instead, which is the one the host has.

## Notes for the agent

**Splicing `DIFF_FLAGS` in alone prints the whole patch after the summary.**
`DIFF_FLAGS` carries `--unified=3`, and a context-size flag turns patch output
on. Measured on git 2.54: `diff *DIFF_FLAGS --shortstat` prints the summary
line, a blank line, then every hunk. `_ADDED` and `_REMOVED` then search the
whole output, and a missing count is taken from the first hunk line that looks
like one.

**Read the summary line, and nothing after it.** `--no-patch` is no fix. On
the cell image's git 2.39.5, `diff *DIFF_FLAGS --no-patch --shortstat` prints
nothing, whether `--no-patch` comes before `--shortstat` or after it. The
read would then give `(0, 0)` for every diff, with no error. Measured
2026-09-17 in `saffron/cell:saffron`. Git 2.54 on the host keeps the summary
when `--no-patch` sits between `DIFF_FLAGS` and `--shortstat`, so a host-only
check passes what the cell fails. On 2.39.5, `diff *DIFF_FLAGS --shortstat`
prints the summary as its first line, then a blank line and the patch, and an
empty diff prints nothing. Take the first line, and read `(0, 0)` when there
is none. Say why in a short comment on the read. `_git` strips its output, so
`splitlines()[0]` raises on an empty range where the read today returns
`(0, 0)`. Have the submodule witness also assert that a range from a commit to
itself reads `(0, 0)`.

**Both witnesses build real commits and read the counts.** A test that checks
the argument list proves nothing about the counts. Build the commits in the
`origin` fixture's repository (`tests/test_mirror.py:27`), then clone it with
`ensure_mirror`. `test_changed_files_lists_a_submodule_the_git_config_ignores`
(`:93`) does both. That test also shows how to add a gitlink with `update-index --cacheinfo` and
how to set `GIT_CONFIG_GLOBAL` with `monkeypatch.setenv`.

**The submodule witness has to catch the patch trap too.** Put both changes
in one commit: the gitlink, and a new file whose only line is text that
`_REMOVED` matches, such as `9 deletions(-)`. The correct counts are `(2, 0)`.
Today the config hides the gitlink, which gives `(1, 0)`. A splice that
searches the whole output gives `(2, 9)`, because the summary has no deletions
and the search finds the file's line in the hunk. Adding `--no-patch` gives
`(0, 0)` on the cell's git. Each wrong implementation fails the same
assertion.

**The rename witness needs no config.** Commit a file of known length. Then
commit a rename of it with no other change, and read `diff_stat` across that
commit. Git's default rename detection is what reports nothing today. Set
`GIT_CONFIG_GLOBAL` to a file with `diff.renames = true` anyway, so an
operator's config cannot change what the test measures.

**Import `DIFF_FLAGS`, as `changed_files` does.** Do not copy the flags. Copies
drifting apart is how this read was missed (backlog item 89).
