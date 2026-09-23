---
id: b-e06dbc
title: Run 15's reviews kept eight small defects inside the specs' own files
status: open
tier: 3
filed: 2026-09-23
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-440f17]
---

## Problem

Found in the spec loop's run 15, 2026-09-23. The seats verified each one,
and the delegate kept it rather than widen a review commit.

- `tests/test_cli.py:1956`: `_pushed_branch` restates `_push_parent_branch`
  (`:434`). From #481.
- `saffron/agents/prompts/implement.md`: "wrong versions" is no
  `CONTEXT.md` term, where §4 names criterion and vacuity probes. The spec
  dictated it. From #480.
- `tests/test_context.py`: the new witness copies
  `_assembled_implement_prompt`'s assembly. From #480.
- `saffron/gates/core/size.py:154`: `>=` for `>` at the 10^9 bound survives,
  since no case sits on it. From #483.
- `saffron/gates/core/size.py`: `size_gate` computes `_token_counts` twice,
  once through `_changed_lines`, which `dead` needs called. From #483.
- `saffron/events.py:5`, `:719`, `:869`: "64 call sites" is stale, and now
  equals `len(FAMILIES)`. From #473.
- `saffron/cli.py:688`, `:757`: "this run's" names a scan, not one task's pin.
  From #481.
- `saffron/events.py:912`: the `PLAN: advisory estimate` row is paired only
  with a literal, never with the text `judge_estimate` builds. From #483.

## Done looks like

Each line above is fixed or closed with a reason.

## Record

- 2026-09-23: filed from the spec loop's run 15.
