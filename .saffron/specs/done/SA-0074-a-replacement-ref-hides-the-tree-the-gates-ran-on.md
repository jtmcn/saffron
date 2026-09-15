---
id: SA-0074
title: a replacement ref planted in the worktree makes the host read a tree the gates never ran on
type: bug
priority: 1
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
      `changed_files` lists every path the worktree's real commits changed, even
      when the worktree carries a replacement ref that substitutes a benign
      commit for its own head. Today it lists the benign commit's paths, so
      `scope` judges a diff that is not the one the gates ran on.
    witness: tests/test_worktree.py::test_changed_files_reads_through_a_planted_replacement
  - claim: >-
      `export_patch` describes the real commits' content under the same
      replacement. The exported patch is what every gate result, every lens and
      PACKAGE read (§5.7), so a patch describing the benign tree ships a tree
      nothing checked.
    witness: tests/test_worktree.py::test_export_patch_reads_through_a_planted_replacement
  - claim: >-
      `read_at_head` returns a file's real content at head under the same
      replacement. It is what a critic finding outside a hunk is anchored
      against (§5.5), so a replaced blob moves where a finding can land.
    witness: tests/test_worktree.py::test_read_at_head_reads_through_a_planted_replacement
  - claim: >-
      A stacked worktree with no replacement exports exactly the child's own
      commit, as it does today.
    witness: tests/test_worktree.py::test_a_stacked_worktree_holds_the_parents_real_commits_and_only_the_childs_new_commit_is_exported
    preserves: true
---

## Context

`docs/BACKLOG.md` item **102**, found reviewing `SA-0072` (PR #219) on
2026-09-12, by probe. An agent that runs `git replace <real> <benign>` in its own
worktree changes what every git read of those objects returns. `_git` in
`saffron/cell/worktree.py` pins two settings with `-c`, and pins nothing about
replacement. Measured: `--name-only` went from `FORBIDDEN.md`, `src/a.py`,
`tests/test_x.py` to `src/a.py` alone, `git show HEAD:FORBIDDEN.md` returned the
benign content, and `rev-parse HEAD` still named the real commit.

Every read the host takes of a cell's worktree goes through `_git`:
`changed_files` and `export_patch` feed `scope` and the diff each gate and lens
reads (`saffron/gates/suite.py`), `read_at_head` anchors findings, and the
`revert` gate's checkouts use it too. The gates that run *code* run it from the
real files in `/work`, which replacement does not touch. So `scope` can judge
one tree while `tests` passes another.

**Probed in review:** a global option before the subcommand that disables
replacement refs restored all three reads. `-c core.useReplaceRefs=false` did
the same. The mirror never receives the cell's `refs/replace`, so the host-side
git in `saffron/phases/package.py` and `saffron/repos/mirror.py` is unaffected.

## Problem

A cell is untrusted, and every control that matters lives outside it (§2).
Replacement is a repo-local fact the agent can write, like the config
`DIFF_FLAGS` exists to beat, and `_git` beats the config and not the
replacement. What the host reads about the agent's work should be the objects
the agent committed, whatever the worktree says to substitute for them.

## Out of scope

**Settings that hide an edit's content without substituting objects.** Binary
rendering through `.git/info/attributes`, `core.attributesFile` and
`core.bigFileThreshold` is backlog item **103**, and the settings that move the
diff's shape are item **89**.

**Git that a repo's own declared gates run inside the cell.** Those scripts are
the target repo's (§2.1), and the cell's environment is set in
`saffron/cell/session.py`, which is forbidden here. This spec is the host's own
reads.

**The mirror and PACKAGE.** They never see the cell's refs, as above.

## Notes for the agent

**This spec adds a new option to `_git`, which is new code, so its criteria
carry witnesses and no mutants.** A mutant would have to pin the option's
spelling, and there are two that work.

**It belongs in `_git`, not in `DIFF_FLAGS`.** `DIFF_FLAGS` follows `diff` and
reaches only diffs. Replacement moves `show`, `rev-list`, `ls-tree` and
`checkout` too, and `_git` is the one function every one of them passes
through.

**Every new witness must fail with `worktree.py` reverted, not merely be missing
at base.** The `revert` gate re-runs each new witness against the reverted
source and blocks any that still pass. All three new criteria describe
something the unpinned `_git` gets wrong, so an honest test fails reverted.
Import nothing new at module scope: a module-scope import of a name you add
turns the reverted run into a collection error, which `revert` reads as `skip`.

**No cell is needed.** The host-git tests in `tests/test_worktree.py` already
point `worktree._git` at a real repo in `tmp_path` through `_host_git`. Use that
seam.

**Plant the replacement the way the probe did.** Make a real commit that
changes more than one file, build a benign commit on the same parent with fewer
changes (`git commit-tree` over a benign tree), and `git replace` the real head
with it. Then **prove the replacement, not only the pin**: before asserting
what the pinned read returns, assert that a bare `git` read in the same repo
returns the benign answer. Without that pairing the test passes on a git that
ignores replacement, exactly as `SA-0072`'s tests pair a bare diff with the
pinned one.

**Write any runner as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. One fixture shared by the three witnesses keeps well inside it.
