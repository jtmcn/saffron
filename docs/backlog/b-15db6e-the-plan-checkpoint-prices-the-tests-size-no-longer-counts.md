---
id: b-15db6e
title: The plan checkpoint prices the tests that `size` no longer counts
status: open
tier: 2
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§5.3, §5.4]
related: [40]
---

## Problem

Found by the spec review of `SA-0274`.

`SA-0274` makes `size` leave the repo's declared test paths out of its
count. The plan checkpoint still prices the whole diff. `judge_estimate`
multiplies the plan's `estimated_lines` by four and compares it with the
ceiling (`saffron/agents/artifacts.py:315`). The plan prompt asks for lines
across the whole diff (`saffron/agents/prompts/implement.md:26-27`).

So at `elevated` a plan can be refused when `size` would pass its diff. The
tests a plan names push its estimate over the ceiling, and the gate never
counts them. The docstring of
`test_the_plan_checkpoint_rejects_an_estimate_exactly_where_size_would_block`
says the checkpoint rejects "exactly where the `size` gate would block the
real diff, never more, never less" (`tests/test_session.py:425-427`). That
goes false for a repo declaring `test_paths`, and the test stays green.

## Done looks like

The plan's estimate and the `size` gate count the same files. Either the
prompt asks for lines outside the declared test paths, or the plan carries
its test lines apart and the checkpoint leaves them out.

## Record

- 2026-10-11: filed from the spec review of `SA-0274`, which keeps
  `saffron/agents/**` forbidden.
