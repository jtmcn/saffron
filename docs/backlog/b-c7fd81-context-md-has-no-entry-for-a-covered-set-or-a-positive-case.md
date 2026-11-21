---
id: b-c7fd81
title: '`CONTEXT.md` has no entry for a covered set or a positive case, the fields SA-0415 adds'
status: done
closed: 2026-11-20
tier: 2
outside_cell: true
filed: 2026-11-18
specs: []
prs: [1275]
commits: []
cites: [§5.4]
related: [b-c12d39]
---

## Problem

Found 2026-11-18, writing `SA-0415`.

`SA-0415` adds two fields to a criterion. `covers` lists the sets its
claim quantifies over, and each member names the witness or wrong
version that drives it. `positive_case` names the case the witness
observes where a negative clause's effect does happen. `CONTEXT.md` has
no word for either. So nothing constrains what the next spec calls them.

`CONTEXT.md` is `protected`, and `SA-0415` forbids it. The entries land
by hand.

## Done looks like

A **Covered set** entry and a **Positive case** entry in `CONTEXT.md`,
beside **Wrong version**. The first says a criterion's `covers` names
each set and its members. It says each member's `driven_by` is the
criterion's own witness or one of its own wrong versions, quoted
exactly. It says `driver.py check` blocks on a member that names
neither, and that no command can know a set is complete. The second
says a positive case is one sentence. It says `check` blocks on a claim
holding a listed negation word that declares none. Its `_Avoid_` line
names "positive control". They land after `SA-0415` merges.

## Record

- 2026-11-18: filed with `SA-0415`.
- 2026-11-20: landed by hand after #1271 merged `SA-0415`, with lines in the
  spec writer's step 6, the spec reviewer's check 3 and `issue-tracker.md`.
