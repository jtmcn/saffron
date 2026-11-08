---
id: b-a7e315
title: '`driver.py status` has no one-line form, so the operator''s status line parses its table'
status: done
tier: 3
filed: 2026-10-02
closed: 2026-11-08
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 25, 2026-10-02.

The operator asked for the loop's queue in the session's status line.
The delegate wrote `~/.claude/saffron-loop-line.py`, which parses
`driver.py status`'s table and reads the running cell's phase from
`events.jsonl`. A change to the table's columns breaks it silently.

## Done looks like

`driver.py status --line` prints the reviewable count, each spec's state
and pull request, the running cell's phase and the held count, on one line.

## Record

- 2026-10-02: filed from the spec loop's run 25.
- 2026-11-07: marked by hand in grooming. The work is in the spec loop's driver under
  `.claude/`, and `SA-0279` refuses any spec that touches that path.
- 2026-11-08: done by hand.
