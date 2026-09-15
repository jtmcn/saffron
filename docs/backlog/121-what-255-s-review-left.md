---
id: 121
title: 'What #255''s review left'
status: open
tier: 3
filed: 2026-09-14
specs: [SA-0086]
prs: [255]
commits: []
cites: []
related: []
---

## Problem

**Tier 3.** Kept from the review of `SA-0086` (PR #255), 2026-09-14.

- **The stacked unmoved-parent note is unwitnessed.** In
  `saffron/phases/package.py`, `moved = needs_reverification(target_head,
  tree_base)` survives the mutant `tree_base` → `base_sha` across all 136 tests
  in `tests/test_package.py`. No test drives a red re-run for a stacked child
  whose parent held still, so the "the base did not move" note is untested on
  that path. It was kept because a stacked witness would have taken the branch
  past its 300-line ceiling.
- **The body's new-failures section may still be the cell's.**
  `render_pr_body` receives `outcome.new_failures` beside the re-run's gate
  table. The section is reached only when the re-run found no new failures, so
  whether this is a defect depends on whether a `READY_FOR_REVIEW` outcome can
  carry a non-empty list, for example advisory failures. Unverified.

## Done looks like

a stacked witness with an unmoved parent and a red re-run,
asserting the note, and the second bullet either reproduced or closed on reading.
