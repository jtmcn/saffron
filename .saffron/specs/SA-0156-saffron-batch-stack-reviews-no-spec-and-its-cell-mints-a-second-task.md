---
id: SA-0156
title: saffron batch --stack reviews no spec, and mints no task for a review to sit on
type: feature
priority: 1
depends_on: [SA-0175]
touches:
  - saffron/cli.py
  - saffron/ledger.py
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
  - saffron/spec_review.py
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
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_spec_review.py
  - tests/test_policy.py
  - tests/test_context.py
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
      `cli._stack_review(*, pinned, repo, out_dir)` returns a callable that
      takes a candidate and its layer. Given a layer, it fetches the branch
      `scheduler._branch` names for the layer's spec id, from the pinned url
      into the pinned mirror, and seeds the cell at the fetched head. Given
      `None`, it fetches nothing and seeds the cell at the pinned
      `base_sha`. A fetch that raises `ParentGone` propagates, and no cell
      comes up. Each call exports `.saffron/` at the pinned `base_sha` into
      `out_dir / "spec-review" / <spec id>`, and loads that export's
      policy. An export with no `policy.yaml` reads as an empty `Policy`.
      The system prompt is `spec_review.spec_review_system_prompt`
      of that policy over `context.PROMPTS_DIR`. It is never filled from
      the operator's checkout or the mirror's `HEAD`. Building the callable
      reads nothing. The cell is `end_review.layer_cell` over `repo`, the
      pinned mirror, that export and its `thread_env`, called with
      `spec_session=True`, on `LayerFields` whose `branch` is the
      candidate's own. The prompt holds `.saffron/specs/` and the
      candidate's file name, `base: ` and the seeded tree, and `is a
      snapshot of the base`. It names no tool path: the witness checks
      `/opt/`, `pytest`, `uv run`, `make check`, `.claude` and `://`. The
      callable calls
      `spec_review.run_spec_review` once, with the cell's container, that
      system prompt and that prompt. Its agent is `implement.run_agent`
      bound to `spec_review.SPEC_REVIEW_TIMEOUT_S` and the candidate's spec
      id. The callable returns what `run_spec_review` returns.
    witness: tests/test_cli.py::test_a_spec_review_fills_cores_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head
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
      Once readiness passes, `saffron batch --stack` builds `_stack_review`
      and `_stack_mint` once each. It passes the `PinnedBase` built from
      readiness, the resolved `--repo`, the ledger `main` opened and
      `main`'s `out_dir`. It passes their callables to `run_stack_batch` as
      `review` and `mint`. It exports no `.saffron/` for them before
      `run_stack_batch` runs. When readiness fails, it
      builds neither callable and passes `None` for both. `saffron batch`
      without `--stack` builds neither. The witness drives all three paths.
    witness: tests/test_cli.py::test_a_stack_batch_wires_its_spec_review_and_mint_once_readiness_passes
---

## Context

Backlog item **b-792ab2**, step 6 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that spec review runs inside a stack batch, before each spec's
first cell. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "Writing and
reviewing specs inside the batch", is the design (`:158-225`). It runs
each review as a host-invoked session in a critic cell, seeded at the
tree the spec's cell is cut from (`:160-162`).

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Step 6 is six specs, and this is the last.** `SA-0149` reads a review
and routes each spec on it, through an injected `review` callable.
`SA-0155` gives each review a task and a record. It calls an injected
`mint` for every spec before its first review, whatever `task_id` the
candidate carries. The operator decided that on 2026-09-24. `SA-0168`
runs the cell on that task. `SA-0169` runs a spec session's `Bash` in its
critic cell as an unprivileged user. `SA-0175` builds the session and
core's prompt for it. This spec builds the production `review` and
`mint`, and passes both from `saffron batch --stack`.

**What the tree base holds.** This spec's tree base is `SA-0175`'s head.
The chain below it runs `SA-0135`, `SA-0136`, `SA-0142` to `SA-0146`,
`SA-0153`, `SA-0154`, `SA-0157`, `SA-0159`, `SA-0147`, `SA-0148`,
`SA-0149`, `SA-0155`, `SA-0168`, `SA-0169` and `SA-0175`. Every line
number below was read at `2bb34a8d`, where none of their code exists. So
`cli.py` and `ledger.py` are cited by symbol where the chain edits them.
This spec consumes these names.

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
- From `SA-0149` and `SA-0155`: `run_stack_batch`'s `review` keyword
  takes a candidate and the last layer's candidate or `None`, and returns
  a `SpecReviewSession`. Its `mint` keyword takes a candidate and returns
  a `task_id`. Given `review` and no `mint`, `run_stack_batch` raises
  `ValueError`. `SA-0155` records the review's attempt, cost and fact,
  and attaches its run to the batch.
