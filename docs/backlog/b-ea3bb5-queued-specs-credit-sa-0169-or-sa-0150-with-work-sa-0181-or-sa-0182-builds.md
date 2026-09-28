---
id: b-ea3bb5
title: Queued specs credit `SA-0169` or `SA-0150` with work `SA-0181` or `SA-0182` now builds
status: open
tier: 3
filed: 2026-09-27
closed:
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 19, 2026-09-27, in the round-1 reviews of #547.

#547 split `SA-0181` from `SA-0169` and `SA-0182` from `SA-0150`. Later specs
still credit the old spec. Line numbers are at `b502abf4`.

- `SA-0182`'s `spec_texts`, `record_spec_text` and `spec_text` are credited to
  `SA-0150` at `SA-0151:157`, `SA-0160:236`, `SA-0161:168`, `SA-0162:237`,
  `SA-0164:212` and `:289`, `SA-0173:103` and `:130`, and `SA-0174:160`.
- `SA-0181`'s unprivileged account is credited to `SA-0169` at
  `SA-0175:230-232`. The chain lists at `SA-0175:215-217`,
  `SA-0156:139-141`, `SA-0160:205` and `SA-0176:158` leave out `SA-0181`.

Each tree base includes both new specs, so no witness breaks. `SA-0175` and
`SA-0156` ran in run 19 and are in `done/`.

## Done looks like

Each queued spec credits the spec that builds the name.

## Record

- 2026-09-27: filed from the spec loop's run 19.
