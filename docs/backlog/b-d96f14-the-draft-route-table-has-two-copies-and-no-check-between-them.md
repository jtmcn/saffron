---
id: b-d96f14
title: "`tests/test_draft.py` and `saffron/draft.py` hold two copies of the route-to-state table, and nothing compares them"
status: open
tier: 3
filed: 2026-10-09
specs: []
prs: [781, 789]
commits: []
cites: []
related: [b-8a0c9a]
---

## Problem

Found by batch 20's end review in the spec loop's run 32.

`saffron/draft.py:35` defines `_ROUTE_STATE`, and `tests/test_draft.py:229`
restates it, with the same keys, values and comment. A change to one passes
the suite when the other is stale. The follow-up `SA-0256` (#789) made the
test import the production table. Both seats showed that drops coverage: a
changed route entry then passes the whole suite. It also undid 7dbf5624 on
#781, which moved the test off production helpers on purpose. The operator
closed #789 and asked for a check between the copies instead.

## Done looks like

A test asserts the two tables agree, entry by entry, and the test's own copy
stays the oracle. A changed entry in `saffron/draft.py` fails it.

## Record

- 2026-10-09: filed from the spec loop's run 32.
