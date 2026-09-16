---
id: 148
title: Two witnesses tell the pre- from the post-rebuttal tree by counting turns, in hand-maintained copies
status: open
tier: 2
filed: 2026-09-16
by_hand: false
specs: [SA-0088, SA-0091]
prs: [277, 284]
commits: []
cites: []
related: [118, 140]
---

## Problem

**Tier 2.** Found reviewing `SA-0091` (PR #284).

`tests/test_session.py` now has two witnesses whose `export_patch` stub decides
which diff to return from `len(cell.turns) > 5`, with the same magic threshold
and the same comment copied between them:

> plan, implement, 3 lenses, rebuttal, extraction = 7 turns by the time REBUT
> asks for a critic cell

It is correct today. Any new REVIEW or IMPLEMENT turn silently invalidates both:
the stub would hand the wrong diff to the wrong phase, and the tests would pass
or fail for the wrong reason. There is no gate on it and nothing links the two
copies.

The review already had to reach past this once — the stub keyed on the turn count
alone, so a re-export from the *implementer's* container returned the reviewed
diff and 202 tests stayed green. The fix keyed it on the container too, which
narrows the exposure without removing the threshold.

## Done looks like

One shared helper, or a boundary keyed off the rebuttal's own commit rather than
a turn count, so adding a turn anywhere cannot silently re-point either stub.
