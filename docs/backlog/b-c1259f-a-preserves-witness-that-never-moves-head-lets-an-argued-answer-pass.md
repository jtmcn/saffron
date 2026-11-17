---
id: b-c1259f
title: A preserves witness for an argued withdrawal never moves HEAD, so an argued answer passing as fixed survives it
status: open
tier: 3
filed: 2026-11-17
closed:
specs: []
prs: []
commits: []
cites: [§5.6]
related: [b-7f6ce2]
---

## Problem

Found by `SA-0405`'s in-cell critic and its Spec seat, #1241, in the spec
loop's run 76.

`tests/test_session.py::test_a_preserves_criterion_probe_argued_out_of_the_diff_is_kept_confirmed`
runs REBUT with HEAD unmoved. So widening `_guarded_blockers`'s
`answer.action == "fixed"` to also take `argued` survives it, at base and at
head. Two `tests/test_rebut.py` witnesses kill that edit, so the suite holds.
The criterion's own witness does not, and `SA-0405` could not edit it.

## Done looks like

That witness adds a case with HEAD moved and an argued answer, and the
widened check fails it.

## Record

- 2026-11-17: filed from the spec loop's run 76, from #1241's review.
