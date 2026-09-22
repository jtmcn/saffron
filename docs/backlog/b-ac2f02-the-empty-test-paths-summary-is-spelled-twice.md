---
id: b-ac2f02
title: The empty-`test_paths` refusal is spelled twice by hand, in `revert` and in `probe_refusal`
status: open
tier: 3
filed: 2026-09-22
specs: [SA-0119, SA-0122]
prs: [431, 436]
commits: []
cites: [§5.4]
related: [b-461729]
---

## Problem

Found reviewing `SA-0119` (#431) and `SA-0122` (#436), 2026-09-22.

`saffron/gates/core/revert.py:159-162` and `saffron/probe.py`'s `probe_refusal`
each spell "the repo declares no test paths, so source cannot be told from
test" by hand. `SA-0119` made the two rules one rule and left the sentence in two
places. A shared constant needs `revert.py`, which both specs forbade.

## Done looks like

One constant holds the sentence, and both call sites read it.

## Record

- 2026-09-22: filed from the spec loop's run 13.
