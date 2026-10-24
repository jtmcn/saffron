---
id: b-7655f9
title: Stacking restates its graph walk, its edges map and its ancestry check
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-1572e7]
---

## Problem

Found in the spec loop's run 47, by the Standards seat on `SA-0312` (#957).

`_reachable` in `saffron/scheduler.py` repeats the walk `_depends_on_path` does. The
`depends_on` edges map is built three times, twice in the scheduler and once in
`saffron/task.py`. The ancestry check is also written three times: `cli._pushed_landed`,
`end_review._is_ancestor` and `task._is_ancestor`. The finish's end review raised the last
one again.

## Done looks like

One walk, one edges map per queue, and one ancestry helper in `saffron/repos/mirror.py`.

## Record

- 2026-10-24: filed from the spec loop's run 47.
