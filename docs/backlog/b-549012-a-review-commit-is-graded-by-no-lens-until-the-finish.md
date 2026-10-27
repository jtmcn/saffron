---
id: b-549012
title: "A review commit is read by no lens until the deferred finish, so a delegate's fix that dropped a kill reached the stack"
status: open
tier: 2
filed: 2026-10-27
specs: [SA-0326]
prs: []
commits: []
cites: [§5.7]
related: [b-e0044f]
---

## Problem

Found in the spec loop's run 49.

The delegate's review commit `2742f631` on #978 made
`survivor_claim_with_suite_verdict` return early when `uncounted` was set.
That dropped a kill whenever the same run left an uncounted failure. Two review
seats had reviewed the original diff, and `make check` passed. Only the deferred
finish's end review raised it, as a blocker. Its follow-up `SA-0323`, #982,
fixed it.

## Done looks like

The lenses read a review commit before the next layer is restacked on it. Or
the loop records why the end review is enough.

## Record

- 2026-10-27: filed from the spec loop's run 49.
