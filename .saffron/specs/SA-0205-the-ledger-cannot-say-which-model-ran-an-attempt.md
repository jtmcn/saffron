---
id: SA-0205
title: The ledger cannot say which model ran an attempt, because no writer of an attempt row passes one
type: feature
priority: 3
depends_on: [SA-0203]
estimated_lines: 297
estimate_measured: true
touches:
  - images/agent_runner.py
  - saffron/phases/implement.py
  - saffron/cell/session.py
  - saffron/spec_review.py
  - saffron/batch.py
  - saffron/follow_up.py
  - saffron/ledger.py
  - tests/test_agent_runner.py
  - tests/test_implement.py
  - tests/test_session.py
  - tests/test_spec_review.py
  - tests/test_batch.py
  - tests/test_follow_up.py
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
  - records/**
  - hooks/**
  - images/cell-base.python.Dockerfile
  - images/proxy.Dockerfile
  - saffron/cli.py
  - saffron/task.py
  - saffron/replay.py
  - saffron/events.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 34
max_attempts: 3
max_turns: 190
acceptance:
  - claim: >-
      The runner's `result` event carries a `model` key. Its value lists each
      distinct `model` the run's assistant messages named, in the order each
      first appeared, joined with ",". An assistant message whose `model` is
      exactly `<synthetic>`, or empty, is skipped. A run with no other
      assistant message gives `null`. The `init` event's model is never
      read. Each run starts with no model seen. The witness drives five runs
      through `main` in one process. They are several models with repeats
      and a synthetic and an empty name among them, one model sent twice,
      none at all, a synthetic and an empty name alone, and one model after
      those two.
    witness: tests/test_agent_runner.py::test_the_result_event_names_each_model_the_turns_assistant_messages_named
    wrong_versions:
      - The model is read from the `init` event's data, so a run carries the configured model.
      - Only the last assistant message's model is kept.
      - The names are sorted, so a run that met `m-b` first reads `m-a,m-b`.
      - A run with no assistant message carries the empty string rather than `null`.
      - The models seen are never cleared between runs, so a later run in one process reports an earlier run's model.
      - The model is read from the result message's `model_usage` keys.
      - A `<synthetic>` name is recorded as a model.
      - An empty name is kept, so a run reads `m-b,m-a,` or `""`.
  - claim: >-
      `AttemptResult` has a field `model`, `None` by default. `run_agent`
      sets it to the result event's `model`, a joined string kept as it
      came. A result event whose `model` is `null` or absent gives `None`.
      A failed turn that reached a result event carries that event's model
      on `AgentFailed.attempt`. A turn with no result event carries `None`.
      An `init` event naming another model changes none of these.
    witness: tests/test_implement.py::test_a_turn_records_the_model_its_result_event_names
    mutant:
      file: saffron/phases/implement.py
      find: model=result.get("model"),
      replace: model=None,
    wrong_versions:
      - The model is taken from the `init` system event, which every stream carries.
      - The model is set on a clean turn only, so a failed turn's attempt carries `None`.
      - A joined value is split and only its first name kept.
  - claim: >-
      Each turn `record_attempts` wraps closes its attempt row with the
      turn's model. That holds for a turn that returns, and for one that
      raises `AgentFailed` carrying its attempt. A turn that raises
      `AgentFailed` with no attempt closes its row with `None`, as does a
      turn whose attempt names no model. The witness drives each of those
      outcomes in order through one wrapped agent.
    witness: tests/test_session.py::test_every_recorded_turn_writes_the_model_its_attempt_names
    mutant:
      file: saffron/cell/session.py
      find: model=attempt.model if attempt else None,
      replace: model=None,
    wrong_versions:
      - The failed path closes its row with `None` though its attempt names a model.
      - A turn whose attempt names no model is recorded as `unknown`.
  - claim: >-
      `SpecReviewSession` has a field `model`, `None` by default. Every
      session `run_spec_review` returns names each distinct model its turns
      named, in first-seen order, joined with ",". A turn's own joined value
      counts as each name in it, and an empty segment counts as none. A
      session whose turns named none gives `None`. The witness drives every
      return path, one row each, and each of those rows expects a model. They
      are a rejected window on the first turn and on the extraction turn, a
      failed first turn, a first turn with no session, a failed extraction
      turn, a clean extraction, a clean re-ask, and a re-ask still off the
      schema. A ninth row, a second clean extraction whose turns name
      nothing, gives `None`.
    witness: tests/test_spec_review.py::test_a_spec_review_session_names_each_model_its_turns_named
    wrong_versions:
      - Only the last turn's model is kept.
      - Turn values are joined without splitting, so `m-a,m-b` then `m-b` gives `m-a,m-b,m-b`.
      - The model reaches the clean returns only, so a failed or rejected session carries `None`.
      - The names are sorted.
      - An empty segment is kept, so `m-a,,m-b` gives `m-a,,m-b`.
  - claim: >-
      `SpecWriterSession` has a field `model`, `None` by default. Every
      session `run_spec_writer` returns names its turns' models by the same
      rule as the review's. The witness drives the same nine rows as the
      review's witness.
    witness: tests/test_spec_review.py::test_a_spec_writer_session_names_each_model_its_turns_named
    wrong_versions:
      - "`_writer_session` gains the field and one of its callers passes nothing, so that path carries `None`."
      - Only the last turn's model is kept.
      - Turn values are joined without splitting.
      - The names are sorted.
      - An empty segment is kept.
  - claim: >-
      `run_stack_batch` closes each `SPEC_REVIEW` attempt with its review
      session's `model`, and each spec-writing attempt with its writer
      session's `model`. That includes a writer session that carried an
      error. A session whose `model` is `None` writes `None`. The witness
      drives both sites, a joined value at each, and a `None` review.
    witness: tests/test_batch.py::test_each_spec_session_attempt_records_the_model_its_session_names
    mutant:
      file: saffron/batch.py
      find: model=turn.model,
      replace: model=None,
    wrong_versions:
      - The review's attempt carries the model and the revision's does not.
      - The revision's attempt carries the model only when the session carried no error.
  - claim: >-
      `write_follow_ups` closes each spec-writing attempt it charges with
      that writer session's `model`. The witness drives all five paths that
      charge a session. They are an accepted follow-up charged to its minted
      task, then four pooled groups charged to the layer's task. Those carry
      an error, text that does not parse, a spec whose id is wrong, and a
      rate limit. Each of the five sessions names its own model.
    witness: tests/test_follow_up.py::test_a_follow_up_writers_attempt_records_the_model_its_session_names
    mutant:
      file: saffron/follow_up.py
      find: model=session.model,
      replace: model=None,
    wrong_versions:
      - The accepted follow-up's row carries the model and a pooled group's row does not.
---

## Context

Backlog item **b-3732ef**, which cites `DESIGN.md` §5.4. Its "Done looks
like" has two halves. The ledger records the model of every attempt.
Then a measurement reruns `EXHAUSTED` tasks with a stronger model from
attempt 3. This spec is the first half only. The item's own record says
the second spends real money on live runs, so it runs by hand from
`docs/evidence/scripts/`. This spec records the model and never chooses
one. It adds no `model` option to `implement.agent_options`.

Every line number below was read at `b698e484`. This spec's parent chain,
`SA-0201` to `SA-0203`, edits `saffron/phases/implement.py`,
`saffron/cell/session.py`, `saffron/batch.py` and their tests first. So
the lines cited in those files sit elsewhere at the cell's base. Each
citation names its function. Find it by that name. `SA-0201` gives
`AttemptResult` a new boolean field, set where `run_agent` builds the
attempt. It adds no place an attempt is built and no caller of
`close_attempt`.

**The ledger can already hold a model.** `Ledger.close_attempt` takes a
keyword `model`, `None` by default (`saffron/ledger.py:1359-1385`). The fold
writes it into `attempts.model` (`:688-701`). No writer passes a value.

**The writers.** Four call sites in three modules close an attempt row for
an agent session.

- `_close_attempt` passes `model=None` with a comment saying no model is
  available (`saffron/cell/session.py:220-236`, the line at `:229`).
  `record_attempts` calls it on a returned turn and on `AgentFailed`
  (`:193-217`). `_drive_cell` wraps every plan, implement, repair, review
  and rebuttal turn in `record_attempts` (`:2054-2064`).
- `run_stack_batch` closes a `SPEC_REVIEW` attempt from a
  `SpecReviewSession` (`saffron/batch.py:580-588`). It closes a spec-writing
  attempt from the writer's `turn` (`:686-695`). Neither passes `model`.
- `write_follow_ups`'s `_charge` closes a spec-writing attempt from a
  `SpecWriterSession` (`saffron/follow_up.py:254-263`). It passes no `model`.
  Five call sites reach it (`:336`, `:340`, `:347`, `:359`, `:372`).

A fifth writer, `replay`, closes a `REPLAY` attempt with no agent at all
(`saffron/replay.py:88-100`). It has no model to record and stays as it is.

**Where the model is.** The SDK pinned in the cell is
`claude-agent-sdk==0.2.142` (`images/cell-base.python.Dockerfile:33`). Read
from its wheel, outside this repo: `AssistantMessage` declares `model` as a
required `str`, at line 1123 of the package's `types.py`. Its parser builds
that from `data["message"]["model"]`. `ResultMessage` has no `model`, only
`model_usage`, keyed by model name. The runner's `result`
event carries neither (`images/agent_runner.py:131-145`). `events()` uses
`hasattr(message, "model")` only to tell an assistant message apart
(`:149`). The `system`/`init` event carries the configured model inside
its clipped `data`. Measured by the operator: 1,565 `init` events in
`~/.saffron/batches` since 2026-09-01 each name `claude-sonnet-5`. So the
model reaches `events.jsonl` today, and never the ledger.

**The aggregating sessions.** `run_spec_review` and `run_spec_writer` each
run up to three turns. Each sums cost and turns and keeps the last session
id in a local `_measure` (`saffron/spec_review.py:321-327`, `:625-631`).
`SpecReviewSession` (`:107-122`) and `SpecWriterSession` (`:562-576`) carry
no model. `run_spec_review` builds its return in seven places.
`run_spec_writer` builds every return through `_writer_session`
(`:579-596`).

**One existing test changes.**
`test_the_result_event_carries_what_the_supervisor_bounds_on` compares the
whole result event with `==` (`tests/test_agent_runner.py:85-114`). It
gains the `model` key, `None` there, since that test feeds no assistant
message.

## Problem

1. **The runner names the model.** Keep each distinct `model` the run's
   assistant messages carry, in first-seen order. Put them in the `result`
   event under `model`, joined with ",", or `null` when there are none.
   Skip a message whose `model` is exactly `<synthetic>`, or empty. The
   CLI writes `<synthetic>` itself for a turn it answers without a model,
   such as a rate limit or an API error.
   Not `model_usage`, which can list helper models the agent's own loop
   never called. Not the `init` event, which states the configured model
   rather than the one that answered. One runner process is one
   `run_agent` call, as the comment above `_seen_assistant_message_ids`
   says (`images/agent_runner.py:43-46`). Clear what you keep in `main`,
   beside `_query_yielded` (`:214-216`), so each run starts empty.
2. **`AttemptResult` carries it.** Add `model: str | None = None` as the
   last field (`saffron/phases/implement.py:84-105`). Read it from
   the result event where the clean or failed `attempt` is built
   (`:386-401`). The no-result path (`:350-364`) leaves it `None`, as it
   leaves `session_id`. `_failed_turn`'s own fallback stays `None` too
   (`saffron/cell/session.py:735-745`).
3. **`_close_attempt` passes it.** Replace `model=None` and its comment.
   The value comes from the attempt, or `None` when there is no attempt.
4. **The two session types carry it.** Add `model: str | None = None` to
   each. Collect names in `_measure`, splitting each turn's value on ",".
   Pass the joined names, or `None`, to every return.
5. **`batch.py` and `follow_up.py` pass it** to `close_attempt` from the
   session at each of the three sites above.
6. **The schema comment.** In `saffron/ledger.py`, the comment above
   `attempts` (`:148-151`) says the session's own call site still passes
   `None`. Rewrite it to say what `model` holds now. Change nothing
   else in `ledger.py`.

## Out of scope

- **Choosing a model.** No `model` option reaches `agent_options`, and no
  turn starts a fresh session. That is the item's second half, by hand.
- **`DESIGN.md` §4.1.** The operator already amended its sentence on
  `attempts.model` in this spec's branch (`DESIGN.md:365`). It reads
  "`attempts.model` names the models an attempt's assistant messages
  named, comma-joined in first-seen order. The CLI's own `<synthetic>`
  marker is no model and is skipped (SA-0205)." The file is protected.
  Do not touch it.
- **`replay`.** Its attempt has no agent, so `None` is its true model.
- **End review turns.** Their agent is `stop_on_rejected` over
  `run_agent` with no `record_attempts` (`saffron/cli.py:657-663`). So
  they write no attempt row today, and this spec adds none.
- **Filtering names past `<synthetic>`.** The runner drops that one name
  and keeps every other name as sent. The operator measured it on
  2026-10-03 in 15 Claude Code transcripts under `~/.claude/projects` on
  the host. The CLI wrote it for messages such as "You've hit your weekly
  limit", "API Error: 500/529" and "Not logged in". Those are the walled
  and errored turns, so a kept name would read `claude-sonnet-5,<synthetic>`.
  `<synthetic>` is no model identifier (`CONTEXT.md:93`). Cell transcripts
  are not kept on the host. So whether such a message reaches the SDK
  stream inside a cell is not measured, and the skip costs nothing if none
  does. No subagent message reaches the runner, since `IMPLEMENT_TOOLS`
  (`saffron/phases/implement.py:30`) offers no `Task`.
- **Rows written before this change.** They keep `None`.

## Notes for the agent

**Which criteria are new code.** Criteria 1, 4 and 5 add code whose
spelling nothing at base fixes. They declare no mutant, and the `witness`
gate reports `skip` for them. Criteria 2, 3, 6 and 7 edit a call that
exists. Each declares a mutant that mirrors the line beside it, the way
`session_id` is passed at the same call.

**Commit as each witness passes.** Seven witnesses, seven commits at least.
A turn cut by a bound then loses one witness's work, not seven.

**Every witness must fail with the source reverted.** Import nothing this
spec adds at module scope. Build a session or attempt with a model inside
the test, with `dataclasses.replace(..., model=...)` or a constructor
call. At base that raises `TypeError` in the test body, a failure, and not
a collection error that `revert` reads as `skip`.

**Criterion 1.** Use `_run_runner_in_process` and `_stub_module`
(`tests/test_agent_runner.py:475-509`). Run `main` five times in one test.
Send one assistant message's `message_id` twice. Put an
`init` system message naming a different model first in each run. The
`none` run sends `init`, a partial message and the result. In the
several-models run, meet the names against alphabetical order, `m-b`
before `m-a`, so a sorted join fails. Put a `<synthetic>` message between
real ones there. Send a message whose `model` is `""` last among that
run's assistant messages. A kept empty name then reads `m-b,m-a,`, which a
run of empty names alone can hide behind a `null`. The synthetic-alone run sends `init`, a
`<synthetic>` message, a message whose `model` is `""`, and the result.
It gives `null`. Run the one-model run last, so a synthetic name kept
from an earlier run would show there. Clear any
module list you add in the `_forget_seen_message_ids` fixture
(`:38-45`), with `getattr` and a default as that fixture already does. A
module list that leaks between tests turns the exact-dict test red.
Annotate any module-level list you add, as `_seen_assistant_message_ids:
set[str]` is annotated (`images/agent_runner.py:46`). The `types` rule
on unannotated identities is gated.

**Criterion 2.** Use `_stream` and `_result_line`
(`tests/test_implement.py:185-237`). Drive a joined value, a single name,
`null`, an absent key, an `is_error` result with exit 1, and a stream with
no result event. `_result_line` names no model, so pass one. The
`is_error` row's result names a joined value, and the test asserts it on
`AgentFailed.attempt.model`. Put an `init` event naming another model
before the result in every row, the `null` and absent-key rows above all.
A fallback to the `init` model then fails there.

**Criterion 3.** Build a real `Ledger` under `tmp_path`, with one repo, run
and task. Wrap a scripted agent in `session.record_attempts` and call it
once per outcome. Read the rows back with `ledger.attempts`. The returned
attempt and the attempt on `AgentFailed` each name a distinct model, so a
failed path that drops its model fails.

**Criteria 4 and 5.** Use `_Agent`, `_first`, `_second`, `_draft` and
`_write_extract` (`tests/test_spec_review.py:54-87`, `:190-204`,
`:1452-1466`). One row per return path. Those helpers build attempts
with no model, and `_KILLED` builds a failure with none. So give every
row's first turn a model with `dataclasses.replace`. Raise a failed first
turn as `AgentFailed(..., replace(_first(), model=...))`, never as
`_KILLED`. All eight return-path rows expect a model. The ninth row, a
second clean extraction whose turns name nothing, is the only one that
expects `None`. That is how a return path that passes nothing shows, on
the rejected, failed and no-session rows above all. In the clean row the
first-seen order runs against alphabetical, `m-b` before `m-a`. Repeat a
name across turns in the clean re-ask row. In the off-schema row, give
the first turn a joined value with an empty segment, `m-a,,m-b`, then a
turn naming `m-b` again.

**Criterion 6.** Use `_RevisionMint`, `_RevisionWrite`, `_RevisionRunner`,
`_written` and `_writer_error` (`tests/test_batch.py:3310-3457`), with a
small `review` callable of your own. One spec revises once and runs. A
second spec's writer session carries an error. `_writer_error` builds a
session with no model, so give that session its own model with
`dataclasses.replace`. Give each review session and each writer session a
distinct model, except one review left at `None`.

**Criterion 7.** Use `_build`, `_stack`, `_qualify_stub`, `_write_stub` and
`_mint_stub` (`tests/test_follow_up.py:131-330`), with a group built as `_q` and
`_shared_findings` build theirs (`:241`, `:369`). Send five groups. A
writer session that met the rate limit pools every later group, so send it
last. Pass every session as a `SpecWriterSession`, never as a string,
since `_write_stub` turns a string into a session with no model. The
accepted, error, parse-failure, wrong-id and rate-limit sessions each
carry a distinct model. A rate-limit session with no model would let its
own path drop the model unseen.
