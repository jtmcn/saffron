---
id: SA-0160
title: A stack batch has no session that revises a spec, so a build or witness blocker can only escalate
type: feature
priority: 1
depends_on: [SA-0150]
touches:
  - saffron/spec_review.py
  - saffron/cli.py
  - saffron/repos/policy.py
  - saffron/agents/prompts/turns/spec-writer-extract.md
  - tests/test_spec_review.py
  - tests/test_cli.py
  - tests/test_policy.py
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
  - saffron/repos/mirror.py
  - saffron/repos/image.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/*.py
  - saffron/agents/prompts/*.md
  - saffron/agents/prompts/turns/extraction.md
  - tests/test_batch.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
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
      `cli._stack_revise(*, pinned, repo, out_dir)` returns a callable that
      takes a candidate, its layer, the spec's current text as
      `str | None`, and the text of a spec review. Given a layer, it fetches the branch
      `scheduler._branch` names for the layer's spec id, from the pinned url
      into the pinned mirror, and seeds the cell at the fetched head. Given
      `None`, it fetches nothing and seeds the cell at the pinned
      `base_sha`. A fetch that raises `ParentGone` propagates, and no cell
      comes up. It exports `.saffron/` at the pinned `base_sha` into
      `out_dir / "spec-write" / <spec id>` and loads that export's policy.
      The system prompt is the file the policy's `spec_writer_prompt` names,
      read at the pinned `base_sha`, after its frontmatter. An unset key
      raises `ValueError` naming `spec_writer_prompt`, and a missing file
      raises one naming its path. Neither brings a cell up. The cell is
      `end_review.layer_cell` over `repo`, the pinned mirror, that export
      and its `thread_env`, called with `spec_session=True` (`SA-0169`). The prompt's first fourteen lines are exactly
      the lines the Problem lists, with the candidate's file name and the
      seeded tree filled in. It then holds the review text inside a pair of
      review tags, then the spec text inside a pair of spec tags. The agent
      is `implement.run_agent` bound to `spec_review.SPEC_WRITER_TIMEOUT_S`,
      3600, and the candidate's spec id. Both turns run in that one cell,
      and the callable returns what `run_spec_writer` returns.
    witness: tests/test_cli.py::test_a_spec_revision_reads_its_policys_writer_prompt_in_a_cell_at_its_predecessors_head
  - claim: >-
      `Policy` takes an optional `spec_writer_prompt`, a string, `None` when
      the policy does not set it. `load_policy` reads it back as written.
    witness: tests/test_policy.py::test_a_policy_names_its_spec_writer_prompt_or_none
  - claim: >-
      Once readiness passes, `saffron batch --stack` refuses where the
      policy in `.saffron/` exported at the pinned `base_sha` sets no
      `spec_writer_prompt`, as `SA-0156` refuses for `spec_review_prompt`.
      A missing `policy.yaml` leaves both unset. It prints one line that
      starts `batch: refused` and names each unset key of the two, and no
      key that is set. It exits 2, resolves no queue and calls no
      `run_stack_batch`. Where readiness fails, it reads no policy and
      refuses nothing. The witness drives both keys set, each one unset
      alone, neither set, no `policy.yaml`, and readiness failing.
    witness: tests/test_cli.py::test_a_stack_batch_is_refused_at_start_without_a_spec_writer_prompt
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.3. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that an agent revises a queued spec for a witness or buildability
blocker, for a bounded number of rounds. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design.
Spec writing runs as a host-invoked session in a critic cell, seeded at the
tree the spec would be cut from (`:152-154`). Its spec returns through the
extraction turn and is hashed on arrival (`:154-155`). Its prompt is the
text the hand path uses, so both read one text (`:155-157`).

**Core names no agent file.** `.claude/agents/` is this repository's
tooling, and core knows nothing about a target repository's tools (§2.1).
So the operator decided, in `SA-0156`'s review, that the policy names each
spec session's prompt. `SA-0156` adds `spec_review_prompt`. This spec adds
`spec_writer_prompt` beside it. Once both land, this repository's policy
will name `.claude/agents/spec-writer.md`, so the hand path and the batch
will still share one text.

**The session holds Bash.** The operator decided that the spec writer
session runs commands in its critic cell, as a hand draft does. It
measures any wrong-build list it adds with a throwaway script. The cell is
torn down after the session, and the host reads the spec only from the
extraction turn, never from `/work`. `SA-0169` runs that Bash as an
unprivileged user, and the chain runs `SA-0168`, `SA-0169`, then
`SA-0156`.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Revision rounds take two specs.** This first one builds the session, its
callable and its policy key. `SA-0164` builds the `revise` route, the
rounds in `run_stack_batch`, the record of each revision, and the wiring
into `saffron batch --stack`. `SA-0161` then writes follow-up specs, and it
runs the same session with a prompt of its own.

**What the tree base holds.** This spec's tree base is `SA-0150`'s head.
Every line number below was read at `68892367`, where no chain code from
`SA-0142` on exists. So `cli.py`, `policy.py` and `spec_review.py` are cited
by symbol where the chain edits them. This spec consumes these names.

- From `SA-0143` and `SA-0144`: `cli.py` imports `scheduler._branch`.
  `saffron batch --stack` calls `run_stack_batch` from `_batch`, once
  readiness passes and the base is pinned.
- From `SA-0146` and `SA-0154`: `end_review.LayerFields`, with `spec_id`,
  `branch`, `pr_url`, `base`, `head` and `known`.
  `end_review.layer_cell(fields, *, repo, mirror, gates_dir, thread_env)`
  is a context manager. It seeds a critic cell at `fields.head`, yields its
  container, and always tears it down.
- From `SA-0156`, in `saffron/spec_review.py`: `run_spec_review`,
  `UNREADABLE_RESET` of 1, and `SPEC_SESSION_TOOLS`, which is `Read`,
  `Glob`, `Grep` and `Bash`. A rejected window in `run_spec_review` gives
  no error and a `resets_at` it shapes from `session._resets_at_fields`,
  or `UNREADABLE_RESET`. `cli._stack_review` builds the review's cell, and
  this spec's callable follows its shape.
- From `SA-0156` too: `Policy.spec_review_prompt`, an optional
  repo-relative path, and the start refusal in `_batch`'s `--stack` path.
  Once `pinned` is bound, and before `_resolve_queue`, it exports
  `.saffron/` at the pinned `base_sha` and loads its policy. A
  `PolicyError` from a missing `policy.yaml` counts as the key unset. It
  prints one line starting `batch: refused`, the shape at
  `saffron/cli.py:778-781`, names `spec_review_prompt`, and returns 2.
  With readiness failed, it reads no policy.
- From `SA-0150`: the `spec_text` fact, and
  `Ledger.record_spec_text(task_id, *, origin, spec_id, path, text)`. A
  row's `spec_sha` is the SHA-256 of its text. This spec calls neither.

**How an extraction turn runs today.** REBUT asks for its fix, then resumes
the same session for the record. "Two turns, because §5.3 allows exactly one
way to produce a structured artifact" (`saffron/phases/rebut.py:160-162`).
The second call passes `resume` and `last_cost_usd`
(`saffron/phases/rebut.py:182-189`), and the costs of both turns are summed
(`:196`). A turn killed before its result event raises `AgentFailed`
with an attempt of no `session_id`, 0 turns and a cost of `last_cost_usd`
(`saffron/phases/implement.py:303-318`). So REBUT's failed extraction adds
the first turn's cost a second time (`saffron/phases/rebut.py:190-193`).
This spec adds nothing for such an attempt. `parse_output_block` returns
the last non-greedy `<output>` block (`saffron/agents/artifacts.py:27`,
`:196-202`). A spec that quotes a closing tag loses its tail there, and a
draft block or a tag in prose moves its start. So this spec reads its own
block.
`hash_artifact` is the SHA-256 of the text's bytes (`:205-206`).
`context.turn_prompt(name)` reads `prompts/turns/<name>.md` and fills its
`{extraction}` slot with the shared rules
(`saffron/agents/context.py:156-171`). `tests/test_context.py` holds every
turn file to a constant that loads it (`:413-433`).

**How a turn is bounded.** `agent_options` sets `max_budget_usd` per turn,
not per session (`saffron/phases/implement.py:95-139`). `AgentFailed`
carries the attempt of a turn that failed, or `None` (`:54-71`).
`session.TURN_TIMEOUT_S` is 900 seconds (`saffron/cell/session.py:63`).

**How the policy reads today.** `Policy` forbids a key it does not declare
(`saffron/repos/policy.py:66-74`). A policy that sets `spec_writer_prompt`
fails to load at `68892367`. `load_policy` wraps that as a `PolicyError`
(`:129-132`).

**What this repository's writer file says.** `.claude/agents/spec-writer.md`
has a frontmatter block (`:1-5`). Its `review:` input is a spec review,
with `spec:` naming the spec it read (`:20-21`). `base:` is the commit a
cell would be cut from (`:25`). Its **Revising against a review** section
runs `make check` and re-runs its steps (`:107-131`).

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
2. **The extraction turn's prompt.** Add
   `saffron/agents/prompts/turns/spec-writer-extract.md`. It asks for the
   whole revised spec file, frontmatter first, and nothing else in the
   block. It forbids a code fence around the file, in words holding `code
   fence`. It ends with the `{extraction}` slot. Add its entry to
   `TURN_PROMPTS` in `tests/test_context.py`, with the constant
   `spec_review` loads it into.
3. **The key.** Add `spec_writer_prompt: str | None = None` to `Policy`,
   beside `spec_review_prompt`. Extend `SA-0156`'s start refusal to it, as
   criterion 4 states.
4. **The callable.** In `saffron/cli.py`, add `_stack_revise`, as
   criterion 2 states. Export `.saffron/` with
   `git_mirror.export_saffron_dir`, as `_stack_review` does into its own
   directory. Load its policy. Read the file its key names with
   `git_mirror.file_at`, and take its body with `intake._FRONTMATTER`.
   Build `LayerFields` as `_stack_review` does. The prompt's first fourteen
   lines are these, with `<name>` the candidate's file name and `<tree>`
   the seeded tree. The review and the spec text follow, each in its tags.

   ```
   review: the spec review between the review tags below.
   spec: .saffron/specs/<name>
   base: <tree>
   The checkout is a snapshot of the base.
   The text between the spec tags below is the spec's current text, and it replaces the file at that path.
   You may run commands in this cell.
   Your commands run as an account that can read the checkout but not write it.
   To run anything that writes, first clone the checkout: git clone -q /work /tmp/w && cd /tmp/w
   Call a tool by its full path when its name does not resolve.
   Measure any list of wrong builds you add with a throwaway script.
   Keep the spec's id and its exact depends_on.
   Raise no budget_usd, max_turns or max_attempts.
   A follow-up's revision keeps its touches within its first text's touches.
   Return the whole spec in the extraction turn.
   ```

   The three lines on the id, the ceilings and `touches` state the rules
   `SA-0150`'s gate 0 holds a revision to. A queued spec's revision can
   still widen its `touches`. Reach
   `package_phase.fetch_parent_branch`, `git_mirror.file_at`,
   `git_mirror.export_saffron_dir`, `end_review.layer_cell` and
   `implement.run_agent` through their modules at call time, since the
   witness replaces them there.

**Three earlier tests turn red.** Each runs `main` with `batch --stack`
past the refusal, on a policy with no `spec_writer_prompt`. Each gains that
key in the policy its run reads at the pinned base, beside the
`spec_review_prompt` `SA-0156` gives it. All three are in
`tests/test_cli.py`.

- `test_saffron_batch_stack_plans_once_and_runs_that_order` (`SA-0144`)
- `test_a_stack_batch_holds_a_quarter_of_its_budget_and_reads_its_stack_at_the_pinned_base`
  (`SA-0157`)
- `test_a_stack_batch_refuses_a_base_that_names_no_review_prompt_and_wires_its_review_and_mint`
  (`SA-0156`), whose run with `spec_review_prompt: r.md` alone exits 0

`_stack_revise` has no caller in `saffron/` until `SA-0164` wires it.
`SPEC_WRITER_SESSION_USD` has none until `SA-0164` reserves by it. So both
are `pending_symbols` entries.

## Out of scope

- **This repository's policy.** `.saffron/policy.yaml` gains
  `spec_review_prompt` and `spec_writer_prompt` by hand, after the cells
  that add them merge. A cell cannot edit `.saffron/**`. Until then
  `saffron batch --stack` on this repository refuses at start.
- **`DESIGN.md`'s list of policy keys** (`DESIGN.md:1497-1498`). It
  names no spec session's prompt. `DESIGN.md` is protected, so the
  delegate adds both keys by hand in this spec's pull request.
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
- **The writer file's bookkeeping.** The session writes no backlog record
  and commits nothing that survives its cell. The finish commits the text
  (`SA-0151`).
- **Follow-up specs.** `SA-0161` builds their prompt and callable around
  `run_spec_writer`, and reserves by `SPEC_WRITER_SESSION_USD`.
- **REBUT's double charge.** Its failed extraction turn adds the
  attempt's cost, which a kill before the result event sets to
  `last_cost_usd` (`saffron/phases/rebut.py:190-193`). `saffron/phases/**`
  is forbidden here, so the delegate files it as its own backlog item.
- **Concurrent sessions.** They wait for per-cell network names
  (b-6a692d).
- **The vocabulary.** `CONTEXT.md` names the `spec-writer` agent only as a
  delegate's tool in a **Spec chain**. A spec writer session in a batch is
  new. Backlog item b-466005 files it by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base runs a spec writer
session, reads a writer prompt or declares `spec_writer_prompt`. So
criteria 1 to 3 declare a witness and no mutant, and `witness` reports
`skip` for each. Criterion 4 extends `SA-0156`'s refusal. `SA-0156` fixes
that refusal's behaviour and its printed line, and leaves its code's
spelling to its cell. A mutant's `find` must match that code exactly once
(§5.4.1), and intake refuses one the spec body spells. No text is
determined to pin, so criterion 4 declares a witness and no mutant too.

**Every witness fails with the source reverted.** Criterion 1 imports
`run_spec_writer`, which the tree base lacks. Criterion 2 calls
`cli._stack_revise`. Criterion 3's policy sets a key the reverted `Policy`
forbids, and names no other key. Criterion 4's case with the writer's key
unset reaches `run_stack_batch` on the reverted build. Import each new name
inside the test body. The new `TURN_PROMPTS` entry reads `spec_review` at
module scope, which is not a declared witness.

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
expected text, or `None` where the text is empty. The witness asserts the
extraction prompt holds `frontmatter`, `code fence` and
`artifacts.EXTRACTION_PROMPT`. It asserts `SPEC_WRITER_SESSION_USD` is the
sum of the two budgets and at most 12.50. Each rejected case asserts
`type(resets_at) is int`. Last, a `RuntimeError` from the first turn, and
one from the extraction turn, each propagate.

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
- a turn file that does not forbid a code fence
- no `spec_sha`, a hash of the text before its newline, a hash of the
  whole turn text, or a hash of empty text

**Criterion 2's witness** follows `SA-0156`'s witness for `_stack_review`,
and reuses the helpers it adds to `tests/test_cli.py`. It builds a git
repository in `tmp_path` as the mirror, with `_git` and `_rev_parse`. Let
`named` be the policy line `spec_writer_prompt: prompts/writer.md`.

- Commit `bare` holds `.saffron/policy.yaml` with `thread_env` `X: bare`
  and `named`. It holds `.claude/agents/spec-writer.md` with a frontmatter
  and the body `hard`, and no `prompts/writer.md`.
- Commit `unset` sets `X: unset` with no key, and adds
  `prompts/writer.md` with a frontmatter and a body.
- Commit `base` sets `X: base` and `named`, and sets `prompts/writer.md`
  to `---\nname: w\n---\nat base\n---\nsecond half\n`.
- A last commit sets `X: head` and names `prompts/head.md`, which it adds
  with a frontmatter and a body. It sets `prompts/writer.md` to `head`.

The `repo` passed holds its own `prompts/writer.md`, reading `in the
checkout`. It replaces these through `monkeypatch`.

- `package.fetch_parent_branch` records `(mirror, url, branch)`. It
  raises `ParentGone` for `saffron/SY-8`, and returns `"d" * 40` for the
  rest.
- `session.cell_up` records its keywords and adds its container to
  `created`. `session.cell_down` records its keywords.
  `runtime.remove_container` returns `None`.
- `implement.run_agent` declares `spec_id` and `timeout_s` as keywords
  with no default. It records each call. For `SY-2` it returns a rejected
  turn at cost 0.25 whose reset is `"soon"`. For a call that resumes, it
  returns text `<output>\n---\nid: SY-1\n---\nrevised\n</output>`, cost
  0.25 and 1 turn. For
  the rest it returns text `report`, cost 0.5, `s-1` and 7 turns.

The witness pins `base` and calls the callable three times. `SY-1` has no
layer, the spec text `spec one\n` and the review `review one`. `SY-2`,
whose `depends_on` is `SY-9`, is on the layer `SY-7`, with `spec two\n`
and `review two`. `SY-3` is on the layer `SY-8`, which raises
`ParentGone`. Then it pins `bare` and calls it for `SY-4`, which raises
`ValueError` matching `prompts/writer.md`. It pins `unset` and calls it
for `SY-5`, which raises `ValueError` matching `spec_writer_prompt`. It
asserts:

- `SY-1`'s session is `---\nid: SY-1\n---\nrevised\n`, 0.75, no error,
  no reset, `s-1` and 8
  turns. `SY-2`'s is empty text, `resets_at` 1, no error, cost 0.25.
- the fetches are `saffron/SY-7` then `saffron/SY-8`, on the pinned
  mirror and url.
- two `cell_up` calls, seeded at `base` then `"d" * 40`, and two
  `cell_down` calls. Each has `repo`, the pinned mirror and `thread_env`
  `{"X": "base"}`. Its `gates_dir` sits under `out_dir / "spec-write"`,
  and holds the `policy.yaml` of `base`.
- three agent calls: `SY-1`, then `SY-1` resuming in the same container,
  then `SY-2`. The resumed call's prompt is the extraction turn's, with
  `SPEC_WRITER_EXTRACT_BUDGET_USD`. Every call's `timeout_s` is
  `SPEC_WRITER_TIMEOUT_S`.
- each first call runs in the container its `cell_up` got. Its system
  prompt is exactly `at base\n---\nsecond half\n`. The prompt's first
  fourteen lines equal the Problem's list, with `<id>-x.md` and the seeded
  tree filled in. It holds no part of `tmp_path`. The text
  `<review>`, the review text, `</review>`, `<spec>`, the spec text and
  `</spec>` appear in that order. The options hold `SPEC_SESSION_TOOLS`,
  `SPEC_WRITER_MAX_TURNS` and `SPEC_WRITER_BUDGET_USD`.

These fail it, each measured:

- the prompt file read from `repo`, or from the mirror's `HEAD`
- a hard-coded `.claude/agents/spec-writer.md` in place of the key
- an unset key read as that hard-coded path
- the key read from the policy at the mirror's `HEAD`
- the body split on every `---`, or the frontmatter kept
- the cell seeded at `base_sha` for every spec
- the branch taken from the candidate's `depends_on[0]`
- a `ParentGone` caught and the cell seeded at `base_sha`
- `.saffron/` exported at the mirror's `HEAD`, or into
  `out_dir / <spec id>`, the task's own directory
- the export's absolute path in the prompt
- the turn bound left at `session.TURN_TIMEOUT_S`, no `spec_id`, or an
  empty `thread_env`
- a missing prompt file run with an empty system prompt
- the review and the spec text swapped, or either left out
- a prompt that opens with `spec:`
- no sentence that the spec text replaces the file
- a sentence that the session holds no tool, or one with no throwaway
  script
- no line on the id and `depends_on`, the ceilings, or `touches`
- a paraphrase of the ceilings line
- `run_spec_review` called in place of `run_spec_writer`
- `stop_on_rejected` around the agent

**Criterion 3's witness** follows `tests/test_policy.py`'s `write_repo`. A
policy that sets `spec_writer_prompt: prompts/writer.md` and no other key
loads it as written. A policy that sets only `thread_env` loads
`spec_writer_prompt` as `None`. These fail it, each measured:

- the key left off `Policy`, which the forbidden extra key refuses
- the key required
- the key defaulted to `.claude/agents/spec-writer.md`

**Criterion 4's witness** follows `SA-0156`'s criterion 4 witness, with
`_readiness_passes` and `_fake_batch_resolution`. It replaces
`cli.git_mirror.export_saffron_dir` with a double that writes the case's
`policy.yaml`, or none. It replaces `cli._resolve_queue` with a recorder,
`cli._stack_review` and `cli._stack_mint` with recorders returning
sentinels, and `cli.run_stack_batch` with a fake returning `DRAINED`. It
runs `main` with `batch --stack` once per row.

| `spec_review_prompt` | `spec_writer_prompt` | exit | output and calls |
|---|---|---|---|
| set | set | 0 | the fake called once |
| set | unset | 2 | one `batch: refused` line naming `spec_writer_prompt` alone |
| unset | set | 2 | one `batch: refused` line naming `spec_review_prompt` alone |
| unset | unset | 2 | one `batch: refused` line naming both |
| no `policy.yaml` | | 2 | one `batch: refused` line naming both |

In each refused row neither the scan recorder nor the fake was called. A
last run with readiness failing calls no export double and refuses
nothing. These fail it, each measured on a stand-in for `SA-0156`'s check:

- the refusal left on `spec_review_prompt` alone
- the refusal on `spec_writer_prompt` alone
- a refusal that names the first unset key only
- one refusal line per unset key
- a missing `policy.yaml` read as naming the writer's prompt

These are unmeasured, since `SA-0156`'s `--stack` path is not at
`68892367`:

- the writer's refusal after the scan, which calls the scan recorder
- the writer's key read with readiness failed, which calls the export
  double
- a writer's refusal that exits 0

**How the lists were measured.** A throwaway prototype ran on 2026-09-24,
and after each of the two reviews. Its tree was `SA-0156`'s prototype,
`24e8152f`. It held stand-ins for `SpecReviewSession`, `run_spec_review`,
`SPEC_SESSION_TOOLS`, `LayerFields`, `layer_cell`, `_stack_review` and
`spec_review_prompt`, as the consumed names above state them. `24e8152f`
differs from `68892367` in `tests/test_scheduler.py` alone. It built
criteria 1 to 3 and their witnesses. It stood in for `SA-0156`'s refusal
with a function that names each unset key, and drove that function, not
`main`. The right build passed all four witnesses. Each of the 78 wrong
versions listed as measured was applied as a text edit, and each failed
its own witness.

**The cell's keyword.** Criterion 2's `layer_cell` recorder asserts
`spec_session=True`. A call without it is a wrong build: the wrapper would
run nothing, and the writer would lose its `Bash`.

**What the witnesses leave undriven.**

- A raise from the export, the policy load or `layer_cell` inside the
  callable. Each propagates, and `SA-0164` counts the raise.
- A block whose text is not a spec. `SA-0150`'s `parse_spec` refuses it at
  run time.
- A prompt file with no frontmatter. `_FRONTMATTER` does not match it, so
  it raises the same `ValueError` as a missing file.
- A key that names a path outside the tree, such as `../x`.
  `git_mirror.file_at` is handed the path as written, and nothing here
  checks it.
- A draft block that itself opens on a `---` fence, before the real
  one. The read starts at the draft and runs to the last closing tag. The
  extraction prompt asks for one block, and `parse_spec` refuses the
  joined text at run time.

**The ceilings.** The backtest's 39 spec reviews cost $71.38, a mean of
$1.83 (`docs/evidence/2026-09-14-spec-reviewer-backtest.md:174`). Design
section 3 measures writing at about six times a review (`:202-203`). So
`SPEC_WRITER_BUDGET_USD` is 11.0, six times that mean. The chain's token
tables put a draft at 1.4 to 2.0 times a review
(`docs/evidence/2026-09-23-spec-chain-feedback.md:69-86`). So 11.0 is three
to four times a draft's estimated mean. `SPEC_REVIEW_BUDGET_USD` keeps 3.3
times over a review. The extraction turn writes one spec out on a context
already cached. `SPEC_WRITER_EXTRACT_BUDGET_USD` of 1.5 is reasoned from
that, not measured. It keeps `SPEC_WRITER_SESSION_USD` at 12.50, the most
`SA-0161`'s sub-cap allows. That sum is best effort. `max_budget_usd`
bounds each call, and no session was ever seen reaching it. So a sibling
reserves by `SPEC_WRITER_SESSION_USD` as a bound on its plan, not as a hard
cap. `SPEC_WRITER_MAX_TURNS` of 120 is a third above
the review's 90.

**The turn bound.** `SA-0165`'s writer measured 79 hand `spec-writer`
transcripts. Their active time had a median of 1396 seconds, and 21
sessions ran past 2700 seconds. Those ran `make check` and prototypes
too, as this session can. `SPEC_WRITER_TIMEOUT_S` is 3600. The callable
binds it for both turns, and the extraction turn ends far sooner.

**The `prose` gate** counts every new comment, docstring and Markdown
file. The new turn file starts its ratchet at zero. Write none with an em
dash, a semicolon, a contraction, the perfect tense or a sentence over 25
words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype, formatted by `ruff format`, measured 2068 changed tokens with
`size_gate`'s own count. `saffron/spec_review.py` took 383,
`saffron/cli.py` 309 with the refusal's stand-in, `saffron/repos/policy.py`
6, the turn file 33 and `tests/test_context.py` 6. The witnesses took
1331. Criterion 4's witness drives `main`, not the stand-in, which adds
about 300. The three red tests each gain one policy line. That is about
2380 tokens, 79% of the ceiling. Keep the doubles shared and the
docstrings short.
