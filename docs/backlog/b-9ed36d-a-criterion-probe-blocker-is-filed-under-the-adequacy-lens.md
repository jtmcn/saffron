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

The first review of `SA-0120` traced six readers that take that blocker as
the adequacy lens's own. No lens raised it. The host did, from a session that
saw one claim and the diff.

- The ledger's findings rows and the pull request body.
- The adequacy verdict session. `saffron/agents/prompts/rebut-verdict.md:1-4`
  tells it "You filed the blockers below".
- REBUT's blocker line, "the tests stayed green"
  (`saffron/phases/rebut.py:133-136`). Only one witness ran. `SA-0120` puts
  that in the finding's claim as a stopgap.
- The adequacy lens's drop rate (`saffron/phases/review.py:121-126`). It
  counts every finding in the lens's list, so an unanchored criterion
  survivor raises it. `DESIGN.md:1038` reads that rate as a sign the lens is
  badly prompted.
- A recovered lens-scoring fixture. `harness/recovery.py:314` copies
  `findings.json` into `recorded-findings.json`, and `calibrate` scores it as
  the lenses' own output (`harness/lens_scoring.py:158-167`, `:428-447`).
- `Finding.probe`'s docstring (`saffron/agents/findings.py:42-53`) calls the
  field a vacuity probe. `CONTEXT.md:372` says to avoid that name for a
  criterion probe.

## Done looks like

A criterion probe's blocker carries a source of its own, and REBUT still runs
a verdict for it. The ledger row and the pull request body name that source.

## Record

- 2026-09-21: filed with `SA-0120`, which chose `adequacy` over editing
  `saffron/phases/rebut.py`.
