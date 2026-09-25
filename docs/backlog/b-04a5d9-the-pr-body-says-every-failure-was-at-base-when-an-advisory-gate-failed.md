---
id: b-04a5d9
title: The PR body says every failure at head was present at base, though an advisory gate's new failure is dropped before it counts
status: open
tier: 2
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§5.4, §5.7]
related: []
---

## Problem

Found in the spec loop's run 16, 2026-09-24, reading the gate path.

`_new_failures` prints "Every failure at head was already present at base"
whenever `new_failures` is empty (`saffron/report/pr_body.py:248-252`).
`_compare` drops advisory gates' new failures before that list is built
(`saffron/gates/suite.py:239-244`).

So a new advisory `size` or `witness` failure reads as present at base. On
`SA-0140` (#501), `size` failed at head only, as an advisory, at 1651 tokens
over a 1300 ceiling.

## Done looks like

The body names new advisory failures in their own section, or the sentence
says blocking failures only. A test packages a head with one new advisory
failure and reads the body.

## Record

- 2026-09-25: filed from the spec loop's run 16.
