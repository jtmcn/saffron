---
id: SA-0156
title: saffron batch --stack reviews no spec, and a cell mints a second task beside the one its review is recorded on
type: feature
priority: 1
depends_on: [SA-0155]
touches:
  - saffron/spec_review.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/cell/session.py
  - saffron/ledger.py
  - tests/test_spec_review.py
  - tests/test_cli.py
  - tests/test_session.py
  - tests/test_task.py
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
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_batch.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_review.py
  - tests/test_package.py
budget_usd: 27
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      `spec_review.run_spec_review(container, *, system_prompt, prompt,
      agent)` calls `agent` once, with the container, the prompt, and
      `implement.agent_options` of that system prompt,
      `SPEC_REVIEW_MAX_TURNS`, `SPEC_REVIEW_BUDGET_USD` and
      `review.REVIEW_TOOLS`. It passes nothing else. It returns a
      `SpecReviewSession` of the turn's text, cost, `session_id` and
      `num_turns`, with no error and no `resets_at`. A turn that raises
      `implement.AgentFailed` gives that failure's text as `error`, with its
      attempt's fields, or empty ones when it carries none. A turn whose
      rate-limit status is `rejected`, returned or raised, gives no error and
      keeps its cost. Its `resets_at` is the `int` that
      `session._resets_at_fields` passes, or `UNREADABLE_RESET`, 1, where
      that passes none. Any other raise propagates. The witness drives a
      returned rejection, raised ones carrying `10**20`, `None`, `"soon"`,
      `True` and a float, a status other than `rejected`, a failed turn with
      an attempt and one without, and a `RuntimeError`.
    witness: tests/test_spec_review.py::test_a_spec_review_session_returns_a_rejected_window_as_a_reset_time
  - claim: >-
      `cli._stack_review(*, pinned, repo, out_dir)` returns a callable that
      takes a candidate and its layer. Given a layer, it fetches the branch
      `scheduler._branch` names for the layer's spec id, from the pinned url
      into the pinned mirror. It seeds the cell at the fetched head. Given
      `None`, it fetches nothing and seeds the cell at the pinned
      `base_sha`. A fetch that raises
      `ParentGone` propagates, and no cell comes up. The system prompt is
      the agent file .claude/agents/spec-reviewer.md at the pinned
      `base_sha`, after its frontmatter, never the operator's copy or the
      mirror's `HEAD`. A `base_sha` with no such file raises `ValueError` naming the path, and
      no cell comes up. The cell is `end_review.layer_cell` over `repo`, the
      pinned mirror, `.saffron/` exported at the pinned `base_sha` under
      `out_dir`, and that export's `thread_env`. The prompt holds
      `.saffron/specs/` and the candidate's file name, `base: ` and the
      seeded tree, and `is a snapshot of the base`. The agent is
      `implement.run_agent` bound to `session.TURN_TIMEOUT_S` and the
      candidate's spec id. The callable returns what `run_spec_review`
      returns, a rejected window's reset time included.
    witness: tests/test_cli.py::test_a_spec_review_reads_the_base_agent_file_in_a_cell_at_its_predecessors_head
  - claim: >-
      `cli._stack_mint(*, pinned, repo, ledger)` returns a callable that
      takes a candidate. Each call upserts the repo at the pinned url, with
      `repo`'s name, the pinned mirror and no `policy_sha`. It creates a run
      at the pinned `base_sha` with no batch, then a task, and returns the
      task's id. The task carries the candidate's spec id and `spec_sha`,
      the branch `scheduler._branch` names, the spec's `risk` and `budget_usd`,
      `context.prompt_sha()` and no `policy_sha`. Two calls for one spec
      give two runs and two tasks. A repo already on record keeps its
      `policy_sha`. The witness drives a repo on record and one that is
      not.
    witness: tests/test_cli.py::test_the_stack_mint_opens_a_run_at_the_pinned_base_and_a_task_per_call
  - claim: >-
      Given a `CellSpec` whose `task_id` is set, `run_one_cell` creates no
      run and no task. Its attempts and state go on that task, and its
      outcome carries that task and the task's run. After it loads the
      exported policy, it calls `Ledger.record_policy` only where the
      task's `policy_sha` differs. A `task_id` that names no task raises
      `ValueError` before any cell comes up. With `task_id` unset, it mints
      its own run and task. The witness drives a minted task with no
      policy, the same task again after `RATE_LIMITED`, an older
      `GATE_ERROR` task on its own run with the policy already recorded, a
      missing task, and no task.
    witness: tests/test_session.py::test_a_cell_given_a_task_runs_on_it_and_its_run_and_mints_neither
  - claim: >-
      `run_task` takes a keyword `task_id`, `None` by default, and builds
      its `CellSpec` with that `task_id`. The witness drives `9` and the
      default.
    witness: tests/test_task.py::test_run_task_hands_its_cell_the_task_it_was_given
  - claim: >-
      `cli._stack_runner`'s runner passes `run_task` the candidate's
      `task_id`, never its predecessor's, with a predecessor and with none.
      `cli._batch_runner`'s runner passes `run_task` no `task_id`, even for a
      candidate that carries one.
    witness: tests/test_cli.py::test_only_the_stack_runner_hands_run_task_the_candidates_task
  - claim: >-
      `saffron batch --stack` builds `_stack_review` and `_stack_mint` once
      each, with the `PinnedBase` built from readiness, the resolved
      `--repo`, the ledger `main` opened and `main`'s `out_dir`. It passes their callables
      to `run_stack_batch` as `review` and `mint`. When readiness fails, it
      builds neither and passes `None` for both.
    witness: tests/test_cli.py::test_a_stack_batch_passes_run_stack_batch_its_spec_review_and_its_mint
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
spec's cell is cut from. Its prompt comes from `spec-reviewer.md`, so the
hand path and the batch share one text (`:152-157`).

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Step 6 is three specs, and this is the last.** `SA-0149` reads a review
and routes each spec on it, through an injected `review` callable.
`SA-0155` gives each review a task and a record. It calls an injected
`mint` for a spec with no task to resume, before its first review. A spec
re-queued with a task at its `spec_sha` is reviewed and run on that task
(`DESIGN.md:387`). This spec builds the production `review` and `mint`,
passes both from `saffron batch --stack`, and has the cell run on the task
the review is recorded on.

