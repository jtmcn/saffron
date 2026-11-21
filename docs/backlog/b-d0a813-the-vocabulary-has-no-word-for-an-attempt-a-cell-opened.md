---
id: b-d0a813
title: "The vocabulary has no word for an attempt a cell opened, and `SA-0418` dates a task by one"
status: open
tier: 3
outside_cell: true
filed: 2026-11-20
specs: []
prs: []
commits: []
cites: [§4.1]
related: [b-952c34]
---

## Problem

Filed with `SA-0418`, written for b-952c34.

`SA-0418` ties a task to the span that holds its last cell attempt. Its
first claim defines a cell attempt as any attempt outside the phases
`SPEC_REVIEW`, `SPEC_WRITING` and `COMMIT_REVIEW`. `CONTEXT.md` defines
**Attempt** (`CONTEXT.md:356`) and names no kind of it.

The same split exists in code under other words. `saffron/task.py:1132-1134`
calls the two spec phases "a spec session charged to this task outside its
own cell". `ontology/` and `CONTEXT.md` are both forbidden to the cell, so
it cannot add the entry itself.

## Done looks like

`ontology/factory.ttl` names a cell attempt, or `CONTEXT.md` says under
**Attempt** which phases are a cell's own. `CONTEXT.md` is rendered from
the vocabulary with `uv run python -m ontology.render`. Or the operator
decides the phrase stays a plain compound and closes this record.

## Record

- 2026-11-20: filed with `SA-0418`, by hand, as `issue-tracker.md` asks of
  a spec that introduces a term.
