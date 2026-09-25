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
max_turns: 170
pending_symbols:
  - saffron/spec_review.py::run_spec_review
  - saffron/spec_review.py::spec_review_system_prompt
  - saffron/spec_review.py::SPEC_REVIEW_TIMEOUT_S
acceptance:
  - claim: >-
      `spec_review.run_spec_review(container, *, system_prompt, prompt,
      agent)` first calls `agent` with the container, the prompt, and
      `implement.agent_options` of that system prompt,
      `SPEC_REVIEW_MAX_TURNS`, `SPEC_REVIEW_BUDGET_USD` and
      `SPEC_SESSION_TOOLS`. It passes nothing else. `SPEC_SESSION_TOOLS`
      holds `Read`, `Glob`, `Grep` and `Bash`, and no other tool.
      `SPEC_REVIEW_MAX_TURNS` is 90, `SPEC_REVIEW_BUDGET_USD` 6.0,
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
      passes the container, `SPEC_REVIEW_EXTRACT_PROMPT`, the same options,
      `resume` of the first turn's `session_id` and `last_cost_usd` of its
      cost, and nothing else. The session's `text` is a `json` fence around
      what `artifacts.parse_output_block` returns for the second turn's text
      alone, once `json.loads` accepts that body. It holds nothing of the
      first turn's text. A second turn with no `<output>` block, or a body
      `json.loads` refuses, goes to criterion 5's one re-ask. Its cost and `num_turns` are
      the two turns' sums, and a failed turn with no attempt counts 0. Its
      `session_id` is the second turn's, or the first's where the second
      carries none. A first turn with no
      `session_id` gives `no session to extract from` as `error`, and no
      second call. A second turn whose status is `rejected`, returned or
      raised, gives no error and an empty `text`. Its `resets_at` follows
      the first turn's rule, driven with 9, -5 and `"soon"`. A second turn that
      raises `AgentFailed` otherwise gives its text as `error` and an empty
      `text`. Any other raise propagates. The witness drives each case, with
      a first status of none and of `allowed`.
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
      `SPEC_REVIEW_EXTRACT_PROMPT` is `context.turn_prompt("spec-review-extract")`,
      holds the shared extraction rules, and names `findings`, `severity`,
      `claim`, `fixes`, `blocker`, `concern`, `note` and `witness`. With
      whitespace runs collapsed to one space, the raw `spec-review.md`
      holds the sentence "A concern that a criterion's witness cannot be
      measured carries `witness`." The extraction prompt holds "Copy each
      finding's `fixes` exactly as your review gave it, and decide no tag
      from the prose." Neither file holds `.claude`, `CLAUDE.md`,
      `DESIGN.md`, `CONTEXT.md`, `driver.py`, `pytest`, `uv run`, `make
      check`, `ruff`, `prek`, `saffron/`, `docs/`, `/opt/`, `://` or `the
      reviewer`. The witness checks each of those fifteen strings in each
      file, case-insensitively.
    witness: tests/test_spec_review.py::test_cores_spec_review_prompts_fill_every_slot_and_name_no_repo_tool
  - claim: >-
      When the second turn's text has no `<output>` block, or `json.loads`
      refuses its last block's body, `run_spec_review` re-asks once. Its
      third call passes the container, the failure's message, a blank line
      and `SPEC_REVIEW_EXTRACT_PROMPT` as the prompt, the same options,
      `resume` of the last `session_id` a turn carried, and `last_cost_usd`
      of the second turn's cost. It passes nothing else. The message is
      `parse_output_block`'s, or `not JSON: ` and the parser's. A third
      turn that passes both checks gives its fenced body as `text`. One
      that fails either gives that message as `error` and an empty `text`,
      and there is no fourth call. A rejected third turn, returned or
      raised, gives no error, an empty `text`, and criterion 1's reset
      rule. A third turn that raises `AgentFailed` otherwise gives its text
      as `error`, and any other raise propagates. Cost and `num_turns` sum
      over every turn, and `session_id` is the last one a turn carried. The
      witness drives each case.
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
nothing of a repo" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:195-196`).
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
read at `2bb34a8d`, where none of their code exists. This spec consumes
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
tools add `Write`, `Edit` and `Bash` (`saffron/phases/implement.py:29`).
`AgentFailed` carries the attempt of a turn that failed, or `None`
(`:56-72`). `stop_on_rejected` raises `RateLimited` on a rejected window,
from a returned turn or a failed one (`saffron/cell/session.py:159-181`).
`terminal_for_rate_limit` reads the status (`:235-238`).
`_resets_at_fields` passes any clean `int`, 0 and negatives included, and
turns anything else into `None` (`:150-156`).

