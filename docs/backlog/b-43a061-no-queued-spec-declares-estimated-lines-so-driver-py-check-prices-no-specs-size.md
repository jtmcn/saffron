---
id: b-43a061
title: No queued spec declares `estimated_lines`, so `driver.py check` prices no spec's size
status: done
tier: 1
filed: 2026-09-27
closed: 2026-09-27
by_hand: true
specs: []
prs: []
commits: [acd2f1f6, 419bcd79, 78ab6179, 36cdfe25]
cites: []
related: [b-db95e1, b-efdf1f, 56]
---

## Problem

Found in the spec loop's run 19, 2026-09-27. Run 18 saw it first.

b-db95e1 gave a spec an `estimated_lines` field and `driver.py check` a rule
that prices it. At run 19's snapshot, none of the 22 queued specs declared
one. Each spec's size lives only in the prose of its notes. So `check` passed
`SA-0147` and `SA-0169`, and both cells ended `PLAN_REJECTED`. The two splits
cost about 5.5 hours of writer and review time.

A pricing of the sixteen remaining specs found landed size near 1.4 times each
spec's own prose estimate. The spread ran from 0.91 to 2.2 times.

## Done looks like

- `.claude/agents/spec-writer.md` asks for `estimated_lines` on every spec.
- `driver.py check` multiplies the estimate by a ratio measured from landed
  history, and reports the ratio it used.
- `check` names each spec that declares no estimate.

## Record

- 2026-09-27: filed from the spec loop's run 19.
- 2026-09-27: fixed by hand. Every queued spec declares a raw `estimated_lines`, and `check` prices it at the measured overrun.
