---
id: b-a5d4af
title: Three texts still tie a probe to REVIEW's adequacy lens after `probe_findings` went general
status: done
tier: 3
filed: 2026-09-27
closed: 2026-09-27
by_hand: true
specs: []
prs: []
commits: [6a6c4e3d]
cites: []
related: [b-37924b, b-792ab2]
---

## Problem

Found in the spec loop's run 19, 2026-09-27, reviewing `SA-0178` (#539).

`SA-0178` made `probe_findings` take any findings, and `SA-0180` calls it from
`saffron/qualify.py:148` for end-review findings. Three texts still describe
REVIEW's adequacy probes alone.

- `CONTEXT.md:376-378`, the **Vacuity probe** entry, says the host applies
  each anchored adequacy finding's probe after REVIEW.
- `saffron/cell/session.py:1457` calls a failure "not an exception that
  discards a paid REVIEW".
- `saffron/phases/review.py:580` says `adequacy_probes already filtered this`.

`CONTEXT.md` is generated from `ontology/factory.ttl` and protected, so the
entry is hand work.

## Done looks like

The entry names end-review findings beside REVIEW's, and both comments name
every caller.

## Record

- 2026-09-27: filed from the spec loop's run 19.
- 2026-09-27: fixed by hand. The entry and both comments name end-review findings too.
