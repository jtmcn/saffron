---
id: SA-0160
title: A stack batch has no session that revises a spec, so a build or witness blocker can only escalate
type: feature
priority: 1
depends_on: [SA-0176]
touches:
  - saffron/spec_review.py
  - saffron/cli.py
  - tests/test_spec_review.py
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
  - saffron/agents/prompts/spec-writer.md
  - saffron/agents/prompts/turns/spec-writer-extract.md
  - saffron/agents/prompts/turns/spec-review-extract.md
  - saffron/agents/prompts/turns/extraction.md
  - tests/test_batch.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_policy.py
  - tests/test_context.py
  - tests/test_session.py
  - tests/test_task.py
  - tests/test_review.py
budget_usd: 24
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
      `SPEC_SESSION_TOOLS`, and nothing else, so those options carry no
      `output_format`. `SPEC_WRITER_MAX_TURNS` is
      the `int` 120, `SPEC_WRITER_BUDGET_USD` 17.0,
      `SPEC_WRITER_EXTRACT_BUDGET_USD` 1.5, `SPEC_WRITER_SESSION_USD` their
      sum, 18.5, and `SPEC_WRITER_TIMEOUT_S` 3600.0. A first turn that
      returns with a `session_id` and no rejected window gets one
      extraction turn. That call passes the same container,
      `SPEC_WRITER_EXTRACT_PROMPT`, and the options with
      `SPEC_WRITER_EXTRACT_BUDGET_USD` in place of the writer's budget,
      merged with `{"output_format": SPEC_WRITER_FORMAT}`. It passes
      `resume` of the first turn's `session_id`, and `last_cost_usd` of the
      smaller of the first turn's cost and `SPEC_WRITER_EXTRACT_BUDGET_USD`.
      The result is a `SpecWriterSession`. When
      `_SpecWriterReply.model_validate` accepts the extraction turn's
      `structured_output`, the text is the validated `spec`, stripped, plus
      one newline. It holds nothing of either turn's `text`. Its
      `spec_sha` is `artifacts.hash_artifact` of that text, or `None` with
      no text. Its
      cost and its turns sum every attempt a turn returned or failed with,
      a killed turn's included. Its `session_id` is the last one any turn
      carried. A turn whose rate-limit status is `rejected`, returned or
      raised, gives no text, no error and a `resets_at` of the clean `int`
      above 0 that `session._resets_at_fields` passes, or 1 otherwise,
      whatever value it holds. A turn that raises `implement.AgentFailed`
      otherwise gives its message as `error` and no text. A first turn with
      no `session_id` gives the error `no session to extract from`, the
      message `SA-0175`'s review session gives, no text and no extraction
      turn. An
      extraction turn whose `structured_output` is `None`, or a value
      `model_validate` refuses, goes to criterion 3's re-ask. Any other
      raise propagates. The witness drives each case, from either turn,
      and reset values of 10**20, 0, -5, `True`, a float, `None` and a
      string. One valid value carries padding, and one sits beside an
      `<output>` block in the turn's text that holds another spec.
    witness: tests/test_spec_review.py::test_a_spec_writer_session_returns_the_extraction_turns_spec
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
  - claim: >-
      When the extraction turn returns, with no rejected window, and its
      `structured_output` is `None` or a value
      `_SpecWriterReply.model_validate` refuses, `run_spec_writer` re-asks
      once. The failure's message is `not the schema: the turn returned no
      structured output` for `None`. For a refused value it is `not the
      schema: ` and the `ValidationError`'s text. Its third call passes the
      container, that message, a blank line and
      `SPEC_WRITER_EXTRACT_PROMPT` as the prompt, and the extraction turn's
      options, `output_format` included. It passes `resume` of the last
      `session_id` a turn carried, and `last_cost_usd` of the smaller of
      the extraction turn's cost and `SPEC_WRITER_EXTRACT_BUDGET_USD`. It
      passes nothing else. A third turn whose value passes gives the text
      criterion 1 builds from it. One whose value is `None` or refused
      gives its own message as `error` and an empty `text`, and there is
      no fourth call. A rejected third turn, returned or raised, gives no
      error, an empty `text` and criterion 1's reset rule. A third turn
      that raises `AgentFailed` otherwise gives its text as `error`, and
      any other raise propagates. Cost and turns sum every attempt, and
      `session_id` is the last one a turn carried. The witness drives each
      case, with `None`, `{}`, `{"spec": 3}`, a value with an extra key and
      a JSON string of a valid value. Each second turn's text beside them
      holds a valid spec in an `<output>` block.
    witness: tests/test_spec_review.py::test_a_spec_writer_re_asks_once_when_its_extraction_is_not_the_schema
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

**Core owns the writer's prompt, and `SA-0176` writes it.** ADR 7 makes
the spec prompts core's, in `saffron/agents/prompts/`
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:63-67`).
`SA-0176` adds `spec-writer.md`, its extraction turn prompt and the fill.
This spec runs them. It fills the system prompt from the policy at the
pinned `base_sha`, as `SA-0156` fills the review's. No policy key names
the prompt, and a batch is never refused for want of one.

