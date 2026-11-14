---
id: b-e11fb7
title: A second reset-time renderer sits beside `events.when`, whose docstring calls itself the one place
status: open
tier: 3
filed: 2026-11-13
closed:
specs: [SA-0388]
prs: []
commits: []
cites: [§5.1]
related: [104, b-45783e]
---

## Problem

Found reviewing #1189 (`SA-0385`) in the spec loop's run 68.

`batch._wait_out_rate_limit` now renders a provider's reset as
`%a %d %b %H:%M` (`saffron/batch.py:438`). It catches the same three
exceptions `events.when` catches (`saffron/events.py:753`). That docstring
still calls `when` the one place a reset time becomes something an operator
reads.

The two differ on purpose. The batch renders in the clock's zone with no
` local` suffix, and `when` renders in the host's zone with one. So the
batch could not import `when`, and `events.py` sat in the spec's
`forbidden`. Item 104 merged the last pair of renderers.

## Done looks like

One function renders a reset time, with the zone as a parameter. Both
callers use it, and its docstring holds.

## Record

- 2026-11-13: filed from the spec loop's run 68.
