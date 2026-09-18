---
id: 166
title: The GateResult kind renders and nothing constructs it, so no event log names the gate that caused a repair turn
status: open
filed: 2026-09-17
specs: [SA-0102]
prs: []
commits: []
cites: [§4.1, §5.4]
related: [160]
---

## Problem

Found 2026-09-17, reading what a single execution can be seen through.

`saffron/events.py` defines ten kinds. Nine have a producer. `GateResult` at
`saffron/events.py:237-254` is the tenth. Its docstring calls it "the host's own
typed record of the fact a watch line already carried a hundred times over".

Nothing constructs one. The name appears in `saffron/events.py` at `:142`,
`:237`, `:241`, `:352`, `:367` and `:776`, and in `tests/test_events.py`. The
only mention elsewhere in `saffron/` is a comment at
`saffron/cell/session.py:612`. `describe` states the gap at
`saffron/events.py:777-781`: "No call site prints one alone today".

Measured across the 54 event logs under `~/.saffron/batches/v0/`: `Agent` 56004,
`PhaseStart` 475, `Preflight` 390, `Attempt` 154, `Teardown` 134, `Baseline` 64,
`Ceilings` 38, `Budget` 4, `Terminal` 2. `GateResult` appears zero times.

What the log carries instead is two summaries that lose the gate. One `Baseline`
per run joins every gate and status into a single line, by design. One `Attempt`
per suite carries a count, so the whole of GATE and REPAIR on `SA-0095` reads as
`gates: attempt 1, 1 new failures -> repair` and then `gates: attempt 2, 0 new
failures -> green`.

The ledger holds all of it. `record_gate_result` is called at
`saffron/cell/session.py:1402` for the baseline and at
`saffron/cell/session.py:1836` for each attempt. So a person holding the event
log cannot answer which gate sent a task back to REPAIR, and a person holding
the ledger can. Both records are written in one function, three lines apart.

The third value of `against` has no producer either. Production calls
`record_gate_result` at those two places only, so `rebuttal` waits on item 160,
which is the decision about what the Gate-only suite belongs to.

## Done looks like

Each gate result reaches the event log as its own event. It names its gate, its
status and what it was measured against, with the attempt's number where there is
one. An errored gate is emitted as errored and never as failed, and contributes
no failure count rather than a zero. The joined `Baseline` line and
the `Attempt` count both stay.

## Record

**Filed 2026-09-17**, from an inventory of what one execution can be seen
through. `SA-0102` carries it.
