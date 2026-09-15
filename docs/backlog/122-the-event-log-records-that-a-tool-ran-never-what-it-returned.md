---
id: 122
title: The event log records that a tool ran, never what it returned
status: open
tier: 3
filed: 2026-09-14
specs: [SA-0087]
prs: []
commits: []
cites: []
related: []
---

## Problem

**Tier 3.** Found diagnosing `SA-0087`'s turn-ceiling loss, 2026-09-14. An agent
`tool_result` event carries `is_error` and nothing else. The size check the
agent ran just before it was cut off therefore left no record of the count it
saw. The log can say what the agent tried and not what it learned, and the
second is what a post-mortem of a lost cell needs first. Bounded output is the
obvious objection, and the log already bounds agent text (`bounded`,
`original_chars`).

## Done looks like

a clipped tail of each tool result in its event, under the
same bound agent text has.
