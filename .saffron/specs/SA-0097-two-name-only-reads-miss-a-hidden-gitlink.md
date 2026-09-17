---
id: SA-0097
title: two name-only diff reads drop a gitlink a committed .gitmodules ignores, so scope passes a path it never saw
type: bug
priority: 2
depends_on: []
touches:
  - saffron/phases/package.py
  - saffron/repos/mirror.py
  - saffron/cell/worktree.py
  - tests/test_package.py
  - tests/test_mirror.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
budget_usd: 14
max_turns: 90
acceptance:
  - claim: >-
      When red work is pushed unpackaged, the changed-file listing that
      PACKAGE hands to `scope` takes its flags from `worktree.DIFF_FLAGS`. It
      therefore includes a submodule path the work adds under a committed
      `.gitmodules` that sets `ignore = all`, and work whose only out-of-scope
      path is that submodule is not pushed. Today the listing is a bare
      `--name-only` read, that path is missing from it, and `scope` passes.
    witness: tests/test_package.py::test_unpackaged_work_adding_a_hidden_submodule_outside_its_touches_is_not_pushed
    mutant:
      file: saffron/cell/worktree.py
      find: '"--ignore-submodules=none",'
      replace: ''
  - claim: >-
      `mirror.changed_files` takes its flags from `worktree.DIFF_FLAGS` as
      well. It lists a submodule path a commit adds even when the git config
      it runs under sets `diff.ignoreSubmodules=all`, as an operator's global
      config can. Today that setting drops the submodule path from its list.
    witness: tests/test_mirror.py::test_changed_files_lists_a_submodule_the_git_config_ignores
    mutant:
      file: saffron/cell/worktree.py
      find: '"--ignore-submodules=none",'
      replace: ''
  - claim: >-
      Red work outside its touches is still not pushed, and says `scope fail`,
      as it does today.
    witness: tests/test_package.py::test_unpackaged_work_outside_its_touches_is_not_pushed
    preserves: true
  - claim: >-
      `mirror.changed_files` still lists exactly the paths a pull request
      moved, as it does today.
    witness: tests/test_mirror.py::test_changed_files_lists_only_what_moved
    preserves: true
  - claim: >-
      The cell's own listing still includes a submodule path that a committed
      `.gitmodules` ignores, as `SA-0082` made it.
    witness: tests/test_worktree.py::test_changed_files_lists_a_submodule_a_committed_gitmodules_ignores
    preserves: true
---

## Context