**What the tree base holds.** This spec's tree base is `SA-0155`'s head.
The chain below it runs `SA-0135`, `SA-0136`, `SA-0142` to `SA-0146`,
`SA-0153`, `SA-0154`, `SA-0157`, `SA-0159`, `SA-0147`, `SA-0148`,
`SA-0149` and `SA-0155`. Every line number below was read at `24e8152f`,
where none of their code exists. So `cli.py`, `task.py` and `session.py` are cited by
symbol where the chain edits them. This spec consumes these names.

- From `SA-0143`: `run_stack_batch` and `cli._stack_runner`. The runner
  takes a candidate and its predecessor, fetches the predecessor's branch,
  and calls `run_task` with a `Handoff`. `task.py` and `cli.py` import
  `scheduler._branch`.
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
  `mint` keyword takes a candidate and returns a `task_id`. The runner
  gets the candidate with `task_id` set to the task the review is
  recorded on, minted or resumed. `SA-0155` records the review's attempt,
  cost and fact on that task, and attaches its run to the batch.
- From `SA-0148`: the wait. A reset time is readable when it falls after
  the clock's now and within six hours. Any other waits one hour.

**How a cell comes by its task today.** `_drive_cell` exports `.saffron/`
at `base_sha` and loads the policy from it (`saffron/cell/session.py:1650`,
`:1662`). It upserts the repo, creates a run at `base_sha`, and creates a
task with that `policy_sha` and `context.prompt_sha()` (`:1688-1707`).
Nothing reads a task id from `CellSpec` (`:250-303`). `run_task` builds
the `CellSpec` and calls `run_one_cell` (`saffron/task.py:303-326`). So a
spec `SA-0155` minted a task for would get a second task, and the review
would sit on a task with no cell. `Ledger.record_policy` writes a task's
policy after it exists (`saffron/ledger.py:1100-1107`), and PACKAGE calls
it only when the value differs (`saffron/phases/package.py:800-801`). The
one method that reads a task's own column, `task_policy_sha`, reads
`policy_sha` alone (`saffron/ledger.py:1090-1098`). No method returns a
task's `run_id`.

