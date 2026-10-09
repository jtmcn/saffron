---
id: SA-0254
title: "`saffron queue --stack` prints no admission arithmetic, so nothing shows what `--budget` admits every layer"
type: feature
priority: 2
depends_on: [SA-0253]
estimated_lines: 207
estimate_measured: true
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/batch.py
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/spec_review.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 28
max_attempts: 3
max_turns: 120
risk: standard
acceptance:
  - claim: >-
      `saffron queue --stack` ends with an admission block for its stack
      order. A header names both shares `saffron batch --stack` holds back
      and the spec review cap. One line per candidate, in order, gives the
      least `--budget` that admits it. A last line gives the `--budget` that
      also pays the last layer's spec review. A refused spec adds no line.
      Without `--stack`, and under `--stack` with no candidate, no admission
      line is printed. The witness drives a three-layer order beside a
      refused spec, the same repo without `--stack`, and a stack queue whose
      one spec is refused.
    witness: tests/test_cli.py::test_queue_stack_prints_each_layers_admission_threshold_and_the_total
    mutant:
      file: saffron/end_review.py
      find: RESERVE_SHARE = 0.25
      replace: RESERVE_SHARE = 0.125
    wrong_versions:
      - The threshold holds back the reserve share alone, so the writer share is left in.
      - The threshold leaves every spec review out.
      - A layer's threshold counts its own spec review as well as every earlier one.
      - The last line repeats the last layer's threshold.
      - The last line gives the spend before the shares are held back.
      - The block is printed without `--stack` too.
      - The block is printed under `--stack` with no candidate, as a header and a zero total.
      - A refused spec's budget is counted as a layer.
  - claim: >-
      Each printed threshold is the least `--budget` at which `saffron batch
      --stack` starts that layer. A cent above it starts every layer up to
      and including it. A cent below it stops `BUDGET` before it. At the
      printed total the batch drains every layer, and its spend equals
      `--budget` less both shares `_batch` passed. The witness drives each
      of three layers above and below its threshold, and the total. It does
      so under the real shares and spec review cap, and again with all three
      patched to other values.
    witness: tests/test_cli.py::test_each_stack_layers_threshold_agrees_with_what_run_stack_batch_admits
    mutant:
      file: saffron/batch.py
      find: reserve_usd=reserve_usd + writer_usd,
      replace: reserve_usd=reserve_usd,
    wrong_versions:
      - The queue's arithmetic holds back a fixed half of `--budget` rather than reading both shares.
      - The queue's arithmetic uses a fixed $8 spec review rather than reading the cap.
      - The queue reads the shares from its own copy of the two constants' values, so a patched share changes the batch and not the queue.
      - The total is the last layer's threshold.
      - The shares helper reads the reserve share but copies the writer share's value.
---

## Context

Backlog item **b-0a08bf**, under `DESIGN.md` §7.1, which says to set the
nightly budget from the queue. Every line below was read at `958db033`.
`SA-0245` and `SA-0253` edit `saffron/cli.py` before this spec runs, so
its line numbers can move. Find each function by name.

**The queue prints no money.** `_queue` resolves the queue and calls
`_print_reconcile_summary` and `_print_queue`, then returns 0
(`saffron/cli.py:1876-1897`). `_print_queue` prints the candidates, the
refusals and the scan gaps (`saffron/cli.py:2085-2114`). `queue` takes
`--repo` and `--stack`, and no `--budget` (`saffron/cli.py:130-134`).

**A stack batch holds back two shares.** `_batch` computes both from
`--budget` under `--stack` (`saffron/cli.py:1558-1563`). The reserve is
`end_review.RESERVE_SHARE`, 0.25 (`saffron/end_review.py:44`). The writer
share is `follow_up.WRITER_SHARE`, 0.25 (`saffron/follow_up.py:32`).
`_batch` passes both to `run_stack_batch` (`saffron/cli.py:1740-1748`).
`run_stack_batch` hands their sum to `_drive` as `reserve_usd`
(`saffron/batch.py:768`).

