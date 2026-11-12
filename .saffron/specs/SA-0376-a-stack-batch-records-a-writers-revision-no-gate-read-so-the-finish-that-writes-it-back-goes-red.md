---
id: SA-0376
title: A stack batch records a spec writer's revision whose send-backs ran out with fault lines left, so the finish that writes it back goes red
type: bug
priority: 2
estimated_lines: 36
estimate_measured: true
touches:
  - saffron/spec_review.py
  - saffron/batch.py
  - tests/test_spec_review.py
  - tests/test_batch.py
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
  - saffron/cli.py
  - saffron/finish.py
  - saffron/follow_up.py
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
  - tests/test_cli.py
  - tests/test_finish.py
  - tests/test_follow_up.py
  - tests/test_draft.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 32
max_attempts: 3
max_turns: 170
acceptance:
  - claim: >-
      `SpecWriterSession` gains a field `fault_lines`, a tuple of strings
      that defaults to empty. `run_spec_writer` sets it to the lines
      `faults` last returned for the session's own `text`, once the
      send-backs ran out. The witness drives six sessions. A clean first
      draft and a send-back that comes back clean leave it empty. A
      send-back still faulted carries the second judgement's lines, which
      differ from the first's. A send-back that does not parse leaves the
      first text standing, with the first judgement's lines. When neither
      text parses, the newest text carries its own lines. A send-back
      whose work turn raises ends in `_give_up` and leaves it empty, as
      today.
    witness: tests/test_spec_review.py::test_a_writer_session_names_the_fault_lines_its_returned_text_still_carries
    wrong_versions:
      - The lines of the first judgement kept, so a send-back that comes back clean still carries them.
      - The newest judgement's lines used whatever text the session returns, so the first text standing carries the unparsed send-back's line.
      - The lines kept on a failed send-back, so the session that gave up carries them.
      - An unparsed text left with no lines, so the session where neither text parses carries none.
      - The field never set, so a send-back still faulted carries none.
  - claim: >-
      In `run_stack_batch`, a spec of the order whose writer session
      ends with `fault_lines` records no text. The batch emits one line,
      the spec id padded to ten columns, then `refused  <n> fault line(s)
      left after the writer's send-backs, first: <line>`, where `<n>`
      counts the lines and `<line>` is the first. It then emits each fault
      line on its own line, the spec id padded to ten columns and three
      spaces before it. It calls the writer no more, reviews the spec no
      more, never hands it to the runner, and marks it missed, so a spec
      whose `depends_on` reaches it is refused. A session with no fault
      lines is recorded and run as today, and so is a follow-up's
      revision whatever its fault lines. The witness drives a faulted
      order spec with a dependent, a clean order spec, and a faulted
      follow-up.
    witness: tests/test_batch.py::test_a_stack_batch_refuses_an_order_spec_whose_revision_still_carries_fault_lines
    wrong_versions:
      - A follow-up refused on its fault lines too.
      - The faulted text recorded before the refusal, so the task's rows hold it.
      - The spec refused but never marked missed, so its dependent runs.
      - The fault lines not emitted, so only the refusal line names one.
      - The refusal line naming the last fault line in place of the first.
      - The text sent back to the writer once more before the refusal.
      - No refusal at all, so the faulted text is recorded and run as today.
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
the same with `SA-0276` and `SA-0281`. Run 56's finish 73 ran an engine
from before `SA-0353` landed (#1099).

**What the writer session checks now.** Since `SA-0353`,
`_stack_revise` hands the writer a `faults` built by `_draft_faults`
(`saffron/cli.py:1569-1576`). It judges each draft with the policy's
`form: true` gates through `finish.judge_draft`
(`saffron/cli.py:1191-1211`). `prose` is one of them
(`.saffron/policy.yaml:24`). `_settle` sends a faulted text back while
send-backs remain (`saffron/spec_review.py:878`), and
`SPEC_WRITER_SEND_BACKS` is 1 (`saffron/spec_review.py:580`). Once they
run out, `_finish` returns the newest parsed text, or the newest of all
when none parsed, whatever its faults (`saffron/spec_review.py:858-867`).
`SpecWriterSession` holds no field saying whether that text still has
faults (`saffron/spec_review.py:649-666`). `_give_up` emits its message
and the lines that opened the failed send-back, then returns `_finish()`
(`saffron/spec_review.py:869-873`). A judge that raises inside
`draft_faults` is emitted once and yields no fault line
(`saffron/spec_review.py:641-645`).

**What the batch does with the session.** `run_stack_batch` calls
`revise` (`saffron/batch.py:894`) and records the attempt
(`saffron/batch.py:902-913`). A rate-limited session waits and an error
session is a miss (`saffron/batch.py:914-926`). Any other session's text
is recorded as a `revision` row, and the batch emits `revised  <n>`
(`saffron/batch.py:927-935`). The loop then reviews that text and, on a
`run` route, hands the spec to `runner` (`saffron/batch.py:842-866`,
`saffron/batch.py:937`). So a text whose send-backs ran out with `prose`
hits left is recorded, run, and later written back by the finish. The
escalation route shows how a refusal misses a spec of the order
(`saffron/batch.py:827-829`).

**Why a follow-up's revision protects no finish.** `commit_finish`
writes a follow-up layer's latest text to `ran_dir`, not into the
finishing commit (`saffron/finish.py:179-182`).

## Problem

A writer session can return a revision that still carries fault lines,
and the batch records and runs it as though it were clean. Make the
session say so, and refuse such a spec of the order for this batch.

1. In `saffron/spec_review.py`, add `fault_lines` to `SpecWriterSession`
   with an empty default, and pass it through `_writer_session`. In
   `_settle`, keep the lines of the newest parsed text and of the newest
   text beside each text. `_finish` hands over the lines of the text it
   returns. `_give_up` hands over none.
2. In `saffron/batch.py`, after the error check at line 918 and before
   line 927, refuse a spec of the order whose session carries
   `fault_lines`. Emit the refusal line and each fault line. Mark the
   spec missed and drop it from `remaining`, as lines 827-829 do. Return
   a `Refused` whose reason is the refusal line's text after `refused  `.
3. Write the two witnesses the criteria name.

## Out of scope

- **A follow-up's revision.** Its text goes to `ran_dir`, never into the
  finishing commit (`saffron/finish.py:179-182`), so refusing it protects
  no finish. It is recorded as today.
- **A session that ends in `_give_up`.** It returns its text with no
  fault lines, as today. Its message and lines are emitted already.
- **A judge that raises inside `faults`.** `draft_faults` emits it and
  returns no fault line, so the text is recorded as today.
- **Gates that are not form gates.** The session's judge narrows the
  suite to the `form: true` gates by design (`saffron/cli.py:1191-1199`).
  `tests` reads the live specs and is no form gate
  (`.saffron/policy.yaml:6`), so it can still turn a finish red on a
  revised text. `census` is a core gate, which the narrowed suite still
  runs (`saffron/cli.py:1145-1147`). What it compares there with `tests`
  left out was not measured.
- **The refused task's state.** The refusal sets none, as the budget
  refusal at lines 881-892 sets none. It raises nothing, so the breaker
  counts no abort (`saffron/batch.py:358-361`).
- **`saffron draft` and the follow-up writer.** Both build sessions with
  `run_spec_writer`, and neither reads the new field.
- **`saffron/cli.py`.** No adapter changes. The field reaches the batch on
  the session `_stack_revise` already returns.

## Notes for the agent

**Every criterion is new code.** `fault_lines` and the refusal do not
exist yet, so no mutant pins their spelling. `witness` will report
`skip` for each, and the wrong versions under each criterion say what
its witness must still catch.

**Where an operator reads the reason.** `_batch` passes no `emit`
(`saffron/cli.py:2668-2686`), so `run_stack_batch` prints
(`saffron/batch.py:503`). The refusal line and each fault line reach the
batch's stdout, which is the launchd log on an unattended night. `run_spec_writer` emits fault lines
only in `_give_up`, so the batch emits them itself.

**Doubles for `tests/test_spec_review.py`.** `_Agent`, `_draft`,
`_write_extract`, `_attempt`, `_faults_double`, `_run_writer`,
`_WRITE_SPEC`, `_SECOND_SPEC` and `_SECOND_V` already exist. Script the
second judgement's lines to differ from the first's, so a version that
keeps the first lines fails. For the failed send-back, script an
`implement.AgentFailed` as the work turn. The existing
`test_a_failed_send_back_keeps_the_last_draft_that_parsed_and_says_why`
compares whole sessions, so it already pins `_give_up` to empty lines.

**Doubles for `tests/test_batch.py`.** Subclass `StackDoubles`
(`tests/test_batch.py:5548`) with a writer that returns scripted sessions
by spec id, built with `dataclasses.replace` on `_written`. Keep the
latest recorded text each runner call sees. Read a task's rows with a
query over `spec_texts` ordered by `n`, and compare whole lists, so a
negative check has its positive case. Give the faulted spec one route,
`revise`, so a second review raises. Give it one scripted session, so a
second writer call raises.

**At base each witness fails in its body.** `SpecWriterSession` has no
`fault_lines`. Import nothing the change adds at module scope.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. `SpecWriterSession`'s docstring stays within ten
lines.

**Size.** A prototype measured 141 changed tokens with `size_gate`,
against the `bug` ceiling of 1300, with 634 more under the test paths.
It held both source changes and the two witnesses. Every test in
`tests/test_batch.py`, `tests/test_spec_review.py`,
`tests/test_follow_up.py`, `tests/test_draft.py`, `tests/test_cli.py`
and `tests/test_finish.py` passed on it.
