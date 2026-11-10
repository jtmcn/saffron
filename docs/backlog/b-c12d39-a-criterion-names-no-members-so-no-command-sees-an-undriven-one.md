---
id: b-c12d39
title: "A criterion names no members of the sets its claim covers, so no command sees an undriven one"
status: open
tier: 2
filed: 2026-11-09
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-250dc7, b-98a3be]
---

## Problem

The spec reviews keep finding one class: a claim over a set whose witness
drives only one member. A claim with a negative clause has a witness that
never observes the positive case. Rules in prose have not stopped it.

- The 2026-11-04 chain record counts five of six blockers in this class.
- The 2026-11-07 chain record counts seven findings in it, three of them
  blockers. Every brief in that run named the class.
- `SA-0353`'s writer killed 44 wrong versions on a prototype, and its review
  still found a member no witness drove.

The writer's step 6 puts a set table in its report, and the report is not in
the spec. A `Criterion` in `saffron/intake.py` has `claim`, `witness`,
`preserves`, `mutant`, `subject` and `wrong_versions`. It forbids any other key.
So no command can read the members, and a spec that declares them fails to
parse.

## Done looks like

1. A criterion can declare the members of each set its claim covers. Each
   member names the witness or wrong version that drives it.
2. A criterion whose claim has a negative clause declares the positive case
   its witness observes through the same instrument.
3. A command fails a spec in which a declared member names no driver, or a
   negative claim declares no positive case.
4. The command cannot know a list is complete, and its docstring says so.
5. Every spec queued and done at the change still parses.

## Record

- 2026-11-09: filed from the spec chain speed review. The writer prompt is
  the interim home of the rule, since a new key breaks parsing until this
  lands.
