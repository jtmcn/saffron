---
id: b-b0cd68
title: Retiring a spec turns this repo's gate suite red, so no stack batch finish can push here
status: open
tier: 2
filed: 2026-09-25
closed:
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-792ab2]
---

## Problem

A stack batch's finishing commit moves each layer's spec to `done/`
(`SA-0151`). This repo's `tests/test_scheduler.py` smoke test pins the live
`.saffron/specs/` list, and `tests/test_queued_specs.py` parametrizes over
each queued spec file. Retiring a spec changes the first and removes
collected ids from the second. `census` fails a removed test name with no
override (`saffron/gates/core/census.py:35-39`). So `SA-0167`'s gate suite on
the finishing tree is red in this repo on every finish, and nothing is
pushed.

## Done looks like

The two tests read the spec directory in a way a retirement does not break, and a finishing commit in this repo can go green.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
