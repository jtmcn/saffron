---
id: b-7251b5
title: A malformed wrong-version answer leaves every declared version unproven, and REVIEW still passes
status: open
tier: 1
filed: 2026-10-03
specs: [SA-0183, SA-0202]
prs: [648]
commits: []
cites: [§4.3, §5.5]
related: [b-12e717, b-2750d5]
---

## Problem

Found in the spec loop's run 26, on `SA-0183`'s cell.

REVIEW's wrong-version turn answered with output that was not valid JSON
("Expecting ',' delimiter"). `run_wrong_versions` caught the parse error and
filed every declared version with no edit (`saffron/phases/review.py`,
`_unresolved_wrong_versions`). Each one then read `unproven`. The cell logged
"5 declared, 0 expressed" and reached `READY_FOR_REVIEW` with no blocker.

A lens turn that is not the schema gets one re-prompt in the same session
(`run_lens`). The wrong-version turn gets none, though it fails the same way.
So one malformed answer turns a measured check into no check, and nothing
says so above a line of the log.

#648's Spec seat then ran all five by hand, and the witness killed each one.
The check that REVIEW owes ran only because the delegate read the log.

## Done looks like

A wrong-version answer that is not the schema is re-prompted once in its own
session, as a lens answer is. A criterion whose versions still read
`unproven` after that is an `error` the cell's REVIEW line names, never a
silent pass.

## Record

- 2026-10-03: filed from the spec loop's run 26.
