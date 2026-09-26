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
      `_stack_runner` returns. That runner's `repo_id` is asked of the
      ledger for each task, so a repo first recorded after the opening
      scan reaches `run_task`. It never calls `run_batch`. When readiness
      fails, it exits 2 and prints the failed step. When `_resolve_queue`
      raises, it exits 2 and prints that the queue could not be resolved.
      Each leaves a batch row closed `INFRASTRUCTURE`.
    witness: tests/test_cli.py::test_saffron_batch_stack_plans_once_and_runs_that_order
  - claim: >-
      `saffron queue --stack` prints the candidates of `build_queue` with
      `stack=True` in the stack order, and its refusals. The witness drives
      a child whose parent has no task, which only the stack order admits,
      and a spec whose entry is declared nowhere. The same repo without
      `--stack` lists the parent alone and refuses the child.
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
and every line number was read at `642a26c3`.

**How the two commands run today.**

- The parser declares `queue` with `--repo` alone, and `batch` with
  `--repo`, `--budget` and `--until` (`saffron/cli.py:105-122`).
- `_resolve_queue` takes `stamp_orphaned` and `pinned` and calls
  `build_queue` (`saffron/cli.py:537-543`, `:610-629`).
- `_queue` calls it with `stamp_orphaned=False` and prints the candidates
  in the order returned (`saffron/cli.py:950`, `:1150-1155`).
- `_batch` checks readiness, then calls `_resolve_queue` with
  `stamp_orphaned=True` and the pinned base (`saffron/cli.py:798-836`). It
  prints the plan, builds a rescan and `_batch_runner`, and calls
  `run_batch` (`:848-891`). It maps the stop reason to an exit code
  (`:893-916`).
- Before readiness passes, `_batch` holds a runner that takes one
  candidate, `_no_candidate_should_run` (`saffron/cli.py:702-714`, `:815`).

## Problem

Add `--stack` to `saffron batch` and to `saffron queue`.

1. `_resolve_queue` takes `stack: bool = False` and passes it to
   `build_queue`.
2. `saffron queue --stack` passes `stack=True` and prints as today.
3. `saffron batch --stack` resolves once with `stack=True`. It builds the
   runner with `_stack_runner` and calls `run_stack_batch` in place of
   `run_batch`, with no rescan. The `repo_id` it passes `_stack_runner`
   is a callable that asks `ledger.resolve_repo_id(pinned.url)` for each
   task, the lookup `_resolve_queue` makes (`saffron/cli.py:587`). It is
   not the opening scan's value, which is `None` on a repo's first night. It keeps the readiness check, the printed
   plan and the exit codes it has today. Its runner before readiness
   passes takes a candidate and a predecessor, as `run_stack_batch`'s
   runner does.

Without `--stack`, both commands behave as today.

`_batch`'s docstring says `run_batch` is the only caller of
`create_batch` and `close_batch` in this module, and that the exit codes
are `run_batch`'s stop reasons (`saffron/cli.py:767-772`). Reword both
sentences to name `run_stack_batch` too.

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
(`tests/test_cli.py:2657`, `:2719` and `:3444`). Add `stack=False` to each
and change nothing else in them.

**Four tests build `_batch`'s arguments by hand** and call `cli._batch`
directly (`tests/test_cli.py:3090`, `:3762`, `:3789` and `:3838`). Each
`argparse.Namespace` lacks `stack`, so a `_batch` that reads `args.stack`
raises `AttributeError` in all four. Add `stack=False` to each and change
nothing else in them.

**Criterion 1's witness** follows
`test_the_batch_rescans_through_the_pinned_base_without_stamping_orphans`
(`tests/test_cli.py:2692-2753`). It fakes `cli.run_batch` to fail the
test in all three of its cases.

- **Readiness passes**, with `_readiness_passes`. It fakes
  `_resolve_queue` to record its keywords and return `SY-2` at priority
  3, then `SY-1` at priority 1. The resolution's `repo_id` is `None`.
  - It keeps a reference to the real `cli._stack_runner`, then fakes it
    to record its keywords and return a sentinel object.
  - It replaces `cli.run_task` with a double that records `repo_id` and
    `handoff`.
  - It fakes `cli.run_stack_batch` to record its candidates and runner.
    Inside that fake, while `main`'s ledger is still open, it upserts a
    repo at `https://github.com/o/r.git`, the url `_readiness_passes`
    pins (`tests/test_cli.py:2618`). It then calls the real
    `_stack_runner` with the recorded keywords, and calls that runner
    with `SY-2` and `None`. It returns `DRAINED`. The rescan test calls
    its runner inside its fake loop the same way
    (`tests/test_cli.py:2726-2732`). `main` closes the ledger when it
    returns (`saffron/cli.py:230-231`), so a call after `main` raises
    `sqlite3.ProgrammingError`.

  `main([..., "batch", "--stack"])` returns 0. It asserts one
  `_resolve_queue` call, with `stack=True`, `stamp_orphaned=True` and a
  pinned base. It asserts the candidates are `SY-2` then `SY-1`, and the
  runner is the sentinel. It asserts the double recorded the upserted
  repo's id and a `handoff` equal to
  `Handoff(stacked_on=None, target_branch=None)`, a real instance, which
  `None` is not.
