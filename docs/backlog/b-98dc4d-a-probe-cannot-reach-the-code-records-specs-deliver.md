---
id: b-98dc4d
title: A vacuity probe can never be applied to the checking code a `records/` spec delivers
status: open
tier: 3
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§5.5, §5.5.1]
related: [117, b-461729]
---

## Problem

Found in the spec loop's run 9, 2026-09-19, on the first cell to run under
`SA-0109`. That cell was `SA-0110`, the next one in the same loop.

The adequacy lens named a probe on `tests/records/check.py:193`. The host
recorded it `unproven`: "tests/records/check.py is a declared test path". That
is criterion 4 of `SA-0109` working exactly as written.

But that file is where `records/`'s checking logic lives, by this repo's own
convention. The three `check_adr_*` functions the spec delivers are in it. So
the substance of the change is permanently out of the probe mechanism's reach,
and the lens's concern stayed a concern. Applied by hand, the probe survives:
the review's Spec seat confirmed the same hole, and it became a blocker.

The rule is right in general. A probe that deletes an assertion in a test file
always survives, which says nothing. It is wrong for a repo that puts checking
logic under `tests/`.

## Done looks like

Either the checking logic a `records/` spec delivers is not under a declared
test path, or a probe on it is answered rather than refused.

## Record

- 2026-09-19: filed from the spec loop's run 9 (#377).