**How an extraction turn runs today.** `rebut.run_rebuttal` runs the
work turn, then resumes the same session with an extraction prompt. It
parses only the second turn's text (`saffron/phases/rebut.py:152-215`).
It passes `resume` and `last_cost_usd` on the second call (`:186-193`).
Its extraction prompt is a turn prompt whose `{extraction}` slot
`context.turn_prompt` fills with the shared rules
(`saffron/agents/prompts/turns/rebut-extract.md`,
`saffron/agents/context.py:156-171`). `parse_output_block` returns the
last `<output>` block, stripped, and raises `ValueError("no <output> block
in the response")` when there is none (`saffron/agents/artifacts.py:196-202`).

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

1. **The constants.** In `saffron/spec_review.py`, add
   `SPEC_REVIEW_MAX_TURNS` of 90, `SPEC_REVIEW_BUDGET_USD` of 6.0,
   `SPEC_REVIEW_TIMEOUT_S` of 1800.0, `UNREADABLE_RESET` of 1,
   `SPEC_SESSION_TOOLS`, `SPEC_REVIEW_PROMPT` and
   `SPEC_REVIEW_EXTRACT_PROMPT`. Define no tags. `SPEC_REVIEW_TAGS`
   already stands in the module, from `SA-0149`. Follow `REVIEW_TOOLS`' spelling for the
   tools, a list of names. Load the extraction prompt with
   `context.turn_prompt` at import, as `rebut.EXTRACT_PROMPT` is loaded.
   Name the 681-second measurement below in the timeout's comment.
2. **The session.** Add `run_spec_review`, as criteria 1, 2 and 5 state.
   Read the rate-limit status with `session.terminal_for_rate_limit`, on
   the returned attempt or the failed one. Call the agent directly, not
   through `stop_on_rejected`, so a rejected turn's cost reaches the
   session. Build the second call as `run_rebuttal` builds its own.
   Build the re-ask as `run_lens` builds its own, from the error and the
   extraction rules (`saffron/phases/review.py:222-227`, `:268-275`). §5.3
   feeds a schema failure back "twice, then reject" (`DESIGN.md:727`).
   This spec re-asks once, as `run_lens` does, and not twice. A session
   whose second answer is still not the schema has spent two turns on
   shape, and `SA-0149` counts its error as an abort.
3. **The system prompt.** Add `spec_review_system_prompt`, as criterion
   3 states. Fill the slots as `format` arguments, never by substituting
   text and formatting the result.
4. **The prompt files.** Write `saffron/agents/prompts/spec-review.md`
   and `saffron/agents/prompts/turns/spec-review-extract.md`, as the notes
   below say. Add `"spec-review-extract"` to `tests/test_context.py`'s
   `TURN_PROMPTS` and to the names its extraction-rules test lists.
   `test_every_turn_prompt_file_is_loaded_by_something` fails without it.

## Out of scope

- **The cell, the mint and the wiring.** They are `SA-0156`'s.
- **This repo's hand path.** `.claude/agents/spec-reviewer.md` stays as
  it is. Core never reads it.
- **Reading the tags.** `SA-0149` reads the block and routes on it. This
  spec only fixes what the block holds and where it comes from.
- **The review turn's prose.** It reaches no record. The block the
  extraction turn returns is what `SA-0155` records.
- **History rows for a ceilings check.** A batch has no ledger in the
  cell, so core's prompt carries no such check.
- **The writer's prompt.** `SA-0160` adds it beside this one.
- **The review's events.** `run_spec_review` passes the agent no `emit`.
  `run_agent`'s default prints each event, cut short
  (`saffron/phases/implement.py:199`, `saffron/events.py:669-675`). No
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

**What `spec-review.md` says.** It is core's, so it names no repo file,
tool or URL, and none of criterion 4's fifteen strings. Keep it within
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

