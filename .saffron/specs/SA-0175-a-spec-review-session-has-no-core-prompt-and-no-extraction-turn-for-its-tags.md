---
id: SA-0175
title: A spec review session has no prompt of core's own, and no extraction turn returns its tags
type: feature
priority: 1
depends_on: [SA-0169]
touches:
  - saffron/spec_review.py
  - saffron/agents/prompts/spec-review.md
  - saffron/agents/prompts/turns/spec-review-extract.md
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
  - saffron/agents/prompts/turns/extraction.md
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_review.py
  - tests/test_policy.py
budget_usd: 26
max_attempts: 3
max_turns: 220
pending_symbols:
  - saffron/spec_review.py::run_spec_review
  - saffron/spec_review.py::spec_review_system_prompt
  - saffron/spec_review.py::SPEC_REVIEW_TIMEOUT_S
  - saffron/spec_review.py::SPEC_REVIEW_SESSION_USD
acceptance:
  - claim: >-
      `spec_review.run_spec_review(container, *, system_prompt, prompt,
      agent)` first calls `agent` with the container, the prompt, and
      `implement.agent_options` of that system prompt,
      `SPEC_REVIEW_MAX_TURNS`, `SPEC_REVIEW_BUDGET_USD` and
      `SPEC_SESSION_TOOLS`. It passes nothing else, so those options carry
      no `output_format`. `SPEC_SESSION_TOOLS`
      holds `Read`, `Glob`, `Grep` and `Bash`, and no other tool.
      `SPEC_REVIEW_MAX_TURNS` is 90, `SPEC_REVIEW_BUDGET_USD` 6.0,
      `SPEC_REVIEW_EXTRACT_BUDGET_USD` 1.0, `SPEC_REVIEW_SESSION_USD` 8.0,
      `SPEC_REVIEW_TIMEOUT_S` 1800.0 and `UNREADABLE_RESET` 1, and the
      witness asserts each literal. A first
      turn that raises `implement.AgentFailed` gives that failure's text as
      `error`, with its attempt's cost, `session_id` and `num_turns`, or
      empty ones when it carries none. A first turn whose rate-limit status
      is `rejected`, returned or raised, gives no error and keeps its cost,
      `session_id` and `num_turns`.
      Its `resets_at` is the `int` that `session._resets_at_fields` passes
      where that is above 0. It is `UNREADABLE_RESET`, 1, where that passes
      none or one at or below 0. Neither case calls `agent` again, and
      neither session's `text` holds anything of the first turn's. Any other
      raise propagates. The witness drives a returned rejection, raised ones
      carrying `10**20`, `None`, `"soon"`, `True`, a float, 0 and -5, a
      failed turn with an attempt and one without, and a `RuntimeError`.
    witness: tests/test_spec_review.py::test_a_spec_review_session_returns_a_rejected_window_as_a_reset_time
  - claim: >-
      After a first turn that returns with a `session_id` and a status other
      than `rejected`, `run_spec_review` calls `agent` a second time. It
      passes the container, `SPEC_REVIEW_EXTRACT_PROMPT`, and the first
      call's options with `max_budget_usd` set to
      `SPEC_REVIEW_EXTRACT_BUDGET_USD` and `output_format` set to
      `SPEC_REVIEW_FORMAT`. It passes `resume` of the first turn's
      `session_id`, and `last_cost_usd` of the smaller of that turn's cost
      and `SPEC_REVIEW_EXTRACT_BUDGET_USD`, and nothing else. `SPEC_REVIEW_FORMAT` is `{"type": "json_schema",
      "schema": _SpecReviewFindings.model_json_schema()}`. That model is an
      object whose one key, `findings`, is a list of `_SpecReviewFinding`.
      Its fields, in order, are `severity` typed `findings.Severity`,
      `claim` a string, `criterion` an integer or null, `file` a string or
      null, `line` an integer or null, and `fixes` any string or null. The
      schema of each of the last four holds a null branch. No field has a
      default, and both models forbid other keys. When
      `_SpecReviewFindings.model_validate` accepts the second turn's
      `structured_output`, the session's `text` is a `json` fence around
      `json.dumps` of the validated model's `model_dump(mode="json")`, with
      `indent=2` and `ensure_ascii=False`. It holds nothing of either
      turn's text. A null `structured_output`, or one `model_validate`
      refuses, goes to criterion 5's one re-ask. Its cost and `num_turns`
      sum every attempt a turn returned or failed with, a killed turn's
      included, and a failed turn with no attempt counts 0. Its
      `session_id` is the second turn's, or the first's where the second
      carries none. A first turn with no
      `session_id` gives `no session to extract from` as `error`, and no
      second call. A second turn whose status is `rejected`, returned or
      raised, gives no error and an empty `text`. Its `resets_at` follows
      the first turn's rule, driven with 9, -5 and `"soon"`. A second turn that
      raises `AgentFailed` otherwise gives its text as `error` and an empty
      `text`. Any other raise propagates. The witness drives each case, with
      a first status of none and of `allowed`, a note whose four nullable
      fields are null, and an extraction turn killed after a first turn of
      cost 0.5 and of 4.0. Every second turn's text holds an `<output>`
      block and a `json` block that disagree with its value.
    witness: tests/test_spec_review.py::test_a_spec_review_returns_its_tags_from_a_separate_extraction_turn
  - claim: >-
      `spec_review.spec_review_system_prompt(policy, *, prompts_dir)` reads
      `prompts_dir / SPEC_REVIEW_PROMPT` when called, and `SPEC_REVIEW_PROMPT`
      is `spec-review.md`. It fills five slots with `str.format`. `{gates}`
      holds one line per declared gate, in declaration order, as a dash and
      the name in backticks. A gate whose `blocking` is false adds
      ` (advisory)`. `{protected}` and `{elevate_on}` hold one such line per
      entry, in order. An empty list fills `none`. `{ceilings}` holds one
      line per entry of `size._CEILINGS`, in its order, as the type in
      backticks, a colon, the number and `changed tokens`. A last line
      gives `size._DEFAULT_CEILING` as `any other type`. `{tags}` holds
      one line per entry of `SPEC_REVIEW_TAGS`, the tuple `SA-0149`
      defines in the same module, read when called. Every line starts with a dash and a space, and
      lines join on a newline. Braces inside a value reach the prompt
      unchanged.
      The witness drives a policy with two gates, one advisory, an empty
      policy, and patched tags.
    witness: tests/test_spec_review.py::test_the_spec_review_system_prompt_fills_the_repos_declarations_into_cores_template
  - claim: >-
      The prompt files exist and serve their loaders.
      `spec_review_system_prompt` over `context.PROMPTS_DIR` holds each of the
      five filled blocks for a policy that declares every list.
      `SPEC_REVIEW_EXTRACT_PROMPT` is `context.turn_prompt("spec-review-extract")`
      and names `findings`, `severity`, `claim`, `fixes`, `blocker`,
      `concern`, `note` and `witness`. Its lines include "Answer now in the
      required structured format.", "Do not change files." and "Do not run
      commands.", each whole. It does not hold
      `artifacts.EXTRACTION_PROMPT`, and the raw file holds no
      `{extraction}`. With whitespace runs collapsed to one space, the raw
      `spec-review.md` holds the sentence "A concern that a criterion's
      witness cannot be measured carries `witness`." The extraction prompt
      holds "Copy each finding's `fixes` exactly as your review gave it, and
      decide no tag from the prose." Neither file holds `.claude`,
      `CLAUDE.md`, `DESIGN.md`, `CONTEXT.md`, `driver.py`, `pytest`, `uv
      run`, `make check`, `ruff`, `prek`, `saffron/`, `docs/`, `/opt/`,
      `://`, `the reviewer`, `<output>` or `output block`. The witness
      checks each of those seventeen strings in each file,
      case-insensitively.
    witness: tests/test_spec_review.py::test_cores_spec_review_prompts_fill_every_slot_and_name_no_repo_tool
  - claim: >-
      When the second turn's `structured_output` is null, or
      `_SpecReviewFindings.model_validate` refuses it, `run_spec_review`
      re-asks once. Its third call passes the container, the failure's
      message, a blank line and `SPEC_REVIEW_EXTRACT_PROMPT` as the prompt,
      the second call's options, `resume` of the last `session_id` a turn
      carried, and `last_cost_usd` of the smaller of the second turn's
      cost and `SPEC_REVIEW_EXTRACT_BUDGET_USD`. It passes nothing else. The message is `not the schema: the turn returned no
      structured output` for a null value. For a refused one it is `not
      the schema: ` and the validation error. A third turn whose value
      passes gives `text` as criterion 2 builds it from that value. One
      whose value is null or refused gives that message as `error` and an
      empty `text`, and there is no fourth call. A rejected third turn, returned or
      raised, gives no error, an empty `text`, and criterion 1's reset
      rule. A third turn that raises `AgentFailed` otherwise gives its text
      as `error`, and any other raise propagates. Cost and `num_turns` sum
      over every turn, and `session_id` is the last one a turn carried. The
      witness drives a null value, a value missing `claim`, one with
      severity `critical`, one with an extra key, and a JSON string of a
      valid value, and a killed re-ask after a second turn of cost 0.25
      and of 3.0. Each second turn's text beside them holds a valid
      `<output>` block and `json` block.
    witness: tests/test_spec_review.py::test_a_spec_review_re_asks_once_when_its_extraction_is_not_the_schema
