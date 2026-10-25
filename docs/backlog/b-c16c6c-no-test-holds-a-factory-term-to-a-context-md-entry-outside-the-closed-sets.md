---
id: b-c16c6c
title: "No test holds a `factory:` term to a `CONTEXT.md` entry outside the closed sets, and the comments that restate entries drift"
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§4.6]
related: [b-2227b0]
---

## Problem

`test_vocabulary_agrees_with_context.py` checks 11 closed sets and nothing else.
Measured at `2e1efa2b`:

- Five labelled classes have no entry: acceptance criterion, diff, plan, pull
  request and scope proposal.
- Seven classes with an entry carry no label, among them `Severity`,
  `RiskTier` and `FactKind`.
- `factory.ttl` holds 22 `rdfs:comment` values, and several restate an entry.
  The comment on `TerminalState` says `CONTEXT.md` §6 lists six terminal
  states, and the entry lists 14. ADR 4 fixed the same drift in the lens
  comment.

## Done looks like

- A test holds every `factory:` class and closed-set member to one
  `CONTEXT.md` entry, or to a stated exclusion. The five missing entries are
  written.
- A definitional `rdfs:comment` is deleted, and its content lives in the entry.
  A comment that records a modelling choice becomes a Turtle comment.

## Record

- 2026-10-24: filed from the three reviews of the parked ADR 12 (b-2227b0),
  which named this as the cheaper path that closes the measured gap.
