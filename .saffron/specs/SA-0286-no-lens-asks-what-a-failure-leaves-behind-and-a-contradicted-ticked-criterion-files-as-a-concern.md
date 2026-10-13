---
id: SA-0286
title: No lens asks what a failure leaves behind, and an adequacy finding that contradicts a ticked criterion files as a concern
type: bug
priority: 1
depends_on: []
estimated_lines: 155
estimate_measured: true
touches:
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/review-adequacy.md
  - tests/test_review.py
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
  - records/**
  - harness/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/report/**
  - saffron/agents/context.py
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-conventions.md
  - saffron/agents/prompts/end-review-join.md
  - saffron/agents/prompts/end-review-spec.md
  - saffron/agents/prompts/end-review-standards.md
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/agents/prompts/criterion-probe.md
  - saffron/agents/prompts/wrong-version.md
  - saffron/agents/prompts/implement.md
  - saffron/agents/prompts/turns/**
  - tests/test_corpus.py
  - tests/test_session.py
  - tests/test_scheduler.py
budget_usd: 24
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      The correctness lens's prompt, as `review.lens_prompt` renders it, ends
      its remit with a bullet asking what a failure leaves behind. The bullet
      names three ways a path stops early, a raise, a non-zero exit and an
      interrupted write, and four things one can leave, a truncated file, a
      half-applied restore, an undo over uncommitted work and cleanup that
      runs only on success. The remit keeps its five other bullets. Its edge
      sentence claims what a failure leaves behind, and no bullet of its
      Not-yours list hands that away. None of the contract, adequacy and
      conventions prompts claims the bullet in its own remit.
    witness: tests/test_review.py::test_the_correctness_lens_asks_what_a_failure_leaves_behind
    mutant:
      file: saffron/phases/review.py
      find: '"correctness": "review-correctness.md",'
      replace: '"correctness": "review-contract.md",'
    wrong_versions:
      - The failure-path bullet placed in the Not-yours list, after the edge sentence, or anywhere but last in the remit.
      - The failure-path bullet written over the order-and-state bullet, so the remit still holds five bullets.
      - A base bullet dropped and a second new bullet added before the failure-path bullet, so the count stays six.
      - The edge sentence left as it stands at base, so a truncated file reads as a stored format another lens holds stable.
      - A Not-yours bullet that hands what a failure leaves behind to the contract lens.
      - The bullet copied into the contract prompt's remit as well.
      - A witness that reads the prompt file by path rather than through `review.lens_prompt`.
  - claim: >-
      The adequacy lens's prompt, as `review.lens_prompt` renders it, keeps
      its `blocker` level for a test that reads as coverage of an acceptance
      criterion but is not. That level now also names any adequacy finding
      that contradicts an acceptance criterion the pull request body renders
      as satisfied, and says it files as a `blocker`, never as a `concern`.
      None of the correctness, contract and conventions prompts carries that
      sentence.
    witness: tests/test_review.py::test_the_adequacy_lens_files_a_contradicted_ticked_criterion_as_a_blocker
    mutant:
      file: saffron/phases/review.py
      find: '"adequacy": "review-adequacy.md",'
      replace: '"adequacy": "review-correctness.md",'
    wrong_versions:
      - The contradicted-criterion sentence placed in the remit or the instruction rather than the `blocker` bullet of the severity section.
      - The sentence calling such a finding a candidate for a `blocker` rather than a `blocker`.
      - The coverage case dropped from the `blocker` bullet when the new case is added.
      - The sentence added to every lens prompt rather than the adequacy prompt alone.
  - claim: >-
      The conventions prompt's list of the other lenses' remits is unchanged.
      The correctness, contract and adequacy prompts' Not-yours lists each
      still end with the conventions lens's remit.
    witness: tests/test_review.py::test_the_four_lenses_declare_disjoint_remits
    preserves: true
---

## Context

Backlog item **79** (`DESIGN.md` §5.5, §5.4). Line numbers were read at
`cf3db797`.

**The failure-path gap is open on the current prompts.** Item 79's own
record says a 2026-09-07 pass raised both of `SA-0062`'s graded defects.
The latest corpus pass disagrees. It has `dirty-restore` and
`truncating-write` each seen in one run of three and graded in none
(`docs/evidence/2026-09-11-lens-corpus-spread.md:49-50` and `:92`). Both
defects are what a failed write leaves behind, and neither needs a run to
find.

**Track C settles the shape.** Widen the correctness lens's remit first
and score it on the harness. Then say in the adequacy prompt that a finding
contradicting a criterion the pull request body renders as satisfied is a
`blocker` (`docs/superpowers/plans/2026-09-07-trusting-the-queue.md:266-285`).

**How a prompt reaches a lens.** `LENSES` maps each lens to its prompt file
(`saffron/phases/review.py:41-46`). `lens_prompt` reads that file from
`prompts_dir` and renders it with `context.build_system_prompt`
(`saffron/phases/review.py:191-214`). The witnesses below render through
`lens_prompt`, so a test that agrees with the file but not with the lens
fails.

**The correctness remit today.** It says the lens owns what the changed
code computes (`saffron/agents/prompts/review-correctness.md:30`). Five
bullets follow, the last being order and state (`:32-42`). The Not-yours
list runs from `:44` to `:60`, and its last bullet hands comments,
docstrings and restated helpers to the conventions lens. The edge sentence
at `:62-64` gives the lens what the code computes and takes from it holding
an interface or a stored format stable. Nothing in the remit names what a
raise, a non-zero exit or an interrupted write leaves on disk.

**The adequacy `blocker` today.** It is reserved for one case, a test that
reads as coverage of the acceptance criterion but is not
(`saffron/agents/prompts/review-adequacy.md:97-100`). Item 79 records the
adequacy concern on PR #154 that contradicted a criterion the same body
ticked. §5.5 holds that a lens filing everything as a `concern` is a
prompting defect.

**What "renders as satisfied" means.** The pull request body ticks a
criterion's box from the `criteria` gate's result. When that gate passed
or failed, a criterion whose witness it names as a failure stays unticked,
and every other box ticks (`saffron/report/pr_body.py:214-231`). Each lens sees the gate
results as `- <gate>: <status> (<tool>)` lines
(`saffron/phases/review.py:170-187`), and sees each claim as a `- [ ]`
line under `## Acceptance criteria` in its task
(`saffron/agents/context.py:220-231`, `saffron/cell/session.py:2930-2931`).

## Problem

The correctness lens has no remit over what a failure leaves behind. The
adequacy lens files a finding that contradicts a ticked criterion at
whatever level it likes.

1. **The correctness remit.** The sentence introducing the remit in
   `review-correctness.md` ends with the text under **The remit's
   opening** in the notes. A sixth bullet, last in the remit, holds the
   text under **The failure-path bullet**. The edge sentence is replaced by
   the text under **The correctness edge**. The Not-yours list is
   unchanged.
2. **The adequacy `blocker`.** In `review-adequacy.md`, the `blocker`
   bullet of the severity section becomes the text under **The adequacy
   blocker**. The `concern` and `note` bullets are unchanged.

## Out of scope

- **A fourth lens.** Track C reaches for one after two prompt iterations
  that raise neither graded defect.
- **Scoring on the harness.** The corpus pass costs money and reads
  `harness/**` and `docs/evidence/fixtures/**`, which `policy.yaml` lists
  under `elevate_on`. The operator runs it by hand after this lands.
  Item 79 closes on that pass, not on this merge.
- **The independent review beside the `SA-0062` fixture.** The operator
  lands it by hand in this spec's pull request, as a copy of item 78's
  Problem.
- **The other lenses' Not-yours lists.** The contract, adequacy and
  conventions prompts keep their bullet naming the correctness lens's
  territory as it stands. The contract lens filed `truncating-write`
  through a written contract in the 2026-09-07 pass, and this spec does
  not take that route from it.
- **`DESIGN.md` §5.5's list for lens #1.** It is protected, and its
  examples stay as they are here.

## Notes for the agent

**This change edits existing files, so each criterion declares a mutant.**
Each mutant points one lens's `LENSES` entry at another prompt file. The
witness then renders the other file through `lens_prompt` and must fail.
The `revert` gate checks the other half, the prompt text itself reverted.
Criterion 3 is `preserves` and names a test that passes now.

**Write the prompt text exactly as below.** Each block is the text the
witness restates as a constant and compares, joined on whitespace. Wrap the
Markdown at 79 columns like its neighbours. The `prose` gate measured each
block at zero new hits on a prototype. Keep the sentence boundaries, and
add no em dash, semicolon or sentence over 25 words.

### The remit's opening

```text
other lenses redundant. Yours is what the changed code *computes*, and what it
leaves behind when it fails:
```

No witness reads this line. It keeps the sentence introducing the remit
true of the bullet below.

### The failure-path bullet

```text
- **What a failure leaves behind**: the state on disk or in a worktree after
  a raise, a non-zero exit or an interrupted write. A truncated file, a
  half-applied restore, an undo over uncommitted work, and cleanup that runs
  only on success are each yours. Follow every path that can stop before it
  finishes, and name what it leaves for the next reader.
```

### The correctness edge

```text
The test at the edge: if the fix changes what the code computes, or what a
failure leaves behind, it is yours. If the fix holds an interface or a stored
format stable, it is not.
```

### The adequacy blocker

```text
- `blocker` — this change should not merge as it stands. Reserve this for two
  cases. The first is a test that reads as coverage of the acceptance
  criterion but is not. The gap alone then stands between "the suite is
  green" and "the criterion is met". The second is any finding of yours that
  contradicts an acceptance criterion the pull request body renders as
  satisfied. The body ticks each criterion's box from the `criteria` gate's
  result, which the gate results below show. File such a finding as a
  `blocker`, never as a `concern`.
```

The first sentence is unchanged from base, em dash included.

### The witnesses

Both are new tests in `tests/test_review.py`. Each renders a prompt with
`review.lens_prompt`, passing `CONTEXT_MD`, `PROMPTS`, `DIFF` and the
`spec_body` and `gates` values the neighbouring tests use
(`tests/test_review.py:20-30`, `:348-357`). Reuse `_bullets_between` and
`_not_yours_bullets_and_edge` (`:572-580`, `:624-647`).

- **Criterion 1.** Render the correctness prompt. Take the remit bullets
  between `## Your remit, and its edges` and `Not yours.`. Assert there are
  six, and the last equals the failure-path bullet joined on whitespace.
  Assert the first five open, in order, with the bold headings they carry
  at base: Time, Boundaries, Missing data, Units and scale, and Order and
  state. Assert the edge sentence equals the correctness edge. Assert no Not-yours
  bullet contains `leaves behind`. Render the contract, adequacy and
  conventions prompts. For each, the text before its first `Not yours.`
  does not contain `What a failure leaves behind`.
- **Criterion 2.** Render the adequacy prompt. Take the section from the
  line opening `## Severity` to the next line opening `## `. Take the
  `blocker` bullet's text, up to the `concern` bullet, joined on whitespace.
  Assert it equals the adequacy blocker without its leading dash. Render the
  correctness, contract and conventions prompts, and assert none contains
  `renders as satisfied` once joined on whitespace.

**Existing tests that read these prompts stay green unchanged.**
`test_the_lenses_declare_disjoint_remits` (`tests/test_review.py:496`),
`test_the_four_lenses_declare_disjoint_remits` (`:583`) and
`test_exactly_one_prompt_claims_the_test_adequacy_remit` (`:900`) each
passed against a prototype of this change. The last one fails if the
correctness remit uses the word "notice", which the bullet above does not.

**Commit as each witness passes.**

**Size.** A prototype of both prompt edits and both witnesses measured 618
changed tokens under `size_gate`. `estimated_lines` is that over four.
