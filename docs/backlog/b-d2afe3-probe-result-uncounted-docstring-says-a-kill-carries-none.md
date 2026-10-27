---
id: b-d2afe3
title: "`ProbeResult.uncounted`'s docstring says a `killed` result carries none, and `check_probe` returns one that does"
status: open
tier: 3
filed: 2026-10-27
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 49, by both seats on #982.

`saffron/probe.py:134-138` says "A `killed` result carries none of these
codes." Yet `check_probe` returns `killed` with a non-empty `uncounted`. It
does so when one new failure is counted and another is not. #982's witness depends on that result.
`SA-0323` listed the file as `forbidden`.

## Done looks like

The docstring states that a `killed` result can carry uncounted failures.

## Record

- 2026-10-27: filed from the spec loop's run 49.
