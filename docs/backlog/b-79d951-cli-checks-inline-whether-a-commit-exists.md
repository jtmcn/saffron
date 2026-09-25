---
id: b-79d951
title: "`saffron/cli.py` checks inline whether a commit exists, which `mirror.has_commit` now does"
status: open
tier: 3
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§4.2]
related: [b-602d00]
---

## Problem

Found in the review of #514 (`SA-0136`), 2026-09-24.

`_pushed_landed` runs `rev-parse --verify --quiet` to learn whether a commit
exists (`saffron/cli.py:347-354`). `SA-0136` added `has_commit` to
`saffron/repos/mirror.py`, and `run_task` calls it. The two spell the same
question twice.

## Done looks like

`_pushed_landed` calls `mirror.has_commit`, and its existing tests stay
green.

## Record

- 2026-09-25: filed from the spec loop's run 16.
