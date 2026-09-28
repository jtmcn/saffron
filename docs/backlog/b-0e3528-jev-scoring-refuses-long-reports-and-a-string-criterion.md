---
id: b-0e3528
title: Jev scoring refuses a report over about 9000 characters and a finding whose criterion is a string
status: open
tier: 3
filed: 2026-09-27
closed:
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 19, 2026-09-27.

- `driver.py jev` failed with a 400 `max_tokens_exceeded` on all four
  spec-review reports of #538, at 6000 to 12000 characters. It failed on
  #551's pull request review too, at 9000 to 11000. Reports of 5000 to 6000
  passed.
- #544's Standards seat wrote a finding's criterion as the string `"1"`. The
  scorer refused it: `finding 1's criterion is not an integer or null`.

Each failure left a review round unscored.

## Done looks like

`driver.py jev` scores a report of 12000 characters. It coerces a criterion
written as a digit string, or the review prompts say integer.

## Record

- 2026-09-27: filed from the spec loop's run 19.
