---
id: SA-0377
title: A finish's follow-up is refused for citations its writer never checked, and its red escalation names no gate
type: bug
priority: 2
estimated_lines: 32
estimate_measured: true
depends_on: [SA-0373]
touches:
  - saffron/follow_up.py
  - saffron/cli.py
  - saffron/finish.py
  - tests/test_follow_up.py
  - tests/test_cli.py
  - tests/test_finish.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/batch.py
  - saffron/spec_citations.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/qualify.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - tests/test_batch.py
  - tests/test_spec_citations.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      `follow_up.write_follow_ups` takes an optional `cite`, called once on
      each draft that parses and validates, with the draft's own text,
      before `judge`. It returns the draft's unresolved citation lines. A
      non-empty return spends the group's one send-back, with the reason
      `N citation(s) do not resolve: ` and the lines joined by `; `. The
      draft is still judged, and a red judgement's own reason follows that
      one, joined by `; `. A second refusal pools the group with the second
      reason. A `cite` that raises charges the session, as a raising
      `judge` does. It pools its group as
      `cite raised <type>: <message>`, judges nothing, and pools every later
      group with that reason unwritten. The witness drives six groups. The
      first is a red cite whose green resend is minted. The second is a red
      cite with a red judgement whose resend is cited red again. The third is
      a parse failure whose resend is cited red. The fourth is a draft
      `_validate` refuses, which is never cited. The fifth is a raising cite,
      and the sixth comes after it.
    witness: tests/test_follow_up.py::test_a_draft_whose_citations_do_not_resolve_is_sent_back_once_then_minted_or_pooled
    wrong_versions:
      - "`cite` is called only once `judge` is green, so the combined reason lacks the citation half."
      - "`judge` is skipped on a draft whose cite is red, so the writer learns of a prose failure only on its second draft."
      - A red cite pools the group at once, with no send-back.
      - A red cite gets a send-back of its own, apart from the parse and judge send-back, so a third draft is written.
      - A raising cite is read as a red one and sent back.
      - A raising cite pools only its own group, so the later group is still written.
      - A raising cite pools its group without charging the session, so the writer's spend reads low.
      - The reason names the count and not the lines.
      - "`cite` reads the writer's prompt rather than the draft's text."
      - The lines are joined by `, ` rather than `; `.
      - "`cite` is called before `_validate`, so a refused draft is cited."
  - claim: >-
      `cli._stack_follow_ups` passes `write_follow_ups` a `cite`. It fetches
      the top layer's branch, `_branch` of its spec id, fresh with
      `package_phase.fetch_parent_branch`. It returns each
      `citation_defects` line at that head, in order. That is the head
      `_stack_cite` reads when the batch reviews the first follow-up atop the
      top layer. The witness seeds a top layer whose remote branch carries
      one commit past its packaged head, which the mirror lacks, and a stack
      review with no graded fields. Its text holds four citations, two of
      which resolve at no head. The follow-up's `cite` runs before
      `_stack_cite`, while the mirror's own ref still names the packaged
      commit. Its lines must equal `_stack_cite`'s own defects
      for a follow-up atop that layer, in order. They must differ from the
      lines at the packaged head and at the pinned base.
    witness: tests/test_cli.py::test_a_stack_batchs_follow_up_cite_reads_the_head_its_batchs_own_cite_reads
    wrong_versions:
      - "`cite` reads the top layer's graded head with no fetch, so a review commit pushed after PACKAGE goes unread."
      - "`cite` reads the pinned `base_sha`."
      - "`cite` reads the mirror's own ref for that branch without fetching it."
      - "`cite` returns the count of defects rather than each defect's line."
      - "`_stack_follow_ups` builds `cite` and never passes it to `write_follow_ups`."
      - The lines are returned in reverse order.
  - claim: >-
      On a red finishing suite, `finish.publish_finish`'s escalation line
      ends with ` in ` and each gate its new failures name. Each gate appears
      once, in the order `verify` first returned it, joined by `, `.
      Failures from `tests`, `prose`, `tests` and `census` read
      `escalate: red suite, 4 new failures in tests, prose, census`. The
      count, its plural and the lines after it stay as they are at base.
      The witness drives that four-failure suite and a one-failure `prose`
      suite.
    witness: tests/test_finish.py::test_a_red_finishs_escalation_line_names_each_failing_gate_once
    wrong_versions:
      - The gates are sorted, so the line reads `census, prose, tests`.
      - A gate is named once per failure, so `tests` appears twice.
      - Only the first failure's gate is named.
      - The gates are named in parentheses after the count rather than after ` in `.
      - The gates are listed last seen first.
---

## Context