**What `spec-review-extract.md` says.** It asks for one JSON object with
the key `findings`, one entry per finding in the review. Each entry holds
`severity` (`blocker`, `concern` or `note`), `claim`, `criterion` (a
number or null), `file`, `line` and `fixes`. It holds this sentence word
for word.

> Copy each finding's `fixes` exactly as your review gave it, and decide
> no tag from the prose.

`fixes` is null where the review gave no
tag. The extraction turn copies tags and judges none. `SA-0164`
routes on the tag the review gave. It ends with the
`{extraction}` slot. Write no `{word}` brace pair elsewhere in it, since
`test_a_loaded_turn_prompt_keeps_no_unfilled_slot` reads one as a slot.

**Criterion 1's witness** calls `run_spec_review` with the container
`c-1`, the system prompt `sys` and the prompt `p`. Its agent double
records each call's arguments and returns or raises the case's turn. Each
case asserts exactly one call, with those three and the options the claim
names, and no other keyword. `J` is a first-turn text of prose, then a
fenced `json` block with one `scope` blocker, then an `<output>` block
holding that same object. A build that parses the turns' texts joined
then finds `J`'s block.

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
- the turns and budget swapped, or either constant at another value
- every exception caught

**Criterion 2's witness** uses the same double, with a first turn that
returns text `J`, cost 0.5, `s-1` and 7 turns. `B` is
`json.dumps(obj, indent=2, ensure_ascii=False)` of one `findings` object
holding one `build` blocker whose claim is `naïve read`, with
`criterion` 1, `file` `a.py` and `line` 3. `X` is a second-turn text
holding two `<output>` blocks. The draft's body is `{"findings": []}`.
The last one is `<output>\n` + `B` + `\n</output>`. `F` is
```` "```json\n" + B + "\n```\n" ````.

| case | calls | `text`, `cost_usd`, `error`, `resets_at`, `session_id`, `num_turns` |
|---|---|---|
| first status none, second returns `X`, cost 0.25, `s-2`, 2 turns | 2 | `F`, 0.75, `None`, `None`, `s-2`, 9 |
| first status `allowed`, reset 9, the same second turn | 2 | the same |
| second returns `X` with no `session_id` | 2 | `F`, 0.75, `None`, `None`, `s-1`, 9 |
| first returns no `session_id` | 1 | empty, 0.5, `no session to extract from`, `None`, `None`, 7 |
| second returns `rejected`, reset 9 | 2 | empty, 0.75, `None`, 9, `s-2`, 9 |
| second returns `rejected`, reset -5 | 2 | empty, 0.75, `None`, 1, `s-2`, 9 |
| second raises `AgentFailed("api_error")`, `rejected`, reset `"soon"` | 2 | empty, 0.75, `None`, 1, `s-2`, 9 |
| second raises `AgentFailed("cut")` with an attempt | 2 | empty, 0.75, `cut`, `None`, `s-2`, 9 |
| second raises `AgentFailed("gone")` with no attempt | 2 | empty, 0.5, `gone`, `None`, `s-1`, 7 |
| second raises `RuntimeError` | 2 | raises |

Each second call is asserted exactly: the container, the prompt
`SPEC_REVIEW_EXTRACT_PROMPT`, the first call's options, `resume="s-1"`
and `last_cost_usd=0.5`, and no other keyword. Every second turn that
carries an attempt carries cost 0.25, `s-2` and 2 turns. The witness also asserts
`scope` appears nowhere in the session's `text`. These fail it:

- the tags read from the first turn's text, or `text` set to it
- the first `<output>` block taken, which fences `{"findings": []}`, or
  the body left unstripped
- the body parsed and written back with `json.dumps`, which loses the
  indent or the `ï` that `SA-0155` hashes as sent
- the turns' texts joined before the parse, which finds `J`'s block
- `text` set to the second turn's raw text, with no fence
- no `resume`, or `resume` of `None`, which opens a fresh session
- no `last_cost_usd`, or the extraction turn's cost alone
- `REVIEW_PROMPT`, `EXTRACTION_PROMPT` or the system prompt as the second
  turn's prompt
- a second call after a first turn with no `session_id`
- a rejected second turn read as an error, or its text kept
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
sentence verbatim. It lowers both sides and checks each of the fifteen
strings against each file. These fail it:

- a review prompt with no sentence tagging an unmeasurable witness, or
  one worded otherwise
