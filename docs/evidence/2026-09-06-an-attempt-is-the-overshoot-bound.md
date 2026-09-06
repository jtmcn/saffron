# What a task actually overshoots its budget by

**Run:** `saffron batch --repo . --budget 22 --until 06:30`, 2026-09-06,
driving `SA-0059` (declared `budget_usd: 16`, `max_attempts: 4`,
`max_turns: 110`). **Result:** `EXHAUSTED`, no pull request, **$26.75 spent**.

The night's budget was $22 and it spent $26.75. The task's own ceiling was $16.

## The attempts

| phase | n | turns | cost | terminal reason |
|---|---|---|---|---|
| IMPLEMENTING | 1 | 27 | $2.80 | completed |
| IMPLEMENTING | 2 | 111 | $9.84 | max_turns |
| REPAIRING | 1 | 111 | $14.11 | max_turns |
| | | | **$26.75** | |

## Why the ceiling did not hold

`session._over_budget` is `spent < spec.budget_usd`, and it is evaluated
*between* attempts:

```
after IMPLEMENTING n=1   $2.80  < $16  -> admit the next
after IMPLEMENTING n=2  $12.64  < $16  -> admit the next
REPAIRING n=1 runs to its 110-turn ceiling and costs $14.11
```

Nothing caps an attempt's *cumulative* cost. `max_budget_usd` is handed to the
agent runtime and caps a single **turn**; `max_turns` caps the count. An
attempt is therefore bounded by `max_turns × per-turn cap`, and an attempt
admitted at $12.64 against a $16 ceiling spent $14.11.

**So the overshoot bound is one attempt, not one turn.** That is the number
this record exists to correct.

## What `DESIGN.md` claims, and what it should

§3 says `budget_usd` is best-effort because "a turn's cost is not knowable
until it ends", and cites the overshoot as **"measured at 6.5% on
`SA-0031`"**. Both halves are true about a *turn* and neither describes what
happened here:

| | |
|---|---|
| documented overshoot | 6.5% of the ceiling |
| measured here | **67%** of the ceiling ($26.75 against $16) |

The mechanism is the same — a unit admitted under the ceiling can finish over
it — but the unit is an attempt, and an attempt that runs to `max_turns` can
cost most of a ceiling again by itself.

## And it propagated to the batch

`run_batch` admits a candidate when `candidate.spec.budget_usd <= budget_usd -
batch_spend(batch_id)`: $16 <= $22 - $0, so it ran. The night then closed at
$26.75 against a $22 budget — **21% over**.

That is exactly the shape `docs/BACKLOG.md` item 44's closure describes — "a
night can end at most one task's overshoot above budget" — and it is the first
measurement of how large one task's overshoot is. It is not a small percentage.

## What this does not say

The bound still holds structurally: the batch checked derived spend before the
candidate, so a night overspends by at most **one** task's overshoot, not by
one per task. A ten-task night does not drift ten times. What is wrong is the
magnitude anyone would infer from "6.5%".

Nor does it say the ceilings are misconfigured. `SA-0059` is nine files at
`elevated`; two attempts hitting a 110-turn ceiling is the spec being too large
for one cell, which is its own finding and is why `EXHAUSTED` is the honest
outcome. The budget observation is independent of whether this spec should have
been split.
