---
id: b-ce832b
title: Three texts still list the stale push states without REVIEW_INCOMPLETE
status: open
tier: 3
filed: 2026-11-18
closed:
specs: []
prs: []
commits: []
cites: []
related: [b-e9dd4c]
---

## Problem

Found in the spec loop's run 79, on #1258 (`SA-0408`). That spec gave
`REVIEW_INCOMPLETE` the refusals `REBUTTAL_UNJUDGED` had, through
`STALE_PUSH_STATES`. Three texts still name the older state alone.

- `push_unpackaged_work`'s docstring (`saffron/phases/package.py:1150`)
  lists the other-row states its guard refuses, without
  `REVIEW_INCOMPLETE`. The spec's Out of scope left it, because the
  docstring runs past ten lines and any edit there is a new `prose` hit.
- The comment above `_ADOPTABLE_STATES` (`saffron/cli.py:3168`) says the
  set is spelled out since `REBUTTAL_UNJUDGED` joined `MERGE_ONLY_STATES`.
  `REVIEW_INCOMPLETE` joined it too. `cli.py` was forbidden to the spec.
- `saffron/record/migrate.py:4-6` names only `REBUTTAL_UNJUDGED` as a
  pushed row that reads as refused after a migration.

## Done looks like

Each text names the set or both states. `push_unpackaged_work`'s
docstring is cut to ten lines or fewer in the same change, so the edit
lowers the `prose` count rather than raising it.
