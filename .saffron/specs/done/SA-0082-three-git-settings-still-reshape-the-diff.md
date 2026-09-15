---
id: SA-0082
title: three git settings a cell can write still reshape the diff the host reads, and one of them hides a path from scope
type: bug
priority: 2
depends_on: []
touches:
  - saffron/cell/worktree.py
  - tests/test_worktree.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - spikes/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - saffron/repos/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
budget_usd: 6
max_attempts: 3
max_turns: 40
risk: elevated
acceptance:
  - claim: >-
      `changed_files` lists a submodule path the worktree's real commits added,
      even when the worktree sets `diff.ignoreSubmodules` to `all`. Today the
      path is missing from the list, so `scope` never judges it against
      `touches`.
    witness: tests/test_worktree.py::test_changed_files_lists_a_submodule_the_worktree_config_ignores
  - claim: >-
      `export_patch` carries no terminal escape codes when the worktree forces
      colour on, whether through `color.ui` or through `color.diff`. Today 23
      lines of a two-hunk patch carry them, including the `diff --git` headers
      the host parses.
    witness: tests/test_worktree.py::test_export_patch_carries_no_color_when_the_worktree_forces_it
  - claim: >-
      `export_patch` keeps two separate hunks separate when the worktree sets
      `diff.interHunkContext` wide enough to merge them. Today they merge into
      one, which widens the lines a critic finding may anchor to, the way
      `diff.context` would.
    witness: tests/test_worktree.py::test_export_patch_keeps_hunks_apart_under_a_wide_inter_hunk_context
  - claim: >-
      `changed_files` lists both paths of a rename, as it does today.
    witness: tests/test_worktree.py::test_changed_files_lists_both_paths_of_a_rename
    preserves: true
  - claim: >-
      A stacked worktree exports exactly the child's own commit, as it does
      today.
    witness: tests/test_worktree.py::test_a_stacked_worktree_holds_the_parents_real_commits_and_only_the_childs_new_commit_is_exported
    preserves: true
---

## Context

`docs/BACKLOG.md` item **89**, the half `SA-0072` left, found reviewing it on
2026-09-11. `DIFF_FLAGS` in `saffron/cell/worktree.py` pins the shape of every
diff the host reads against config the agent can write in its own worktree
(§2). Three more repo-local settings still move it, and no flag pins them.

**Probed 2026-09-13** on git 2.39.5 (the cell image, `saffron/cell:saffron`) and
git 2.54 (the host), against `_git`'s `-c` overrides plus `DIFF_FLAGS`. Both
gave the same results:

| worktree setting | effect | restored by |
|---|---|---|
| `diff.ignoreSubmodules=all` | a submodule path added by a commit vanishes from the name-only listing and the patch | `--ignore-submodules=none`, or `-c diff.ignoreSubmodules=none` |
| `color.ui=always` | 23 lines of the patch carry escape codes; the name-only listing has none | `--no-color` |
| `color.ui=always` and `color.diff=always` | the same 23 | `--no-color`; `-c color.ui=never` does **not** |
| `diff.interHunkContext=10` | two hunks eight lines apart become one | `--inter-hunk-context=0`, or `-c diff.interHunkContext=0` |

The script is `docs/evidence/scripts/2026-09-13-history-and-diff-pins.sh`.

## Problem

A cell is untrusted, and every control that matters lives outside it (§2). The
submodule setting is a hole in `scope` itself: the list `scope` checks against
`touches` loses a path the agent's commits added. The other two change the bytes
every host-side reader of the patch sees, which `DIFF_FLAGS`' own comment says
cannot happen.

## Out of scope

**`harness/recovery.py`'s `pinned_diff`**, which repeats several of these flags.
Deleting the duplicates is a harness change, left for later (item 89).

**PACKAGE's own name-only listing** in `saffron/phases/package.py`. It reads the
operator's worktree on the host, not the cell's, so the agent cannot set its
config.

**`.git/info/attributes`**, which no flag or `-c` override reaches (item 103).

**Grafts and `.git/shallow`**, which move history reads rather than the diff.
They are `SA-0083`, stacked on this.

## Notes for the agent

**The three pins are new text, so those criteria carry witnesses and no
mutants.** The rename criterion is `preserves`: its witness was written ahead of
this spec, because nothing tested the rename flag before.

**They belong in `DIFF_FLAGS`,** beside the flags that already pin the diff's
shape. They are diff options, placed after `diff`, and both `changed_files` and
`export_patch` pass through `DIFF_FLAGS`. For colour, use the flag, not a `-c`
override. The table shows why: `color.diff` beats `-c color.ui=never`.

**Prove the setting, not only the pin.** In each witness, first assert that a
bare `git diff` in the same repo is moved by the setting. Then assert that the
pinned read is not. `test_changed_files_reads_through_a_planted_replacement`
pairs them this way.

**Isolate the test from the operator's git config.** Set `GIT_CONFIG_GLOBAL` and
`GIT_CONFIG_SYSTEM` to `os.devnull`, as the replacement fixture does. An
operator's own `color.ui=always` must not reach the bare read.

**A submodule needs no second repository.** A gitlink entry is enough, and that
is how the probe made one:
`git update-index --add --cacheinfo 160000,<sha>,vendor/sub`, then commit.

**No cell is needed.** `_host_git` in `tests/test_worktree.py` points
`worktree._git` at a real repo in `tmp_path`.

**Every new witness must fail with `worktree.py` reverted, not merely be missing
at base.** Import nothing new at module scope, because a module-scope import of
a name you add turns the reverted run into a collection error, which `revert`
reads as `skip`.

**Write any runner as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and `integrity` fails that suppression
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
