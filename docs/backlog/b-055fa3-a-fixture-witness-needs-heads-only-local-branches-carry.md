---
id: b-055fa3
title: A fixture witness needs heads that only local branches carry, so pruning one fails it at base and head
status: open
tier: 2
filed: 2026-09-22
specs: [SA-0121]
prs: [435]
commits: []
cites: []
related: [89]
---

## Problem

Found in the spec loop's run 13, 2026-09-22.

`SA-0121`'s witness,
`tests/test_corpus.py::test_every_shipped_fixture_reproduces_its_own_declared_range`,
needs each fixture's head commit. Three of those heads sit only on local
branches: `joel/batch-documents`, `joel/sa-0054-review-fixes` and
`backup/spec-review-pre-delta`. None is on GitHub.

The mirror copies every local ref with `fetch --prune origin +refs/*:refs/*`
(`saffron/repos/mirror.py:63`). So the cell sees them today. Deleting any of the
three branches fails the witness at base and at head.

## Done looks like

Each fixture's head is reachable from a ref the repo keeps on purpose, and a
test names the ref each fixture needs.

## Record

- 2026-09-22: filed from the spec loop's run 13.
