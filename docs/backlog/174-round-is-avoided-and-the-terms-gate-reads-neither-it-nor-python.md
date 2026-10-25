---
id: 174
title: '"round" is on Attempt''s _Avoid_ line, and the `terms` gate reads neither it nor a `.py` file'
status: open
tier: 3
filed: 2026-09-17
specs: []
prs: []
commits: []
cites: []
related: [156, b-8220e6]
---

## Problem

Found reviewing `SA-0096` (PR #320), 2026-09-17. The cell wrote "a REBUT-round
lens" in a test docstring. `CONTEXT.md`'s **Attempt** entry lists "round" on
its _Avoid_ line. The review fixed it on the branch.

No gate caught it. `.saffron/gates/prose.py`'s `AVOIDED` table (`:120`) does
not list "round", and the `terms` rule reads only `.md` files.
`saffron/phases/review.py:144` has the same word on `main`: "the implementer
spends a REBUT round arguing".

## Done looks like

"round" is a `_Confusable_:` phrase under each entry that avoids it, which
ADR 11 makes the conventions lens's to judge. `AVOIDED` is deleted by
b-8220e6. `terms` reads Python docstrings and comments, or a recorded
decision says why not. `review.py:144` is fixed.

## Record

- 2026-09-19: still open after the spec loop's run 8. `check()` returns no hit
  for a `.py` file under `terms` (`.saffron/gates/prose.py:415-418`). So
  `CONTEXT.md`'s _Avoid_ words in a Python comment or docstring reach no gate,
  and the loop's Standards seat reads them by hand.
- 2026-10-24: ADR 11 (#963) makes "round" a confusable phrase, so the first
  arm of Done moved from `AVOIDED` to a `_Confusable_:` line.
