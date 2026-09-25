---
id: b-acee54
title: A stack batch's escalations are printed lines, not record facts
status: open
tier: 3
filed: 2026-09-25
closed:
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-792ab2]
---

## Problem

In the design, each escalation is a record fact. It is also a line near
the top of the queue page (design record §4).
No spec in `b-792ab2`'s chain adds that fact kind. `SA-0167` prints each
escalation as a `finish: escalate:` line, and `SA-0152`'s stack view shows
none.

## Done looks like

An escalation fact kind exists, the finish and the spec review record one, and the queue page lists them.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
