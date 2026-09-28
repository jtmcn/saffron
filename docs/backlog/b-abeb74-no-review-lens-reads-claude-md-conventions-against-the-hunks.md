---
id: b-abeb74
title: No REVIEW lens reads CLAUDE.md's conventions against the hunks, and the Standards seat finds them on every PR
status: open
tier: 1
filed: 2026-09-28
closed:
specs: []
prs: []
commits: []
cites: [§5.5]
related: [79, b-17d0d5, b-7e69d0]
---

## Problem

Found in the spec loop's run 20, 2026-09-28. The operator ranked it third.

REVIEW runs three lenses: correctness, contract and adequacy
(`saffron/phases/review.py:39-42`). None judges a hunk against `CLAUDE.md`'s
conventions. The Standards seat found such defects on every pull request of the
run.

- A comment that contradicts its code: #565's timeout comment, #566's "lone
  witness concern" docstring three times.
- A restated constant: #559's `record_key`, #560's `3600`.
- A citation to a section that does not say it: #562's `§4.2.1` references.

## Done looks like

A fourth lens reads each hunk against `CLAUDE.md` and the `Conventions` it
states. It is measured on run 20's Standards findings before and after.

## Record

- 2026-09-28: filed from the spec loop's run 20.
