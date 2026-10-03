---
id: b-23a149
title: The wall bound cut an IMPLEMENT session during its own full-suite run, which GATE repeats
status: open
tier: 2
filed: 2026-10-03
specs: [SA-0170]
prs: [647]
commits: []
cites: [§4.3, §5.3]
related: [b-36b551, b-d4e015, b-209696]
---

## Problem

Found in the spec loop's run 26, on `SA-0170`'s cell.

The IMPLEMENT session's wall is 15 seconds a turn, so 1950 seconds at
`max_turns` 130 (`saffron/cell/session.py`, `WALL_SECONDS_PER_TURN`). The
agent had three commits and every core gate green by its own run. Its last
action was `timeout 300 uv run pytest -q`, the whole suite, and the wall
cut the session there.

The host runs that suite next at GATE, outside the session. The agent spent its
last minutes of wall on a check the host repeats. Attempt 1 then failed
`committed` and needed a repair turn. The ledger read $1.24 for the cut
session, a floor (b-209696).

Run 25's idle kill (b-d4e015) is fixed, so a long session now reaches the
wall instead.

## Done looks like

An agent knows the host runs the full suite at GATE, and runs only the
witnesses it touched. Or the wall leaves room for one suite run the agent
asks for. Either way, a session is not cut in a check GATE repeats.

## Record

- 2026-10-03: filed from the spec loop's run 26.
