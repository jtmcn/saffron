---
id: b-47659f
title: The criterion-probe witness reads a container name that outlives teardown, so a probe asked after it passes unverified
status: open
tier: 2
filed: 2026-09-29
closed:
specs: []
prs: []
commits: []
cites: [§5.5]
related: [b-7e69d0, b-2750d5, b-76953a]
---

## Problem

Found in the spec loop's run 21, 2026-09-29, by the Spec seat on #576
(`SA-0190`). **Unverified.** No probe ran against it.

`SA-0190`'s witness for wrong versions checked
`cell.turn_containers[6] == _CRITIC_CONTAINER`. The container name stays the
same after teardown. A `run_wrong_versions` call moved past the `with
critic_cell(...)` block survived. Review fixed it with a `cell.order`
timeline assertion.

`SA-0120`'s criterion-probe witness checks the same shape,
`cell.turn_containers[6:] == [_CRITIC_CONTAINER] * 2`
(`tests/test_session.py:7273` at `d2ea4afe`). The seat read it as blind to
`run_criterion_probes` asked after teardown in the same way.

## Done looks like

Move `run_criterion_probes` past the critic cell's teardown and run the
witness. If it passes, it asserts on `cell.order` the way `SA-0190`'s now
does.

## Record

- 2026-09-29: filed from the spec loop's run 21.
