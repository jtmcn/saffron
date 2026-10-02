---
id: b-8a6f43
title: '`snapshot --force` drops every hold, so a scoped loop re-holds its specs after each re-snapshot'
status: open
tier: 3
filed: 2026-10-02
specs: [SA-0170, SA-0183, SA-0152]
prs: []
commits: []
cites: []
related: [b-c07b92]
---

## Problem

Found in the spec loop's run 25, 2026-10-02.

Run 25's operator scoped the loop to `SA-0177` and `SA-0167`, so the
delegate held the other three specs. Each spec PR that merged made the order
stale, and `snapshot --force` rebuilt it with no hold kept. The delegate
re-held the specs four times in one run.

## Done looks like

`snapshot --force` keeps every hold whose spec is still in the order, as
it keeps recorded outcomes. Or the operator's scope is an argument the
order records once.

## Record

- 2026-10-02: filed from the spec loop's run 25.
