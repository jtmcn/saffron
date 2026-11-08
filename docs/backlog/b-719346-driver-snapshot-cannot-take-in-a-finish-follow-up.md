---
id: b-719346
title: "`driver.py snapshot --add` refuses a finish's follow-up, so its pull request is recorded only after a hand edit of the order"
status: done
tier: 2
filed: 2026-10-27
closed: 2026-11-08
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-e0044f, b-25f2b2]
---

## Problem

Found in the spec loop's run 49.

`saffron finish 58` opened #982 for its follow-up `SA-0323`. `driver.py record
SA-0323` said it was not in the order. `snapshot --force --add SA-0323` said it
was not new since the last snapshot, because the queue counts a spec with a
reviewable pull request as done. The delegate wrote the order entry by hand and
placed the spec in the tree untracked.

## Done looks like

`snapshot` takes in each follow-up a finish ran, with its branch, its pull
request and its parent, and `record` reads it without a hand edit.

## Record

- 2026-10-27: filed from the spec loop's run 49.
- 2026-11-07: marked by hand in grooming. The work is in the spec loop's driver under
  `.claude/`, and `SA-0279` refuses any spec that touches that path.
- 2026-11-07: b-25f2b2 closed in grooming into this item. Its `record` refusal of a stack batch's follow-up is the same gap, and this item's fix lets `record` read the follow-up.
- 2026-11-07: raised to tier 2 in grooming. b-25f2b2 was tier 2, and its gap now lives
  only here, so this item takes its rank.
- 2026-11-08: done by hand.
