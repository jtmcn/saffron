---
id: SA-0238
title: qualify reads an unreadable mirror path as an absent one
type: bug
priority: 2
estimated_lines: 79
estimate_measured: true
touches:
  - saffron/qualify.py
  - tests/test_qualify.py
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
  - saffron/repos/mirror.py
  - saffron/agents/findings.py
  - saffron/follow_up.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/finish.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - tests/test_cli.py
  - tests/test_follow_up.py
  - tests/test_findings.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 14
max_attempts: 3
max_turns: 90
acceptance:
  - claim: >-
      `qualify` lets every error `file_at` raises at a layer's head
      propagate out of it, the error's own type and message unchanged, and
      writes no `qualifications` row for the finding whose read raised. The
      witness drives each way `file_at` raises: a tree, a submodule, a
      symlink leaving the tree and a symlink to another symlink, each an
      `UnreadablePath`. It also drives a regular file whose blob the mirror
      lacks, a plain `GitError` from a failed `git show`. An absent path
      still reads as no file, so its finding is `unanchored`. A regular
      file and an in-tree symlink to one are still read, so a finding on
      either anchors.
    witness: tests/test_qualify.py::test_a_path_the_mirror_cannot_read_raises_out_of_qualify
    wrong_versions:
      - The read still catches `UnreadablePath` and answers `None`, so the four mode cases anchor nothing and raise nothing.
      - The read lets `UnreadablePath` through and still answers `None` for any other `GitError`, so the missing blob reads as an absent file.
      - The read re-raises every `GitError` as an `UnreadablePath`, so the missing blob's error is no longer a plain `GitError`.
      - The read wraps every `GitError` in a `ValueError` or another type outside `GitError`.
      - The read raises for an absent path too, so `src/z.py` raises instead of filing `unanchored`.
      - The read answers an empty string for an error rather than raising.
      - The read is bound to the range's base rather than its head, so the readable findings stop anchoring.
      - The range records each input as `unanchored`, its reason the error's text, before it re-raises.
  - claim: >-
      `cli._stack_follow_ups` turns a `RuntimeError` raised inside
      `follow_up.write_follow_ups` before `qualify` returns into one
      `follow-ups: stopped, ` line naming it. It returns no candidate and
      pools nothing beyond what was pooled before. `GitError` and
      `UnreadablePath` are both `RuntimeError`s, so this is how a stack
      batch reports the raise criterion 1 adds.
    witness: tests/test_cli.py::test_a_stack_batchs_follow_ups_are_qualified_and_written_from_the_pinned_base_at_the_stacks_top
    preserves: true
---

## Context

Backlog item **b-00534f**, found by #610's Standards seat in the spec
loop's run 23. It belongs to ADR 7's step 4, qualification in host code
(backlog item b-792ab2).

