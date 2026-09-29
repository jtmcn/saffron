---
id: SA-0193
title: A lens withdraws the host's probe blocker on a `preserves` criterion because its line is outside the diff
type: feature
priority: 1
estimated_lines: 218
touches:
  - saffron/phases/rebut.py
  - saffron/cell/session.py
  - tests/test_rebut.py
  - tests/test_session.py
  - tests/test_agent_runner.py
  - tests/test_events.py
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
  - saffron/agents/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - saffron/ledger.py
  - saffron/task.py
  - saffron/intake.py
  - saffron/end_review.py
  - saffron/phases/review.py
  - saffron/phases/package.py
  - tests/test_findings.py
  - tests/test_review.py
  - tests/test_report.py
budget_usd: 26
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      A `withdrawn` verdict on a host-filed blocker whose criterion is
      `preserves` stands only when that blocker's first answer is `fixed` and
      HEAD moved. Otherwise the host reads it as `confirmed`, with a reason
      that opens with the host's sentence and ends with the lens's own. That
      holds for the blocker filed from the criterion's own edit and from one
      of its wrong versions. It holds for a first answer that argued, with
      HEAD moved or not, that claimed a fix HEAD never carried, or that is
      missing. `rebuttal.json` records each refusal under its lens, with the
      finding number and the lens's own reason. A withdrawal argued the same
      way stands unchanged on three other blockers. They are a host-filed
      blocker of a criterion without `preserves`, a lens's own blocker naming
      the `preserves` witness, and another lens's blocker. A guarded blocker
      the lens confirmed records nothing.
    witness: tests/test_rebut.py::test_a_withdrawn_host_filed_blocker_on_a_preserves_criterion_stands_only_after_a_committed_fix
    wrong_versions:
      - A blocker is guarded when its claim starts with the host prefix and the witness, with no check of the text after the witness.
      - Every host-filed blocker is guarded, whatever its criterion declares.
      - Every blocker whose claim names a `preserves` witness is guarded, the lens's own included.
      - A withdrawal stands whenever HEAD moved, whatever the blocker's answer.
      - A withdrawal stands whenever the blocker's answer is `fixed`, whether or not HEAD moved.
      - The last answer to a blocker decides, not the first.
      - A withdrawal of a blocker nobody answered stands.
      - The refused verdict keeps the lens's reason alone.
      - The refused verdict stays `withdrawn`.
      - The refusal is not written to `rebuttal.json`.
      - A guarded blocker the lens confirmed is recorded as refused.
      - Only the first lens's verdicts are checked.
      - A withdrawal is refused only when the first answer argued or HEAD did not move, so an unanswered blocker's withdrawal stands once HEAD moved.
      - A refusal is recorded only when HEAD did not move.
  - claim: >-
      A task whose `preserves` criterion's probe survives its witness and
      anchors, whose implementer argues the blocker is outside the diff and
      commits nothing, and whose lens then withdraws it, ends
      `READY_FOR_REVIEW`. The blocker is `confirmed` in `rebuttal.json` and on
      its ledger row, and the refusal is recorded under its lens.
    witness: tests/test_session.py::test_a_preserves_criterion_probe_argued_out_of_the_diff_is_kept_confirmed
    wrong_versions:
      - The session passes REBUT no criteria.
      - The session passes REBUT only the criteria without `preserves`.
  - claim: >-
      A lens's own blocker, argued and withdrawn, still lands on its ledger
      row as `withdrawn`.
    witness: tests/test_session.py::test_a_verdict_lands_on_the_finding_the_review_recorded
    preserves: true
---

## Context

Backlog item **b-cd5fd2**, found in the spec loop's run 21 on #581
(`SA-0192`). It cites `DESIGN.md` §5.5 and §5.6. Every line number below was
read at `60510037`.

`SA-0192`'s criterion 3 was `preserves`. The host's criterion probe added an
adequacy question to `review-correctness.md`, and the witness stayed green.
The host filed that as a blocker. REBUT argued that the line sat outside the
implementer's diff and committed nothing, and the adequacy lens withdrew.
Both seats found the hole real, and review commit `d2ea4afe` fixed the
witness (`docs/evidence/2026-09-29-spec-loop-skill-feedback-run-21.md:43-44`,
`:107-108`). A `preserves` criterion is a property of the whole file. Where
the diff sits does not answer a probe that breaks it.

