---
id: SA-0341
title: A rebuttal extraction that is not the schema gets no second chance, so one trailing comma loses every argument
type: bug
priority: 2
depends_on: [SA-0340]
estimated_lines: 53
estimate_measured: true
touches:
  - saffron/phases/rebut.py
  - saffron/events.py
  - saffron/cell/session.py
  - tests/test_rebut.py
  - tests/test_session.py
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
  - hooks/**
  - saffron/ledger.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/review.py
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - tests/test_task.py
  - tests/test_report.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
budget_usd: 42
max_attempts: 3
max_turns: 210
risk: standard
acceptance:
  - claim: >-
      An extraction whose answer is not the schema is re-prompted once. The
      re-prompt resumes the extraction's own session with the extraction's
      own options, and its prompt is the validation error followed by the
      extraction prompt. A schema answer then gives the turn its rebuttals,
      with no error, the first error kept as `reprompt_error`, and every
      turn's cost summed. One `PhaseStart` quoting the error is emitted
      between the first extraction and the re-prompt. The witness drives both
      shapes `_validate` calls not the schema, an answer with no structured
      output and a value the model rejects.
    witness: tests/test_rebut.py::test_an_extraction_that_is_not_the_schema_is_re_prompted_once_quoting_its_error
    wrong_versions:
      - The re-prompt sends the bare extraction prompt, without the validation error.
      - The re-prompt drops `output_format` from its options.
      - The re-prompt resumes the session the fix turn reported rather than the extraction's.
      - The re-prompt sends the fix turn's prompt again before the extraction prompt.
      - The turn's cost leaves out the re-prompt's.
      - The turn keeps the extraction's session id rather than the re-prompt's.
      - Only a value the model rejects is re-prompted, so an answer with no structured output keeps its error.
      - Only an answer with no structured output is re-prompted.
      - The line is emitted after the re-prompt returns.
      - The line names the re-prompt without quoting the error.
      - "`reprompt_error` is left unset when the re-prompt's answer is read."
  - claim: >-
      A second answer that is not the schema is not re-prompted again. The
      turn makes three calls in all, and its error is the second answer's own
      `not the schema` error from `_validate`. Its rebuttals are empty, and
      its cost sums all three calls. The witness drives the two shapes in both
      orders, with a schema answer scripted after them.
    witness: tests/test_rebut.py::test_a_second_unreadable_extraction_is_recorded_and_not_re_prompted
    wrong_versions:
      - The extraction is re-prompted until an answer is the schema.
      - The turn's error is the first answer's error rather than the second's.
      - The turn's error is rewritten to a new sentence that does not start with `not the schema`.
      - The turn's cost leaves out the second answer's.
  - claim: >-
      A turn that raised `implement.AgentFailed` is never re-prompted, and the
      fix turn runs once in every case. The witness drives each turn that can
      raise, with schema answers scripted after it. A failed fix turn makes one
      call. A failed first extraction makes two. A failed re-prompt makes
      three. Each keeps the raised error as its own, with the cost of every
      call it made. Only the re-prompt's failure sets `reprompt_error`.
    witness: tests/test_rebut.py::test_a_turn_that_raised_is_never_re_prompted_and_the_fix_turn_never_repeats
    wrong_versions:
      - A first extraction that raised is re-prompted too.
      - A fix turn that raised buys an extraction.
      - A re-prompt that raised is followed by another.
      - A re-prompt that raised leaves the turn with the first answer's schema error.
      - A re-prompt that raised is charged nothing.
      - An unreadable extraction runs the fix turn again before it asks for the schema.
  - claim: >-
      The re-prompt draws on the extraction's reserve under `_RebutCap`. In a
      whole cell with that reserve's money left, its `max_budget_usd` is what
      the pool holds after the first extraction. With nothing left the pool
      refuses it and it never starts. The task then ends `EXHAUSTED` with the
      extraction's reserve line, and `rebuttal.json` carries the pool's
      refusal as the error. The re-prompt's line, which says it is
      re-prompting once, comes before the line naming that refusal. A
      re-prompt that fails having spent the rest ends the same way, naming its
      own error. The witness drives all three.
    witness: tests/test_session.py::test_the_extraction_re_prompt_draws_on_the_extraction_reserve_and_one_it_cannot_cover_does_not_start
    wrong_versions:
      - The re-prompt opens the extraction's pool again, so it gets a fresh $4.00 reserve.
      - The pool's refusal of the re-prompt is caught and the first answer's schema error kept, so `rebuttal.json` names no refusal.
      - The verdict pool is opened before the re-prompt, so the re-prompt draws on the verdicts' reserve.
      - The re-prompt line is emitted only once the call returns, so a refused re-prompt logs none.
  - claim: >-
      The re-prompt is visible in `events.jsonl` and in `rebuttal.json`. The
      witness drives three cells through the real event log. A first answer
      that is read writes `reprompt_error` as null and logs no extra REBUT
      line. A re-prompt whose answer is read logs one REBUT `PhaseStart`
      quoting the first error, before REBUT's summary line, and
      `rebuttal.json` names that error under `rebuttal.reprompt_error`. A
      re-prompt whose answer is not the schema does the same, with the second
      error under `rebuttal.error`.
    witness: tests/test_session.py::test_the_extraction_re_prompt_is_logged_in_events_jsonl_and_named_in_rebuttal_json
    wrong_versions:
      - "`as_dict` leaves `reprompt_error` out of `rebuttal.json`."
      - "`as_dict` writes `reprompt_error` only when it is set, so a read first answer has no key."
      - The re-prompt line is emitted through `print` rather than `emit`, so `events.jsonl` never holds it.
      - The re-prompt line is emitted for every extraction, read or not.
      - The re-prompt line carries `phase="REVIEW"`.
---

## Context

Backlog item **42**, its re-prompt half. It cites `DESIGN.md` §5.6. Every
line below was read at `6db66941`.

`DESIGN.md` §5.6 reads as amended at that commit (`DESIGN.md:1264`). An
extraction that is not the schema is re-prompted once. The re-prompt quotes
the validation error and draws on the extraction's reserve. The fix turn is
never repeated, and a second unreadable answer is recorded as unreadable. The
reserve paragraph after it is unchanged (`DESIGN.md:1266`). The extraction's
pool is $4.00 plus what the rebuttal turn left of the $10.00 cap.

**What the turn does today.** `run_rebuttal` runs the fix turn, then one
extraction (`saffron/phases/rebut.py:239-270`). A fix turn that raised
`implement.AgentFailed` returns at once with `error=str(failed)`
(`saffron/phases/rebut.py:248-253`). So does an extraction that raised
(`saffron/phases/rebut.py:266-270`). An answer `_validate` rejects returns
with its `not the schema` error (`saffron/phases/rebut.py:277-281`).
`_validate` names two shapes (`saffron/phases/rebut.py:90-95`). One is an
answer with no structured output, and the other a value `model_validate`
rejects. The comment at `saffron/phases/rebut.py:274-276` gives the reason for
no re-prompt. This spec reverses it.

**The record.** `RebuttalTurn.error` holds the failure
(`saffron/phases/rebut.py:105-107`). `RebutResult.as_dict` writes it under
`rebuttal.error` (`saffron/phases/rebut.py:148-151`), and `session.py` writes
that dict to `rebuttal.json` (`saffron/cell/session.py:3717-3719`). On
`SA-0040` one trailing comma lost both arguments of a $2.59 turn, and the
critic then confirmed a blocker on a false premise.

**The pool.** `session.py` wraps every REBUT session in `_RebutCap`
(`saffron/cell/session.py:3636-3637`). `run_rebuttal` opens the extraction's
pool before the extraction (`saffron/phases/rebut.py:256`). A call the pool
cannot cover raises `implement.AgentFailed` reading `the REBUT extraction pool
is already spent` and sets `cut` (`saffron/cell/session.py:222-229`). A failed
call that spends the pool sets `cut` too (`saffron/cell/session.py:236-241`).
A cut that leaves REBUT `REBUTTAL_UNJUDGED` becomes `EXHAUSTED`, with the
reserve's line (`saffron/cell/session.py:3697-3705`).

**The patterns.** The plan checkpoint re-prompts once, with the error ahead
of the extraction prompt, and emits a `PhaseStart` first
(`saffron/cell/session.py:718-736`). A REVIEW lens does the same through
`_parse_or_reprompt` (`saffron/phases/review.py:235-290`). Its `announce`
emits the lens's line (`saffron/phases/review.py:328-337`).

## Problem

1. **The re-prompt.** In `run_rebuttal`, an extraction answer `_validate`
   rejects earns one more call. It resumes the extraction's session id, with
   the extraction's options, and prompts with the error, a blank line, then
   `EXTRACT_PROMPT`. A schema answer is the turn's result. A second rejected
   answer, or a raise, ends the turn with that error. The fix turn never runs
   again.
2. **The record.** `RebuttalTurn` gains `reprompt_error: str | None`, the
   error the re-prompt quoted, default `None`. `as_dict` writes it under
   `rebuttal.reprompt_error`, always, null when no re-prompt ran.
3. **The line.** Before the re-prompt's call, emit one `PhaseStart` with
   `phase="REBUT"` and `label="REBUT"`. Its detail says the extraction was not
   the schema, says `re-prompting once` as intent, and quotes the error. The
   pool can still refuse the call after it, as at the plan checkpoint. `run_rebuttal`
   takes a required `spec_id` for it, and `run_rebut` passes its own.
4. **The table.** Add one `_Family` row for the line to `FAMILIES` in
   `saffron/events.py`, citing `phases/rebut.py:run_rebuttal`. Move the count in
   `tests/test_events.py:1397-1398` from 72 to 73. Name `SA-0341` on the last
   line of the docstring at `tests/test_events.py:1387-1396`. That docstring is
   at the `prose` gate's limit of ten lines, so a new line fails it.

## Out of scope

- A verdict that is not the schema (`saffron/phases/rebut.py:384-387`). It stays
  unre-prompted.
- Rebuilding `reprompt_error` from `rebuttal.json` in `saffron/task.py`'s
  `_rebuild_rebut_result` (`saffron/task.py:1142-1169`). No reader of the
  rebuilt result reads it, so it stays `None` there.
- Recording a second unreadable answer as unread in the ledger. `SA-0340`
  owns that.
- Refusing a re-prompt the pool could start, as REVIEW refuses one given less
  than its first turn spent (`saffron/phases/review.py:258-263`). Only the
  pool decides whether this re-prompt starts.

## Notes for the agent

**`SA-0340`, the parent.** It edits `sustained_blockers` and `unkept_fixes`
(`saffron/phases/rebut.py:607-665`) and the ledger write near
`saffron/cell/session.py:3727`. This spec assumes it leaves alone
`saffron/phases/rebut.py:81-108`, `:137-164`, `:221-284` and `:722-734`. It
also assumes `saffron/cell/session.py:222-229` and `:2903-2908` stay as they
are. Lines cited here were read before it, so find each by its text.

**Edit or new.** The re-prompt, the field and the line are new code. So
criteria 1, 2, 4 and 5 declare no mutant, and `witness` reports an honest
`skip` on each. Criterion 3 is partly an edit. Its failed fix turn and failed
first extraction are existing branches (`saffron/phases/rebut.py:248-253`,
`:266-270`). Their return text occurs twice, so a `find` cannot match once,
and criterion 3 declares no mutant either. Its witness still fails at base, on
the new `spec_id` argument and on the failed re-prompt case.

**Comments that turn false.** Replace the comment at
`saffron/phases/rebut.py:274-276`. The docstring at `:233-238` says two turns.
The comment at `:725` says these two turns, and so does
`saffron/cell/session.py:2907`. The comment at `saffron/cell/session.py:224` says
only a verdict meets the pool's refusal, which the re-prompt now meets too.
Keep each comment at two lines or fewer.

**The witnesses.** Use plain `def`s, never a parametrised test.

- In `tests/test_rebut.py`, call `rebut.run_rebuttal` directly. Script each call
  with its own session id and cost. Put each call and each emitted event on one
  list, so the line's place among the calls is asserted. Compute each expected
  error with `rebut._validate(rebut._Rebuttals, value)[1]`. A value whose one
  argument is empty is a rejected shape, as
  `test_an_empty_argument_is_not_an_argument` shows.
- In `tests/test_session.py`, drive a cell through `_through_rebut`, `_rebuttable`
  and `_drive`, with a `budget_usd` far above the spend. Criterion 4's three
  cells pass `rebut_commits=0`, since a moved HEAD opens the verdict pool and
  clears the cut (`saffron/cell/session.py:208-212`). Find the re-prompt in
  `cell.turns` as a prompt that ends with `EXTRACT_PROMPT` and is not equal to it.
  With a $6.00 fix turn and a $2.50 extraction, the re-prompt's cap is $5.50. An
  $8.00 extraction leaves nothing. In that refused cell, assert the re-prompt's
  line comes before the REBUT line naming the refusal. `_rebuttal_log` reads the
  real `events.jsonl`.

**Existing tests this changes.** `_agent` in `tests/test_rebut.py` scripts a bare
string as a turn with no structured output. So a test whose extraction is
unreadable now feeds its next scripted turn to the re-prompt. The stub in
`tests/test_session.py` hands a re-prompt its next scripted turn, or a default
one (`tests/test_session.py:1624`). `_agent` has no default and raises `StopIteration` when its script runs out.
So the rule covers any test whose extraction is unreadable, whatever is
scripted after it, `SA-0340`'s included. Give each such test a second
unreadable answer right after its first. A `tests/test_session.py` test that
reads its expected error from `rebuttal.json` needs no edit. Make no other
edit, save the one count named below. A full suite run over a prototype of this change, without
`SA-0340`'s code, failed four tests, all in `tests/test_rebut.py`.

- `test_a_rebuttal_that_neither_moved_nor_argued_ends_rebuttal_unjudged`, its
  `outside_schema` case.
- `test_a_commit_stands_even_when_the_rebuttal_was_not_recorded`.
- `test_an_empty_argument_is_not_an_argument`.
- `test_a_rebuttal_turn_without_a_valid_structured_output_is_not_the_schema`.
  Its `len(record) == 2` becomes `len(record) == 3`, because that count is the
  old rule this spec reverses.

**Every new test fails with the source reverted.** On the prototype, all five
witnesses failed with `saffron/` reverted. The moved count in
`tests/test_events.py` failed there too. The three `tests/test_rebut.py` witnesses fail there on the
new `spec_id` argument first. Criteria 1, 2 and 3 each also hold a case that
needs the re-prompt itself.

**Size.** The prototype measured 212 changed tokens by `size_gate`, against the
`bug` ceiling of 1300, and 889 more under the test paths. `estimated_lines` is
the first figure over four.
