---
id: b-be3adc
title: DESIGN.md §5.5 still lists the correctness lens without the failure path SA-0286 gave it
status: open
tier: 3
filed: 2026-10-13
specs: [SA-0286]
prs: [867]
commits: []
cites: [§5.5, §5.5.1]
related: [79]
---

## Problem

Found by the Standards seat on #867 in the spec loop's run 37.

`SA-0286` gave the correctness lens what a failure leaves behind. `DESIGN.md`
§5.5 still lists lens #1 as timezones, chunk boundaries, null and gap
propagation, unit errors and market-hours assumptions. A truncating write now
sits in both the correctness and the contract remits. §5.5.1 records the
blast-radius overlap and not this one. The spec forbade `DESIGN.md`.

## Done looks like

§5.5's lens #1 names the failure path, and §5.5.1 records the overlap on a
truncating write beside the one it already keeps.

## Record

- 2026-10-13: filed from the spec loop's run 37.
