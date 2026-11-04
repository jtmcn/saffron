---
id: b-8c6696
title: A spec that adds a plan field misses the fixtures that pin the plan's sha
status: open
tier: 3
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: [§5.3]
related: []
---

## Problem

Found by the by-hand build of `SA-0333` in the spec loop's run 53.

`SA-0333` added `estimated_test_lines` to the plan. The plan's sha is pinned
in `tests/fixtures/watch-golden.txt` and `tests/test_events.py`, and neither
sat in the spec's `touches`. A cell fails `scope` on such a file.
`create-saffron-spec`'s pre-flight check 6 asks what the change breaks, and
no check names a pinned sha.

## Done looks like

The spec pre-flight names each test or fixture that pins a hash of a
structure the spec changes, and the writer puts it in `touches`.

## Record

- 2026-11-04: filed from the spec loop's run 53.