**How the blocker reaches REBUT.** `_apply_criterion_probes` applies each
criterion probe and each wrong version in a gate-only cell
(`saffron/cell/session.py:1561`). A survivor becomes a finding through
`review.survivor_finding` (`saffron/cell/session.py:1701`), is anchored, and
is appended to the `adequacy` review (`:1712`). `survivor_finding` files it
under the `adequacy` lens (`saffron/phases/review.py:699`). Its claim opens
with `HOST_FILED` (`saffron/phases/review.py:55`), then the witness, then
` stayed green with ` (`:687` for the criterion's own edit, `:693` for a
wrong version). A lens cannot file a claim with that prefix.
`_from_report` strips every leading `HOST_FILED` from a lens's claim
(`saffron/phases/review.py:216-231`). `anchored_blockers` passes an anchored
blocker on to REBUT (`saffron/phases/review.py:724`).

**How a verdict is judged today.** `run_rebut`
(`saffron/phases/rebut.py:555`) numbers the blockers from 1 into
`numbered` (`:599`). It runs one verdict session per
lens, in `review.LENSES` order (`:675-676`). Then it calls
`_check_contradictions` on every lens (`:704`) and `rebut_state` (`:706`). `_check_contradictions`
(`:383-412`) is the only host check that changes a verdict. It reads `contradicted`
alone, so a `withdrawn` verdict stands as the lens gave it. `first_answers`
keys the rebuttal by blocker number, first answer winning (`:477`).

**What the verdict session knows.** It is shown `spec.body` joined with
`context.criteria_section(spec.acceptance)` (`saffron/cell/session.py:2913`).
That section renders each claim as `- [ ] {c.claim}`
(`saffron/agents/context.py:133`), and nothing there marks a criterion as
preserved. So the lens cannot tell a `preserves` survivor from any other,
and prompt text alone could not tell it. No parameter of `run_rebut`
carries a criterion (`saffron/phases/rebut.py:555-590`).

**Who reads the verdict.** `session.py` writes `rebuttal.json` from
`RebutResult.as_dict` (`saffron/cell/session.py:2942`). It then writes each
verdict onto its finding's ledger row through `ledger.record_rebuttal`
(`:2966-2969`). The pull request's
disagreements table prints `verdict: reason` in the critic cell
(`saffron/report/pr_body.py:337`). `_confirmed_with` counts a `confirmed`
verdict (`saffron/phases/rebut.py:493`), so `sustained_blockers` (`:516`)
counts an argued blocker the host kept.

## Problem

A lens can withdraw the host's own blocker on a `preserves` criterion
because the line sits outside the diff. Have the host refuse that
withdrawal.

1. **The criteria reach REBUT.** `run_rebut` gains a required keyword
   argument `acceptance`, a sequence of `saffron.intake.Criterion`. Give it
   no default. `session.py`'s one call passes `spec.acceptance`. The three
   test call sites pass what the notes say.
2. **The guarded blockers.** Take each criterion in `acceptance` that
   declares `preserves`. A blocker is guarded by it if its claim starts
   with `review.HOST_FILED`, that criterion's witness and
   ` stayed green with `, in that order. That text follows from `survivor_finding` for both
   of its forms. A witness that is a prefix of another is then no match.
3. **The check.** After `_check_contradictions` has run on a lens, check that
   lens's verdicts. A `withdrawn` verdict on a guarded blocker stands only
   when the blocker's first answer, by `first_answers`, is `fixed` and HEAD
   moved. Every other `withdrawn` verdict on a guarded blocker becomes a
   `confirmed` one. It keeps the finding number. Its reason is the host's
   sentence under **The reason** in the notes, then the lens's own reason,
   with nothing between them. Its quote fields are `None`. Every other
   verdict is left as the lens gave it.
