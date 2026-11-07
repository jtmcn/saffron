---
id: b-c9a913
title: "A criterion probe is judged against its declared witness alone, so a blocker another test kills stands after REBUT"
status: superseded
tier: 2
filed: 2026-10-10
closed: 2026-11-07
specs: [SA-0322]
prs: [794, 801, 978]
commits: []
cites: [§5.5]
related: [117, b-b9365d]
superseded_by: b-b9365d
---

## Problem

Found in the spec loop's run 33, on `SA-0242` (#794) and `SA-0248` (#801).

The host runs an adequacy probe against the one witness the criterion
declares. On both layers the probe survived that witness, so the blocker
stood after REBUT and the implementer argued it.

- **`SA-0242`:** another test killed the inversion,
  `test_a_red_rebuttal_line_names_each_gate_that_failed_anew`.
- **`SA-0248`:** the declared witness never reaches REBUT. Flipping
  `GATE_ERROR` to `EXHAUSTED` at `saffron/phases/rebut.py:739` survived it.
  `tests/test_rebut.py::test_a_post_rebuttal_binary_change_ends_gate_error`
  killed it (1 failed).

The delegate settled each one by re-running the probe by hand. The cell
cannot tell a vacuous suite from a misnamed witness.

## Done looks like

- A probe that survives the declared witness is run against the whole
  `tests` gate.
- A probe that some other test kills is reported as a misnamed witness, and
  it is no blocker.
- A test drives both outcomes.

## Record

- 2026-10-10: filed from the spec loop's run 33.
- 2026-11-07: superseded in grooming by b-b9365d, the same defect filed from
  run 48 and done by `SA-0322` (#978). A survived criterion probe now asks the
  whole `tests` gate and names each test that failed under its edit
  (`saffron/phases/review.py`, `SUITE_KILL_SENTENCE`). The second bullet here
  was decided the other way in `SA-0322`'s Context: a suite kill can be a
  style failure, so it informs the blocker and never downgrades it.
