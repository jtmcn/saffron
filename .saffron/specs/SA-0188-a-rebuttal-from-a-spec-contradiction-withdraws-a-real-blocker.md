---
id: SA-0188
title: A rebuttal that quotes one spec line against another wins, so the lens withdraws a real blocker
type: feature
priority: 1
depends_on: [SA-0190]
estimated_lines: 376
touches:
  - saffron/phases/rebut.py
  - saffron/report/pr_body.py
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/agents/prompts/turns/verdict.md
  - tests/test_rebut.py
  - tests/test_report.py
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
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/ledger.py
  - saffron/task.py
  - saffron/intake.py
  - saffron/end_review.py
  - saffron/phases/review.py
  - saffron/phases/package.py
  - saffron/agents/context.py
  - saffron/report/index.py
  - tests/test_session.py
  - tests/test_context.py
  - tests/test_package.py
budget_usd: 25
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      A blocker the implementer argued from one spec line, whose lens answers
      `contradicted` with a quote for each side, ends `READY_FOR_REVIEW` with
      that verdict standing as `contradicted`. Each quote is found in the spec
      text the session was shown once every run of whitespace in both is
      collapsed to one space, and the two quotes differ. The verdict keeps both
      quotes as the lens gave them. `rebut_state`'s line counts it apart from
      the confirmed blockers, and never as withdrawn. The line carries the
      unkept-fix suffix beside that count when a fix was claimed and no commit
      was made.
    witness: tests/test_rebut.py::test_a_blocker_argued_from_one_spec_line_against_another_is_contradicted_and_counted_apart
  - claim: >-
      A `contradicted` verdict fails the host's check in each of four ways. Its
      rebuttal quote is not in the spec text the session was shown, even where
      the rebuttal's own argument holds it. Its finding quote matches a spec
      line only when case is ignored. A quote is whitespace alone. The two
      quotes are the same text once whitespace is collapsed. Each is read as
      `confirmed`, never `withdrawn`. `rebuttal.json` records the failure
      against the lens that gave it, with the finding number, the reason and
      both quotes. The rebuttal quote is checked first.
    witness: tests/test_rebut.py::test_a_contradicted_verdict_whose_quotes_fail_the_check_is_read_as_confirmed_and_recorded
  - claim: >-
      A `contradicted` verdict missing a quote fails the host's check like a
      quote not found, so the task still reaches `READY_FOR_REVIEW`. That holds
      for an absent `rebuttal_quote`, an absent `finding_quote`, a null
      `finding_quote` and an empty `rebuttal_quote`. Each is read as
      `confirmed`, and `rebuttal.json` records the failure, with the reason
      naming the missing side. The lens records no error. A verdict value
      outside `confirmed`, `withdrawn` and `contradicted` is still not the
      schema, and the task halts at `REBUTTING`.
    witness: tests/test_rebut.py::test_a_contradicted_verdict_missing_a_quote_is_read_as_confirmed_and_recorded
  - claim: >-
      The pull request's disagreements table marks a `contradicted` blocker's
      critic cell as the spec contradicting itself, and shows both quotes
      through the same escaping as every other cell. A `confirmed` blocker in
      the same table keeps its `confirmed:` cell.
    witness: tests/test_report.py::test_a_contradicted_row_says_the_spec_contradicts_itself_and_shows_both_quotes
  - claim: >-
      `sustained_blockers` counts an argued blocker verdicted `contradicted`, and
      `unkept_fixes` counts a `contradicted` blocker whose only answer was a fix
      that never committed, as each counts a `confirmed` one. A withdrawn
      blocker counts in neither.
    witness: tests/test_rebut.py::test_a_contradicted_blocker_counts_as_sustained_or_unkept_like_a_confirmed_one
  - claim: >-
      The verdict session's system prompt offers `contradicted` beside
      `confirmed` and `withdrawn`, and names the two quote fields it requires.
      The verdict turn prompt names all three answers.
    witness: tests/test_rebut.py::test_the_verdict_prompts_offer_contradicted_and_ask_for_both_quotes
  - claim: >-
      A lens that leaves a blocker unverdicted still has not withdrawn it.
    witness: tests/test_rebut.py::test_a_lens_that_leaves_a_blocker_unverdicted_has_not_withdrawn_it
    preserves: true
---

## Context

Backlog item **b-ab4b33**, found in the spec loop's run 20 on #562
(`SA-0186`). It cites `DESIGN.md` §5.6. Every line number below was read at
`a4299786`.

