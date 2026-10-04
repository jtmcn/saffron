---
id: b-348114
title: Four lines of `CLAUDE.md` and `DESIGN.md` lag what run 27's stack built
status: open
tier: 3
filed: 2026-10-03
by_hand: true
specs: [SA-0197, SA-0198, SA-0199]
prs: [659, 662, 670]
commits: []
cites: [§4.7, §6]
related: [b-2d09de, b-49a2f7, b-0703c8]
---

## Problem

Found by the step 1b reviews and the Standards seats in the spec loop's run 27.
Each spec forbade these files, so no cell could fix them.

- `CLAUDE.md:63` lists only `saffron watch SA-NNNN`. The form with no spec id
  follows every task (`SA-0197`).
- `DESIGN.md:548` says each spec has one `events.jsonl` that `saffron watch`
  follows. The command now follows them all.
- `DESIGN.md:1285` says the header can only show the rate over prior batches.
  `SA-0198` counts the night's own settled tasks, as §6's next paragraph and
  `CONTEXT.md` define the window. The operator ran it as written.
- `DESIGN.md:1277` calls the end-of-task line "the verdict line". `CONTEXT.md`
  says a queue line is never a verdict.

## Done looks like

Each line says what the code does. `DESIGN.md:1285` says the window counts the
night's own settled tasks, or the operator decides otherwise.

## Record

- 2026-10-03: filed from the spec loop's run 27.
