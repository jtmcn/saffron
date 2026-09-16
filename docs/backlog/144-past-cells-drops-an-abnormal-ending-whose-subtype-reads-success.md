---
id: 144
title: A cell's history hides any attempt that ended abnormally while its subtype read `success`
status: open
tier: 2
filed: 2026-09-16
by_hand: false
specs: [SA-0092]
prs: [279]
commits: []
cites: [§4.3]
related: [123, 34]
---

## Problem

**Tier 2.** Found reviewing `SA-0092` (PR #279), against the live ledger.

`driver.py`'s `_past_cells` builds each row's `endings` only from attempts whose
`subtype not in (None, "success")`. An attempt that ended on something other
than `completed` while its subtype read `success` never reaches the row's
`ended:` field at all.

The live ledger has six such rows — `subtype=success, terminal_reason=api_error`
— including a 22-turn REVIEWING and a 7-turn REBUTTING attempt. A spec review
reading `history` cannot see that those attempts ended abnormally, and no
predicate built on `endings` can either.

That is the same shape as the defect `SA-0092` fixed one line over: the driver
read a cut-off from the *rendered* `endings` string rather than the attempt's own
fields, so a turn-ceiling kill carried on `terminal_reason` alone was invisible.
The review fixed the predicate by carrying `PastCell.peak_cut_off` from the peak
attempt. `endings` itself still filters on subtype.

## Done looks like

`endings` keyed on `terminal_reason != "completed" or subtype != "success"`, so
an abnormal ending reaches the row however it was spelled.
