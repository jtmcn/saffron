---
id: SA-0176
title: A spec writer session has no prompt of core's own, and no extraction turn prompt to return its spec
type: feature
priority: 1
depends_on: [SA-0150]
touches:
  - saffron/spec_review.py
  - saffron/agents/prompts/spec-writer.md
  - saffron/agents/prompts/turns/spec-writer-extract.md
  - tests/test_spec_review.py
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
  - images/**
  - harness/**
  - records/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/*.py
  - saffron/agents/prompts/spec-review.md
  - saffron/agents/prompts/turns/spec-review-extract.md
  - saffron/agents/prompts/turns/extraction.md
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_review.py
  - tests/test_policy.py
budget_usd: 22
max_attempts: 3
max_turns: 140
pending_symbols:
  - saffron/spec_review.py::spec_writer_system_prompt
  - saffron/spec_review.py::SPEC_WRITER_EXTRACT_PROMPT
  - saffron/spec_review.py::SPEC_WRITER_FORMAT
acceptance:
  - claim: >-
      `spec_review.spec_writer_system_prompt(policy, *, prompts_dir)` reads
      `prompts_dir / SPEC_WRITER_PROMPT` when called, and
      `SPEC_WRITER_PROMPT` is `spec-writer.md`. It fills four slots with
      `str.format`: `{gates}`, `{protected}`, `{elevate_on}` and
      `{ceilings}`. Each slot holds exactly the lines
      `spec_review_system_prompt` fills that slot with for the same policy
      and the same `size._CEILINGS`, read when called. Braces inside a value
      reach the prompt unchanged. The witness drives a policy with two
      gates, one advisory, and an empty `Policy()`, under a patched
      ceiling, over one template written as both files. It then rewrites
      the writer's template alone.
    witness: tests/test_spec_review.py::test_the_spec_writer_system_prompt_fills_the_same_declarations_as_the_reviews
  - claim: >-
      The prompt files exist and serve their loaders.
      `spec_writer_system_prompt` over `context.PROMPTS_DIR` leaves none of
      the four slots unfilled, and holds each of the four filled blocks for
      a policy that declares every list. The raw `spec-writer.md` holds each
      of the three account lines `SA-0156` quotes, verbatim, each as a
      whole line. It holds the line "Measure any list of wrong builds you
      add with a throwaway script." as a whole line too.
      The raw `spec-writer-extract.md` holds the Problem's two lines, "Put
      the whole spec file in the `spec` field, frontmatter first." and "Do
      not wrap the file in a code fence.", each as a whole line. Its last
      three non-blank lines are "Answer now in the required structured
      format.", "Do not change files." and "Do not run commands.", in that
      order. It holds no brace pair, so no `{extraction}`. The raw
      `spec-writer.md` holds `{gates}`, `{protected}`, `{elevate_on}` and
      `{ceilings}` once each, and no other brace pair.
      `SPEC_WRITER_EXTRACT_PROMPT` is
      `context.turn_prompt("spec-writer-extract")`, and does not hold
      `artifacts.EXTRACTION_PROMPT`. Neither raw file holds any of the
      seventeen strings the notes list. The witness checks each of those
      seventeen in each file, case-insensitively.
    witness: tests/test_spec_review.py::test_cores_spec_writer_prompts_fill_every_slot_and_name_no_repo_tool
  - claim: >-
      `spec_review._SpecWriterReply` is a Pydantic model with one field,
      `spec`, a `str` with no default, and it forbids other keys.
      `SPEC_WRITER_FORMAT` equals `{"type": "json_schema", "schema":
      _SpecWriterReply.model_json_schema()}`. That schema's top-level
      `type` is `object`, its `required` is `["spec"]`, its `properties`
      name `spec` alone with `type` `string`, and its
      `additionalProperties` is `False`. `model_validate` returns a
      multi-line `spec` with its whitespace unchanged. It refuses `{}`,
      `{"spec": 3}`, `{"spec": None}`, `{"spec": "x", "extra": 1}` and a
      JSON string of a valid value.
    witness: tests/test_spec_review.py::test_the_spec_writer_format_is_the_schema_of_one_string_field
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.3. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that an agent writes and revises specs inside a stack batch.
Section 3 of `docs/superpowers/specs/2026-09-23-stack-batch-design.md` is
the design. A spec writer's spec returns through the extraction turn and
is hashed on arrival
(`docs/superpowers/specs/2026-09-23-stack-batch-design.md:162-163`).

**Core owns the writer's prompt.** ADR 7 makes the spec prompts core's.
They live "in `saffron/agents/prompts/`"
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:63-64`).
"A target repo supplies none of them, so ADR 2 holds. They name no repo
file, tool or URL"
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:64-65`).
A repo's facts reach them "as input the host fills from what the repo
declares in `.saffron/`", read at the `base_sha` export
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:65-67`).
Core "demands nothing of a repo"
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:198-199`).
The design record adds that this repo's `.claude/agents/spec-writer.md`
stays the hand path's own and differs from core's by design
(`docs/superpowers/specs/2026-09-23-stack-batch-design.md:164-168`). So
this spec writes `saffron/agents/prompts/spec-writer.md` and fills it from
a `Policy`, as `SA-0175` fills `spec-review.md`. `SA-0160` and `SA-0165`
pass the policy they export at the pinned `base_sha`. No policy key names
the prompt, and a batch is never refused for want of one.

**This spec is split from `SA-0160`.** Core's writer prompt, its
extraction turn prompt and their fill put `SA-0160` past the `feature`
ceiling. So this spec builds the prompts and the fill, as `SA-0175` does
for the review. `SA-0160` builds the session that runs them, and the
revision callable. `SA-0165` fills the same prompt for a follow-up.
Nothing in `saffron/` calls `spec_writer_system_prompt` or reads
`SPEC_WRITER_EXTRACT_PROMPT` or `SPEC_WRITER_FORMAT` until `SA-0160`
lands, hence `pending_symbols`. `SPEC_WRITER_FORMAT` reads
`_SpecWriterReply` at import, so the model needs no entry.

**The session holds Bash.** A spec writer session runs commands in its
critic cell, as a hand draft does. `SA-0169` runs that Bash as an
unprivileged user. `SA-0156` measured three account lines that tell a
session so, and quotes them in its Problem. Core's writer prompt carries
those same three lines, so a revision and a follow-up both read them.

**What the tree base holds.** This spec's tree base is `SA-0150`'s head.
Below it the chain runs through `SA-0169`, `SA-0175`, `SA-0156` and
`SA-0150`. Every line number below was read at `71140772`, where no chain
code from `SA-0142` on exists. This spec consumes these names.

- From `SA-0175`, in `saffron/spec_review.py`:
  `spec_review_system_prompt(policy, *, prompts_dir)` fills `{gates}`,
  `{protected}`, `{elevate_on}`, `{ceilings}` and `{tags}` in core's
  `spec-review.md`, read when called. `SPEC_REVIEW_PROMPT` is that file's
  name. Its criterion 4 names strings neither of its prompt files holds.
  This spec's notes list its own seventeen, so neither spec reads the
  other's list.
- From `SA-0156`: the three account lines its Problem quotes, verbatim.

**How a turn prompt is loaded today.** `context.turn_prompt(name)` reads
`prompts/turns/<name>.md` and fills any `{extraction}` slot with the
shared rules (`saffron/agents/context.py:156-171`). A file with no slot
loads unchanged. `rebut.EXTRACT_PROMPT` is loaded that way at import
(`saffron/phases/rebut.py:36`), and its file holds no slot.
`tests/test_context.py` holds every turn file to a constant that loads it
(`tests/test_context.py:413-429`), and lists the turns that carry the
shared rules (`tests/test_context.py:450-452`). `rebut-extract` is not
among them. `context.PROMPTS_DIR` is the one locator for the prompt tree
(`saffron/agents/context.py:21`). `size._CEILINGS` holds the ceiling per
spec type (`saffron/gates/core/size.py:26`).

**How a structured turn asks today.** `SA-0141` moved REBUT's extraction
turn onto the SDK's `output_format`. REBUT builds its format from its
model's `model_json_schema()` (`saffron/phases/rebut.py:66-69`). It merges
that format into the options of its resumed call
(`saffron/phases/rebut.py:207-214`). Its `_validate` checks the returned
value with that model (`saffron/phases/rebut.py:72-86`).
Its turn prompt ends with three lines, one to a line
(`saffron/agents/prompts/turns/rebut-extract.md:9-11`). They ask for the
structured format, and forbid file changes and commands. A schema
whose top level is not an object is refused by the API, and
`additionalProperties: false` is accepted
(`docs/evidence/2026-09-23-structured-output-spike.md:38-49`). The
spike's last addendum is headed "a whole spec as one string". It
returned specs of 40,153 and 45,945 characters exactly, each as the one
string field `spec` of a resumed turn. The operator decided the
writer moves onto this path and keeps its separate extraction turn
(principle 18, `docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:91-94`).

## Problem

Build three things.

1. **The system prompt.** Add `SPEC_WRITER_PROMPT` and
   `spec_writer_system_prompt`, as criterion 1 states. Fill each slot with
   the lines `SA-0175`'s fill builds. Sharing that code within the module
   is the cell's choice. Fill the slots as `format` arguments, never by
   substituting text and formatting the result.
2. **The prompt files.** Write `saffron/agents/prompts/spec-writer.md`, as
   the notes below say. Add
   `saffron/agents/prompts/turns/spec-writer-extract.md`. It holds these
   two lines, each word for word and on a line of its own.

   ```
   Put the whole spec file in the `spec` field, frontmatter first.
   Do not wrap the file in a code fence.
   ```

   It asks for nothing else in the field. It ends with these three lines,
   as `rebut-extract.md` ends.

   ```
   Answer now in the required structured format.
   Do not change files.
   Do not run commands.
   ```

   It holds no `{extraction}` slot and no other brace pair.
   `test_a_loaded_turn_prompt_keeps_no_unfilled_slot` reads a `{word}` as
   a slot (`tests/test_context.py:441-447`). Load it at import into
   `SPEC_WRITER_EXTRACT_PROMPT`, as `rebut.EXTRACT_PROMPT` is loaded
   (`saffron/phases/rebut.py:36`). Add `"spec-writer-extract"` to
   `tests/test_context.py`'s `TURN_PROMPTS` with that constant.
   `test_every_turn_prompt_file_is_loaded_by_something` fails without it.
   Leave the extraction-rules test's list as it is, since this turn
   carries no shared rules.
3. **The reply's shape.** Beside `SPEC_WRITER_EXTRACT_PROMPT`, add
   `_SpecWriterReply` and `SPEC_WRITER_FORMAT`, as criterion 3 states.
   Build the format as `rebut._REBUTTALS_FORMAT` is built
   (`saffron/phases/rebut.py:68`). `SA-0160` sends it on the extraction
   turn and validates the reply with the model.

## Out of scope

- **The session and the callable.** `SA-0160` builds `run_spec_writer`,
  its extraction turn and re-ask, and `_stack_revise`. They read the
  names this spec adds.
- **This repo's hand path.** `.claude/agents/spec-writer.md` stays as it
  is. Core never reads it.
- **`SA-0175`'s prompts.** This spec edits neither `spec-review.md` nor
  `spec-review-extract.md`, and changes nothing
  `spec_review_system_prompt` does.
- **The prompt's quality.** A prompt that fills every slot can still
  write badly. The first stack night measures it.
- **The vocabulary.** Backlog item b-466005 files the spec writer
  session's `CONTEXT.md` entry by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base fills a writer
prompt or holds one. So each criterion declares a witness and no mutant,
and `witness` reports `skip` for each.

**Every witness fails with the source reverted.** Each calls or reads a
name this spec adds. Import each new name inside the test body. A
module-scope import makes the reverted run a collection error, which
`revert` reads as `skip`. The new `TURN_PROMPTS` entry reads
`spec_review` at module scope, and is not a declared witness.

**What `spec-writer.md` says.** It is core's, so it names no repo file,
tool or URL, and none of the seventeen strings below. That bars
`.saffron/` too, since `saffron/` is one of them. The user prompt names the
spec's path. Keep the file within 50 lines. It holds each of the four
slots once, and no other brace. It covers these, in words of its own.

- It addresses the session as "you", and never writes "the reviewer".
- You write one spec file: YAML frontmatter between `---` fences, then a
  body. Each acceptance criterion holds a claim and a witness test.
- The user prompt takes one of two forms. A `review:` line asks you to
  revise a spec. The review sits between review tags, and the spec's
  current text sits between spec tags. The `spec:` line names the path
  where that text will live, and the text replaces the file there. Read
  the current text from the spec tags, never from that path in the
  checkout. Apply each blocker and concern that holds at the base, and
  keep the spec's purpose. A `context:` line asks for a new spec from the
  findings it gives.
- Each witness fails a plausible wrong build, and a claim over a set
  drives every member. New code declares a witness and no mutant.
- Every sentence about current code names a file and line you read at
  the base.
- Every file the change edits sits in `touches`, and none sits in
  `forbidden` or `{protected}`. A file the change must not edit goes in
  `forbidden`.
- `pending_symbols` names each new name that nothing calls until a later
  spec lands, as `<path>::<name>`. A name left out can fail a declared
  gate that reads unused code.
- The size estimate stays under its type's ceiling in
  `{ceilings}`. The size check blocks when a changed path matches
  `{elevate_on}`.
- A line that ends in a colon, then `{gates}` on the lines below it, says
  which gates the repo declares.
- The three account lines `SA-0156` quotes, each on its own line and
  word for word. Then "Measure any list of wrong builds you add with a
  throwaway script." on its own line.
- You write no file that outlives the cell. The host asks for the whole
  spec in a later turn.

**The seventeen strings** neither prompt file holds, compared lowered
with each file lowered: `.claude`, `CLAUDE.md`, `DESIGN.md`,
`CONTEXT.md`, `driver.py`, `pytest`, `uv run`, `make check`, `ruff`,
`prek`, `saffron/`, `docs/`, `/opt/`, `://`, `the reviewer`, `<output>`
and `output block`. The first fifteen name this repo's tools and paths.
The last two keep the writer off the `<output>` block, as
`test_rebuts_prompts_ask_for_no_output_block` keeps REBUT off it
(`tests/test_context.py:455-466`). Write the list in the witness, not
imported from `SA-0175`'s.

**Criterion 1's witness** writes one template into a `tmp_path` prompts
directory, as both `spec-review.md` and `spec-writer.md`:
``"G\n{gates}\nP\n{protected}\nE\n{elevate_on}\nC\n{ceilings}\n"``. It
builds `Policy` directly, never through `load_policy`. The first policy is
`SA-0175`'s criterion 3 witness's: `tests` then `lint`, with `lint` not
blocking, `protected` `uv.lock` then `docs/{a,b}.md`, and `elevate_on`
`saffron/ledger.py`. It sets `size._CEILINGS["feature"]` to 2999 with
`monkeypatch.setitem`. It asserts `SPEC_WRITER_PROMPT` is
`spec-writer.md`. For the first policy and for `Policy()`, the writer's
fill equals `spec_review_system_prompt` of the same policy over the same
directory. The first policy's fill holds each of three lines, given
here as Python strings with no trailing space: ``"- `lint` (advisory)"``,
``"- `docs/{a,b}.md`"`` and ``"- `feature`: 2999 changed tokens"``. Last, it
rewrites `spec-writer.md` alone as ``"W\n{gates}\n"``, and the writer's
fill is exactly ``"W\n- `tests`\n- `lint` (advisory)\n"``. These fail it:

- `SPEC_REVIEW_PROMPT` read in place of `SPEC_WRITER_PROMPT`
- the template read once at import, or from `context.PROMPTS_DIR`
- gates or lists sorted
- an empty list filled with an empty string, not `none`
- the ceilings written out by hand, which misses 2999
- the values substituted and the result then formatted, which fails on
  `{a,b}`

**Criterion 2's witness** fills the real template with criterion 1's
first policy, without the `setitem`. It asserts no `{gates}`,
`{protected}`, `{elevate_on}` or `{ceilings}` is left. The result
holds each of these four blocks.

```
- `tests`
- `lint` (advisory)
```

```
- `uv.lock`
- `docs/{a,b}.md`
```

```
- `saffron/ledger.py`
```

```
- `feature`: 3000 changed tokens
```

It reads `spec-writer.md` raw, splits
it into lines, and asserts each of `SA-0156`'s three account lines and the
throwaway-script line is one of them. It asserts
`sorted(re.findall(r"\{[^{}]*\}", raw))` for `spec-writer.md` equals
`["{ceilings}", "{elevate_on}", "{gates}", "{protected}"]`. It reads
`spec-writer-extract.md` raw, splits it into lines, and asserts each of
the Problem's two lines is one of them. Its non-blank lines end with the
Problem's three closing lines, in order. `re.findall(r"\{[^{}]*\}", raw)`
for it is `[]`. It asserts `SPEC_WRITER_EXTRACT_PROMPT` equals
`context.turn_prompt("spec-writer-extract")`, and does not hold
`artifacts.EXTRACTION_PROMPT`. It lowers both raw files and checks each of
the seventeen strings against each. These fail it, reasoned:

- a turn file that asks for the file inside a code fence, or words the
  ban otherwise, which a check for the words `code fence` passes
- a turn file that asks for the body alone, or the frontmatter last
- a template that leaves a slot out, or spells a stray brace
- a `{tags}` slot in the writer's template, which the fill passes over
  unseen
- a slot written twice, which fills both places
- a turn file that keeps the `{extraction}` slot, whose load then holds
  the shared rules and their `<output>` block
- a turn file that asks for an `<output>` block, or names the field other
  than `spec`
- a turn file with text after "Do not run commands.", or one of the three
  closing lines left out or reordered
- an account line reworded, joined to another line, or left out
- the account lines in the user prompt alone, where a follow-up's
  session never reads them
- a writer prompt that names this repo's tools or `.saffron/`, as the hand
  path's agent file does

**Criterion 3's witness** imports `_SpecWriterReply` and
`SPEC_WRITER_FORMAT` inside its body. It asserts the format equals the
dict criterion 3 names, and reads the schema's `type`, `required`,
`properties` and `additionalProperties` from it. It validates
`{"spec": "---\nid: X\n---\n  body  \n"}` and asserts the `spec` it
returns equals that string. It asserts `pydantic.ValidationError` for
each of the five refused values. These fail it, measured on 2026-09-25
in a throwaway script over Pydantic's own models:

- no `extra="forbid"`, which accepts the extra key and drops
  `additionalProperties`
- a default on `spec`, which accepts `{}` and empties `required`
- the field named `text`
- `str_strip_whitespace`, which changes the body's padding
- `coerce_numbers_to_str`, which accepts `{"spec": 3}`
- a `RootModel[str]`, whose schema's top level is a string, the shape
  the API refuses

**The other lists are unmeasured.** Nothing below this spec's head is
built, and neither prompt file was prototyped. Criteria 1 and 2's lists
are reasoned from the code they name.

**What the witnesses leave undriven.** A prompt that names a repo file by
a string outside the seventeen passes. So does one that fills every slot
and writes badly. An empty `spec` validates, and `SA-0150`'s
`parse_spec` refuses it at run time. No witness sends the format to the
API. The spike measured the one-field shape on the host, not in a cell.

**The `prose` gate** counts both new prompt files, and every new comment
and docstring. Write none with an em dash, a semicolon, a contraction, the
perfect tense, a hedge or a sentence over 25 words. Use no word from
`FILLER` (`.saffron/gates/prose.py:67-83`), such as `just` or `simply`.
Run `python3 hooks/prose_limit.py --file <path>` on each prompt file. Keep
each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
estimate is about 1100 to 1350 changed tokens, 37% to 45% of the
ceiling. The `history` rows beside this spec measured lines against the
old ceiling of 600 changed lines, so none compares with this figure
directly.
The fill and its two constants run about 80 to 130 tokens in
`saffron/spec_review.py`. The model, the format and the import add about
60, as `saffron/phases/rebut.py:39-69` runs for two models and two formats.
`spec-writer.md` at 50 lines runs about 310 to 460 tokens. That is 6.2
to 9.1 words a line, as the system prompts in `saffron/agents/prompts/`
run (`wc -lw`). The extraction turn prompt runs about 50. Criteria 1 and
2's witnesses run about 160 and 220, the second with the seventeen
strings written out. Criterion 3's runs about 140, and
`tests/test_context.py` takes about 5.
