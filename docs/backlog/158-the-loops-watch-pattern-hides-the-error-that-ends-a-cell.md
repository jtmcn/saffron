---
id: 158
title: The spec loop's watch pattern shows a cell's teardown and hides the error that ended it
status: open
tier: 2
filed: 2026-09-16
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [139]
---

## Problem

**Tier 2.** By hand: `driver.py pattern` is the skill's. Found in the spec
loop's run 5, 2026-09-16.

`SA-0093`'s second cell died at REVIEW on
`saffron: CellRuntimeError: container network create … failed: Error: invalid
network name: saffron-gate-net-SA-0093`. The Monitor built from `pattern`
showed the implementer's notes, then
`teardown: network saffron-gate-net-SA-0093 survived — Error: failed to delete
one or more networks`, then `teardown`. It never showed the line that said what
went wrong, because `saffron:`-prefixed error lines are not in the pattern.
The survival line read as the cause, and the real cause took a log read to
find. Every Monitor after that was armed with `|^saffron: ` added by hand.

## Done looks like

`pattern` matches the CLI's own error line, and a test holds it to what
`saffron/cli.py` prints when a cell raises.

## Record

**Filed 2026-09-16** from the spec loop's run 5 (stack #308).
