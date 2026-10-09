---
id: b-3d2aa1
title: commit_finish drops spec parse failures silently, and an OSError from it exits 2
status: superseded
tier: 2
filed: 2026-10-01
closed: 2026-10-08
specs: [SA-0151]
prs: [628]
commits: []
cites: []
related: [b-792ab2]
superseded_by: b-a63235
---

## Problem

Found by #628's Spec seat, 2026-10-01.

- `saffron/finish.py` discards `discover_specs`' failures. A layer whose spec
  does not parse at the finishing tree stays unretired, and nothing says so.
- `_stack_finish` catches only `GitError` and `ValueError`. An `OSError` from
  a write or rename, or a sqlite error, reaches `main`, which exits 2. The
  operator kept the catch narrow and the docstring now says so.

## Done looks like

`commit_finish` emits one line per parse failure on a layer's path. The
operator decides whether `_stack_finish` keeps the exit code on any raise,
as `_stack_follow_ups` does.

## Record

- 2026-10-01: filed from #628's review seats.
- 2026-10-08: superseded by b-a63235. The finish no longer parses the spec
  directory, so no layer stays unretired. The operator kept `_stack_finish`'s
  catch narrow, which settles the second half.
