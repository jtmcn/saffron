---
id: b-fab381
title: The spec loop's `snapshot` strands a child whose other parent already merged, so one refusal cuts a chain
status: open
tier: 2
filed: 2026-09-26
specs: []
prs: []
commits: []
cites: [§4.2]
related: [b-bff670, b-afec7c]
---

## Problem

Found in the spec loop's run 18, 2026-09-26, at `snapshot --new`.

`_order` in `.claude/skills/run-saffron-spec-loop/driver.py` admits a spec
refused for `depends_on` only when every entry is already in the order
(`all(d in admitted for d in spec.depends_on)`). `SA-0147` declares
`[SA-0159, SA-0138]`. `SA-0159` was in the order and `SA-0138` had merged, so
`SA-0138` was never admitted and `SA-0147` was refused. Twenty-one specs
below it went with it.

The refusal line named only `SA-0159`, which was in the order, so the output
read as a contradiction of SKILL.md step 1.

## Done looks like

- An entry the scheduler already counts as merged satisfies `_order` too.
- The refusal names the entry that kept the spec out.
- A test orders a child with one parent in the order and one merged.

## Record

- 2026-09-26: filed from the spec loop's run 18.
