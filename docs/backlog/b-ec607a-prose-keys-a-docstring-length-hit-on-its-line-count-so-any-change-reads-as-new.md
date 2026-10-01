---
id: b-ec607a
title: '`prose` keys a docstring-length hit on its line count, so a grow or a shrink reads as a new hit'
status: done
tier: 3
filed: 2026-09-27
closed: 2026-09-30
by_hand: true
specs: []
prs: []
commits: [b3cd37fd, 9ef9e7b2]
cites: [§8]
related: [b-044ae7, b-43061c]
---

## Problem

Found in the spec loop's run 19, 2026-09-27. Three defects in the gate
39ab1e4b rebuilt for b-044ae7.

- A `docstring-length` hit's identity holds the block's line count. So a
  docstring already over the limit reads as a new hit when it grows and when
  it shrinks. The queue smoke test's docstring trips it on every re-measure.
  The loop replaces its newest paragraph at equal length to pass.
- A code span wrapped across a line break hides the hits after it in the
  paragraph. An em dash on #544 passed the gate, and the Standards seat
  found it.
- A sentence hit's identity is its text. Editing a sentence that holds an old
  hit makes the old hit new (#546).

## Done looks like

A `docstring-length` hit is new only when a block crosses the limit or grows
past its base length. A wrapped code span hides no later hit. An old hit in an
edited sentence stays old. A test holds each case.

## Record

- 2026-09-27: filed from the spec loop's run 19.
- 2026-09-27: two of three fixed by hand. A wrapped code span hides no later hit, and a word hit keys on the words near it. A shrinking docstring still reads as new, because baseline subtraction compares identities and cannot see that a block grew.
- 2026-09-30: the third is fixed. A `docstring-length` hit is one per line past
  the limit, keyed by name and line. A shrink adds no hit, and a growth adds
  only the lines past its base.
