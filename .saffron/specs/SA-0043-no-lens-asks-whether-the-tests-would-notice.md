---
id: SA-0043
title: no lens asks whether the tests would catch the code being wrong
type: feature
priority: 1
depends_on: []
touches:
  - saffron/phases/review.py
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/review-contract.md
  - tests/test_review.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/findings.py
  - saffron/agents/context.py
  - saffron/phases/implement.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/report/**
  - images/**
acceptance:
  - claim: >-
      A third lens is declared, and its remit is whether the suite would notice
      the code being wrong. `saffron/phases/review.py` gains one entry and one
      prompt file; nothing else has to learn about it, because `run_review`
      iterates the mapping rather than a second list.
    witness: tests/test_review.py::test_the_declared_lenses_are_the_three_that_run
  - claim: >-
      The remits stay disjoint. The test-adequacy language leaves the
      correctness lens's own remit list, and each of the three prompts names
      the other two's territory as not its own — two lenses sharing a remit
      reads as corroboration, and there is no vote.
    witness: tests/test_review.py::test_exactly_one_prompt_claims_the_test_adequacy_remit
  - claim: >-
      The new lens must state what it cannot verify. It holds no tool that can
      run anything, so every finding names the edit that would keep the suite
      green — a claim someone who *can* run it checks in one command, rather
      than an assertion about coverage the lens cannot have made.
    witness: tests/test_review.py::test_the_adequacy_prompt_demands_a_checkable_mutation
  - claim: >-
      Every declared lens still runs exactly once, in a fresh session, and
      never resumes. Adding a third must not turn the loop into one that
      reuses a transcript.
    witness: tests/test_review.py::test_every_declared_lens_runs_once_and_never_resumes
    preserves: true
  - claim: >-
      The host still stamps the lens on every finding. A lens that names its
      own lens can file under someone else's remit and the drop rate would
      still read clean.
    witness: tests/test_review.py::test_findings_are_stamped_with_the_lens_that_filed_them
    preserves: true
budget_usd: 12
max_attempts: 3
max_turns: 110
risk: elevated
---

## Context
The critic has two lenses. `correctness` covers what the code *computes* —
time, boundaries, missing data, units, order. `contract` covers what a
downstream consumer depends on. Neither asks whether the tests would notice the
code being wrong, and `docs/BACKLOG.md` item 6 has said so since 2026-08-25:
*"No lens asks whether the tests would catch the code being wrong, and a critic
that reads the diff without mutating it cannot."*

Six specs later that gap is the dominant source of post-package defects. On the
spec that ran the day this one was written, both lenses returned **zero**
findings and an independent review found a blocker in the first pass. The two
defects it found, each reproduced by hand:

- one field of an event changed from `PACKAGE` to `REVIEW` — every terminal
  line the phase prints, and every logged event, silently mislabelled — and
  **1163 tests passed**;
- five call sites rewritten to bypass the seam the spec existed to build, and
  **1165 tests passed**, lint and types green.

Both are one class: *the test does not fail when the behaviour is broken.* The
same class had already appeared twice in the two preceding specs.

The research record under `docs/evidence/` priced the four candidate answers to
this remit and its recommendation is **a prompted lens, not a mutation tool**:
diff-scoped coverage reports nothing on the motivating defect by construction,
one mutation tool scopes to a diff and misses the defect class, the other finds
it and cannot scope below a function — while a prompted lens named the defect,
its cause and its exposing input three times out of three, from the diff alone.
This spec is that lens.

## Problem
- **The remit exists in the wrong prompt.** The correctness lens's own remit
  list ends with an `Evidence` bullet naming *"a test that would pass
  identically before this change"* — the test-adequacy remit, filed under a
  lens whose other five bullets are data semantics. Item 6 records that both
  lenses once filed the same finding and that an overlap is a prompt defect,
  not a duplicate to deduplicate: §5.5's no-voting rule rests on the remits
  being disjoint by construction. Adding a third lens without moving that
  bullet creates the overlap the item warns about.
- **A test asserts the lens set is exactly two, and its stated reason is no
  longer true.** It says nothing carries a risk tier. `effective_risk` now
  computes one on every attempt and `size` already reads it. The assertion has
  to change for this spec to land at all; the point is to change it to what is
  true rather than to delete the check.
- **The lens cannot run anything, and its prompt must be written for that.**
  The critic's tools are read-only by design — a critic that can run a command
  can change the thing it is judging. So this lens cannot do what found the
  defects above. What it *can* do is name the mutation that would survive, and
  a finding shaped that way is checkable in one command by the operator, the
  implementer, or a later gate.

## Out of scope
**A risk tier on this lens.** Item 6's done condition says the third lens runs
at `elevated`. Measured against this repo's own specs: **28 of 34 declare
`elevated`**, so a tier gate would exclude six specs while costing an edit to
the supervisor, which is `forbidden` here and carries the operator-visibility
batch's changes. Run it at every tier and record the deviation. The cost is one
fresh session — measured at $0.76 and $0.91 for the two existing lenses on the
spec above — and the review phase is deliberately not gated on the host budget
ceiling, so this does not make a task fail for money.

**The blast-radius lens.** §5.5's original third lens. Item 6 explicitly retired
that plan in favour of this remit; leave it undeclared and keep asserting that
it is.

**Any mutation tool, and any coverage gate.** Both were priced and both lost.
Reaching for either here is re-deciding a question with a written record.

**`revert`.** The gate that answers whether the new tests test *anything*. This
lens asks whether they test *each thing*. They are not substitutes and it is a
separate spec.

**Changing what a finding is.** No new severity, no new field, no change to
anchoring or the drop rate. Those are the instruments that will tell you
whether this lens is any good; changing them in the diff that introduces it
destroys the measurement.

## Notes for the agent
**The prompt file is the deliverable.** The code change is one line in the
`LENSES` mapping. Everything that decides whether this works is prose, and the
two existing prompt files are the form to follow exactly — the framing sentence,
the "do not manufacture one" clause, the bounded remit, the explicit *Not
yours* list, the three severities, and the `<output>` block contract. A
parametrised test already asserts most of that shape over every declared lens,
so a new prompt missing any of it fails immediately.

**Write the remit as questions about evidence, not about coverage.** The lens
cannot know what is covered. It can read a test and ask what would still pass
if a named line changed. Useful shapes, all drawn from real defects in this
repository: an assertion on a field the renderer never reads; a test that
constructs the value it then asserts; a structural assertion over source text
that any rename or reformat defeats; a witness that would pass unchanged
against the parent commit; a test whose setup is the only input the new code is
correct for.

**Severity is where this lens will fail first.** A test-adequacy lens has more
true-but-trivial findings available to it than either existing lens — every
test in a diff can be made stronger. `note` exists so that filing everything as
a `concern` is visibly wrong, and the concern count is what the morning queue
sorts on. Say in the prompt that a stronger assertion nobody would act on is a
`note`.

**Move the `Evidence` bullet, do not copy it.** After this change the phrase
about a test that would pass identically before the change must appear in
exactly one prompt file. Both existing prompts also need their *Not yours* list
extended so all three lenses name all three boundaries.

**Two of this spec's own witnesses live in a file it may edit.** `tests/test_review.py`
is in `touches` because the lens-set assertion has to change; the criteria
marked `preserves` are in that same file and must be green before and after,
untouched. Weakening one to make room for the third lens satisfies the
`criteria` gate and destroys the thing the criterion was protecting — this is
the exact move the two specs before this one had to have reverted in review.

**Cite code by file and symbol, never by line number**, and do not backtick a
path in an acceptance criterion that this spec's `touches` does not cover — gate
0 reads the criteria's own backticked path tokens and refuses on the first one
it cannot match, reporting only that one.

**Record the deviation in `docs/BACKLOG.md`.** Item 6's done condition names a
risk tier and this spec deliberately does not build one. An item closed against
a condition it did not meet is worse than an item left open: say which half
landed, and that the tier is the half that did not.

Commit after each coherent step. Uncommitted work dies with the cell.
