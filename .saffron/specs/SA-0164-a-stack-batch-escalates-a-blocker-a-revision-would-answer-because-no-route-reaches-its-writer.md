---
id: SA-0164
title: A stack batch escalates a blocker a revision would answer, because no route hands the spec to its writer
type: feature
priority: 1
depends_on: [SA-0160]
touches:
  - saffron/spec_review.py
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_spec_review.py
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
  - images/**
  - harness/**
  - records/**
  - saffron/task.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_session.py
  - tests/test_task.py
  - tests/test_review.py
  - tests/test_policy.py
budget_usd: 25
max_attempts: 3
max_turns: 190
acceptance:
  - claim: >-
      `spec_review_route` routes a read `revise` when it holds a `blocker`
      and every blocker's `fixes` is `build` or `witness`. It also routes
      `revise` a read with no blocker whose `concern` has a `claim` holding
      `unmeasured`, matched without regard to case. A blocker whose `fixes` is `scope`, null or
      absent routes the read `escalate`, whatever else the read holds and
      in either order. `wait` and `error` keep their precedence. Every other
      read routes `run`. The witness drives each `fixes` value, a mix in
      both orders, the word in two cases, a concern without it, a note with
      it, the word in `file` alone, and a concern tagged `witness`.
    witness: tests/test_spec_review.py::test_a_build_or_witness_blocker_and_an_unmeasured_concern_route_to_a_revision
  - claim: >-
      Given `revise`, `run_stack_batch` revises a spec whose review routes
      `revise`. It calls `revise` with the candidate, the layer the review
      read, the latest `spec_text` row's text on the spec's task or `None`,
      and the review session's `text`. It records the returned text with
      `record_spec_text`, and reviews the spec again on the same layer. Each
      review of a spec whose task holds a spec text gets the latest as the
      keyword `spec_text`, and a review of one that holds none gets no
      `spec_text`. Rounds are counted per call of `run_stack_batch`, never
      from the ledger. A read with a blocker still routed `revise` once
      `MAX_REVISE_ROUNDS`, 3, revisions ran escalates as `SA-0149`'s
      `escalate` does. Its line ends ` after 3 revisions`, and its
      descendants are refused. A read with no blocker never escalates. It is
      revised only when the spec has had no revision in this call, and
      otherwise routes `run`. With `revise` unset, a `revise` route with a
      blocker escalates with no suffix, and one without routes `run`. Each
      runner call's task holds, as its latest spec text, the text its last
      review read.
    witness: tests/test_batch.py::test_a_revisable_blocker_is_revised_and_reviewed_again_for_at_most_three_rounds
  - claim: >-
      A writer session with `resets_at` set ends the task `RATE_LIMITED` and
      goes through `SA-0148`'s wait, as a review routed `wait` does. The spec
      is offered again and revised again on the same review text, with no
      review between, and the session counts as no round. A session with an
      `error` ends the task `GATE_ERROR`, emits one ` unrevised  ` line
      holding the error, and counts as an abort. A `revise` that raises ends
      the task `GATE_ERROR` and counts as an abort. Before every revision
      round, the budget left is the batch's budget less `reserve_usd` and
      `batch_spend`. When it falls short of `SPEC_WRITER_SESSION_USD`,
      `SPEC_REVIEW_BUDGET_USD` and the spec's `budget_usd` together,
      `revise` is not called. The spec
      returns a `Refused` with an ` unrevised  ` line, counts no abort, and
      keeps its task's state.
    witness: tests/test_batch.py::test_a_revision_waits_on_a_rate_limit_and_stops_on_an_error_a_raise_or_the_budget
  - claim: >-
      Each writer session that returns adds one attempt to the spec's task
      in phase `spec_review.WRITING_PHASE`, `SPEC_WRITING`, with its cost,
      `session_id` and turns. Its subtype is `error` when the session
      carries an error, and `success` otherwise. A `revise` that raises adds
      none. Each text a session returns is one `spec_text` fact of origin
      `revision`, at `.saffron/specs/` and the candidate's file name,
      numbered on from the task's earlier rows. A review that led to a
      revision is recorded routed `revise`. One escalated for spent rounds
      or no writer is recorded `escalate`, and ends its task
      `SPEC_WITHHELD`. A read with no blocker that is not revised is
      recorded `run`.
      `batch_spend` counts each writer session once.
    witness: tests/test_batch.py::test_each_revision_is_an_attempt_and_a_spec_text_on_its_specs_task
  - claim: >-
      `cli._stack_review`'s callable takes an optional keyword `spec_text`.
      Given one, its prompt is the prompt it builds with none, then a
      sentence and the text inside a pair of spec tags. The sentence says
      to review that text, and that a change to what the spec is for is a
      scope blocker. `cli._stack_revise`'s callable, handed `None` as the
      spec text, reads `.saffron/specs/` and the candidate's file name at
      the pinned `base_sha`, and runs on that text. A path absent there
      raises `ValueError` naming it, before any cell comes up. The witness
      drives no layer, a layer whose fetched head holds another text, and a
      text handed in.
    witness: tests/test_cli.py::test_a_review_reads_a_recorded_text_and_a_revision_starts_from_the_queued_file
  - claim: >-
      `saffron batch --stack` builds `_stack_revise` once, with the
      `PinnedBase` built from readiness, the resolved `--repo` and `main`'s
      `out_dir`. It passes its callable to `run_stack_batch` as `revise`.
      When readiness fails, it builds none and passes `revise=None`.
    witness: tests/test_cli.py::test_a_stack_batch_passes_run_stack_batch_its_spec_revision
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §4.2,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:52-57`)
decides that an agent revises a spec for a witness or buildability blocker,
for a bounded number of rounds. Each round's fresh
review reads the revision beside the original. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design
(`:168-180`). A `build` or `witness` blocker is revised, up to three rounds.
A `scope` blocker, no tag, or a spec still blocked after round three is
skipped and escalated. An `unmeasured` concern from check 3 routes as
`witness`.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Revision rounds take two specs, and this is the second.** `SA-0160`
builds the writer session, its callable and its policy key. This spec
routes a spec to it, runs the rounds, records each one, and wires the
callable into `saffron batch --stack`. `SA-0161` then writes follow-up
specs with the same session.

**What the tree base holds.** This spec's tree base is `SA-0160`'s head.
Every line number below was read at `68892367`, where no chain code from
`SA-0142` on exists. So `batch.py`, `cli.py` and `spec_review.py` are cited
by symbol where the chain edits them. This spec consumes these names.

- From `SA-0143`, `SA-0148` and `SA-0157`: `run_stack_batch` and its runner
  wrapper, which hands a runner `(candidate, predecessor)`. A spec that
  reaches a miss through a `depends_on` entry is refused. `sleep` and the
  wait after a `RATE_LIMITED` task, which offers the same spec again on the
  same predecessor. `reserve_usd`, which the task loop holds back from each
  budget comparison.
- From `SA-0149`: `SpecReviewSession`, `read_spec_review`, and
  `spec_review_route`, which returns `wait`, `run`, `escalate` or `error`.
  Each finding on the read carries `severity`, `claim`, `fixes`,
  `criterion`, `file` and `line`. `run_stack_batch`'s `review` keyword. The
  wrapper reviews a spec, keeps its route by spec id, and reviews it once. An
  `escalate` emits `escalated  ` and its count of blockers, and returns a
  `Refused`. An `error` emits ` unreviewed  ` and raises. A `wait` goes
  through `SA-0148`'s wait and reviews the spec again.
- From `SA-0155`: the `mint` keyword. A stack batch mints a fresh task for
  every spec, every night, whatever task the queue carries (decision D1).
  So every run and attempt of the spec belongs to tonight's batch. Each
  review adds one attempt on that task in phase `SPEC_REVIEW`, and one
  `spec_review` fact with its route. `escalate` ends the task
  `SPEC_WITHHELD`, `error` or a raise ends it `GATE_ERROR`, and `wait`
  leaves it `RATE_LIMITED`. The task's run is attached to the batch, so
  `batch_spend` counts its attempts.
- From `SA-0168`: `run_task`'s keyword `task_id`, and `_stack_runner`,
  which passes it the candidate's `task_id`. The re-queue cap's phase
  clause admits `SPEC_REVIEW` and `SPEC_WRITING` beside `IMPLEMENTING`. So
  a writer attempt on a task disqualifies it from no cap.
- From `SA-0156`: `SPEC_REVIEW_BUDGET_USD`, 6.0, and `cli._stack_review`,
  whose callable takes a candidate and its layer. `_batch`'s `--stack`
  path builds `_stack_review` and `_stack_mint` where readiness passed and
  `pinned` is bound, and passes `None` for both when readiness fails. Its
  prompt file is the one `Policy.spec_review_prompt` names, read at the
  pinned base.
- From `SA-0150`: `Ledger.record_spec_text(task_id, *, origin, spec_id,
  path, text)` and `Ledger.spec_text(task_id)`, the task's latest row or
  `None`. `record_spec_text` takes a `spec_id` equal to the task's. A
  `revision` row's path is any one file name in `.saffron/specs/`.
  `run_task` then runs a revision only at the queued spec's own file at
  the pinned base, or at an earlier row's path on the task. Given a
  `task_id` whose task holds a spec text, `run_task` runs the latest text
  in place of the handed spec.
- From `SA-0160`: `SpecWriterSession`, `SPEC_WRITER_SESSION_USD`, the
  ceiling of both turns of one session, at most 12.50, and
  `cli._stack_revise`. Its callable takes a candidate, its layer, the
  spec's current text and a review's text. It returns what
  `run_spec_writer` returns: the whole spec file as `text`, or empty text
  with an `error` or a `resets_at`. It records nothing.

**Every revised spec passes gate 0 again before its cell (principle 54).**
`SA-0150` builds this for any task with a `spec_texts` row. `run_task`
refuses a text whose hash is not its `spec_sha`, one `parse_spec` refuses,
and one whose id or `depends_on` list differs from the handed spec's. It
refuses one whose `budget_usd`, `max_turns` or `max_attempts` exceeds the
handed spec's. It runs the `protected`, criterion path and retirement
refusals at the pinned base. `_stack_runner` hands `run_task` the task
(`SA-0168`), so each revision this spec records meets those checks. This
spec adds no check of its own.

**What the findings block says of `unmeasured`.** Check 3 names an
arrangement it could not run `unmeasured`. It reports it "as a concern
whose fix is that run" (`.claude/agents/spec-reviewer.md:72-80`). Its
findings block holds `severity`, `criterion`, `file`, `line` and `claim`,
and only a blocker adds `fixes` (`:149-153`). No field says "unmeasured".
So the word in a concern's `claim` is the one signal the block carries.

**Why the batch cannot read the queued file itself.** `_resolve_queue`
builds the queue from a temporary export of `.saffron/`. That directory is
gone once it returns (`saffron/cli.py:596-621`). So a
`Candidate.path` names a file that no longer exists by the time a batch
runs. Its name is still the spec file's name. The mirror holds the file at
the pinned base (`saffron/repos/mirror.py:231-259`).

**How a batch meets money today.** Before each task, `_drive` compares the
spec's `budget_usd` with the budget less `batch_spend`
(`saffron/batch.py:194-196`). Nothing checks money inside a runner call.
`batch_spend` sums the attempts of the tasks on the batch's runs
(`saffron/ledger.py:897-912`). `open_attempt` takes a phase
(`:1000-1023`).

## Problem

Build four things.

1. **The route.** In `saffron/spec_review.py`, `spec_review_route` gains
   `"revise"`, as criterion 1 states. Name the two revisable tags once, in
   a module constant the route reads. Add `WRITING_PHASE = "SPEC_WRITING"`,
   the phase of every writer session's attempt. `SA-0161` charges its
   follow-up writer in the same phase.
2. **The rounds.** In `saffron/batch.py`, add `MAX_REVISE_ROUNDS = 3` and a
   keyword `revise` on `run_stack_batch`, `None` by default. Revise inside
   the wrapper, where `SA-0149` reviews, as criteria 2 to 4 state. Keep the
   rounds and any review text awaiting a rate-limited writer by spec id,
   per call of `run_stack_batch`.
3. **The review's text and the writer's fallback.** Both are in
   `saffron/cli.py`, as criterion 5 states. `_stack_review`'s callable takes
   the keyword `spec_text`. `_stack_revise`'s callable takes `None` for its
   spec text. Read the queued file with `git_mirror.file_at`, before the
   fetch.
4. **The wiring.** In `_batch`'s `--stack` path, build `_stack_revise` where
   `_stack_review` is built, as criterion 6 states. `_stack_revise` then has
   a caller, and `SA-0160`'s `pending_symbols` entry for it is spent.
   `record_spec_text`, which `SA-0150` lists, gains its caller here too.

A round, in order:

- Review the spec on the layer. Read the task's latest spec text first,
  and hand it to the review as `spec_text` when there is one.
- Route the read. A `revise` route with a blocker becomes `escalate` with
  `revise` unset or three revisions run. One with no blocker becomes `run`
  with `revise` unset or one revision run. Record the review's attempt
  and fact with the route taken, as `SA-0155` does.
- On `revise`, check the budget left before every round, as criterion 3
  states. Compute it where the task loop computes its own comparison, from
  one held amount. Here that amount is `reserve_usd`. `SA-0173` adds
  `writer_usd` to it for generation 0. `SA-0162` runs follow-ups with both
  reserves released, so it passes the generation and the round's check
  releases them too. Read `spec_review.SPEC_WRITER_SESSION_USD` and
  `spec_review.SPEC_REVIEW_BUDGET_USD` through the module at call time.
  The check must see the spec's own attempts in `batch_spend`. `SA-0155`'s
  wrapper attaches the minted run right after the mint, before the first
  review, so every review and writer attempt already counts.
- Call `revise` with the task's latest spec text or `None`, and the review
  session's `text`. Record its attempt. A reset time waits, and an error or
  a raise ends the task `GATE_ERROR`.
- Record the text with `origin="revision"`, `spec_id` the candidate's, and
  the path `.saffron/specs/` plus `candidate.path.name`. Emit ` revised  `
  and the round's number. Go back to the review.

## Out of scope

- **A spec text recorded by another process.** In a batch, only the wrapper
  records a revision. It records none between a review routed `run` and
  that spec's runner calls. So the text the runner reads is the
  text the review read. Criterion 2's witness pins it at each runner call.
  A row another process records for the task between those two calls is
  not caught. `run_task` reads the latest row when it runs (`SA-0150`).
  Nothing outside a stack batch records a spec text, and a batch runs one
  task at a time (`DESIGN.md:407`).
- **Rounds and revisions across nights.** Each night mints a fresh task
  (D1), so its rounds and its texts start empty. A revision recorded on
  last night's task does not carry over, and tonight's review revises
  again from the queued file. No held-task path exists here for that
  reason: no attempt of tonight's spec lands on another night's run.
- **The reviewed text's number on the fact.** The `spec_review` fact
  records no `n` of the spec text it read. Inside a batch the pin holds by
  construction, as the first bullet says. A later reader cannot tie a
  review to its text from the facts alone.
- **A spend reserve for revisions.** Design section 3 draws spec work from
  a start-of-batch reserve. Here each round checks the budget left instead.
  `SA-0173` adds `writer_usd` to the held amount, and `SA-0162` releases
  both reserves for a follow-up's rounds.
- **The open pull request refusals on a revision.** A revision can change a
  spec's `touches`. `run_task` does not run gate 0's two refusals that need
  GitHub (`SA-0150`), and neither does this spec.
- **The earlier review, handed to the fresh one.** The fresh review reads
  the whole revised spec beside the original, as design section 3 says.
  The writer walks the earlier findings, since its prompt holds the
  review.
- **The words.** `CONTEXT.md` has no entry for a revision round, the
  `revise` route or the `SPEC_WRITING` phase. Backlog item b-466005 files
  them by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base routes
`revise`, calls a writer, or passes `revise` to a batch. So each criterion
declares a witness and no mutant, and `witness` reports `skip` for each.

**Every witness fails with the source reverted.** Criterion 1's build
blocker routes `escalate` there. Criteria 2 to 4 pass `revise=` to
`run_stack_batch`, which the tree base does not take. Criterion 5 passes
`spec_text=` to the review callable, and criterion 6 asserts a `revise`
keyword. Import each new name inside the test body.

**Keep the older witnesses as they are.** The loop witnesses of `SA-0149`
and `SA-0155` pass no `revise`. So a `build` or `witness` blocker there
still escalates with the same line. No spec there holds a spec text, so
the batch hands their review doubles no `spec_text`. If a row of
`SA-0149`'s route witness holds only `build` or `witness` blockers, change
that row's route to `revise` and nothing else. Type the `review` keyword so
it accepts the new keyword. A `run_stack_batch` fake in `tests/test_cli.py`
that names its keywords with no `**kwargs` gets `revise=None` added, and
nothing else.

**Criterion 1's witness** builds each session as `SA-0149`'s route witness
does, and asserts the route. `b(x)` is a blocker with `fixes` `x`, and
each finding holds `criterion`, `file` `a.py`, `line` and `claim` `x`
unless its row says otherwise.

| findings | route |
|---|---|
| `b(build)` | `revise` |
| `b(witness)` | `revise` |
| `b(build)`, `b(witness)` | `revise` |
| `b(build)`, `b(scope)` | `escalate` |
| `b(scope)`, `b(witness)` | `escalate` |
| `b(witness)`, `b(null)` | `escalate` |
| `b(build)`, a blocker with no `fixes` | `escalate` |
| a concern claiming `Unmeasured: criterion 2's arrangement` | `revise` |
| a concern claiming ``the arrangement is `unmeasured` `` | `revise` |
| a concern claiming `the witness is not measured` | `run` |
| a concern with `file` `unmeasured.py` | `run` |
| a note claiming `unmeasured` | `run` |
| a concern with `fixes` `witness` | `run` |
| a concern claiming `unmeasured`, then `b(scope)` | `escalate` |
| a concern claiming `unmeasured`, then `b(null)` | `escalate` |
| `b(build)` with `resets_at` 9 | `wait` |
| `b(build)` with `error` set | `error` |

These fail it, each measured:

- the word matched with its case, or any concern routed `revise`
- a note with the word routed `revise`
- the substring `measured`, or the word read from any field
- the first blocker's tag deciding the route
- an untagged blocker, or a null one, routed `revise`
- `escalate` for a `scope` blocker alone
- a concern tagged `witness` routed `revise`
- an unmeasured concern outranking a `scope` blocker

The choice of the word admits two wrong routes the witness cannot kill,
since the reviewer writes both. A concern that says "no longer unmeasured"
routes `revise`, and costs one round. A concern that says "not run" without
the word routes `run`, as every concern did before.

**Criteria 2 to 4 share one arrangement** in `tests/test_batch.py`, built
once. Its `ledger` has a `MemoryRecord` and its own repo, as `SA-0155`'s
arrangement does. The batch budget is 100, `reserve_usd` 8, `until`
`None`, with `_ready`, `SA-0148`'s clock and a fake `sleep` that records
each call. Each candidate's path is `<id>-x.md`, so a text recorded at the
spec id's own name fails. Every `budget_usd` is 12 unless a row says
otherwise.

- **The mint** creates a run and a task for the spec id, and keeps the
  task id by spec id. For `TE-5` alone it also records three `revision`
  texts on the new task, `s1\n`, `s2\n` and `s3\n`, at
  `.saffron/specs/TE-5-x.md`. So a round count read from the task's rows
  starts `TE-5` at 3.
- **The review double** takes `(candidate, layer, **kw)`. It records the
  spec id, the layer's spec id or `None`, and `kw`. It returns the spec's
  next scripted session. Each session's text is `report`, a newline, then
  the fenced `json` block, so a writer handed only the block fails. Each
  review costs 0.5. `u` below is a read holding one concern that claims
  `Unmeasured: the arrangement`, and no blocker.
- **The revise double** records `(spec id, layer id, spec text, review
  text)`, and the state of the spec's task at the call. It returns or
  raises the spec's next scripted turn. A written turn has `session_id`
  `w-1`, 9 turns and cost 1.0 unless its row says otherwise.
- **The runner double** records the spec id, `candidate.task_id`, and the
  text of `ledger.spec_text` of that task or `None`. It mints its own run
  and task with one closed attempt at 1.0, and returns
  `READY_FOR_REVIEW`.

| order | spec | reviews in turn | writer turns in turn |
|---|---|---|---|
| 1 | `TE-1` | `b(build)`, `b(witness)`, clean | `r1a\n`, `r1b\n` |
| 2 | `TE-2` | `b(witness)`, `b(witness)`, `b(build)`, `b(witness)` | rejected at cost 0.25 with `resets_at` 60 s on, then `r2a\n`, `r2b\n` and `r2c\n` |
| 3 | `TE-3`, on `TE-2` | none | none |
| 4 | `TE-4` | `u`, `u` | `r4\n` |
| 5 | `TE-5` | `b(build)`, `u` | `r5\n` |
| 6 | `TE-10` | `b(build)` three times, then `u` | `t1\n`, `t2\n`, `t3\n` |
| 7 | `TE-7` | clean | none |
| 8 | `TE-6` | `b(build)` | `error` `api_error`, cost 0.125 |
| 9 | `TE-9`, `budget_usd` 48.5 | `b(witness)`, `b(witness)` | `r9\n` |
| 10 | `TE-8` | `b(build)` | raises `RuntimeError("writer cell would not start")` |
| 11 | `TE-11` | none | none |

`TE-9`'s first round sees 24.375 spent, so 67.625 is left against a need
of 67. Its second sees 25.875 spent, so 66.125 is left, and it is refused.
Leaving out any one of the five terms lets the second round run. So does
`SPEC_WRITER_BUDGET_USD` in place of `SPEC_WRITER_SESSION_USD`, and a
check before the first round alone. The reviewer's figure of 56 assumed
the earlier order, and `TE-10` and the rounds moved the spend. The aborts
are `TE-6` and `TE-8`, with `TE-9` between them counting none. So the batch
stops `INFRASTRUCTURE` before `TE-11`. Each cost is a sum of powers of two,
so each total is exact.

**Criterion 2's witness** asserts these.

- The reviews are `TE-1` on `None` with no keyword, then with `spec_text`
  `r1a\n`, then `r1b\n`. Then `TE-2` on `TE-1` four times, with no keyword,
  `r2a\n`, `r2b\n` and `r2c\n`. Then `TE-4` on `TE-1` with none, then
  `r4\n`. Then `TE-5` on `TE-4` with `s3\n`, then `r5\n`. Then `TE-10` on
  `TE-5` with none, `t1\n`, `t2\n` and `t3\n`. Then `TE-7` on `TE-10`.
- The writer calls for `TE-1` hand it `None`, then `r1a\n`. Each call gets
  the text of the review before it. For `TE-2` on `TE-1` the calls hand it
  `None` twice, then `r2a\n` and `r2b\n`. `TE-4` gets one call, with `None`.
  `TE-5` gets one, with `s3\n`. `TE-10` gets three.
- The runner calls are `TE-1` with `r1b\n`, `TE-4` with `r4\n`, `TE-5`
  with `r5\n`, `TE-10` with `t3\n` and `TE-7` with none, each on its own
  task.
- The lines hold `TE-1`'s ` revised  2`, `TE-5`'s ` revised  1`, `TE-2`'s
  ` revised  3` and `TE-2`'s ` escalated  1 after 3 revisions`. `TE-3` is
  refused.
- A second batch in the same process, on a fresh ledger, runs `TE-2` and
  `TE-9`, each with `b(build)` then clean and one writer turn. Each prints
  ` revised  1`, so a store of rounds at module scope fails.
- A third batch on a fresh ledger runs `TE-11` with `b(build)` and `TE-12`
  with `u`, and no `revise`. It stops `DRAINED`, calls no writer, runs
  `TE-12` alone. Its last line for `TE-11` ends ` escalated  1`, with no
  suffix.

**Criterion 3's witness** asserts the sleeps are `[60.0]`. `TE-2`'s first
two writer calls see its task `QUEUED`, then `RATE_LIMITED`. The last
writer calls are `TE-6`, `TE-9` once, and `TE-8`, each on `TE-7`. The last
reviews are `TE-6`, `TE-9` twice, the second with `spec_text` `r9\n`, and
`TE-8`. One line for `TE-6` ends ` unrevised  api_error`. `TE-9` prints
` revised  1`, then one line holding ` unrevised  `. Exactly one line for
`TE-8` holds `raised RuntimeError`. The stop reason is `INFRASTRUCTURE`,
and no line names `TE-11`.

**Criterion 4's witness** reads each task's attempts as `(phase, cost)`.
With `R` for `SPEC_REVIEW` at 0.5 and `W` for `SPEC_WRITING` at 1.0:

| spec | attempts | state |
|---|---|---|
| `TE-1` | R, W, R, W, R | `QUEUED` |
| `TE-2` | R, W at 0.25, W, R, W, R, W, R | `SPEC_WITHHELD` |
| `TE-6` | R, W at 0.125 with subtype `error` | `GATE_ERROR` |
| `TE-8` | R | `GATE_ERROR` |
| `TE-9` | R, W, R | `QUEUED` |

Every other attempt's subtype is `success`. `TE-1`'s first `W` carries
`w-1` and 9 turns. `TE-1`'s `spec_text` facts are `(1, revision,
.saffron/specs/TE-1-x.md, r1a\n)`, then the same with 2 and `r1b\n`.
`TE-2`'s texts are `r2a\n`, `r2b\n` and `r2c\n`. `TE-5`'s fourth is `(4,
revision, .saffron/specs/TE-5-x.md, r5\n)`. `TE-6` and `TE-8` hold none.
The `spec_review` routes are these.

| spec | routes |
|---|---|
| `TE-1` | `revise`, `revise`, `run` |
| `TE-2` | `revise` three times, then `escalate` |
| `TE-4` | `revise`, `run` |
| `TE-5` | `revise`, `run` |
| `TE-10` | `revise` three times, then `run` |
| `TE-9` | `revise`, `revise` |

`batch_spend` is exactly 26.375. In the third batch, `TE-11`'s fact is
routed `escalate` and its task is `SPEC_WITHHELD`. `TE-12`'s is routed
`run`.

These fail criteria 2 to 4, each measured:

- no fresh review after a revision
- the fresh review handed no text, or a text only after tonight's revision
- each revision handed the queued file, or the review's block, or no layer
- rounds counted across the batch, from the task's spec texts, or at
  module scope
- a bound of 2 or of 4
- a read with no blocker escalated after the rounds, or with no writer
- a read with no blocker given three rounds
- D4 read as one unmeasured-triggered round, which revises `TE-5` a second
  time
- a rate-limited session counted as a round, or followed by a fresh review
- a rate-limited session read as an error, or leaving the state
- an errored revision returned as a refusal, or ending `SPEC_WITHHELD`
- a raise from the writer returned as a refusal, or leaving the state
- the budget refusal raised as an abort, or ending `SPEC_WITHHELD`
- no budget check, one before the first round alone, or one that leaves
  out any of its five terms
- the writer's first-turn ceiling in place of the session's
- no writer read as `run` for a blocker, or no suffix after the rounds
- no state for an escalation with no writer
- no attempt for a writer session, or one in phase `SPEC_REVIEW`
- an attempt only for a session that wrote a text
- the fact routed as read after the rounds are spent
- a text recorded at the spec id's own name, or as a follow-up
- the text recorded after the fresh review, so the runner reads a text no
  review read

**Criterion 5's witness** follows `SA-0160`'s witness for `_stack_revise`,
with its git helpers and doubles. The mirror's `base` commit holds a
policy naming the writer's and the reviewer's prompt files, both files,
and `.saffron/specs/SY-1-x.md` reading `queued at base\n`. A later commit
`head` sets that file to `at head\n`. The `repo` checkout holds it as `in
the checkout\n`. The fetch returns `head`. It pins `base`.

- It calls the review for `SY-1` with no text, then with `spec_text`
  `revised\n`. The second prompt starts with the first. The rest holds
  `<spec>\nrevised\n</spec>` and `scope blocker`. The first holds no
  `<spec>`.
- It calls the writer for `SY-1` with no layer and `None`, with the layer
  `SY-7` and `None`, and with no layer and `given\n`. The first two
  prompts hold `<spec>\nqueued at base\n</spec>`, and the third
  `<spec>\ngiven\n</spec>`. None holds `at head`, `in the checkout` or
  `None`.
- It calls the writer for `SY-5`, whose file is not at `base`, with
  `None`. That raises `ValueError` matching `.saffron/specs/SY-5-x.md`, and
  the count of `cell_up` calls is unchanged.

These fail it, each measured:

- the queued file read at the mirror's `HEAD`, from the checkout, or at the
  seeded tree
- no fallback, which puts `None` in the prompt
- a missing file sent as an empty spec
- the text with no spec tags, or in place of the prompt
- no sentence naming a scope blocker

**Criterion 6's witness** follows `SA-0156`'s wiring witness, with
`_readiness_passes` and `_fake_batch_resolution`. The policy at the pinned
base names both `spec_review_prompt` and `spec_writer_prompt`, since
`SA-0156` and `SA-0160` refuse a batch that leaves either unset. It replaces
`cli._stack_revise` with a recorder that returns a sentinel, and
`cli.run_stack_batch` with a fake that records its keywords and returns
`DRAINED`. It runs `main` with `batch --stack` with readiness passing, then
failing. With it passing, the recorder got the pinned base, the resolved
`--repo` and `main`'s `out_dir`, once, and the fake got the sentinel as
`revise`. With it failing, the recorder was not called and `revise` is
`None`. These fail it, unmeasured, since the `--stack` path is not at
`68892367`:

- no `revise` passed, which escalates every `revise` route
- the callable built before readiness, on a base not yet pinned
- the callable built with another `out_dir`, or the checkout unresolved

**How the lists were measured.** A throwaway prototype ran on 2026-09-24.
Its tree was `SA-0160`'s prototype, with stand-ins for `SA-0149`'s read
and route and for `run_stack_batch` as `SA-0143` to `SA-0157` leave it.
The stand-ins held `SA-0149`'s wrapper, `SA-0155`'s mint, attempts and
facts, and `SA-0148`'s wait with a fixed 60 seconds. A `Ledger` subclass
stood in for `SA-0150`'s and `SA-0155`'s tables and methods. The mint ran
for every spec, as D1 decides. It built
criteria 1 to 5 and their witnesses. The right build passed all of them.
Each wrong build listed as measured was applied as a text edit, and each
failed its witness. Criterion 6 needs `SA-0144`'s `--stack` path, so
nothing ran it.

**What the witnesses leave undriven.**

- A budget left exactly equal to a round's need. The check runs the round
  then.
- A follow-up's rounds with both reserves released. `SA-0162` passes the
  generation and drives it.
- A raise from `record_spec_text`. It propagates as an abort, and the task
  keeps the state its review left.
- A writer text that is not a spec. The fresh review reads it, and
  `SA-0150`'s `run_task` refuses it before any cell.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype, formatted by `ruff format`, measured 2138 changed tokens with
`size_gate`'s own count. The route took 73, the rounds 265 and the two
callables 96. The witnesses for criteria 1 to 5 took 1704, about 80 of it
a helper and imports `tests/test_batch.py` already carries. Criterion 6's
witness, the wiring and the docstrings add about 320. That is about 2380
tokens, 79% of the ceiling. Keep the arrangement's helpers shared across
the three batch witnesses.
