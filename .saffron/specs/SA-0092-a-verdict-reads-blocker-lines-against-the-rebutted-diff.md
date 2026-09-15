---
id: SA-0092
title: a verdict session reads each blocker's line number against the diff after the rebuttal, where a committed fix has already moved it
type: bug
priority: 3
depends_on: [SA-0089]
touches:
  - saffron/phases/rebut.py
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/cell/session.py
  - tests/test_rebut.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/agents/context.py
  - saffron/agents/artifacts.py
  - saffron/agents/findings.py
  - saffron/agents/prompts/implement.md
  - saffron/agents/prompts/review-*.md
  - saffron/phases/review.py
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/gates/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/replay.py
budget_usd: 8
max_attempts: 3
max_turns: 60
risk: elevated
acceptance:
  - claim: >-
      Each verdict session's system prompt carries the diff its lens's
      blockers were filed and anchored against, as well as the diff after the
      rebuttal, and says which of the two the blocker line numbers refer to.
      Today it carries only the diff after the rebuttal, so a blocker whose fix
      was committed names a line that has since moved.
    witness: tests/test_rebut.py::test_the_verdict_prompt_carries_the_diff_its_blockers_were_filed_against
  - claim: >-
      `saffron cell` hands REBUT the diff REVIEW's lenses were shown, not a
      diff exported again after the rebuttal turn.
    witness: tests/test_session.py::test_the_verdict_prompt_carries_the_diff_the_lenses_were_shown
---

## Context

Found 2026-09-14 while checking REBUT against the rule, from
`keli-wen/agentic-harness-patterns-skill`, that a fresh session's prompt must
hold everything it depends on. A line number that refers to a tree the session
is not shown is a dependency the session does not hold.

`blocker_lines` (`saffron/phases/rebut.py`) renders each blocker as
`N. [lens] file:line — claim`. `file:line` is the finding as REVIEW filed it,
anchored against the diff REVIEW's lenses were shown (`anchor` in
`saffron/agents/findings.py`). The verdict prompt (`rebut-verdict.md`) shows
those lines under "Your findings", then shows "The diff, after the rebuttal":
`run_rebut` calls `diff()` after the rebuttal turn, and when the implementer
fixed and committed, that is a different diff. Nothing tells the critic that
its line numbers belong to the earlier one.

A critic that reads line 40 of the file as it now stands can find different
code there, and withdraw a blocker because "that line no longer does that."
A withdrawal is the one verdict nobody re-reads: `sustained_blockers` counts
only `confirmed`. This is reasoned from the code and has not been seen in a
recorded night.

## Problem

A verdict session is shown the line numbers of one tree and the diff of
another.

## Out of scope

**Re-anchoring findings onto the post-rebuttal tree.** The numbers stay what
REVIEW recorded. They are the ledger's and the pull request body's too, and
`anchored_blockers` says the order is load-bearing.

**Where either diff is read from.** `SA-0087` moved REVIEW's diff to the critic
cell and `SA-0088` moved `diff()` there. Keep both sources. The diff REVIEW was
shown is a string `session.py` already holds when it calls `run_review`: pass
that string, and do not export it a second time.

**The lens templates.** `SA-0091` reorders them. The verdict template's own
order is a later spec.

## Notes for the agent

**The criteria carry witnesses and no mutants.** The new argument and the new
prompt block are new code, so no text exists yet that a mutant could pin
honestly. `witness` will report `skip`, and that is expected.

**Read `SA-0088`'s change to `run_rebut` before editing it.** This spec stacks
on `SA-0089`, which stacks on `SA-0088`. `diff()` and the verdicts must read the
same tree (`SA-0088`, Notes), and nothing here changes that.

**Say which diff the numbers belong to, in the template.** The two diffs get
headings that tell them apart, and the instruction above "Your findings" says
the line numbers refer to the diff the findings were filed against. Keep the
verdict contract, one entry per finding with `finding`, `verdict` and `reason`,
exactly as it is.

**Test the rebut half through `run_rebut`, not `verdict_prompt` alone.** Give
it a filed-against diff and a `diff()` that returns something different, record
the verdict session's options, and assert its system prompt carries both. For
the session half, test through `_drive`: make the exported patch differ before
and after the rebuttal turn, and assert the verdict prompt, the one carrying
`## The rebuttal`, holds the diff the lens prompts held. Reverted, the verdict
prompt carries only the later diff, so honest tests of both criteria fail.
Import nothing new at module scope: a module-scope import of a name you add
turns the reverted run into a collection error, which `revert` reads as `skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. Both diffs are bounded by that same gate, so the verdict prompt at
most doubles a bounded diff.
