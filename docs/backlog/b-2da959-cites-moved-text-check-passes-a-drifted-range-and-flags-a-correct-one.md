---
id: b-2da959
title: "`cite`'s moved-text check passes a range that drifted and flags a range that is right"
status: done
tier: 2
filed: 2026-10-16
closed: 2026-10-24
specs: [SA-0314]
prs: [956]
commits: []
cites: [§3.2]
related: [b-d31930]
---

## Problem

Found in the spec loop's run 42, refreshing 18 citations in #892.

`_moved_lines` reports a move only when none of the sentence's backticked
strings sits in the cited range. A common token in the range passes it.
`SA-0275` cited `saffron/ledger.py:314-321` for `stack_finishes`, which had
moved to 318-324. The check passed it, because `IF NOT EXISTS` sits in both.

It fails the other way too. Four of the 18 ranges were right, but the name
the sentence quotes sat on the `def` or `class` line above the range.
The check reported each one as moved.

`SA-0294` ports this check into core as the batch's preflight. It carries
both faults with it.

A third fault, found in run 43 by the in-cell critic and both seats on #898.
Only a range's end is checked against the file. A citation at line `0`, or a
reversed range such as `f.py:3-1`, resolves. `SA-0294` kept the driver's
behaviour word for word, so `driver.py` and `saffron/spec_citations.py` both
carry it.

## Done looks like

A citation is judged by the construct it names, not by any string in its
sentence. A range that holds the named body passes, and so does one that
starts a line below its `def`. A range that moved off its construct fails,
whatever common tokens it still holds. A range that starts below line 1, or ends before it starts, fails in both
copies. Each case has a test.

## Record

- 2026-10-16: filed from the spec loop's run 42.
- 2026-10-17: the line-0 and reversed range fault added from the spec loop's run 43. The operator chose to fix both copies together.
- 2026-10-23: recurred in the spec loop's run 46. The batch's own `citation_defects` refused 19 correct citations out of 20 in `SA-0304`. Refreshes for `SA-0305` and `SA-0306` split sentences and widened ranges only to pass it.
- 2026-10-24: done by `SA-0314` (#956), from the spec loop's run 47. A hand
  commit on that layer points `driver.py cite` at the core checker, so both
  copies now share one rule. b-c3688d carries the layout rule left in core.