4. **The record.** `LensVerdicts` gains a list field `withdrawal_refusals`,
   empty by default. Each refused verdict appends one dict with two keys,
   `finding` and `withdrawn_reason`. The second is the lens's own reason.
   `as_dict` writes the list under the lens's entry, beside
   `quote_failures`.
5. **The state.** `rebut_state` is unchanged. It reads the verdicts after
   the check, so a kept blocker counts as confirmed in its line.

## Out of scope

- **The verdict prompt.** The session cannot see which criterion is
  `preserves`, so a sentence there has nothing to act on. Marking
  `preserves` in `criteria_section` changes what every critic reads. It is
  a separate change, with a measured pass (ADR 8).
- **A non-`preserves` criterion's survivor.** The operator scoped the
  refusal to `preserves`. Its withdrawal stands as today.
- **A `contradicted` or `confirmed` verdict on a guarded blocker.** Both
  stand as the check leaves them now.
- **`DESIGN.md` and `CONTEXT.md`.** §5.6 and the **Verdict** entry list
  the cases the host reads as `confirmed`, and this adds one. The operator
  edited both, and §4.1, by hand at e1bb7578.
- **`saffron/agents/findings.py`.** Backlog item b-38d45f changes
  `_is_anchored` there. This spec reads a blocker only after it anchored.
- **The ledger and the pull request body.** The ledger stores the verdict
  as text, and the table prints the new reason through `_cell` already.

## Notes for the agent

**New or edit.** Criteria 1 and 2 build new code, so each declares a
witness and no mutant. `witness` reports `skip` for them. Criterion 3 is
`preserves`, and names a test that passes now. Each wrong version listed
under a criterion is one its witness must fail. REVIEW turns each into an
edit and runs the witness. Do not run them yourself.

**The reason.** The host's sentence is the line below, then one space.
The lens's own reason follows that space.

```
The host kept this blocker: its criterion is `preserves`, so it holds over the whole file, and no committed fix answered it. The lens withdrew it:
```

**Commit as each witness passes.** Run the witness, then commit, before
the next one.

**Keep every existing test as it is.** Rename no test, and change no
parametrise row. The `census` gate reads a renamed test as a removed one.
Add the two new tests beside the existing ones.

**The three other callers.** `tests/test_rebut.py`'s `_run` helper
(`tests/test_rebut.py:152-197`) gains an `acceptance` keyword defaulting to
`()`, passed to `run_rebut` as a list. `tests/test_agent_runner.py:783` and
`tests/test_events.py:2420` each call `run_rebut` directly. Pass
`acceptance=[]` there.

**Criterion 1's witness** runs `_run` twice, over two criteria built inside
the test body. The first is `preserves`, with witness `t.py::test_a`. The
second is not, with witness `t.py::test_a_b`, which extends the first. A
host-filed blocker is `_blocker(lens="adequacy", ...)` whose claim is
`review.HOST_FILED`, the witness, then ` stayed green with ` and either
form's tail. Every `argued` answer's argument below is the same text,
`the line sits outside my diff, so it is not mine to answer`. Each verdict's
reason is `r` followed by its finding number, as `_verdict(n, reason=str(n))`
builds it.

Run 1, HEAD unmoved, eight blockers in this order.

1. Host-filed on `t.py::test_a`, the criterion's own edit. Argued, withdrawn.
2. Host-filed on `t.py::test_a`, a wrong version. Argued, withdrawn.
3. Host-filed on `t.py::test_a`. Answered `fixed`, withdrawn.
4. Host-filed on `t.py::test_a`. No answer, withdrawn.
5. Host-filed on `t.py::test_a_b`. Argued, withdrawn.
6. An `adequacy` blocker with the claim
   `t.py::test_a stayed green with any edit`. Argued, withdrawn.
7. Host-filed on `t.py::test_a`. Argued, `confirmed`.
8. A `correctness` blocker from `_blocker`. Argued, withdrawn.

The correctness lens verdicts first, so a check that reads only the first
lens fails. The witness asserts these.

- The state is `READY_FOR_REVIEW`.
- `why` equals this line.

  ```
  5 blocker(s) confirmed after the rebuttal, 6 argued — recorded disagreement, yours to adjudicate (a fix was claimed for some of them and no commit was made)
  ```