Backlog item **b-4a9207**, filed 2026-11-02. It cites `DESIGN.md` §5.7.
Every line number below was read at `a80264c8`.

**The incident.** Finish 64's end review drafted `SA-0332`. The finishing
suite failed that draft's prose first. The batch then refused the revised
draft with `2 citation(s) do not resolve`, and the finishing layer ended `escalate: red suite, 1 new failure`. Finish 58
lost `SA-0324` to two citations the same way. Finish 80 lost `SA-0370` to
eleven. The item's Record lists each later finish where it recurred.

**How a draft is judged now.** `write_follow_ups` parses each draft and
calls `_validate` on it (`saffron/follow_up.py:438-447`). It then calls
`judge(path, session.text)`, and a red result goes through `send_back`
with the reason `the finishing suite failed it: ` (`saffron/follow_up.py:452-466`).
`send_back` resends the prompt once per group. A second refusal pools the
group (`saffron/follow_up.py:301-328`). A raising `judge` pools its group
and sets `halt_reason`, which pools every later group (`saffron/follow_up.py:452-458`, `saffron/follow_up.py:334-337`).
A green draft is minted, and its text is recorded with the origin
`follow_up` (`saffron/follow_up.py:468-483`). The production `judge` is
`finish.judge_draft` atop the top layer's graded head (`saffron/cli.py:1923-1937`).
`judge_draft` returns one rendered line per new failure (`saffron/finish.py:258-294`).
No step reads a draft's citations.

**How the batch reads a follow-up's citations.** The batch drives a
follow-up in its second pass, at generation 1 (`saffron/batch.py:1016-1035`). Its
`pred` is the batch's `predecessor` (`saffron/batch.py:667`), the last
candidate whose outcome made a layer (`saffron/batch.py:955-956`). Before
the spec review, the batch reads the follow-up's recorded text and calls
`cite` (`saffron/batch.py:716-736`). It refuses with
`{len(left)} citation(s) do not resolve` when any defect is left
(`saffron/batch.py:738-746`). The production `cite` is `_stack_cite`
(`saffron/cli.py:1462-1495`). A given text holds no citation there, so
`rewrite_moved_citations` leaves every defect (`saffron/spec_citations.py:490-526`).
So the batch's verdict is `citation_defects` at the head `_stack_head`
returns (`saffron/spec_citations.py:421-424`, `saffron/cli.py:860-872`).
With a predecessor, `_seed_branch` names `_branch` of its spec id, and the
predecessor outranks any stack base (`saffron/cli.py:845-857`).
`_stack_head` fetches that branch with `package_phase.fetch_parent_branch`.

**Why that is the top layer.** `review_stack` walks a batch's layers
highest position first (`saffron/end_review.py:106-113`), so
`stack.layers[0]` is the last layer recorded. `saffron finish` seeds its
resume's `top` from the last of `Ledger.stack_layers` (`saffron/cli.py:2823-2830`).
`_stack_follow_ups` reads that layer as `top` through
`qualify.graded_fields` (`saffron/cli.py:1853`). `top.head` is the head the
end review graded, or the packaged head when the review graded none
(`saffron/qualify.py:222-232`). An end review that raised returns no graded
fields at all (`saffron/cli.py:954-995`). The branch can carry a review
commit past that head, and the batch fetches it.

**How a red finish escalates now.** `publish_finish` builds
`escalate: red suite, N new failures` from the count alone, then adds one
cleaned line per failure (`saffron/finish.py:516-521`). Each line holds
`baseline.render`'s `[gate]` prefix (`saffron/gates/baseline.py:25-33`).
A `NewFailure` carries its `gate` (`saffron/gates/baseline.py:20-22`). The
runner parses each gate's JSON against the declared name
(`saffron/gates/runner.py:141`).

## Problem

A finish mints a follow-up its own batch then refuses for citations, and a
red finishing layer's escalation line names no gate. Check each drafted
follow-up's citations where the batch will check them, before the mint.
Name each failing gate on the escalation line.

1. **`saffron/follow_up.py`.** Add the optional `cite` to
   `write_follow_ups`, `None` by default. After `_validate` passes, call it
   on the draft's text, inside its own `try`, then call `judge`. Build the
   send-back reason from the citation part and the judge part, as
   criterion 1 says. A `None` `cite` checks nothing, and every existing
   test keeps its behaviour. Update the module docstring and the function
   docstring to name `cite`.
2. **`saffron/cli.py`.** In `_stack_follow_ups`, beside `judge`, build the
   `cite` criterion 2 names and pass it to `write_follow_ups`. Fetch on
   each call. `_branch` and `citation_defects` are already imported there.
3. **`saffron/finish.py`.** Add the gate list to the escalation line, as
   criterion 3 says.

