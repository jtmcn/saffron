---
id: b-d9a027
title: A review commit that edits a witness is never asked the wrong versions that witness killed
status: done
closed: 2026-11-17
tier: 2
filed: 2026-11-16
specs: [SA-0403, SA-0404, SA-0405]
prs: [1236, 1237, 1238, 1239, 1240, 1241]
commits: []
cites: [§5.4, §5.5]
related: [b-9efbe2, b-60317d]
---

## Problem

Left by b-9efbe2, closed in the spec loop's run 75.

`SA-0401` and `SA-0402` ask a parent's killed wrong versions in REVIEW,
when a child's cell edits the parent's witness. A review commit runs in no
cell, so nothing asks them of it. In run 70 a review commit on #1202 rewrote
`SA-0389`'s clause. The spec's own wrong version 8 then passed the witness.
Finish 88's end review found it, and `SA-0391` (#1204) pinned it.

`saffron regate` already judges a pull request's head with the task's own
gates. It reads no recorded wrong version.

A second gap sits beside it. A lens can withdraw a parent survivor's blocker
in REBUT. `_guarded_blockers` guards only a `preserves` criterion's survivor.

## Done looks like

`saffron regate` asks the task's own killed wrong versions, and each parent's,
of every witness the head's commits edit. A survivor fails the re-gate and
names its spec and version. REBUT cannot withdraw a parent survivor's blocker.

## Record

- 2026-11-16: filed from the spec loop's run 75, from the out-of-scope
  sections of `SA-0401` and `SA-0402`.
- 2026-11-17: closed by the spec loop's run 76. `SA-0403` (#1239) chooses
  the versions, `SA-0404` (#1240) asks them in `saffron regate`, and
  `SA-0405` (#1241) refuses a withdrawn parent survivor in REBUT. The
  review left b-988eb9 and b-c1259f.
