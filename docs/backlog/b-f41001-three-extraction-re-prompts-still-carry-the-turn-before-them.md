---
id: b-f41001
title: Three extraction re-prompts still charge a killed turn the cost of the turn before them
status: done
tier: 3
filed: 2026-11-11
closed: 2026-11-11
specs: []
prs: [1152]
commits: []
cites: [§4.1]
related: [b-6a101f, b-593d50]
---

## Problem

Found by the review of #1147, which closed b-6a101f for REBUT alone.

`run_agent` charges a turn killed before its result event
`max(floor_usd_est, last_cost_usd)` (`saffron/phases/implement.py:392`).
Three extraction re-prompts still pass the turn before them as that carry:

- the lens re-prompt (`saffron/phases/review.py:279`)
- the plan's scope re-prompt (`saffron/cell/session.py:698`)
- the plan's schema re-prompt (`saffron/cell/session.py:731`)

Each one resumes after a full turn. A crashed re-prompt is then charged that
whole turn a second time. Specs pinned the carry as a criterion, as in
`tests/test_review.py:1467` ("passes its cost as `last_cost_usd`"), so this
reverses a recorded choice.

REBUT's fix turn carries the implement turn's cost the same way
(`saffron/phases/rebut.py:279`). There a crash can still print "REBUT ran out
of its $10.00 budget".

## Done looks like

A killed extraction re-prompt adds only its own floor. The criteria that pin
the carry say why the extraction is the exception. REBUT's fix turn is
decided either way, with the reason written down.

## Record

- 2026-11-11: filed from the review of #1147.
- 2026-11-11: done by hand in #1152. Five re-prompts pass no carry. REBUT's
  fix turn keeps its carry, since it is a full turn of the implement session.