---

## Context

Backlog item **b-792ab2**, step 6 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that spec review runs inside a stack batch, before each spec's
first cell. It also decides whose prompt that review reads. "The spec
prompts, the end-review lens prompts and the tags blockers route by are
core's, in `saffron/agents/prompts/`. A target repo supplies none of
them" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:63-67`).
A repo's facts reach them "as input the host fills from what the repo
declares in `.saffron/`", read at the `base_sha` export. Core "demands
nothing of a repo" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:198-199`).
"A spec review returns its tags the same way", through a separate
extraction turn, so it keeps principle 18
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:91-94`).
Section 3 of `docs/superpowers/specs/2026-09-23-stack-batch-design.md`
says the same (`docs/superpowers/specs/2026-09-23-stack-batch-design.md:160-168`).
It adds that this repo's `.claude/agents/spec-reviewer.md` stays the hand
path's own and differs from core's by design.

**This spec is split from `SA-0156`.** Core's prompt and its extraction
turn put `SA-0156` past 80% of the `feature` ceiling. So this spec builds
the session and its prompts, and `SA-0156` builds the callable that runs
it in a cell, the mint and the wiring. Nothing in `saffron/` calls
`run_spec_review` until `SA-0156` lands, hence `pending_symbols`.

**What the tree base holds.** This spec's tree base is `SA-0169`'s head.
The chain below it runs `SA-0135`, `SA-0136`, `SA-0142` to `SA-0146`,
`SA-0153`, `SA-0154`, `SA-0157`, `SA-0159`, `SA-0147`, `SA-0148`,
`SA-0149`, `SA-0155`, `SA-0168` and `SA-0169`. Every line number below was
read at `71140772`, where none of their code exists. This spec consumes
these names.

- From `SA-0149` and `SA-0155`: `saffron/spec_review.py` with
  `SpecReviewSession`, a frozen dataclass of `text`, `cost_usd`, `error`,
  `resets_at`, `session_id` and `num_turns`. `read_spec_review` reads the
  last fenced `json` block of `text`, `{"findings": [...]}`. Each finding
  holds `severity`, `claim` and `fixes`, and `fixes` is `scope`, `build`,
  `witness`, null or absent. `SPEC_REVIEW_TAGS` is the tuple `("scope",
  "build", "witness")`, and the read checks `fixes` against it. A
  `concern` whose `fixes` is `witness` marks a witness that cannot be
  measured. `SA-0155` hashes that block and records it.
- From `SA-0169`: a session whose tools hold `Bash` and neither `Write`
  nor `Edit` runs its `Bash` as an unprivileged account. A resumed
  extraction turn reads the transcript in the state volume.

**How a critic session runs today.** `review.run_lens` builds
`agent_options` with `REVIEW_TOOLS`, `Read`, `Glob` and `Grep`, and calls
the agent (`saffron/phases/review.py:35`, `:229-236`). The implementer's
tools add `Write`, `Edit` and `Bash` (`saffron/phases/implement.py:30`).
`AgentFailed` carries the attempt of a turn that failed, or `None`
(`saffron/phases/implement.py:57-73`). `stop_on_rejected` raises `RateLimited` on a rejected window,
from a returned turn or a failed one (`saffron/cell/session.py:159-181`).
`terminal_for_rate_limit` reads the status (`:235-238`).
`_resets_at_fields` passes any clean `int`, 0 and negatives included, and
turns anything else into `None` (`:150-156`).

**How REBUT's extraction turn runs today.** `SA-0141` (#520) moved it
to the SDK's `output_format`. `rebut.run_rebuttal` runs the work turn,
then resumes the same session with an extraction prompt
(`saffron/phases/rebut.py:173-233`). The second call passes `resume`,
`last_cost_usd`, and the work turn's options with `output_format` set
to `_REBUTTALS_FORMAT` (`:207-214`). That format is `{"type":
"json_schema", "schema": _Rebuttals.model_json_schema()}` (`:68`). The
host reads the second turn's `structured_output` alone, through
`_validate` (`:226`). `_validate` gives `not the schema: the turn
returned no structured output` for a null value, and `not the schema: `
and the validation error for a refused one (`:72-86`). REBUT does not
re-ask, because its attempt is already made (`:223-225`).
`AttemptResult.structured_output` carries the result event's value
whole (`saffron/phases/implement.py:96-98`). The runner copies it from
the SDK's result message (`images/agent_runner.py:130-132`).

REBUT's extraction prompt has no `{extraction}` slot, so the shared
`<output>` rules never reach it. It ends with three lines: "Answer now
in the required structured format.", "Do not change files." and "Do not
run commands." (`saffron/agents/prompts/turns/rebut-extract.md:9-11`).
`test_rebuts_prompts_ask_for_no_output_block` checks two of the three
closing lines whole. They are "Do not change files." and "Do not run
commands." It
also checks that the prompt holds neither `<output>` nor
`artifacts.EXTRACTION_PROMPT` (`tests/test_context.py:455-466`). Criterion
4 here checks all three lines itself. `context.turn_prompt` fills an
`{extraction}` slot where one stands (`saffron/agents/context.py:156-171`).

**What the SDK's structured output does, measured.** The schema holds
on a resumed session (`docs/evidence/2026-09-23-structured-output-spike.md:34-36`).
The CLI answers `output_format` through a tool named `StructuredOutput`
(`docs/evidence/2026-09-23-structured-output-spike.md:84-85`). A schema
whose root is not an object is refused with an API 400
(`docs/evidence/2026-09-23-structured-output-spike.md:38-49`). A turn no value satisfies still ends `success`, with a null
`structured_output`, after four tries of that tool inside the one turn
(`docs/evidence/2026-09-23-structured-output-spike.md:51-59`). So the CLI already retries the shape within a turn.
§5.3 records the move for REBUT, and says the other extraction turns
still emit the block (`DESIGN.md:731`).

The spike's last addendum sent this spec's finding shape through a
resumed turn. The API took four required nullable fields. The turn
returned two findings with all four null, and both validated. That
extraction turn cost $0.08
(`docs/evidence/2026-09-23-structured-output-spike.md:196-207`).

**How a killed turn is charged today.** A turn killed before its result
event raises `AgentFailed`. Its attempt has no `session_id` and 0 turns.
Its cost is the `last_cost_usd` its call passed
(`saffron/phases/implement.py:334-345`). A failed turn that reported 0
falls back to that same figure (`saffron/phases/implement.py:411-423`).
§4.1 names the rule (`DESIGN.md:343`). `SA-0160` caps the figure its
writer passes at the next turn's own budget, and this spec does the same.

**How a lens prompt is loaded today.** `LENSES` maps a lens to a file
name, and `lens_prompt` reads `prompts_dir / LENSES[lens]` when called
(`saffron/phases/review.py:39-43`, `:168-188`). `context.PROMPTS_DIR` is
the one locator for the prompt tree (`saffron/agents/context.py:21`).

**What a repo declares.** `Policy` holds `gates`, a mapping of name to a
`GateDeclaration` with `blocking`, and the lists `elevate_on` and
`protected` (`saffron/repos/policy.py:45-74`). `size._CEILINGS` holds the
ceiling per spec type (`saffron/gates/core/size.py:26`).
`saffron/agents/artifacts.py:21` already imports it.

## Problem

Build four things.

1. **The constants and the model.** In `saffron/spec_review.py`, add
   `SPEC_REVIEW_MAX_TURNS` of 90 and `SPEC_REVIEW_BUDGET_USD` of 6.0. Add
   `SPEC_REVIEW_EXTRACT_BUDGET_USD` of 1.0 and `SPEC_REVIEW_SESSION_USD`
   of 8.0. Add `SPEC_REVIEW_TIMEOUT_S` of 1800.0, `UNREADABLE_RESET` of 1,
   `SPEC_SESSION_TOOLS`, `SPEC_REVIEW_PROMPT` and
   `SPEC_REVIEW_EXTRACT_PROMPT`. Write the session figure as the sum of
   the review's budget and two extraction budgets. Define no tags. `SPEC_REVIEW_TAGS`
   already stands in the module, from `SA-0149`. Follow `REVIEW_TOOLS`' spelling
   for the tools, a list of names. Load the extraction prompt with
   `context.turn_prompt` at import, as `rebut.EXTRACT_PROMPT` is loaded.
   Name the 681-second measurement below in the timeout's comment. Add
   the Pydantic models `_SpecReviewFinding` and `_SpecReviewFindings` and
   `SPEC_REVIEW_FORMAT`, as criterion 2 states. Build the format once at
   import, as `rebut._REBUTTALS_FORMAT` is built (`saffron/phases/rebut.py:68`).
2. **The session.** Add `run_spec_review`, as criteria 1, 2 and 5 state.
   Read the rate-limit status with `session.terminal_for_rate_limit`, on
   the returned attempt or the failed one. Call the agent directly, not
   through `stop_on_rejected`, so a rejected turn's cost reaches the
   session. Build the second call as `run_rebuttal` builds its own, the
   first call's options with `output_format` added. Set its
   `max_budget_usd` to `SPEC_REVIEW_EXTRACT_BUDGET_USD` too, as `SA-0160`
   does for its writer. Pass each later turn `min(prior cost,
   SPEC_REVIEW_EXTRACT_BUDGET_USD)` as `last_cost_usd`. Read the value as
   `rebut._validate` reads it. Calling it is the cell's choice, since it
   gives the messages criterion 5 names. Build the re-ask as `run_lens`
   builds its own, from the error, a blank line and the turn's own prompt
   (`saffron/phases/review.py:222-227`, `:268-275`). §5.3 feeds a schema
   failure back "twice, then reject" (`DESIGN.md:727`). This spec re-asks
   once, as `run_lens` does, and not twice.
3. **The system prompt.** Add `spec_review_system_prompt`, as criterion
   3 states. Fill the slots as `format` arguments, never by substituting
   text and formatting the result.
4. **The prompt files.** Write `saffron/agents/prompts/spec-review.md`
   and `saffron/agents/prompts/turns/spec-review-extract.md`, as the notes
   below say. Add `"spec-review-extract"` to `tests/test_context.py`'s
   `TURN_PROMPTS`. `test_every_turn_prompt_file_is_loaded_by_something`
   fails without it. Leave it out of the names
   `test_a_prompt_declaring_the_slot_gets_the_extraction_rules` lists,
   since this prompt declares no slot.

## Out of scope

- **The cell, the mint and the wiring.** They are `SA-0156`'s.
- **This repo's hand path.** `.claude/agents/spec-reviewer.md` stays as
  it is. Core never reads it.
- **Reading the tags.** `SA-0149` reads the block and routes on it. This
  spec only fixes what the block holds and where it comes from.
- **The review turn's prose.** It reaches no record. `SA-0155` records
  the block the host writes from the extraction turn's value.
- **§5.3's text.** It names REBUT alone as using `output_format`, and
  says "the other extraction turns still emit the block" (`DESIGN.md:731`).
  Principle 18 calls the extraction turn tool-less. Both lag this turn,
  which keeps the session's tools. `DESIGN.md` is forbidden here, and
  backlog item b-4e0868 owns that text as the other turns move.
- **History rows for a ceilings check.** A batch has no ledger in the
  cell, so core's prompt carries no such check.
- **The writer's prompt.** `SA-0176` adds it beside this one.
- **The review's events.** `run_spec_review` passes the agent no `emit`.
  `run_agent`'s default prints each event, cut short
  (`saffron/phases/implement.py:196-203`, `saffron/events.py:669-675`). No
  review event reaches an `events.jsonl`, so `saffron watch` shows none.
- **The review's budget.** `SPEC_REVIEW_BUDGET_USD` of 6.0 is unmeasured
  for a batch review. `SA-0155` records each review's cost, so the first
  stack night measures it.
- **The vocabulary.** Backlog item b-466005 files the spec review's
  `CONTEXT.md` entry by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base runs a spec
review session or holds a spec review prompt. So each criterion declares a
witness and no mutant, and `witness` reports `skip` for each.

**Every witness fails with the source reverted.** Each calls or reads a
name this spec adds. Import each new name inside the test body. A
module-scope import makes the reverted run a collection error, which
`revert` reads as `skip`.

**How long one review runs.** `session.TURN_TIMEOUT_S` is 900 seconds of
wall clock per turn (`saffron/cell/session.py:63`). The hand reviews of
this chain, run on 2026-09-24 with `Bash`, took 566 to 681 seconds.
`SA-0156`'s round-1 review took 681 seconds and 64 tool uses.
`SPEC_REVIEW_TIMEOUT_S` is twice the bound for that reason.

**Why 1 and not 0 or less.** `SA-0148` waits an hour for a reset time at
or before now. `SA-0149` routes `wait` when `resets_at` is set. A check
written as `if review.resets_at:` reads 0 as unset, and routes the
session `error`.

**Why `text` is empty on every failure.** `SA-0155` records the block it
reads from `text` whatever the route. A failed first turn's text is the
review's own prose, and any `json` block in it would then be recorded as
the tags. So only a completed extraction turn puts anything in `text`.

**Why `text` is the host's own serialization.** The extraction turn now
sends no JSON text. Its answer arrives as a parsed value on
`structured_output`. So the host writes `text` itself, in one fixed
form, fenced as `json`. `SA-0149` reads that fence as it reads any, and
`SA-0155` hashes its body. What gets hashed is therefore the host's
serialization, never bytes the model sent. `model_dump` puts the keys
in the model's field order, so one set of findings always gives the same
bytes and the same hash. Serializing the raw value instead would keep
whatever key order the turn chose. Read neither turn's text: a text
block beside a null value is not a fallback.

**Why the re-ask stays.** The CLI already retries the shape inside the
turn. The spike's unsatisfiable schema drew four `StructuredOutput`
calls before the turn ended with a null value. So the host's one re-ask
is a backstop. REBUT has none, because its attempt is already made and
HEAD already says what it did (`saffron/phases/rebut.py:223-225`). A
spec review's value is its whole product. Without its findings the
review's spend buys nothing, and `SA-0149` routes the session `error`,
which counts as an abort. The spike's extraction turn cost $0.08, far
less than the review it saves.

**The bound on one session.** The review turn runs at
`SPEC_REVIEW_BUDGET_USD`, 6.0. The extraction turn and the re-ask each
run at `SPEC_REVIEW_EXTRACT_BUDGET_USD`, 1.0, a dozen times the spike's
$0.08. That turn resumes a context a real review made far longer, so 1.0
is reasoned with room, not measured in a cell. Each fallback figure is
capped at the next turn's own budget. So a session records at most
6.0 + 1.0 + 1.0, which is `SPEC_REVIEW_SESSION_USD`, 8.0. It holds as
long as each turn reports within its `max_budget_usd`, which is best
effort. `SA-0164` reserves by it. A first turn killed before its result
event records $0, since `run_spec_review` passes it no `last_cost_usd`.

**Why four fields take null.** The CLI holds the turn to the schema
before the host sees a value. A `fixes` typed `str` would make the turn
write a string where the review gave no tag, such as `none`. `SA-0149`
checks each `fixes` against `SPEC_REVIEW_TAGS`, and routes that read
`error`. A `file` or `line` that cannot be null would make the turn
invent a place for a finding about the whole spec. `_Reported` types
`file` and `line` without null (`saffron/phases/review.py:67-68`), since a
lens finding is always anchored. A spec review finding is not. The spike
measured this shape (`docs/evidence/2026-09-23-structured-output-spike.md:196-207`).

**Why the model checks no tag.** `fixes` is any string or null.
`SA-0149`'s read checks each `fixes` against `SPEC_REVIEW_TAGS` when
called, and that stays the only tag check. A `Literal` of the tags built
at import would be a second tag constant, where criterion 3 reads the
one constant when called. Criterion 2's `typo` row and its read of the
schema refuse one. `severity` does use
`findings.Severity`, the one spelling of that set
(`saffron/agents/findings.py:23`), as `SA-0149` does. The `dead` gate's
vulture reports a model field whose name nothing uses, measured on a
scratch model. It matches names globally, and every field name here is
used in `saffron/` at the tree base. `criterion` is a loop name in
`saffron/intake.py:282`, and `fixes` is read by `SA-0149`'s read.

**What `spec-review.md` says.** It is core's, so it names no repo file,
tool or URL, and none of criterion 4's seventeen strings. Keep it within
60 lines. It holds each of the five slots once, and no other brace. It
covers these, in words of its own.

- It addresses the session as "you", and never writes "the reviewer".
  `CONTEXT.md` keeps that word for the operator (`CONTEXT.md:469`).
- You read one spec before a cell spends money on it. The user prompt
  names the spec's path and base. The working tree is a snapshot of that
  base.
- Severities. A blocker gets a cell wrong if built as written. A concern
  needs the operator's judgement. A note is true and minor.
- Each blocker carries one tag from `{tags}`. `scope` changes the spec's
  goal. `build` changes what the cell builds within that goal. `witness`
  changes only a test or probe. Then this sentence, word for word, the
  one place the rule is written: "A concern that a criterion's witness
  cannot be measured carries `witness`." It is the design's own rule
  (`docs/superpowers/specs/2026-09-23-stack-batch-design.md:198-199`).
- Five checks. A criterion built as written breaks the repository's
  standing instructions or design. Every file the change edits sits in
  `touches` and outside `forbidden` and `{protected}`. Each witness fails
  a plausible wrong build, and a claim over a set drives every member.
  The size estimate stays under its type's ceiling in `{ceilings}`. The
  gate blocks when the spec says `risk: elevated` or a changed path
  matches `{elevate_on}`. Every sentence about current code is true at
  the snapshot.
- A line that ends in a colon, then `{gates}` on the lines below it,
  says which gates the repo declares. So an empty list reads `none`.
- You write a report in prose, and the host asks for the findings in a
  later turn. You write no file in the tree.

**What `spec-review-extract.md` says.** It asks for an object with the
key `findings`, one entry per finding in the review. Each entry holds
`severity` (`blocker`, `concern` or `note`), `claim`, `criterion` (a
number or null), `file`, `line` and `fixes`. `file` and `line` are null
for a finding that names no place. It holds this sentence word for word.

> Copy each finding's `fixes` exactly as your review gave it, and decide
> no tag from the prose.

`fixes` is null where the review gave no
tag. The extraction turn copies tags and judges none. That sentence names
the field on purpose. In the spike, a prompt said "tag" and never
named `fixes`. The turn wrote the tag into the claim as `[tag: build]`,
and left `fixes` null
(`docs/evidence/2026-09-23-structured-output-spike.md:209-212`). So
criterion 4 pins it. `SA-0164`
routes on the tag the review gave. It ends with these three lines, each
on its own, as `rebut-extract.md` does.

```
Answer now in the required structured format.
Do not change files.
Do not run commands.
```

It has no `{extraction}` slot, so the shared `<output>` rules never reach
it. Write no `{word}` brace pair in it, since
`test_a_loaded_turn_prompt_keeps_no_unfilled_slot` reads one as a slot.

**Criterion 1's witness** calls `run_spec_review` with the container
`c-1`, the system prompt `sys` and the prompt `p`. Its agent double
records each call's arguments and returns or raises the case's turn. Each
case asserts exactly one call, with those three and the options the claim
names, and no other keyword. It asserts `"output_format"` is not in
that call's options. `J` is a first-turn text of prose, then a
fenced `json` block with one `scope` blocker, then an `<output>` block
holding that same object. No first turn carries a `structured_output`.
A build that reads the first turn's text finds `J`'s `scope` blocker.

| first turn | `text`, `cost_usd`, `error`, `resets_at`, `session_id`, `num_turns` |
|---|---|
| returned, text `J`, `rejected`, reset 1755800000, cost 0.25, `s-1`, 7 turns | empty, 0.25, `None`, 1755800000, `s-1`, 7 |
| raised `AgentFailed("api_error")`, `rejected`, reset `10**20`, cost 0.125, `s-1`, 3 turns | empty, 0.125, `None`, `10**20`, `s-1`, 3 |
| the same with reset `None`, `"soon"`, `True`, 1755800000.0, 0 and -5 | empty, 0.125, `None`, 1, `s-1`, 3 |
| raised `AgentFailed("idle bound")`, text `J`, cost 0.0625, `s-1`, 7 turns | empty, 0.0625, `idle bound`, `None`, `s-1`, 7 |
| raised `AgentFailed("no result")` with no attempt | empty, 0.0, `no result`, `None`, `None`, 0 |
| raised `RuntimeError("runner died")` | raises |

Each rejected case asserts `type(resets_at) is int`. The witness also
asserts `SPEC_SESSION_TOOLS`, sorted, is `Bash`, `Glob`, `Grep` and
`Read`. These fail it:

- `stop_on_rejected` around the agent, which raises `RateLimited`
- a rejection read from a returned turn only, or a failed one only
- `None` where the reset time cannot be shaped
- the raw reset value, or 0 in place of 1
- a reset at or below 0 passed through, or only 0 mapped to 1
- the failure's text kept as `error` on a rejected turn
- a failed turn's text, cost or `session_id` dropped into or out of the
  session as the table does not say
- an extraction turn after a rejected or failed first turn
- `IMPLEMENT_TOOLS`, `REVIEW_TOOLS`, or a list that adds `Write`
- the turns and budget swapped, or any constant at another value
- `SPEC_REVIEW_SESSION_USD` written as 6.0 plus one extraction budget
- `output_format` sent on the review turn too
- every exception caught

**Criterion 2's witness** uses the same double, with a first turn that
returns text `J`, cost 0.5, `s-1` and 7 turns. `D` is the dict
`{"findings": [{"severity": "blocker", "claim": "naïve read",
"criterion": 1, "file": "a.py", "line": 3, "fixes": "build"},
{"severity": "note", "claim": "the title runs long", "criterion": None,
"file": None, "line": None, "fixes": None}]}`, its keys in the model's
order. `V` is `D` with each finding's keys in reverse order. `T` is a text of prose, then an `<output>` block, then a fenced
`json` block. Each block holds one `scope` blocker, and each parses. `F`
is ```` "```json\n" + json.dumps(D, indent=2, ensure_ascii=False) + "\n```\n" ````.
Every second turn returns or fails with text `T`. Every one that carries
an attempt carries `structured_output` `V`, cost 0.25, `s-2` and 2 turns,
unless its row says otherwise. The killed turn is the attempt
`run_agent` gives a turn cut before its result event. The double builds
it from the call it gets: no `session_id`, subtype `error`, 0 turns, no
`structured_output`, and a cost equal to the `last_cost_usd` that call
passed. It raises `AgentFailed("the agent produced no result event")`
with it.

| case | calls | `text`, `cost_usd`, `error`, `resets_at`, `session_id`, `num_turns` |
|---|---|---|
| first status none, second returns | 2 | `F`, 0.75, `None`, `None`, `s-2`, 9 |
| first status `allowed`, reset 9, the same second turn | 2 | the same |
| second returns `V` with its first `fixes` `typo` | 2 | `F` with `build` replaced by `typo`, and the rest as above |
| second returns with no `session_id` | 2 | `F`, 0.75, `None`, `None`, `s-1`, 9 |
| first returns no `session_id` | 1 | empty, 0.5, `no session to extract from`, `None`, `None`, 7 |
| second returns `rejected`, reset 9 | 2 | empty, 0.75, `None`, 9, `s-2`, 9 |
| second returns `rejected`, reset -5 | 2 | empty, 0.75, `None`, 1, `s-2`, 9 |
| second raises `AgentFailed("api_error")`, `rejected`, reset `"soon"` | 2 | empty, 0.75, `None`, 1, `s-2`, 9 |
| second raises `AgentFailed("cut")` with an attempt | 2 | empty, 0.75, `cut`, `None`, `s-2`, 9 |
| second raises `AgentFailed("gone")` with no attempt | 2 | empty, 0.5, `gone`, `None`, `s-1`, 7 |
| second is the killed turn | 2 | empty, 1.0, `the agent produced no result event`, `None`, `s-1`, 7 |
| first at cost 4.0, second the killed turn | 2 | empty, 5.0, `the agent produced no result event`, `None`, `s-1`, 7 |
| second raises `RuntimeError` | 2 | raises |

Each second call is asserted exactly. It passes the container and the
prompt `SPEC_REVIEW_EXTRACT_PROMPT`. Its options are the first call's,
with `max_budget_usd` set to 1.0 and `output_format` set to
`SPEC_REVIEW_FORMAT`. It passes `resume="s-1"`, and `last_cost_usd` of
0.5, or 1.0 after the first turn at 4.0. It passes no other keyword. The witness also asserts
`scope` appears nowhere in the session's `text`. So every row with a
value is the case where the text's blocks and the value disagree.

It then reads the format itself. It asserts `SPEC_REVIEW_FORMAT` equals
`{"type": "json_schema", "schema":
_SpecReviewFindings.model_json_schema()}`. The schema's root `type` is
`object`, its `required` is `["findings"]`, and its `additionalProperties`
is false. It follows the `$ref` under `findings.items` into `$defs`. That
schema's properties are `severity`, `claim`, `criterion`, `file`, `line`
and `fixes`, in order, and all six are required. Its
`additionalProperties` is false. `severity`'s `enum` is `blocker`,
`concern`, `note`. Each of `criterion`, `file`, `line` and `fixes` has
an `anyOf` that holds `{"type": "null"}`. No `enum` or `const` appears
anywhere in `fixes`' schema. These fail it:

- the tags read from the first turn's text, or `text` set to it
- `text` read from the second turn's `<output>` or `json` block, alone or
  where the value is present, which carries `scope`
- the raw value dumped without `model_dump`, which keeps `V`'s reversed
  key order
- `json.dumps` with no `indent=2`, or with `ensure_ascii` left true,
  which escapes the `ï`
- `text` with no fence, or the fence with no trailing newline
- no `output_format` on the second call, or one built by hand
- a `Literal` of the tags on `fixes`, which refuses `typo`
- the four fields typed without null, as `_Reported` types `file` and
  `line` (`saffron/phases/review.py:67-68`), which refuses the note and
  drops the null branch
- the extraction turn run at `SPEC_REVIEW_BUDGET_USD`, 6.0
- `last_cost_usd` of the first turn's cost uncapped, which charges the
  killed turn 4.0 after the first at 4.0
- a killed turn's cost dropped from the sum
- a root that is not an object, such as a bare list of findings
- no `resume`, or `resume` of `None`, which opens a fresh session
- no `last_cost_usd`, or the extraction turn's cost alone
- `REVIEW_PROMPT`, `EXTRACTION_PROMPT` or the system prompt as the second
  turn's prompt
- a second call after a first turn with no `session_id`
- a rejected second turn read as an error, or its value kept
- the first turn's `session_id` kept where the second carries one

**Criterion 3's witness** writes a template into a `tmp_path` prompts
directory, as `spec-review.md`: ``"G\n{gates}\nP\n{protected}\nE\n{elevate_on}\nC\n{ceilings}\nT\n{tags}\n"``.
It builds `Policy` directly, never through `load_policy`, so no gate
executable is needed. The first policy declares `tests` then `lint`,
with `lint` not blocking. Its `protected` is `uv.lock` then
`docs/{a,b}.md`, and its `elevate_on` is `saffron/ledger.py`. It sets
`size._CEILINGS["feature"]` to 2999 with `monkeypatch.setitem`. It asserts
the whole output, exactly.

```
G
- `tests`
- `lint` (advisory)
P
- `uv.lock`
- `docs/{a,b}.md`
E
- `saffron/ledger.py`
C
- `bug`: 1300 changed tokens
- `feature`: 2999 changed tokens
- `refactor`: 4200 changed tokens
- any other type: 4200 changed tokens
T
- `scope`
- `build`
- `witness`
```

It then asserts `Policy()` gives `none` for the first three slots, the
same last two blocks, and the same text. It asserts `SPEC_REVIEW_PROMPT`
is `spec-review.md`. It patches `spec_review.SPEC_REVIEW_TAGS` to
`("x", "y")` with `monkeypatch.setattr`, and the `T` block becomes two
lines, `x` then `y`. Last, it rewrites the template file and calls
again, and the output follows the new text. These fail it:

- gates or lists sorted, which moves `tests` and `uv.lock`
- the advisory mark dropped, or put on a blocking gate
- an empty list filled with an empty string
- the ceilings written out by hand, which misses 2999
- the default ceiling left out
- the tags written into the template in place of the slot, or spelled
  in the fill, which misses `x` and `y`
- the tags copied into a second constant, or bound to a default argument
  at import, which misses `x` and `y`
- the values substituted and the result then formatted, which fails on
  `{a,b}`
- the template read once at import

**Criterion 4's witness** fills the real template with the first
policy from criterion 3's witness, without the `setitem`. It asserts each of the five rendered blocks
appears in the result, and no `{gates}`, `{protected}`, `{elevate_on}`,
`{ceilings}` or `{tags}` is left. It reads both files' raw text,
collapses each run of whitespace to one space, and asserts each file's
sentence verbatim. It asserts each of the three closing lines is a whole
line of `SPEC_REVIEW_EXTRACT_PROMPT.splitlines()`. That REBUT test
checks two of the three, and this witness checks all three. It asserts
`artifacts.EXTRACTION_PROMPT` is not in that constant, and `{extraction}`
is not in the raw file. It lowers both sides and checks each of the
seventeen strings against each file. These fail it:

- a review prompt with no sentence tagging an unmeasurable witness, or
  one worded otherwise
- an extraction prompt that nulls `fixes` on a concern, or tells the
  turn to judge a tag from the prose
- an extraction prompt that keeps the `{extraction}` slot, which brings
  in the `<output>` rules
- the three closing lines run together on one line
- a prompt that names this repo's tools, as the hand path's agent file
  does
- a prompt that calls the session "the reviewer"

**Criterion 5's witness** uses criterion 2's double, first turn, `D`,
`V`, `T` and `F`. `S` is `json.dumps(V)`, a string. Every second turn
carries text `T`, cost 0.25, `s-2` and 2 turns. Every third turn that
carries an attempt carries text `T`, cost 0.25, `s-3` and 2 turns. The
table names each turn's `structured_output`, and rows differ only as
they say.

| second's value | third | calls | `text`, `cost_usd`, `error`, `resets_at`, `session_id`, `num_turns` |
|---|---|---|---|
| `None` | returns `V` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `V` with no `claim` in its first finding | returns `V` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `V` with severity `critical` | returns `V` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `V` with a key `note` added to its first finding | returns `V` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `S` | returns `V` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `None`, no `session_id` | returns `V` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `None` | returns `None` | 3 | empty, 1.0, `not the schema: the turn returned no structured output`, `None`, `s-3`, 11 |
| `None` | returns `S` | 3 | empty, 1.0, starts `not the schema: `, `None`, `s-3`, 11 |
| `None` | returns `V` with no `session_id` | 3 | `F`, 1.0, `None`, `None`, `s-2`, 11 |
| `None` | returns `rejected`, reset 9 | 3 | empty, 1.0, `None`, 9, `s-3`, 11 |
| `None` | raises `AgentFailed("api_error")`, `rejected`, reset `"soon"` | 3 | empty, 1.0, `None`, 1, `s-3`, 11 |
| `None` | raises `AgentFailed("cut")` with an attempt | 3 | empty, 1.0, `cut`, `None`, `s-3`, 11 |
| `None` | raises `AgentFailed("gone")` with no attempt | 3 | empty, 0.75, `gone`, `None`, `s-2`, 9 |
| `None` | the killed turn | 3 | empty, 1.0, `the agent produced no result event`, `None`, `s-2`, 9 |
| `None`, cost 3.0 | the killed turn | 3 | empty, 4.5, `the agent produced no result event`, `None`, `s-2`, 9 |
| `None` | raises `RuntimeError` | 3 | raises |

Each third call is asserted exactly. After `None` its prompt is
`"not the schema: the turn returned no structured output\n\n" +
SPEC_REVIEW_EXTRACT_PROMPT`. After a refused value it starts `not the
schema: ` and ends `"\n\n" + SPEC_REVIEW_EXTRACT_PROMPT`. It carries the
second call's options, `output_format` included, and `resume="s-2"`, or
`"s-1"` where the second carries no `session_id`. It carries
`last_cost_usd` of 0.25, or 1.0 after the second at 3.0, and no other
keyword. No row makes a fourth call,
and `scope` appears in no session's `text`. The first row is `SA-0141`'s
fallback case: a null value beside a text whose blocks parse. These fail
it:

- no re-ask, which routes `None` to `error` after two calls
- a second re-ask, which makes a fourth call on `None` then `None`
- a fallback to `T`'s `<output>` or `json` block on a null value,
  which makes two calls and carries `scope`
- `json.loads` of a string value before validation, which accepts `S`
  after two calls
- `severity` typed as a plain string, which accepts `critical`
- other keys allowed, which accepts `note`
- the error or `SPEC_REVIEW_EXTRACT_PROMPT` left out of the re-ask's
  prompt
- `EXTRACTION_PROMPT` in place of `SPEC_REVIEW_EXTRACT_PROMPT`
- a re-ask without `output_format`, or with the first call's options
- a re-ask with no `resume`, or `resume` of the first turn's id
- the re-ask's cost or turns left out of the sums
- `last_cost_usd` of the second turn's cost uncapped, which charges the
  killed re-ask 3.0
- a third turn's rejection read as an error

**The wrong-version lists are unmeasured**, but for the model. Nothing
below this spec's head is built. So no stand-in for the session or the
fill can run at the tree base. Each list is reasoned from the code it
names. A scratch copy of the two models ran at `71140772`. It gave the
schema criterion 2's witness reads, with a null branch on each of the
four fields. It refused `S`, `critical` and `note`. `model_dump` put
both of `V`'s findings back in `D`'s key order, so the text equalled `F`.
A copy with the four fields typed without null refused `V`, and its
`fixes` schema was a bare string.

**What the witnesses leave undriven.** A repo file named by a string
outside criterion 4's seventeen passes. So does a prompt that fills every
slot and reviews badly. The prompt's quality is measured on the first
stack night, as its budget is. No witness runs the real CLI with this
schema. The spike ran `SA-0141`'s two schemas and three others, each an
object root with `Literal` fields and a model nested under `$defs`.

**The `prose` gate** counts both new prompt files, and every new comment
and docstring. Write none with an em dash, a semicolon, a contraction,
the perfect tense, a hedge or a sentence over 25 words. Use no word from
`FILLER` (`.saffron/gates/prose.py:67-83`), such as `just` or `simply`.
Run
`python3 hooks/prose_limit.py --file <path>` on each prompt file. Keep
each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**The turn ceiling.** `max_turns` is 220. `SA-0133` hit its own
ceiling at 161 turns on a change of 1252 changed tokens, under half this
estimate. So 161 is a floor for a change this size, and 220 leaves room.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
estimate, in changed tokens, is about 3150, 105% of the ceiling. The
session's single-turn prototype for `SA-0156` measured 218 tokens in
`spec_review.py` and 264 in its witness. The second turn, the re-ask, the
fill and the constants add about 380 to the source. The two models, the
format and the validation add about 100 more, and the text parse they
replace takes about 25 away. The two extraction constants and the
capped `last_cost_usd` add about 35, so about 710. `SA-0141`'s whole
`rebut.py` change, two formats, `_validate` and two reads, measured 180.
`spec-review.md` at 60 lines runs about 370 to 550, at the 6.2 to 9.1
words a line of the system prompts in `saffron/agents/prompts/` (`wc
-lw`). The extraction prompt runs about 105. The five witnesses run about
1760 to 1960. They hold about 41 table cases and an exact 21-line block.
They also hold the schema's reads, the second finding and the killed-turn
double.
`tests/test_context.py` adds about 10. The range is 2950 to 3335. The
operator chose not to split it, and `size` stays advisory.
