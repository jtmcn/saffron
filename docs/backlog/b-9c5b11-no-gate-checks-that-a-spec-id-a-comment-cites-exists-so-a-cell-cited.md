---
id: b-9c5b11
title: "No gate checks that a spec id a comment cites exists, so a cell cited the nonexistent SA-0320"
status: open
tier: 3
filed: 2026-10-25
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

Found in the spec loop's run 48.

`SA-0315`'s cell wrote `SA-0320` into two docstrings and a test banner.
No spec with that id existed, and `saffron next-id` returned `SA-0317`.
The conventions lens caught it, so it cost a review fix and not a defect.

## Done looks like

A gate fails a new `SA-NNNN` in a diff that names no spec file in
`.saffron/specs/` or `.saffron/specs/done/`.

## Record

- 2026-10-25: filed from the spec loop's run 48.
