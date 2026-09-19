---
id: b-6f7f8d
title: The spec loop has no step after its stack merges, so main went red on a record the loop had filed
status: open
tier: 2
filed: 2026-09-19
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-4589be, b-65e7e2]
---

## Problem

Found after the spec loop's run 8 stack merged, 2026-09-19.

`SKILL.md` step 5 runs before the operator merges the stack. It files items
with the loop's pull requests in `awaiting:`, and it retires a spec only "if
the spec merged". Nothing in the skill runs after the merge, so two things
went wrong.

- `tests/records` fails on every branch once an `awaiting` pull request
  merges. Run 8's stack merged at 20:12, and `main` stayed red on
  b-d6bff7 until #370. #369's CI failed twice on that alone.
- The five specs sat at the top of `.saffron/specs/` until #372 retired them.

The retirement PR (#372) then hit two traps.

- A spec moved to `done/` but not yet committed fails
  `tests/test_queued_specs.py::test_a_committed_spec_is_read_at_a_commit_not_the_working_tree`.
  `_authored_at` returns `None` for an uncommitted change, so `make check`
  fails until the move is committed. The failure names the test, not the
  cause.
- Retiring a spec forces every item that lists it in `specs:` out of `open`,
  not only its origin item. Item 160 listed `SA-0102`, which did part of it,
  and had to become `partial`.

## Done looks like

`SKILL.md` has a step 6, run when the operator says the stack merged:

1. Pull `main`.
2. For each merged spec, grep `docs/backlog` for every item whose `specs:`
   or `awaiting:` names it or its pull request, not only its origin item.
   Close each item, or record what is left and move the number to `prs`.
3. `git mv` each spec to `done/`, re-measure the queue smoke test, and
   commit before running `make check`.

A `driver.py merged` command could list those items, and b-4589be is the
place for it. b-65e7e2's loop branch would collapse this step into the
stack's own merge.

## Record

- 2026-09-19: filed by hand after run 8, from #370 and #372.
