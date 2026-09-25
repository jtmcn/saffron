---
id: SA-0156
title: saffron batch --stack reviews no spec, and mints no task for a review to sit on
type: feature
priority: 1
depends_on: [SA-0169]
touches:
  - saffron/spec_review.py
  - saffron/cli.py
  - saffron/repos/policy.py
  - saffron/ledger.py
  - tests/test_spec_review.py
  - tests/test_cli.py
  - tests/test_policy.py
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
  - saffron/events.py
  - saffron/reconcile.py
  - saffron/preflight.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/mirror.py
  - saffron/repos/image.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_review.py
  - tests/test_package.py
budget_usd: 27
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `spec_review.run_spec_review(container, *, system_prompt, prompt,
      agent)` calls `agent` once, with the container, the prompt, and
      `implement.agent_options` of that system prompt,
      `SPEC_REVIEW_MAX_TURNS`, `SPEC_REVIEW_BUDGET_USD` and
      `SPEC_SESSION_TOOLS`. It passes nothing else. `SPEC_SESSION_TOOLS`
      holds `Read`, `Glob`, `Grep` and `Bash`, and no other tool. It returns a
      `SpecReviewSession` of the turn's text, cost, `session_id` and
      `num_turns`, with no error and no `resets_at`. A turn that raises
      `implement.AgentFailed` gives that failure's text as `error`, with its
      attempt's fields, or empty ones when it carries none. A turn whose
      rate-limit status is `rejected`, returned or raised, gives no error and
      keeps its cost. Its `resets_at` is the `int` that
      `session._resets_at_fields` passes where that is above 0. It is
      `UNREADABLE_RESET`, 1, where that passes none or one at or below 0.
      Any other raise propagates. The witness drives a returned rejection,
      raised ones carrying `10**20`, `None`, `"soon"`, `True`, a float, 0
      and -5, a status other than `rejected`, a failed turn with an attempt
      and one without, and a `RuntimeError`.
    witness: tests/test_spec_review.py::test_a_spec_review_session_returns_a_rejected_window_as_a_reset_time
  - claim: >-
      `cli._stack_review(*, pinned, repo, out_dir)` returns a callable that
      takes a candidate and its layer. Given a layer, it fetches the branch
      `scheduler._branch` names for the layer's spec id, from the pinned url
      into the pinned mirror, and seeds the cell at the fetched head. Given
      `None`, it fetches nothing and seeds the cell at the pinned
      `base_sha`. A fetch that raises `ParentGone` propagates, and no cell
      comes up. Each call exports `.saffron/` at the pinned `base_sha` into
      `out_dir / "spec-review" / <spec id>`, and loads that export's
      policy. The system prompt is the file its `spec_review_prompt` names,
      read at the pinned `base_sha`, after its frontmatter. It is never the
      operator's copy, the mirror's `HEAD`, or a path core names. An unset
      key raises `ValueError` naming `spec_review_prompt`, and a path the
      base lacks raises one naming the path. Neither brings a cell up.
      Building the callable reads nothing, so each raises only when called.
      The cell is `end_review.layer_cell` over `repo`, the pinned mirror,
      that export and its `thread_env`, called with `spec_session=True`. The prompt holds `.saffron/specs/`
      and the candidate's file name, `base: ` and the seeded tree, and `is a
      snapshot of the base`. The agent is `implement.run_agent` bound to
      `spec_review.SPEC_REVIEW_TIMEOUT_S`, 1800, and the candidate's spec
      id. The callable returns what `run_spec_review` returns, a rejected
      window's reset time included.
    witness: tests/test_cli.py::test_a_spec_review_reads_the_prompt_its_base_policy_names_in_a_cell_at_its_predecessors_head
  - claim: >-
      `cli._stack_mint(*, pinned, repo, ledger)` returns a callable that
      takes a candidate. Each call upserts the repo at the pinned url, with
      `repo`'s name, the pinned mirror and no `policy_sha`. It creates a run
      at the pinned `base_sha` with no batch, then a task, and returns the
      task's id. The task carries the candidate's spec id and `spec_sha`,
      the branch `scheduler._branch` names, the spec's `risk` and
      `budget_usd`, `context.prompt_sha()` and no `policy_sha`. Two calls
      for one spec give two runs and two tasks. A candidate that carries an
      earlier night's `task_id` gets a fresh task too, and that earlier
      task keeps its state and its run. A repo already on record keeps its
      `policy_sha`. The witness drives a repo on record, one that is not,
      and a candidate that carries a `RATE_LIMITED` task.
    witness: tests/test_cli.py::test_the_stack_mint_opens_a_run_at_the_pinned_base_and_a_task_per_call
  - claim: >-
      Once readiness passes, `saffron batch --stack` exports `.saffron/` at
      the pinned `base_sha` into a directory outside `out_dir`, and reads its
      policy. It then reads the file `spec_review_prompt` names at that
      `base_sha`. It does both before the scan resolves and before
      `run_stack_batch` opens the batch row. `Policy` takes the key only as
      a non-empty path with no leading `/` and no `..` segment. The night is
      refused where the base holds no `.saffron/`, no `policy.yaml`, or a
      policy that fails to load. It is refused where the key is unset or
      breaks that rule, and where the file is absent or has no frontmatter.
      It then prints one line that starts `batch: refused` and names
      `spec_review_prompt`, and exits 2. It opens no `batches` row, resolves
      no queue and builds neither callable. Otherwise it builds
      `_stack_review` and `_stack_mint` once each, with
      the `PinnedBase` built from readiness, the resolved `--repo`, the
      ledger `main` opened and `main`'s `out_dir`. It passes their callables
      to `run_stack_batch` as `review` and `mint`. When readiness fails, it
      reads no policy, refuses nothing, builds neither callable and passes
      `None` for both. `saffron batch` without `--stack` reads no policy for
      the key. The witness drives each refusal above, with the key empty,
      absolute, and holding a `..` segment.
    witness: tests/test_cli.py::test_a_stack_batch_refuses_a_base_that_names_no_review_prompt_and_wires_its_review_and_mint
---

## Context

Backlog item **b-792ab2**, step 6 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that spec review runs inside a stack batch, before each spec's
first cell. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "Writing and
reviewing specs inside the batch", is the design (`:150-166`). It runs each
review as a host-invoked session in a critic cell, seeded at the tree the
spec's cell is cut from.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Step 6 is four specs, and this is the last.** `SA-0149` reads a review
and routes each spec on it, through an injected `review` callable.
`SA-0155` gives each review a task and a record. It calls an injected
`mint` for every spec before its first review, whatever `task_id` the
candidate carries. The operator decided that on 2026-09-24. `SA-0168`
runs the cell on that task. `SA-0169` runs a spec session's `Bash` in its
critic cell as an unprivileged user. This spec builds the production
`review` and `mint`, and passes both from `saffron batch --stack`.

**What the tree base holds.** This spec's tree base is `SA-0169`'s head.
The chain below it runs `SA-0135`, `SA-0136`, `SA-0142` to `SA-0146`,
`SA-0153`, `SA-0154`, `SA-0157`, `SA-0159`, `SA-0147`, `SA-0148`,
`SA-0149`, `SA-0155`, `SA-0168` and `SA-0169`. Every line number below was
read at `f2a08a9f`, where none of their code exists. So `cli.py` and `ledger.py`
are cited by symbol where the chain edits them. This spec consumes these
names.

- From `SA-0143`: `run_stack_batch` and `cli._stack_runner`.
- From `SA-0144`: `saffron batch --stack`, whose `_batch` builds
  `_stack_runner` and calls `run_stack_batch` where readiness passed and
  `pinned` is bound.
- From `SA-0146` and `SA-0154`: `end_review.LayerFields`, with `spec_id`,
  `branch`, `pr_url`, `base`, `head` and `known`. `end_review.layer_cell(
  fields, *, repo, mirror, gates_dir, thread_env)` is a context manager.
  It seeds a cell at `fields.head` on the branch `fields.branch`, yields
  its container, and always tears it down.
- From `SA-0157`: `_stack_end_review` and its wiring into the `--stack`
  path of `_batch`. That wiring passes `run_stack_batch` `end_review` and
  `reserve_usd`, and passes `end_review=None` when readiness fails.
- From `SA-0149` and `SA-0155`: `saffron/spec_review.py` with
  `SpecReviewSession`, a frozen dataclass of `text`, `cost_usd`, `error`,
  `resets_at`, `session_id` and `num_turns`. `run_stack_batch`'s `review`
  keyword takes a candidate and the last layer's candidate or `None`. Its
  `mint` keyword takes a candidate and returns a `task_id`. Given `review`
  and no `mint`, `run_stack_batch` raises `ValueError`. `SA-0155` records
  the review's attempt, cost and fact, and attaches its run to the batch.
- From `SA-0148`: the wait. A reset time is readable when it falls after
  the clock's now and within six hours. Any other waits one hour.
- From `SA-0168`: `CellSpec.task_id`, and the cell that runs on it.
- From `SA-0169`: a spec session's `Bash` runs as an unprivileged user in
  the critic cell `layer_cell` brings up. It cannot write the runner or
  its files. `layer_cell` grants the wrapper its two capabilities only
  when called with `spec_session=True`, so this spec passes that. Without
  it the wrapper runs nothing, and the review loses its `Bash`. The
  witness's `layer_cell` recorder asserts the keyword. A call without it
  is a wrong build.

**How a critic session runs today.** `review.run_lens` builds
`agent_options` with `REVIEW_TOOLS`, `Read`, `Glob` and `Grep`, and calls
the agent (`saffron/phases/review.py:35`, `:208-236`). It calls it again
only to repair a report that is not the schema (`:244-292`). The
implementer's tools add `Write`, `Edit` and `Bash`
(`saffron/phases/implement.py:27`). `implement.run_agent` takes
`spec_id` with no default (`saffron/phases/implement.py:190-204`).
`AgentFailed` carries the attempt of a turn that failed, or `None`
(`:54-71`). `stop_on_rejected` raises `RateLimited` on a rejected window,
from a returned turn or a failed one (`saffron/cell/session.py:159-181`,
`:230-238`). `_resets_at_fields` passes any clean `int`, 0 and negatives
included, and turns anything else into `None` (`:150-156`).

**How long one review runs.** `session.TURN_TIMEOUT_S` is 900 seconds of
wall clock per turn (`saffron/cell/session.py:58-63`). A spec review is
one `run_agent` turn. The hand reviews of this chain, run on 2026-09-24
with `Bash`, took 566 to 681 seconds. `SA-0156`'s round-1 review took 681
seconds and 64 tool uses, 219 seconds under the turn bound. A cut raises `AgentFailed`, which `SA-0149`
routes `error`, and two in a row end the night `INFRASTRUCTURE`.

**Where the prompt comes from.** Core invokes declared gates, never tools
(§2.1). ADR 2 says that where a check reads as repo-specific, "core keeps
the question and the repo declares the tokens" (`docs/adr/0002-core-invokes-declared-gates-never-tools.md:65-67`).
The design names `.claude/agents/spec-reviewer.md` so the hand path and
the batch share one text (`:154-157`). That path is this repository's own
tooling, and another repository has no such file. So the operator decided
that `.saffron/policy.yaml` declares it. `Policy` refuses an unknown key
(`saffron/repos/policy.py:66-74`), so the key must exist before any
repository sets it. This repository's policy then names
`.claude/agents/spec-reviewer.md`, and the two paths still share one text.
Preflight reads a base with no `.saffron/` as absent, not as broken
(`saffron/preflight.py:487-495`). The start refusal reads it the same way,
and refuses, since such a base names no prompt.

**Where `Bash` departs from §5.5.** §5.5 keeps model-authored code out of
the critic cell (`DESIGN.md:1062`). There it would run as root beside the
runner a lens re-executes. A spec session's `Bash` runs commands the
model writes in that cell. `SA-0169` narrows the departure: those
commands run as a user that cannot write the runner or its files. The
operator records the narrowed departure in `DESIGN.md` by hand.

**What that agent file says.** `.claude/agents/spec-reviewer.md` has a
frontmatter block and a body. Its inputs are `spec:`, `base:` and
`history:` (`:12-20`). A prompt that says the tree is "a snapshot of the
base" lets it read the working tree with Read, Grep and Glob (`:25-27`).
Its report ends in a fenced `json` findings block (`:149-153`), which
`SA-0149` reads.

## Problem

Build four things.

1. **The session.** In `saffron/spec_review.py`, add
   `SPEC_REVIEW_MAX_TURNS` of 90, `SPEC_REVIEW_BUDGET_USD` of 6.0,
   `SPEC_REVIEW_TIMEOUT_S` of 1800.0, `UNREADABLE_RESET` of 1,
   `SPEC_SESSION_TOOLS`, and `run_spec_review`, as criterion 1 states.
   The operator gave the session `Bash` inside its critic cell. With it,
   the session can run a wrong build and measure size, as the hand chain
   does.
   The cell is the boundary: no credentials, and network through the
   proxy alone. `SA-0160`'s writer takes the same list. Follow
   `REVIEW_TOOLS`' spelling, a list of tool names. Read the rate-limit status
   with `session.terminal_for_rate_limit`, on the returned attempt or the
   failed one. Call the agent directly, not through `stop_on_rejected`, so
   a rejected turn's cost reaches the session. Name the 681-second
   measurement in the timeout's comment.
2. **The key.** Add `spec_review_prompt` to `Policy`, `None` by default,
   a path relative to the repository root. Constrain it with a pydantic
   `pattern`: non-empty, no leading `/`, and no `..` segment. Pydantic's
   default regex engine has no lookaround, so build the pattern from
   segments.
3. **The review callable.** In `saffron/cli.py`, add `_stack_review`, as
   criterion 2 states. Read the file with `git_mirror.file_at`. Take its
   body with `intake._FRONTMATTER`, whose second group is the text after
   the first closing fence. Export `.saffron/` with
   `git_mirror.export_saffron_dir` into `out_dir / "spec-review" / <spec
   id>`. That keeps it out of `out_dir / <spec id>`, the task's own
   directory, which the export would clear. Build `LayerFields` with the
   spec's id, `_branch` of it, `base` and `head` both the seeded tree, and
   `pr_url` and `known` empty. The prompt is `spec:`, `base:` and
   `history:` lines, then the snapshot sentence. The `history:` line says
   a batch has no history rows. Three lines follow, as `SA-0160`'s writer
   prompt holds them. The account reads the checkout and cannot write it.
   Anything that writes runs in a clone in the cell's temporary directory.
   A tool whose name does not resolve is called by its full path.
   `SA-0169` measured all three. Reach `package_phase.fetch_parent_branch`,
   `git_mirror.file_at`, `git_mirror.export_saffron_dir`,
   `end_review.layer_cell` and `implement.run_agent` through their modules
   at call time, since the witness replaces them there.
4. **The mint and the wiring.** In `saffron/cli.py`, add `_stack_mint`, as
   criterion 3 states. In `_batch`'s `--stack` path, after `pinned` is
   bound and before `_resolve_queue`, export `.saffron/` at the pinned
   `base_sha` into a temporary directory and load its policy. A `GitError`
   from the export and a `PolicyError` from the load each refuse. Then read
   the named file with `git_mirror.file_at` and match it with
   `_FRONTMATTER`, as the review callable does. Refuse as criterion 4
   states, with the `batch: refused` shape that
   `runtime.unattended_refusal` already prints (`saffron/cli.py:778-781`).
   Never export into `out_dir` or under it: the export clears its
   destination first (`saffron/repos/mirror.py:187`). Then
   build both callables where `_stack_runner` and `_stack_end_review` are
   built, and pass them to `run_stack_batch`.

One docstring in `saffron/ledger.py` becomes false. `attach_run_to_batch`
says `run_one_cell` is the only call that mints a run
(`saffron/ledger.py:849-850`), and `_stack_mint` mints one too. Reword it.

## Out of scope

- **This repository's `spec_review_prompt`.** `.saffron/**` is forbidden
  to a cell. The operator adds `spec_review_prompt:
  .claude/agents/spec-reviewer.md` to `.saffron/policy.yaml` by hand,
  after this spec merges. Before it merges, `Policy` refuses the key. So
  `saffron batch --stack` refuses on this repository until then.
- **The agent file's own text.** `.claude/agents/spec-reviewer.md` says
  the reviewer "runs no test", and names the hand loop's "Step 1b". An
  in-batch session with `Bash` needs leave to run a throwaway wrong build
  outside the tree. That hand edit lands before the operator sets the
  key.
- **The writer's prompt.** `SA-0160` adds `spec_writer_prompt` beside this
  key, and widens the refusal to it.
- **The review's record and its spend.** `SA-0155` records the attempt,
  the fact and the state, and attaches the run. So `_stack_review` takes
  no ledger, and `run_spec_review` records nothing. A second attempt
  written here would count the review's cost twice in `batch_spend`.
- **The review's events.** `run_spec_review` passes the agent no `emit`.
  `run_agent`'s default prints each event, cut short
  (`saffron/phases/implement.py:197`, `saffron/events.py:673-675`). No
  review event reaches an `events.jsonl`, so `saffron watch` shows none.
- **The review's budget.** `SPEC_REVIEW_BUDGET_USD` of 6.0 is unmeasured
  for a batch review. `SA-0155` records each review's cost, so the first
  stack night measures it.
- **Revision rounds.** They are `SA-0160`'s. Every blocker still routes
  `escalate`.
- **Concurrent reviews.** They wait for per-cell network names
  (b-6a692d).
- **History rows for check 4.** `driver.py` lives in `.claude/skills/`,
  a tool of this repository, and core invokes declared gates, never tools
  (§2.1). The cell holds no ledger for it to read, even with `Bash`. So
  check 4 has no rows in a batch, and says so.
- **The prompt tree's digest.** `context.prompt_sha()` digests
  `saffron/agents/prompts/`, and the agent file is not there. A change to
  it shows in no task's `prompt_sha`.
- **The vocabulary.** `CONTEXT.md` calls a spec review a delegate's
  advisory read, and its **Critic cell** entry names a patch applied. A
  spec review in the batch fits neither. Backlog item b-466005 files both
  by hand.
- **`DESIGN.md` §2.1's table.** It lists what `policy.yaml` declares
  (`DESIGN.md:148`). The spec review's prompt path joins that list by
  hand, since `DESIGN.md` is protected.

## Notes for the agent

**Every criterion is new code.** No text at the tree base runs a spec
review session or mints a task outside a cell. None reads the new key. So each
criterion declares a witness and no mutant, and `witness` reports `skip`
for each.

**Every witness fails with the source reverted, measured.** Criterion 1
imports `SPEC_REVIEW_BUDGET_USD`, which the tree base lacks. Criteria 2,
3 and 4 call or replace `cli._stack_review` and `cli._stack_mint`. Import
each new name inside the test body.

**Criterion 1's witness** calls `run_spec_review` with the container
`c-1`, the system prompt `sys` and the prompt `p`. Its agent double
records each call's arguments and returns or raises the case's turn. Each
case asserts one call, with exactly those three and the options the claim
names, and no other keyword.

| turn | `text`, `cost_usd`, `error`, `resets_at` |
|---|---|
| returned, text `t`, cost 0.5, `s-1`, 7 turns, no status | `t`, 0.5, `None`, `None` |
| returned, status `allowed`, reset 9 | `t`, 0.5, `None`, `None` |
| returned, status `rejected`, reset 1755800000, cost 0.25 | error `None`, `resets_at` 1755800000, cost 0.25 |
| raised `AgentFailed("api_error")`, `rejected`, reset `10**20`, cost 0.125 | error `None`, `10**20`, 0.125 |
| the same with reset `None`, `"soon"`, `True`, 1755800000.0, 0 and -5 | error `None`, 1, 0.125 |
| raised `AgentFailed("idle bound")`, text `half`, cost 0.0625 | `half`, 0.0625, `idle bound`, `None`, `s-1`, 7 |
| raised `AgentFailed("no result")` with no attempt | empty text, 0.0, `no result`, `None`, `None`, 0 |
| raised `RuntimeError("runner died")` | raises |

Each rejected case asserts `type(resets_at) is int`. The witness also
asserts `SPEC_SESSION_TOOLS`, sorted, is `Bash`, `Glob`, `Grep` and
`Read`. These fail it, each measured:

- `stop_on_rejected` around the agent, which raises `RateLimited`
- a rejection read from a returned turn only, or a failed one only
- `None` where the reset time cannot be shaped, which `SA-0149` routes
  `error` and counts as an abort
- the raw reset value, or 0 in place of 1
- a reset at or below 0 passed through, or only 0 mapped to 1
- the failure's text kept as `error` on a rejected turn
- a failed turn's cost or `session_id` dropped
- `IMPLEMENT_TOOLS`, `REVIEW_TOOLS`, or a list that adds `Write`
- the turns and budget swapped
- every exception caught

**Why 1 and not 0 or less.** `SA-0148` waits an hour for a reset time at
or before now. `SA-0149` routes `wait` when `resets_at` is set. A check
written as `if review.resets_at:` reads 0 as unset, and routes the
session `error`. A negative reset reads as set, but nothing in the
provider's contract makes one mean a time.

**Criterion 2's witness** builds a git repo in `tmp_path` as the mirror,
with `tests/test_cli.py`'s `_git` and `_rev_parse`. Its commits, oldest
first:

| commit | `.saffron/policy.yaml` | files |
|---|---|---|
| `unset` | `thread_env` `X: unset`, no key | `.claude/agents/spec-reviewer.md` with a body `named by no one` |
| `absent` | the key `review/agent.md`, `X: bare` | no `review/agent.md` |
| `base` | the key `review/agent.md`, `X: base` | `review/agent.md` as `---\nname: r\n---\nat base\n---\nsecond half\n` |
| `head` | the key `review/head.md`, `X: head` | both review files reading `head` |

The `repo` passed holds its own `review/agent.md`, `in the checkout`. The
witness replaces these through `monkeypatch`.

- `package.fetch_parent_branch` records `(mirror, url, branch)`. It
  raises `ParentGone` for `saffron/SY-8`, and returns `"d" * 40` for the
  rest.
- `session.cell_up` records its keywords and adds its container to
  `created`. `session.cell_down` records its keywords.
  `runtime.remove_container` returns `None`.
- `implement.run_agent` declares `spec_id` and `timeout_s` as keywords
  with no default, so a binding left out raises `TypeError`. It records
  each call. For `SY-2` it returns a rejected turn at cost 0.25 whose
  reset is `"soon"`. For the rest it returns text `rev`, cost 0.5,
  `s-1` and 7 turns.

Each candidate's path is `tmp_path / "export" / ".saffron" / "specs" /
"<id>-x.md"`. The witness pins `base` and calls the callable three times:
`SY-1` with no layer, `SY-2`, whose `depends_on` is `SY-9`, on the layer
`SY-7`, and `SY-3` on the layer `SY-8`, which raises `ParentGone`. It then
builds a callable pinned at `absent`, and one pinned at `unset`, and
calls each for `SY-4`. They raise `ValueError` matching `review/agent.md`
and `spec_review_prompt` in turn. It asserts:

- `SY-1`'s session is `rev`, 0.5, no error, no reset, `s-1` and 7 turns.
  `SY-2`'s is `resets_at` 1, no error, cost 0.25.
- the fetches are `saffron/SY-7` then `saffron/SY-8`, on the pinned
  mirror and url.
- two `cell_up` calls, seeded at `base` then `"d" * 40`, and two
  `cell_down` calls. Each has `repo`, the pinned mirror and `thread_env`
  `{"X": "base"}`. Its `gates_dir` is `out_dir / "spec-review" / <spec
  id>`, and its `policy.yaml` ends `X: base`.
- two agent calls, each in the container its `cell_up` got. The system
  prompt is exactly `at base\n---\nsecond half\n`. The prompt holds
  `.saffron/specs/<id>-x.md`, `base: ` with the seeded tree, and `is a
  snapshot of the base`. It holds no part of `tmp_path`. The options hold
  `SPEC_SESSION_TOOLS` and the two constants. `timeout_s` is
  `SPEC_REVIEW_TIMEOUT_S` and equals 1800. The spec ids are `SY-1` then
  `SY-2`, and no call resumes.

These fail it, each measured:

- `.claude/agents/spec-reviewer.md` named in core, or taken for an unset
  key
- the agent file read from `repo`, or from the mirror's `HEAD`
- the body split on every `---`, or the frontmatter kept
- the cell seeded at `base_sha` for every spec, with or without the fetch
- the branch taken from the candidate's `depends_on[0]`
- `stop_on_rejected` around the agent
- `REVIEW_TOOLS` in place of `SPEC_SESSION_TOOLS`
- a `ParentGone` caught and the cell seeded at `base_sha`
- `.saffron/` exported at the mirror's `HEAD`, or into `out_dir / <spec
  id>`
- the export's absolute path in the prompt
- `session.TURN_TIMEOUT_S`, no `timeout_s`, no `spec_id`, or an empty
  `thread_env`
- a missing agent file run with no body
- the key read at build time, which raises on building for `unset`

**Build the prompt in one place.** Build the review's prompt as one
string, in one spot, and send it as the one turn's `prompt`. Send no
second turn. `SA-0164` gives the callable a `spec_text` keyword beside
`(candidate, layer)`. It appends a sentence and the text, inside `<spec>`
tags, to that string.

**Criterion 3's witness** opens a `Ledger` in `tmp_path` and upserts a
repo at `https://github.com/o/r.git`, named `old`, with `policy_sha`
`"p" * 64`. On a run at `"e" * 40` it creates an older task for `SY-1`
and ends it `RATE_LIMITED`. It pins `base_sha` `"a" * 40`. The
candidates' `spec_sha` is `"c" * 64`. It mints `SY-1`, with `budget_usd`
7.5 and `risk` `elevated`, twice: first with `task_id` the older task,
then with none. It then mints `SY-2` with the defaults. It asserts three
distinct task ids, none the older task, each on its own run. Each run is
at `"a" * 40`, on the upserted repo, with no `batch_id`. Each task
carries its spec id, `spec_sha` `"c" * 64` and the branch `saffron/<spec
id>`. Each is `QUEUED`, with no `policy_sha`, and `prompt_sha` equals
`context.prompt_sha()`. `SY-1`'s rows carry 7.5 and `elevated`, and
`SY-2`'s carry 12.0 and `standard`. The older task is still
`RATE_LIMITED` on its own run. The one repo row now carries `repo`'s name
and the pinned mirror, and still `"p" * 64`. Last, it mints `SY-1` over a
fresh `Ledger` with no repo row. That task's run hangs from a repo at the
pinned url with no `policy_sha`. These fail it, each measured:

- the candidate's own `task_id` returned wherever it carries one
- the run created at the candidate's `spec_sha`
- the task's `spec_sha` taken from the pinned `base_sha`
- the branch built from the candidate's file name
- no `prompt_sha`, or no `risk`, or no `budget_usd`
- the repo upserted with `""` for its policy, which overwrites it
- one run reused across calls
- the repo looked up with `resolve_repo_id` in place of the upsert

**Criterion 4's witness** follows `SA-0157`'s wiring witness, with
`_readiness_passes` and `_fake_batch_resolution`
(`tests/test_cli.py:2603-2640`). It replaces these through `monkeypatch`:

- `cli.git_mirror.export_saffron_dir`, with a double that records
  `(mirror, sha, dest)`. It raises `GitError` for the case `gone`, and
  otherwise writes the case's `policy.yaml`, or none.
- `cli.git_mirror.file_at`, with a double that records `(mirror, sha,
  path)`. It returns `None` for `review/absent.md`, `no fence` for
  `review/bare.md`, and an agent body with frontmatter for any other
  path. So a bad path the pattern lets through is read, and passes.
- `cli._resolve_queue`, with a double that records each call.
- `cli._stack_review` and `cli._stack_mint`, with recorders that record
  their keywords and return two distinct sentinels.
- `cli.run_stack_batch`, with a fake that records its ledger and keywords
  and returns `DRAINED`. `cli.run_batch`, with one that records its call.

It runs `main` with `batch --stack` for each refused case, in turn: `gone`,
no `policy.yaml`, `thread_env: {}`, and the key as `""`, `/etc/agent.md`,
`review/../agent.md`, `review/absent.md` and `review/bare.md`.

- Each exits 2 and prints a line holding `batch: refused` and
  `spec_review_prompt`. No recorder, scan or fake was called, and the
  ledger holds no `batches` row. The export double saw the pinned mirror
  and `"a" * 40` eight times. No `dest` it saw is `out_dir` or under it.
  `file_at` was called for `review/absent.md` and `review/bare.md` alone,
  at the pinned mirror and base.
- With the key `review/agent.md`, it exits 0. Each recorder was called
  once, with the pinned base `_readiness_passes` returns and the resolved
  `--repo`. The review got `main`'s `out_dir`, and the mint the ledger the
  fake received. The fake got the two sentinels as `review` and `mint`.
- `batch` without `--stack`, over a policy with no key, exits 0. The
  plain fake was called once, and the export double not again.
- With readiness failing, neither recorder nor the export double is
  called, and the fake gets `None` for both.

These fail it, measured against a stand-in `--stack` path:

- no refusal, or an unread policy read as set
- a `GitError` or a `PolicyError` raised past the refusal
- the key's pattern dropped, which lets `""` through
- no read of the file at start, or its presence alone checked
- the start export into `out_dir`
- the key read without `--stack`
- the refusal read from the operator's checkout
- the refusal after the scan, or the policy read before readiness
- `review` passed without `mint`, which `SA-0155` refuses with
  `ValueError`
- either callable built before readiness, on a base not yet pinned
- a mint over a ledger other than `main`'s

**The earlier `--stack` witnesses.** Each `main` run with `--stack` whose
readiness passes now meets the start refusal. Two such tests reach the
tree base, and each needs the key and its file at the pinned base.
`SA-0160` adds `spec_writer_prompt` to the same list, and they need that
key too from then on.

- `SA-0144`'s `test_saffron_batch_stack_plans_once_and_runs_that_order`,
  in its readiness-passing and raising-scan runs. `_readiness_passes`
  pins a mirror that does not exist. So replace
  `cli.git_mirror.export_saffron_dir` with a double that writes a policy
  naming the key, and `cli.git_mirror.file_at` with one that returns an
  agent body with frontmatter.
- `SA-0157`'s
  `test_a_stack_batch_holds_a_quarter_of_its_budget_and_reads_its_stack_at_the_pinned_base`.
  Its mirror is a real git repository. Add the key to the base commit's
  `policy.yaml`, and the agent file beside it. Leave its `head` commit
  as it is.

Change nothing else in either test.

**How the lists were measured.** A throwaway prototype ran on 2026-09-24
at `f2a08a9f`, on the host's git, over `SA-0168`'s prototype. It stood in
for `SpecReviewSession`, `LayerFields` and `layer_cell` as the consumed
names above state them. It stood in for the `--stack` path as a branch
of `_batch` that builds `_stack_runner` and calls a `run_stack_batch`
taking `review` and `mint`. The right build passed all four witnesses and
the existing `test_cli.py`, `test_policy.py`, `test_ledger.py` and
`test_preflight.py`. Each wrong version above was applied as a text edit,
and each failed its own witness. With the source reverted, each witness
failed. `SA-0169`'s code was not in the prototype, so nothing here ran its
user. `SA-0169` measures that user in a real cell.

**What the witnesses leave undriven.**

- A raise from the export, the policy load or `layer_cell` inside the
  review callable. Each propagates, and `SA-0155` records the review as
  errored.
- A `GitError` from `file_at` at the start refusal, such as a symlink out
  of the tree. The refusal names it. Only `None` and a body without
  frontmatter are driven.
- A `_resets_at_fields` value that is a clean `int` above 0 but past or
  far ahead. `SA-0148`'s wait reads those, and waits the hour.
- An agent file with no frontmatter at all. `_FRONTMATTER` does not match
  it, so it raises the same `ValueError` as a missing file.
- Two reviews of one spec in a night. Each exports under the same
  directory, and the export clears it first
  (`saffron/repos/mirror.py:173-187`).

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype, formatted by `ruff format`, measured 2245 changed tokens with
`size_gate`'s own count. `saffron/cli.py` took 466,
`saffron/spec_review.py` 218, `policy.py` 41 and `ledger.py` 14. The
witnesses took 1506. `tests/test_spec_review.py` counted as a new file,
264 of it. The two earlier witnesses' edits are not at `f2a08a9f`, so
they are unmeasured, about 80 more. That is about 2325, 78% of the
ceiling. Keep test helpers shared and docstrings short.
