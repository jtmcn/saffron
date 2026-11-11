---
id: b-0bd346
title: REBUT ends a task `EXHAUSTED` on a gate failure its own fix introduced, with no repair turn
status: partial
tier: 2
filed: 2026-10-23
specs: [SA-0311]
prs: [929, 955]
commits: []
cites: [§5.5]
related: [b-b8f0d9, b-619b7d]
---

## Problem

Found in the spec loop's run 46, on `SA-0298`.

REBUT fixed all five blockers on `SA-0298`, and the re-probe killed each one.
The gates then ran on the moved head. `prose` failed on five hits in the test
comments REBUT itself wrote. REBUT does not re-enter repair, so the task
ended `EXHAUSTED` at $9.61 with its branch pushed and no pull request.

The delegate fixed three comments by hand, opened #929 and ran
`saffron adopt`. The ledger kept `EXHAUSTED`, so the loop's driver could not
stack or size the task (b-619b7d).

## Done looks like

A red gate after REBUT, on a head REBUT moved, earns one repair turn bounded
by the task's remaining budget. A task whose only red gate after REBUT is one
REBUT's own commit introduced does not end `EXHAUSTED` without that turn.

## Record

- 2026-10-23: filed from the spec loop's run 46. The REBUT log is
  `~/.saffron/batches/v0/SA-0298/rebuttal.json`.
- 2026-10-24: done by `SA-0311` (#955), from the spec loop's run 47. The
  delegate also declared `format`, `lint` and `prose` as form gates in
  `.saffron/policy.yaml`, a hand commit on that layer.
- 2026-11-10: reopened from the spec loop's run 58. `SA-0311` gave a repair
  turn to the form gates alone. On `SA-0360` REBUT fixed all seven blockers
  and added a call `ty` rejects. `types` and `tests` went red, and the task
  ended `EXHAUSTED` at $43.27 of $60. The delegate fixed it by hand on #1117.
