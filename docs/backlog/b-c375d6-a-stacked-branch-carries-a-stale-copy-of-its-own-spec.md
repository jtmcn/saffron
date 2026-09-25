---
id: b-c375d6
title: A stacked branch carries its own spec as it stood when its base was cut, so a PR seat reading that copy reviews against stale text
status: open
tier: 2
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§4.2, §5.5]
related: [b-bff670]
---

## Problem

Found in the spec loop's run 16, 2026-09-24, on `SA-0136` (#514).

`SA-0136`'s branch was cut from `SA-0135`'s, which forked from main before
#511 edited `SA-0136`'s spec. The cell ran main's text. The PR's Spec seat
read the spec from the branch, and raised a concern about a parenthetical
that #511 dropped. The concern was void.

Any spec edited on main after its stack's base was cut has the same gap. The
branch diff shows no change to the spec, so nothing flags the copy as old.

## Done looks like

A PR seat reads the spec at the commit the cell ran, which the task records.
The skill names that commit in the seat's prompt. A test or a driver check
shows the two copies differ on a stacked fixture.

## Record

- 2026-09-25: filed from the spec loop's run 16.
