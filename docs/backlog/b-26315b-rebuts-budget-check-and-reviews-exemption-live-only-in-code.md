---
id: b-26315b
title: REBUT's budget check and REVIEW's exemption from §4.3 live only in a code comment, and §5.5.1 cites a §5.5 sentence that does not exist
status: open
tier: 3
filed: 2026-09-22
by_hand: true
specs: []
prs: []
commits: []
cites: [§4.3, §5.5, §5.5.1, §5.6]
related: [120]
---

## Problem

Found reviewing ADR 4, 2026-09-22.

§4.3 bounds every phase on spend, host-side. Two phases break that rule, and
only a comment in `saffron/cell/session.py` (`REVIEW_FLOOR_USD`) says so.

- REVIEW is never stopped for money. Each lens runs on the remainder, floored
  at $2, and the host sums the cost after every lens has run.
- REBUT checks the ceiling before the rebuttal turn. A task already over it
  ends `EXHAUSTED` with no rebuttal, so "any one blocker goes to REBUT" has an
  exception no section states.

§5.5.1 says "REVIEW is not gated on the spend ceiling (§5.5)". §5.5 has no such
sentence.

## Done looks like

§4.3 names both exceptions, §5.5 or §5.6 states REBUT's check, and §5.5.1's
citation points at a sentence that exists.

## Record

- 2026-09-22: filed from ADR 4's review. ADR 4's principle 29 records it.