- From `SA-0168`: `CellSpec.task_id`, and the cell that runs on it.
- From `SA-0169`: a spec session's `Bash` runs as an unprivileged user in
  the critic cell `layer_cell` brings up. It cannot write the runner or
  its files. `layer_cell` grants the wrapper its two capabilities only
  when called with `spec_session=True`, so this spec passes that. Without
  it the wrapper runs nothing, and the review loses its `Bash`.
- From `SA-0175`, in `saffron/spec_review.py`: `run_spec_review(container,
  *, system_prompt, prompt, agent)`, which runs the review turn and its
  extraction turn and returns a `SpecReviewSession`.
  `spec_review_system_prompt(policy, *, prompts_dir)`, which fills core's
  `spec-review.md` from a `Policy`. `SPEC_REVIEW_TIMEOUT_S`, 1800.0.

**How a turn is bound today.** `implement.run_agent` takes `spec_id` with
no default, and `timeout_s` with a default of 3600
(`saffron/phases/implement.py:192-205`). `session.TURN_TIMEOUT_S` is 900
seconds (`saffron/cell/session.py:63`). A spec review needs longer, so
`SA-0175` gives it its own bound.

**Where the prompt comes from.** ADR 7 makes the spec prompts core's.
"The spec prompts, the end-review lens prompts and the tags blockers
route by are core's, in `saffron/agents/prompts/`"
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:63-64`).
"A target repo supplies none of them, so ADR 2 holds" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:64-65`). A
repo's facts reach them "as input the host fills from what the repo
declares in `.saffron/`" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:65-66`). The host reads those "at the
`base_sha` export, never at a layer's head" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:67`). Core "demands nothing of a
repo" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:195-196`). The design record adds that this repo's
`.claude/agents/spec-reviewer.md` stays the hand path's own, and differs
from core's by design (`docs/superpowers/specs/2026-09-23-stack-batch-design.md:164-168`).
So the review callable reads no prompt file from the repo. It fills
core's template from the policy it exports at the pinned `base_sha`. A
repo that declares nothing for the prompt is reviewed all the same.
`_protected_paths` already reads a base with no `policy.yaml` as one
that declares nothing (`saffron/cli.py:290-294`). The review callable
does the same, so it demands no policy of a repo.

**How a policy is read from an export today.** `_resolve_queue` exports
`.saffron/` at the pinned base (`saffron/cli.py:606-608`).
`_protected_paths` calls `load_policy` on an export
(`saffron/cli.py:295-296`). The export clears its destination first
(`saffron/repos/mirror.py:196`).

**Where `Bash` departs from §5.5.** §5.5 keeps model-authored code out of
the critic cell (`DESIGN.md:1065`). There it would run as root beside the
runner a lens re-executes. A spec session's `Bash` runs commands the
model writes in that cell. `SA-0169` narrows the departure: those
commands run as a user that cannot write the runner or its files. The
operator records the narrowed departure in `DESIGN.md` by hand.

## Problem

Build three things.

1. **The review callable.** In `saffron/cli.py`, add `_stack_review`, as
   criterion 1 states. Export `.saffron/` with
   `git_mirror.export_saffron_dir` into `out_dir / "spec-review" / <spec
   id>`. That keeps it out of `out_dir / <spec id>`, the task's own
   directory, which the export would clear. Load its policy with
   `load_policy`, or take `Policy()` where the export holds no
   `policy.yaml`. Build `LayerFields` with the spec's id, `_branch` of it,
   `base` and `head` both the seeded tree, and `pr_url` and `known` empty.
   The prompt is a `spec:` line and a `base:` line, then the snapshot
   sentence. Three lines follow, as `SA-0160`'s writer prompt holds them.
   The account reads the checkout and cannot write it. Anything that
   writes runs in a clone in the cell's temporary directory. A tool whose
   name does not resolve is called by its full path. `SA-0169` measured
   all three. Reach `package_phase.fetch_parent_branch`,
   `git_mirror.export_saffron_dir`, `end_review.layer_cell`,
   `spec_review.run_spec_review` and `implement.run_agent` through their
   modules at call time, since the witness replaces them there.
2. **The mint.** In `saffron/cli.py`, add `_stack_mint`, as criterion 2
   states.
3. **The wiring.** In `_batch`'s `--stack` path, build both callables
   where `_stack_runner` and `_stack_end_review` are built, and pass them
   to `run_stack_batch`, as criterion 3 states. Building reads nothing,
   so either side of `_resolve_queue` is safe. Build them beside
   `_stack_runner`.

