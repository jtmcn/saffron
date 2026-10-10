---
id: b-20043f
title: A spec's notes can ask for work no criterion declares, and nothing notices it missing
status: open
tier: 2
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-bf0c91, b-43a061]
---

## Problem

Found in the spec loop's run 19, 2026-09-27.

`SA-0169`'s notes asked for a cell-marked test of about 600 tokens. The wall
cut its IMPLEMENT session (b-bf0c91), and the salvage turn committed no test.
No gate or lens noticed. The test was no criterion, and `pytest -m cell` is
deselected by default.

The pull request (#550) landed 304 changed tokens against the 935 the writer
measured. The Spec seat found the gap, and a subagent wrote the test in
review. A landed size far under the spec's own estimate was the one signal,
and nothing reads it.

## Done looks like

`size` or `criteria` reports a landed size under a floor of the spec's
`estimated_lines`. Or the spec writer turns each request in the notes into a
criterion. A test holds the floor.

## Record

- 2026-09-27: filed from the spec loop's run 19.
- 2026-10-03: seen again in the spec loop's run 27. `SA-0199`'s witness notes
  asked criterion 4's test for the nine rows whole, a no-change call on repo `r`
  and an existing empty directory. The cell (#670) dropped all three, and no gate
  or lens noticed. #670's Spec seat found each as a surviving wrong build.
- 2026-10-10: recurred in the spec loop's run 33. Seats found a witness that
  missed part of its claim on #793, #794, #795, #796, #799, #800 and #801,
  each after the in-cell critic.
