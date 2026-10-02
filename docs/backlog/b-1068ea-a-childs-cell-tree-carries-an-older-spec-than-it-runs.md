---
id: b-1068ea
title: 'A child''s cell tree carries its spec as of the parent''s branch, while the host passes the newer text'
status: open
tier: 3
filed: 2026-10-02
specs: [SA-0167]
prs: [637, 638]
commits: []
cites: []
related: [b-1f1188]
---

## Problem

Found in the spec loop's run 25, 2026-10-02.

`SA-0167`'s cell was cut from `saffron/SA-0177` at `4e66195d`. That branch
sat on #635's merge, so its tree held `SA-0167`'s spec without #637's two
witness fixes. The host passed the #637 text, so the prompt and the tree
disagreed. The cell built to the prompt, and the Spec seat confirmed the
#637 text was met.

## Done looks like

A child's cell sees one spec text. The worktree's copy is the text the
host passes, or the cell is told which one governs.

## Record

- 2026-10-02: filed from the spec loop's run 25.