One docstring in `saffron/ledger.py` becomes false. `attach_run_to_batch`
says `run_one_cell` is the only call that mints a run
(`saffron/ledger.py:849-850`). It is false already, since `replay` mints
one (`saffron/replay.py:54`), and `_stack_mint` mints one too. Reword it
to name all three.

## Out of scope

- **The session and core's prompts.** They are `SA-0175`'s. This spec
  edits neither `saffron/spec_review.py` nor `saffron/agents/prompts/`.
- **This repo's hand path.** `.claude/agents/spec-reviewer.md` stays as
  it is, and no code here reads it.
- **The writer's prompt.** `SA-0160` adds core's writer prompt beside
  the review's.
- **The review's record and its spend.** `SA-0155` records the attempt,
  the fact and the state, and attaches the run. So `_stack_review` takes
  no ledger. A second attempt written here would count the review's cost
  twice in `batch_spend`.
- **Revision rounds.** They are `SA-0164`'s. Every blocker still routes
  `escalate`.
- **Concurrent reviews.** They wait for per-cell network names
  (b-6a692d).
- **The vocabulary.** `CONTEXT.md` calls a spec review a delegate's
  advisory read, and its **Critic cell** entry names a patch applied. A
  spec review in the batch fits neither. Backlog item b-466005 files both
  by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base builds a review
callable or mints a task outside a cell. So each criterion declares a
witness and no mutant, and `witness` reports `skip` for each.

**Every witness fails with the source reverted.** Each calls or replaces
`cli._stack_review` or `cli._stack_mint`. Import each new name inside the
test body.

**Criterion 1's witness** builds a git repo in `tmp_path` as the mirror,
with `tests/test_cli.py`'s `_git` and `_rev_parse`. It has three
commits. `bare` holds `.saffron/README` and no `policy.yaml`. `base` holds `.saffron/policy.yaml` with `thread_env` `X: base` and
`protected` `base/**`. `head` changes them to `X: head` and `head/**`.
The `repo` passed holds its own `.saffron/policy.yaml`, with `X:
checkout` and `checkout/**`. The witness replaces these through
`monkeypatch`.

- `package.fetch_parent_branch` records `(mirror, url, branch)`. It
  raises `ParentGone` for `saffron/SY-8`, and returns `"d" * 40` for the
  rest.
- `session.cell_up` records its keywords and adds its container to
  `created`. `session.cell_down` records its keywords.
  `runtime.remove_container` returns `None`.
- `end_review.layer_cell` is wrapped by a spy that records its fields
  and keywords and calls the original.
- `session.assert_bash_is_unprivileged` is replaced with a recorder of
  its container. With `spec_session=True`, `SA-0169`'s `layer_cell` runs
  that check through `runtime.exec_` against the container. The fake
  container would make a correct build raise.
- `implement.run_agent` declares `spec_id` and `timeout_s` as keywords
  with no default, so a binding left out raises `TypeError`. It records
  each call and returns a turn.
- `spec_review.run_spec_review` records its container, `system_prompt`
  and `prompt`. It calls its `agent` once, with that container, a prompt
  `x` and empty options. It returns a distinct sentinel per call.

