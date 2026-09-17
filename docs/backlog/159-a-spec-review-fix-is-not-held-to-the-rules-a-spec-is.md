---
id: 159
title: A spec edited to answer its review is not held to the rules a spec is, and three such edits cost a cell or a repair
status: open
tier: 2
filed: 2026-09-17
by_hand: true
specs: [SA-0093, SA-0094, SA-0095]
prs: [292, 293, 304, 306]
commits: []
cites: [§5.4]
related: [152, 153]
---

## Problem

**Tier 2.** By hand: `docs/agents/issue-tracker.md` and the spec loop's step
1b. Measured in the spec loop's run 5, 2026-09-16 to 2026-09-17.

Step 1b's reviews are good at finding what is wrong with a spec. What the loop
writes back into the spec to fix it gets no second look before a cell is
paid for, unless a child spec happens to be reviewed again. Three edits in
this run broke rules the authoring conventions already state or imply:

- **#292 asked `SA-0093`'s cell for two tests that pass at base** — guards for
  a property already true. `revert` judges every new test, declared or not, so
  it failed the attempt: `2 of 5 new test(s) passed without their source`.
  #293 took them out, and the review added them instead.
- **#292 widened `SA-0095`'s criterion 1** to "an aborted or drifted suite
  included" and gave it no witness. The re-review at the parent branch found
  it, and #306 fixed it.
- **#306 then offered "parametrise the witness"**. A parametrised test's
  node id carries a `[case]` suffix, so the declared bare id named nothing, and
  `criteria` failed attempt 1: `witness-not-collected`. The repair turn
  cost the cell its second attempt.

The same run's re-reviews also found a witness stub that answers every
subnet alike (#304) and two notes pointing at code seams that do not exist
(#306), both in text the first review had already passed.

## Done looks like

`docs/agents/issue-tracker.md` states that a test the cell is asked for must
fail at base, that a declared witness is never parametrised, and that a claim
added or widened in review needs its witness named in the same edit. The loop
re-reviews an edited spec before its first cell, not only a child spec at its
parent's branch.

## Record

**Filed 2026-09-17** from the spec loop's run 5 (stack #308).
