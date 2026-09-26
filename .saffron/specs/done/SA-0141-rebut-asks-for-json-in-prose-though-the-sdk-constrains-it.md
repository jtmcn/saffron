---
id: SA-0141
title: REBUT asks for its rebuttal and its verdicts as JSON in prose, though the pinned SDK can constrain both turns to a schema
type: feature
priority: 2
depends_on: [SA-0133, SA-0138, SA-0139, SA-0140]
touches:
  - images/agent_runner.py
  - saffron/phases/implement.py
  - saffron/phases/rebut.py
  - saffron/agents/prompts/turns/rebut-extract.md
  - saffron/agents/prompts/turns/verdict.md
  - saffron/agents/prompts/rebut-verdict.md
  - tests/test_agent_runner.py
  - tests/test_implement.py
  - tests/test_rebut.py
  - tests/test_session.py
  - tests/test_events.py
  - tests/test_context.py
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
  - images/cell-base.python.Dockerfile
  - images/proxy.Dockerfile
  - saffron/agents/prompts/turns/extraction.md
  - saffron/agents/prompts/turns/plan.md
  - saffron/agents/prompts/turns/review.md
  - saffron/agents/prompts/turns/notes.md
  - saffron/agents/prompts/turns/criterion-probe.md
  - saffron/agents/artifacts.py
  - saffron/agents/context.py
  - saffron/phases/review.py
  - saffron/phases/package.py
  - saffron/cell/**
  - saffron/events.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_artifacts.py
  - tests/test_review.py
budget_usd: 22
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      The runner's `result` event carries the result message's
      `structured_output` under the key `structured_output`, whole and
      unclipped. The witness drives three result messages. One holds a value
      with a nested string of 500 characters. One holds `None`, and one has
      no such attribute. The key is present in all three events. Its value
      equals the message's value in the first, and is `None` in the other
      two. The first event, written as one
      stdout line and fed to `implement.run_agent` through an `exec_stream`
      double, gives an `AttemptResult` whose `structured_output` equals the
      message's value.
    witness: tests/test_agent_runner.py::test_the_result_event_carries_structured_output_whole
  - claim: >-
      `run_agent` reads `structured_output` from the `result` event only. The
      witness drives three streams. In the first the result event carries a
      value, and the `AttemptResult` carries it. In the second a `tool_use`
      event named `StructuredOutput` carries a value in its `input` and the
      result event carries `null`, and the `AttemptResult` carries `None`. In
      the third a `system` event carrying a top-level `structured_output`
      value comes before a result event with no such key, and the
      `AttemptResult` carries `None`. The second and third turns still
      return, since their subtype is `success`.
    witness: tests/test_implement.py::test_structured_output_is_read_from_the_result_event_only
  - claim: >-
      REBUT's rebuttal extraction turn is sent `output_format` equal to
      `{"type": "json_schema", "schema": rebut._Rebuttals.model_json_schema()}`,
      and every other option it is sent equals the rebuttal turn's. The
      rebuttal turn before it is sent no `output_format`. The rebuttals REBUT
      records are the extraction turn's `structured_output`. The witness's
      extraction turn carries text holding a valid `<output>` block that
      argues finding 1, and a `structured_output` that marks it `fixed`. The
      agent is called three times, and the recorded rebuttals are exactly one,
      marked `fixed`.
    witness: tests/test_rebut.py::test_the_rebuttal_extraction_turn_asks_for_the_schema_and_records_its_structured_output
  - claim: >-
      Each verdict session is sent `output_format` equal to
      `{"type": "json_schema", "schema": rebut._Verdicts.model_json_schema()}`,
      beside the options `implement.agent_options` builds for it with
      `review.REVIEW_TOOLS`. Its verdicts are its `structured_output`. The
      witness drives one blocker per lens in `review.LENSES`, so three verdict
      sessions. Each one's text holds a valid `<output>` block confirming its
      finding, and its `structured_output` withdraws it. The agent is called
      for exactly three verdict sessions, and the recorded verdicts are three,
      each `withdrawn`.
    witness: tests/test_rebut.py::test_each_verdict_session_asks_for_the_schema_and_records_its_structured_output
  - claim: >-
      A rebuttal extraction turn whose `structured_output` is not a value
      `_Rebuttals` accepts records no rebuttal, and its error starts
      `not the schema`. The witness makes three `run_rebut` calls, one turn
      each, with subtype `success`, no `is_error`, and text holding a valid
      `<output>` block that argues finding 1. Their values are `None`, an
      entry whose `action` is `"maybe"`, and a valid payload serialised to a
      JSON string. HEAD does not move in any of them. Each call makes exactly
      two agent calls, records no rebuttal, and ends `REBUTTING` with that
      error in its `why`.
    witness: tests/test_rebut.py::test_a_rebuttal_turn_without_a_valid_structured_output_is_not_the_schema
  - claim: >-
      A verdict session whose `structured_output` is not a value `_Verdicts`
      accepts has no verdict, and its error starts `not the schema`. The
      witness makes three `run_rebut` calls, each with one blocker, HEAD
      moved, and a valid structured rebuttal marking it `fixed`. Each verdict
      session has subtype `success`, no `is_error`, and text holding a valid
      `<output>` block confirming the finding. Their values are `None`, an
      entry whose `verdict` is `"maybe"`, and a valid payload serialised to a
      JSON string. Each call makes exactly three agent calls. Its one lens
      records no verdict and an error starting `not the schema`, and REBUT
      ends `REBUTTING`.
    witness: tests/test_rebut.py::test_a_verdict_session_without_a_valid_structured_output_is_not_the_schema
  - claim: >-
      Neither REBUT turn asks for an `<output>` block. The witness reads
      `rebut.EXTRACT_PROMPT`, `rebut.VERDICT_TURN_PROMPT` and the
      `rebut-verdict.md` template. None holds `<output>`, the phrase
      `output block` in any case, or `artifacts.EXTRACTION_PROMPT`.
      `rebut.EXTRACT_PROMPT` holds `Do not change files.` and
      `Do not run commands.`, each spelled on one line.
    witness: tests/test_context.py::test_rebuts_prompts_ask_for_no_output_block
  - claim: >-
      A lens that verdicts fewer blockers than it was asked about has still
      not withdrawn the rest.
    witness: tests/test_rebut.py::test_a_lens_that_leaves_a_blocker_unverdicted_has_not_withdrawn_it
    preserves: true
  - claim: >-
      A rebuttal whose `argument` is empty is still not an argument.
    witness: tests/test_rebut.py::test_an_empty_argument_is_not_an_argument
    preserves: true
---

## Context

Backlog item **b-4e0868**, first slice. Items **42** and **60** are the two
measured losses behind it. `SA-0040` lost a rebuttal to
`Illegal trailing comma` after a $2.59 turn. `SA-0053` ended an attempt at
$3.61 on a lens report missing a field.

The record `docs/evidence/2026-09-23-structured-output-spike.md` measured
`claude-agent-sdk==0.2.142`, the version the cell image pins. Every claim
below about `output_format` comes from it.

- `ClaudeAgentOptions.output_format` set to
  `{"type": "json_schema", "schema": ...}` holds on a resumed session. It
  also holds under the production option shape, with `tools`,
  `allowed_tools` and `permission_mode="dontAsk"`, and no denial.
- `ResultMessage.structured_output` carries the parsed value.
- A schema no value satisfies ends `subtype: success`, `is_error: false`,
  `structured_output: null`. Only the null says the value never came.
- A schema whose top level is `anyOf` is refused with an API 400, raised
  out of `query()`. `_Rebuttals` and `_Verdicts` are objects, and both were
  accepted as `model_json_schema()` generates them.
- The CLI implements the option as a tool named `StructuredOutput`.

The spike ran on the host, not in a cell. Its SDK and bundled CLI are the
wheel a cell installs.

Four queued specs edit files this one edits, and all four are its parents.
`SA-0140` edits the runner's `_run`, `run_verdict` and `run_agent`.
`SA-0133` and `SA-0139` edit `implement.py` too. `SA-0138` edits `rebut.py`'s `_blocker_line`
and adds session tests that script REBUT. The line numbers below were read
at `23c39a62` and move before a cell runs.

**What the code does now.**

- The runner copies the request's options into a dict
  (`images/agent_runner.py:162`). It hands that dict to the SDK unchanged, as
  `ClaudeAgentOptions(**options)` (`images/agent_runner.py:168`). So a
  host option named `output_format` reaches the SDK with no runner change.
- The runner's `result` event carries `subtype`, `num_turns`,
  `total_cost_usd`, `session_id`, `terminal_reason`, `is_error` and four
  token counts (`images/agent_runner.py:116-127`). It carries no
  `structured_output`.
- `_clip` cuts every string over 200 characters
  (`images/agent_runner.py:62-69`), and a `tool_use` event's `input` goes
  through it (`:84-90`). So the `StructuredOutput` tool call reaches the
  host clipped. The `result` event is the one route that can carry the
  whole value.
- `run_agent` keeps the `result` event whole with `result.update(event)`
  (`saffron/phases/implement.py:251-252`), before it emits the event. It
  builds the `AttemptResult` from it at `:341-356`. `AttemptResult` has no
  field for a structured value (`:73-92`).
- A turn fails only on `is_error`, a subtype other than `success`, a kill or
  a non-zero exit (`saffron/phases/implement.py:340`). Nothing there reads a
  structured value, so a turn whose value is null returns clean.
- `run_rebuttal` sends its extraction turn the same `options` as the
  rebuttal turn (`saffron/phases/rebut.py:165-170`, `:182-189`). It reads
  `_Rebuttals` from the last `<output>` block in the turn's text
  (`:199-201`). A `ValueError` or `ValidationError` there becomes
  `error=f"not the schema: {exc}"` (`:202-208`).
- `run_verdict` builds its options with `implement.agent_options` and
  `tools=review.REVIEW_TOOLS` (`saffron/phases/rebut.py:276-281`). It reads
  `_Verdicts` from the text the same way, with the same error (`:289-294`).
  It then refuses a verdict set whose finding numbers differ from the
  numbers it asked about, at `if given != asked:` (`:297`).
- `rebut-extract.md` and `verdict.md` each end in the `{extraction}` slot
  (`saffron/agents/prompts/turns/rebut-extract.md:9`,
  `saffron/agents/prompts/turns/verdict.md:4`). `context.turn_prompt`
  fills it with `extraction.md` at load, by splitting on the slot
  (`saffron/agents/context.py:156-171`). `extraction.md` asks for a single
  `<output>` block and forbids changing files and running commands
  (`saffron/agents/prompts/turns/extraction.md:1-2`).
- The verdict system prompt asks for a single `<output>` block in its
  "What to emit" section (`saffron/agents/prompts/rebut-verdict.md:47-61`).
- `tests/test_context.py:444-448` asserts that `verdict` and `rebut-extract`
  both carry the extraction rules. `tests/test_agent_runner.py:83-111`
  asserts the result event's exact keys.

## Problem

REBUT's two structured turns ask for JSON in prose and find it with a
regex. A trailing comma or a missing field then costs the whole phase. The
SDK the cell pins can constrain both turns to the schema the host already
validates against. Saffron uses none of it, and the runner drops the value
the SDK returns.

## Out of scope

**The other structured turns.** These are later slices of b-4e0868.
REVIEW's lens reports and the criterion probe's answer are one. The plan
checkpoint is another. Its plan-or-scope union is an `anyOf` at the top,
which the API refuses, so it needs a wrapper object first. The notes turn is
free text and needs no schema. `extraction.md` and every prompt that fills
its slot stay as they are.

**A re-prompt.** A null or invalid value takes REBUT's existing
`not the schema` path. Whether a failed shape buys a second turn is still
item 42's open question.

**A fallback to the `<output>` block.** A turn sent `output_format` is read
from `structured_output` only. Criteria 3 to 6 witness it.

**`DESIGN.md` §5.3 and `CONTEXT.md`'s Extraction turn.** Both are
`protected`, so the operator edited them by hand in this spec's pull
request, under backlog item **b-e51967**. §5.3 now records what the pinned
SDK measured. The glossary entry now says REBUT's turns return a
schema-constrained value. That entry sits in the glossary's section 2, which
IMPLEMENT and REVIEW both inject (`saffron/agents/context.py:30-31`). So both
REBUT sessions read the new rule. Both files stay forbidden.

**What the schema says to the model.** The schema is sent as
`model_json_schema()` generates it, docstrings included as `description`.
The spike did not measure whether they change an answer. That is a ceiling
this slice accepts.

**A turn cut before it calls the tool.** One spike run under `max_turns=1`
still delivered. Whether a turn ceiling can cut the tool call is not
measured. If it does, the value is null and criterion 5 or 6 names the path.

**A large result event in the log.** `EventLog.append` bounds an event whose
JSON runs past `BOUND_CHARS`, 8192 characters (`saffron/events.py:61`,
`:418-426`). A result event carrying a large value is then stored as a
bounded line in `events.jsonl`. That line loses the turn's cost and token
counts, and `saffron watch` loses its summary. The host reads the event
before it emits it (`saffron/phases/implement.py:251-260`). So the value
the host validates is whole. That is a ceiling this slice accepts.

**The schema beside a system prompt file.** The spike sent string system
prompts. After `SA-0140`, the runner hands the SDK a file reference. Whether
`output_format` holds beside it is not measured. The operator's first live
REBUT settles it.

## Notes for the agent

**New code, so witnesses and no mutants.** The event key, the
`AttemptResult` field and the option are all new. No text exists at base for
a mutant to name. Criteria 8 and 9 are `preserves` and name tests that
exist.

**The runner.** Add `structured_output` to the `result` branch's dict in
`events`, read with a `None` default, and never through `_clip`. Update the
exact-keys assertion in
`test_the_result_event_carries_what_the_supervisor_bounds_on` to expect
`None`. Leave `_run` alone. `SA-0140` rewrites it.

**`implement.py`.** Give `AttemptResult` a `structured_output` field
defaulting to `None`. Fill it from the result event in `run_agent`'s
success path. Nothing else in `run_agent` changes. `SA-0133` and `SA-0140`
edit the same function, and this spec is cut after both land.

**`rebut.py`.** Send the extraction call `options` merged with
`output_format`, as a new dict. Never mutate the `options` the rebuttal turn
was given, because a test double records each call's dict by reference.
Build the verdict options the same way. Validate the value with
`_Rebuttals.model_validate` and `_Verdicts.model_validate`. Never parse a
string value as JSON first. A `None` value is `not the schema` too, with a
message saying the turn returned no structured output. Drop the
`parse_output_block` import and `json` if nothing else uses them. `SA-0140`
also edits `run_verdict`, to wrap the `emit` it passes. Keep that wrapper.

**The prompts.** Take the `{extraction}` slot out of `rebut-extract.md` and
`verdict.md`. In its place, `rebut-extract.md` asks for the answer in the
required structured format. It spells `Do not change files.` and
`Do not run commands.` each on one line. `extraction.md` wraps the first
across a line break, so a copy of its text fails criterion 7. The rebuttal
turn resumes a session holding `Write`, `Edit` and `Bash`. In
`rebut-verdict.md`, rewrite "What to emit" the same way. Keep these:

- its field list and its one-entry-per-finding rule.
- the sentence about the disagreements table, which
  `tests/test_context.py:387-388` reads in both files.
- the clause saying the diff under "The diff, after the rebuttal" below is
  the change as it now stands
  (`saffron/agents/prompts/rebut-verdict.md:49-51`).
  `tests/test_rebut.py:505-509` pins it, guarding `SA-0091`'s fix.
- the `## The rebuttal` heading, which `tests/test_session.py` uses to find
  the verdict prompt.

**Existing tests the change breaks, which you update.** Each feeds REBUT's
payload as an `<output>` block in `text`. Move it onto `structured_output`.

- `tests/test_rebut.py`: `_turn`, `_rebuttals` and `_verdicts`. The helper
  change carries every test that uses them.
- `tests/test_session.py`: its `_turn` helper, `_CLAIMED_FIX`'s use, and
  each REBUT turn scripted with a `rebuttals` or `verdicts` payload. That
  includes tests the parents add. A test that scripts REBUT as runner lines
  through `exec_stream` moves the payload onto its result line's
  `structured_output`. `SA-0133` adds a keyword to `_drive` whose
  `exec_stream` double builds each `result` line from five named fields and
  the cost. Make that double copy the turn's `structured_output` onto the
  line too. Without it, a migrated turn reaches `run_agent` as `None`, and
  nothing fails.
- `tests/test_events.py`: the two REBUT payloads handed to
  `_scripted_agent`, around line 2396.
- `tests/test_context.py`: drop `verdict` and `rebut-extract` from the
  parametrised list at line 445.
- `tests/test_agent_runner.py`: the exact-keys assertion above, and
  `SA-0140`'s `test_a_verdict_session_that_never_started_ends_rebut_gate_error`.
  In that test, the stub result message of the lens that returns a valid
  verdict set carries its payload as `structured_output`. So does the
  scripted rebuttal extraction turn. Left in text, that lens reads
  `not the schema`, and the test stops killing SA-0140's wrong version
  "`GATE_ERROR` that needs every lens to fail".

**The completion check.** After the change, no test places a `rebuttals` or
`verdicts` payload in text, whether through `_block`, `_CLAIMED_FIX` or a
literal `<output>`. A payload left there often fails nothing. Run this from
the repo root:

```
uv run python -c "import re,pathlib; pat=re.compile(r'_block\(\s*(\{\s*)?\"(rebuttals|verdicts)\"|_block\(_CLAIMED_FIX\)|<output>[^<]*(rebuttals|verdicts)'); print(*[f'{p}:{p.read_text().count(chr(10),0,m.start())+1}' for p in sorted(pathlib.Path('tests').rglob('*.py')) for m in pat.finditer(p.read_text())], sep=chr(10))"
```

At base it prints 27 lines: 23 in `tests/test_session.py`, 2 in
`tests/test_rebut.py` and 2 in `tests/test_events.py`. After the change,
every line it prints falls inside the witnesses of criteria 3 to 6, or in a
helper only they call. Those place a conflicting block in text on purpose.

The grep reads text, so it misses a payload built from a variable or a
helper, which a parent's test can use. So also list every dict key
spelled as a literal:

```
git grep -n -E "[\"'](rebuttals|verdicts)[\"']\s*:" -- tests
```

Read each hit, and confirm its payload reaches `structured_output` and not
`text`.

**Witness 1.** Build each message as a `SimpleNamespace`, as the tests
beside it do. Feed the first event to `run_agent` with a stream double that
calls `on_line` with `json.dumps(event)`. `_stream` in
`tests/test_implement.py` is one to copy. Assert the key with `in` before
reading it, since `.get` passes a runner that omits it.

**Nothing new at module scope** in `tests/test_agent_runner.py`,
`tests/test_implement.py`, `tests/test_rebut.py` or `tests/test_context.py`.
That covers an import of a name the change adds, a module-level
`AttemptResult(structured_output=...)`, and a constant built from one. Each
turns the reverted run into a collection error, which `revert` reads as
`skip` (`saffron/gates/core/revert.py:276-296`). Build them inside the test
or its helpers.

**Witnesses 3 to 6.** Drive `run_rebut` through `_run`, and read each
call's options off `record`. For witness 4, compare each verdict call's
options, minus `output_format`, to `implement.agent_options` built with that
call's own `system_prompt`, `max_turns=20`, `budget_usd=2.0` and
`review.REVIEW_TOOLS`. Witness 6 keeps `_run`'s default `moved=True`. With
HEAD unmoved and a `fixed` rebuttal, `run_rebut` returns before any verdict
session (`saffron/phases/rebut.py:514-518`). It then ends `REBUTTING` whatever
the verdict code does.

**Measured against a prototype on 2026-09-23.** The operator's delegate
built a minimal change in a scratch worktree. It wrote witnesses 3 to 6 as
their criteria describe them. With `rebut.py` and `implement.py` reverted, all
four failed. Each wrong version below then ran against them:

| Wrong version | Killed by |
|---|---|
| a null value read as a cue to parse the block | 5, 6 |
| a block preferred over a value beside it | 3, 4, 5, 6 |
| a string value parsed as JSON | 5, 6 |
| `subtype == "success"` read as the value arriving | 5, 6 |
| `rebut.py` as at base | 3, 4, 5, 6 |

A variant of witness 6 with HEAD unmoved passed every one of them. That is
the early-return route above. Witness 5 exercises only the rebuttal side and
witness 6 only the verdict side, so each kill is that side's.

**Wrong versions the witnesses must kill:**

- A runner that clips `structured_output`, or omits a null key.
- `run_agent` taking the value from an event other than the result.
- `run_agent` reading the value from the `StructuredOutput` tool call's
  input.
- `output_format` sent on the rebuttal turn as well, or set by mutating the
  shared options dict.
- A hand-written schema, or one with its descriptions stripped.
- A null `structured_output` read as a cue to parse the `<output>` block.
  A block preferred over a value present beside it.
- Treating `subtype == "success"` as the value having arrived.
- Parsing a string `structured_output` as JSON before validating it.
- A prompt that drops the extraction rules and with them the ban on
  changing files.

**The `size` gate counts tokens.** The `feature` ceiling is 3000. Most of
the diff is test helpers moving a payload from text to a field. Keep
docstrings to one or two lines.
