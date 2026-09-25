---
id: b-e8027b
title: '`snapshot --force` releases every hold, including one whose spec edit is still an open pull request'
status: open
tier: 2
filed: 2026-09-21
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-4589be, 137]
---

## Problem

Step 1b holds a spec while its edit is unmerged, so `next` cannot run its old
text. The skill says the re-snapshot after the merge releases the hold.

Any `snapshot --force` releases it, whether or not that edit merged. In the
spec loop's run 12, `SA-0116`'s edit (#413) merged first. The re-snapshot that
added `SA-0116` also released `SA-0117`'s hold, while `SA-0117`'s edit (#414)
was still open. `next` then named `SA-0117` at its old text. The delegate
noticed and held it again by hand.

## Done looks like

A hold carries the pull request it waits on, and `snapshot --force` keeps it
while that pull request is open. `status` names every hold it kept and why.

## Record

- 2026-09-21: filed from the spec loop's run 12.
- 2026-09-25: recurred in the spec loop's run 16. `snapshot --force` after
  #497 released `SA-0140`'s hold while its edit (#498) was open. The
  delegate held it again by hand.