- an extraction prompt that nulls `fixes` on a concern, or tells the
  turn to judge a tag from the prose
- a prompt that names this repo's tools, as the hand path's agent file
  does
- a prompt that calls the session "the reviewer"

**Criterion 5's witness** uses criterion 2's double, first turn and `X`.
`N` is a text with no `<output>` block. `Q` is `<output>{"findings":
[}</output>`. Every second turn carries cost 0.25, `s-2` and 2 turns, and
every third turn that carries an attempt carries cost 0.25, `s-3` and 2
turns, unless its row says otherwise.

| second | third | calls | `text`, `cost_usd`, `error`, `resets_at`, `session_id`, `num_turns` |
|---|---|---|---|
| `N` | returns `X` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `Q` | returns `X` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `N` with no `session_id` | returns `X` | 3 | `F`, 1.0, `None`, `None`, `s-3`, 11 |
| `N` | returns `N` | 3 | empty, 1.0, `no <output> block in the response`, `None`, `s-3`, 11 |
| `Q` | returns `Q` | 3 | empty, 1.0, starts `not JSON: `, `None`, `s-3`, 11 |
| `N` | returns `X` with no `session_id` | 3 | `F`, 1.0, `None`, `None`, `s-2`, 11 |
| `N` | returns `rejected`, reset 9 | 3 | empty, 1.0, `None`, 9, `s-3`, 11 |
| `N` | raises `AgentFailed("api_error")`, `rejected`, reset `"soon"` | 3 | empty, 1.0, `None`, 1, `s-3`, 11 |
| `N` | raises `AgentFailed("cut")` with an attempt | 3 | empty, 1.0, `cut`, `None`, `s-3`, 11 |
| `N` | raises `AgentFailed("gone")` with no attempt | 3 | empty, 0.75, `gone`, `None`, `s-2`, 9 |
| `N` | raises `RuntimeError` | 3 | raises |

Each third call is asserted exactly. After `N` its prompt is
`"no <output> block in the response\n\n" + SPEC_REVIEW_EXTRACT_PROMPT`.
After `Q` it starts `not JSON: ` and ends `"\n\n" +
SPEC_REVIEW_EXTRACT_PROMPT`. It carries the first call's options,
`resume="s-2"`, or `"s-1"` where the second carries no `session_id`, and
`last_cost_usd=0.25`, and no other keyword. No row makes a fourth call.
These fail it:

- no re-ask, which routes `N` to `error` after two calls
- a second re-ask, which makes a fourth call on `N` then `N`
- the error or the extraction rules left out of the re-ask's prompt
- `EXTRACTION_PROMPT` alone in place of `SPEC_REVIEW_EXTRACT_PROMPT`
- a re-ask with no `resume`, or `resume` of the first turn's id
- the re-ask's cost or turns left out of the sums
- a third turn's rejection read as an error

**The wrong-version lists are unmeasured.** Nothing below this spec's
head is built. So no stand-in for the session or the fill can run at the
tree base. Each list is reasoned from the code it names.

**What the witnesses leave undriven.** A repo file named by a string
outside criterion 4's fifteen passes. So does a prompt that fills every
slot and reviews badly. The prompt's quality is measured on the first
stack night, as its budget is.

**The `prose` gate** counts both new prompt files, and every new comment
and docstring. Write none with an em dash, a semicolon, a contraction,
the perfect tense, a hedge or a sentence over 25 words. Use no word from
`FILLER` (`.saffron/gates/prose.py:67-83`), such as `just` or `simply`.
Run
`python3 hooks/prose_limit.py --file <path>` on each prompt file. Keep
each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
estimate, in changed tokens, is about 2850, 95% of the ceiling. The
session's single-turn prototype for `SA-0156` measured 218 tokens in
`spec_review.py` and 264 in its witness. The second turn, the JSON check,
the re-ask, the fill and the constants add about 380 to the source, so
about 600.
`spec-review.md` at 60 lines runs about 370 to 550, at the 6.2 to 9.1
words a line of the system prompts in `saffron/agents/prompts/` (`wc
-lw`). The extraction prompt runs about 100. The five witnesses run about
1450 to 1650, with about 30 table cases and an exact 21-line block, and
`tests/test_context.py` about 20. The operator chose not to split it,
and `size` stays advisory.
