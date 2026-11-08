---
id: b-937778
title: "The loop driver's `history` takes peak turns over every phase's attempts and compares them to `max_turns`"
status: done
tier: 3
filed: 2026-10-05
closed: 2026-11-08
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-60ff2e]
---

## Problem

Found in stage 2 of the delegate-loop plan.

`_past_cells` in `.claude/skills/run-saffron-spec-loop/driver.py` takes the
peak attempt over every attempt of a task (`driver.py:1952`). It stores that
attempt's `num_turns` as `peak_turns` (`driver.py:1967`). `_ceilings_line`
then compares the highest `peak_turns` to the target's `max_turns`
(`driver.py:2016`). A spec review or spec-writing attempt counts, though
`max_turns` never bounds it.

b-60ff2e fixed the same defect on the stack page. `history` still carries it.

## Done looks like

`history`'s peak reads only the attempts `max_turns` bounds, or the line names
each phase beside its peak.

## Record

- 2026-10-05: filed from stage 2 of the delegate-loop plan (the first live stack batches, batches 13 and 14).
- 2026-11-07: marked by hand in grooming. The work is in the spec loop's driver under
  `.claude/`, and `SA-0279` refuses any spec that touches that path.
- 2026-11-08: done by hand.