The correctness lens raised a blocker at `saffron/task.py:236`. REBUT
quoted one spec line against it, and the lens withdrew. The finding rested
on another line of the same spec, and the blocker was right. The operator
settled which line held (`.saffron/rejections.md:1235-1238`, and
`docs/evidence/2026-09-28-spec-loop-skill-feedback-run-20.md:47-49`).

**What a verdict can say today.** `Verdict.verdict` is
`Literal["confirmed", "withdrawn"]` (`saffron/phases/rebut.py:58`). The
system prompt offers the lens those two words
(`saffron/agents/prompts/rebut-verdict.md:17-22`, `:58`). The turn prompt
opens with "Confirm or withdraw"
(`saffron/agents/prompts/turns/verdict.md:1`). So a lens that sees the spec
disagree with itself has one honest answer left, and it is `withdrawn`.

**What the session is shown.** `verdict_prompt` passes `spec_body` as the
`{spec}` value (`saffron/phases/rebut.py:275`). `build_system_prompt`
substitutes it verbatim (`saffron/agents/context.py:216`), under "The task"
(`saffron/agents/prompts/rebut-verdict.md:76-78`). In production that value
is `spec.body` joined with `context.criteria_section(spec.acceptance)`
(`saffron/cell/session.py:2861`). `run_rebut` holds the same string as its
own `spec_body` argument (`saffron/phases/rebut.py:489`).

**How a verdict set is judged.** `run_verdict` validates the structured
output against `_Verdicts` (`saffron/phases/rebut.py:333`). A set that is not
the schema is an error for that lens (`:334-337`). A set that misses a blocker
is an error too, never a withdrawal (`:338-347`). `run_rebut` appends one
`LensVerdicts` per lens (`:603-628`) and calls `rebut_state` (`:630-632`).
An errored lens halts the task at `REBUTTING` (`:380-381`). Otherwise
`rebut_state` counts the `confirmed` verdicts (`:382-384`). With any, its line
names that count and the argued count (`:390-397`). With none, the line says
every blocker was withdrawn (`:398`). Both reach `READY_FOR_REVIEW`.

**Who reads the verdict.**

- `session.py` writes `v.verdict` onto each finding's ledger row
  (`saffron/cell/session.py:2908-2918`). The column is free text
  (`saffron/ledger.py:184`), and no fold step checks its value
  (`saffron/ledger.py:821-831`).
- `_confirmed_with` counts blockers whose verdict is `confirmed`
  (`saffron/phases/rebut.py:429-435`). `sustained_blockers` (`:438-457`) and
  `unkept_fixes` (`:460-480`) both go through it, and the queue page ranks on
  them.
- The pull request's disagreements table prints `verdict.verdict` and
  `verdict.reason` in the critic cell (`saffron/report/pr_body.py:332`),
  through `_cell` (`:142-153`). PACKAGE scans the whole body for credentials
  before it pushes (`saffron/phases/package.py:886`).
- `RebutResult.as_dict` writes each lens's verdicts to `rebuttal.json`
  (`saffron/phases/rebut.py:138-147`).
- `end_review.py` prints the ledger's verdict text as it stands
  (`saffron/end_review.py:72-74`).

## Problem

A rebuttal can rest on one spec line while its finding rests on another
line of the same spec. The lens then withdraws a real blocker, and nothing
tells the operator the spec disagreed with itself.

Give the verdict session a third answer, and have the host check it.

1. **The answer.** `Verdict.verdict` takes `contradicted` beside `confirmed`
   and `withdrawn`. `Verdict` gains two fields, `rebuttal_quote` and
   `finding_quote`, both optional strings defaulting to `None`. No validator
   ties them to the verdict value, so every verdict validates with or without
   them. The host's check below decides a missing quote. A `verdict` value
   outside the three still fails validation, as it does today.
2. **The check.** `run_rebut` checks every `contradicted` verdict of every
   lens against its own `spec_body`, before `rebut_state` reads them. Collapse
   every run of whitespace to one space and strip both ends, as
   `" ".join(text.split())` does, in each quote and in `spec_body`. Compare
   case and every other character exactly. The check fails on the first of
   these, in this order.
   - The collapsed rebuttal quote is empty or is not in the collapsed spec
     text. A quote that is absent or `None` counts as empty. The reason is `the rebuttal's quote is not in the spec text`.
   - The finding quote fails that same test. The reason is
     `the finding's quote is not in the spec text`.
   - The two collapsed quotes are equal. The reason is
     `the two quotes are the same spec text`.
