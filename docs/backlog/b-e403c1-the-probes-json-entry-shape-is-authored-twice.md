---
id: b-e403c1
title: '`probes.json`''s entry shape is authored twice, with nothing holding the two together'
status: done
closed: 2026-09-22
tier: 3
filed: 2026-09-19
specs: [SA-0122]
prs: [436]
commits: []
cites: [§5.5]
related: [94, 117]
---

## Problem

Found by the spec loop's Standards seat reviewing #375, 2026-09-19.

The host writes `probes.json` from a dict literal in `saffron/cell/session.py`.
The lens-corpus driver writes the same record from `_baseline_keys` in
`docs/evidence/scripts/2026-09-08-lens-corpus.py`. The key names match today,
checked line by line, and no test compares them. Item 94's fields will drift
the first time either side gains one, and the corpus is what a lens's kill rate
is measured against.

## Done looks like

The entry-shape helper lives in `saffron/probe.py` and both writers call it.

## Record

- 2026-09-19: filed from the spec loop's run 9 (#375). Both files were
  forbidden to `SA-0109`.
- 2026-09-22: done, `SA-0122`, #436, in the spec loop's run 13. Both writers
  call one helper in `saffron/probe.py`.
