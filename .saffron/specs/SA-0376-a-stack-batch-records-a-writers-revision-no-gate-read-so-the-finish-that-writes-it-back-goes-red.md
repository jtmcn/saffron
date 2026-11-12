---
id: SA-0376
title: A stack batch records a spec writer's revision that no gate read, so the finish that writes it back goes red
type: bug
priority: 2
estimated_lines: 73
estimate_measured: true
depends_on: [SA-0373]
touches:
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_batch.py
  - tests/test_cli.py
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
  - saffron/finish.py
  - saffron/follow_up.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/draft.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/qualify.py
  - saffron/agents/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/repos/**
  - tests/test_finish.py
  - tests/test_follow_up.py
  - tests/test_spec_review.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 170
acceptance:
  - claim: >-
      `run_stack_batch` takes a keyword `judge`, a callable of the
      candidate, its predecessor and a text that returns a sequence of
      failure lines. Given one, each revision the spec writer returns
      with no error and no rate limit meets `judge` before any
      `spec_texts` row holds that text. An empty sequence passes the
      text, which is then recorded and reviewed as it is now. The
      witness drives an order spec with no predecessor, an order spec
      with a predecessor, and a follow-up spec. It checks each call's
      predecessor and text, and that the latest recorded text at the
      call is still the one from before the revision.
    witness: tests/test_batch.py::test_a_stack_batch_judges_each_revision_before_it_records_the_text
    wrong_versions:
      - The judge called only for a spec of the order, so the follow-up's revision is recorded unjudged.
      - The judge handed the text the writer was given, not the text it returned.
      - The judge handed no predecessor, so the second spec's call names none.
      - The judge called after the row is recorded, so its call sees the revision as the latest text.
  - claim: >-
      A revision whose judgement returns lines is not recorded. The
      batch emits one line, the spec id padded to ten columns, then
      `sent back  <n> new failure(s)`, where `<n>` counts those lines. It
      calls the writer once more, with the failing text as its spec text
      and a review text that starts with the review's own text and holds
      each failure line. A passing reply is recorded as that revision,
      and the `revised` line counts it once. Each later revision of the
      same spec gets its own send-back. The witness drives a spec whose
      first revision is sent back, and a spec whose first and second
      revisions are each sent back.
    witness: tests/test_batch.py::test_a_revision_the_judge_fails_goes_back_to_the_writer_once_with_its_lines
    wrong_versions:
      - The failing text recorded before the send-back, so the task's rows hold it.
      - The send-back hands the writer the text it was given, not the failing one.
      - The send-back's review text carries no failure line.
      - The send-back never cleared once a revision passes, so the second spec's second failure is refused instead of sent back.
      - Each writer call counted as a revision, so the first spec prints `revised  2`.
      - No `sent back` line emitted.
  - claim: >-
      A revision whose send-back also fails records neither text and
      refuses the spec for this batch. The batch emits one line, the spec
      id padded to ten columns, then `refused  <n> new failure(s) after a
      send-back`, where `<n>` counts the second judgement's lines. The
      `Refused` carries the same reason. The batch reviews the spec no
      more, calls the writer no more, and never hands it to the runner. A
      spec of the order is missed, so each spec whose `depends_on` reaches
      it is refused. A follow-up is refused and misses nothing, so the
      next follow-up still runs. The witness drives an order spec with no
      recorded text and one with an earlier passing revision, each with a
      dependent. It drives a follow-up beside a second follow-up. It also
      drives a send-back that met the account's rate limit, retried after
      the wait with the same text and review text, then refused.
    witness: tests/test_batch.py::test_a_revision_that_fails_after_its_send_back_refuses_its_spec_for_the_batch
    wrong_versions:
      - The second failing text recorded before the refusal, so the task's rows hold it.
      - The text from before the revision kept and run, so the runner is handed the spec.
      - The spec refused but never marked missed, so its dependent runs.
      - The send-back state kept per offer of the spec, so the rate-limited spec is sent back a second time after its wait.
      - The refusal counts the first judgement's lines.
      - A second failure sent back again, with no bound.
      - A second failure that starts a fresh review, so the review double is asked once too often.
      - No refusal line emitted, so only the dependents' lines appear.
  - claim: >-
      A raise from `judge` records no text, leaves the spec's task
      `GATE_ERROR`, and reaches `_drive`, as a raise from the writer
      does. A plain exception misses a spec of the
      order, so a spec that depends on it is refused. A
      `CellRuntimeError` leaves the spec queued, so it is reviewed again
      and its dependent runs. The witness drives one of each.
    witness: tests/test_batch.py::test_a_judge_that_raises_stops_the_revision_as_a_writer_raise_does
    wrong_versions:
      - A raise read as failure lines, so the plain raise's spec is sent back and runs.
      - A raise swallowed and the text recorded as passing.
      - A `CellRuntimeError` missed like any raise, so its dependent is refused.
      - No `GATE_ERROR` set, so the plain raise's task stays `QUEUED`.
  - claim: >-
      `cli._stack_judge(pinned=, repo=, out_dir=, stack_base=)` returns
      `run_stack_batch`'s `judge`. Each call hands `finish.judge_draft`
      the pinned mirror, the commit `_stack_head` resolves for the
      predecessor and the stack base, the path `.saffron/specs/` joined
      to the candidate's file name, and the text. Its `verify` is one
      `cli._finish_verify` builds with no `only`, and `workdir` and the
      gates directory are two paths under `out_dir`. Its lines come back
      as they are. The witness drives the three seeds: a predecessor's
      branch, the stack base's branch with no predecessor, and
      `base_sha` with neither.
    witness: tests/test_cli.py::test_stack_judge_judges_a_revision_atop_its_seed_with_the_whole_finishing_suite
    wrong_versions:
      - A verify narrowed to the form gates with `only`, as `_draft_faults` builds one.
      - The head always `base_sha`, so neither branch is fetched.
      - The stack base never passed to `_stack_head`, so the second seed is `base_sha`.
      - The candidate's bare file name as the path, outside `.saffron/specs/`.
  - claim: >-
      `saffron batch --stack` builds `_stack_judge` once, with the pinned
      base, the resolved `--repo`, `main`'s `out_dir` and the order's
      stack base. It passes it to `run_stack_batch` as `judge`, with or
      without `--defer-end-review`. A readiness that fails builds none and
      passes `judge=None`. `saffron finish` builds one with its pinned
      base, `--repo` and `out_dir`, and passes it as `judge`. The witness
      drives all four.
    witness: tests/test_cli.py::test_a_stack_batch_and_saffron_finish_pass_run_stack_batch_the_revision_judge
    wrong_versions:
      - A batch that builds the judge but passes `judge=None`.
      - A finish that passes no judge.
      - The judge built only without `--defer-end-review`, beside the follow-ups.
      - The judge built with no stack base.
---

## Context

Backlog item **b-703e64**, the revision half its 2026-11-07 Record line
names. It cites `DESIGN.md` §4.2 and §5.4, and the stack batch is ADR 7.
`SA-0327` landed the follow-up half. Every line number below was read at
`a80264c8`.

**The incident.** In the spec loop's run 37, batch 29, the writer revised
`SA-0286` twice. The finish wrote the revision back and re-verification
reported 13 new failures, 12 of them `prose` hits in the revised text.
The finish escalated and pushed nothing. Batches 37 and 38 of run 44 did
the same with `SA-0276` and `SA-0281`. In run 56, finish 73, writer drafts
failed `prose` at re-verification four times before one held.

**What the batch does with a revision now.** `run_stack_batch` calls
`revise` with the candidate, the predecessor, the spec text and the
review text (`saffron/batch.py:894`). It records the attempt
(`saffron/batch.py:902-913`). A rate-limited reply stores the pair in
`pending_revision` and raises `SpecReviewWait`
(`saffron/batch.py:914-917`). The next offer pops that pair and calls the
writer with it, with no review between (`saffron/batch.py:719`,
`saffron/batch.py:868-869`). An error reply is a miss
(`saffron/batch.py:918-926`). Any other reply's text is recorded as a
`revision` row and the batch emits `revised  <n>`
(`saffron/batch.py:927-935`). Nothing judges that text. The loop then
reads the new text and reviews it (`saffron/batch.py:721-722`,
`saffron/batch.py:766`). A spec whose review
routes `run` meets gate 0's open-pull-request refusals on its latest
revision (`saffron/batch.py:842-865`), then reaches `runner`
(`saffron/batch.py:937`). A raise from the writer sets `GATE_ERROR` and
misses the spec unless it is a `CellRuntimeError`
(`saffron/batch.py:895-901`).

**What the follow-up path does.** `write_follow_ups` hands each parsed,
validated draft to `judge` before the mint (`saffron/follow_up.py:453`).
A failing draft goes back to the writer once (`saffron/follow_up.py:459-465`,
`saffron/follow_up.py:312`). Its `judge` is `finish.judge_draft` with a
verify from `_finish_verify`, atop the top layer's head
(`saffron/cli.py:1922-1935`). `judge_draft` commits the text at its path
atop a head and runs `verify(sha, head)` under a throwaway ref
(`saffron/finish.py:258-294`). `_finish_verify` builds the finishing suite
and runs `package_phase.reverify` (`saffron/cli.py:1132-1173`). The
finish's own re-verification uses `_finish_verify` the same way
(`saffron/cli.py:1302-1307`). So the same verify judges a revision as the
one that goes red on it.

**The writer's own check is not enough.** `SA-0353` gave the writer
session a `faults` callable. `_stack_revise` builds it with
`_draft_faults` (`saffron/cli.py:1569-1576`), which narrows the verify to
the policy's `form: true` gates (`saffron/cli.py:1197-1199`). The session
sends a faulty text back once (`saffron/spec_review.py:580`). It then
returns its newest parsed text whatever its faults
(`saffron/spec_review.py:858-860`). The batch cannot tell a clean reply
from a faulty one. The `tests` gate, which reads the live specs, is no
form gate (`.saffron/policy.yaml:6`).

**Where a revision's head is.** `_stack_head` resolves a layer's branch,
else the stack base's, else `base_sha` (`saffron/cli.py:860-872`).
`_stack_revise` seeds the writer's cell there (`saffron/cli.py:1529`).
`_batch` builds `_stack_revise` with the order's stack base
(`saffron/cli.py:2613-2615`) and passes it as `revise`
(`saffron/cli.py:2685`). That block runs with `--defer-end-review` too.
`_finish` builds one with no stack base (`saffron/cli.py:2875`) and passes
it (`saffron/cli.py:2910`).

## Problem

A revision the spec writer returns is recorded and handed to the cell
with no gate. The finish then writes that text into the tree, and
re-verification fails it. Judge each revision before the batch records
it, with the follow-up path's mechanism.

1. In `saffron/batch.py`, add the `judge` keyword to `run_stack_batch`,
   defaulting to `None`. In the revision block, after the error check at
   line 918 and before line 927, call it with the candidate, `pred` and
   the reply's text. On lines, send the text back once by storing the
   failing text and the extended review text in `pending_revision` and
   continuing the loop. The existing budget check, attempt,
   rate-limit and error handling then serve the send-back unchanged. Keep
   a per-batch set of the spec ids already sent back, so a wait between
   the two writer calls does not reset it. Clear an id when its revision
   passes. On a second failure, emit the refusal line and return a
   `Refused` with that reason. Mark a spec of the order missed and drop
   it from `remaining`, as the escalation at lines 825-832 does, and
   leave a follow-up unmissed. A raise from `judge` takes the shape of the writer's raise at lines
   895-901.
2. In `saffron/cli.py`, add `_stack_judge`, built the way `_stack_revise`
   is. Build it beside `stack_revise` in `_batch` and in `_finish`, and
   pass it as `judge` in both `run_stack_batch` calls. A readiness that
   fails leaves it `None`, as `stack_revise` is left.
3. Write the six witnesses the criteria name.

## Out of scope

- **`commit_finish` and the finish's re-verification.** They read the
  latest text as they do now. This spec only changes which texts reach
  the ledger.
- **The follow-up path.** `write_follow_ups` already judges its drafts.
- **The end review**, and the writer session's own `faults`.
- **A send-back the budget cannot cover.** The existing budget check
  refuses the spec there, as it refuses a first revision it cannot cover.
- **Running an earlier text.** A spec whose revision fails twice is
  refused, never run on the text from before that revision. Its review
  asked for a revision, so running the older text would run a spec with
  a finding the review routed to the writer.
- **The refused task's state.** The refusal sets none, as the budget
  refusal at lines 881-892 sets none.
- **The citation rewrite's text.** It is recorded before the review
  (`saffron/batch.py:754-760`) and is not a revision.
- **`saffron draft`.** Its writer path is `saffron/draft.py`, outside this
  change.

## Notes for the agent

**Every criterion is new code.** `judge` and `_stack_judge` do not exist
yet, so no mutant pins their spelling. `witness` will report `skip` for
each, and the wrong versions under each criterion say what its witness
must still catch.

**Error is not fail.** A raise from `judge` is the verify breaking, such
as a drifted or errored suite. It is never read as failure lines. That is
why criterion 4 copies the writer's raise and not the send-back.

**Doubles for `tests/test_batch.py`.** Subclass `StackDoubles`
(`tests/test_batch.py:5548`). Script each spec's writer replies and
judgements by spec id, and keep the latest recorded text each judge and
runner call sees. `_written`, `_Rejected`, `_spec_text`, `_pr`,
`AdvancingClock` and `_task_state` already exist. Pass `clock` and
`clock.sleep`, so a rate-limited send-back waits on the clock. Give each
reviewed spec a route list in `rows`, so a review asked once too often
raises. Read a task's rows with a query over `spec_texts` ordered by `n`,
and compare whole lists, so a negative check has its positive case.

**Seed each state so the wrong version reaches its branch.**

- Criterion 1's follow-up comes from `follow_ups`, with its own
  `follow_up` row, as `StackDoubles.follow_ups` records one.
- Criterion 2's second spec needs routes `revise`, `revise`, `run` and
  four replies, failing and passing in turn.
- Criterion 3's earlier revision passes its judgement, then the next
  review routes `revise` again. Give each refused order spec a dependent,
  and put a spec with no revision last, so the order still drains. Give
  the refused follow-up a second follow-up after it, routed `run`.
- Criterion 4's plain-raise spec needs a second reply and a passing
  judgement scripted, so a version reading the raise as lines runs it.

**`tests/test_cli.py`.** For criterion 5, replace
`package.fetch_parent_branch`, `cli._finish_verify` and
`finish.judge_draft` with spies. For criterion 6, follow
`test_a_stack_batch_passes_run_stack_batch_its_spec_revision`
(`tests/test_cli.py:10863`) and build a candidate with a `StackBase`, as
`tests/test_cli.py:10953-10960` does. For `saffron finish`, use
`_deferred_finish_home` and `_finish_readiness_passes`.

**Cost.** A judgement runs no agent and spends no model money. It runs
the finishing suite twice in gate-only cells, a baseline and the judged
commit (`saffron/phases/package.py:525-556`). Finish 80's re-verification
took 10 minutes 33 seconds. That figure is read from file timestamps,
not timed live: `gates` was created at 08:43:04 and `verify.json` was
written at 08:53:37. So each judged revision adds about 10.5 minutes of
wall clock before the review that follows it, and a send-back doubles
that.

**At base each witness fails in its body.** `run_stack_batch` takes no
`judge` and `cli` has no `_stack_judge`. Import nothing the change adds
at module scope.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. A docstring stays within ten lines, and
`run_stack_batch`'s own is at ten already, so put the new keyword's
account in a comment beside it.

**Size.** A prototype measured 291 changed tokens with `size_gate`,
against the `bug` ceiling of 1300, with 1745 more under the test paths.
It held both source changes and the six witnesses. Every test in
`tests/test_batch.py`, `tests/test_cli.py`, `tests/test_finish.py` and
`tests/test_follow_up.py` passed on it.
