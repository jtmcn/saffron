---
id: SA-0154
title: No lens reads the joins between a stack's layers, and no cell exists to read a layer in
type: feature
priority: 1
depends_on: [SA-0153]
touches:
  - saffron/end_review.py
  - saffron/agents/prompts/end-review-join.md
  - tests/test_end_review.py
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
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/context.py
  - saffron/agents/findings.py
  - saffron/agents/artifacts.py
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/end-review-spec.md
  - saffron/agents/prompts/end-review-standards.md
  - saffron/agents/prompts/turns/**
  - tests/test_review.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_session.py
  - tests/test_cli.py
budget_usd: 28
max_attempts: 3
max_turns: 160
pending_symbols:
  - saffron/end_review.py::run_end_review
  - saffron/end_review.py::layer_cell
  - saffron/end_review.py::RESERVE_SHARE
  - saffron/end_review.py::LENS_BUDGET_USD
  - saffron/end_review.py::LENS_MAX_TURNS
  - saffron/end_review.py::layers
acceptance:
  - claim: >-
      `end_review.review_joins(ledger, batch_key, reserve_usd, specs, ...)`
      takes `review_stack`'s keywords and reads that batch's layers alone,
      in position order. With fewer than two layers it returns `None` and
      records nothing, whatever the reserve. Otherwise it records one `end_review` fact with the
      lens `join` under the top layer's task. While `reserve_usd` is below
      `budget_usd`, that fact is `not_reached` at 0, no cell is opened, and
      it returns `None`. Otherwise it opens
      `open_cell` once, on the top layer's fields. In that cell it runs the
      lens `join` once through `review.run_lens`, with `max_turns` and
      `budget_usd` as given. The prompt holds the stack's combined diff:
      `git diff` with `DIFF_FLAGS` over `<bottom head>^..<top head>` in
      `mirror`. It holds that range as text, each layer's spec body from the
      bottom up, and the standing instructions. The findings go through
      `record_findings` under the top layer's task, after its own. The fact
      is `reviewed` at the lens's cost, or `error` with its cost and error
      when the lens returns one. A raise from `open_cell` gives `error` at 0
      naming it. It returns that `LensReview`. The witness runs five
      batches on one ledger, and a batch key that names no layer.
    witness: tests/test_end_review.py::test_the_join_lens_reads_the_whole_stack_once_from_the_top_layers_cell
  - claim: >-
      `saffron/agents/prompts/end-review-join.md` asks for ADR 6's three
      joins in the design's words. It holds "a name one layer uses and
      another layer produces", "a name a layer produces and no later layer
      uses" and "work a layer redoes that an earlier layer already
      provides". It holds "do not manufacture one" in any case, and the
      fields `file`, `line`, `severity` and `claim` and the three
      severities, each in backticks. It holds `worktree.WORKTREE_MOUNT`, and
      no `probe` in backticks. It holds none of `.claude`, `CLAUDE.md`,
      `CONTEXT.md`, `DESIGN.md`, `driver.py`, `pytest`, `uv run`, `make
      check`, `ruff`, `prek`, `saffron/`, `docs/`, `/opt/` or `://`,
      matched without regard to case. Each check reads the raw file, never
      a filled prompt. The witness checks each of those fourteen strings.
    witness: tests/test_end_review.py::test_the_join_prompt_asks_for_adr_6s_three_joins_and_nothing_else
  - claim: >-
      `end_review.run_end_review(ledger, batch_key, reserve_usd, specs,
      ...)` calls `review_joins` and then `review_stack`. Each gets the same
      ledger, batch key, specs and keywords. `review_stack`'s reserve is
      `reserve_usd` less the join's cost, an errored join's included. A
      join of `None` leaves the reserve whole. It returns a frozen
      `StackReview` whose `join` is what `review_joins` returned and whose
      `layers` is what `review_stack` returned. The witness drives a join
      that ran, one that is `None` and one with an error.
    witness: tests/test_end_review.py::test_the_end_review_runs_the_join_lens_first_and_the_layers_on_what_it_left
  - claim: >-
      `end_review.layer_cell(fields, *, repo, mirror, gates_dir,
      thread_env)` is a context manager. It removes a leftover container of
      its own name, then calls `session.cell_up` with `tree_base` set to
      `fields.head`. It passes the repo, the mirror, the gates directory and
      the thread env it was given. It yields the container `cell_up` was
      given. It calls `session.cell_down` once, with the same network,
      volume, state, container and `created` set. It does so when
      `cell_up` raises, when the body raises, and when neither does. Each
      call's `note` takes that function's own arguments: `(step, detail)`
      for `cell_up`, and `(step, ok, detail)` for `cell_down`.
    witness: tests/test_end_review.py::test_a_layers_critic_cell_is_seeded_at_its_head_and_always_torn_down
  - claim: >-
      `review.LENSES` still names the three in-cell lenses, so no cell's
      REVIEW runs the join lens.
    witness: tests/test_review.py::test_the_declared_lenses_are_the_three_that_run
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 3 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 2 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "The end review",
is the design. Its paragraph "One lens reads the joins" names the join lens
and ADR 6's rubric. ADR 6
(`docs/adr/0006-work-larger-than-one-cell-is-a-composite-spec.md`) states
that rubric in three parts. Its principle 50 says that at the joins the
critic is the only full reader.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, cut from the head of the
layer below it, its **predecessor**. Once the last queued task settles, one
**end review** reads the stack. Two end-review lenses read each layer. One
join lens reads the joins between layers.

**This spec is the third of four for step 3.** `SA-0146` builds the Spec
and Standards lenses. `SA-0153` runs them over a stack, top down within a
reserve, and records each lens of each layer. This spec adds the join lens,
the critic cell a layer is read in, and the one call that runs the whole
end review. `SA-0157` wires that call into `saffron batch --stack`.
`SA-0147` then qualifies the findings.

**What the tree base holds.** This spec's tree base is `SA-0153`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`). The chain
`SA-0142` to `SA-0153` puts these there, so they are cited by symbol. Every
line number below was read at `e3020b3b`.

- `SA-0145` writes one `stack_layers` row per layer, keyed on record keys:
  `task_key`, `batch_key`, `position`, `spec_id`, `predecessor_key`,
  `predecessor_head` and `generation`. `batch_key` is the batch's id as
  text. `Ledger.record_stack_layer(task_id, *, position,
  predecessor_task_id, generation)` writes one.
- `SA-0146` adds `LayerFields`, with `spec_id`, `branch`, `pr_url`, `base`,
  `head` and `known`. `layer_fields(ledger, task_key)` fills one, and raises
  `ValueError` for a layer with no pushed head.
- `SA-0153` adds `LayerReview`, with `task_key` and `reviews`, and
  `review_stack`. Its arguments are `ledger`, `batch_key`, `reserve_usd`
  and `specs`. Its keywords are `mirror`, `open_cell`, `context_md`,
  `claude_md`, `prompts_dir`, `max_turns`, `budget_usd`, `agent` and
  `emit`. `open_cell` takes a layer's `LayerFields` and returns a
  context manager that yields a container name. It adds
  `Ledger.record_end_review(task_id, *, lens, status, cost_usd, error)`,
  whose row keys on `(task_key, lens)`. It adds `reserve_usd` and
  `end_review` to `run_stack_batch`. `end_review` runs once after the loop,
  with the batch's id as text, the reserve and each spec of the order by
  its id. `run_stack_batch` discards what it returns.

**How a lens runs.** `review.run_lens` runs one fresh session in the
container it is given, with `REVIEW_TOOLS` (`saffron/phases/review.py:35`,
`:208-293`). `run_lens` takes a required `spec_id` for its events
(`saffron/phases/review.py:216`), and this spec passes the top layer's. The
agent arrives already bound by `SA-0157`, so nothing here binds it again.
A lens id with no entry in
`_REPORTED` is parsed against the default model, which has no `probe`
(`saffron/phases/review.py:85-91`). `build_system_prompt` substitutes
`{spec}` verbatim and formats every other slot (`saffron/agents/context.py:174-198`).

**How a cell comes up today.** `cell_up` brings up the network, the proxy,
the repo's image, the isolation asserts and the worktree at `tree_base`
(`saffron/cell/session.py:866-972`). `cell_down` is its pair
(`:975-1025`). `_drive_cell` removes a leftover container of its name first
(`:1650`), and calls `cell_down` from a `finally` (`:2862`, `:2884-2891`). The
worktree's environment is `cell_env`, which carries the proxy and the
token (`:732-748`). `critic_cell` joins the network a task brought up, or
makes one with no proxy. Either way it applies a patch to the tree base
(`:1119-1234`). An end review runs after the loop, when no task's network
is up and there is no patch. So each layer's critic cell comes up through
`cell_up` at the layer's head, and nothing is applied to it.

**What a lens costs.** On 2026-09-23 the ledger held 392 `REVIEWING`
attempts, one per in-cell lens session. Their cost averaged $0.68 and
peaked at $1.80. Their turns averaged 11.8 and peaked at 41.

## Problem

Build three things.

1. **The join lens.** Add `saffron/agents/prompts/end-review-join.md`. It is
   a system prompt for a read-only session in the top layer's critic cell.
   It asks for ADR 6's three joins and nothing else, and names the three
   in the design's words. It carries the slots `{vocabulary}`, `{base}`,
   `{head}`, `{standing_instructions}`, `{diff}` and `{spec}`. `{base}` is
   the bottom layer's head followed by `^`, and `{head}` is the top
   layer's head. `{spec}` carries the layers, bottom first: one heading per layer with its spec
   id, branch and head, then its spec's body. The lens emits the
   `<output>` block the in-cell lenses emit. Each finding has `file`,
   `line`, `severity` and `claim`, and none carries a probe. Then add
   `review_joins` to `saffron/end_review.py`, with `review_stack`'s
   signature, as criterion 1 states. It finds the top layer's task id by
   its record key, as `Ledger._apply` does (`saffron/ledger.py:532-534`).
   `run_lens` gets the top layer's spec id, and the prompt is built with
   phase `REVIEW`, as `SA-0146` builds its own.
2. **The end review over a stack.** Add a frozen dataclass `StackReview`,
   with `join` and `layers`, and `run_end_review` to
   `saffron/end_review.py`. The join lens runs first. Each layer already
   had three in-cell lenses, and the joins had none (ADR 6, principle 50).
   So a short reserve spends on the joins before the layers. Add
   `LENS_BUDGET_USD` of 2.5, `LENS_MAX_TURNS` of 50 and `RESERVE_SHARE` of
   0.25 to `saffron/end_review.py`. `SA-0157` passes the first two as each
   lens's ceilings, and holds `RESERVE_SHARE` of `--budget` as the reserve.
   `SA-0157` gives the reason for a share.
3. **The critic cell.** Add `layer_cell` to `saffron/end_review.py`, as
   criterion 4 states. Its network is `saffron-cells`, the name
   `_drive_cell` uses (`saffron/cell/session.py:1639`). Its container,
   volume and state names carry the layer's spec id. Its `branch` is
   `fields.branch`. Reach `cell_up`,
   `cell_down` and `runtime.remove_container` through their modules at
   call time, since the witness replaces them there. Its two notes print
   their detail line.

**`SA-0147` reads the `StackReview`.** `run_end_review` returns it.
`SA-0157`'s callable returns it to `run_stack_batch`. `SA-0173` hands it
on to `follow_ups`, and `SA-0165` binds `SA-0147`'s `qualify` in that
`follow_ups` callable. `qualify` reads `StackReview.layers`, the `LayerReview` list top down, and
`StackReview.join`, a `LensReview` or `None`. The join's findings sit
under the top layer's task, the first entry of `layers`.

## Out of scope

- **Qualification.** Anchoring, probes, severity and grouping are
  `SA-0147`'s. For the join lens, `SA-0147` anchors against the combined
  diff. It rebuilds that range from the same `stack_layers` rows.
- **A revised layer's latest text in `{spec}`.** Each body comes from
  `specs`, the order's queued `Spec`s read at `base_sha`. A revised layer
  ran its latest recorded text, which `SA-0150` builds above this spec in
  the chain. `SA-0173` has `run_stack_batch` hand `end_review` that text,
  parsed, in place of the queued `Spec`. `review_joins` reads `specs` as
  given, so it needs no change then.
- **A probe on a join finding.** The join lens uses the default report
  model. The design says two parts of the rubric carry no probe, and names
  no model for the third.
- **A rate-limited lens.** `RateLimited` raises out of `run_lens`, so the
  join or the layer reads as `error`. The rate-limit wait is `SA-0148`'s.
- **An event log for the end review.** Its events print to the batch's
  output alone. No `events.jsonl` in the batch tree gains them.
- **The wiring.** `saffron batch --stack` passing a reserve and a callable
  that calls `run_end_review` is `SA-0157`'s. So are the agent, the inputs
  read at the pinned base, and the plan header. Until it lands nothing calls
  `run_end_review`, `layer_cell` or the three constants. They are
  `pending_symbols`, and the `dead` gate defers them while this spec is
  open (`.saffron/gates/dead.py:4-6`).
- **The spec-review session.** It is `SA-0156`'s, and `layer_cell` and
  the reserve are open to it.
- **The vocabulary.** `CONTEXT.md` has no entry for the join lens. Its
  **Critic cell** entry names a cell whose tree is a task's base with the
  exported patch applied. A layer's critic cell has no patch. Backlog item
  b-466005 files both by hand.

## Notes for the agent

**Every criterion but the last is new code.** No text at the tree base runs
a join lens. None seeds a cell at a layer's head or runs one end review. So
criteria 1 to 4 declare a witness and no mutant, and `witness` reports
`skip` for them. Criterion 5 is `preserves` and names a
test that passes now.

**Import every new name inside the test body.** `review_joins`,
`run_end_review`, `StackReview`, `layer_cell` and the three constants do
not exist at the tree base. A module-scope import fails collection when the
source is reverted, and `revert` reads that as `skip`.

**Criterion 1's witness.** Point `GIT_CONFIG_GLOBAL` at a file in
`tmp_path` that sets `diff.noprefix = true`, with `monkeypatch`. Build a
git repo in `tmp_path` as the mirror, and give every commit the message
`msg <file>`. On `main`, commit `a.txt` as commit `A`, then `m.txt` "moved
main". Then commit one file per spec, `<spec>.txt` holding "`<spec>`
layer", in this order: `TE-9`, `TE-3`, `TE-7`, `TE-4`, `TE-2`, `TE-6`,
`TE-8`, `TE-5`, `TE-1` and `TE-10`. `TE-7`'s commit also rewrites
`TE-9.txt` to "TE-9 layer v2", so one layer edits an earlier layer's file.

Build a `Ledger` with a `MemoryRecord`. Open five batches. For each spec,
create a run with `base_sha` `A` and its batch's id, then a task. Package
it `READY_FOR_REVIEW` at its commit, on the branch `saffron/<spec>`. Record
each batch's layers in the order shown, each on the layer one position
below it:

| batch | reserve | layers, in recording order |
|---|---|---|
| 1 | 1.0 | `TE-3` at 2, `TE-7` at 3, `TE-9` at 1 |
| 2 | 0.75 | `TE-4` at 1, `TE-2` at 2 |
| 3 | 4.0 | `TE-6` at 1, `TE-8` at 2 |
| 4 | 4.0 | `TE-5` at 1, `TE-1` at 2 |
| 5 | 0.5 | `TE-10` at 1 |

Record one correctness concern "in-cell c7" on `TE-7`. `specs` holds a
`Spec` for each, with the body "body `<spec>`", built in sorted id order so
its iteration order is not bottom-up by chance. `TE-3`'s body is "body
TE-3 {gap}". `open_cell` records the fields it is given. It raises
`RuntimeError("no cell for TE-8")` for `TE-8`, and yields `critic-<spec>`
for the rest. The agent double records each call's container, options and
keywords, and returns the next scripted reply. It raises `AssertionError`
with none left. Call 1 returns a concern "j7 join" on line 1 of `TE-7.txt` at a
cost of 0.25. Call 2 raises `implement.AgentFailed` with an attempt
costing 0.4. `budget_usd` is 1.0, `max_turns` 17, and `claude_md` one
line. Call `review_joins` once per batch, with its reserve. Then call it
with the key `6` and a reserve of 4.0. No batch has that key.

It asserts:

- two agent calls, in `critic-TE-7` then `critic-TE-1`. Each has
  `REVIEW_TOOLS`, `max_turns` 17, `max_budget_usd` 1.0 and no `resume`.
- `open_cell` given `TE-7`, `TE-8` and `TE-1`, in that order, each with
  its own head.
- call 1's system prompt holds "+TE-9 layer", "+TE-3 layer" and "+TE-7
  layer", and "diff --git a/TE-9.txt b/TE-9.txt". It holds "+TE-9 layer
  v2" and no "-TE-9 layer". It holds `TE-9`'s head,
  `^..` and `TE-7`'s head, joined. It holds "body TE-9", "body TE-3 {gap}"
  and "body TE-7" in that order, and the `claude_md` line. It holds none of
  "moved main", "msg TE-" and "+TE-4 layer".
- batch 1 returns a review of lens `join` at 0.25 with no error, whose one
  finding is "j7 join". Batch 2 returns `None`. Batch 3 returns an error
  naming "no cell for TE-8" at 0.0. Batch 4 returns an error at 0.4. Batch
  5 and the key `6` return `None`.
- four `end_reviews` rows, all lens `join`. `TE-7`'s is `reviewed` at
  0.25 with no error, and `TE-2`'s is `not_reached` at 0.0. `TE-8`'s is
  `error` at 0.0 naming "no cell for TE-8". `TE-1`'s is `error` at 0.4
  with an error.
- `TE-7`'s findings are "in-cell c7" of lens `correctness`, then "j7 join"
  of lens `join`, neither anchored. `TE-9`, `TE-3`, `TE-8`, `TE-1` and
  `TE-10` have none.

These fail it, each measured:

- the range from the run's `base_sha`, or from the bottom layer's
  `fields.base`, which holds "moved main"
- the range from the bottom layer's head with no `^`, or the top layer's
  own commit alone
- each layer's own diff, concatenated, which holds "-TE-9 layer"
- the reserve checked before the layer count, which writes a
  `not_reached` row for batch 5
- the layers ordered by spec id, or in the order they were recorded
- every batch's layers, which raises on the primary key
- the lens run once per layer above the bottom
- the cell opened on the bottom layer
- the reserve checked with a strict `>`, or against two lenses' budgets
- a lens not reached given no row, or returned as an empty review
- a lens's error ignored, so it reads `reviewed`
- a raise that propagates
- the findings recorded under the bottom layer's task
- a batch of one layer read as a stack, or a key with no layers read as one
- the layers' bodies top down
- a diff with no `DIFF_FLAGS`, or `git log -p` in place of `git diff`
- a fixed `max_turns` or lens budget
- no standing instructions

**Criterion 2's witness** reads the raw prompt file and flattens its
whitespace. It checks each phrase and name the claim lists. It asserts no
`` `probe` ``. It lowers the raw file and checks each of the fourteen
strings, lowered, against it, as `SA-0146`'s criterion 2 does for the two
lens files. The filled prompt holds the standing instructions, which can
name any of them, so a check there fails the right build. These fail it,
reasoned:

- a prompt that names `CLAUDE.md` or `Claude.md`, or tells the lens to run
  `uv run pytest`
- a prompt that cites a URL
- the three joins in other words than the design's

**Criterion 3's witness** replaces `end_review.review_joins` and
`end_review.review_stack` with recorders, through `monkeypatch`. Each
records its arguments and keywords. It passes nine distinct objects as the
nine keywords, and a reserve of 5.0. The join recorder returns, in turn, a
`LensReview` of cost 0.75, then `None`, then a `LensReview` of cost 0.5
with an error. The stack recorder returns one fixed list. It asserts the
calls in order: join then stack, for batches `1`, `2` and `3`. The stack's
reserves are 4.25, 5.0 and 4.5. Both recorders got the same ledger, the
same `specs` object and the nine keywords each time. Each result's `join`
is the join recorder's return, and its `layers` equals the stack
recorder's. These fail it, each measured:

- the layers before the join
- the reserve not reduced by the join's cost, or reduced by the lens budget
- an errored join's cost left out
- the join or the layers dropped from the result
- `open_cell` withheld from `review_stack`

**Criterion 4's witness** replaces `session.cell_up`, `session.cell_down`
and `runtime.remove_container` with recorders that append to one log.
The `cell_up` recorder calls its `note` once with a step and a detail. The
`cell_down` recorder calls its own once with a step, `True` and a detail.
The fields have distinct `base` and `head`. It runs three cases. In the first
the body appends the yielded name. It asserts the log reads remove, up,
body, down, and checks the claim's arguments. In the second, `cell_up`
adds its container to `created` and raises. It asserts the raise
propagates, the log reads remove, up, down, and `created` holds that
container. In the third the body raises, and the log still ends in down.
These fail it, each measured:

- the cell seeded at `fields.base`, the predecessor's head
- `cell_down` outside a `finally`, or `cell_up` outside the `try`
- a fresh `created` set handed to `cell_down`
- a yielded name other than the container `cell_up` was given
- no leftover container removed first
- one two-argument note shared by both calls, which raises from the
  `finally`

**How the lists were measured.** Throwaway simulations ran on 2026-09-23 at
`f0c8f82d`. They subclassed `Ledger` with `SA-0145`'s and `SA-0153`'s
tables and both write methods. They stood in for `layer_fields`,
`LayerFields`, `LayerReview` and `review_stack`. They ran the real
`review.run_lens`, `context.build_system_prompt` and
`session.stop_on_rejected` on the host's git. The right build passed each
witness, and every wrong version listed failed its own. After the first
spec review they ran again, with the rewritten `TE-9.txt`, batch 5's short
reserve and the notes. The code of
`SA-0143` to `SA-0153` is not at `f0c8f82d`, so no witness ran against it.

**What the witnesses leave undriven.**

- A raise from `layer_fields`, the spec lookup, the diff or `run_lens`.
  Criterion 1 claims only `open_cell`'s. Catch each of the others in the
  same place, with the same record.
- The `context_md`, `prompts_dir` and `emit` pass-through in
  `review_joins`. Pass each as given.
- The `{spec}` slot's per-layer headings and `layer_cell`'s `branch`.
  Build each as the Problem states.

**Why the join goes first, and where that costs a layer.** Each layer
already had three in-cell lenses. At the joins the critic is the only full
reader (ADR 6, principles 40 and 50). So a short reserve buys the joins
before any layer. The cost is a floor. `review_stack` starts a layer only
while $5 remains after the join. With a join near $1.50, a `--budget` below
about $26 reserves too little, and a two-layer stack gets the join and no
layer. At the lens ceiling of $2.50 that floor is $30. Each layer not
reached still gets its `not_reached` rows from `review_stack`.

**The double's `AssertionError` is caught.** `review_joins` catches a raise
from the lens step, the double's included. So an extra lens call reads as
`error`, and the call count is what fails.

**A brace in the prompt file is a slot.** `build_system_prompt` runs
`format` over the file (`saffron/agents/context.py:194-197`). So a literal
brace, as in a JSON example, is written doubled or not at all.

**The `prose` gate** reads the prompt file and every new comment and
docstring (`.saffron/gates/prose.py:43-44`). Write no em dash, semicolon,
contraction, perfect tense, hedge or sentence over 25 words. Keep each
docstring within ten lines. Check the prompt file with
`python3 hooks/prose_limit.py --file <path>` before you commit it.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). A
prototype of this change, with its four witnesses formatted by
`ruff format`, measured 1946 changed tokens with `size_gate` itself.
`saffron/end_review.py` took 471, the prompt 192 and
`tests/test_end_review.py` 1283. The fourteen-string check adds about 50
over the three names it replaces, as `SA-0146` counted its own. That is
about 2000, 67% of the ceiling. Keep the witnesses' helpers shared and
their docstrings short.
