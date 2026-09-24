---
id: SA-0157
title: saffron batch --stack never runs its end review, and holds no reserve for it
type: feature
priority: 1
depends_on: [SA-0154]
touches:
  - saffron/cli.py
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
  - saffron/task.py
  - saffron/batch.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_end_review.py
  - tests/test_review.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_session.py
budget_usd: 22
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      `saffron batch --stack --budget N` passes `run_stack_batch` the
      budget `N` whole, a `reserve_usd` of `N` times
      `end_review.RESERVE_SHARE`, and an `end_review` callable. Its plan
      header prints that reserve beside the budget. The callable calls
      `end_review.run_end_review` with the ledger and the batch key, reserve
      and specs it was given. It returns the `StackReview` that call
      returns. `mirror` is the pinned mirror. `claude_md` is `CLAUDE.md` at
      the pinned `base_sha`, never the checkout's. `open_cell` is
      `layer_cell` over the repo and the pinned mirror. Its gates directory
      is `.saffron/` exported at that `base_sha`, and its `thread_env` is
      that export's policy's. `context_md` is Saffron's own `CONTEXT.md`,
      and `prompts_dir` is `context.PROMPTS_DIR`. `max_turns` and
      `budget_usd` are `end_review.LENS_MAX_TURNS` and
      `end_review.LENS_BUDGET_USD`. `agent` calls `implement.run_agent` with
      `timeout_s` of `session.TURN_TIMEOUT_S` and `spec_id` of
      `end-review-<batch key>`. It raises `RateLimited` on a rejected
      window. A raise from the export, the policy load or the `CLAUDE.md`
      read is caught. The callable then prints one line naming it and
      returns a `StackReview` with no join and no layers. It does not call
      `run_end_review`. The witness drives a raise from each of the three.
    witness: tests/test_cli.py::test_a_stack_batch_holds_a_quarter_of_its_budget_and_reads_its_stack_at_the_pinned_base
  - claim: >-
      `saffron batch` without `--stack` still hands `run_batch` its budget
      and its defaults.
    witness: tests/test_cli.py::test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes
    preserves: true
  - claim: >-
      A night without `--stack` prints its plan header as before, with no
      reserve.
    witness: tests/test_cli.py::test_the_printed_night_is_unchanged_by_sharing_the_base
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 3 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 2 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "The end review",
is the design. Its **Money** paragraph says the batch reserves the end
review's budget at start.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**. Once the last queued task
settles, one **end review** reads the stack: two end-review lenses per
layer, and one join lens over the joins.

**This spec is the fourth of four for step 3.** `SA-0146` builds the Spec
and Standards lenses. `SA-0153` runs them over a stack within a reserve.
`SA-0154` adds the join lens, the critic cell a layer is read in, and
`run_end_review`, which runs the whole end review. This spec wires
`run_end_review` into `saffron batch --stack`. `SA-0147` then qualifies the
findings.

**What the tree base holds.** This spec's tree base is `SA-0154`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:133-136`). The chain
`SA-0142` to `SA-0154` puts these there, so they are cited by symbol. Every
line number below was read at `f0c8f82d`.

- `SA-0144` adds `--stack` to `saffron batch`. Given it, `_batch` builds
  its runner with `_stack_runner` and calls `run_stack_batch` in place of
  `run_batch`. It does so inside the branch where readiness passed, where
  `pinned` is bound (`saffron/cli.py:811-822`).
- `SA-0153` adds `reserve_usd` and `end_review` to `run_stack_batch`. Its
  task loop holds the reserve back from each budget comparison.
  `end_review` runs once after the loop, with the batch's id as text, the
  reserve and each spec of the order by its id. `run_stack_batch` discards
  what it returns.
- `SA-0154` adds to `saffron/end_review.py`:
  - `run_end_review(ledger, batch_key, reserve_usd, specs, *, mirror,
    open_cell, context_md, claude_md, prompts_dir, max_turns, budget_usd,
    agent, emit)`, which returns a `StackReview`.
  - `StackReview`, a frozen dataclass with `join` and `layers`.
  - `layer_cell(fields, *, repo, mirror, gates_dir, thread_env)`, a
    context manager that brings a critic cell up at `fields.head` through
    `session.cell_up`, and down through `session.cell_down`.
  - `LENS_BUDGET_USD` of 2.5, `LENS_MAX_TURNS` of 50 and `RESERVE_SHARE`
    of 0.25.

  All five are `SA-0154`'s `pending_symbols`, because only this spec calls
  them.

