---
id: 73
title: The budget overshoot is one attempt, not one turn, and the design says 6.5%
status: done
tier: 1
filed: 2026-09-06
closed: 2026-09-12
by_hand: true
specs: [SA-0031]
prs: []
commits: [a960687]
cites: [§3, §5.4]
related: [44]
---

## Problem

**Tier 1.** Measured 2026-09-06 driving `SA-0059`
(`docs/evidence/2026-09-06-an-attempt-is-the-overshoot-bound.md`).

A task declaring `budget_usd: 16` spent **$26.75**, inside a night whose budget
was $22. Both ceilings were exceeded, and neither is broken in the way its
documentation implies.

`session._over_budget` is `spent < spec.budget_usd`, evaluated *between*
attempts. Nothing caps an attempt's cumulative cost: `max_budget_usd` caps a
single turn inside the cell and `max_turns` caps the count, so an attempt is
bounded by their product. Measured — an attempt admitted at $12.64 against a
$16 ceiling ran to its 110-turn limit and cost $14.11.

**`DESIGN.md` §3 cites the overshoot as "measured at 6.5% on `SA-0031`".** That
is a *turn's* overshoot and it is a true measurement of the wrong unit. The
overshoot that matters is an attempt's, and here it was 67% of the ceiling.
`CONTEXT.md`'s Task entry and item **44**'s closure inherit the same
understatement — "at most one task's overshoot" is structurally right and reads
as small.

**What is *not* wrong.** The bound holds: `run_batch` checks derived spend
before each candidate, so a night overspends by at most one task's overshoot
rather than one per task. A ten-task night does not drift ten times. The defect
is that three documents describe that bound in a way that makes it sound like a
rounding error.

**Not** a finding about `SA-0059`'s size. Nine files at `elevated` exhausting
two attempts is a spec too large for one cell, which is separate and is why
`EXHAUSTED` was the honest outcome.

## Done looks like

a decision between two answers, taken deliberately:

- **Say it accurately.** Amend §3, `CONTEXT.md` and item 44 to name the
  attempt as the unit and this run as the measurement. Cheapest, changes no
  behaviour, and leaves an unattended night able to end ~1.7x a task's ceiling
  over budget.
- **Bound it.** Refuse an attempt whose *remaining* budget is less than some
  fraction of a whole one, rather than merely greater than zero — the ceiling
  becomes a real bound at the cost of ending some tasks earlier than they need
  to end. Note this interacts with `max_attempts`: a task that would have
  passed on attempt 3 is refused into `EXHAUSTED` instead, which spends the
  money and gets nothing.

The first is not a lesser fix. §5.4's whole argument for `budget_usd` being
best-effort is that guessing a bound costs more than the overshoot; the same
argument applies here, and the honest answer may be that only the documentation
is wrong.

## Record

**Status: done, 2026-09-12, by hand — the first answer below, *say it
accurately*.** `DESIGN.md` §3, `CONTEXT.md`'s Task entry and item 44's closure
now name the attempt as the unit and `SA-0059`'s $26.75 against $16 as the
measurement. No behaviour changed: an unattended night can still end about
1.7× a task's ceiling over budget, and that is now what the documents say.
