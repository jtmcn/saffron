---
id: b-fa014a
title: REBUT's post-repair re-run reuses the pre-repair exempt set, and two of its branches have no witness
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§5.6]
related: [b-0bd346]
---

## Problem

Found in the spec loop's run 47, in the seats' review of `SA-0311` (#955).

After the repair turn, every gate re-runs with the `revert_exempt` that the pre-repair
patch earned. No probe asks again whether a probed fix survived the repair. The Spec seat
flagged this as unverified.

Two branches of that re-run survive deletion against the whole suite. One is the
`probe_infra` rule and the other is the `exempt` argument. Review added a witness for the
drifted re-run alone.

## Done looks like

The post-repair re-run probes the repaired patch, or a test shows why the pre-repair
set still holds. Each of the two branches has a witness that fails when it is deleted.

## Record

- 2026-10-24: filed from the spec loop's run 47.
