---
id: b-19dbc9
title: "`ParentGone`'s text calls the branch it names a parent, so the end review rewrites it"
status: open
tier: 3
filed: 2026-10-23
specs: []
prs: [937]
commits: []
cites: [§5.7]
related: []
---

## Problem

Found by the Standards seat on #937 (`SA-0302`), in the spec loop's run 46.

`saffron/phases/package.py:186-198` raises `ParentGone` with "parent branch
{branch} is gone" or "moved". The end review raises it for a layer's own
branch, not a parent. `saffron/end_review.py:271` therefore catches it and
writes its own message. `package.py` was forbidden to `SA-0302`.

## Done looks like

`ParentGone`'s text names the branch with no role, and each caller adds the
role it knows. `end_review.py` drops its rewrite.

## Record

- 2026-10-23: filed from the spec loop's run 46.