**Where each input lives.** `_drive_cell` exports `.saffron/` at the run's
`base_sha` and loads the policy from that export
(`saffron/cell/session.py:1650`, `:1662`). It reads `CLAUDE.md` at the same
sha (`:1655`) and Saffron's own `CONTEXT.md` from Saffron's root (`:1798`).
It wraps the agent in `stop_on_rejected` and binds `timeout_s` and
`spec_id` (`:1829-1839`). `review.run_lens` calls the agent with no
`spec_id` (`saffron/phases/review.py:236`), and `run_agent` requires one
(`saffron/phases/implement.py:196`). `stop_on_rejected` raises
`RateLimited` on a rejected window (`saffron/cell/session.py:159-181`,
`:230-232`). `_default_emit` prints each event's `describe` line
(`:85-87`).

**The plan header.** `_print_batch_plan` prints the candidate count, the
budget and the deadline on one line (`saffron/cli.py:715-735`). `_batch`
calls it once the queue resolves (`:839`).
`tests/test_cli.py:3802-3850` pins that output exactly for a night without
`--stack`.

**What a lens costs.** On 2026-09-23 the ledger held 392 `REVIEWING`
attempts, one per in-cell lens session. Their cost averaged $0.68 and
peaked at $1.80.

## Problem

1. **The callable.** Add `_stack_end_review(*, pinned, repo, ledger,
   out_dir)` to `saffron/cli.py`, beside `_stack_runner`. It returns the
   callable criterion 1 states. The callable exports `.saffron/` at the
   pinned `base_sha` under `out_dir`, in a directory named for the batch
   key. It reads the export, the policy and `CLAUDE.md` inside one `try`.
   A raise there would leave `run_stack_batch` after the loop, and `main`
   would exit 2 for a night that drained. So the callable catches it,
   prints one line and returns an empty `StackReview`. Its `emit` prints
   each event's `describe` line, as `_default_emit` does.
2. **The wiring.** `_batch`'s `--stack` path builds the callable where it
   builds `_stack_runner`. It passes `run_stack_batch` the callable and a
   reserve of `--budget` times `end_review.RESERVE_SHARE`. A night whose
   readiness fails passes `end_review=None`, and `run_stack_batch` then
   runs none.
3. **The plan header.** `_print_batch_plan` takes `reserve_usd`, `None` by
   default. Given one, the header reads `budget $<budget>, reserve
   $<reserve>, until <deadline>`. Given none, it reads as it does today.
   The `--stack` path passes the reserve.

Reach `end_review.run_end_review`, `end_review.layer_cell`,
`implement.run_agent`, `git_mirror.export_saffron_dir`, `git_mirror.file_at`
and `cli.load_policy` through their modules at call time. The witness
replaces each there.

**The reserve is a share of `--budget`, not a flag.** The design's command
line names `--budget` and `--ready` alone. It is in design section 4, under
"What the delegate still does". A flag would be one more number the
operator sizes each night, and a default in dollars fits one budget only. A
share keeps the night bounded by the one number the operator gives. At the
lens ceiling, the join and `n` layers cost at most `(2n + 1) × 2.5`. A $100
night reserves $25, which covers the join and four layers at the ceiling.
`review_stack` starts a layer only while $5 remains. So at the measured
mean of $0.68 a lens, $25 covers the join and about fifteen layers. The
join runs first (`SA-0154`), so below about $26 of `--budget` a two-layer
stack can get the join and no layer.

**`SA-0147` reads the `StackReview`.** The callable returns what
`run_end_review` returns, and `run_stack_batch` discards it. So `SA-0147`
qualifies inside the callable or inside `run_end_review`.

## Out of scope

- **The end review itself.** The join lens, `layer_cell`,
  `run_end_review` and the constants are `SA-0154`'s. The lenses over each
  layer are `SA-0153`'s.
- **Qualification.** It is `SA-0147`'s.
- **A rate-limited lens.** `RateLimited` raises out of `run_lens`, so the
  join or the layer reads as `error`. The rate-limit wait is `SA-0148`'s.
- **An event log for the end review.** Its events print to the batch's
  output alone. No `events.jsonl` in the batch tree gains them.
- **Two sentences this makes false.** `README.md:123-124` says a night ends
  at the deadline plus at most one task. The end review now runs after an
  `UNTIL` stop. `DESIGN.md`'s one-task overshoot bound (`DESIGN.md:202`)
  gains an end-review lens too. Both files are forbidden here, and backlog
  item b-1adb50 files them by hand.
- **The reserve on the queue page.** The stack view is `SA-0152`'s.

## Notes for the agent