- **Readiness fails**, as
  `test_a_readiness_failure_names_the_step_that_failed` sets it up
  (`tests/test_cli.py:2972-2993`), with the real `run_stack_batch`. It
  expects exit 2, the step and detail printed, and the newest `batches`
  row closed `INFRASTRUCTURE`. It reads that row with the query at
  `tests/test_cli.py:3651-3659`.
- **`_resolve_queue` raises**, as
  `test_any_raise_resolving_the_queue_still_closes_the_batch_row` sets it
  up (`tests/test_cli.py:3634-3659`), with the real `run_stack_batch`. It
  expects exit 2, `batch: the queue could not be resolved:` and the
  raise's text, and the row closed `INFRASTRUCTURE`. It expects no
  `readiness failed`, as
  `test_a_queue_that_cannot_be_resolved_says_so_on_the_batch_line` does
  (`tests/test_cli.py:3663-3685`).

These fail it:

- a rescan on the stack path
- `run_batch` called with the stack order
- `_batch_runner`'s runner handed to the stack loop
- a two-argument wrapper over `_batch_runner` that drops the predecessor
- a `repo_id` fixed at the opening scan's value, which records `None`
- `None` passed as `repo_id`
- the candidates re-sorted by priority, which puts `SY-1` first
- `stack` left at its default in the one call
- a stack branch placed inside `if readiness.ok`
- a stack path that hands the loop a readiness check blind to the scan's
  raise, which prints `DRAINED` and exits 0

**How the order and `repo_id` were measured.** A throwaway simulation
ran on 2026-09-23 against a real `Ledger`. The right `repo_id` callable
returned the upserted id. An opening-scan value and `None` both failed,
and so did a priority re-sort of `SY-2` then `SY-1`. A lookup on a closed
ledger raised `ProgrammingError`.

**The raise case leans on `SA-0143`.** `_batch` names the scan's raise
only when the same exception object leaves the loop
(`saffron/cli.py:893-899`). `run_batch` lets it out through its
`finally` (`saffron/batch.py:120-143`). If `run_stack_batch` wraps the
exception, this case fails, and the fix is in `SA-0143`'s loop.

**Criterion 2's witness** uses `_repo_with_spec`
(`tests/test_cli.py:1268`). `SY-1` has priority 1 and
`depends_on: [SY-2]`. `SY-2` has priority 3. `SY-3` depends on `SY-9`,
which no spec declares. It runs `queue --stack` and reads the lines after
`queue:`. The candidates are `SY-2` then `SY-1`, and a refusal line names
`SY-3` and `SY-9`. The same repo without `--stack` lists `SY-2` alone
and refuses `SY-1`. These fail it:

- a flag parsed and not passed
- candidates sorted by priority, which puts `SY-1` first
- `_queue` passing `stack=True` always, which the default half catches

That default half guards criterion 3. Its witness writes one spec with no
`depends_on` (`tests/test_cli.py:1318-1321`). So a `_queue` that always
passes `stack=True` prints the same bytes there.

Measured on 2026-09-23 at `71ef7909`, the default half printed:

```
reconcile: nothing moved
queue: 1 candidate(s)
  SY-2       priority=3  .saffron/specs/SY-2.md
refusals: 2
  .saffron/specs/SY-1.md: depends_on SY-2 has no task at its current spec_sha, so nothing says it merged: it has not run, or not since it was last edited
  .saffron/specs/SY-3.md: depends_on SY-9 is not among the specs in this directory, not retired to done/ as shipped, and no task in the ledger says it merged
```

The stack half needs `SA-0142`'s head and was not run.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** About 50 changed lines of source and 200 of test. `SA-0131`'s
cell measured 4.3 tokens a line in `saffron/cli.py` and 4.0 in
`tests/test_cli.py` (`50ef269d`). At 4.5 and 3.8 that is about 990 tokens
of the 3000 ceiling (`saffron/gates/core/size.py:26`).