**Admission is one comparison before each layer.** `_drive` stops `BUDGET`
when a candidate's `budget_usd` exceeds `budget_usd - reserve_usd -
ledger.batch_spend(batch_id)` (`saffron/batch.py:241-245`). Equality
admits. The batch's order is the scan's `candidates`, resolved with
`stack=args.stack` (`saffron/cli.py:1624-1631`, `:1651`). `saffron queue
--stack` resolves the same scan (`saffron/cli.py:1884-1886`).

**A layer's spec review spends after its own admission.** The runner is
called once the comparison passes (`saffron/batch.py:256-257`). Under a
stack batch that runner is `wrapped` (`saffron/batch.py:519`). It runs
the review first (`saffron/batch.py:562`). It records the review's cost
as an attempt on the minted task (`saffron/batch.py:588-597`). That
task's run joins the batch at its mint (`saffron/batch.py:538-540`). So
the cost counts against the next comparison. A review spends up to
`spec_review.SPEC_REVIEW_SESSION_USD`,
$8 (`saffron/spec_review.py:56`). So a layer's own review moves the next
layer's threshold, never its own.

**Revision rounds are not admission.** Each revision round meets its own
check first. It asks for a writer session, a review and the layer's
budget (`saffron/batch.py:661-686`). A shortfall refuses the layer
`unrevised`. The admission comparison never reads the writer session's
cost. This spec prints admission alone.

## Problem

1. **One helper for the shares.** Add a function in `saffron/cli.py` that
   returns the reserve and the writer share for a given `--budget`. It
   reads `end_review.RESERVE_SHARE` and `follow_up.WRITER_SHARE` at call
   time. `_batch` calls it for the two amounts it passes
   `run_stack_batch`, in place of its own two products. The queue's
   arithmetic calls it too. So the queue holds back what the batch holds
   back, by construction.
2. **The arithmetic.** Each earlier layer contributes its `budget_usd`
   plus one spec review. Layer `k`'s threshold adds those to its own
   `budget_usd`. Divide that sum by one less both shares. The total adds
   every layer's `budget_usd` plus one spec review, divided the same way.
   Read the review cap from `spec_review.SPEC_REVIEW_SESSION_USD` at call
   time.
3. **The printed block.** `_queue` prints it after `_print_queue`'s
   output, only under `--stack` and only with a candidate. For the
   witness's order it reads exactly as below.

   ```
   admission: reserve 25% and writer 25% of --budget held back, spec review $8.00 per layer, no revision round
     --budget $20.00 admits SY-1 (budget $10.00)
     --budget $64.00 admits SY-2 (budget $14.00)
     --budget $92.00 admits SY-3 (budget $6.00)
     --budget $108.00 runs every layer and its spec review
   ```

   Each share prints as a percent. Each amount has two decimals. Round it up
   to the cent, with a tolerance of 1e-9 so a float error adds no cent. No
   printed figure then sits below its threshold. A layer
   line never starts with two spaces and a spec id. The existing
   `test_queue_stack_prints_the_stack_order` reads such a line as a
   candidate (`tests/test_cli.py:2925`). Its filter sits at
   `tests/test_cli.py:2950-2951`.

## Out of scope

- A revision round's writer session. It meets its own check, not
  admission, as Context says.
- The follow-ups. Their pass holds back nothing
  (`saffron/batch.py:814`). The queue cannot see them.
- A `--budget` flag on `queue`, and any change to `saffron batch`'s own
  output.
- Any change to `_drive`'s comparison or to `run_stack_batch`.
- A cell spending past its own ceiling. The arithmetic assumes each
  earlier layer spends exactly its ceiling. A batch goes on after an
  overshoot (`tests/test_batch.py:430`).

## Notes for the agent

**Both criteria edit existing code, and both mutants sit outside it.** The
change edits `_queue` and `_batch`. Each mutant changes a value the new
arithmetic must read rather than copy. Criterion 1's mutant changes the
reserve share, so the printed block must change. Criterion 2's mutant
changes what `run_stack_batch` holds back, so the batch stops agreeing
with the printed thresholds. Leave `saffron/end_review.py` and
`saffron/batch.py` unedited. The wrong versions
under each criterion are what its witness must kill. Do not run them
yourself.

**Every witness must fail at base.** At base `_queue` prints no admission
line, so both witnesses find no block. Import nothing at module scope that
this change adds.

**One fixture serves both witnesses.** Build it with `_repo_with_spec`.
`SY-1.md` has `budget_usd: 10` and no parent. `SY-2.md` has `budget_usd:
14` and depends on `SY-1`. `SY-3.md` has `budget_usd: 6` and depends on
`SY-2`. `SY-4.md` has `budget_usd: 40` and depends on `SY-9`, which no
spec declares, so it is refused. Find the block as the lines from the one
starting `admission:` to the end of the output.

**Criterion 1.** Assert the five lines above exactly. Then run `queue`
without `--stack` on the same repo and assert no line holds `admission`.
Then build a second repo whose only spec, `SY-1`, depends on `SY-9`.
Assert `queue: 0 candidate(s)` and no `admission` line under `--stack`.

**Criterion 2.** Run `saffron queue --stack` on the fixture and parse each
amount from the block. For each layer, run `main` with `batch --stack
--budget` at its threshold plus 0.01, then minus 0.01, each on its own
`--home`. Then run it at the total.

- Fake readiness with `_readiness_passes`. Inside a `monkeypatch.context()`,
  replace `cli._resolve_queue` with `_fake_batch_resolution` carrying three
  `Candidate`s that match the fixture's ids, budgets and parents. The
  context keeps the next `queue` call real.
- In the same context, replace `cli.run_stack_batch` with a wrapper. It
  calls the real `saffron.batch.run_stack_batch` with the order, ledger,
  budget and readiness check it was given. It passes on the `reserve_usd`
  and `writer_usd` `_batch` gave it. It substitutes its own runner, review
  and mint, and passes no end review, follow-ups or finish.
- The mint opens a run and a task, as `MintDouble` in `tests/test_batch.py`
  does. The review returns a `SpecReviewSession` with an empty fenced
  findings block, costing `spec_review.SPEC_REVIEW_SESSION_USD` as read at
  call time. The runner records the spec id, opens a run and a task, and
  closes one attempt costing the layer's `budget_usd`. It returns
  `READY_FOR_REVIEW`.
- Above layer `k`'s threshold, assert the runner started exactly the first
  `k` layers. Below it, assert exactly the first `k - 1` and the stop
  reason `BUDGET`. At the total, assert all three started and the stop
  reason `DRAINED`. Assert `ledger.batch_spend` equals the total less the
  two shares `_batch` passed, within half a cent.
- Run the whole case under the real values, where the block parses to
  20, 64, 92 and a total of 108. Then patch `end_review.RESERVE_SHARE` and
  `follow_up.WRITER_SHARE` each to 0.375, and
  `spec_review.SPEC_REVIEW_SESSION_USD` to 3.0. Run the case again. The
  block then parses to 40, 108, 144 and a total of 156. Assert both lists.
  Each patched value differs from its real one, so a copied constant
  fails.

**Measured on a prototype.** A prototype at `958db033` passed both
witnesses, and each failed with `saffron/cli.py` reverted. Its diff
measured 828 changed tokens. Every wrong version above but the refused
spec's was applied as an edit, and so was each declared mutant. Each
failed its own criterion's witness. The
existing `tests/test_cli.py` and `tests/test_batch.py` still passed.
