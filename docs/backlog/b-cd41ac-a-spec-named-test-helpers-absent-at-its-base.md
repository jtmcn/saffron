---
id: b-cd41ac
title: "A spec told its cell to reuse five test helpers that did not exist at its base, and two spec reviews passed it"
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Measured in the spec loop's run 30. `SA-0223`'s notes said "Reuse the
module's `_source`, `_task`, `_close`, `_migrated` and `_rows`". At its base,
`d553d510`, the test module defined only `_set`. The cell wrote all five, two
of them one-line wrappers. Both PR seats found it. The spec chain's two
review rounds did not.

## Done looks like

The spec reviewer checks that every symbol a spec names exists at its base,
and reports a missing one as a `build` blocker.

## Record

- 2026-10-07: filed from the spec loop's run 30 (#733).
