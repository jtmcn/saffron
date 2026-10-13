---
id: b-cd1566
title: "`CONTEXT.md` has no entry for a criterion's subject, the `subject:` field SA-0291 adds"
status: open
tier: 2
by_hand: true
filed: 2026-10-13
specs: [SA-0291]
prs: []
commits: []
cites: [§5.4, §5.4.1]
related: [b-000d04, 84]
---

## Problem

Found 2026-10-13, writing `SA-0291`.

`SA-0291` adds `subject:` to an acceptance criterion. It names the path a
claim is about when the mutant's file is not that code. `revert` then sets
a witness aside only when its mutant's file and its subject both lie
outside the diff's source.

`CONTEXT.md` has no entry for it. Its **Mutant** entry says a mutant is
declared "against its own subject". That reads the mutant's file as the
subject, and `SA-0291` makes the two separable. So nothing constrains what
the next spec calls the field, and the **Mutant** entry says less than the
code.

`CONTEXT.md` is `protected`, and `SA-0291` forbids it. The entry lands by
hand.

## Done looks like

A **Subject** entry in `CONTEXT.md`, beside **Witness** and **Mutant**. It
says a criterion declares one only beside a mutant, as a repo-relative
path. It says a subject can only keep a witness judged by `revert`, never
set one aside. Its `_Avoid_` line names "target" and "scope". The
**Mutant** entry says a mutant's file is the subject unless the criterion
declares one. It lands after `SA-0291` merges.

## Record

- 2026-10-13: filed with `SA-0291`.