**Criterion 1 is new code.** No text at the tree base passes an end review
from the command line. So criterion
1 declares a witness and no mutant, and `witness` reports `skip` for it.
Criteria 2 and 3 name tests that pass now.

**Why the witness fails at the tree base.** `SA-0154` puts every
`end_review` name there. With the source reverted, `_batch` passes
`run_stack_batch` no `reserve_usd`, so the fake's read of that keyword
raises.

**Criterion 1's witness** builds a git repo as the mirror, with two
commits. The first holds `.saffron/policy.yaml` with `thread_env` `X:
base` and `CLAUDE.md` "claude at base". The second changes both to `head`.
The pinned base is the first commit. The working directory is a checkout
holding its own `CLAUDE.md` and `CONTEXT.md`, with other text. Readiness
passes with that mirror and sha, as `_readiness_passes` does
(`tests/test_cli.py:2603-2621`). `_resolve_queue` returns
`_fake_batch_resolution` (`:2624-2640`), and takes any keyword.

- A fake `run_stack_batch` records its budget and keywords. It calls
  `end_review` with `"7"`, 10.0 and a mapping of one `Spec`, and keeps
  what it returns. It also keeps the callable.
- `end_review.run_end_review` is replaced with a recorder that returns a
  sentinel.
- `implement.run_agent` is replaced with one that takes a required
  keyword-only `spec_id`. It records its keywords and returns an attempt
  whose `rate_limit_status` is `rejected`.
- `session.cell_up`, `session.cell_down` and `runtime.remove_container` are
  recorders. The `cell_up` recorder calls its `note` once with a step and a
  detail. The `cell_down` recorder calls its own once with a step, `True`
  and a detail.

It runs `main` with `batch --stack --budget 40` and asserts exit 0. The
output holds `budget $40.00, reserve $10.00, until none`. It asserts the
budget 40.0, the reserve 10.0, the sentinel returned, and the claim's
arguments and keywords. It enters `open_cell` on fields whose head is `h`
forty times. It asserts `cell_up` got `thread_env` `{"X": "base"}`, the
checkout as `repo`, the pinned mirror and that head. The `policy.yaml`
under the `gates_dir` it got reads `X: base`. It calls `agent` and asserts
`RateLimited`. The `timeout_s` passed is `session.TURN_TIMEOUT_S`, and the
`spec_id` is `end-review-7`.

Last, it replaces each read in turn with one that raises
`PolicyError("unreadable")`, through `monkeypatch.context()`. The three are
`git_mirror.export_saffron_dir`, `cli.load_policy` and `git_mirror.file_at`.
For each it calls the kept callable with `"8"`. The result equals a
`StackReview` with no join and no layers, and the recorder was not called.
The output holds three lines naming "unreadable". These fail it, each
measured on `_stack_end_review` alone:

- `CLAUDE.md` read from the mirror's `HEAD`, or from the checkout
- `.saffron/` exported at the mirror's `HEAD`, for the policy or for the
  cell's gates directory alone
- `CONTEXT.md` read from the checkout
- an agent with no `stop_on_rejected`, or no `timeout_s`
- an agent with no `spec_id`, or one bound to another id
- the reads left unguarded, or `CLAUDE.md` read outside the guard
- a caught raise returned as `None`
- a callable that drops what `run_end_review` returns
- `specs` not passed through
- `max_turns` and `budget_usd` swapped

These are unmeasured, because `SA-0144`'s `--stack` path is not at
`f0c8f82d`:

- the budget less the reserve passed as the budget, which holds the reserve
  twice
- a reserve in dollars that ignores `--budget`
- no reserve in the plan header
- a reserve printed without `--stack`, which criterion 3's exact output
  refuses

**How the list was measured.** A throwaway simulation ran on 2026-09-23 at
`f0c8f82d`. It stood in for `SA-0154`'s `run_end_review`, `layer_cell`,
`StackReview` and constants. It ran the real `session.stop_on_rejected`,
`git_mirror.export_saffron_dir`, `git_mirror.file_at` and `load_policy` on
the host's git. It called `_stack_end_review` directly, without `main`.
The right build passed, and every wrong version listed failed. After the
first spec review of `SA-0154` it ran again, with the `spec_id`, the
guarded reads and the notes.

**What the witness leaves undriven.** The callable's `emit`, and
`end_review=None` on a night whose readiness fails. Build each as the
Problem states.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as the witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). A
prototype of this change, with its witness formatted by `ruff format`,
measured 604 changed tokens with `size_gate` itself. `saffron/cli.py` took
184 and `tests/test_cli.py` 420. That is 20% of the ceiling.
Reuse `tests/test_cli.py`'s own git helpers where it has them.
