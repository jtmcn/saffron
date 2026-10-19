---
id: b-b8f0d9
title: The state clause of REBUT's cut check is pinned by no test, so a cap cut that ends another way could read as `EXHAUSTED`
status: open
tier: 3
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§5.6]
related: [120]
---

## Problem

Found by the Spec seat on #903, in the spec loop's run 44.

The cut check reads `cut = cap.cut is not None and result.state ==
"REBUTTAL_UNJUDGED"` (`saffron/cell/session.py:3580`). The seat dropped the
state clause, and 427 tests across the session, rebut, task and batch suites
still passed. The delegate re-ran the probe: 326 passed. The same clause was
equally unpinned at base, when it compared against `REBUTTING`.

Without the clause, a cap-cut REBUT that ended `GATE_ERROR` from a lens that
never started would read as `EXHAUSTED`. Whether a cut and that state can meet
in a real run is unmeasured.

## Done looks like

A witness drives a cap cut that ends in a state other than
`REBUTTAL_UNJUDGED` and asserts the task does not end `EXHAUSTED`. The probe
above then fails it.

## Record

- 2026-10-19: filed from the spec loop's run 44.