3. **A failed check.** Replace the verdict with a `confirmed` one carrying
   the same `finding` and `reason`, and both quote fields `None`.
   `LensVerdicts` gains `quote_failures`, a list defaulting to empty. Append
   one entry per failed verdict: a dict with keys `finding`, `reason`,
   `rebuttal_quote` and `finding_quote`, the quotes as the lens gave them.
   An absent quote is recorded as `None`.
   `as_dict` writes it under the lens's entry as `quote_failures`. A passed
   check leaves the verdict as the lens gave it, quotes included.
4. **The state and its line.** A `contradicted` blocker reaches
   `READY_FOR_REVIEW` with the confirmed ones, and no new state is added.
   With at least one `contradicted` verdict, the line reads as follows, where
   C, K and A are the confirmed, contradicted and argued counts.

   ```
   C blocker(s) confirmed after the rebuttal, K on spec lines that contradict each other, A argued — recorded disagreement, yours to adjudicate
   ```

   The unkept-fix suffix follows it, as today. With none, every line
   `rebut_state` returns is the one it returns at base.
5. **The counts.** `_confirmed_with` counts a `contradicted` verdict as it
   counts a `confirmed` one. So `sustained_blockers` and `unkept_fixes` both
   count it, and the queue ranks the task at level 3.
6. **The table.** For a `contradicted` verdict, the critic cell is this text,
   passed whole through `_cell`. Q1 and Q2 are the rebuttal and finding
   quotes as recorded, and R is the reason.

   ```
   spec contradicts itself: the rebuttal quotes "Q1", the finding quotes "Q2": R
   ```

   Every other verdict keeps its `verdict: reason` cell.
7. **The prompts.** In `rebut-verdict.md`, replace the instruction's first
   line and add a third bullet. Change the `verdict` field's bullet, and add
   one bullet per quote field after `reason`. Change "Each element has exactly
   these fields:" to "Each element has these fields:". Rewrite
   `turns/verdict.md`. The exact text is in the notes.

**A departure from the item.** b-ab4b33 asked for `SCOPE_REVIEW`. The
operator chose `READY_FOR_REVIEW` on 2026-09-28. A contradicted blocker is a
recorded disagreement the operator adjudicates in the pull request, like a
confirmed one. So the item's test reads `READY_FOR_REVIEW`, the marked row
and the line.

## Out of scope

- **`DESIGN.md`, `CONTEXT.md` and ADR 4.** §4.1, §5.6 and §6 name two
  verdict values. So do `CONTEXT.md`'s **Verdict** entry and
  `docs/adr/0004-the-critic-is-host-invoked-lenses-with-no-vote.md:72`. The
  operator edits them by hand in this spec's pull request.
- **Two comments outside `touches`.** `saffron/ledger.py:171` and
  `saffron/report/index.py:42` still describe a verdict as confirm or
  withdraw. `saffron/report/index.py` is in queued `SA-0152`'s `touches`.
- **The ledger.** `findings.verdict` stores `contradicted` as text, with no
  schema change. The quotes live in `rebuttal.json` and the pull request, not
  in a ledger column.
- **An event for a failed check.** `rebuttal.json` is its record.
- **A minimum quote length.** A failed check reads as `confirmed`, and a
  passed one counts with the confirmed blockers. So a short quote can
  mislabel a row, and it can never withdraw a blocker.
- **`session.py`, `review.py` and `intake.py`.** The change reaches none of
  them. `SA-0190` is the parent because the operator ordered the chain.

## Notes for the agent

**New or edit.** Every criterion but the last builds new code. This spec
cannot know its `find` text, so each declares a witness and no mutant.
`witness` reports `skip` for them. The last is `preserves`, and names a
test that passes now.

**Commit as each witness passes.** Run the witness, then commit, before
the next one.

**Shared helpers, not copies.** Specs in this chain landed at 1.4 to 1.7
times their estimate, mostly from tests that copied helpers and rows.

- In `tests/test_rebut.py`, give `_run` (`tests/test_rebut.py:125-169`) a
  `spec_body` keyword defaulting to `"fix the gap"`, and pass it through at
  `:155`. Add one `_contradicted(finding, rebuttal_quote, finding_quote,
  reason)` dict helper beside `_verdict` (`:73`). Build turns with
  `_rebuttals`, `_argued`, `_fixed` and `_verdicts` (`:57-71`), blockers
  with `_blocker` (`:26`), and results with `_result` (`:576`).
