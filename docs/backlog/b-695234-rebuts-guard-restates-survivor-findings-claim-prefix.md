---
id: b-695234
title: REBUT's guard restates `survivor_finding`'s claim prefix by hand
status: open
tier: 3
filed: 2026-09-29
specs: [SA-0193]
prs: [596]
commits: []
cites: []
related: [b-cd5fd2]
---

## Problem

Found in the spec loop's run 22, 2026-09-29, on #596 (`SA-0193`).

`saffron/phases/rebut.py` builds
`f"{review.HOST_FILED}{criterion.witness} stayed green with "` by hand.
`saffron/phases/review.py:687` and `:693` write the same prefix. A change to
either sentence breaks REBUT's guard with no test red.

The in-cell conventions lens and the Standards seat both raised it. The spec
forbade edits to `review.py`, so the cell could not share it.

## Done looks like

One helper in `review.py` builds the prefix, and both modules call it. A guard
test reads a blocker filed through the wrong-version form.

## Record

- 2026-09-29: filed from the spec loop's run 22.
