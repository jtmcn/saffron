---
id: b-9efbe2
title: A child's cell can weaken its parent's witness, and no gate re-checks the parent's wrong versions
status: done
closed: 2026-11-16
tier: 2
filed: 2026-10-12
specs: [SA-0270, SA-0401, SA-0402]
prs: [856, 1232, 1233]
commits: []
cites: [§5.4, §5.5]
related: [b-20043f]
---

## Problem

Found by both review seats on #856, in the spec loop's run 36.

`SA-0270` moved every task network onto a subnet pool. Its cell had to edit
`SA-0269`'s witness
`test_two_tasks_bring_up_and_tear_down_only_their_own_networks_and_proxy`,
because the seeding read a subnet the pool replaced. The cell deleted the
seeding instead of moving it. The test then held none of the other task's
networks. `SA-0269`'s own wrong version, a pre-clean that sweeps every
`saffron-` holder, passed it.

The gates judge a child's witnesses and the child's declared mutants. Nothing
runs a parent's recorded wrong versions against the parent's witness once a
child edits it. Each parent's `wrong-versions.json` sits in its batch folder.

## Done looks like

When a cell edits a test that a merged or stacked parent declared as a
witness, the host re-runs that parent's wrong versions against it. One that
survives blocks the attempt, and the result names the parent and the version.

## Record

- 2026-10-12: filed from the spec loop's run 36. A review commit on #856 put
  the seeding back, and the sweep probe then failed the test.
- 2026-11-14: the same hole opened from a review commit in the spec loop's
  run 70. A review commit on #1202 rewrote `SA-0389`'s clause, and the
  spec's wrong version 8 then passed the witness. Finish 88's end review
  found it, and `SA-0391` (#1204) pinned it.
- 2026-11-16: `SA-0401` (#1232) chooses each killed wrong version a parent
  recorded under a witness the child's diff edits. `SA-0402` (#1233) asks
  them in REVIEW, and a survivor blocks naming its parent. A review commit
  that edits a witness is still never asked them, which b-d9a027 carries.