**How a critic session runs today.** `review.run_lens` builds
`agent_options` with `REVIEW_TOOLS`, `Read`, `Glob` and `Grep`, and calls
the agent (`saffron/phases/review.py:35`, `:208-236`). It calls it again
only to repair a report that is not the schema (`:244-292`). No Bash, so
the session cannot change the tree it reads. `implement.run_agent` takes
`spec_id` with no default (`saffron/phases/implement.py:190-204`).
`AgentFailed` carries the attempt of a turn that failed, or `None`
(`:54-71`). `stop_on_rejected` raises `RateLimited` on a rejected window,
from a returned turn or a failed one (`saffron/cell/session.py:159-181`,
`:230-238`). `_resets_at_fields` passes a clean `int` and turns anything
else into `None` (`:150-156`).

**What the agent file says.** `.claude/agents/spec-reviewer.md` has a
frontmatter block and a body. Its inputs are `spec:`, `base:` and
`history:` (`:12-20`). A prompt that says the tree is "a snapshot of the
base" lets it read the working tree with Read, Grep and Glob (`:25-27`).
Its report ends in a fenced `json` findings block (`:149-153`), which
`SA-0149` reads.

## Problem

Build five things.

1. **The session.** In `saffron/spec_review.py`, add
   `SPEC_REVIEW_MAX_TURNS` of 90, `SPEC_REVIEW_BUDGET_USD` of 6.0,
   `UNREADABLE_RESET` of 1, and `run_spec_review`, as criterion 1 states.
   Read the rate-limit status with `session.terminal_for_rate_limit`, on
   the returned attempt or the failed one. Call the agent directly, not
   through `stop_on_rejected`, so a rejected turn's cost reaches the
   session.
2. **The review callable.** In `saffron/cli.py`, add `_stack_review`, as
   criterion 2 states. Read the agent file with `git_mirror.file_at`. Take
   its body with `intake._FRONTMATTER`, whose second group is the text
   after the first closing fence. Export `.saffron/` with
   `git_mirror.export_saffron_dir` under `out_dir`, in a directory named
   for the spec id, and load its policy. Build `LayerFields` with the
   spec's id, `_branch` of it, `base` and `head` both the seeded tree, and
   `pr_url` and `known` empty. The prompt is `spec:`, `base:` and
   `history:` lines, then the snapshot sentence. The `history:` line says
   a batch has no history rows. Reach `package_phase.fetch_parent_branch`,
   `git_mirror.file_at`, `git_mirror.export_saffron_dir`,
   `end_review.layer_cell` and `implement.run_agent` through their modules
   at call time, since the witness replaces them there.
3. **The mint.** In `saffron/cli.py`, add `_stack_mint`, as criterion 3
   states.
4. **The cell on the given task.** Add `task_id: int | None = None` to
   `CellSpec`. In `_drive_cell`, where the run and task are created, a set
   `task_id` takes the task and its run instead, as criterion 4 states.
   Add `Ledger.task_run(task_id)`, which returns the task's `run_id` and
   raises `ValueError` for a task that does not exist. Add `task_id` to
   `run_task`, as criterion 5 states. `_stack_runner` passes
   `candidate.task_id` to it.
5. **The wiring.** In `_batch`'s `--stack` path, build both callables
   where `_stack_runner` and `_stack_end_review` are built, and pass them
   to `run_stack_batch`, as criterion 7 states.

Two docstrings in `saffron/ledger.py` become false. `attach_run_to_batch`
says `run_one_cell` is the only call that mints a run (`:849-850`), and
`_stack_mint` mints one too. `tasks_by_spec` says `cell/session.py` mints
a run and a task on each invocation (`:690-691`), which a set `task_id`
now stops. Reword both.

## Out of scope

- **The review's record and its spend.** `SA-0155` records the attempt,
  the fact and the state, and attaches the run. So `_stack_review` takes
  no ledger, and `run_spec_review` records nothing. A second attempt
  written here would count the review's cost twice in `batch_spend`.
- **Revision rounds.** They are `SA-0150`'s. Every blocker still routes
  `escalate`.
- **Concurrent reviews.** They wait for per-cell network names
  (b-6a692d).
- **History rows for check 4.** `driver.py` lives in `.claude/skills/`,
  a tool of this repository, and core invokes declared gates, never tools
  (§2.1). The session has no Bash either. So check 4 has no rows in a
  batch, and says so.