- Declare one module constant for the spec text the rebut witnesses share.
  Put each witness's cases in a table of rows and loop over it.
- In `tests/test_report.py`, build the body with `_rebut_body`
  (`tests/test_report.py:1079`) over `_two_blocker_reviews` (`:1066`).

**The spec text the rebut witnesses share** is two lines, the second
wrapped with a newline and two spaces of indent.

```
Only a `MERGED` or `REJECTED` newest task unstacks a child.

The resolver stacks on no row when the newest task
  is outside the waiting states.
```

**Criterion 1's witness** runs twice over that spec text. Its rebuttal
quote is the second line on one line, with a single space where the text
wraps. Its finding quote is the first line with a leading space, a tab in
place of the space after `MERGED`, and a trailing newline.

1. One correctness blocker, argued, with HEAD unmoved. The lens answers
   `contradicted`. The state is `READY_FOR_REVIEW`. The lens's verdicts equal
   one `Verdict` carrying both quotes as given. Its `quote_failures` is
   empty in `as_dict`. The line is exactly this.

   ```
   0 blocker(s) confirmed after the rebuttal, 1 on spec lines that contradict each other, 1 argued — recorded disagreement, yours to adjudicate
   ```

2. Blocker 1 is the same. Blocker 2 is an adequacy blocker answered `fixed`,
   and its lens answers `confirmed`. HEAD is unmoved. The line is exactly
   this.

   ```
   1 blocker(s) confirmed after the rebuttal, 1 on spec lines that contradict each other, 1 argued — recorded disagreement, yours to adjudicate (a fix was claimed for some of them and no commit was made)
   ```

**Criterion 2's witness** has two argued blockers. Blocker 1 is a
correctness blocker its lens withdraws. Blocker 2 is a contract blocker, and
its lens answers `contradicted`. The contract lens runs after the
correctness one, so a check that reads only the first lens fails. Blocker
2's argument text holds the case (a) rebuttal quote word for word. Five
rows, one per case.

- (a) The rebuttal quote is not in the spec text. The reason is the
  rebuttal's.
- (b) The finding quote is the first line with `merged` and `rejected` in
  lower case. The reason is the finding's.
- (c) Both quotes are the second line, one with a newline where the other
  has a space. The reason names the same spec text.
- (d) The rebuttal quote is a space, a newline and a tab. The reason is the
  rebuttal's.
- (e) Neither quote is in the spec text. The reason is the rebuttal's.

Each row asserts four things. The state is `READY_FOR_REVIEW`. The contract
lens's verdicts equal one `confirmed` `Verdict` with the lens's reason and
no quotes. The correctness lens's verdicts are unchanged. In `as_dict`, the
correctness entry's `quote_failures` is empty. The contract entry's equals
one dict with that row's finding, reason and quotes. The line is exactly
this.

```
1 blocker(s) confirmed after the rebuttal, 2 argued — recorded disagreement, yours to adjudicate
```

**Criterion 3's witness** runs five rows through `_run` over the shared
spec text, each with one argued correctness blocker. The first four give a
`contradicted` verdict whose other quote is valid.

- (a) No `rebuttal_quote` key. The reason is the rebuttal's.
- (b) No `finding_quote` key. The reason is the finding's.
- (c) `finding_quote` is `None`. The reason is the finding's.
- (d) `rebuttal_quote` is the empty string. The reason is the rebuttal's.

Each of these asserts five things. The state is `READY_FOR_REVIEW`. The
lens's error is `None`. Its verdicts equal one `confirmed` `Verdict` with
the lens's reason and no quotes. Its `quote_failures` in `as_dict` equals
one dict with the finding, the reason and both quotes, an absent one as
`None`. The line is exactly this.

```
1 blocker(s) confirmed after the rebuttal, 1 argued — recorded disagreement, yours to adjudicate
```

The fifth row gives the verdict value `overruled`. It asserts the state
`REBUTTING`, the lens's verdicts empty, its error set, and `why` exactly
`['correctness'] produced no verdict — the rebuttal is unjudged`.

**Criterion 4's witness** gives blocker 1 an argued rebuttal and a
`contradicted` verdict with reason `the two lines disagree`. Its rebuttal
quote is `The resolver stacks on no row outside the waiting states.` Its
finding quote is ``Only a `MERGED` | `REJECTED` newest task unstacks a
child.`` That pipe proves the quote passes through `_cell`. Blocker 2 is
argued and `confirmed`, with reason `still wrong`. The witness asserts that
the rows starting `| 1 ` and `| 2 ` equal a list of two whole lines, built
by hand in the test. Both rows name the `correctness` lens, because
`_finding` defaults it (`tests/test_report.py:702-713`).