**The writer's structured output keeps principle 18.** ADR 7 says "A spec
writer returns its spec through a separate extraction turn"
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:91-94`).
Criterion 1 runs that turn. The operator decided the turn asks through the
SDK's `output_format`, as REBUT's now does, and keeps one host re-ask. The
host reads the spec only from the extraction turn's `structured_output`,
never from either turn's text or from `/work`.

**The session holds Bash.** The operator decided that the spec writer
session runs commands in its critic cell, as a hand draft does. It
measures any wrong-build list it adds with a throwaway script. The cell is
torn down after the session. `SA-0169` runs that Bash as an unprivileged
user. `SA-0156` measured three account lines that tell a session so, and
quotes them in its Problem. `SA-0176`'s writer prompt carries those same
three lines.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Revision rounds take two specs, after the prompt.** `SA-0176` writes
core's writer prompt. This spec builds the session and the callable. `SA-0164` builds the `revise`
route, the rounds in `run_stack_batch`, the record of each revision, and
the wiring into `saffron batch --stack`. `SA-0161` and `SA-0165` then write
follow-up specs. They run the same session with `SA-0176`'s prompt and a
user prompt of their own.

**What the tree base holds.** This spec's tree base is `SA-0176`'s head.
Below it the chain runs through `SA-0169`, `SA-0175`, `SA-0156`,
`SA-0150` and `SA-0176`. Every line number below was read at `71140772`, where no chain
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
  `UNREADABLE_RESET`.
- From `SA-0176`, in `saffron/spec_review.py`:
  `spec_writer_system_prompt(policy, *, prompts_dir)`, which fills core's
  `spec-writer.md` from a `Policy`, and `SPEC_WRITER_EXTRACT_PROMPT`, the
  extraction turn's prompt. `_SpecWriterReply`, a model of one `str`
  field, `spec`, that forbids other keys. `SPEC_WRITER_FORMAT`, the
  `output_format` value built from that model's schema. The account lines
  and the rule on a throwaway script are in that system prompt.
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
way to produce a structured artifact" (`saffron/phases/rebut.py:185-186`).
§5.3 now also records the schema path. The pinned SDK's `output_format`
constrains the answer, and REBUT's turns use it (`DESIGN.md:731`). It stays
a separate turn. The second call passes `resume`, `last_cost_usd` and
`options | {"output_format": _REBUTTALS_FORMAT}`, and the costs of both
turns are summed (`saffron/phases/rebut.py:207-221`). It validates the
turn's `structured_output`, and gives `not the schema: the turn returned
no structured output` for `None` and `not the schema: ` with the
validation error for a refused value (`saffron/phases/rebut.py:72-86`).
`AttemptResult.structured_output` carries the result event's value whole
(`saffron/phases/implement.py:96-98`). The runner copies it into that
event unclipped (`images/agent_runner.py:130-132`). A turn killed
before its result event raises `AgentFailed` with an attempt of no
`session_id`, 0 turns and a cost of `last_cost_usd`
(`saffron/phases/implement.py:334-345`). A failed turn that reported 0
falls back to that same figure (`saffron/phases/implement.py:411-423`).
That fallback is §4.1's rule. "An attempt that burned $4 and then crashed
records $0 unless the supervisor falls back to the last good figure it
saw" (`DESIGN.md:343`). So this spec counts every failed attempt. It caps
the figure it passes at the next turn's own budget, since the first
turn's cost can run past ten times an extraction's. Salvage scales its fallback
for the same reason (`saffron/cell/session.py:2113-2119`).

**How a schema failure is retried.** §5.3 feeds a schema failure back
"twice, then reject" (`DESIGN.md:727`). The CLI already retries shape
inside the turn. The spike's unsatisfiable turn called its
`StructuredOutput` tool four times, then ended `success` with a null
value (`docs/evidence/2026-09-23-structured-output-spike.md:50-58`). So
a null reaching the host is past the CLI's own retries. REBUT re-asks
nothing, since its attempt is already made
(`saffron/phases/rebut.py:223-225`). This spec keeps one host re-ask as
a backstop. A writer session's value is its whole product, and one
extraction turn costs a fraction of the session before it. `SA-0175`'s review re-asks once too. A writer session whose second
answer is still not the schema has spent two turns on shape, and
`SA-0164` counts its error.

**How large a value the path carries.** The spike's last addendum is
headed "a whole spec as one string". It sent `output_format` for an
object of one string field, `spec`, on a resumed turn. It returned specs
of 40,153 and 45,945 characters, each identical to the expected text.
Each extraction turn
ran 130 to 150 seconds, since it writes the whole file as output. Each
extraction turn cost $0.40 or $0.41, and each whole session under $0.60.
One run each, on
the host and not in a cell. `SPEC_WRITER_TIMEOUT_S` of 3600 clears 150
seconds many times over. The idle bound of 300 seconds
(`saffron/cell/runtime.py:176`) is twice 150 seconds. Whether a
structured turn emits any event before its answer is unmeasured. The
addendum sits in
the working tree beside this revision and is cited by its heading.

`hash_artifact` is the SHA-256 of the text's bytes
(`saffron/agents/artifacts.py:205-206`). `context.PROMPTS_DIR` is the one
locator for the prompt tree (`saffron/agents/context.py:21`).

**How a turn is bounded.** `agent_options` sets `max_budget_usd` per turn,
not per session (`saffron/phases/implement.py:101-144`). `AgentFailed`
carries the attempt of a turn that failed, or `None`
(`saffron/phases/implement.py:57-73`). `session.TURN_TIMEOUT_S` is 900
seconds (`saffron/cell/session.py:63`).

**How a policy is read from an export today.** `_protected_paths` reads a
base with no `policy.yaml` as one that declares nothing. Otherwise it
calls `load_policy` on the export (`saffron/cli.py:290-296`). The export clears
its destination first (`saffron/repos/mirror.py:196`).

## Problem

Build two things.

1. **The session.** In `saffron/spec_review.py`, add these.
   - `SpecWriterSession`, a frozen dataclass of `text: str`,
     `cost_usd: float`, `error: str | None`, `resets_at: int | None`,
     `session_id: str | None`, `num_turns: int` and
     `spec_sha: str | None`.
   - `SPEC_WRITER_MAX_TURNS` of 120, `SPEC_WRITER_BUDGET_USD` of 17.0,
     `SPEC_WRITER_EXTRACT_BUDGET_USD` of 1.5, `SPEC_WRITER_SESSION_USD` as
     their sum, and `SPEC_WRITER_TIMEOUT_S` of 3600.0.
   - `run_spec_writer`, as criteria 1 and 3 state. Build the re-ask as
     `SA-0175`'s `run_spec_review` builds its own. Validate the value with
     `SA-0176`'s `_SpecWriterReply`, and word each failure as
     `rebut._validate` does. Sharing a helper within the module is the
     cell's choice. Read nothing from a turn's `text`. It takes any
     prompt, so `SA-0161` can run it for a follow-up.
2. **The callable.** In `saffron/cli.py`, add `_stack_revise`, as
   criterion 2 states. Export `.saffron/` with
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
- **Core's writer prompt.** `SA-0176` writes `spec-writer.md`,
  `spec-writer-extract.md` and `spec_writer_system_prompt`. This spec
  edits none of them.
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
  `spec` field stripped, plus one newline, and checks nothing inside it.
- **The fresh review of a revision.** `SA-0164` has the next review read
  the revision beside the original.
- **A spec text of `None`.** The callable's type takes it, because
  `SA-0164` hands `None` before any revision exists. `SA-0164` builds the
  read of the queued file at the pinned `base_sha` for that case, and its
  witness drives it. No caller here passes `None`.
- **The session's report.** Only the extraction turn's value is kept. The
  first turn's report, with any finding it answered rather than applied,
  reaches no record. The next round's fresh review is the check on the
  revision (principle 15).
- **Follow-up specs.** `SA-0161` builds their user prompt and host logic
  around `run_spec_writer`, and reserves by `SPEC_WRITER_SESSION_USD`.
  `SA-0165` runs them with `SA-0176`'s `spec_writer_system_prompt`.
- **Concurrent sessions.** They wait for per-cell network names
  (b-6a692d).
- **The vocabulary.** `CONTEXT.md` names the `spec-writer` agent only as a
  delegate's tool in a **Spec chain**. A spec writer session in a batch is
  new. Backlog item b-466005 files it by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base runs a spec
writer session or builds a revision callable. So
each criterion declares a witness and no mutant, and `witness` reports
`skip` for each.

**Every witness fails with the source reverted.** Each calls or reads a
name this spec adds. Import each new name inside the test body. A
module-scope import makes the reverted run a collection error, which
`revert` reads as `skip`.

**Criterion 1's witness** calls `run_spec_writer` with the container `c-1`,
the system prompt `sys` and the prompt `p`. Its agent double is one small
class that pops the next turn of the case's script, returns or raises it,
and records each call. Each turn is an `AttemptResult` with `session_id`
`s-1`, 7 turns, text `t` and no `structured_output`, unless its row says
otherwise. `spec` is `---\nid: SY-1\n---\nbody quotes <output>a</output>
here\n`, and `V` is `{"spec": spec}`. The draft turn costs 0.5. Its
`structured_output` is `{"spec": "---\nid: SY-8\n---\ndraft\n"}`, and its
text is that draft inside an `<output>` block. Three extraction turns cost
0.25, with `session_id` `s-2`.

- final: value `V`, text `t`
- padded: value `{"spec": "\n  " + spec + "\n\n"}`, text `t`
- conflicting: value `V`, text `<output>\n---\nid: SY-9\n---\nwrong\n</output>`

The killed turn is the attempt `run_agent` gives a turn cut before its
result event. The double builds it from the call it gets: no
`session_id`, subtype `error`, 0 turns, and a cost equal to the
`last_cost_usd` that call passed. It raises `AgentFailed("the agent
produced no result event")` with it. `R` stands for each of seven reset
values in turn. 1755800000 and `10**20` give themselves. `None`, `"soon"`,
`True`, 1755800000.0, 0 and -5 each give 1.

| first turn | extraction turn | text, cost, error holds, `resets_at`, `session_id`, turns |
|---|---|---|
| draft | final | `spec`, 0.75, none, `None`, `s-2`, 14 |
| draft | padded | `spec`, 0.75, none, `None`, `s-2`, 14 |
| draft | conflicting | `spec`, 0.75, none, `None`, `s-2`, 14 |
| draft | the killed turn | empty, 1.0, `no result event`, `None`, `s-1`, 7 |
| draft at cost 4.0 | the killed turn | empty, 5.5, `no result event`, `None`, `s-1`, 7 |
| draft | raises `AgentFailed("api_error")` with 7 turns and cost 0.5 | empty, 1.0, `api_error`, `None`, `s-1`, 14 |
| status `allowed`, reset 9, cost 0.5 | final | `spec`, 0.75, none, `None`, `s-2`, 14 |
| status `rejected`, reset `R`, cost 0.25 | none | empty, 0.25, none, what `R` gives, `s-1`, 7 |
| raises `AgentFailed("api_error")`, `rejected`, reset `R`, cost 0.125 | none | empty, 0.125, none, what `R` gives, `s-1`, 7 |
| draft | `rejected`, reset 1755800000, cost 0.0625, value `V` | empty, 0.5625, none, 1755800000, `s-1`, 14 |
| draft | `rejected`, reset -5, cost 0.0625, value `V` | empty, 0.5625, none, 1, `s-1`, 14 |
| draft | raises `AgentFailed("api_error")`, `rejected`, no reset, cost 0.0625 | empty, 0.5625, none, 1, `s-1`, 14 |
| raises `AgentFailed("idle bound")`, value `V`, cost 0.0625 | none | empty, 0.0625, `idle bound`, `None`, `s-1`, 7 |
| raises `AgentFailed("no result")` with no attempt | none | empty, 0.0, `no result`, `None`, `None`, 0 |
| draft | raises `AgentFailed("api_error")`, value `V`, cost 0.125 | empty, 0.625, `api_error`, `None`, `s-1`, 14 |
| draft | raises `AgentFailed("idle bound")`, `session_id` `None`, cost 0.125 | empty, 0.625, `idle bound`, `None`, `s-1`, 14 |
| draft | raises `AgentFailed("no result")` with no attempt | empty, 0.5, `no result`, `None`, `s-1`, 7 |
| returned with no `session_id`, cost 0.5 | none | empty, 0.5, `no session to extract from`, `None`, `None`, 7 |

"none" in the second column means the case asserts one call. Each other case
asserts two. The first call is exactly `c-1`, `p` and the options with
`SPEC_WRITER_BUDGET_USD`, with no other keyword, and its options hold no
`output_format` key. The second is `c-1`, `SPEC_WRITER_EXTRACT_PROMPT`,
the options with `SPEC_WRITER_EXTRACT_BUDGET_USD` merged with
`{"output_format": SPEC_WRITER_FORMAT}`, `resume` `s-1` and
`last_cost_usd`, with no other keyword. That `last_cost_usd` is 0.5, or 1.5
after the draft at cost 4.0. Each case asserts `spec_sha` is the SHA-256
of the expected text, or `None` where the text is empty. Each rejected
case asserts `type(resets_at) is int`. The witness asserts
`SPEC_WRITER_MAX_TURNS == 120` with `type(...) is int`,
`SPEC_WRITER_BUDGET_USD == 17.0`, `SPEC_WRITER_EXTRACT_BUDGET_USD == 1.5`,
`SPEC_WRITER_SESSION_USD == 18.5` and `SPEC_WRITER_TIMEOUT_S == 3600`.
Last, a `RuntimeError` from the first turn, and one from the extraction
turn, each propagate.

These fail it, measured on the earlier prototype:

- one turn, with the text read from the first turn
- an extraction turn not resumed, or with no `last_cost_usd`
- the writer's budget on the extraction turn, or the session sum on the
  writer turn
- an extraction turn after a rejected first turn
- the extraction turn's cost dropped, or a failed turn's cost dropped
- a rejection read from the first turn only, or from a returned turn only
- `stop_on_rejected` around the agent
- `REVIEW_TOOLS`, `IMPLEMENT_TOOLS`, or the review's turn ceiling
- every exception caught
- the failure's message kept as `error` on a rejected turn
- no check for a missing `session_id`, which resumes nothing
- the first turn's `session_id`
- the last attempt's `session_id`, `None` included
- the last turn's turn count alone
- `artifacts.EXTRACTION_PROMPT` as the extraction turn's prompt
- no `spec_sha`, a hash of the text before its newline, a hash of the
  whole turn text, or a hash of empty text

These fail it too, reasoned, since the prototype read a block and the
cost rule and the reset rows are new:

- the extraction turn sent with no `output_format`, with another
  model's format, or the first turn sent one
- the spec read from the extraction turn's `<output>` block, which gives
  `SY-9` on the conflicting row
- the spec read from the first turn's value or block, which gives `SY-8`
- the value not stripped, or no newline appended, which the padded row
  fails
- the value read before the rejection, which gives `spec` on a rejected
  row
- a failed turn's value kept, which gives `spec` where the row wants
  empty text
- a killed extraction turn's cost dropped, or every failed attempt with 0
  turns or no `session_id` skipped
- `last_cost_usd` of the first turn's cost uncapped, which charges 8.0
  after the draft at 4.0
- a cap at `SPEC_WRITER_BUDGET_USD` or at the session sum
- a reset at or below 0, `True` or a float passed through, or `None`
  where it cannot be shaped
- any of the five constants at another value

**Criterion 2's witness** follows `SA-0156`'s criterion 1 witness, and
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
  returns `structured_output` `{"spec": "---\nid: SY-1\n---\nrevised"}`,
  text `t`, cost 0.25 and 1 turn. For the rest it returns text `report`, cost 0.5, `s-1`
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
  `SPEC_WRITER_EXTRACT_BUDGET_USD` and `output_format` of
  `SPEC_WRITER_FORMAT`. Every call's `timeout_s` is
  `SPEC_WRITER_TIMEOUT_S` and equals 3600.
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

**Criterion 3's witness** uses criterion 1's double, its draft first turn
at cost 0.5, its `spec`, `V`, final turn and killed turn. `B` is
`"<output>\n" + spec + "</output>"`, a valid spec in a block. Each second
turn below carries text `B` beside its value.

- `N`: value `None`
- `K`: value `{"spec": "x", "extra": 1}`
- `Z`: value `{"spec": 3}`
- `J`: value `json.dumps(V)`, a `str`
- `O`: value `{}`

`M` is `not the schema: the turn returned no structured output`. `M(v)`
is `"not the schema: " + str(err)`, where `err` is the `ValidationError`
that `_SpecWriterReply.model_validate(v)` raises in the witness. Every
second turn carries cost 0.25, `s-2` and 7 turns. Every third turn that
carries an attempt carries cost 0.25, `s-3` and 7 turns. A row can say
otherwise.

| second | third | calls | text, cost, error, `resets_at`, `session_id`, turns |
|---|---|---|---|
| `N` | final | 3 | `spec`, 1.0, `None`, `None`, `s-3`, 21 |
| `K` | final | 3 | the same |
| `Z` | final | 3 | the same |
| `J` | final | 3 | the same |
| `O` | final | 3 | the same |
| `N` with no `session_id` | final | 3 | the same |
| `N` | final with no `session_id` | 3 | `spec`, 1.0, `None`, `None`, `s-2`, 21 |
| `N` | `N` | 3 | empty, 1.0, `M`, `None`, `s-3`, 21 |
| `N` | `K` | 3 | empty, 1.0, `M` of `K`'s value, `None`, `s-3`, 21 |
| `K` | `N` | 3 | empty, 1.0, `M`, `None`, `s-3`, 21 |
| `N` | `rejected`, reset 9, value `V` | 3 | empty, 1.0, `None`, 9, `s-3`, 21 |
| `N` | `rejected`, reset 0 | 3 | empty, 1.0, `None`, 1, `s-3`, 21 |
| `N` | raises `AgentFailed("api_error")`, `rejected`, reset `"soon"` | 3 | empty, 1.0, `None`, 1, `s-3`, 21 |
| `N` | raises `AgentFailed("cut")` with an attempt of value `V` | 3 | empty, 1.0, `cut`, `None`, `s-3`, 21 |
| `N` | the killed turn | 3 | empty, 1.0, `no result event`, `None`, `s-2`, 14 |
| `N` at cost 3.0 | the killed turn | 3 | empty, 5.0, `no result event`, `None`, `s-2`, 14 |
| `N` | raises `AgentFailed("gone")` with no attempt | 3 | empty, 0.75, `gone`, `None`, `s-2`, 14 |
| `N` | raises `RuntimeError` | 3 | raises |

Each third call is asserted exactly. It passes `c-1`, and the prompt
`M + "\n\n" + SPEC_WRITER_EXTRACT_PROMPT`, or `M(v)` of the second
turn's value `v` in place of `M` where that value is not `None`. It
passes the second call's options, `output_format` included, and
`resume="s-2"`, or `"s-1"` where the second carries no `session_id`. It
passes `last_cost_usd=0.25`, or 1.5 after `N` at cost 3.0, and no other
keyword. No row makes a fourth call. Each rejected row asserts
`type(resets_at) is int`, and each `spec_sha` follows criterion 1's rule.
These fail it, reasoned:

- no re-ask, which routes `N` to an error after two calls
- a second re-ask, which makes a fourth call on `N` then `N`
- a null value read as a cue to parse the text's `<output>` block,
  which takes `B` as the spec after two calls
- the value read without the model, as `value["spec"]` or `json.loads`
  of a string, which takes `K` or `J` with no re-ask
- the message, its validation error or the extraction prompt left out
  of the re-ask's prompt, or `EXTRACTION_PROMPT` in place of
  `SPEC_WRITER_EXTRACT_PROMPT`
- the second turn's message kept as the error, which `K` then `N` fails
- the writer's options on the re-ask, or the re-ask sent with no
  `output_format`
- a re-ask with no `resume`, or `resume` of the first turn's id
- the re-ask's `last_cost_usd` uncapped, which charges 6.5 after `N` at
  cost 3.0
- the re-ask's cost or turns left out of the sums
- a third turn's rejection read as an error

**How the lists were measured.** A throwaway prototype ran on 2026-09-24,
and after each of the two reviews. Its tree was `SA-0156`'s prototype,
`24e8152f`. It built an earlier shape of this spec, whose prompt came from
a file the policy named. Criterion 1's first list is unchanged from it.
The right build passed its witness, and each wrong version listed as
measured was applied as a text edit and failed it. `24e8152f` is not in
this repository's history, so a reader cannot rerun it. The prototype
read an `<output>` block. The move to `structured_output`, the cost
rule, the reset rows and criterion 3 are new since it. Criterion 2
changed when ADR 7 made the prompt core's. Those lists are unmeasured,
and so is each witness's reverted run. `SA-0176` measured the model's
own wrong builds, which criterion 3's `K`, `Z`, `J` and `O` rows reach
through it.

**What the witnesses leave undriven.**

- A raise from the export, the policy load or `layer_cell` inside the
  callable. Each propagates, and `SA-0164` counts the raise.
- A base whose `policy.yaml` is present and broken. The load raises
  `PolicyError`, and the callable raises with it.
- A `spec` value that is not a spec, an empty one included. It
  validates, and `SA-0150`'s `parse_spec` refuses it at run time.
- The CLI's own retries inside the turn. The double returns a value or
  `None` directly, so no witness sends the format to the API.
- An extraction turn that writes a spec larger than the spike's 46 KB
  for longer than the idle bound of 300 seconds with no event. It
  raises `AgentFailed`, and criterion 1's failed-turn rule applies.

**The ceilings.** `SA-0161` priced 74 hand `spec-writer` sessions from
their transcripts. Their mean was $6.24, their p90 $16.92 and their max
$23.43
(`.saffron/specs/SA-0161-a-stack-batchs-qualified-findings-reach-no-writer-so-no-follow-up-spec-exists.md:209-211`).
`SPEC_WRITER_BUDGET_USD` is 17.0, that p90 rounded up. A turn that
reaches `max_budget_usd` raises, and the session ends in an error, so the
ceiling sits above nine sessions in ten. The extraction turn writes one
spec out on a context already cached. The spike's addendum measured each
extraction turn at $0.40 or $0.41, for specs of 40 and 46 KB. A real writer's extraction turn resumes a longer context, so
`SPEC_WRITER_EXTRACT_BUDGET_USD` of 1.5 is reasoned from that figure
with room, not measured in a cell. `SPEC_WRITER_SESSION_USD` is their
sum, 18.5. `SA-0161` and `SA-0164` reserve by it.

**The bound on one session.** Every turn's `max_budget_usd` bounds its
call, and each fallback figure is at most that turn's own budget. So a
session records at most `SPEC_WRITER_BUDGET_USD` plus twice
`SPEC_WRITER_EXTRACT_BUDGET_USD`, $20.00. That is `SPEC_WRITER_SESSION_USD`
plus the re-ask's cap. It holds as long as each turn reports within its
`max_budget_usd`, which is best effort. A first turn killed before its
result event records $0, since no turn came before it. `run_agent`'s
default `last_cost_usd` is 0.0 (`saffron/phases/implement.py:196-205`).
So a sibling reserves by `SPEC_WRITER_SESSION_USD` as a bound on its plan,
not as a hard cap.
`SPEC_WRITER_MAX_TURNS` of 120 is a third above `SA-0175`'s 90.

**The turn bound.** `SA-0165`'s writer measured 79 hand `spec-writer`
transcripts. Their active time had a median of 1396 seconds, and 21
sessions ran past 2700 seconds. Those ran `make check` and prototypes
too, as this session can. `SPEC_WRITER_TIMEOUT_S` is 3600. The callable
binds it for both turns. The spike's extraction turns ran 130 to 150
seconds for a 46 KB spec, so the extraction turn ends far sooner.

**The `prose` gate** counts every new comment and docstring. Write none with an em dash, a semicolon, a contraction, the
perfect tense, a hedge or a sentence over 25 words. Use no word from
`FILLER` (`.saffron/gates/prose.py:67-83`), such as `just` or `simply`.
Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
estimate is about 2000 to 2300 changed tokens, 67% to 77% of the
ceiling. The earlier prototype, formatted by `ruff format`, measured
`saffron/spec_review.py` at 383 tokens. The re-ask and the cap add about
80. Its block regex goes, and the format merge, the validation and its
two messages come in, about 20 more, so about 480. `saffron/cli.py`
measured 309 with a start refusal and a prompt-file read. Both go, and
so do six prompt lines, so about 200. The earlier witnesses measured
1331, with a policy witness and a refusal witness that go. Criteria 1
and 2 keep about 1140, with the reset rows, the literals, the values,
the spy and the account check's recorder added. Criterion 3 runs about
380, with five second-turn values and the message helper. Keep the
doubles shared, the reset values in one loop, the rows in one table, and
the docstrings short.