- **A repository with no `spec-reviewer.md`.** Its reviews each raise, and
  `SA-0155` records each as an errored review. Two in a row end the batch
  `INFRASTRUCTURE`. ADR 7 names this file as the one text.
- **The resumed task's run.** A task a spec re-queued on stays on the run
  it was created on, at an older `base_sha`. The cell still runs at the
  night's pinned base, since `CellSpec.base_sha` pins the gates and the
  tree. No fact moves a task to another run.
- **The prompt tree's digest.** `context.prompt_sha()` digests
  `saffron/agents/prompts/`, and the agent file is not there. A change to
  it shows in no task's `prompt_sha`.
- **The vocabulary.** `CONTEXT.md` calls a spec review a delegate's
  advisory read, and its **Critic cell** entry names a patch applied. A
  spec review in the batch fits neither. Backlog item b-466005 files both
  by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base runs a spec
review session. None mints a task outside a cell, or reads a task id
from `CellSpec`. So each criterion declares a witness and no mutant, and
`witness` reports `skip` for each.

**Every witness fails with the source reverted.** Criterion 1 imports
`run_spec_review`, which the tree base lacks. Criteria 2, 3 and 7 call or
replace `cli._stack_review` and `cli._stack_mint`. Criterion 4 builds
`CellSpec(task_id=...)`, and criterion 5 passes `run_task` a `task_id`.
Criterion 6's stack half asserts a `task_id` the reverted runner never
passes. Import each new name inside the test body.

**A `run_task` double that names its keywords.** `_stack_runner` now
passes `task_id`. A double in `tests/test_cli.py` that declares its
keywords with no `**kwargs` then raises `TypeError`. Add `task_id=None`
to each such double and change nothing else in it.

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
| the same with reset `None`, `"soon"`, `True` and 1755800000.0 | error `None`, 1, 0.125 |
| raised `AgentFailed("idle bound")`, text `half`, cost 0.0625 | `half`, 0.0625, `idle bound`, `None`, `s-1`, 7 |
| raised `AgentFailed("no result")` with no attempt | empty text, 0.0, `no result`, `None`, `None`, 0 |
| raised `RuntimeError("runner died")` | raises |

Each rejected case asserts `type(resets_at) is int`. These fail it, each
measured:

- `stop_on_rejected` around the agent, which raises `RateLimited`
- a rejection read from a returned turn only, or a failed one only
- `None` where the reset time cannot be shaped, which `SA-0149` routes
  `error` and counts as an abort
- the raw reset value, or 0 in place of 1
- the failure's text kept as `error` on a rejected turn
- a failed turn's cost or `session_id` dropped
- `IMPLEMENT_TOOLS`, or the turns and budget swapped
- every exception caught

**Why 1 and not 0.** `SA-0148` waits an hour for a reset time at or before
now. `SA-0149` routes `wait` when `resets_at` is set. A check written as
`if review.resets_at:` reads 0 as unset, and routes the session `error`.

