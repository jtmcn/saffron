---
id: b-db95e1
title: A spec estimated near its `size` ceiling runs unsplit, and two cells in a row landed within 25 lines of 1000
status: open
tier: 2
filed: 2026-09-22
specs: [SA-0129]
prs: []
commits: []
cites: [§5.4]
related: [b-89ec93, b-fd1468]
---

## Problem

Found in the spec loop's run 14, 2026-09-22.

`SA-0117` landed at 979 changed lines against the `refactor` ceiling of 1000.
`SA-0123`, the next spec on the same file, landed at 1001 and ended
`EXHAUSTED`. Its spec review warned that the prototype measured 865. The
delegate cut 90 lines from the spec and ran it, and the cell still crossed.

A spec's size estimate lives only in its prose notes. `driver.py check` judges
a spec's turns and budget against cells of its shape, and reads no estimate
of size. So nothing stops a spec whose own estimate sits near its ceiling.

## Done looks like

A spec can declare its estimated changed lines in its frontmatter.
`driver.py check` fails a spec whose estimate is within 20% of the `size`
ceiling for its `type`, and names the split. A spec that declares no estimate
is not refused for it.

## Record

- 2026-09-22: filed from the spec loop's run 14. The operator asked for the
  rule as a `driver.py check` command, not as writer guidance.
