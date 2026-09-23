---
id: SA-0144
title: Neither saffron batch nor saffron queue has a flag for the stack order, so no command runs a stack batch
type: feature
priority: 1
depends_on: [SA-0143]
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
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_task.py
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_consumes.py
  - tests/test_package.py
budget_usd: 20
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      `saffron batch --stack` calls `_resolve_queue` once, with `stack=True`,
      `stamp_orphaned=True` and the pinned base. It hands that call's
      candidates, in order, to `run_stack_batch` with the runner
      `_stack_runner` returns. It never calls `run_batch`.
    witness: tests/test_cli.py::test_saffron_batch_stack_plans_once_and_runs_that_order
  - claim: >-
      `saffron queue --stack` prints the candidates of `build_queue` with
      `stack=True` in the stack order, and its refusals. The witness drives
      a child whose parent has no task, which only the stack order admits,
      and a spec whose entry is declared nowhere.
    witness: tests/test_cli.py::test_queue_stack_prints_the_stack_order
  - claim: >-
      Without `--stack`, `saffron queue` prints what it printed before.
    witness: tests/test_cli.py::test_the_printed_queue_is_unchanged_by_sharing_the_base
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 1 of its Done. It cites `DESIGN.md` §4.2
and §4.2.1. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 1 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design.

A stack batch plans its order once, at batch start, and runs it into one
pull request stack.

**This spec is the third of four.** `SA-0142` builds the stack order as
`build_queue(..., stack=True)`. `SA-0143` builds `run_stack_batch`, which
runs an order and hands each task its predecessor's branch. It also builds
`cli._stack_runner`, the runner that loop takes. Both are `SA-0143`'s
`pending_symbols`, because nothing calls them yet. This spec adds the two
flags that call them. `SA-0145` records the stack's layers.

**What the tree base holds.** This spec's tree base is `SA-0143`'s head.
That chain runs through `SA-0142` and `SA-0136`, and `SA-0135` edits
`cli._batch` and `_batch_runner`. So `cli.py` is cited by symbol below,
and every line number was read at `012f8aab`.

**How the two commands run today.**

- The parser declares `queue` with `--repo` alone, and `batch` with
  `--repo`, `--budget` and `--until` (`saffron/cli.py:99-116`).
- `_resolve_queue` takes `stamp_orphaned` and `pinned` and calls
  `build_queue` (`saffron/cli.py:527-533`, `:600-619`).
- `_queue` calls it with `stamp_orphaned=False` and prints the candidates
  in the order returned (`saffron/cli.py:940`, `:1140-1145`).
- `_batch` checks readiness, then calls `_resolve_queue` with
  `stamp_orphaned=True` and the pinned base (`saffron/cli.py:788-826`). It
  prints the plan, builds a rescan and `_batch_runner`, and calls
  `run_batch` (`:838-881`). It maps the stop reason to an exit code
  (`:883-906`).
- Before readiness passes, `_batch` holds a runner that takes one
  candidate, `_no_candidate_should_run` (`saffron/cli.py:692-704`, `:805`).

## Problem

Add `--stack` to `saffron batch` and to `saffron queue`.

1. `_resolve_queue` takes `stack: bool = False` and passes it to
   `build_queue`.
2. `saffron queue --stack` passes `stack=True` and prints as today.
3. `saffron batch --stack` resolves once with `stack=True`. It builds the
   runner with `_stack_runner` and calls `run_stack_batch` in place of
   `run_batch`, with no rescan. It keeps the readiness check, the printed
   plan and the exit codes it has today. Its runner before readiness
   passes takes a candidate and a predecessor, as `run_stack_batch`'s
   runner does.

Without `--stack`, both commands behave as today.

## Out of scope

- **The loop, the handoff and the stack runner.** They are `SA-0143`'s,
  and `saffron/batch.py` and `saffron/task.py` are forbidden here.
- **The record of the layers.** That is `SA-0145`'s.
- **Gate 0's overlap exemption for the batch's own tasks.** That is step 2
  of b-792ab2. A stack batch resolves its queue once, before any of its
  own pull requests is open.
- **The vocabulary.** `CONTEXT.md` has no entry for a stack batch. Backlog
  item b-466005 files it by hand.
- **`SA-0141`.** It is queued on another branch and also edits
  `saffron/cli.py`. If its pull request is still open when this cell
  starts, gate 0's open pull request overlap refusal holds this spec back
  until it merges. So no `depends_on` names it.

## Notes for the agent

**Criteria 1 and 2 are new code.** No flag text exists at the tree base.
So they declare a witness and no mutant, and `witness` reports `skip` for
them. Criterion 3 is `preserves` and names a test that passes now.

**Three test fakes declare `_resolve_queue`'s signature**
(`tests/test_cli.py:2657`, `:2719` and `:3448`). Add `stack=False` to each
and change nothing else in them.

**Criterion 1's witness** follows
`test_the_batch_rescans_through_the_pinned_base_without_stamping_orphans`
(`tests/test_cli.py:2692-2753`), with `_readiness_passes`. It fakes
`_resolve_queue` to record its keywords and return `SY-2` then `SY-1`. It
fakes `cli.run_stack_batch` to record its candidates and runner and return
`DRAINED`. It fakes `cli.run_batch` to fail the test.
`main([..., "batch", "--stack"])` returns 0. It asserts one
`_resolve_queue` call, with `stack=True`, `stamp_orphaned=True` and a
pinned base. It then calls the recorded runner with `SY-2` and `None`,
with `cli.run_task` replaced, and asserts a handoff of two `None`s. These
fail it:

- a rescan on the stack path
- `run_batch` called with the stack order
- `_batch_runner`'s runner handed to the stack loop
- `stack` left at its default in the one call

**Criterion 2's witness** uses `_repo_with_spec`
(`tests/test_cli.py:1268`). `SY-1` has priority 1 and
`depends_on: [SY-2]`. `SY-2` has priority 3. `SY-3` depends on `SY-9`,
which no spec declares. It runs `queue --stack` and reads the lines after
`queue:`. The candidates are `SY-2` then `SY-1`, and a refusal line names
`SY-3` and `SY-9`. The same repo without `--stack` lists `SY-2` alone.
These fail it:

- a flag parsed and not passed
- candidates sorted by priority, which puts `SY-1` first

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** About 45 changed lines of source and 110 of test. `SA-0131`'s
cell measured 4.3 tokens a line in `saffron/cli.py` and 4.0 in
`tests/test_cli.py` (`50ef269d`). At 4.5 and 3.8 that is about 620 tokens
of the 3000 ceiling (`saffron/gates/core/size.py:26`).
