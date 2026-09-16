---
id: SA-0091
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
  - tests/test_events.py
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
budget_usd: 16
max_attempts: 3
max_turns: 90
risk: elevated
acceptance:
  - claim: >-
      Each verdict session's system prompt carries the diff its lens reviewed,
      as well as the diff after the rebuttal, and says that the blocker line
      numbers refer to the files as they stood when the findings were filed —
      naming that block by its own heading, never by its position, so the
      sentence stays true wherever the block sits. Today the prompt carries
      only the diff after the rebuttal, so a blocker whose fix was committed
      names a line that has since moved.
    witness: tests/test_rebut.py::test_the_verdict_prompt_carries_the_diff_its_blockers_were_filed_against
  - claim: >-
      A task hands REBUT the diff REVIEW's lenses were shown, in addition
      to the diff after the rebuttal, which it still exports. The reviewed
      diff is not re-exported to stand in for it.
    witness: tests/test_session.py::test_the_verdict_prompt_carries_the_diff_the_lenses_were_shown
  - claim: >-
      A verdict still lands on the finding REVIEW recorded, under the number
      the implementer answered, as it does today.
    witness: tests/test_session.py::test_a_verdict_lands_on_the_finding_the_review_recorded
    preserves: true
---

## Context

Found 2026-09-14 while checking REBUT against the rule, from
`keli-wen/agentic-harness-patterns-skill`, that a fresh session's prompt must
hold everything it depends on. A line number that refers to a tree the session
is not shown is a dependency the session does not hold.

`blocker_lines` (`saffron/phases/rebut.py`) renders each blocker as
`N. [lens] file:line — claim`. `line` is a line in the file as it stood at the
HEAD REVIEW read: the lens prompt asks for one "as it stands after the change",
and `anchor` (`saffron/agents/findings.py`) checks it against that diff's hunks
or that tree's files. The verdict prompt (`rebut-verdict.md`) shows those lines
under "Your findings", then shows "The diff, after the rebuttal": `run_rebut`
calls `diff()` after the rebuttal turn, and when the implementer fixed and
committed, that is a different diff. Nothing tells the critic that its line
numbers belong to the earlier tree.

A critic that reads line 40 of the file as it now stands can find different
code there, and withdraw a blocker because "that line no longer does that."
A withdrawal is the one verdict nobody re-reads: `sustained_blockers` and
`unkept_fixes` count only confirmed verdicts. This is reasoned from the code and has not been seen in a
recorded night.

## Problem

A verdict session is shown the line numbers of one tree and the diff of
another.

## Out of scope

**Re-anchoring findings onto the post-rebuttal tree.** The numbers stay what
REVIEW recorded. They are the ledger's and the pull request body's too, and
`anchored_blockers` says the order is load-bearing.

**Findings anchored outside any hunk.** The reviewed diff does not show such a
line, so for those the critic still reads the file as it now stands. Showing
the line's text as filed would need `Finding` to carry it, in
`saffron/agents/findings.py`, which is a later spec.

**Where either diff is read from.** `SA-0087` moved REVIEW's diff to the critic
cell and `SA-0088` moved `diff()` there. Keep both sources. Pass REBUT the
exact diff string `run_review` was handed, and do not export it a second time.
`critic_cell` yields the container, not a diff, and the reviewed diff is
exported at the `run_review` call site in `session.py`: bind that expression to
a name and hand the name to both `run_review` and `run_rebut`. Criterion 2's
"not re-exported" is already observable — `tests/test_session.py`'s
`test_rebut_verdicts_read_a_tree_rebuilt_from_the_post_rebuttal_patch` counts
the critic container's exports, and a third one reds it.

**Reordering the verdict template's blocks for prompt caching.** Whether
sessions can share a cached prompt is backlog item 126, and it waits on a
measurement. This is not licence to leave the new block anywhere: wherever it
goes, the instruction must name it by its heading, because an instruction that
says "the first diff" above a block printed second tells the critic exactly the
false thing this spec exists to remove.

## Notes for the agent

**The first two criteria carry witnesses and no mutants; the third is
`preserves`.** The new argument and the new prompt block are new code, so no
text exists yet that a mutant could pin honestly. `witness` will report `skip`
on the first two, and that is expected.

**Read `SA-0088`'s change to `run_rebut` before editing it.** This spec stacks
on `SA-0089`, which stacks on `SA-0088`. `diff()` and the verdicts must read the
same tree (`SA-0088`, Notes), and nothing here changes that.

**Say which tree the numbers belong to, in the template.** The two diffs get
headings that tell them apart, and the instruction above "Your findings" says
the line numbers refer to the files as they stood when the findings were filed,
naming the block by its heading rather than by its position — "the first diff"
is false the moment the block is appended instead, and every observation this
spec declares still passes when it is. "What to emit" already opens "the diff below
is the change as it now stands" — with two diffs below it that sentence names
neither, so make it say which one it means. Keep the verdict contract, one entry per
finding with `finding`, `verdict` and `reason`, exactly as it is.

**Test the rebut half through `run_rebut`, not `verdict_prompt` alone.** Give
it a reviewed diff and a `diff()` that returns something different, record the
verdict session's options, and assert its system prompt carries both — and the
instruction above `## Your findings` with them. Two containment checks alone
pass on a prompt whose second diff has no heading and no instruction, which
leaves the critic exactly as unable to read a line number as it is today.

**`run_rebut` has a caller outside `tests/test_rebut.py`.** `tests/test_events.py`
drives it too, which is why that file is in `touches`. A new argument is
required, not defaulted, following `run_rebut`'s own `spec_id`. (That
comment's stated reason is its own — the phase authors its own
`PhaseStart` line. The reason here is that a default would let a caller
keep today's behaviour without noticing.)

**Pre-bind the reviewed diff, the way `session.py` pre-binds `reviews` and
`recorded`.** `repair_loop` can hand back `EXHAUSTED` or `GATE_ERROR` and skip
REVIEW entirely, so a name assigned only inside `if outcome ==
"READY_FOR_REVIEW":` and read inside the REBUT branch reads as possibly-unbound
to the blocking `types` gate. The comment above those two names says why.

**Test the session half through `_drive`, with a patch stub that changes only
in the new witness.** `_stub_the_runtime` in `tests/test_session.py` returns one
fixed patch for every export, and after `SA-0087` and `SA-0088` the diffs are
read from critic cells. Read the stub as it stands when you start. Make the
exported patch differ before and after the rebuttal turn inside the new witness
alone: other tests, the `preserves` witness among them, anchor findings against
the fixed patch. Assert that the verdict prompt, the one carrying
`## The rebuttal`, holds the diff the lens prompts held.

**Both witnesses must fail with the source reverted.** Reverted, the verdict
prompt carries only the later diff, so honest tests of both criteria fail.
Import nothing new at module scope: a module-scope import of a name you add
turns the reverted run into a collection error, which `revert` reads as `skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. Both diffs are bounded by that same gate, so the verdict prompt at
most doubles a bounded diff.
