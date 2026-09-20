---
id: b-27b9db
title: A kind's required headings are read only when it also declares allowed ones
status: open
tier: 3
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: []
related: [b-9ff0fd]
---

## Problem

Found by the spec loop's Spec seat reviewing #377, 2026-09-19.

`Kind` gained `required`, the subset of `sections` that must appear
(`records/kinds.py`), and `records/load.py` consults it inside `if
kind.sections:`. A kind that declares `required` and no `sections` therefore
checks nothing, silently.

Harmless today: the backlog and the ADR both declare each. The coupling is
invisible at the dataclass, which is where a third kind will be written.

## Done looks like

A `Kind` whose `required` is not a subset of its `sections` is refused where
the kind is defined. So is one that declares `required` with no `sections`.
Neither is ignored where a record is loaded.

## Record

- 2026-09-19: filed from the spec loop's run 9 (#377).
