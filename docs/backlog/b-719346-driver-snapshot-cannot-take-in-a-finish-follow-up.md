---
id: b-719346
title: "`driver.py snapshot --add` refuses a finish's follow-up, so its pull request is recorded only after a hand edit of the order"
status: open
tier: 3
filed: 2026-10-27
specs: []
prs: []
commits: []
cites: []
related: [b-e0044f]
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