## Out of scope

- **A one-line finding fixed in the finishing layer.** The item's first
  "Done looks like" sentence stays open on b-4a9207.
- **The batch's own spec-review revision path.** `SA-0376` judges a
  revision there.
- **The writer's own in-session faults.** `spec_review.draft_faults` reads
  no citation, and stays as it is.
- **A later follow-up's head.** Once one follow-up makes a layer, the next
  one's `pred` is that follow-up (`saffron/batch.py:955-956`). Its citations
  are read at that branch, which no draft can know. This spec checks every
  draft at the top layer's branch.
- **The batch's own refusal.** `saffron/batch.py` keeps its check as it is.
- **The writer's view of the cited tree.** The writer's cell, its faults and
  `judge` read `top.head`. That is the head the end review graded, else the
  packaged head. `cite` reads the fetched
  branch tip, which a review commit can move past that head. A draft whose
  citations fail there gets the defect lines alone on its one resend. A
  second failure pools it. That is still cheaper than a mint the batch refuses.

## Notes for the agent

**Every criterion is new code.** None declares a mutant, so `witness` will
report `skip` for each. The wrong versions under each criterion name what
its witness must still catch.

**At base each witness fails in its body.** Criterion 1's call passes a
`cite` that base rejects. Criterion 2's fake never reaches a `cite`.
Criterion 3's line lacks the gates. Import nothing the change adds at
module scope.

**Seeding criterion 1.** The prototype drove all six groups through one
`write_follow_ups` call. It read each draft's id from the prompt's `id:`
line, as `test_a_draft_the_finishing_suite_fails_is_sent_back_once_with_its_failures_and_then_minted`
does. Tag each draft by its claim text, so `cite` and `judge` doubles can
pick it out. Assert the positive half of each absence. A judged draft for
group one comes before the check that group five's draft was never judged.
Cited drafts for groups one to three come before the check that group four's
was never cited. A second draft for group two comes before the check for no
third. List the origin task's writing-phase attempts' session ids, as
`tests/test_follow_up.py:1659-1664` does for a raising `judge`. The list
must include group five's raising draft's session.

**Seeding criterion 2.** A non-bare `remote` repository, with `trunk` at
the base and `saffron/SY-1` holding the packaged commit, then a review
commit. The mirror is a bare clone taken before the review commit. Set
`pinned.url` to the remote's path, so the fetch is real. Seed the layer
with `Ledger.set_task_package` and `record_stack_layer`, as
`test_a_stack_batchs_follow_up_writer_is_seeded_at_the_top_head_the_end_review_graded`
does. Pass `end_review.StackReview` with no `fields`. Fake
`write_follow_ups` to call the `cite` it receives on a text with four
backticked citations. The prototype cited lines 7 to 9, 20 to 25, 40 to
41 and 50 to 52 of one file. That file held 5, 10 and 30 lines at the base,
packaged and review commits. Compare with `cli._stack_cite(pinned=pinned)`
called with the follow-up, the layer as `Candidate`, and the same text.
Call the follow-up's `cite` first. `_stack_cite` fetches the branch and
moves the mirror's ref, so called first it would let the no-fetch wrong
version pass.

**Tests that pin the old shapes.** Two fakes in `tests/test_cli.py` list
`write_follow_ups`'s keywords by name and need `cite=None`. They are
`_fake_write_follow_ups` and `_make_partial_double`'s `_double`, both in
`test_a_stack_batchs_follow_ups_are_qualified_and_written_from_the_pinned_base_at_the_stacks_top`.
In `tests/test_finish.py`, the `red` and `red-one` cases of
`test_each_escalation_leaves_the_stack_unpushed` pin the old line exactly.
So do `test_a_red_finish_names_each_new_failure_it_counts`'s `lines[0]`
and its docstring. Update each to the new line.

**No refusal of a queued spec.** The new check pools a draft before it is
minted, so no `retired_first` entry applies.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.

**Why `depends_on: [SA-0373]`.** Both specs edit `saffron/cli.py`.
`SA-0373` edits `_adopt`, far from `_stack_follow_ups`. It forbids
`saffron/finish.py` without touching it, as `SA-0375` forbids `saffron/cli.py`
and `saffron/finish.py`. Neither of those is an overlap.

**Size.** A prototype measured 128 changed tokens with `size_gate`,
against the `bug` ceiling of 1300, with 1181 more under the test paths. It
held all three edits, the three witnesses and the updated pins and fakes. Every
test in `tests/test_follow_up.py`, `tests/test_finish.py` and
`tests/test_stack_base_follow_up.py` passed on it, with `tests/test_cli.py`'s
follow-up, finish and stack tests.