**What `qualify` does with a read today.** `_qualify_range` anchors each
range's findings with `anchor(inputs, diff, read_head=partial(_read_head,
mirror, head))` (`saffron/qualify.py:131`). `_read_head` calls `file_at` and
returns `None` on any `GitError` (`saffron/qualify.py:63-67`). `anchor` reads
a finding's file through `read_head` only when its line falls outside every
hunk (`saffron/agents/findings.py:214-220`). A `None` there makes the finding
unanchored (`saffron/agents/findings.py:221-222`). `_decide` then files it
`unanchored` (`saffron/qualify.py:183-184`), and the loop records that as a
`qualifications` fact (`saffron/qualify.py:173-178`).

**What `file_at` promises.** It returns `None` only when the tree at `sha`
has no entry at `path` (`saffron/repos/mirror.py:248-250`). Its docstring
ends "absent is an answer, unreadable is not" (`saffron/repos/mirror.py:246-247`).
It raises `UnreadablePath` for four shapes. A symlink whose target leaves the
tree is one, and a symlink whose target is not a regular file is another
(`saffron/repos/mirror.py:257-265`). Any mode but a regular file or a
symlink is the rest, which covers a tree and a submodule
(`saffron/repos/mirror.py:267-269`). `UnreadablePath` subclasses `GitError`
(`saffron/repos/mirror.py:43`). A git call that exits non-zero raises a plain
`GitError` through `_git` (`saffron/repos/mirror.py:60-63`). So today every
one of those reaches the ledger as a decision about the finding.

**The other copy is gone.** `SA-0161` carried a copy of `_read_head` into
`saffron/follow_up.py`, and #610's review removed it. That module no longer
catches a read error.

**How the raise reaches the operator.** `qualify` has one production
caller. `cli._stack_follow_ups` wraps it as `run_qualify`
(`saffron/cli.py:1125-1143`). It hands that to `follow_up.write_follow_ups`
(`saffron/cli.py:1179-1193`). That function's first statement calls it,
and nothing there catches a raise (`saffron/follow_up.py:237`). The
adapter's `except Exception` prints `follow-ups: stopped, <type>: <message>`
(`saffron/cli.py:1194-1196`). `run_qualify` sets `kept` only once the call
returns (`saffron/cli.py:1130`). The handler pools only under
`if kept is not None:` (`saffron/cli.py:1197`), then returns `[]`
(`saffron/cli.py:1215`). The
batch writes no follow-up from an empty list (`saffron/batch.py:788-793`). So
the night's exit code stays its stop reason's, and no row calls the broken
read a finding's outcome. Criterion 2 pins that path with the existing test,
whose `_raising_write_follow_ups` case raises a `RuntimeError` there
(`tests/test_cli.py:6850-6862`).

## Problem

A mirror read that fails is filed as a fact about the finding. `error` is
not `fail`: a gate that broke is never a verdict on the code, and a read
that broke is never a verdict on a finding. Today a submodule, an escaping
symlink or a failed `git show` turns an end-review finding into
`unanchored`. It then reaches `findings.json` as that outcome, and no
follow-up is ever written from it.

## Out of scope

- `file_at` itself, and what it counts as absent. `saffron/repos/mirror.py`
  is forbidden.
- The follow-up adapter's handling of the raise. It already reports any
  raise as one line, as criterion 2 pins. Making a stack batch exit `2` on a
  broken read is a separate decision about every follow-up error, not this
  one.
- The ranges a walk finished before the one that raised. Their
  `qualifications` facts stay written. Undoing them is a transaction this
  module does not own.
- REVIEW's own anchoring (`saffron/phases/review.py:364`) and the cell's
  (`saffron/cell/session.py:1842`). Both read through the worktree, not
  `file_at`.

## Notes for the agent

**The change is a deletion.** Remove `_read_head` and pass `file_at` itself,
bound to the mirror and the range's head, as `anchor`'s `read_head`. Drop
the `GitError` import it leaves unused. No catch of any kind stays between
`file_at` and `anchor`. Criterion 1 is an edit whose fix leaves no text a
mutant could pin at head, so it declares a witness and no mutant. Expect
`witness` to report `skip`. Criterion 2 is `preserves`, and that test
exists at base.

**The fixture, measured on 2026-10-07 (host git 2.54.0).** Give
`_stack_mirror` and `_build` a keyword `unreadable`, false by default. Every
existing test's mirror then stays as it is. When true, `_stack_mirror`
seeds these at commit `A`, before its `add -A`, and none of them is in any
range's diff.

- `vendor/sub`: a nested repository with one empty commit, made with the
  file's own `_git` helper. The parent's `add -A` records it as a
  submodule.
- `src/out.py`: a symlink to `../../outside.py`, which leaves the tree.
- `src/hop.py`: a symlink to `out.py`, a symlink rather than a regular file.
- `src/c_link.py`: a symlink to `c.py`, read through to `c.py` at `H2`.
- `src/gone.py`: a regular file with one line no other file holds.

After `H2` commits, `_stack_mirror` deletes `src/gone.py`'s loose object
under `.git/objects`, found with `rev-parse` of `<H2>:src/gone.py`. `ls-tree`
still lists it, so `file_at` reaches `git show`, which exits 128. The tree
case needs no seeding: `src` is a directory.

**The witness.** Build once with `unreadable=True`. For each case, set
`built.layers` to one `LayerReview` for `TE-2`'s key, carrying one `spec`
lens finding of severity `concern` and no probe, and call `built.run`. No
join, no probe, and no in-cell concern is in play.

- `src`, `vendor/sub`, `src/out.py` and `src/hop.py`, each at line 3:
  `pytest.raises(UnreadablePath)`, and the message starts with the path and
  ` at `.
- `src/gone.py` at line 3: `pytest.raises(GitError)`, its type exactly
  `GitError`, and the path in its message.
- `src/z.py` at line 1: returns, with that finding alone in the pool as
  `unanchored` and no group.
- `src/c.py` and `src/c_link.py`, each at line 11: returns, with that
  finding alone in one group for its own file and an empty pool. Line 11
  at `H2` shares `beta_rate` with the diff.

Give each finding its own claim. At the end, `TE-2`'s `qualifications` rows
hold exactly the three that returned, in order, and none of the five that
raised. Import `GitError` and `UnreadablePath` from `saffron.repos.mirror` at
module scope, since both exist at base. Keep `qualify` imported inside the
test body, as the file's other tests do.

Commit after the witness passes. Uncommitted work dies with the cell.
