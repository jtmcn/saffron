---
id: b-c94a2f
title: A second `depends_on` entry orders a spec but carries no code into its cell, and nothing says so
status: open
tier: 2
filed: 2026-10-03
specs: [SA-0199]
prs: [657]
commits: []
cites: [§4.2]
related: [59, b-877e93]
---

## Problem

Found at step 1b of the spec loop's run 27.

`SA-0199` declared `depends_on: [SA-0198, SA-0197]`. A cell is cut from
`depends_on[0]` alone (`saffron/task.py`, `_resolve_stacked_on`, K=1). Its tree
would have held `SA-0198`'s code and not `SA-0197`'s, though both edit
`saffron/cli.py`. The spec chain added the second entry to order the two
specs, and no reviewer or check noticed it carried no code.

The overlap refusal walks `depends_on[0]` alone as well
(`scheduler._ancestor_branches`). So on a plain night `SA-0197`'s open pull
request refuses `SA-0199` for `open_pr_overlap`. A dead `SA-0197` refuses it
outright. The operator chained the three specs instead (#657).

## Done looks like

Intake refuses a spec with more than one `depends_on` entry, naming K=1. Or
the spec-reviewer's check 3 reports a second entry and asks whether the spec
needs that parent's code.

## Record

- 2026-10-03: filed from the spec loop's run 27.
