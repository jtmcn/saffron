---
id: SA-0137
title: A global `attr.tree` prints an edit as binary on the cell's git 2.47, and `git_argv` does not pin it
type: bug
priority: 2
depends_on: []
touches:
  - saffron/cell/worktree.py
  - tests/test_worktree.py
forbidden:
  - harness/**
  - tests/test_package.py
  - tests/test_session.py
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - records/**
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
budget_usd: 16
max_attempts: 3
max_turns: 130
risk: elevated
acceptance:
  - claim: >-
      When the agent's global git config sets `attr.tree` to a tree whose
      `.gitattributes` marks every path `-diff`, an edited text file still
      shows its hunks in two reads: `_git`'s diff in the worktree's own git
      dir, and `export_patch`. A genuinely binary file committed in the same
      range still reads as binary in both. A key `git_argv` does not pin is
      still read from the global config file `GIT_CONFIG_GLOBAL` names.
      Today both reads print only that
      the text file's binary content differs.
    witness: tests/test_worktree.py::test_git_argv_shows_hunks_under_a_global_attr_tree
---

## Context

Backlog item **b-a9ee32**.

`git_argv` (`saffron/cell/worktree.py:169-205`) prefixes every in-cell git
call with `-c` pins. Two of them, `core.bigFileThreshold` and
`core.attributesFile` (`:201`, `:203`), stop a setting from printing an edit
as `Binary files differ` (backlog item 103). `_git` (`:208-209`) runs
`git_argv` in the worktree's own git dir. `export_patch` (`:250-269`) builds
its script's git prefix from `git_argv()` (`:260`). It then reads the diff
through a fresh bare git dir that borrows the worktree's objects (`:237-247`).
That fresh dir is `SA-0118`'s answer to the attribute files in `.git/info`.
The agent's global config still reaches it, which is why `SA-0118`'s
witnesses plant their settings there (`tests/test_worktree.py:1699-1708`).

No pin covers `attr.tree`. It names a tree whose `.gitattributes` git reads
in place of the worktree's.

**Measured 2026-09-23** by the operator's delegate, on git 2.47.3 in
`saffron/cell:saffron` and git 2.54 on the host, with git 2.39.5 as a control:

1. A global `attr.tree` naming a tree whose `.gitattributes` holds
   `* -diff` makes the fresh-dir read `export_patch` uses print
   `Binary files a/f.py and b/f.py differ` with no hunks. The tree was built
   with `git hash-object -w` and `git mktree`, and never committed. This
   holds on 2.47.3 and 2.54. On 2.39.5 the setting has no effect.
2. `-c attr.tree=` restores the hunks on 2.47.3 and 2.54. On 2.39.5 it is
   accepted and changes nothing: exit 0, the same hunks.
3. With a committed `.gitattributes` holding `f.py -diff` and a genuine
   binary (NUL bytes) added in the range, the pin changes nothing on all
   three gits. The worktree's own diff prints both files as binary with and
   without it. The fresh-dir read prints `f.py`'s hunks and the binary as
   binary with and without it.
4. In the worktree's own git dir, a global `attr.tree` also turns the edit
   binary on 2.47.3 and 2.54.

**The cell must carry git 2.47.** Pull request #488 moved
`images/cell-base.python.Dockerfile` to `python:3.12-slim-trixie`
(`:11-12`), whose git is 2.47.3 (item b-b5f379). It is a hand pull request,
so no spec names it in `depends_on`. `saffron.repos.image` builds the base
from the checkout that runs `saffron cell` (`saffron/repos/image.py:18-19`,
`:61-67`). So this spec's cell runs from a checkout whose images carry #488.
On a 2.39.5 image the witness's first assertion fails at head, loudly, and
the `tests` gate fails the attempt.

## Problem

A cell is untrusted, and every control that matters lives outside it (§2).
The critic reads `export_patch`'s output (§5.5). One global setting the
agent can write decides whether that output holds the edit at all. On the
cell's git 2.47.3 it now does. For a file inside `touches`, `integrity`
then errors the attempt (`saffron/gates/core/integrity.py:243-252`), which
is charged to nobody (§5.4).

## Out of scope

**Repo-local and system config.** A `-c` pin outranks both, so the global
case is the one witnessed. Neither is witnessed separately.

**`GIT_ATTR_SOURCE` and `--attr-source`.** A cell cannot set an environment
variable or a flag on a host exec, the argument `SA-0118` made for
`GIT_DEFAULT_HASH`.

**Other copies of the pins.** `harness/recovery.py`'s `pinned_diff` spells
two of them on a repo the host built. `saffron/cell/session.py:1070` and
`:1097` take theirs from `git_argv`, as `tests/test_session.py:4443-4446`
does, so a new pin needs no edit there.

**Where the global config lives.** The witness writes the file
`GIT_CONFIG_GLOBAL` names. The `-c` pin outranks every global file, so its
half holds wherever that file is. The half that keeps other keys readable
is not driven for `~/.gitconfig` or the XDG path.

**The image.** Bumping the cell's git is item b-b5f379, done by hand in #488.

## Notes for the agent

**New code, so a witness and no mutant.** The pin does not exist at base,
so there is no text for a mutant to name. `revert` drives the witness
instead. It bites only on a git that reads `attr.tree`, which is why the
image must carry #488.

**The pin.** Pin `attr.tree` empty with a `-c` entry in `git_argv`, beside
the two from item 103. Name item b-a9ee32 in a one- or two-line comment.
`export_patch` takes its prefix from `git_argv()`, so one entry reaches both
reads. Leave the global config readable. `SA-0118`'s witnesses plant their
settings there, and their mutants die only through that file.

**The witness**, modelled on
`test_export_patch_shows_hunks_under_a_configured_attributes_file`
(`tests/test_worktree.py:1858`):

1. Build on `_isolated_repo_with_a_text_file`
   (`tests/test_worktree.py:1647`). Point the global config outside the
   repo with `_point_global_config_outside_the_repo`
   (`tests/test_worktree.py:1699`). Write every key with `_set_global`
   (`tests/test_worktree.py:1707`).
2. Write a file holding a NUL byte, then call `_edit_and_commit_f`
   (`tests/test_worktree.py:1670`), so both land in one commit.
3. After that commit, build the attributes tree in the worktree's own
   object store with `git hash-object -w --stdin` and `git mktree`. Commit
   nothing. The fresh dir finds the tree through `objects/info/alternates`.
   Set `attr.tree` to it globally.
4. Set one more global key that no pin names, with any value.
5. Prove the setting bites. A plain `git diff base..HEAD` in the repo prints
   `f.py`'s block as binary. Check it per path with `_diff_block`
   (`tests/test_worktree.py:1689`).
   `_assert_bare_diff_is_binary` accepts any `Binary files` line, and the
   NUL file supplies one whether or not `attr.tree` bites.
6. Read `worktree._git("c", "diff", f"{base}..HEAD")` through the
   `_host_git` seam that step 1's fixture installs. Assert `f.py`'s block
   holds `+one = 2` and no `Binary files`, and the NUL file's block reads
   `Binary files`.
7. Assert the same three things of `worktree.export_patch("c", base)`.
8. Assert `worktree._git("c", "config", "--get", <step 4's key>)` prints
   step 4's value.

Never run `git config --global` in a test. Import nothing new at module
scope, or the reverted run is a collection error that `revert` reads as
`skip`.

**Wrong versions the witness must kill:**

- A pin in `export_patch`'s script alone, so `_git`'s read still hides the
  edit.
- A pin in `_git` alone, so `export_patch`'s prefix lacks it.
- `--text` in `DIFF_FLAGS`, which prints the NUL file as text.
- An environment entry in `git_argv` that stops git reading the global
  config, such as one pointing `GIT_CONFIG_GLOBAL` at `/dev/null`. It hides
  step 4's key.

**The `size` gate counts tests.** A `bug` gets 1300 tokens, and the gate
blocks at `elevated`. Keep the witness's docstring to one or two lines.
