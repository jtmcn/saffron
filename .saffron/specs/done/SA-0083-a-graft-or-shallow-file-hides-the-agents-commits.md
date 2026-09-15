---
id: SA-0083
title: a graft file or a shallow file in the worktree hides the agent's own commits from the host's count of them and its record of their subjects
type: bug
priority: 2
depends_on: [SA-0082]
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
      `commits_ahead` counts, and `commit_subjects` lists, every real commit
      between the base and head when the worktree carries a graft file that
      re-parents head onto the base. Today the count drops and the subjects
      lose every commit the graft skips. The count is how doneness is measured
      (§4.3), and the subjects are the only trace of the agent's own commits
      once the squash lands (§5.7).
    witness: tests/test_worktree.py::test_history_reads_see_through_a_graft_file
  - claim: >-
      The same two reads hold when the worktree carries a shallow file that
      cuts head off from its parents.
    witness: tests/test_worktree.py::test_history_reads_see_through_a_shallow_file
  - claim: >-
      `changed_files` still reads through a planted replacement ref, as it
      does today.
    witness: tests/test_worktree.py::test_changed_files_reads_through_a_planted_replacement
    preserves: true
  - claim: >-
      A stacked worktree exports exactly the child's own commit, as it does
      today.
    witness: tests/test_worktree.py::test_a_stacked_worktree_holds_the_parents_real_commits_and_only_the_childs_new_commit_is_exported
    preserves: true
---

## Context

`docs/BACKLOG.md` item **110**, found reviewing `SA-0074` (PR #228) on
2026-09-12. `SA-0074` pinned replacement refs off in `_git`
(`saffron/cell/worktree.py`), but a graft is not a replacement ref, and neither
is `.git/shallow`. Both change what history reads return. The diff is
unaffected, so `scope`, the gates and PACKAGE still judge the real tree. What
moves is `commits_ahead` and `commit_subjects`.

**Probed 2026-09-13** on git 2.39.5 (the cell image, `saffron/cell:saffron`) and
git 2.54 (the host). Both gave the same results. The fixture was three commits
(base, one touching a forbidden path, one innocent), each read through `_git`'s
own `-c` overrides:

| worktree carries | pin | count | subjects | name-only |
|---|---|---|---|---|
| nothing | — | 2 | both | both paths |
| `.git/info/grafts`: head → base | — | **1** | innocent only | both paths |
| the same | `--no-replace-objects` | **1** | innocent only | both paths |
| the same | `GIT_GRAFT_FILE=/dev/null` | 2 | both | both paths |
| `.git/shallow`: head | — | **1** | innocent only | both paths |
| the same | `GIT_SHALLOW_FILE=/dev/null` | 2 | both | both paths |
| the same | `GIT_GRAFT_FILE=/dev/null` alone | **1** | innocent only | both paths |
| both files | both variables | 2 | both | both paths |
| neither file | both variables | 2 | both | both paths |

Also measured on both versions:

- `git --shallow-file=…` is refused as an unknown option, so the shallow file
  has no command-line pin. `GIT_SHALLOW_FILE` is the only one, and git does not
  document it.
- Setting `GIT_GRAFT_FILE` makes git print its eight-line "grafts is
  deprecated" hint on stderr on every call, even with no graft file present.
  `-c advice.graftFileDeprecated=false` silences it.

The script is `docs/evidence/scripts/2026-09-13-history-and-diff-pins.sh`.

## Problem

Doneness is measured, never argued with (§4.3). An agent that writes one file in
its own `.git` makes the host undercount its commits and drop their subjects
from the squash body, with nothing to show for it.

## Out of scope

**Every other kind of `.git` state the agent can write.** This spec pins the two
files the probe showed moving these reads.

**A refusal instead of a pin**, meaning a task that fails because either file
exists. The pins restore the right answer, and a refusal would turn one written
file into a lost task.

## Notes for the agent

**Both pins are new code, so the criteria carry witnesses and no mutants.**

**Pin them in `_git`**, so every read the host takes of the worktree carries
them, as `SA-0074`'s replacement pin does. `runtime.exec_` takes no environment,
and `saffron/cell/runtime.py` is forbidden. Prefixing `env` with both variables
ahead of `git` in `_git`'s argument list works: the probe ran exactly that in
the cell image. Add `-c advice.graftFileDeprecated=false` alongside the other
`-c` overrides.

**`GIT_SHALLOW_FILE` is undocumented,** so its comment says it was measured, and
on which versions. A measured fact beats a reasoned one, and this is the line a
later reader would "simplify" otherwise.

**Ignoring the shallow file cannot break a read.** `prepare_worktree` seeds with
a full `git fetch`, so a cell never has a legitimate shallow file. One that
exists was written by the agent.

**This spec is cut from `SA-0082`'s branch**, which edits `DIFF_FLAGS` in the
same file. Read what it left before you add to it.

**Build the fixtures the way `_repo_with_a_planted_replacement` does:** config
isolated, then prove the plant first. A bare `rev-list --count` in the same repo
must be fooled before the pinned read is asserted. A graft file is one line,
`<head> <base>`, in `.git/info/grafts`. A shallow file is head's sha in
`.git/shallow`.

**No cell is needed.** `_host_git` runs `_git`'s argument list through
`subprocess` on the host, where `env` exists as well.

**Every new witness must fail with `worktree.py` reverted, not merely be missing
at base.** Import nothing new at module scope, because a module-scope import of
a name you add turns the reverted run into a collection error, which `revert`
reads as `skip`.

**Write any runner as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and `integrity` fails that suppression
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
