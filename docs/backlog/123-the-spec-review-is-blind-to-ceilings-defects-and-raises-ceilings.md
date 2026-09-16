---
id: 123
title: The spec review is blind to ceilings defects and raises ceilings blockers the outcome contradicts
status: partial
tier: 3
filed: 2026-09-14
specs: [SA-0092]
prs: [279]
commits: []
cites: []
related: [124, 125, 144, 145]
---

## Problem

**Tier 3.** Found running the spec review's 2026-09-14 backtest.

- It missed every recorded ceilings defect: SA-0031, SA-0087@24edb32 and
  SA-0059 were marked `checked` or blamed on the wrong cause.
- It raised two ceilings blockers that the cells contradicted: SA-0060 and
  SA-0027 finished inside the ceilings it called too low.
- Evidence: `docs/evidence/2026-09-14-spec-reviewer-backtest.md`.

## Done looks like

check 4 either reads `history`'s peak and endings correctly on the recorded
cases, or is dropped from the spec review in favour of a deterministic
comparison in `driver.py history`.

## Record

**Filed 2026-09-14.**

**2026-09-16, `SA-0092` ran and is open as PR #279.** `history` now computes the
comparison check 4 was reading by eye: the max peak among the rows it printed,
the max pre-REVIEW spend, direction and magnitude against each declared ceiling,
and a cut-off row's peak called a floor rather than a use.

The review found the line said "above by 0t" when `max_turns` *equals* the peak —
the threshold `.claude/agents/spec-reviewer.md` itself calls a blocker, rendered
as headroom. It also found the direction words witnessed one way each, so
hardcoding both passed all 2075 tests, with ceiling-below-peak being `SA-0031`,
the very case this item cites.

Two things the item still needs. The prompt that should read the line does not
know it exists (item **145**) — until it does, the comparison is computed and
ignored. And `endings` still hides any attempt that ended abnormally while its
subtype read `success`, six of which are in the live ledger (item **144**).

This run also produced a third data point for the check-4 caveat, against the
operator's own decision: `SA-0091`'s ceilings were raised on measured evidence —
`SA-0088` had just exhausted 80 turns on five of the same six files — and the
cell then peaked at **60** turns and $8.39 of $16. Neither raise bound. The
reasoning was sound before the fact and the raise cost nothing, which is the
shape this item should expect: check 4's forecasts are weak in *both* directions,
and the line is worth more than the judgement either way.

**2026-09-16, partial.** `SA-0092` merged as PR #279, so `history` computes the
comparison rather than asking a spec review to make it by eye. The item stays
open in two places: `.claude/agents/spec-reviewer.md` check 4 still says to
compare by eye and does not know the line exists (item **145**), so the line is
computed and unread; and `endings` still hides an attempt that ended abnormally
while its subtype read `success` (item **144**), six of which are in the live
ledger.

