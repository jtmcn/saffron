---
id: b-d2b6b3
title: '`revert` reads no declared rename, so a renamed test that passes without the source is refused as new'
status: done
closed: 2026-11-15
tier: 3
filed: 2026-11-14
specs: [SA-0389]
prs: [1202]
commits: []
cites: [§5.4]
related: [b-f30189]
---

## Problem

Found writing and running `SA-0387` (#1196) in the spec loop's run 69.

`census` now accepts a spec's declared `renames`. `revert` does not read
them. It treats a name collected at head and not at base as a new test
(`saffron/gates/core/revert.py:261`). So a renamed test that passes
without the diff's source is still refused, as #1099's was. `SA-0387`'s
Out of scope names this.

The finishing layer has the same hole from the other side. Its suite runs
under the synthetic `FINISH-0` spec (`saffron/finish.py:110-115`), which
declares no renames. So finish 82's revised parametrize ids still read as
a removed test.

## Done looks like

`revert` leaves a declared rename's new name out of its new-test set
when the old name was collected at base. The finishing layer passes its
layers' declared renames to its own suite, or says why it cannot.

## Record

- 2026-11-14: filed from the spec loop's run 69.
- 2026-11-14: `SA-0389` (#1202) lets `revert` read a spec's declared renames
  by `census`'s rule. The `FINISH-0` half stays open, since that spec
  declares none.
- 2026-11-15: closed, since the `FINISH-0` half cannot apply. The
  finishing suite's base is the top layer, so every layer's declared
  rename already sits below it. Passing them would exempt nothing.
