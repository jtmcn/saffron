---
id: b-14ccc7
title: A live-cell test fails when two worktrees run `make check` at once
status: open
tier: 3
filed: 2026-10-03
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 26.

`tests/test_spec_loop_driver.py::test_a_live_saffron_cell_is_found_by_its_spec_id`
failed inside `make check` in two spec-writer worktrees.
`_cell_running("SA-9998")` returned true. Each run passed alone. Both
worktrees ran `make check` at the same moment, so the test read the other
suite's process as a live cell. That cause is inferred, not measured.

## Done looks like

The test finds only a process it started itself, so a parallel suite on
the same host cannot pass or fail it.

## Record

- 2026-10-03: filed from the spec loop's run 26.
