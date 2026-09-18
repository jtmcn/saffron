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
related: [156]
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

`AVOIDED` lists "round" with its term. `terms` reads Python docstrings and
comments, or a recorded decision says why not. `review.py:144` is fixed.
