---
id: b-223244
title: A re-queued spec runs on a fresh task, where DESIGN 4.2.1 says it resumes its task row
status: open
tier: 3
filed: 2026-09-25
closed:
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-792ab2]
---

## Problem

`DESIGN.md:387` says a re-queued spec "resumes that task row". Plain
`saffron batch` has never done so. `_batch_runner` passes `run_task` no
`task_id` (`saffron/cli.py:475-490`), so each cell mints a new task. Gate 0
exempts a resume (`saffron/scheduler.py:650-656`), which the design text
still describes.

The operator chose the same for a stack batch on 2026-09-24 (`SA-0155`,
`SA-0168`). A fresh task each night keeps every run, attempt and layer on
tonight's batch, so its spend and layers read exactly.

## Done looks like

`DESIGN.md` §4.2.1 describes what both paths do: a re-queued spec runs on a fresh task, and the older task keeps its state.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
