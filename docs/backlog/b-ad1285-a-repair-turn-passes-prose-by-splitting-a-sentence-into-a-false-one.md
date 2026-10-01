---
id: b-ad1285
title: A repair turn passed `prose` by splitting a sentence, and the new sentence was false
status: partial
tier: 2
filed: 2026-09-28
closed:
by_hand: true
specs: []
prs: []
commits: [1dd2a73c]
cites: [§5.4]
related: [161, 163, b-044ae7]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, by #565's Standards seat
(`SA-0160`).

Attempt 1's four new failures were all `prose`. The repair turned
"many times over" and a clause on the idle bound, joined by a semicolon, into
two sentences. The second read "Twice the idle bound of 300 seconds."
(`saffron/spec_review.py:540` at `b9cbb5cc`) about 3600 seconds. `prose` passed
it. Review rewrote the comment in `6fc23834`.

## Done looks like

A repair that edits a comment only to clear `prose` is visible to REVIEW as
such. The repair prompt says a split keeps each sentence true. A lens reads a
comment the repair changed against its code.

## Record

- 2026-09-28: filed from the spec loop's run 20.
- 2026-09-30: the three `prose` messages that ask for a split now say each
  part stays true. A repair turn reads them verbatim. Two parts stay open.
  REVIEW does not see that a repair edited a comment only to clear `prose`.
  No lens reads a comment the repair changed against its code.
