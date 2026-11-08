---
id: b-3df181
title: '`rebut_state` reads an empty rebuttal error as no answer, so an unreadable turn''s why line says "recorded nothing"'
status: open
tier: 2
filed: 2026-11-08
specs: []
prs: []
commits: []
cites: [§5.6]
related: [42, b-31e3c8]
---

## Problem

Found reviewing `SA-0340` (#1084), in the spec loop's run 55. Both seats
kept it as out of scope.

`SA-0340` sets a turn's error whenever `error is not None`, the empty string
included. `rebut_state` still tests the error for truth
(`saffron/phases/rebut.py:543`, `rebuttal.error or "recorded nothing"`). A
session that raised with an empty message is unreadable, and its why line
reads as a turn that answered nothing. §5.6 forbids that reading.

## Done looks like

`rebut_state` tests `error is not None`, as `blocker_answers` does. A test
drives a turn whose error is the empty string and asserts the why line says
the rebuttal was unreadable.

## Record

- 2026-11-08: filed from the spec loop's run 55.
