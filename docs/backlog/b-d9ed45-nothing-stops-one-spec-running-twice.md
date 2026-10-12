---
id: b-d9ed45
title: Nothing stops one spec running in two cells at once, and the second removes the first one's container and volumes
status: open
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§5.1]
related: [b-ca3bc6, b-a714d2]
---

## Problem

Found 2026-10-11 while listing what blocks two cells on one host.

A cell's container and volumes are named from the spec id alone:
`saffron-cell-<SPEC>`, `saffron-wt-<SPEC>` and `saffron-st-<SPEC>`
(`saffron/cell/session.py:1899-1901`). The critic and gate cells follow the
same rule. Each create is preceded by a remove of the same name, so a run
killed by SIGKILL cannot block the next one.

That pre-clean cannot tell a leftover from a live cell. Two `saffron cell`
runs of one spec, or a batch beside a by-hand cell, end with the second run
removing the first run's container mid-task. How the first run then ends is
not measured.

The batch directory is keyed by spec too (`saffron/task.py`), so both runs
append to one `events.jsonl`.

## Done looks like

A second run of a spec that is already running is refused before any
container is touched, naming the run that holds it. A leftover from a dead
run is still cleaned up. A test holds the claim for one spec and asserts a
second start refuses.

## Record

- 2026-10-11: filed from the parallel-cells survey, beside b-ca3bc6.
