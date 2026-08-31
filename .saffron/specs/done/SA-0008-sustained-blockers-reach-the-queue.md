---
id: SA-0008
title: §6's level 3 has a definition, a measurement behind it, and no implementation
type: bug
priority: 1
touches:
  - saffron/phases/rebut.py
  - saffron/report/index.py
  - saffron/phases/package.py
  - tests/test_rebut.py
  - tests/test_report.py
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/phases/review.py
  - saffron/cell/session.py
budget_usd: 8
max_attempts: 4
max_turns: 80
risk: elevated
---

## Context
`DESIGN.md` §6 rev 17 added sort level 3 — **sustained blockers, descending** —
and says in the same breath that it is the one level `sort_key` does not
implement. That gap is deliberate and it is not meant to last: §6 is
authoritative, and it currently describes a page the code does not produce.

The level exists because of a measurement, not an argument
(`docs/evidence/2026-08-25-morning-queue-from-real-rows.md`). Rendering the
morning queue from this machine's real ledger put `SA-0005` — the most expensive
task Saffron has produced, $10.07 over 8 phase-sessions — on the **bottom line of
ten**, captioned `0 concerns`, while it carried a blocker the critic confirmed
against the implementer's argument. `rebut.py` hands that case to the operator as
*"recorded disagreement, yours to adjudicate"*. The page never mentions it.

## Problem
Two mechanisms, and neither is in `report/index.py` by accident:

- `anchored_concerns` sums `severity == "concern"`. A blocker is not a concern at
  any verdict, so a sustained one contributes **nothing** to the number the page
  ranks on.
- `sort_key`'s `_ORDINARY` bucket ranks on that count alone, with nothing above it.

So the ranking is not merely incomplete — on the one task in the ledger that
produced a recorded disagreement, it ranks that task *last*. A page whose stated
job is "dismiss in 10 seconds, accept in two minutes" puts the row you must not
accept where you will never reach it.

**The counting rule is the whole task, and the obvious version of it is wrong.**
`rebut.py` verdicts `confirmed` against a `fixed` rebuttal exactly as readily as
against an `argued` one — the critic is confirming that the finding was real, not
that it is outstanding. Counting every `confirmed` blocker would rank a task by
work the implementer had **already committed**, which is the mirror of the defect
this level exists to fix. Measured on `SA-0005`: three blockers filed, two
anchored, both confirmed — one `argued`, one `fixed`. The sustained count is
**one**, not two and not three.

## Acceptance criteria
- [ ] `rebut.py` exposes one function returning the sustained-blocker count: a
      blocker whose `Verdict.verdict` is `confirmed` **and** whose `Rebuttal.action`
      is `argued`, paired on the shared 1-based blocker number
- [ ] It returns `0` when `rebut_result` is `None`, when the rebuttal turn
      errored, and when a blocker was verdicted but never rebutted
- [ ] `QueueLine` carries the count and `_row` renders it, in a cell that is
      visibly distinct from the concern cell
- [ ] `sort_key` ranks any line with a non-zero count above `risk: elevated` and
      above the concern bucket, descending by the count; `_STATE_RANK`'s existing
      ranks 3 and 4 shift to 4 and 5, and `REVIEWING`/`REBUTTING` keep sorting
      with elevated risk
- [ ] `package.py` supplies the count from `outcome.rebut_result`, and the test
      for it asserts **at `package.package`** — not by constructing a `QueueLine`
      and asserting on the value it was handed
- [ ] A test on `SA-0005`'s real shape: three blockers, two anchored, one
      `argued`+`confirmed` and one `fixed`+`confirmed`, asserting the count is `1`
- [ ] A test that a line with one sustained blocker and `0` concerns sorts above
      a green `elevated` line with `2` concerns

## Out of scope
`saffron/phases/review.py` is **forbidden**. `anchored_blockers` and
`anchored_concerns` are both correct and both load-bearing: the first defines the
order `rebut.py` numbers from and the pull-request body renders against, and the
second is the concern count this task ranks *below* rather than replaces. Do not
widen either to mean something new — the new rule is a new function.

`session.py` is forbidden for the same reason it was in `SA-0007`: the producer
already carries `rebut_result` out on `CellOutcome`, and this task's failure mode
is changing a correct producer to suit a consumer that was not reading it.

Do not change §6, `CONTEXT.md`, or the evidence record. §6 is the specification
being implemented; if the code cannot match it, that is a finding to report, not
a document to edit.

## Notes for the agent
**The numbering is global, not per-lens.** `rebut.py:374` does
`enumerate(blockers, 1)` over `anchored_blockers(reviews)` — every lens then
verdicts a subset of *those* numbers. So a `Verdict` and a `Rebuttal` pair on one
shared index across all lenses, and the count must not be computed per lens and
summed.

**Only anchored blockers reach REBUT** (`review.py:231`, §5.5). An unanchored
blocker has no verdict and no rebuttal and must not be counted or crashed on.
`SA-0005`'s third blocker is exactly this case.

**`QueueLine` is constructed by a test factory.** `tests/test_report.py:194` does
`QueueLine(**{**defaults, **overrides})`; a new field without a default breaks all
52 tests in that file at once. The dataclass already ends with defaulted fields,
so the new one goes after them.

**The trap this repository has fallen into five times** (`docs/BACKLOG.md` item
18): a value that is computed, carried, and read by nobody, with tests that pass
because they hand the function the argument they then assert on. `SA-0005` shipped
green with exactly that defect and the critic caught it. A test that builds a
`QueueLine` with `sustained=1` and checks it sorts first proves `sort_key` works;
it proves nothing about whether `package.py` ever passes a non-zero value. **The
assertion that matters belongs at the caller.**

Commit after each coherent step. Uncommitted work dies with the cell.
