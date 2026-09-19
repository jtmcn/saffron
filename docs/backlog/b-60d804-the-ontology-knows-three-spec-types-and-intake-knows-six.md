---
id: b-60d804
title: The ontology knows three spec types and intake knows six, so a merged `test` or `docs` task never enters the projection
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.1]
related: [53, b-946f03, b-952c34]
---

## Problem

Found in the spec loop's run 8, 2026-09-19, reviewing #355 (`SA-0107`).

`factory:SpecType` has three members, `feature`, `bug` and `refactor`
(`ontology/factory.ttl:163-164`). `saffron.intake.SpecType` has six, adding
`test`, `docs` and `chore` (`saffron/intake.py:18`). Intake accepts all six.

The projection takes its spec types from the shapes. A task whose spec type is
not among them is left out as `spec_unusable`
(`saffron/projection.py:163` on `origin/saffron/SA-0107`). Four specs in
`.saffron/specs/done/` are `test` or `docs`: `SA-0012`, `SA-0013`, `SA-0021`
and `SA-0079`. Two of them have a merged task in the ledger: `SA-0013` task 8
(PR #51) and `SA-0079` task 79 (PR #245).

`SA-0013` task 8 is the one overwrite in history that Appendix T's comparison
exists to find (item b-952c34). This type check alone is enough to leave it out.

Item 53 names closed sets that live only in the shapes. This one lives in both
places, and the two disagree.

## Done looks like

One list of spec types, held by a test that compares `factory:SpecType` with
`saffron.intake.SpecType`. The vocabulary edit goes through
`uv run python -m ontology.render`. A merged `test` or `docs` task reaches the
projection.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353). The cell restated the three types as `_SPEC_TYPES`, and the
  review commit `5bce64a` made the projection read them from the shapes. Both
  leave the same tasks out.
