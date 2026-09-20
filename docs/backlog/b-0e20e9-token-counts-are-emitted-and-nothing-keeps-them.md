---
id: b-0e20e9
title: The runner emits token counts and nothing keeps them, so a task's token cost is unqueryable
status: open
tier: 3
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.1]
related: [94]
---

## Problem

Asked by the operator during the spec loop's run 9, 2026-09-19: does the loop
track tokens and time per cell?

Time and money are first-class. `attempts` carries `started_at`, `ended_at`,
`num_turns` and `cost_usd_est`, summed into `tasks.spent_usd_est`, and
`gate_results` carries `duration_ms`. Both spend ceilings are enforced from
them.

Tokens are not. `images/agent_runner.py:28-37` declares the usage keys and
attaches them at `:126` (the result's cumulative four) and `:133-137` (one
step's three, once per assistant `message_id`). They reach `events.jsonl` and
stop: no `input_tokens` anywhere under `saffron/`, and no token column in the
ledger.

The emission is newer than the machinery. Every task from `SA-0102` to
`SA-0108` has zero `input_tokens` lines in its event log. `SA-0109`, run the
same week, has them from its first turn. So the only record is a per-task file
whose contents changed between runs with nothing saying so.

## Done looks like

An attempt's token counts sit beside its `cost_usd_est`, so a task's token cost
is one query and a cache-read regression is visible across runs.

## Record

- 2026-09-19: filed from the spec loop's run 9, at the operator's request.
