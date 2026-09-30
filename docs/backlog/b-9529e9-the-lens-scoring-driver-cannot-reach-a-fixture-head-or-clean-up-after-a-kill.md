---
id: b-9529e9
title: The lens scoring driver cannot reach a fixture head or clean up after a kill
status: open
tier: 3
filed: 2026-09-29
specs: []
prs: []
commits: []
cites: []
related: [79, b-abeb74]
---

## Problem

Found running ADR 8's pass for `SA-0195`, 2026-09-29.

- **Fixture heads.** Two of five fixture heads sit only on `refs/fixtures/*`.
  The driver's mirror fetches every ref. But the cell seeds its clone with
  `git fetch origin`, which takes `refs/heads/*` only. So `SA-0184`'s and
  `SA-0186`'s runs failed with `fatal: unable to read tree`. Local branches
  at each head fixed it by hand.
- **A kill.** A run lasts 13 to 15 minutes. Ten runs outlasted the 2-hour
  background limit, and the kill left the scoring cell and `saffron-proxy`
  running. The delegate removed both. A later cell would have met them.
- **No resume.** A killed pass restarts from its first fixture.

## Done looks like

The driver reads a fixture head the cell can reach, or seeds the cell with
it. A SIGTERM tears the cell and the proxy down. A pass skips a fixture whose
output directory already holds a scored run.

## Record

- 2026-09-29: filed from the spec loop's run 22.
