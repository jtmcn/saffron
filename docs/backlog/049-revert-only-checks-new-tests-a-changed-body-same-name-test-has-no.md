---
id: 49
title: '`revert` only checks *new* tests — a changed-body-same-name test has no coverage'
status: open
tier: 1
specs: []
prs: []
commits: []
cites: [§2.1, §5.4, §5.5.1]
related: [50, 51]
---

## Problem

Its subset is `collected(head) - collected(base)`, `census`'s own route. That
catches a new test that tests nothing; it cannot catch an *existing* test
rewritten under the same node id, which needs a hunk-to-node-id mapping —
language knowledge §2.1 keeps out of core. `criteria`'s witnesses and the
third critic lens (§5.5.1) both narrow this, so a changed-body test with no
declared witness is the only true gap.

## Done looks like

a repo-declared role reporting that mapping, so core can compute a second,
disjoint subset through the machinery already built; unbuilt because no
runner reports it yet.

## Record

**Decided 2026-09-04, with items 50 and 51: the `tests` role reports what
became of each name it was handed.** One §5.4 contract addition, not three
fixes. It closes 50 and 51 outright and narrows this one; what is left here is
the changed-body-same-name case, which needs the repo-declared hunk-to-node-id
mapping this item already describes. **Tier 1** with 51, since that is what
forces the contract.
