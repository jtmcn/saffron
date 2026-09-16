---
id: 134
title: session.py carries three copies of the teardown closure and two of the leak-report loop
status: open
tier: 3
filed: 2026-09-15
by_hand: true
specs: [SA-0087]
prs: [274]
commits: []
cites: [§5.1]
related: [118]
---

## Problem

**Tier 3.** Found reviewing `SA-0087` (PR #274).

`critic_cell`'s `finally` restates `cell_down`'s leak-report loop verbatim —
message string and the `[:160]` truncation included — and `_critic_teardown` is a
third copy of the same `emit(Teardown(...))` closure, alongside the two already
in `_drive_cell`, which differ from each other only in their defaults.

`cell_down`'s own docstring records what paraphrasing that block cost once
before: *"The harness paraphrased this block once and its first run died on
'network saffron-cells already exists'."* The copies are currently identical, so
nothing is wrong today; the item is that the next edit has three places to reach
and a measured history of one of them being missed.

`_phase_start` in the same function shows where a closure shared across
`_drive_cell` belongs.

## Done looks like

one `_report_leaks(removed, created, note)` called from both teardowns, and one
`_teardown` closure hoisted above the `try` and passed as `note`.
