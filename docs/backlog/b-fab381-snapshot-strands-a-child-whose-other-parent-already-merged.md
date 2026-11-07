---
id: b-fab381
title: The spec loop's `snapshot` strands a child whose other parent already merged, so one refusal cuts a chain
status: partial
tier: 2
filed: 2026-09-26
specs: []
prs: [917]
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
- 2026-10-09: recurred in the spec loop's run 32. The snapshot again
  stranded six children whose other parent merged.
- 2026-10-10: recurred in the spec loop's run 33. `SA-0248` names `SA-0244`,
  in the order, and `SA-0237`, merged, so the snapshot left out it and its
  child `SA-0249`. `--force --add` refused both as not new, and `record`
  refused both as not in the order. The batch ran them as #801 and #802.
- 2026-11-07: groomed. `a345fa7c` (#917) counts a parent in `done/` as met in `_order`. A test orders a child with one parent in the order and one merged. The refusal line still prints the scheduler's own reason. It can name a parent in the order and not the entry that kept the spec out.
