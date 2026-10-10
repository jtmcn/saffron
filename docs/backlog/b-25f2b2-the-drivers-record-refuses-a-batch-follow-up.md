---
id: b-25f2b2
title: "The loop driver's `record` refuses a stack batch's follow-up as \"not in the order\""
status: open
tier: 2
filed: 2026-10-09
specs: []
prs: [789]
commits: []
cites: []
related: [b-f10412, b-792ab2]
---

## Problem

Found in the spec loop's run 32.

Batch 20's end review drafted two follow-ups, `SA-0256` and `SA-0257`. The
batch ran each in a cell. `driver.py record SA-0256` failed with "SA-0256 is
not in the order", because `cmd_record` looks the spec up in the snapshot
alone (`.claude/skills/run-saffron-spec-loop/driver.py:1130-1135`). A
follow-up is minted during the batch and never enters the snapshot. So the
delegate read the follow-up's outcome from the ledger by hand.

## Done looks like

`record` reports a task the batch minted as a follow-up, read from the ledger
by spec id. A test drives `record` over a ledger holding a follow-up and no
order row for it.

## Record

- 2026-10-09: filed from the spec loop's run 32.
