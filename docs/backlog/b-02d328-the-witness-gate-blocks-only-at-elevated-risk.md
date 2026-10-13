---
id: b-02d328
title: "The `witness` gate blocks only at `elevated` risk, so a spec's own declared mutant survives and its task packages"
status: open
tier: 1
filed: 2026-10-12
specs: [SA-0288]
prs: []
commits: []
cites: [§5.4]
related: [b-7e69d0]
---

## Problem

Measured in the spec loop's run 35, on #846 (`SA-0267`).

`SA-0267` declared a mutant for criterion 1. It drops `READY_FOR_REVIEW`
from `DEPENDENCY_WAITING_STATES`. The `witness` gate applied it twice, on
attempt 1 and on the rebuttal. Each time it reported `fail` with "1 of 2
witness(es) survived their own mutant".

`ontology/factory.ttl:93` makes `witness` blocking only when the task is
`elevated`. `SA-0267` touched no `elevate_on` path, so it stayed `standard`.
The failure blocked nothing. REBUT never saw it as a blocker, and the task
went `READY_FOR_REVIEW`.

The witness looped over the set the mutant shrinks, imported from the
module under test. The Spec seat found it by running the same mutant by
hand.

## Done looks like

- A declared mutant that survives its witness is a blocker at every risk
  tier, or REBUT receives it as a finding to answer.
- A test drives a `standard` task whose witness survives its mutant and
  asserts the task does not package `READY_FOR_REVIEW` unanswered.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#846).
- 2026-10-12: `SA-0288` queued. The operator chose the first arm, so a
  survivor blocks at every tier. The design record, the vocabulary, the
  shapes and ADR 3 changed by hand in the spec's own commit.
