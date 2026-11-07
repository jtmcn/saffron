---
id: b-9c5b11
title: "No gate checks that a spec id a comment cites exists, so a cell cited the nonexistent SA-0320"
status: superseded
tier: 3
filed: 2026-10-25
closed: 2026-11-07
specs: []
prs: [1017]
commits: []
cites: [§5.4]
related: []
superseded_by: b-249808
---

## Problem

Found in the spec loop's run 48.

`SA-0315`'s cell wrote `SA-0320` into two docstrings and a test banner.
No spec with that id existed, and `saffron next-id` returned `SA-0317`.
The conventions lens caught it, so it cost a review fix and not a defect.

## Done looks like

A gate fails a new `SA-NNNN` in a diff that names no spec file in
`.saffron/specs/` or `.saffron/specs/done/`.

## Record

- 2026-10-25: filed from the spec loop's run 48.
- 2026-11-07: closed in grooming as superseded by b-249808, filed in #1017. Both ask for a gate that fails a diff citing a spec id with no file in `.saffron/specs/` or `done/`. b-249808 also admits the task's own id and carries the later, larger case (`SA-0330` cited `SA-0332` at 20 sites). No gate under `saffron/gates/` or `.saffron/gates/` reads a cited spec id today, so the defect stays open under b-249808.
