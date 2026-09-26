---
id: b-2d9ae9
title: A review test's docstring says only adequacy files an edit, and SA-0146's Spec lens files one too
status: open
tier: 3
filed: 2026-09-23
closed:
specs: []
prs: []
commits: []
cites: [§5.5]
related: [b-792ab2]
---

## Problem

Found 2026-09-23 in `SA-0146`'s round-2 spec review. The docstring at
`tests/test_review.py:475` says only adequacy's defect class is an edit that
keeps the suite green. `SA-0146` gives the Spec end-review
lens a report model with an optional probe, so that sentence goes false.
`SA-0146` forbids `tests/test_review.py`, so its cell cannot fix it.

## Done looks like

The docstring names both lenses that file an edit, once `SA-0146` merges. No assertion changes.

## Record

- 2026-09-23: filed from `SA-0146`'s round-2 review.
