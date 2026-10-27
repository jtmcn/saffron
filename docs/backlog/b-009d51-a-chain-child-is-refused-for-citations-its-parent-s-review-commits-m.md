---
id: b-009d51
title: "A chain child is refused for citations its parent's review commits moved, so each child costs a spec PR and a batch"
status: open
tier: 2
filed: 2026-10-25
specs: [SA-0321]
prs: []
commits: []
cites: [§3.4]
related: [b-d31930]
---

## Problem

Found in the spec loop's run 48.

`SA-0315` was refused in batch 53 with four citations unresolved at
`origin/saffron/SA-0313`. `SA-0316` was refused in batch 54 with seven
unresolved at `origin/saffron/SA-0315`. Each refusal cost a spec PR (#962,
#965), a CI wait and one more batch. `cite` already names where each
construct moved, as in "the construct it names sits at
tests/test_cli.py:5671-5690". The delegate copied those lines by hand.

## Done looks like

A citation whose construct `cite` finds at one new place is rewritten, or
judged by the construct, before the batch refuses the spec.

## Record

- 2026-10-25: filed from the spec loop's run 48.
