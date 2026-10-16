---
id: b-d31930
title: A queued spec cites lines that moved since it was written, and nothing says so before its batch pays to find out
status: open
tier: 2
filed: 2026-10-15
specs: [SA-0273, SA-0294, SA-0295]
prs: [880]
commits: []
cites: [§3.2]
related: [b-b24cf7]
---

## Problem

Found in the spec loop's run 40.

`SA-0273` was written against `bc879e2c`. By the time it ran, nine landed specs
had moved `saffron/cell/session.py` and `saffron/cli.py` by hundreds of lines.
The batch's spec review found 15 citations pointing at the wrong code and
blocked the spec. That cost $2.32 and a hand-made PR, #880.

`driver.py cite` finds this in seconds. Nothing runs it on a queued spec
before the batch does. Run 39's handoff named the refresh as optional.

## Done looks like

`driver.py check`, or the batch's own preflight, runs the citation check over
each spec in the order. A citation that no longer resolves blocks before any
money is spent.

## Record

- 2026-10-15: filed from the spec loop's run 40.
