---
id: b-b431c1
title: The ledger's per-lens drop rate still counts a host-filed survivor against the adequacy lens
status: open
tier: 3
filed: 2026-09-22
specs: [SA-0120]
prs: [434]
commits: []
cites: [§4.1, §5.5]
related: [b-2750d5]
---

## Problem

Found writing and reviewing `SA-0120` (#434), 2026-09-22.

`DESIGN.md` §4.1 reads the drop rate off `findings.anchored` grouped by lens
(`DESIGN.md:335`, `saffron/ledger.py:144-146`). The host files a surviving
criterion probe under `adequacy`, so that query counts it against the lens.
`SA-0120` excluded it from `LensReview.drop_rate` alone, because
`saffron/ledger.py` was forbidden to it.

## Done looks like

The ledger's drop rate leaves out a finding whose claim starts with
`review.HOST_FILED`, with a witness over a stored survivor.

## Record

- 2026-09-22: filed from the spec loop's run 13.
