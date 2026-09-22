---
id: b-408cf5
title: The plan checkpoint refuses on a ceiling the `size` gate would not have enforced
status: open
tier: 1
filed: 2026-09-19
specs: [SA-0125]
prs: []
commits: []
cites: [§5.3, §5.4]
related: [40, b-17fb8b]
---

## Problem

Found in the spec loop's run 9, 2026-09-19. It cost `SA-0110` a whole cell.

`validate_plan` refuses a plan whose own `estimated_lines` exceeds the ceiling
for the spec's type (`saffron/agents/artifacts.py:288-292`). Its message says
"the diff `size` gate will fail on before a single edit is made". That sentence
is false whenever `size` is advisory. The gate blocks only at an elevated risk
tier (`saffron/gates/core/size.py`, `.saffron/policy.yaml`'s `elevate_on`), and
`SA-0110` touches `records/` and `tests/records/`, which elevate nothing.

So the cell died at PLAN_REJECTED on 620 estimated lines against a 600 ceiling
that passes the diff. $1.20 spent, nothing edited. The operator then cut two
acceptance criteria out of the spec to get the *planner's own estimate* under a
number that never bound anything.

The estimate is also the wrong instrument for the refusal. It is the model's
guess before it writes anything: the same scope was estimated at 620 by one
cell and 520 by the next, and the spec reviewer priced it at 505.

## Done looks like

The plan checkpoint computes the effective risk the way `GateSuite` does, and
refuses only when `size` would block. When `size` is advisory it says so in the
plan record rather than ending the task. A refusal message that names a gate
can be checked against that gate's own verdict.

## Record

- 2026-09-19: filed from the spec loop's run 9 (#375, #377). Ranked first in
  `docs/evidence/2026-09-19-spec-loop-skill-feedback-run-9.md`.
- 2026-09-21: a second occurrence, in the spec loop's run 11 (#406). Nothing
  told `SA-0115`'s cell that `size` is advisory at `risk: standard`. Its implement
  turn made 18 `pytest` calls while compacting toward 600 lines, and the 900s turn
  wall cut it (`saffron/cell/session.py:65`). The fixture it compacted lacks cases
  the spec named. `SA-0116`'s spec now tells the cell by hand (#407).