- The correctness lens's verdicts equal one `Verdict`: finding 8,
  `withdrawn`, reason `r8`.
- The adequacy lens's verdicts equal a list of seven `Verdict`s built by
  hand. Findings 1 to 4 are `confirmed`, each reason the host's sentence
  then `r1` to `r4`. Findings 5 and 6 are `withdrawn` with `r5` and `r6`.
  Finding 7 is `confirmed` with `r7`.
- In `as_dict`, keyed by lens, the correctness entry's
  `withdrawal_refusals` is empty. The adequacy entry's equals four dicts,
  `{"finding": n, "withdrawn_reason": "rn"}` for n from 1 to 4.

Run 2, HEAD moved, run 1's first four blockers. Blocker 1 is answered
`fixed`. Blocker 2 is argued. Blocker 3 is argued first and answered
`fixed` second. Blocker 4 has no answer. The lens withdraws all four. The
witness asserts these.

- The adequacy verdicts equal four `Verdict`s. Finding 1 is `withdrawn`
  with `r1`. Findings 2 to 4 are `confirmed`, each reason the host's
  sentence then `r2` to `r4`.
- In `as_dict`, the adequacy entry's `withdrawal_refusals` equals three
  dicts, `{"finding": n, "withdrawn_reason": "rn"}` for n from 2 to 4.
- `why` equals this line.

  ```
  3 blocker(s) confirmed after the rebuttal, 2 argued — recorded disagreement, yours to adjudicate
  ```

Write each expected string and each expected `Verdict` as a literal in the
test. Never build one from `rebut.py`'s own constant.

**Criterion 2's witness** follows
`test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker`
(`tests/test_session.py:7376`). Build one criterion inside the test body:
claim `one prompt claims it`, witness `t.py::a`, `preserves` true. Drive it
with `_stub_the_runtime` over `_ANCHORING_DIFF`, whose `gate_cell_suite` is
one passing `tests` result collecting `t.py::a`. Call `_rebuttable` with
`rebut_commits=0`. `_stub_probe_gates` answers one passing `tests` result,
so the probe survives. Stub `worktree.read_at_head` to return
`def y():\n    return 1\nassert x == 1\n` for `src/x.py` outside the
critic container. The probe edit is `assert x == 1` to `x2` in `src/x.py`.
Its line anchors by the token `x`. After `_probe_turns` come three turns.
The first is the rebuttal's attempt. The second extracts one `argued`
answer to finding 1, argument `outside my diff`. The third is one
`withdrawn` verdict on finding 1, reason `fair`. Assert these.

- The outcome's state is `READY_FOR_REVIEW`.
- `rebuttal.json` holds one lens entry. Its `verdicts` equal one dict:
  finding 1, verdict `confirmed`, reason the host's sentence then `fair`,
  and both quote fields `None`.
- Its `withdrawal_refusals` equal `[{"finding": 1, "withdrawn_reason": "fair"}]`.
- The finding's ledger row's `verdict` and `rebuttal` are `confirmed` and
  `argued: outside my diff`.

**Measured.** On 2026-09-29 a prototype of this change passed both
witnesses. With its source reverted to `60510037`, both failed. Criterion
1's failed with a `TypeError` from `_run`, and criterion 2's on its
`verdicts` assertion. Each wrong version above was applied to the
prototype, and at least one of the two witnesses failed on every one. The
two about HEAD having moved passed a run 2 without blocker 4 and its
refusal asserts. They fail the run 2 above.

**A shared witness.** The guard keys on witness text. Nothing in
`saffron/intake.py` makes a witness unique to one criterion, and
`SA-0121` shared one across three. So a survivor of a criterion without
`preserves` is guarded too if another criterion is `preserves` over the
same witness. That errs toward keeping a blocker, which is the safe
direction. No criterion drives it.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks here. The
prototype, counted by `size_gate`, came to 871 tokens against the
`feature` ceiling of 3000. `estimated_lines` is that over four, with no
overrun added. About a quarter of it is `saffron/`, and the rest is tests.
