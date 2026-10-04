---
id: b-2944c9
title: The header key `trailing accept rate` is spelled by hand at seven sites, where one helper would serve all of them
status: open
tier: 3
filed: 2026-10-03
specs: [SA-0198, SA-0199]
prs: [662, 670]
commits: []
cites: [§6]
related: [b-49a2f7, b-0703c8]
---

## Problem

Found by the Standards seats on #662 and #670 in the spec loop's run 27.

Every page writer builds `header={"trailing accept rate": trailing_accept_rate(ledger)}`
itself. After the stack, the key is spelled at `saffron/task.py` three times,
`saffron/cli.py`, `saffron/phases/package.py`, `saffron/report/stack.py` and
`saffron/replay.py`. A typo at one site drops the rate from that writer's pages
alone. Each spec forbade some of the files, so no cell could add one helper for
all seven. The operator chose to file it rather than add a partial helper.

## Done looks like

One helper in `saffron/report/index.py`, such as
`accept_rate_header(ledger) -> dict[str, str]`, builds the field. Every writer
imports it, and replay keeps its own placeholder or calls it too.

## Record

- 2026-10-03: filed from the spec loop's run 27.
