---
id: SA-0160
title: A stack batch has no session that revises a spec, so a build or witness blocker can only escalate
type: feature
priority: 1
depends_on: [SA-0150]
touches:
  - saffron/spec_review.py
  - saffron/cli.py
  - saffron/agents/prompts/spec-writer.md
  - saffron/agents/prompts/turns/spec-writer-extract.md
  - tests/test_spec_review.py
  - tests/test_cli.py
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
  - saffron/batch.py
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
  - saffron/agents/*.py
  - saffron/agents/prompts/spec-review.md
  - saffron/agents/prompts/turns/spec-review-extract.md
  - saffron/agents/prompts/turns/extraction.md
  - tests/test_batch.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_policy.py
  - tests/test_session.py
  - tests/test_task.py
  - tests/test_review.py
budget_usd: 22
max_attempts: 3
max_turns: 180
pending_symbols:
  - saffron/cli.py::_stack_revise
  - saffron/spec_review.py::SPEC_WRITER_SESSION_USD
acceptance:
  - claim: >-
      `spec_review.run_spec_writer(container, *, system_prompt, prompt,
      agent)` calls `agent` with the container, the prompt, and
      `implement.agent_options` of that system prompt,
      `SPEC_WRITER_MAX_TURNS`, `SPEC_WRITER_BUDGET_USD` and
      `SPEC_SESSION_TOOLS`, and nothing else. A first turn that returns with
      a `session_id` and no rejected window gets one extraction turn. That
      call passes the same container, the options with
      `SPEC_WRITER_EXTRACT_BUDGET_USD` in place of the writer's budget, the
      prompt `context.turn_prompt("spec-writer-extract")`, `resume` of the
      first turn's `session_id` and `last_cost_usd` of its cost.
      `SPEC_WRITER_SESSION_USD` is the sum of the two budgets, and at most
      12.50. The result is a `SpecWriterSession`. Its text starts at the
      extraction turn's first opening output tag that optional whitespace
      and a `---` fence follow. It runs from that fence to the last closing
      output tag, stripped, plus one newline. Its `spec_sha` is
      `artifacts.hash_artifact` of that text, or `None` with no text. Its
      turns sum each turn that returned or failed with an attempt, and so
      does its cost. A failed extraction attempt with no `session_id` and 0
      turns carries no result event, and adds no cost. Its `session_id` is
      the last one any turn set. A turn whose rate-limit status is `rejected`, returned or
      raised, gives no text, no error and a `resets_at` shaped as
      `run_spec_review` shapes one, whatever block it holds. A turn that
      raises `implement.AgentFailed` gives its message as `error` and no
      text. An extraction turn with no such block gives an error and no
      text. A first turn with no `session_id` does too, and runs no
      extraction turn. Any other raise propagates. The witness drives each
      case, from either turn.
    witness: tests/test_spec_review.py::test_a_spec_writer_session_returns_the_extraction_turns_spec
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
      `SPEC_WRITER_EXTRACT_PROMPT` is
      `context.turn_prompt("spec-writer-extract")`, and holds
      `artifacts.EXTRACTION_PROMPT`, `frontmatter` and `code fence`. Neither
      raw file holds any of the fifteen strings `SA-0175`'s criterion 4
      lists. The witness checks each of those fifteen in each file,
      case-insensitively.
    witness: tests/test_spec_review.py::test_cores_spec_writer_prompts_fill_every_slot_and_name_no_repo_tool
  - claim: >-
      `cli._stack_revise(*, pinned, repo, out_dir)` returns a callable that
      takes a candidate, its layer, the spec's current text as
      `str | None`, and the text of a spec review. Building it reads
      nothing. Given a layer, it fetches the branch `scheduler._branch`
      names for the layer's spec id, from the pinned url into the pinned
      mirror, and seeds the cell at the fetched head. Given `None`, it
      fetches nothing and seeds the cell at the pinned `base_sha`. A fetch
      that raises `ParentGone` propagates, and no cell comes up. Each call
      exports `.saffron/` at the pinned `base_sha` into
      `out_dir / "spec-write" / <spec id>` and loads that export's policy.
      An export with no `policy.yaml` reads as an empty `Policy`. The
      system prompt is `spec_review.spec_writer_system_prompt` of that
      policy over `context.PROMPTS_DIR`. It is never read from the
      operator's checkout or the mirror's `HEAD`. The cell is
      `end_review.layer_cell` over `repo`, the pinned mirror, that export
      and its `thread_env`, called with `spec_session=True` (`SA-0169`), on
      `LayerFields` whose `branch` is the candidate's own. The prompt's
      first eight lines are exactly the lines the Problem lists, with the
      candidate's file name and the seeded tree filled in. It then holds
      the review text inside a pair of review tags, then the spec text
      inside a pair of spec tags. The agent is `implement.run_agent` bound
      to `spec_review.SPEC_WRITER_TIMEOUT_S`, 3600, and the candidate's
      spec id. Both turns run in that one cell, and the callable returns
      what `run_spec_writer` returns.
    witness: tests/test_cli.py::test_a_spec_revision_fills_cores_writer_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.3. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that an agent revises a queued spec for a witness or buildability
blocker, for a bounded number of rounds. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design.
Spec writing runs as a host-invoked session in a critic cell, seeded at the
tree the spec would be cut from
(`docs/superpowers/specs/2026-09-23-stack-batch-design.md:160-162`). Its
spec returns through the extraction turn and is hashed on arrival
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
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:195-196`).
The design record adds that this repo's `.claude/agents/spec-writer.md`
stays the hand path's own and differs from core's by design
(`docs/superpowers/specs/2026-09-23-stack-batch-design.md:164-168`). So
this spec writes `saffron/agents/prompts/spec-writer.md` and fills it from
the policy at the pinned `base_sha`, as `SA-0175` fills `spec-review.md`.
No policy key names it, and a batch is never refused for want of one.

**The writer's structured output keeps principle 18.** ADR 7 says "A spec
writer returns its spec through a separate extraction turn"
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:92-93`).
Criterion 1 already runs that turn. The host reads the spec only from the
extraction turn's block, never from the first turn's text or from `/work`.

**The session holds Bash.** The operator decided that the spec writer
session runs commands in its critic cell, as a hand draft does. It
measures any wrong-build list it adds with a throwaway script. The cell is
torn down after the session. `SA-0169` runs that Bash as an unprivileged
user. `SA-0156` measured three account lines that tell a session so, and
quotes them in its Problem. Core's writer prompt carries those same three
lines. The chain runs `SA-0168`, `SA-0169`, `SA-0175`, then `SA-0156`.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Revision rounds take two specs.** This first one builds the session,
core's writer prompt and the callable. `SA-0164` builds the `revise`
route, the rounds in `run_stack_batch`, the record of each revision, and
the wiring into `saffron batch --stack`. `SA-0161` and `SA-0165` then write
follow-up specs. They run the same session with core's writer prompt and a
user prompt of their own.

**What the tree base holds.** This spec's tree base is `SA-0150`'s head.
Below it the chain runs through `SA-0169`, `SA-0175`, `SA-0156` and
`SA-0150`. Every line number below was read at `18c72f36`, where no chain
code from `SA-0142` on exists. So `cli.py` and `spec_review.py` are cited
by symbol where the chain edits them. This spec consumes these names.

- From `SA-0143` and `SA-0144`: `cli.py` imports `scheduler._branch`.
- From `SA-0146` and `SA-0154`: `end_review.LayerFields`, with `spec_id`,
  `branch`, `pr_url`, `base`, `head` and `known`.
  `end_review.layer_cell(fields, *, repo, mirror, gates_dir, thread_env)`
  is a context manager. It seeds a critic cell at `fields.head`, yields its
  container, and always tears it down.
- From `SA-0169`: `layer_cell`'s `spec_session` keyword. With it, the
  session's `Bash` runs as an account that cannot write `/work`, and
  `layer_cell` checks that account in the cell it brings up.
- From `SA-0175`, in `saffron/spec_review.py`: `run_spec_review`,
  `UNREADABLE_RESET` of 1, and `SPEC_SESSION_TOOLS`, which is `Read`,
  `Glob`, `Grep` and `Bash`. A rejected window in `run_spec_review` gives
  no error and a `resets_at` of the clean `int` above 0, or
  `UNREADABLE_RESET`. `spec_review_system_prompt(policy, *, prompts_dir)`
  fills `{gates}`, `{protected}`, `{elevate_on}`, `{ceilings}` and
  `{tags}` in core's `spec-review.md`. `SPEC_REVIEW_PROMPT` is that file's
  name.
- From `SA-0156`: `cli._stack_review(*, pinned, repo, out_dir)`, whose
  callable exports `.saffron/` at the pinned `base_sha`, reads a missing
  `policy.yaml` as `Policy()`, and runs its review in a `layer_cell` with
  `spec_session=True`. This spec's callable follows its shape. Its
  Problem quotes the three account lines, verbatim.
- From `SA-0150`: the `spec_text` fact, and
  `Ledger.record_spec_text(task_id, *, origin, spec_id, path, text)`. A
  row's `spec_sha` is the SHA-256 of its text. This spec calls neither.

**How an extraction turn runs today.** REBUT asks for its fix, then resumes
the same session for the record. "Two turns, because §5.3 allows exactly one
way to produce a structured artifact" (`saffron/phases/rebut.py:164-165`).
The second call passes `resume` and `last_cost_usd`, and the costs of
both turns are summed (`saffron/phases/rebut.py:186-200`). A turn killed before its result event
raises `AgentFailed` with an attempt of no `session_id`, 0 turns and a cost
of `last_cost_usd` (`saffron/phases/implement.py:330-341`). So REBUT's
failed extraction adds the first turn's cost a second time. Its handler
adds the failed attempt's cost to the first turn's
(`saffron/phases/rebut.py:194-198`). This spec adds nothing for such an
attempt. `parse_output_block` returns the last non-greedy `<output>` block
(`saffron/agents/artifacts.py:27`, `saffron/agents/artifacts.py:196-202`).
A spec that quotes a closing tag loses its tail there, and a draft block or
a tag in prose moves its start. So this spec reads its own block.
`hash_artifact` is the SHA-256 of the text's bytes
(`saffron/agents/artifacts.py:205-206`). `context.turn_prompt(name)` reads
`prompts/turns/<name>.md` and fills its `{extraction}` slot with the shared
rules (`saffron/agents/context.py:156-171`). `tests/test_context.py` holds
every turn file to a constant that loads it
(`tests/test_context.py:413-429`), and lists the turns that carry the
shared rules (`tests/test_context.py:446-450`). `context.PROMPTS_DIR` is
the one locator for the prompt tree (`saffron/agents/context.py:21`).

**How a turn is bounded.** `agent_options` sets `max_budget_usd` per turn,
not per session (`saffron/phases/implement.py:97-140`). `AgentFailed`
carries the attempt of a turn that failed, or `None`
(`saffron/phases/implement.py:56-72`). `session.TURN_TIMEOUT_S` is 900
seconds (`saffron/cell/session.py:63`).

**How a policy is read from an export today.** `_protected_paths` reads a
base with no `policy.yaml` as one that declares nothing. Otherwise it
calls `load_policy` on the export (`saffron/cli.py:290-296`). The export clears
its destination first (`saffron/repos/mirror.py:196`).

## Problem

Build four things.

1. **The session.** In `saffron/spec_review.py`, add these.
   - `SpecWriterSession`, a frozen dataclass of `text: str`,
     `cost_usd: float`, `error: str | None`, `resets_at: int | None`,
     `session_id: str | None`, `num_turns: int` and
     `spec_sha: str | None`.
   - `SPEC_WRITER_MAX_TURNS` of 120, `SPEC_WRITER_BUDGET_USD` of 11.0,
     `SPEC_WRITER_EXTRACT_BUDGET_USD` of 1.5, `SPEC_WRITER_SESSION_USD` as
     their sum, and `SPEC_WRITER_TIMEOUT_S` of 3600.0.
   - `run_spec_writer`, as criterion 1 states. Read the block with a
     regular expression local to this module. It opens on the first
     `<output>` that optional whitespace and `---` follow, and reads
     greedily to the last `</output>`. It takes any prompt, so `SA-0161`
     can run it for a follow-up.
2. **The system prompt.** Add `SPEC_WRITER_PROMPT` and
   `spec_writer_system_prompt`, as criterion 2 states. Fill each slot with
   the lines `SA-0175`'s fill builds. Sharing that code within the module
   is the cell's choice. Fill the slots as `format` arguments, never by
   substituting text and formatting the result.
3. **The prompt files.** Write `saffron/agents/prompts/spec-writer.md`, as
   the notes below say. Add
   `saffron/agents/prompts/turns/spec-writer-extract.md`. It asks for the
   whole spec file, frontmatter first, and nothing else in the block. It
   forbids a code fence around the file, in words holding `code fence`. It
   ends with the `{extraction}` slot. Load it at import into
   `SPEC_WRITER_EXTRACT_PROMPT`, as `rebut.EXTRACT_PROMPT` is loaded
   (`saffron/phases/rebut.py:38`). Add `"spec-writer-extract"` to
   `tests/test_context.py`'s `TURN_PROMPTS` with that constant, and to the
   names its extraction-rules test lists.
   `test_every_turn_prompt_file_is_loaded_by_something` fails without the
   first.
4. **The callable.** In `saffron/cli.py`, add `_stack_revise`, as
   criterion 4 states. Export `.saffron/` with
   `git_mirror.export_saffron_dir` into `out_dir / "spec-write" / <spec
   id>`, as `_stack_review` does into its own directory. Load its policy
   with `load_policy`, or take `Policy()` where the export holds no
   `policy.yaml`. Build `LayerFields` as `_stack_review` does. The
   prompt's first eight lines are these, with `<name>` the candidate's
   file name and `<tree>` the seeded tree. The review and the spec text
   follow, each in its tags.

   ```
   review: the spec review between the review tags below.
   spec: .saffron/specs/<name>
   base: <tree>
   The checkout is a snapshot of the base.
   The text between the spec tags below is the spec's current text, and it replaces the file at that path.
   Keep the spec's id and its exact depends_on.
   Raise no budget_usd, max_turns or max_attempts.
   A follow-up's revision keeps its touches within its first text's touches.
   ```

   The last three lines state the rules `SA-0150`'s gate 0 holds a
   revision to. A queued spec's revision can still widen its `touches`.
   The account lines and the rule on a throwaway script live in the system
   prompt, so a follow-up's session reads them too. Reach
   `package_phase.fetch_parent_branch`, `git_mirror.export_saffron_dir`,
   `end_review.layer_cell`, `spec_review.run_spec_writer` and
   `implement.run_agent` through their modules at call time, since the
   witness replaces them there.

`_stack_revise` has no caller in `saffron/` until `SA-0164` wires it.
`SPEC_WRITER_SESSION_USD` has none until `SA-0164` reserves by it. So both
are `pending_symbols` entries.

## Out of scope

- **This repo's hand path.** `.claude/agents/spec-writer.md` stays as it
  is. Core never reads it.
- **`SA-0175`'s prompt and session.** This spec edits neither
  `spec-review.md` nor `spec-review-extract.md`, and changes nothing
  `run_spec_review` or `spec_review_system_prompt` does.
- **The route, the rounds and the wiring.** They are `SA-0164`'s. It adds
  `"revise"` to `spec_review_route`, calls the callable up to three times
  per spec, and passes it from `saffron batch --stack`. Every blocker still
  routes `escalate` here.
- **The record and the spend.** `SA-0164` records each session's attempt,
  as `SA-0155` records a review's. It records the text with `SA-0150`'s
  `record_spec_text`, whose `spec_sha` matches the session's. So
  `_stack_revise` takes no ledger, and `run_spec_writer` records nothing.
- **Parsing the revised text.** `SA-0150` runs `parse_spec`'s refusals and
  gate 0 again on a recorded text before its cell. The session returns the
  text as the block holds it.
- **A re-ask on a missing block.** `SA-0175`'s review re-asks once on a
  block that is not the schema. The writer's extraction turn gets none. A
  session with no block ends with an error, and `SA-0164` counts it.
- **The fresh review of a revision.** `SA-0164` has the next review read
  the revision beside the original.
- **A spec text of `None`.** The callable's type takes it, because
  `SA-0164` hands `None` before any revision exists. `SA-0164` builds the
  read of the queued file at the pinned `base_sha` for that case, and its
  witness drives it. No caller here passes `None`.
- **The session's report.** Only the extraction turn's block is kept. The
  first turn's report, with any finding it answered rather than applied,
  reaches no record. The next round's fresh review is the check on the
  revision (principle 15).
- **Follow-up specs.** `SA-0161` builds their user prompt and host logic
  around `run_spec_writer`, and reserves by `SPEC_WRITER_SESSION_USD`.
  `SA-0165` runs them with `spec_writer_system_prompt`.
- **REBUT's double charge.** Its failed extraction turn adds the
  attempt's cost (`saffron/phases/rebut.py:194-198`). A kill before the
  result event sets that cost to the first turn's. `saffron/phases/**`
  is forbidden here, so the delegate files it as its own backlog item.
- **Concurrent sessions.** They wait for per-cell network names
  (b-6a692d).
- **The vocabulary.** `CONTEXT.md` names the `spec-writer` agent only as a
  delegate's tool in a **Spec chain**. A spec writer session in a batch is
  new. Backlog item b-466005 files it by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base runs a spec
writer session, fills a writer prompt or builds a revision callable. So
each criterion declares a witness and no mutant, and `witness` reports
`skip` for each.

**Every witness fails with the source reverted.** Each calls or reads a
name this spec adds. Import each new name inside the test body. A
module-scope import makes the reverted run a collection error, which
`revert` reads as `skip`. The new `TURN_PROMPTS` entry reads
`spec_review` at module scope, and is not a declared witness.

**What `spec-writer.md` says.** It is core's, so it names no repo file,
tool or URL, and none of criterion 3's fifteen strings. That bars
`.saffron/` too, since `saffron/` is one of them. The user prompt names the
spec's path. Keep the file within 50 lines. It holds each of the four
slots once, and no other brace. It covers these, in words of its own.

- It addresses the session as "you", and never writes "the reviewer".
- You write one spec file: YAML frontmatter between `---` fences, then a
  body. Each acceptance criterion holds a claim and a witness test.
- The user prompt takes one of two forms. A `review:` line asks you to
  revise the spec it names against the review it quotes. Apply each
  blocker and concern that holds at the base, and keep the spec's
  purpose. A `context:` line asks for a new spec from the findings it
  gives.
- Each witness fails a plausible wrong build, and a claim over a set
  drives every member. New code declares a witness and no mutant.
- Every sentence about current code names a file and line you read at
  the base.
- Every file the change edits sits in `touches`, and none sits in
  `{protected}`. The size estimate stays under its type's ceiling in
  `{ceilings}`. The size check blocks when a changed path matches
  `{elevate_on}`.
- A line that ends in a colon, then `{gates}` on the lines below it, says
  which gates the repo declares.
- The three account lines `SA-0156` quotes, each on its own line and
  word for word. Then "Measure any list of wrong builds you add with a
  throwaway script." on its own line.
- You write no file that outlives the cell. The host asks for the whole
  spec in a later turn.

**Criterion 1's witness** calls `run_spec_writer` with the container `c-1`,
the system prompt `sys` and the prompt `p`. Its agent double is one small
class that pops the next turn of the case's script, returns or raises it,
and records each call. Each turn is an `AttemptResult` with `session_id`
`s-1`, 7 turns and text `t`, unless its row says otherwise. `spec` is
`---\nid: SY-1\n---\nbody quotes <output>a</output> here\n`. The draft turn
returns text `<output>draft</output>` at cost 0.5. Three extraction turns
return `spec` at cost 0.25, with `session_id` `s-2`.

- final: `x <output>\n` plus `spec` plus `\n  </output>`
- prose: `I emit one <output> next.\n<output>\n` plus `spec` plus
  `</output>`
- drafted: `<output>draft</output>\n<output>\n` plus `spec` plus
  `</output>`

The killed turn is the attempt `run_agent` gives a turn cut before its
result event: no `session_id`, subtype `error`, 0 turns and cost 0.5.

| first turn | extraction turn | text, cost, error holds, `resets_at`, `session_id`, turns |
|---|---|---|
| draft | final | `spec`, 0.75, none, `None`, `s-2`, 14 |
| draft | prose | `spec`, 0.75, none, `None`, `s-2`, 14 |
| draft | drafted | `spec`, 0.75, none, `None`, `s-2`, 14 |
| draft | raises `AgentFailed` with the killed turn | empty, 0.5, `no result event`, `None`, `s-1`, 7 |
| draft | raises `AgentFailed("api_error")` with 7 turns and cost 0.5 | empty, 1.0, `api_error`, `None`, `s-1`, 14 |
| status `allowed`, reset 9, cost 0.5 | final | `spec`, 0.75, none, `None`, `s-2`, 14 |
| status `rejected`, reset 1755800000, cost 0.25 | none | empty, 0.25, none, 1755800000, `s-1`, 7 |
| raises `AgentFailed("api_error")`, `rejected`, reset `"soon"`, cost 0.125 | none | empty, 0.125, none, 1, `s-1`, 7 |
| draft | `rejected`, reset 1755800000, cost 0.0625, the final text | empty, 0.5625, none, 1755800000, `s-1`, 14 |
| draft | raises `AgentFailed("api_error")`, `rejected`, no reset, cost 0.0625 | empty, 0.5625, none, 1, `s-1`, 14 |
| raises `AgentFailed("idle bound")`, text `<output>x</output>`, cost 0.0625 | none | empty, 0.0625, `idle bound`, `None`, `s-1`, 7 |
| raises `AgentFailed("no result")` with no attempt | none | empty, 0.0, `no result`, `None`, `None`, 0 |
| draft | raises `AgentFailed("api_error")`, text `<output>partial</output>`, cost 0.125 | empty, 0.625, `api_error`, `None`, `s-1`, 14 |
| draft | raises `AgentFailed("idle bound")`, `session_id` `None`, cost 0.125 | empty, 0.625, `idle bound`, `None`, `s-1`, 14 |
| draft | raises `AgentFailed("no result")` with no attempt | empty, 0.5, `no result`, `None`, `s-1`, 7 |
| draft | text `no block`, cost 0.25 | empty, 0.75, `<output>`, `None`, `s-1`, 14 |
| draft | text `<output>` then two spaces and a newline, then `</output>`, cost 0.25 | empty, 0.75, `<output>`, `None`, `s-1`, 14 |
| returned with no `session_id`, cost 0.5 | none | empty, 0.5, `session_id`, `None`, `None`, 7 |

"none" in the second column means the case asserts one call. Each other case
asserts two. The first call is exactly `c-1`, `p` and the options with
`SPEC_WRITER_BUDGET_USD`, with no other keyword. The second is `c-1`,
`context.turn_prompt("spec-writer-extract")`, the options with
`SPEC_WRITER_EXTRACT_BUDGET_USD`, `resume` `s-1` and `last_cost_usd` 0.5,
with no other keyword. Each case asserts `spec_sha` is the SHA-256 of the
expected text, or `None` where the text is empty. It asserts
`SPEC_WRITER_SESSION_USD` is the sum of the two budgets and at most 12.50.
Each rejected case asserts `type(resets_at) is int`. Last, a
`RuntimeError` from the first turn, and one from the extraction turn, each
propagate.

These fail it, each measured:

- one turn, with the text read from the first turn
- the last block alone, as `parse_output_block` reads it
- the first block alone, read non-greedy, or the whole turn text
- a block from the first opening tag with no fence required
- a block from the last opening tag, as `rpartition` reads it
- an anchored block read to the first closing tag
- the block not stripped, or no newline appended
- an extraction turn not resumed, or with no `last_cost_usd`
- the writer's budget on the extraction turn, or the session sum on the
  writer turn
- an extraction budget that puts the session above 12.50
- an extraction turn after a rejected first turn
- the extraction turn's cost dropped, or a failed turn's cost dropped
- a killed extraction turn's cost added
- every extraction attempt with no `session_id` skipped, whatever its turns
- a failed extraction skipped for a cost equal to the first turn's
- a rejection read from the first turn only, or from a returned turn only
- the block parsed before the rejection is read
- `stop_on_rejected` around the agent
- `REVIEW_TOOLS`, `IMPLEMENT_TOOLS`, or the review's turn ceiling
- every exception caught
- the failure's message kept as `error` on a rejected turn
- a failed extraction turn answered with the first turn's block
- no check for a missing `session_id`, which resumes nothing
- the first turn's `session_id`
- the last attempt's `session_id`, `None` included
- the last turn's turn count alone
- `artifacts.EXTRACTION_PROMPT` as the extraction turn's prompt
- no `spec_sha`, a hash of the text before its newline, a hash of the
  whole turn text, or a hash of empty text

**Criterion 2's witness** writes one template into a `tmp_path` prompts
directory, as both `spec-review.md` and `spec-writer.md`:
``"G\n{gates}\nP\n{protected}\nE\n{elevate_on}\nC\n{ceilings}\n"``. It
builds `Policy` directly, never through `load_policy`. The first policy is
`SA-0175`'s criterion 3 witness's: `tests` then `lint`, with `lint` not
blocking, `protected` `uv.lock` then `docs/{a,b}.md`, and `elevate_on`
`saffron/ledger.py`. It sets `size._CEILINGS["feature"]` to 2999 with
`monkeypatch.setitem`. It asserts `SPEC_WRITER_PROMPT` is
`spec-writer.md`. For the first policy and for `Policy()`, the writer's
fill equals `spec_review_system_prompt` of the same policy over the same
directory. The first policy's fill holds ``- `lint` (advisory)``,
``- `docs/{a,b}.md` `` and ``- `feature`: 2999 changed tokens``. Last, it
rewrites `spec-writer.md` alone as ``"W\n{gates}\n"``, and the writer's
fill is exactly ``"W\n- `tests`\n- `lint` (advisory)\n"``. These fail it:

- `SPEC_REVIEW_PROMPT` read in place of `SPEC_WRITER_PROMPT`
- the template read once at import, or from `context.PROMPTS_DIR`
- gates or lists sorted
- an empty list filled with an empty string, not `none`
- the ceilings written out by hand, which misses 2999
- the values substituted and the result then formatted, which fails on
  `{a,b}`

**Criterion 3's witness** fills the real template with criterion 2's
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
`SPEC_WRITER_EXTRACT_PROMPT` equals
`context.turn_prompt("spec-writer-extract")`, and holds
`artifacts.EXTRACTION_PROMPT`, `frontmatter` and `code fence`. It lowers
both raw files and checks each of the fifteen strings against each. These
fail it. The first was measured on the old turn file, and the rest are
reasoned.

- a turn file that does not forbid a code fence
- a template that leaves a slot out, or spells a stray brace
- an account line reworded, joined to another line, or left out
- the account lines in the user prompt alone, where a follow-up's
  session never reads them
- a writer prompt that names this repo's tools or `.saffron/`, as the hand
  path's agent file does

**Criterion 4's witness** follows `SA-0156`'s criterion 1 witness, and
reuses the helpers it adds to `tests/test_cli.py`. It builds a git
repository in `tmp_path` as the mirror, with `_git` and `_rev_parse`. It
has three commits. `bare` holds `.saffron/README` and no `policy.yaml`.
`base` holds `.saffron/policy.yaml` with `thread_env` `X: base` and
`protected` `base/**`. `head` changes them to `X: head` and `head/**`. The
`repo` passed holds its own `.saffron/policy.yaml`, with `X: checkout` and
`checkout/**`. It replaces these through `monkeypatch`.

- `package.fetch_parent_branch` records `(mirror, url, branch)`. It
  raises `ParentGone` for `saffron/SY-8`, and returns `"d" * 40` for the
  rest.
- `session.cell_up` records its keywords and adds its container to
  `created`. `session.cell_down` records its keywords.
  `runtime.remove_container` returns `None`.
- `end_review.layer_cell` is wrapped by a spy that records its fields and
  keywords and calls the original.
- `session.assert_bash_is_unprivileged`, which `SA-0169`'s `layer_cell`
  runs with `spec_session=True`, replaced with a recorder of its
  container. The fake container would make a correct build raise.
- `implement.run_agent` declares `spec_id` and `timeout_s` as keywords
  with no default. It records each call. For `SY-2` it returns a rejected
  turn at cost 0.25 whose reset is `"soon"`. For a call that resumes, it
  returns text `<output>\n---\nid: SY-1\n---\nrevised\n</output>`, cost
  0.25 and 1 turn. For the rest it returns text `report`, cost 0.5, `s-1`
  and 7 turns.

The witness pins `base` and builds the callable. It asserts no
`out_dir / "spec-write"` exists yet. It calls the callable three times.
`SY-1` has no layer, the spec text `spec one\n` and the review `review
one`. `SY-2`, whose `depends_on` is `SY-9`, is on the layer `SY-7`, with
`spec two\n` and `review two`. `SY-3` is on the layer `SY-8`, which raises
`ParentGone`. It asserts:

- `SY-1`'s session is `---\nid: SY-1\n---\nrevised\n`, 0.75, no error,
  no reset, `s-1` and 8 turns. `SY-2`'s is empty text, `resets_at` 1, no
  error, cost 0.25.
- the fetches are `saffron/SY-7` then `saffron/SY-8`, on the pinned
  mirror and url.
- two `cell_up` calls, seeded at `base` then `"d" * 40`, and two
  `cell_down` calls. Each has `repo`, the pinned mirror and `thread_env`
  `{"X": "base"}`. Its `gates_dir` is `out_dir / "spec-write" / <spec
  id>`, and its `policy.yaml` holds `X: base`.
- two `layer_cell` calls, each with `spec_session=True`, on fields whose
  `branch` is `saffron/SY-1` then `saffron/SY-2`.
- two unprivileged checks, one per cell, each on the container its
  `cell_up` got.
- three agent calls: `SY-1`, then `SY-1` resuming in the same container,
  then `SY-2`. The resumed call's prompt is the extraction turn's, with
  `SPEC_WRITER_EXTRACT_BUDGET_USD`. Every call's `timeout_s` is
  `SPEC_WRITER_TIMEOUT_S`.
- each first call runs in the container its `cell_up` got. Its system
  prompt equals `spec_writer_system_prompt` of `load_policy` over that
  `gates_dir`, with `prompts_dir=context.PROMPTS_DIR`. It holds
  `` `base/**` ``, and neither `head/**` nor `checkout/**`. The prompt's
  first eight lines equal the Problem's list, with `<id>-x.md` and the
  seeded tree filled in. It holds no part of `tmp_path`. The text
  `<review>`, the review text, `</review>`, `<spec>`, the spec text and
  `</spec>` appear in that order. The options hold `SPEC_SESSION_TOOLS`,
  `SPEC_WRITER_MAX_TURNS` and `SPEC_WRITER_BUDGET_USD`.

Last, it pins `bare`, builds a second callable, and calls it for `SY-4`
with no layer. The system prompt equals `spec_writer_system_prompt` of
`Policy()`, and the cell's `thread_env` is empty. These fail it:

- the policy loaded from `repo`, or exported at the mirror's `HEAD`
- a prompts directory other than `context.PROMPTS_DIR`
- `spec_review_system_prompt` in place of the writer's
- a base with no `policy.yaml` refused, or read from `repo` instead
- the cell seeded at `base_sha` for every spec
- the branch taken from the candidate's `depends_on[0]`
- a `ParentGone` caught and the cell seeded at `base_sha`
- `.saffron/` exported into `out_dir / <spec id>`, the task's own
  directory, or into `out_dir / "spec-review"`
- the export run at build time, before any call
- the export's absolute path in the prompt
- `layer_cell` called without `spec_session=True`
- the layer's branch in the fields, in place of the candidate's
- the turn bound left at `session.TURN_TIMEOUT_S`, no `spec_id`, or an
  empty `thread_env`
- the review and the spec text swapped, or either left out
- a prompt that opens with `spec:`
- no sentence that the spec text replaces the file
- no line on the id and `depends_on`, the ceilings, or `touches`
- a paraphrase of the ceilings line
- `run_spec_review` called in place of `run_spec_writer`
- `stop_on_rejected` around the agent

**How the lists were measured.** A throwaway prototype ran on 2026-09-24,
and after each of the two reviews. Its tree was `SA-0156`'s prototype,
`24e8152f`. It built an earlier shape of this spec, whose prompt came from
a file the policy named. Criterion 1 and its list are unchanged from it.
The right build passed its witness, and each wrong version listed as
measured was applied as a text edit and failed it. Criteria 2 to 4 changed
when ADR 7 made the prompt core's. Their lists are unmeasured in the new
shape, and so are their witnesses' reverted runs.

**What the witnesses leave undriven.**

- A raise from the export, the policy load or `layer_cell` inside the
  callable. Each propagates, and `SA-0164` counts the raise.
- A base whose `policy.yaml` is present and broken. The load raises
  `PolicyError`, and the callable raises with it.
- A block whose text is not a spec. `SA-0150`'s `parse_spec` refuses it at
  run time.
- A draft block that itself opens on a `---` fence, before the real
  one. The read starts at the draft and runs to the last closing tag. The
  extraction prompt asks for one block, and `parse_spec` refuses the
  joined text at run time.
- A writer prompt that names a repo file by a string outside the fifteen.
  So does one that fills every slot and writes badly. Its quality is
  measured on the first stack night.

**The ceilings.** The backtest's 39 spec reviews cost $71.38, a mean of
$1.83 (`docs/evidence/2026-09-14-spec-reviewer-backtest.md:174`). Design
section 3 measures writing at about six times a review
(`docs/superpowers/specs/2026-09-23-stack-batch-design.md:222-223`). So
`SPEC_WRITER_BUDGET_USD` is 11.0, six times that mean. The chain's token
tables put a draft at 1.4 to 2.0 times a review
(`docs/evidence/2026-09-23-spec-chain-feedback.md:69-86`). So 11.0 is three
to four times a draft's estimated mean. The extraction turn writes one
spec out on a context already cached. `SPEC_WRITER_EXTRACT_BUDGET_USD` of
1.5 is reasoned from that, not measured. It keeps
`SPEC_WRITER_SESSION_USD` at 12.50, the most `SA-0161`'s sub-cap allows.
That sum is best effort. `max_budget_usd` bounds each call, and no session
was ever seen reaching it. So a sibling reserves by
`SPEC_WRITER_SESSION_USD` as a bound on its plan, not as a hard cap.
`SPEC_WRITER_MAX_TURNS` of 120 is a third above `SA-0175`'s 90.

**The turn bound.** `SA-0165`'s writer measured 79 hand `spec-writer`
transcripts. Their active time had a median of 1396 seconds, and 21
sessions ran past 2700 seconds. Those ran `make check` and prototypes
too, as this session can. `SPEC_WRITER_TIMEOUT_S` is 3600. The callable
binds it for both turns, and the extraction turn ends far sooner.

**The `prose` gate** counts both new prompt files, and every new comment
and docstring. Write none with an em dash, a semicolon, a contraction, the
perfect tense, a hedge or a sentence over 25 words. Use no word from
`FILLER` (`.saffron/gates/prose.py:67-83`), such as `just` or `simply`.
Run `python3 hooks/prose_limit.py --file <path>` on each prompt file. Keep
each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
estimate is about 2150 to 2500 changed tokens, 72% to 83% of the ceiling.
The earlier prototype, formatted by `ruff format`, measured
`saffron/spec_review.py` at 383 tokens and its turn file at 33, and those
carry over. The system prompt's fill adds about 60 to 110, so about 470.
`saffron/cli.py` measured 309 with a start refusal and a prompt-file read.
Both go, and so do six prompt lines, so about 200.
`spec-writer.md` at 50 lines runs about 310 to 460 tokens. That is 6.2 to
9.1 words a line, as the system prompts in `saffron/agents/prompts/` run
(`wc -lw`). The earlier witnesses measured 1331, with a policy witness and a
refusal witness that go. Criteria 1 and 4 keep about 1000, with the spy
and the account check's recorder added. Criteria 2 and 3 run about 150
each, and `tests/test_context.py` about 10. Keep the doubles shared and
the docstrings short.
