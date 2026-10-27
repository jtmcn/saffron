---
id: b-1b8b1e
title: "No witness drives `citations_held_at`'s `tokens_at` for a file suffix that leaves the tree by the later head"
status: open
tier: 3
filed: 2026-10-27
specs: []
prs: []
commits: []
cites: []
related: [b-009d51]
---

## Problem

Found in the spec loop's run 49, by `saffron finish 58`.

A review commit on #977 made `citations_held_at` read path suffixes at
`tokens_at`, the head the later check reads. Its witness drives a suffix that
appears by that head. The end review drafted `SA-0324` for the other direction,
a suffix that leaves the tree, as in a removed `x.rs`. The finish refused the
draft for two citations that do not resolve, so it never ran. The draft asks for
a unit witness, an integration witness through `cli._stack_cite`, and one
docstring sentence.

## Done looks like

A witness fails when `tokens_at` is dropped for a suffix that leaves the tree
by the later head, at both `citations_held_at` and `_stack_cite`.

## Record

- 2026-10-27: filed from the spec loop's run 49.
