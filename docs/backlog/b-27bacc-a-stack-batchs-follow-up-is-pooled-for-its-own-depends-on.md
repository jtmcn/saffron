---
id: b-27bacc
title: "A stack batch's follow-up is pooled for declaring a `depends_on`, so the writer's spend buys no spec"
status: open
tier: 2
filed: 2026-10-10
specs: []
prs: []
commits: []
cites: []
related: [b-8a0c9a, b-25f2b2]
---

## Problem

Found in the spec loop's run 33, reading the end review of batch 21
(`~/.saffron/batches/v0/finish/21/findings.json`).

The writer drafted follow-ups for the end review's findings, and none
became a spec. `follow_up._validate` refuses a candidate that declares a
`depends_on` entry (`saffron/follow_up.py:185`). In a stack every layer
sits on another, so the writer named one each time. Three groups were
pooled for that reason. Two more were pooled because the writer's text had
no YAML frontmatter. One was pooled because the writer declared type `test`.
The batch's `follow_ups` list came back empty.

## Done looks like

- The writer is told the shape `_validate` accepts, or `_validate` admits a
  stack follow-up that names the layer it fixes as its parent.
- A pooled draft says which rule refused it in the batch log, and the
  writer is not paid again for that rule.
- A test drafts a follow-up in a stack and admits it.

## Record

- 2026-10-10: filed from the spec loop's run 33.
