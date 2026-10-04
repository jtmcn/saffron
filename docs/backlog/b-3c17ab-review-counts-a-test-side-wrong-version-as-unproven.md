---
id: b-3c17ab
title: REVIEW counts a test-side wrong version as unproven, though no source edit can express one
status: open
tier: 3
filed: 2026-10-03
specs: [SA-0198]
prs: [662]
commits: []
cites: [§5.5]
related: [b-7251b5, b-ef8543]
---

## Problem

Found in the spec loop's run 27.

`SA-0198`'s REVIEW printed `wrong versions: 30 declared, 28 expressed`. The two
it left `unproven` were mistakes in the witness itself: a table compared as a
subset, and a table that agrees with a wrong set. REVIEW expresses a wrong
version as an edit to the source, so it cannot express either. Its reason says
so, and the line still reads as a gap.

The delegate closed both by reading `tests/test_accept_rate.py`. Run 26 learned
to read the `declared, expressed` line in every log and run the gap by hand. A
gap that is test-side by kind makes that line cry wolf.

## Done looks like

A spec writer lists a test-side wrong version apart from the source edits, and
REVIEW checks it against the witness's assertions. Or REVIEW's line counts
test-side versions apart from the unproven ones.

## Record

- 2026-10-03: filed from the spec loop's run 27.
