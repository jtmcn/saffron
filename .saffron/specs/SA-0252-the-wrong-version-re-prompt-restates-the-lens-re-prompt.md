---
id: SA-0252
title: The wrong-version re-prompt restates the lens re-prompt line for line, so a change to one rule must be made twice
type: refactor
priority: 2
depends_on: [SA-0247]
estimated_lines: 265
estimate_measured: true
touches:
  - saffron/phases/review.py
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
  - harness/**
  - records/**
  - hooks/**
  - saffron/agents/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/events.py
  - saffron/end_review.py
  - saffron/spec_review.py
  - saffron/phases/implement.py
  - saffron/phases/rebut.py
  - tests/test_events.py
  - tests/test_session.py
  - tests/test_end_review.py
budget_usd: 46
max_attempts: 3
max_turns: 180
risk: standard
acceptance:
  - claim: >-
      `run_lens` and `run_wrong_versions` each hand every first answer that
      is not the schema to one helper, `_parse_or_reprompt` in
      `saffron/phases/review.py`. Through either caller, the helper
      re-prompts a first turn that left exactly what it spent. It refuses
      one that left less, and one with no session id. Each refusal files
      `not the schema: ` and the error, charged the first turn alone. Only
      the lens announces a re-prompt, and only one that fires. The witness
      drives all three first turns through each caller and counts six
      helper calls.
    witness: tests/test_review.py::test_both_callers_refuse_a_reprompt_on_the_one_rule
    wrong_versions:
      - The re-prompt is refused when the ceiling left equals what the first turn spent.
      - The re-prompt fires whenever any of the ceiling is left.
      - A first turn with no session id is re-prompted anyway.
      - "`run_wrong_versions` keeps its own re-prompt and never calls the helper."
      - "`run_lens` keeps its own re-prompt and never calls the helper."
      - "`run_lens` refuses a re-prompt itself and calls the helper only when one fires."
      - A refusal's error drops the colon after `not the schema`.
      - The lens announces a refused re-prompt as well as one that fires.
      - The helper announces every re-prompt itself, so a wrong-version re-prompt emits a line too.
  - claim: >-
      The re-prompt each caller makes resumes the failed turn's session. It
      passes that turn's cost as `last_cost_usd` and the caller's own
      `emit`. Its prompt is the error, two newlines, then
      `EXTRACTION_PROMPT`. Its options equal `implement.agent_options` built
      from the first turn's system prompt and turn bound, the budget that
      turn left, and `REVIEW_TOOLS`. The lens alone emits a `PhaseStart`
      line for it, between the two turns, naming the lens and the error.
      The witness drives one re-prompt through each caller on a turn bound
      of 7.
    witness: tests/test_review.py::test_both_callers_build_one_reprompt_turn
    wrong_versions:
      - The re-prompt is given the whole ceiling, not what the first turn left.
      - The re-prompt holds the implementer's tools.
      - The re-prompt's turn bound is a constant rather than the caller's.
      - The re-prompt starts a fresh session instead of resuming the failed one.
      - The re-prompt sends `EXTRACTION_PROMPT` alone, without the error.
      - The re-prompt puts the error after `EXTRACTION_PROMPT`.
      - The re-prompt joins the error and `EXTRACTION_PROMPT` with one newline.
      - The re-prompt passes no `last_cost_usd`.
      - The re-prompt is handed an `emit` that drops every event.
      - The re-prompt is given an empty system prompt.
      - The lens no longer announces its re-prompt.
      - The lens announces its re-prompt after the second turn returns.
      - The lens's announcement leaves out the lens's name.
  - claim: >-
      Once a re-prompt fires, each caller files the same three outcomes. A
      second turn that raises `AgentFailed` files `re-prompted once, then `
      and its failure. It is charged both turns, or the first alone when the
      failure carries no turn. A second answer that is not the schema files
      `not the schema, even after a re-prompt: ` and that answer's own error,
      charged both turns. The witness drives all three through each caller.
    witness: tests/test_review.py::test_both_callers_spell_each_reprompt_error_alike
    wrong_versions:
      - A second turn that raises is charged the first turn alone.
      - A second turn that raises with no turn attached raises `AttributeError`.
      - A second bad answer's error carries the first answer's cause.
      - A second bad answer is filed with the first answer's prefix.
      - A second bad answer is charged the second turn alone.
      - "`run_wrong_versions` files a raising second turn with the second-bad-answer prefix."
      - "`run_lens` rewrites the second-bad-answer prefix in its own words."
  - claim: >-
      A lens whose re-prompt answers the schema still files that answer's
      findings, charged both turns, in two agent calls.
    witness: tests/test_review.py::test_a_malformed_first_output_is_reprompted_once_and_recovers
    preserves: true
  - claim: >-
      A lens whose first answer is the schema is still asked once.
    witness: tests/test_review.py::test_a_well_formed_first_output_never_reprompts
    preserves: true
  - claim: >-
      A wrong-version first answer that is not the schema is still
      re-prompted and recovered, for a missing block, JSON that does not
      parse, a schema refusal and a wrong answer count.
    witness: tests/test_review.py::test_a_wrong_version_answer_that_is_not_the_schema_is_reprompted_once_in_its_own_session
    preserves: true
  - claim: >-
      A wrong-version re-prompt still fires once, and only where a lens
      re-prompt would, with the errors and costs it files today.
    witness: tests/test_review.py::test_a_wrong_version_reprompt_fires_once_and_only_where_a_lens_would
    preserves: true
---

## Context

Backlog item **b-708c8a**, found reviewing #675 in the spec loop's run 28.
It cites `DESIGN.md` §5.5. The wrong-version re-prompt is §5.4's, at
`DESIGN.md:1088-1089`. Every line number below was read at `958db033`. Your
base also carries `SA-0233` and `SA-0247`. In `saffron/phases/review.py`
they edit `describe_wrong_versions` and `apply_probe_verdict` (`:704`,
`:828`), below every line cited here. Both add tests to
`tests/test_review.py`, so its line numbers can drift. Follow the test
names given beside each number.

**The lens re-prompt.** `run_lens` (`saffron/phases/review.py:234`) parses
its answer and catches `ValueError` and `ValidationError` (`:269-270`). It
refuses a re-prompt when the ceiling left is less than the failed turn
spent, or the turn carries no session id (`:271-277`). Otherwise it emits a
`PhaseStart` naming the lens and the error (`:278-286`). It builds the
second turn's options on the budget left with `REVIEW_TOOLS` (`:287-292`).
It resumes the failed session with the error then `EXTRACTION_PROMPT`, and
passes `last_cost_usd` (`:293-301`). A second turn that raises files
`re-prompted once, then ` and the failure, charged both turns (`:302-308`).
A second bad answer files `not the schema, even after a re-prompt: `
(`:310-317`).

**The wrong-version re-prompt.** `SA-0202` gave `run_wrong_versions`
(`saffron/phases/review.py:595`) the same re-prompt, copied. The parse and
catch are at `:646-648`. The refusal rule is at `:649-658`, the options at
`:659-664`, the second turn at `:665-674`. The three error strings are at
`:655`, `:680` and `:692`. Each outcome goes through
`_unresolved_wrong_versions` or `_resolved_wrong_versions` (`:544`,
`:559`). Only the announcement is missing, by design (`SA-0202`'s Out of
scope). The docstring says it follows `run_lens`'s own rule (`:613-618`).

**One row names where the lens line fires.** `events.FAMILIES` cites
`phases/review.py:run_lens` for the `REVIEW: not the schema` line
(`saffron/events.py:957`). `tests/test_events.py:1208` checks the symbol
exists in that file.

## Problem

The two copies share the refusal rule, the second turn's options, its
prompt and three error strings. A change to one must be made twice, and no
test fails when one copy is missed.

1. **One helper.** Add `_parse_or_reprompt` to `saffron/phases/review.py`.
   It takes the first turn's result, the caller's parse step as a callable,
   and the system prompt, turn bound, ceiling, agent and `emit`. It owns
   the parse of both answers, the refusal rule, the second turn's options,
   its prompt and its call, and all three error strings. It returns what
   the caller needs to file: the parsed answer or the error, and the cost
   of every turn it took.
2. **The lens announcement stays in `run_lens`.** The helper takes an
   optional callback it calls with the error, before the second turn.
   `run_lens` passes one that emits its `PhaseStart`, built in `run_lens`'s
   own body as today. `run_wrong_versions` passes none.
3. **Both callers use it.** `run_lens` maps the helper's result to a
   `LensReview`. `run_wrong_versions` maps it to its two entry builders.
   Neither keeps a refusal check, a second agent call or an error string of
   its own. A first turn that raises `AgentFailed` stays in each caller, as
   today, and is never handed to the helper.
4. **Behaviour is unchanged.** Every error string, cost and agent call
   either caller makes today, it makes after.

## Out of scope

- **Other re-prompts.** `run_criterion_probe` has none
  (`saffron/phases/review.py:412`). The PLAN and SCOPE re-prompts live in
  `saffron/cell/session.py` (`:600`, `:633`). `spec_review.py` has its own
  re-ask (`saffron/spec_review.py:448`). None moves.
- **The first turn.** The first agent call, its options and its
  `AgentFailed` handling stay in each caller.
- **`describe_wrong_versions` and `apply_probe_verdict`.** `SA-0233` and
  `SA-0247` edit them. Leave both functions, and their tests, as your base
  has them.
- **The events table.** `saffron/events.py` is forbidden. Its row stays
  true while `run_lens` builds the `PhaseStart`.

## Notes for the agent

**New or edit.** The helper is new code, and both callers' bodies are
rewritten around it. So no criterion declares a mutant, and `witness`
reports `skip`. Criteria 1 to 3 each name a new witness. Criteria 4 to 7 are
`preserves` and name tests that pass now. Each wrong version listed under a
criterion is one its witness must fail. REVIEW turns each into an edit and
runs the witness. Do not run them yourself.

**Why each new witness spies on the helper.** Every behaviour these
witnesses check is true at base. A test of it alone passes with the source
reverted, and `revert` blocks that. So each witness wraps
`review._parse_or_reprompt` with `monkeypatch.setattr` in a spy that counts
calls and delegates to the real helper. At base the attribute is missing,
and the test fails. Read it at call time from the `review` module, never
imported at module scope, or the reverted run is a collection error.

**Keep every existing test's name and body.** The `census` gate reads a
renamed test as a removed one. Add the three new tests after
`test_a_wrong_version_reprompt_fires_once_and_only_where_a_lens_would`
(`tests/test_review.py:1540`), before
`test_a_wrong_versions_survivor_names_the_version_it_came_from` (`:1630`).
They use `_probe_agent` (`:1046`) and `_wv_turn` (`:1423`), both defined
above that point. A small helper per caller keeps each test short. One calls
`review.run_lens` with lens `correctness` and system prompt `s`. The other
calls `review.run_wrong_versions` over N criteria with one version each.
Both use a ceiling of 2.0 and spec id `SY-1`.

**Criterion 1's witness.** For the lens, three `run_lens` calls share one
recording list and one event list. The first turns are plain text with no
block: at 1.0 with session `s-a`, then at 1.5 with `s-b`, then at 0.3 with
session `None`. The first is followed by a good answer at 0.2. Assert the
errors `None` and twice
`not the schema: no <output> block in the response`. Assert costs 1.2, 1.5
and 0.3, `resume` on the second call alone, and exactly one event. Script
the same through `run_wrong_versions` over three criteria. Assert the same
errors, costs and `resume` pattern, and no event. The spy counts six calls.

**Criterion 2's witness.** Loop over both callers with a turn bound of 7.
Script a first turn of plain text at 0.3 with session `s-1`, then a good
answer at 0.2. Pass the same list as the agent's recording list and as
`emit`, so calls and events interleave in order. Assert two calls. The
second call's options equal `implement.agent_options` with the first call's
system prompt, `max_turns=7`, `budget_usd=1.7` and `REVIEW_TOOLS`. Compare
`max_budget_usd` with `pytest.approx`. Its prompt equals the error, two
newlines and `EXTRACTION_PROMPT`, exactly. Its `resume` is `s-1`, its
`last_cost_usd` is 0.3, and its `emit` is the caller's `emit`. For the lens,
the list's item types are call, `PhaseStart`, call. The event's spec id,
phase, label and detail are `SY-1`, `REVIEW`, `REVIEW` and
`correctness: not the schema, re-prompting once — ` then the error. For
`run_wrong_versions` there is no event. The spy counts two calls.

**Criterion 3's witness.** Three cases per caller, each a first turn at 0.3.

1. Plain text, then `implement.AgentFailed("retry cut off", ...)` carrying
   a turn at 0.25.
2. Plain text, then `implement.AgentFailed("retry gone")` with no turn.
3. A block whose JSON does not parse, then plain text at 0.2. The two
   causes differ, so the error shows whose it carries.

Drive the lens with three `run_lens` calls and `run_wrong_versions` over
three criteria. Each caller's errors are exactly
`re-prompted once, then retry cut off`,
`re-prompted once, then retry gone` and
`not the schema, even after a re-prompt: no <output> block in the response`.
Its costs are 0.55, 0.3 and 0.5. The spy counts six calls.

**Measured.** On 2026-10-07 a prototype of this change passed all 54 tests
in `tests/test_review.py`, three of them new. `tests/test_session.py`,
`tests/test_end_review.py` and `tests/test_events.py` passed too. With
`saffron/phases/review.py` reverted to `958db033`, all three new witnesses
failed. Each of the 29 wrong versions above was applied to the prototype,
and its own criterion's witness failed on every one. The prototype used
`functools.partial` for the wrong-version parse step, because a lambda in
the loop trips ruff's `B023`.

**What the new witnesses leave out.** They drive no first turn that raises,
because that stays in each caller. Criterion 7's witness drives it for
`run_wrong_versions`, and `test_a_lens_whose_session_failed_still_charges_what_it_spent`
(`tests/test_review.py:202`) does for a lens. The kinds of malformed answer
are not a set these claims cover. Criterion 6 drives four for
`run_wrong_versions`, and criterion 3 drives two for a lens.

**One docstring goes stale.** `run_wrong_versions`'s says the re-prompt
follows `run_lens`'s own rule (`saffron/phases/review.py:613-618`). Make it
name the helper instead.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. The `PhaseStart` detail string is code and keeps its em dash.

**Size.** Neither file is in `elevate_on`, so `size` stops nothing here. The
prototype, counted by `size_gate`, came to 1061 tokens against the
`refactor` ceiling of 4200. `estimated_lines` is that over four, with no
overrun added.