**Criterion 5's witness** builds three results with `_result`. An argued
blocker verdicted `contradicted`, HEAD moved, gives `sustained_blockers` 1
and `unkept_fixes` 0. A fixed blocker verdicted `contradicted`, HEAD
unmoved, gives 0 and 1. An argued blocker verdicted `withdrawn` gives 0 and
0. Build each `Rebuttal` from its row with `model_validate`. The `types`
gate rejects a plain `str` passed as `action`.

**Criterion 6's witness** renders `verdict_prompt` with `claude_md=None`.
It reads the text between `## Your instruction` and `## Your findings`.
The first paragraph, whitespace collapsed, equals this line.

```
For each finding, answer `confirmed`, `withdrawn` or `contradicted`.
```

The bullets there, each whitespace collapsed without its leading `- `,
equal this list in order.

```
`confirmed` — the finding still stands. The fix does not address it, or the argument is wrong, or nothing was done about it. Say concretely why.
`withdrawn` — you were wrong, or the change under "The diff, after the rebuttal" resolves it.
`contradicted`: two lines of the spec under "The task" disagree. The rebuttal's argument rests on one of them, and your finding rests on the other. Quote both, each copied exactly. The host looks for both quotes in that spec. It reads your answer as `confirmed` when it cannot find one, or when the two are the same text.
```

It reads the bullets between `## What to emit` and the next heading the
same way. They equal this list in order.

```
`finding` (integer) — the number of the finding, exactly as listed above.
`verdict` (string): `confirmed`, `withdrawn` or `contradicted`.
`reason` (string) — one or two sentences. If you are confirming, why the fix or the argument does not settle it; if you are withdrawing, what changed your mind.
`rebuttal_quote` (string): required with `contradicted`. The spec text the rebuttal's argument rests on.
`finding_quote` (string): required with `contradicted`. The spec text your finding rests on.
```

`rebut.VERDICT_TURN_PROMPT`, whitespace collapsed, equals this line.

```
For each of your findings, answer `confirmed`, `withdrawn` or `contradicted` now, given the rebuttal. Read whatever you need to. You hold no tool that can change anything. Answer now in the required structured format.
```

Wrap the new prompt lines as the file wraps its own. Leave the first two
bullets and the `reason` bullet as they stand. Their text is the base's.

**Keep what other tests read.** `tests/test_context.py:454-481` reads
`rebut-verdict.md` for three phrases. `tests/test_context.py:530-541` reads
both prompts for an output block. Both files are forbidden, so keep those
phrases, and add no output block.

**Wrong versions these witnesses must kill.** Each one below failed a
prototype's witnesses on 2026-09-28. Each witness also failed with the
prototype's source reverted to the base.

- A check that compares text without collapsing whitespace.
- A check that ignores case.
- A check against the whole system prompt, or the rebuttal, not `spec_body`.
- An empty quote accepted because the empty string is in every text.
- Two equal quotes accepted.
- The finding quote checked before the rebuttal quote.
- A failed check read as `withdrawn`, or left `contradicted`.
- A failed check that records nothing, or records it on the wrong lens.
- A check that reads only the first lens's verdicts.
- A `contradicted` verdict with a missing or null quote that errors the lens.
- A missing quote recorded under the other side's reason.
- A verdict value outside the three accepted.
- A line that folds the contradicted count into the confirmed one.
- A contradicted-only set whose line says every blocker was withdrawn.
- A line that drops the unkept-fix suffix.
- A table cell built outside `_cell`.
- `_confirmed_with` left counting `confirmed` alone.

**The `prose` gate** reads the prompts and every new comment. The pinned
prompt text above passes it. Write no new comment or docstring with an em
dash, a semicolon, a contraction, the perfect tense or a sentence over 25
words.

**Size.** `size` is advisory here: no touched path is in `elevate_on`, and
the spec is `standard`. A prototype with all six new witnesses, counted by
`size_gate`, came to 1505 tokens against the `feature` ceiling of 3000.
`estimated_lines` is those measured 1505 tokens over four, with no overrun
added. `driver.py check` applies its hand-estimate overrun on top and prices
it at 81%. That counts the overrun twice (item b-b0a187). About a third of
the prototype is `saffron/` and the prompts, and the rest is tests.