Backlog item **115**, found reviewing `SA-0082` (PR #244) on 2026-09-14.

`SA-0082` added `--ignore-submodules=none` to `worktree.DIFF_FLAGS`
(`saffron/cell/worktree.py:152-155`). Without it, git's submodule-ignore
settings drop a gitlink from a name-only listing, and `scope` cannot object to
a path it was never given. A committed `.gitmodules` that sets `ignore = all`
hides a gitlink the same way. Because it is content the agent commits, not
config, `-c diff.ignoreSubmodules=none` does not undo it. Only the flag does
(`tests/test_worktree.py:1817-1845` measures both).

Two host-side name-only reads carry neither the flag nor `DIFF_FLAGS`:

- `push_unpackaged_work` (`saffron/phases/package.py:1000`) lists the changed
  files with `"diff", "--name-only", "-z", "--no-renames", tree_base`
  (`:1147-1149`) and passes that list to `scope_gate` (`:1154-1160`).
  `package.py` already imports `DIFF_FLAGS` (`:25`) for its patch read at
  `:857`.
- `mirror.changed_files` (`saffron/repos/mirror.py:125-142`) runs
  `-c core.quotePath=false diff --name-only -z base..head`. Its docstring says
  the paths "are matched against `touches`". `saffron/replay.py:48` is its one
  caller.

`scope_gate` (`saffron/gates/core/scope.py:63-73`) reads the patch text only to
check that its headers carry `a/` and `b/`. Every path it judges comes from the
listing it is given.

Measured on git 2.54 on 2026-09-16, with a commit that adds `.gitmodules`
(with `ignore = all`) and a gitlink at `vendor/sub`:

- **PACKAGE.** A patch exported with `DIFF_FLAGS` goes through
  `package.apply_patch` cleanly, and the commit then holds the gitlink.
  PACKAGE's listing as written returns only `.gitmodules`. The same read with
  `--ignore-submodules=none`, or with `DIFF_FLAGS`, returns `.gitmodules` and
  `vendor/sub`.
- **The mirror is different.** It is a bare clone, and a bare repository does
  not read a committed `.gitmodules`: `mirror.changed_files` already returns
  both paths for that commit. What hides the submodule there is config. With
  `diff.ignoreSubmodules = all` in the global git config
  (`GIT_CONFIG_GLOBAL`), `mirror.changed_files` returns only `.gitmodules`, and
  the same read with `DIFF_FLAGS` returns both.

## Problem

Red work that adds a submodule under an ignoring `.gitmodules` is pushed with a
`scope` pass that never saw the submodule. The mirror's listing drops the same
path whenever the operator's git config ignores submodules.

## Out of scope

**`scope_gate` itself.** It judges the list it is given. `saffron/gates/**` is
forbidden.

**The cell's listing** (`worktree.changed_files`). `SA-0082` fixed it, and a
preserves witness holds it.

**`saffron/cell/worktree.py`.** It is in `touches` only because both mutants
are applied there. Do not edit `DIFF_FLAGS`.

## Notes for the agent

**Both reads take `DIFF_FLAGS`, not a copied flag.** The mutants remove the
flag from `DIFF_FLAGS` itself, so a read that spells the flag out on its own
survives them, and `witness` fails. Copies drifting apart is how these two
reads were missed (backlog item 89). `saffron.repos` importing
`saffron.cell.worktree` creates no cycle: `worktree` imports only
`saffron.cell.runtime` and `saffron.intake`, and `saffron/repos/image.py`
already imports from `saffron.cell`.

**`DIFF_FLAGS` includes `--no-renames` and several patch-shape flags.** With
`--name-only` the patch-shape flags do nothing. `--no-renames` lists both sides
of a rename, which is what `scope` needs. The mirror's preserves witness has no
rename, so its expected list stays the same. Keep `-z` and the `quotePath`
override.

**The PACKAGE witness has a trap.** `packageable`'s spec has
`touches: ["src/**"]` (`tests/test_package.py:271`), so a root `.gitmodules`
is already out of scope, and `scope` fails today for that reason alone. A
witness that only checks for `scope fail` then passes at base, and `criteria`
refuses it. The refusal note carries counts, not paths (`scope.py:144-156`).
Make the submodule the thing that decides the result: give the task a spec
whose `touches` covers `.gitmodules` and not the submodule path, or assert on
something that names the submodule.
`test_unpackaged_work_outside_its_touches_is_not_pushed`
(`tests/test_package.py:3033`) shows how to drive the push.

**The mirror witness sets config, not `.gitmodules`.** A `.gitmodules` in the
commit proves nothing there: the bare mirror lists the submodule today
regardless, so that witness would pass at base. Point `GIT_CONFIG_GLOBAL` (with
`monkeypatch.setenv`) at a file that sets `diff.ignoreSubmodules = all`, and
check that the listing still names the submodule. The `origin` fixture in
`tests/test_mirror.py` builds the repository the mirror is cloned from.

**Build the submodule the way the existing test does.** `_commit_a_gitlink` in
`tests/test_worktree.py:1752` writes a gitlink with `update-index --cacheinfo
160000,…`. The `.gitmodules` text is at `:1828-1830`. Reuse the approach, not
the helper: it is private to that module.

**Name each reason.** Both edits are small. Say in a short comment on each read
that it takes `DIFF_FLAGS` so `scope` sees what the patch carries.
