---
id: SA-0075
title: a cell's own git settings can print an edit as binary, so no lens reads its content
type: bug
priority: 2
depends_on:
  - SA-0074
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
      `export_patch` prints an edited text file's hunks even when the worktree
      sets `core.bigFileThreshold` low enough that every file counts as big.
      Today the patch says only that the binary files differ, so no lens reads
      the edit, and `integrity` errors the attempt, which is charged to nobody.
    witness: tests/test_worktree.py::test_export_patch_shows_hunks_under_a_tiny_big_file_threshold
  - claim: >-
      `export_patch` prints the hunks when the worktree's `core.attributesFile`
      names a file marking every path `-diff`. That file lives outside the
      repository, so no commit shows it and `integrity`'s check on a committed
      `.gitattributes` never sees why the content went missing.
    witness: tests/test_worktree.py::test_export_patch_shows_hunks_under_a_configured_attributes_file
  - claim: >-
      A stacked worktree with neither setting exports exactly the child's own
      commit, as it does today.
    witness: tests/test_worktree.py::test_a_stacked_worktree_holds_the_parents_real_commits_and_only_the_childs_new_commit_is_exported
    preserves: true
---

## Context

`docs/BACKLOG.md` item **103**, found reviewing `SA-0072` (PR #219) on
2026-09-12, by probe. Four repo-local settings make the pinned diff print
`Binary files a/f.py and b/f.py differ` with no hunks, while the name-only
listing is unchanged. Two of them are config that `_git` in
`saffron/cell/worktree.py` can override on the command line, the way it already
overrides `core.quotePath` and `diff.suppressBlankEmpty`.

**Re-probed 2026-09-12 on git 2.54**, against `DIFF_FLAGS` on a one-file edit:

| worktree setting | bare diff | with the `-c` override |
|---|---|---|
| `core.bigFileThreshold=1` | binary, no hunks | `-c core.bigFileThreshold=2g`: hunks |
| `core.attributesFile` naming `* -diff` | binary, no hunks | `-c core.attributesFile=/dev/null`: hunks |

`--numstat` printed `-	-	f.py` under `-diff`, so the added lines cannot be
counted any other way either.

PACKAGE refuses a binary change with no full index line (`_NO_FULL_INDEX` in
`saffron/phases/package.py`), so the hidden content does not reach a pull
request unreviewed. The task fails instead, and as infrastructure rather than
as its own failure. That is why this is tier 2 rather than tier 1.

## Problem

A cell is untrusted, and every control that matters lives outside it (§2).
What the critic reads is `export_patch`'s output (§5.5), and a setting the
agent can write decides whether that output contains the edit at all. `_git`
already pins two settings for the same reason. These two are the same kind of
setting and are not pinned.

## Out of scope

**`.git/info/attributes`**, and a `diff.<driver>.binary` driver that it
assigns. No `-c` override reaches them: `core.attributesFile=/dev/null` did not.
`--text` did restore the hunks in the probe above, but it also renders every
genuinely binary file as text. That changes what `integrity`'s binary check sees
and whether PACKAGE's no-full-index refusal ever fires. It is a design decision,
so it stays in item 103.

**`integrity`'s comment** about a `--numstat` cross-check. The probe above
falsified it, and it was corrected by hand beside this spec, because
`saffron/gates/**` is forbidden here.

**Settings that change the diff's shape without hiding content.** Those are item
**89**.

**Git that a repo's own declared gates run inside the cell.** Those gates belong
to the target repo (§2.1). This spec covers the host's own reads.

## Notes for the agent

**Both overrides are new entries in `_git`'s argument list, which is new code,
so the criteria carry witnesses and no mutants.** A mutant would have to pin a
spelling you have not yet written.

**They belong in `_git`, not `DIFF_FLAGS`.** A `-c` override has to come before
the subcommand, and `DIFF_FLAGS` comes after `diff`. The `-c` entries already
in `_git` are where these go, and the comment above them is where the reason
goes.

**This spec is cut from `SA-0074`'s branch**, which also edits `_git`. Read
what it left there before you add to it.

**Prove the setting, not only the override.** In each witness, first assert
that a bare `git diff` in the same repo prints `Binary files` for the edited
file. Then assert that `export_patch` prints its hunk. Without that pairing the
test passes on a git that ignores the setting, which is how `tests/test_scope.py`
pairs a bare diff with the pinned one.

**Isolate the test from the operator's own git config.** Set
`GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1` as
`tests/test_scope.py` does. Also set `XDG_CONFIG_HOME` to a directory inside
`tmp_path`: `core.attributesFile` defaults to a file under it, so an operator's
own attributes file would otherwise reach the reference diff.

**No cell is needed.** `_host_git` in `tests/test_worktree.py` points
`worktree._git` at a real repo in `tmp_path`, and `export_patch` takes any
container name through it.

**Every new witness must fail with `worktree.py` reverted, not merely be missing
at base.** The `revert` gate re-runs each one against the reverted source and
blocks any that still pass. Import nothing new at module scope: a module-scope
import of a name you add turns the reverted run into a collection error, which
`revert` reads as `skip`.

**Write any runner as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. One fixture shared by both witnesses keeps well inside it.
