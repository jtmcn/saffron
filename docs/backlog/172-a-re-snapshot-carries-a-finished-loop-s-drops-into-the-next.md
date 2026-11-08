---
id: 172
title: A re-snapshot carries a finished loop's drops into the next, and nothing undoes a drop
status: done
closed: 2026-11-07
tier: 2
filed: 2026-09-17
by_hand: true
specs: []
prs: [326, 1049]
commits: []
cites: []
related: [137]
---

## Problem

Found starting the spec loop's run 6, 2026-09-17. `driver.py snapshot --force`
ran over run 5's order. It listed `SA-0096`, `SA-0097` and `SA-0098` as
dropped, each with run 5's reason:

```
queued after this loop's snapshot; operator kept the loop to the SA-0093 chain (2026-09-16)
```

That reason was true of run 5 only, and run 5's pull requests had all merged.

`_carried` (`.claude/skills/run-saffron-spec-loop/driver.py`) keeps every row
with `p.dropped` set, and `drop` has no inverse. The way out was moving
`.saffron-loop/order.json` aside and running a plain `snapshot`. The skill's step
1 says "an existing order is kept until `snapshot --force`", which reads as the
command to start a new loop with.

## Done looks like

`snapshot` refuses an order whose every reviewable pull request is merged or
closed, and says to start fresh with `--new`. Or `_carried` forgets a drop
recorded before the order's own snapshot. An `undrop` command covers a spec
dropped by mistake.

## Record

- 2026-11-07: the new-loop half is done. #326 (`8bfb8512`) added
  `snapshot --new`, which carries no drops and refuses while the last loop has
  an open pull request. A bare `snapshot` over an existing order now names
  `--new`, and the skill's step 1 says a new loop starts with it.
- Left: nothing undoes a drop. The driver has no `undrop`, and
  `snapshot --force` still carries a drop forward through `_carried`.
- 2026-11-07: marked by hand in grooming. The work is in the spec loop's driver under
  `.claude/`, and `SA-0279` refuses any spec that touches that path.
- 2026-11-07: done by hand in #1049.
