---
id: b-30cbb8
title: A task re-gating after REBUT prints nothing until the whole check ends, so a forty-minute run reads as stalled
status: open
tier: 3
filed: 2026-10-23
specs: []
prs: [944]
commits: []
cites: [§5.5]
related: [b-52e670]
---

## Problem

Found in the spec loop's run 46, on `SA-0305`.

`SA-0305`'s REBUT answered five blockers and moved its head at 17:38. The
host then re-ran the gates and every probe on the new head. The batch log
printed its next line about forty minutes later. The operator read the
silence as a stall. `SA-0303` and `SA-0306` took 11 and 16 minutes for one
and two rebuttals.

## Done looks like

Each gate result and each probe verdict after REBUT prints one line to the
batch log and one event to `events.jsonl`.

## Record

- 2026-10-23: filed from the spec loop's run 46.
