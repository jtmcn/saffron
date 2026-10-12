---
id: b-6677b6
title: "No record append emits an event, though the record design binds that rule at the wiring"
status: open
tier: 1
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: []
related: [170]
---

## Problem

Found by the spec review of `SA-0278`, the spec that wires the record in.

The record design's §8 rule reads: every record append also emits an event,
and no event implies an append. It binds once a production caller constructs a
`Ledger` with a record
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:363-367`).
`SA-0278` is that caller and leaves the rule unbuilt. `Ledger._append` takes no
event sink and emits nothing (`saffron/ledger.py:590-594`). The deferral was the
operator's call on `SA-0278`'s pull request.

Until it is built, `events.jsonl` can omit a fact the record holds, and nothing
reports the gap.

## Done looks like

Each append a production ledger makes emits one event on the task's stream. A
test drives a write method of each fact kind the ledger appends and finds its
event.

## Record

- 2026-10-12: filed from `SA-0278`'s spec review, round 1.
