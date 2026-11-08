---
id: b-3cf039
title: "`migrate` derives no `rebuttal` fact for a blocker no verdict reached, so it refuses the ref a live cell wrote"
status: open
tier: 2
filed: 2026-11-07
specs: []
prs: []
commits: []
cites: [§5.6]
related: [42, b-9c7001]
---

## Problem

Found reviewing `SA-0340`, 2026-11-07.

A live cell writes a `rebuttal` fact for every confirmed blocker
(`saffron/cell/session.py:3738-3743`). `saffron migrate` derives one only when
the row's verdict or rebuttal is set (`saffron/record/migrate.py:534`). A REBUT
that ends at its early exit leaves both null, so `migrate` derives no fact for
any of its blockers. The top-up then holds more facts than it derives and
refuses the whole ref. `SA-0340` sets aside the new `answer` and `error` keys,
and this gap stays. Every unread or unanswered blocker at the early exit has
that shape.

## Done looks like

`migrate` derives a `rebuttal` fact for every blocker the ledger holds a
finding for, null verdict and null rebuttal included. A live ref with an
unread early exit tops up, and a test drives one.

## Record

- 2026-11-07: filed from `SA-0340`'s second spec review.
