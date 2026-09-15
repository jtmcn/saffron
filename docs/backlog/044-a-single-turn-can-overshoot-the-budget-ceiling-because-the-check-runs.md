---
id: 44
title: A single turn can overshoot the budget ceiling, because the check runs before it
status: done
tier: 0
closed: 2026-09-05
specs: [SA-0031, SA-0050, SA-0059]
prs: [121]
commits: [57b676c]
cites: [§3, §9]
related: [56, 58, 73]
---

## Problem

**Status: done** — `SA-0050`, PR #121, merge `57b676c`. `run_batch` computes
`budget_usd - ledger.batch_spend(batch_id)` before each candidate, reading
spend back out of the ledger rather than trusting a tally kept in the loop —
which is what survives a caller cut mid-night.

The wording this item settled needed one correction after review, and
`DESIGN.md` §3 and `CONTEXT.md` now carry it: the batch bound is *also*
best-effort, because it admits a task on that task's **declared** ceiling. A
night can end at most one task's overshoot above budget. Bounded by one
overshoot rather than unbounded is the real distinction, and it is the whole
value of checking between tasks.

Option one is rejected for the reason this item states about itself: a turn's
cost is not knowable until it ends, so charging a worst-case estimate means
*guessing* the bound. That is the defect item 56 argues against for size
predicates, and here it is worse — a guess that refuses a legitimate turn costs
more than a 6.5% overshoot.

The reframe is what §9's v1 target buys. Unattended, one task running $1.17
over is not the exposure; a night spending unboundedly is. Between tasks
nothing is mid-flight, which is exactly why a bound is enforceable there and
cannot be inside a turn. **Tier 0**, with item 58.

`_over_budget` gates a turn on what has been spent *so far*. It cannot bound
what the turn about to run will cost, and a turn's cost is not knowable until
it ends.

The overshoot is bounded only by the turn ceiling and the wall clock, which are
the same two bounds that let the turn get long in the first place. A task with
`max_turns` raised — the obvious response to a turn that ran out of turns — has
a proportionally larger overshoot available to it.

## Done looks like

Done looks like a decision about which of two honest options to take, not a
patch: charge the ceiling *before* a turn against a worst-case estimate and
refuse a turn that could exceed it, or accept that `budget_usd` is a
best-effort bound and say so where it is declared. What it should not stay is a
number the system reports as a ceiling and enforces as a suggestion.

## Record

Measured on `SA-0031`, 2026-09-01. Admitted under an $18.00 budget with roughly
$6 spent, its IMPLEMENT turn ran to the 140-turn ceiling and cost **$13.18 on
its own**, ending the run at **$19.17 — 6.5% over a ceiling it never checked
against.** The ledger row records `budget_usd 18.0, spent_usd_est 19.165`.

**Decided 2026-09-04: option two, plus the ceiling that is actually
enforceable.** `budget_usd` is a best-effort bound and says so where it is
declared. The enforceable ceiling is **per batch, checked between tasks** —
folded into item 58.

**One task's overshoot is one attempt, not one turn** (item 73, corrected
2026-09-12). The $1.17 and 6.5% below are a turn's. `SA-0059` measured the
attempt: $26.75 against a $16 ceiling, inside a $22 night that closed 21% over.
