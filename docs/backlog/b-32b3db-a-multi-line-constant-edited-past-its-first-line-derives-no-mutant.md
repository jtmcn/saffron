---
id: b-32b3db
title: A multi-line constant edited past its first string segment derives no constant mutant, so its read-back witness passes
status: open
tier: 2
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [b-5b1f8a]
---

## Problem

Found by the Spec seat and the in-cell critic on #908, in the spec loop's run 44.

`SA-0280` counts a constant pattern's match only when it overlaps an added
line. A constant pattern matches up to the constant's opening quote. The seat
edited the third line of a parenthesized multi-line constant, and no mutant
was derived. An edit to its second line derived one. The spec's own overlap
rule gives that result, so it is a gap in the spec and not in the build.

## Done looks like

An edit to any line of a constant's value derives its mutant. A test edits
the last segment of a multi-line constant and asserts the mutant is derived.

## Record

- 2026-10-19: filed from the spec loop's run 44.
