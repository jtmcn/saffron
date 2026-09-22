---
id: b-9ed36d
title: A criterion probe's blocker is filed under the adequacy lens, so the ledger and the pull request body credit a lens that never raised it
status: open
tier: 3
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: [§5.5, §5.6]
related: [b-2750d5]
---

## Problem

Found writing `SA-0120`, 2026-09-21. `SA-0120` files a criterion probe its
witness survives as a blocker for REBUT. REBUT runs verdicts only for the
lenses in `review.LENSES` (`saffron/phases/rebut.py:554-557`). A finding under
any other lens name reads as withdrawn. So the spec files the blocker under
`adequacy`, since `saffron/phases/rebut.py` was forbidden to it.

The ledger's findings rows, the pull request body and the adequacy verdict
session all read that blocker as the adequacy lens's own. No lens raised it.
The host did, from a session that saw one claim and the diff.

## Done looks like

A criterion probe's blocker carries a source of its own, and REBUT still runs
a verdict for it. The ledger row and the pull request body name that source.

## Record

- 2026-09-21: filed with `SA-0120`, which chose `adequacy` over editing
  `saffron/phases/rebut.py`.
