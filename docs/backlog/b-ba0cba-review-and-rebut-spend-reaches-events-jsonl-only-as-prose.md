---
id: b-ba0cba
title: REVIEW and REBUT spend reaches `events.jsonl` only as prose, so a follower's running total stalls from IMPLEMENT to the outcome
status: open
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§6]
related: [47, b-036cc5]
---

## Problem

Found by the `cell-watch` mod spike on 2026-10-07, while it followed `SA-0222`
in a live batch.

The last typed spend before the outcome is the IMPLEMENT `Attempt`, at $6.26.
Each REVIEW lens then states its own cost inside `PhaseStart.detail`, as text:
`correctness: 0 blocker, 0 concern, 0 note, drop rate 0% of 0, $0.81`. The
REBUT `Attempt` carries `spent_usd_est: null`, as item 47 decided for every GATE
and REBUT row. The next typed figure is the `TaskOutcome`, at $17.34 of $26.

So a reader of the log sees $6.26 for the whole of REVIEW and REBUT. In
`SA-0222`, the IMPLEMENT notes to the outcome ran 48 minutes and spent $11.08. A follower must either
show the stale figure or parse prose that `describe` owns. The mod shows the
stale figure.

## Done looks like

Every phase that spends writes a typed event that carries the task's running
spend. A follower that reads only typed fields can show spend against budget
at each lens and at REBUT. A test reads a REVIEW lens's spend back from the log
without parsing `detail`.

## Record

- 2026-10-07: filed from the `cell-watch` mod spike, measured on `SA-0222`.
