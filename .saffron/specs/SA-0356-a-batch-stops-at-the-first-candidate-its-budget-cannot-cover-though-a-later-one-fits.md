---
id: SA-0356
title: A batch stops at the first candidate its budget cannot cover, though a later one fits
type: bug
priority: 2
depends_on: [SA-0353]
estimated_lines: 22
estimate_measured: true
touches:
  - saffron/batch.py
  - tests/test_batch.py
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
  - hooks/**
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/spec_review.py
  - saffron/gates/**
  - saffron/phases/**
  - saffron/cell/**
  - tests/test_cli.py
  - tests/test_scheduler.py
budget_usd: 30
max_attempts: 3
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      A batch passes over a candidate whose `budget_usd` exceeds what is left,
      and offers the next candidate that fits. It names each candidate it
      passes over on one line, with that candidate's budget and what was left
      when it was checked. A candidate passed over is named once, however many
      later rescans offer it again. A batch that passed over a candidate ends
      `BUDGET` once no candidate it has not tried fits, and its row closes
      `BUDGET`. The witness passes over the first candidate before any spend
      and a later one after a spend, runs a candidate after each, and rescans
      the whole list after every task.
    witness: tests/test_batch.py::test_a_batch_passes_over_a_candidate_its_budget_cannot_cover_and_runs_the_next_that_fits
    wrong_versions:
      - The line is printed and the batch then returns `BUDGET` at once, as at base, so no later candidate runs.
      - The set of candidates passed over is cleared after each rescan, so the first candidate is named again after each task.
      - A batch that passed over a candidate and then ran out of candidates returns `DRAINED`.
      - What is left is read once, before the first candidate, so a candidate the first task's spend no longer fits still runs.
  - claim: >-
      A stack batch that passes over a spec of its order records it as a miss.
      Every later spec of the order whose `depends_on` reaches it is refused
      with the `refused  reaches` line a missed layer's dependents get. That
      holds for a direct dependent next in the order and for one that reaches
      it through another refused spec. A later spec that reaches no miss still
      runs, and its predecessor is the last layer that reached
      `READY_FOR_REVIEW`. The batch ends `BUDGET`.
    witness: tests/test_batch.py::test_a_stack_batch_refuses_the_dependents_of_a_layer_it_passed_over_and_runs_the_rest
    wrong_versions:
      - The spec passed over is excluded from the order's pass but never recorded in `missed`, so its direct dependent runs.
      - The miss is recorded, but the dependent next in the order is offered before `resolve_prefix` runs again, so it runs.
      - The stack batch passes no hook to `_drive`, so a spec passed over stays at the head of `remaining` and its dependent runs.
      - The pass ends `DRAINED`, so the follow-ups would run.
  - claim: >-
      A follow-up whose `budget_usd` exceeds what is left is passed over the
      same way, named on the same line, and the next follow-up that fits runs
      on the order's top layer. The follow-up passed over is named in the
      `follow-ups unrun` line, and the batch ends `BUDGET`.
    witness: tests/test_batch.py::test_a_follow_up_its_budget_cannot_cover_is_passed_over_and_the_next_one_runs
    wrong_versions:
      - The follow-up pass returns `BUDGET` at its first follow-up over budget, so the second follow-up never runs.
      - The follow-up pass returns `DRAINED` once every follow-up was tried.
  - claim: >-
      A candidate whose `budget_usd` equals what is left still runs. A lone
      candidate over it runs nothing, and the batch closes `BUDGET`.
    witness: tests/test_batch.py::test_the_budget_gate_is_one_comparison_before_each_task
    preserves: true
  - claim: >-
      `saffron batch --stack` over a chain still starts each layer at its
      printed threshold and stops `BUDGET` a cent below it, having started no
      layer from that one on.
    witness: tests/test_cli.py::test_each_stack_layers_threshold_agrees_with_what_run_stack_batch_admits
    preserves: true
---

## Context

Backlog item **b-f73cd0**, under `DESIGN.md` §4.2.1. Related: b-b24cf7.
Every line below was read at `origin/main` `35e8aad0`.

**What the design says.** §4.2.1 says "A batch ends four ways, and says
which. The queue drains, the budget is gone, `--until` hits, or the breaker
fires" (`DESIGN.md:503`). It also says the budget gate "is one comparison
before each task" (`DESIGN.md:499`).

**What the batch does today.** `_drive` takes the first candidate it has not
started (`saffron/batch.py:252`). It checks `--until`, then computes what is
left as `budget_usd` less `reserve_usd`, less `writer_left`, less
`batch_spend` (`saffron/batch.py:269-276`). When the candidate's
`budget_usd` exceeds that, it returns `BUDGET` at once
(`saffron/batch.py:277-278`). It reads no later candidate. With no candidate
left it returns `DRAINED`, or `INFRASTRUCTURE` while the breaker's count
stands (`saffron/batch.py:253-261`). After each task it replaces `pending`
with `rescan()` (`saffron/batch.py:382`).

**What a stack batch does today.** `run_stack_batch` drives its order through
`_drive` with `resolve_prefix()` as the candidates and `resolve_prefix` as the
rescan (`saffron/batch.py:943-960`). `resolve_prefix` refuses each spec at
the head of `remaining` whose `depends_on` reaches a key of `missed`. It
prints `refused  reaches <ids>`, records the spec in `missed` and pops it
(`saffron/batch.py:612-628`). It returns `remaining` itself (`:629`). `wrapped` records
a spec that did not reach `READY_FOR_REVIEW` as
`missed[spec id] = frozenset({spec id})` and removes it from `remaining`
(`saffron/batch.py:919-924`). The follow-up pass is a second `_drive` with the
follow-ups as its rescan (`saffron/batch.py:994-1010`). It runs only when the
order's pass returned `DRAINED` (`saffron/batch.py:987`). A follow-up no
review routed is named in the `follow-ups unrun` line
(`saffron/batch.py:1012-1018`).

**What it cost.** Batch 35 ran `--stack` with 16 candidates, `SA-0284`
second. After `SA-0275` it had $26.47 left. `SA-0284` needs $42, so the batch
stopped `BUDGET`. `SA-0294` needs $25 and never ran.

## Problem

1. **Pass over, do not stop.** In `_drive`, a candidate whose `budget_usd`
   exceeds what is left no longer returns `BUDGET`. It prints one line,
   `f"{spec id:<10} over budget  needs {budget_usd:.3f}, {left:.3f} left"`,
   the shape the `unrevised` line already uses (`saffron/batch.py:847-851`).
   `_drive` then offers the next candidate it has neither started nor passed
   over. Each candidate is checked against what is left when it is reached,
   so the `--until` check still comes first, and the breaker's check after.
2. **Named once.** `_drive` keeps the ids it passed over beside `started`,
   and leaves them out of every later `pending`, rescanned or not. What is
   left never grows within a pass, since `writer_left` falls as fast as
   spec writing adds to `batch_spend` (`saffron/batch.py:199-203`). So a
   candidate passed over stays over.
3. **`BUDGET` ends a pass that passed over a candidate.** A pass out of
   candidates with the breaker's count standing returns `INFRASTRUCTURE`, as
   today. Otherwise it returns `BUDGET` when it passed over any candidate,
   and `DRAINED` when it passed over none.
4. **A stack batch records the miss.** For the order's pass, `_drive` hands
   the candidate it passed over to a callable `run_stack_batch` gives it. That
   callable records `missed[spec id] = frozenset({spec id})`, removes the spec
   from `remaining`, and returns `resolve_prefix()` as the new `pending`. So
   `resolve_prefix` refuses its dependents before `_drive` offers another
   spec. This is the missed-layer path, and it adds no stack state. A plain
   batch and the follow-up pass give no such callable. A follow-up passed
   over is not a layer miss, as a follow-up's refusal is not one today.
5. **One existing test changes.** It is
   `test_a_follow_up_meets_until_the_budget_and_the_breaker_as_any_task_does`
   (`tests/test_batch.py:6265`). Its batch 2 offers `TE-44` at $27 and then
   `TE-40` at $1 (`:6303-6340`). It asserts that no line says `refused`
   (`:6339`). `TE-44` is now
   passed over, and `TE-40` meets the open pull request's refusal on `x.py`.
   Replace that assertion with two: a line starting `TE-44      over budget`,
   and one starting `TE-40      refused  touches`. Keep the rest of batch 2
   as it is. A prototype of the change failed this test alone of
   `tests/test_batch.py`, `tests/test_cli.py`, `tests/test_follow_up.py` and
   `tests/test_history_run.py`.

## Out of scope

- `_print_stack_admission`'s thresholds (`saffron/cli.py:2121-2153`). Each
  still assumes every earlier candidate ran. For a chain, criterion 5 holds
  that as the least `--budget` that starts the layer. A spec that reaches no
  earlier one now starts under a lower `--budget` whenever an earlier spec is
  passed over. The printed line stays true as a budget that admits it. A
  tighter threshold is a separate item.
- A plain batch's dependents of a candidate passed over. Its rescan is
  `build_queue`, which judges each `depends_on` as today, and this spec
  leaves it alone.
- `DESIGN.md` and `CONTEXT.md`, which are `protected`. §4.2.1's "the budget
  is gone" becomes true of the code, so neither needs an edit.
- The revision check's own `unrevised` refusal (`saffron/batch.py:838-858`).

## Notes for the agent

**Stack order.** `depends_on: [SA-0353]` orders the stack only, since both
edit `tests/test_batch.py`. This spec consumes nothing `SA-0353` adds. Find
each test by name, since its line numbers shift in the cell's tree.

**Mutants and new code.** The code each criterion is about is new: the set of
candidates passed over, the line and the stack batch's callable. The base
does not fix their spelling, so no criterion declares a mutant, and `witness`
reports `skip` for each. Criteria 4 and 5 name tests that exist, and they must
stay green. The wrong versions under each criterion are what REVIEW runs. Do
not run them yourself.

**The three witnesses.** Each new test needs no name the change adds, so each
collects at base and fails there.

- Criterion 1 calls `run_batch` with `budget_usd=20.0`, `rescan` returning the
  whole list, and four candidates at $30, $8, $8 and $2. A `FakeRunner`
  returns two `READY_FOR_REVIEW` outcomes whose runs `_spend` $15 and $1.
  Assert the runner saw the second and fourth candidates. Assert the reason
  and the row's status are `BUDGET`. The lines holding `over budget` are
  exactly two, in order. The first candidate's says `needs 30.000, 20.000
  left` and the third's says `needs 8.000, 5.000 left`.
- Criterion 2 calls `run_stack_batch` at $30 with `StackDoubles`' runner, which
  spends $1 a task, and no review. The order is `TE-1` $5, `TE-2` $50, `TE-3`
  $5 on `TE-2`, `TE-4` $5, and `TE-5` $5 on `TE-3`. Assert the runner calls
  are `[("TE-1", None), ("TE-4", "TE-1")]`, the reason is `BUDGET`, and the
  lines hold `TE-2`'s `needs 50.000, 29.000 left` and both `refused  reaches
  TE-2` lines.
- Criterion 3 drives one order spec at $5 under a $30 budget, with
  `reserve_usd=6.0`, `writer_usd=2.0` and `StackDoubles`' review, mint, end
  review and follow-ups. The follow-ups are $40 and then $1. Assert the
  runner calls are the order spec and then the $1 follow-up on it. Assert the
  reason is `BUDGET`. The lines hold the $40 follow-up's `needs 40.000,
  29.000 left` and `follow-ups unrun  <its id>`.

These arrangements were run against a prototype of the change. Every wrong
version listed under each criterion failed its witness, and with
`saffron/batch.py` reverted all three witnesses failed.

**Words.** A candidate is "passed over", never "skipped": `skip` is a gate
status (`CONTEXT.md:385`, `:533`). Name a turn, an attempt or a batch,
never a bare "run". New comments and docstrings take no em-dash,
semicolon, contraction or sentence over 25 words.
