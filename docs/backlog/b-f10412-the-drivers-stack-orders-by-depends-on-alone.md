---
id: b-f10412
title: "The loop driver's `stack` orders layers by `depends_on` alone, so it misreads a stack batch's chain"
status: open
tier: 2
filed: 2026-10-09
specs: []
prs: [780, 788, 790]
commits: []
cites: []
related: [b-2247dd, b-883f74]
---

## Problem

Found in the spec loop's run 32, linking stack #791.

A stack batch cuts every layer from its predecessor's head, whatever
`depends_on` says. `_stack_order` in
`.claude/skills/run-saffron-spec-loop/driver.py:538-591` sorts layers by
`depends_on` alone. So it put siblings in an order the branches do not hold.
It printed that #788's diff is unaffected, which is false when a layer is
built on its predecessor.

It also keeps only rows it reads as reviewable, with a pull request in the
ledger. #780 (`SA-0233`, hand-packaged after a PACKAGE seed failure) and #790
(`SA-0255`, finished by hand) have none. So `stack` left both out. The
delegate wrote a script to rebase the real chain and to put #780 on top.

## Done looks like

`stack` reads the order a stack batch built, from its predecessor heads, and
prints no claim about a diff it did not measure. A layer the delegate packaged
by hand can be named on the command line. A test drives a three-layer stack
batch whose `depends_on` names none of its predecessors.

## Record

- 2026-10-09: filed from the spec loop's run 32.
