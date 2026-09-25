---
id: b-e471bd
title: The cell's agent refuses every write under `.claude/` in dontAsk mode, so a spec that touches `.claude/**` depends on the agent routing around a denial
status: open
tier: 1
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§5.3, §4.2]
related: []
---

## Problem

Found in the spec loop's run 16, 2026-09-24, on `SA-0129`.

`SA-0129` touches `.claude/skills/run-saffron-spec-loop/driver.py`. Its cell
ended `NOT_IMPLEMENTED` at $1.77. The agent CLI denied every Edit and Write
under `.claude/skills/run-saffron-spec-loop/`, citing dontAsk mode, and the
agent stopped.

The protection is not new. `SA-0116`'s cell hit the same denial on
`driver.py` on 2026-09-21. That agent routed around it with `python3` from
Bash and finished. So the outcome turns on what the agent chooses to do.

A host A/B on SDK 0.2.142 and CLI 2.1.237 used `implement.agent_options`
(`saffron/phases/implement.py:109-118`). The CLI denied an Edit under
`.claude/` with the system prompt as a string and as a file. It allowed the
same Edit under `pkg/`. `permission_mode="dontAsk"` and an empty
`setting_sources` leave no rule that grants the path.

## Done looks like

One of two, decided before a spec lands:

- The host grants writes under the spec's `.claude/**` touches explicitly,
  and a cell test edits a file there with Edit.
- Intake refuses a spec whose `touches` include `.claude/**`, with a reason
  and no model call.

## Record

- 2026-09-25: filed from the spec loop's run 16. `SA-0129` was taken by hand
  as #502.
