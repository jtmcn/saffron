---
id: SA-0405
title: A lens withdraws the host's blocker on a parent's surviving wrong version in REBUT
type: feature
priority: 3
estimated_lines: 214
estimate_measured: true
touches:
  - saffron/phases/rebut.py
  - tests/test_rebut.py
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
  - saffron/cell/**
  - saffron/agents/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - saffron/task.py
  - saffron/intake.py
  - saffron/parent_versions.py
  - saffron/phases/review.py
  - saffron/phases/package.py
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_parent_versions.py
budget_usd: 30
max_attempts: 3
max_turns: 170
acceptance:
  - claim: >-
      A `withdrawn` verdict on the host's survivor of a parent's wrong
      version never stands. A parent survivor is a blocker whose claim
      starts with `review.HOST_FILED`, then the witness, then the first
      ` stayed green with `, then a name other than `the spec`, then `'s
      wrong version `.
      Its witness need not be any criterion's in `acceptance`. The host
      reads the verdict as `confirmed`, with the parent sentence under
      **The reason** ahead of the lens's own reason. It records the refusal
      in `withdrawal_refusals` under its lens, with the same two keys as
      today. That holds for a first answer that is `fixed` with HEAD moved,
      `fixed` with HEAD unmoved, argued with HEAD moved or unmoved, or
      missing with HEAD moved or unmoved. It holds for the claim's three tails, the witness-only one,
      the whole `tests` gate killing, and the whole `tests` gate green. It
      holds for a parent named `SA-1` and one named `SP-2`, and for a
      version whose `repr` is single-quoted and one double-quoted. A
      parent survivor whose witness is a `preserves` criterion's is refused
      the same way, with the parent sentence. Seven withdrawals in the same
      call stand unchanged. They are the spec's own wrong version, a
      criterion's own edit whose claim quotes `SA-1's wrong version`, the
      spec's own version whose text holds `SA-1's wrong version here`, the
      spec's own version whose text holds ` stayed green with SA-1's wrong
      version `, a
      lens claim quoting a parent claim after a word, a parent claim with no
      `review.HOST_FILED`, and another lens's blocker. In the same call a
      `preserves` survivor answered `fixed` with HEAD moved stays withdrawn.
      An argued one is refused with the `preserves` sentence. A parent
      survivor the lens confirmed records nothing.
    witness: tests/test_rebut.py::test_a_withdrawn_parent_survivor_is_kept_confirmed_whatever_its_answer
    wrong_versions:
      - The parent guard keys on the witnesses in `acceptance`, as the `preserves` guard does, so a parent's own witness is never guarded.
      - The name is read as everything up to the first `'s wrong version ` anywhere in the claim, so a criterion's own edit whose quoted claim holds that phrase is guarded.
      - Any `'s wrong version ` after the first ` stayed green with ` counts when the word before it is not `spec`, so the spec's own version quoting a parent is guarded.
      - The name only has to differ from `the spec`, with no check of `'s wrong version ` after it, so a criterion's own edit is guarded.
      - The claim need not start with `review.HOST_FILED`, so a lens claim without it is guarded.
      - The claim holds `review.HOST_FILED` anywhere rather than at its start.
      - A parent survivor keeps the exception for a first answer of `fixed` with HEAD moved.
      - The `preserves` guard is checked first, so a parent survivor on a `preserves` witness takes its sentence and its exception.
      - A parent survivor's reason opens with the `preserves` sentence.
      - A `preserves` survivor's reason opens with the parent sentence.
      - The exception for `fixed` with HEAD moved is dropped for a `preserves` survivor too.
      - A parent survivor is guarded only when a `preserves` criterion shares its witness.
      - A guarded blocker the lens confirmed is recorded as refused.
      - The refusal is not written to `withdrawal_refusals`.
      - A parent survivor is refused only when its first answer is not `fixed`.
      - A parent survivor nobody answered keeps its withdrawal.
      - The parse requires the claim to end with the witness-only tail, so a claim the whole `tests` gate extended is not guarded.
      - A parent survivor is refused only when HEAD moved.
      - A refusal's dict gains a key naming its kind.
      - Only the first lens's verdicts are checked.
      - The name must be `SA-` then digits, so a parent named `SP-2` is not guarded.
      - The text after the name must be `wrong version '`, so a version whose `repr` is double-quoted is not guarded.
      - The name is read after the last ` stayed green with ` in the claim, so the spec's own version holding that phrase is guarded.
      - A parent survivor nobody answered keeps its withdrawal when HEAD did not move.
  - claim: >-
      A `withdrawn` verdict on the host's survivor of a `preserves`
      criterion, other than a parent survivor (criterion 1), still stands
      only when the first answer is `fixed` and HEAD moved. Its reason
      still opens with the `preserves` sentence.
    witness: tests/test_rebut.py::test_a_withdrawn_host_filed_blocker_on_a_preserves_criterion_stands_only_after_a_committed_fix
    preserves: true
  - claim: >-
      A task whose `preserves` survivor is argued out of the diff and
      withdrawn still records one refusal dict with the keys `finding` and
      `withdrawn_reason` in `rebuttal.json`.
    witness: tests/test_session.py::test_a_preserves_criterion_probe_argued_out_of_the_diff_is_kept_confirmed
    preserves: true
---

## Context

Backlog item **b-d9a027**, its REBUT half. It cites `DESIGN.md` §5.4 and
§5.5, and this half changes §5.6's verdict check. `SA-0403` and `SA-0404`
take its `saffron regate` half, and this spec is independent of both.
Every line number below was read at `d72d0733`.

**How a parent survivor is filed.** `SA-0402` asks each parent's killed
wrong versions in REVIEW. `parent_versions._parent_pairs` builds each pair
with `"parent": parent_id` and the recorded `"version"`
(`saffron/parent_versions.py:110-118`). A survivor becomes a finding
through `review.survivor_finding(..., version=entry.get("version"),
parent=entry.get("parent"))` (`saffron/cell/session.py:2238-2244`). The
criterion passed there is the parent's, so its witness is the parent's
witness. `survivor_finding` writes three claim forms
(`saffron/phases/review.py:913-926`).

- With no version: `HOST_FILED`, the witness, then ` stayed green with the
  criterion's own edit applied to `.
- With a version and no parent: the same up to ` stayed green with `, then
  `the spec's wrong version `.
- With both: the same up to ` stayed green with `, then the parent's id and
  `'s wrong version `.

The version follows as its `repr`. `survivor_claim_with_suite_verdict`
rewrites only the tail after the quoted claim
(`saffron/phases/review.py:943-964`). A lens cannot open a claim with
`HOST_FILED`, since `_strip_host_filed` removes every leading copy
(`saffron/phases/review.py:218-223`).

**How a withdrawal is judged today.** `run_rebut` calls
`_guarded_blockers(numbered, acceptance)` once, then
`_check_withdrawal_refusals` on every lens (`saffron/phases/rebut.py:993-999`).
`_guarded_blockers` returns a set of blocker numbers. A number is in it only
when its claim starts with `HOST_FILED`, a `preserves` criterion's witness
from `acceptance`, then ` stayed green with `
(`saffron/phases/rebut.py:545-564`). A parent's witness is not in the
child's `acceptance`. So a lens can withdraw a parent survivor, as it can
any survivor of a criterion without `preserves`.
`_check_withdrawal_refusals` lets a withdrawal stand when the first answer
was `fixed` and HEAD moved. It turns every other one into `confirmed`, with
`_WITHDRAWAL_REFUSED_REASON` ahead of the lens's reason, and appends
`{"finding": n, "withdrawn_reason": reason}`
(`saffron/phases/rebut.py:539-601`).

**Why a parent survivor has no exception.** After the rebuttal,
`_rebut_gates` asks every survived probe again over the post-rebuttal patch
(`saffron/cell/session.py:3759-3764`). A kill there counts only against the
names `added_tests` reads, the tests the diff adds
(`saffron/probe.py:406-408`). The parent's witness exists at base. The
re-ask feeds `rebut-probes.json`, `revert-exempt.json` and an
infrastructure check (`saffron/cell/session.py:3814-3834`). `run_rebut`
gets only a stop state from `rerun_gates` (`saffron/phases/rebut.py:937`).
So the refusal check sees `moved` and the first answers, and nothing says
the parent's witness now kills the version. The operator decided the
refusal holds whatever the first answer was.

**Who reads the record.** `rebuttal.json`'s `withdrawal_refusals` is read
back by `saffron/task.py:1245`, and
`tests/test_session.py:14081` asserts its dict shape by equality. Neither
changes here.

## Problem

A lens can withdraw the host's blocker on a parent's surviving wrong
version. Have the host refuse that withdrawal always.

1. **The parent survivor.** Its claim starts with `review.HOST_FILED`.
   After that comes the first ` stayed green with `.
   The text after it, up to the first `'s `, is the name. The name must not
   be `the spec`, and the text after that `'s ` must start with
   `wrong version `. Nothing in `acceptance` is read for it.
2. **The guarded blockers.** `_guarded_blockers` returns each guarded
   blocker number with the host's sentence for it. A parent survivor takes
   the parent sentence, whatever `acceptance` holds. Any other blocker the
   `preserves` rule guards today takes `_WITHDRAWAL_REFUSED_REASON`.
3. **The check.** A `withdrawn` verdict on a parent survivor always becomes
   `confirmed`. Its reason is the parent sentence, one space, then the
   lens's own reason, and its quote fields are `None`. A `preserves`
   blocker keeps today's rule and today's sentence. Every other verdict is
   left as the lens gave it.
4. **The record.** Each refusal appends the same two-key dict as today.
   `rebut_state` and `run_rebut`'s signature are unchanged.
5. **The words that go false.** Update the docstrings of
   `_guarded_blockers` and `_check_withdrawal_refusals` to name both rules.

## Out of scope

- **`saffron regate`.** `SA-0403` and `SA-0404` ask a review commit the
  wrong versions it never met.
- **`depends_on` in REBUT.** The guard reads the claim text alone, so
  `run_rebut` gains no parameter and `saffron/cell/session.py` is untouched.
- **A forged parent claim.** `_strip_host_filed` already keeps a lens out of
  `HOST_FILED`. A blocker wrongly guarded is kept, which is the safe
  direction.
- **A parent pair recorded with no version.** `survivor_finding` then writes
  the criterion's own edit and drops the parent. `_parent_pairs` copies the
  record's `version` as it stands. No witness drives that pair, and the
  guard leaves it alone.
- **A `contradicted` or `confirmed` verdict on a parent survivor.** Both
  stand as the checks leave them now.
- **The verdict prompt and the pull request body.** No lens is told of the
  rule. The disagreements table prints the new reason as text.
- **A `retired_first`.** This refuses a lens's verdict, not a spec, and the
  queue holds no other spec at `d72d0733`.
- **Hand edits, made in this spec's own pull request.** `DESIGN.md` §5.6,
  the paragraph opening **The order, settled**, gains one sentence after the
  one ending `(b-cd5fd2).`

  > The host reads a `withdrawn` answer on its survivor of a parent's wrong
  > version as `confirmed` too, whatever the first answer was (`SA-0405`).

  `CONTEXT.md`'s **Verdict** entry gains one sentence after the one ending
  `unless the first answer was `fixed` and HEAD moved.`

  > It reads a `withdrawn` answer on its survivor of a parent's wrong
  > version as `confirmed` always (`SA-0405`).

## Notes for the agent

**New or edit.** Criterion 1 builds new code, so it declares a witness and
no mutant, and `witness` reports `skip` for it. Criteria 2 and 3 are
`preserves`, and both witnesses pass at `d72d0733`. Each wrong version
under criterion 1 is one its witness must fail. REVIEW turns each into an
edit and asks the witness. Do not ask them yourself.

**The reason.** The parent sentence is the line below, then one space.
The lens's own reason follows that space.

```
The host kept this blocker: a parent's wrong version survived its witness, and a lens cannot withdraw that. The lens withdrew it:
```

**Keep every existing test as it is.** Rename no test. The `census` gate
reads a renamed test as a removed one. Add the new test after
`test_a_lens_blocker_quoting_the_host_text_mid_claim_stays_withdrawn`,
and reuse that section's `_WITHDRAWAL_ARGUMENT` and
`_WITHDRAWAL_HOST_SENTENCE`.

**Criterion 1's witness** calls `_run` twice. Build these inside the test
body, with `Criterion` and `Mutant` from `saffron.intake`.

- `preserved`: claim `the total is unchanged`, witness `t.py::test_a`,
  `preserves` true.
- `plain`: claim `the total stays sorted`, witness `t.py::test_c`.
- The parent's criterion: claim `the sum holds`, witness `t.py::test_p`.
- One edit, `if amount < 0:` to `if False:` in `src/gap.py`, and the
  content `if amount < 0:\n`.

Build every host-filed blocker with `review.survivor_finding` over that
edit and content, never as a hand-written string. A parent survivor passes
`version="a sum that skips zero"` and `parent="SA-1"`. Each `argued`
answer's argument is `_WITHDRAWAL_ARGUMENT`. Each verdict's reason is `r`
then its finding number, as `_verdict(n, reason=str(n))` builds it. Both
calls pass `acceptance=[preserved, plain]`.

The first call has HEAD moved and these fourteen blockers in order.

1. A parent survivor on `t.py::test_p`. Answered `fixed`, withdrawn.
2. Blocker 1 with its claim passed through
   `review.survivor_claim_with_suite_verdict` and a `killed`
   `probe.ProbeResult` failing `t.py::test_b`. Argued, withdrawn.
3. The same with a `survived` result that names no failure. No answer,
   withdrawn.
4. A parent survivor of a criterion on `t.py::test_a`, the `preserves`
   witness. Answered `fixed`, withdrawn.
5. A parent survivor on `t.py::test_p`. Argued, `confirmed`.
6. `plain`'s survivor of the spec's own version `a total left unsorted`.
   Argued, withdrawn.
7. The own-edit survivor of a criterion on `t.py::test_c` whose claim is
   `SA-1's wrong version 'v' stays killed`. Argued, withdrawn.
8. `plain`'s survivor of the spec's own version
   `SA-1's wrong version here`. Argued, withdrawn.
9. An `adequacy` `_blocker` whose claim is `see ` then blocker 1's claim.
   Argued, withdrawn.
10. An `adequacy` `_blocker` whose claim is blocker 1's with its leading
    `review.HOST_FILED` removed. Argued, withdrawn.
11. `preserved`'s own-edit survivor. Answered `fixed`, withdrawn.
12. `preserved`'s own-edit survivor. Argued, withdrawn.
13. A `correctness` blocker from `_blocker`. Argued, withdrawn.
14. `plain`'s survivor of the spec's own version
    `x stayed green with SA-1's wrong version y`. Argued, withdrawn.

The correctness lens verdicts first, so a check of the first lens alone
fails. Assert these.

- The state is `READY_FOR_REVIEW`.
- `why` equals this line.

  ```
  6 blocker(s) confirmed after the rebuttal, 10 argued — recorded disagreement, yours to adjudicate
  ```

- The correctness lens's verdicts equal one `Verdict`: finding 13,
  `withdrawn`, reason `r13`.
- The adequacy lens's verdicts equal thirteen `Verdict`s built by hand.
  Findings 1 to 4 are `confirmed`, each reason the parent sentence then
  `r1` to `r4`. Finding 5 is `confirmed` with `r5`. Findings 6 to 11 are
  `withdrawn` with `r6` to `r11`. Finding 12 is `confirmed`, its reason
  `_WITHDRAWAL_HOST_SENTENCE` then ` r12`. Finding 14 is `withdrawn` with
  `r14`.
- In `as_dict`, keyed by lens, the correctness entry's
  `withdrawal_refusals` is empty. The adequacy entry's equals
  `{"finding": n, "withdrawn_reason": "rn"}` for n in 1, 2, 3, 4 and 12.

The second call has HEAD unmoved and three parent survivors on
`t.py::test_p`. The first is blocker 1 of the first call, answered `fixed`.
The second passes `version="a sum off by one"` and `parent="SP-2"`, and
is argued. The third passes `version="a sum that's off by one"` and
`parent="SA-1"`, and has no answer. The lens withdraws all three. Assert
that each verdict is `confirmed` with the parent sentence then `r1` to
`r3`. Assert that `withdrawal_refusals` holds the three dicts.

Write the parent sentence and each expected `Verdict` as a literal in the
test. Never build one from `rebut.py`'s own constant.

**Measured.** On 2026-11-16 a prototype at `d72d0733` passed the new
witness and every test in `tests/test_rebut.py`, `tests/test_session.py`,
`tests/test_events.py` and `tests/test_agent_runner.py`. With `rebut.py` reverted
to `d72d0733` the new witness failed on its `why` assertion. Each wrong
version under criterion 1 was applied to the prototype, and the new witness
failed on every one.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.

**Size.** `size_gate` counted the prototype at 228 changed tokens outside
`tests/` and 626 under it, against the `feature` ceiling of 3000.
`estimated_lines` is both over four. `rebut.py` is not in `elevate_on`.
