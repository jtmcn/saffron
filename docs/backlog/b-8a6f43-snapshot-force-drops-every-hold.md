---
id: b-8a6f43
title: '`snapshot --force` drops every hold, so a scoped loop re-holds its specs after each re-snapshot'
status: superseded
tier: 3
filed: 2026-10-02
closed: 2026-11-07
specs: []
prs: []
commits: ["e8d38ff5"]
cites: []
related: [b-c07b92, b-e8027b]
superseded_by: b-c07b92
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
- 2026-10-03: `SA-0170`, `SA-0183` and `SA-0152` left `specs`. They were the
  specs run 25 held, never a fix for this item. Run 26 held `SA-0152` once,
  and the `snapshot --force` after its spec merged released it, as intended.
- 2026-11-07: closed in grooming as superseded by b-c07b92. Both items ask for one way to scope a loop to the specs the operator names. A hold was never that tool. `cmd_hold` keeps `next` off a spec whose edit is an open pull request, and `snapshot` clears every hold on purpose since `d21982b1` (`driver.py:914`). Spec loop run 26 saw that release work as intended. b-c07b92 carries the scoping need, with three runs of evidence and its 2026-09-30 entry (`e8d38ff5`) placing the fix in the stack batch. A hold that must outlive a re-snapshot while its edit is open is b-e8027b. b-e8027b closed the same day as superseded by b-792ab2, since step 1b's review, the only source of a hold, is gone.