**Criterion 2's witness** builds a git repo in `tmp_path` as the mirror,
with `tests/test_cli.py`'s `_git` and `_rev_parse`. Commit `bare` holds
`.saffron/policy.yaml` with `thread_env` `X: bare`, and no agent file.
Commit `base` sets `X: base`, and the agent file
`---\nname: r\n---\nat base\n---\nsecond half\n`. A last commit sets `X:
head` and the agent file `head`. The `repo` passed holds its own agent
file, `in the working copy`. It replaces these through `monkeypatch`.

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
"<id>-x.md"`. The witness pins `base` and calls the callable four times:
`SY-1` with no layer, `SY-2`, whose `depends_on` is `SY-9`, on the layer
`SY-7`, and `SY-3` on the layer `SY-8`, which raises `ParentGone`. Then it
pins `bare` and calls it for `SY-4`, which raises `ValueError` matching
`spec-reviewer.md`. It asserts:

- `SY-1`'s session is `rev`, 0.5, no error, no reset, `s-1` and 7 turns.
  `SY-2`'s is `resets_at` 1, no error, cost 0.25.
- the fetches are `saffron/SY-7` then `saffron/SY-8`, on the pinned
  mirror and url.
- two `cell_up` calls, seeded at `base` then `"d" * 40`, and two
  `cell_down` calls. Each has `repo`, the pinned mirror and `thread_env`
  `{"X": "base"}`. Its `gates_dir` sits under `out_dir`, and holds a
  `policy.yaml` reading `X: base`.
- two agent calls, each in the container its `cell_up` got. The system
  prompt is exactly `at base\n---\nsecond half\n`. The prompt holds
  `.saffron/specs/<id>-x.md`, `base: ` with the seeded tree, and `is a
  snapshot of the base`. It holds no part of `tmp_path`. The options hold
  `REVIEW_TOOLS` and the two constants. `timeout_s` is
  `session.TURN_TIMEOUT_S`, the spec ids are `SY-1` then `SY-2`, and no
  call resumes.

These fail it, each measured:

- the agent file read from `repo`, or from the mirror's `HEAD`
- the body split on every `---`, or the frontmatter kept
- the cell seeded at `base_sha` for every spec, with or without the fetch
- the branch taken from the candidate's `depends_on[0]`
- `stop_on_rejected` around the agent
- a `ParentGone` caught and the cell seeded at `base_sha`
- `.saffron/` exported at the mirror's `HEAD`
- the export's absolute path in the prompt
- no `timeout_s`, no `spec_id`, or an empty `thread_env`
- a missing agent file run with no body

**Criterion 3's witness** opens a `Ledger` in `tmp_path` and upserts a
repo at `https://github.com/o/r.git`, named `old`, with `policy_sha`
`"p" * 64`. It pins `base_sha` `"a" * 40`. The candidates' `spec_sha` is
`"c" * 64`. It mints `SY-1`, with `budget_usd` 7.5 and `risk` `elevated`,
twice, then `SY-2` with the defaults. It asserts three distinct task ids,
each on its own run. Each run is at `"a" * 40`, on the upserted repo,
with no `batch_id`. Each task is `QUEUED`, with no `policy_sha`, and
`prompt_sha` equals `context.prompt_sha()`. `SY-1`'s rows carry 7.5 and
`elevated`, and `SY-2`'s carry 12.0 and `standard`. The one repo row now
carries `repo`'s name and the pinned mirror, and still `"p" * 64`. Last,
it mints `SY-1` over a fresh `Ledger` with no repo row. That task's run
hangs from a repo at the pinned url with no `policy_sha`. These fail it,
each measured:

- the run created at the candidate's `spec_sha`
- no `prompt_sha`, or no `risk`, or no `budget_usd`
- the repo upserted with `""` for its policy, which overwrites it
- one run reused across calls
- the repo looked up with `resolve_repo_id` in place of the upsert

**Criterion 4's witness** follows
`test_a_wall_on_the_plan_turn_is_not_the_task_failing`
(`tests/test_session.py:4161-4180`), with `_stub_the_runtime`, `_drive`,
`_spec` and `_rejected`. `_drive` opens `tmp_path / "ledger.db"` itself
(`:1307`). So the witness opens that file first and closes it before
the first drive.

- It upserts a repo and creates an older run at `"e" * 40`. On it, a task
  for `SY-1` has the policy the drive exports, one closed attempt, and
  state `GATE_ERROR`. That policy is the SHA-256 of `gates: {}\n`, which
  `_drive` writes by default (`:1221`).
- It creates a second run at `"b" * 40` and a task on it with no policy,
  the minted task.
- It wraps `Ledger.record_policy` to record `(task_id, policy_sha)` and
  then call through.

It drives the minted task with a rejected plan turn, then the minted task
again with a plan and an implement turn. It then drives the older task,
and then task 999. It asserts:

- the first outcome is the minted task and its run, `RATE_LIMITED`. The
  second is the minted task and its run, and the third the older task and
  the older run.
- task 999 raises `ValueError`, and its cell created no network.
- `record_policy` was called once, for the minted task.
- two tasks and two runs, and at least two attempts on each task.
- each task's state is its last outcome's, so the older task is no
  longer `GATE_ERROR`.

It then drives once with no `task_id` and asserts a new task on a new run.
These fail it, each measured:

- a run created for a given task, which makes three runs
- `record_policy` called always, or never
- the given task ignored, which mints a task per drive
- a `task_run` that returns 0 for a missing task

