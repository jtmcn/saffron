---
id: b-cd5fd2
title: A lens withdraws a probe blocker on a `preserves` criterion because its line is outside the diff
status: open
tier: 1
filed: 2026-09-29
closed:
specs: [SA-0193]
prs: []
commits: []
cites: [§5.5, §5.6]
related: [b-ab4b33, b-38d45f]
---

## Problem

Found in the spec loop's run 21, 2026-09-29, on #581 (`SA-0192`).

Criterion 3 was a `preserves` criterion: exactly one prompt carries the test
adequacy remit. The host's criterion probe added an adequacy question to
`review-correctness.md`, and the suite still passed. The host filed that as a
blocker. REBUT argued that the line sat outside the implementer's diff and
committed nothing. The adequacy lens withdrew.

A `preserves` criterion is a property of the whole file. A probe that breaks it
anywhere is a real hole, wherever the diff sits. Both seats found it real, and
review commit `d2ea4afe` fixed the witness.

REBUT ran from `main`, without `SA-0188`'s `contradicted` verdict (item
b-66d1c3). This is item b-ab4b33's shape on a different argument.

## Done looks like

The verdict session for a `preserves` blocker is told that the diff's extent
is no defence. Or the host refuses a withdrawal whose only argument is the
line's position. A test drives such a rebuttal and reads the blocker still
standing.

## Record

- 2026-09-29: filed from the spec loop's run 21.
- 2026-09-29: hit again one run later, on `SA-0194` (#598) in run 22.
  `SA-0193`'s fix sat unmerged, and REVIEW runs main's code (item b-66d1c3).
  The review commit fixed the witness.
