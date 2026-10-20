---
id: b-998bb7
title: A comment split by a blank line passes the `prose` gate's two-line limit
status: done
tier: 2
filed: 2026-10-20
closed: 2026-10-20
by_hand: true
specs: []
prs: [920, 924]
commits: []
cites: [§5.4]
related: [b-122686, b-044ae7]
---

## Problem

Found by both seats on #920, in the spec loop's run 45.

`SA-0291`'s cell wrote two four-line comments, one in
`saffron/gates/core/revert.py` and one in `tests/test_revert.py`. Each was
one thought split by a blank line into two blocks of two lines. The
`comment-block` rule counts a block that ends at a blank line
(`.saffron/gates/prose.py`, `COMMENT_LIMIT = 2`). So each half passed. The
Spec seat joined the halves and measured a 4-line `comment-block` hit at
each site. The critic raised neither. Review cut each to two lines.

## Done looks like

The `comment-block` rule reads a comment run broken only by blank lines as
one block, unless code sits between the parts. The rule ships with the
`SA-0291` shape as its failing case.

## Record

- 2026-10-20: filed from the spec loop's run 45. A review commit on #920
  fixed both instances.
- 2026-10-20: fixed by hand in #924. A comment run now ends only at code.
  Eight existing runs join into hits that subtraction grandfathers.
