---
id: b-cf832a
title: '`revert` gives no verdict when one new test cannot be collected at base, so it checks no witness in the subset'
status: open
tier: 1
filed: 2026-09-29
closed:
specs: []
prs: []
commits: []
cites: [§5.4]
related: [50, 51, b-4a63b7, b-76f08d, b-7e69d0]
---

## Problem

Found in the spec loop's run 21, 2026-09-29. Measured at `095e9fef` before any
cell ran.

`revert` hands the reverted run every new test id at once. Two shapes make that
run uncollectable at base.

- A parametrised id absent at base. pytest exits 4 on it. `SA-0191`'s
  `[conventions]` ids were this shape.
- A module-scope reference to a new name. The whole file becomes a collection
  error. `SA-0187`'s `TURN_PROMPTS` in `tests/test_context.py:536-547` reads
  `review.WRONG_VERSION_PROMPT` at import.

`.saffron/gates/tests.py:73` maps exit 3 or 4 to `error`. `revert` maps a run
with no readable verdict to `skip` (`saffron/gates/core/revert.py:274` at
`095e9fef`). One uncollectable id therefore skips the whole subset. `SA-0187`
ended green with `revert` at `skip`, and its seat traced the cause by hand.
Run 21 worked around `SA-0191` with a declared mutant instead (#573).

Item 50 is the same defect. `GateResult.uncollected` exists since `SA-0127`,
and this repo's `tests` gate still leaves it empty.

## Done looks like

- `.saffron/gates/tests.py` fills `uncollected`, which closes item 50. An id
  absent at base then reads as uncollected, not as a broken run.
- Or `revert` runs each new witness id on its own and deselects the ones that
  cannot be collected.
- The spec writer learns that a test module binds no new name at import, and
  `TURN_PROMPTS` becomes lazy.

A test drives one uncollectable id beside one real witness and reads a verdict
for the real one.

## Record

- 2026-09-29: filed from the spec loop's run 21.