**Criterion 5's witness** follows `_drive` in `tests/test_task.py:24-86`,
with `_push`. It wraps `task_module.CellSpec` to record each one built.
It replaces `task_module.run_task` with `functools.partial(run_task,
task_id=9)` for one drive, then restores it for a second. It asserts the
two `task_id`s are 9 then `None`. A `CellSpec` built without the keyword
fails it, measured.

**Criterion 6's witness** replaces `cli.run_task` with a double that
records its keywords. It replaces the fetch `_stack_runner` makes, where
`_stack_runner` reads it, with one that returns `"d" * 40`. It calls
`_stack_runner`'s runner on `SY-1` with `task_id` 7 and no predecessor,
then on `SY-2` with `task_id` 8 and the predecessor `SY-1` with `task_id`
3. It calls `_batch_runner`'s runner on `SY-5` with `task_id` 5. It
asserts `run_task` got 7, then 8, then no `task_id` or `None`. These fail
it, unmeasured, since `_stack_runner` is not at `24e8152f`:

- the stack runner that drops the candidate's `task_id`, which lets the
  cell mint a second task
- the predecessor's `task_id` passed, which runs `SY-2` on `SY-1`'s task
- the same pass-through added to `_batch_runner`, which runs a plain
  batch on a re-queued task and changes what gate 0 sees

**Criterion 7's witness** follows `SA-0157`'s wiring witness, with
`_readiness_passes` and `_fake_batch_resolution`
(`tests/test_cli.py:2603-2640`). It replaces `cli._stack_review` and
`cli._stack_mint` with recorders that record their keywords and return
two distinct sentinels. It replaces `cli.run_stack_batch` with a fake
that records its ledger and keywords and returns `DRAINED`. It runs `main`
with `batch --stack` twice, once with readiness passing and once failing,
as `SA-0144`'s witness sets each up. With readiness passing it asserts
one call of each recorder. Each got the pinned base `_readiness_passes`
returns, the resolved `--repo` and `main`'s `out_dir`. The mint's
`ledger` is the one the fake received. The fake got the two sentinels as
`review` and `mint`. With readiness failing it asserts no recorder call,
and `None` for both keywords. These fail it, unmeasured, since the
`--stack` path is not at `24e8152f`:

- `review` passed without `mint`, which `SA-0155` refuses with
  `ValueError`
- either callable built before readiness, on a base not yet pinned
- a mint over a ledger other than `main`'s

**How the lists were measured.** A throwaway prototype ran on 2026-09-23
at `24e8152f`, on the host's git. It stood in for `SpecReviewSession`,
`LayerFields` and `layer_cell` as the consumed names above state them.
It built `run_spec_review`, `_stack_review`, `_stack_mint`,
`Ledger.task_run`, `CellSpec.task_id` and `run_task`'s keyword, with
witnesses for criteria 1 to 5. The right build passed all five. Each
wrong version listed as measured was applied as a text edit, and each
failed its own witness. Criteria 6 and 7 need `SA-0143`'s and
`SA-0144`'s code, which is not at `24e8152f`.

**What the witnesses leave undriven.**

- A raise from the export, the policy load or `layer_cell` inside the
  review callable. Each propagates, and `SA-0155` records the review as
  errored.
- A `_resets_at_fields` value that is a clean `int` but past or far
  ahead. `SA-0148`'s wait reads those, and waits the hour.
- An agent file with no frontmatter at all. `_FRONTMATTER` does not match
  it, so it raises the same `ValueError` as a missing file.
- Two reviews of one spec in a night. Each exports under the same
  directory, and the export clears it first
  (`saffron/repos/mirror.py:173-187`).

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` and `saffron/cell/**` are in `elevate_on`,
so `size` blocks at the `feature` ceiling of 3000 tokens
(`saffron/gates/core/size.py:26`). The prototype, formatted by
`ruff format`, measured 1965 changed tokens with `size_gate`'s own count.
`saffron/cli.py` took 303, `saffron/spec_review.py` 186, `session.py` 40,
`ledger.py` 48 and `task.py` 7. The witnesses for criteria 1 to 5 took
1381, about 90 of it imports their files already carry. Criterion 6 and
7's witnesses, the wiring, one runner line and the two docstrings add
about 380. That is about 2250 tokens, 75% of the ceiling. Keep test
helpers shared and docstrings short.