Each candidate's path is `tmp_path / "export" / ".saffron" / "specs" /
"<id>-x.md"`. The witness pins `base` and builds the callable. It asserts
no `out_dir / "spec-review"` exists yet. It then calls the callable three
times: `SY-1` with no layer, `SY-2`, whose `depends_on` is `SY-9`, on the
layer `SY-7`, and `SY-3` on the layer `SY-8`, which raises `ParentGone`.
It asserts:

- the first two calls return their sentinels, and the third raises
  `ParentGone`.
- the fetches are `saffron/SY-7` then `saffron/SY-8`, on the pinned
  mirror and url.
- two `cell_up` calls, seeded at `base` then `"d" * 40`, and two
  `cell_down` calls. Each has `repo`, the pinned mirror and `thread_env`
  `{"X": "base"}`. Its `gates_dir` is `out_dir / "spec-review" / <spec
  id>`, and its `policy.yaml` holds `X: base`.
- two `layer_cell` calls, each with `spec_session=True`, on fields whose
  `branch` is `saffron/SY-1` then `saffron/SY-2`.
- two unprivileged checks, one per cell, each on the container its
  `cell_up` got.
- two `run_spec_review` calls, each with the container its `cell_up` got.
  Each system prompt equals `spec_review_system_prompt` of `load_policy`
  over that `gates_dir`, with `prompts_dir=context.PROMPTS_DIR`. It holds
  `` `base/**` ``, and neither `head/**` nor `checkout/**`. The prompt
  holds `.saffron/specs/<id>-x.md`, `base: ` with the seeded tree, and
  `is a snapshot of the base`. It does not contain `str(tmp_path)`. It
  contains none of `/opt/`, `pytest`, `uv run`, `make check`, `.claude`
  and `://`.
- two agent calls. `timeout_s` is `SPEC_REVIEW_TIMEOUT_S` and equals
  1800. The spec ids are `SY-1` then `SY-2`.

Last, it pins `bare`, builds a second callable, and calls it for `SY-4`
with no layer. The system prompt equals `spec_review_system_prompt` of
`Policy()`, and the cell's `thread_env` is empty.

These fail it:

- the policy loaded from `repo`, or exported at the mirror's `HEAD`
- a prompts directory other than `context.PROMPTS_DIR`
- the cell seeded at `base_sha` for every spec, with or without the fetch
- the branch taken from the candidate's `depends_on[0]`
- a `ParentGone` caught and the cell seeded at `base_sha`
- `.saffron/` exported into `out_dir / <spec id>`
- the export's absolute path in the prompt
- `layer_cell` called without `spec_session=True`
- the layer's branch in the fields, in place of the candidate's
- a tool path such as `/opt/venv/bin/pytest` in the prompt
- `session.TURN_TIMEOUT_S`, no `timeout_s`, no `spec_id`, or an empty
  `thread_env`
- the export run at build time, before any call
- a base with no `policy.yaml` refused, or read from `repo` instead

**Build the prompt in one place.** Build the review's prompt as one
string, in one spot, and pass it to `run_spec_review` as `prompt`.
`SA-0164` gives the callable a `spec_text` keyword beside
`(candidate, layer)`. It appends a sentence and the text, inside `<spec>`
tags, to that string.

**Criterion 2's witness** opens a `Ledger` in `tmp_path` and upserts a
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

**Criterion 3's witness** follows `SA-0157`'s wiring witness, with
`_readiness_passes` and `_fake_batch_resolution`
(`tests/test_cli.py:2603-2640`). It replaces these through `monkeypatch`:

- `cli._stack_review` and `cli._stack_mint`, with recorders that record
  their keywords and return two distinct sentinels.
- `cli.git_mirror.export_saffron_dir`, with a double that records each
  call.
- `cli.run_stack_batch`, with a fake that records its ledger and keywords
  and returns `DRAINED`. `cli.run_batch`, with one that records its call.

It runs `main` three times.

- With `batch --stack` and readiness passing, it exits 0. Each recorder
  was called once, with the pinned base `_readiness_passes` returns and
  the resolved `--repo`. The review got `main`'s `out_dir`, and the mint
  the ledger the fake received. The fake got the two sentinels as
  `review` and `mint`. The export double was not called before the fake.
- With readiness failing, neither recorder is called, and the fake gets
  `None` for both.
- `batch` without `--stack` exits 0. The plain fake was called once, and
  neither recorder was.

These fail it:

- `review` passed without `mint`, which `SA-0155` refuses with
  `ValueError`
- either callable built before readiness, on a base not yet pinned
- either callable built once per spec
- a mint over a ledger other than `main`'s
- either callable built without `--stack`

**Other fakes of `run_stack_batch`.** `SA-0144` and `SA-0157` fake
`run_stack_batch` in `tests/test_cli.py`. Each fake must accept the new
`review` and `mint` keywords, through `**kwargs` or by name. The file is
in `touches`, so edit each fake that refuses them. Where such a test
asserts the exact keywords the fake got, widen that assertion to allow
`review` and `mint`. Change nothing else in those tests.

**How the lists were measured.** A throwaway prototype ran on 2026-09-24
at `f2a08a9f`, on the host's git, over `SA-0168`'s prototype. It built an
earlier shape of this spec, whose prompt came from a file the policy
named. Criterion 2 and its wrong versions are unchanged from it, and
each wrong version failed its witness there. Criteria 1 and 3 changed
when ADR 7 made the prompt core's. Their lists are unmeasured in the new
shape, and so are both witnesses' reverted runs.

**What the witnesses leave undriven.**

- A raise from the export, the policy load or `layer_cell` inside the
  review callable. Each propagates, and `SA-0155` records the review as
  errored.
- A base whose `policy.yaml` is present and broken. The load raises
  `PolicyError`, and the review errors. Preflight fails readiness on such
  a base before the night starts (`saffron/preflight.py:493-500`).
- Two reviews of one spec in a night. Each exports under the same
  directory, and the export clears it first
  (`saffron/repos/mirror.py:182-196`).

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
estimate is about 1460 changed tokens, 49% of the ceiling. The earlier
prototype measured 466 tokens in `saffron/cli.py` and 14 in `ledger.py`.
Its start refusal and prompt-file read go, about 150, so `cli.py` runs
about 320. The witnesses run about 1110: criterion 1's about 490, the
mint's about 350, the wiring's about 250, and the fakes about 20.
