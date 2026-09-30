---
id: b-91ead2
title: driver.py labels reads no cell round, and jev writes cell rounds outside spec-loop
status: open
tier: 3
filed: 2026-09-29
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Run 21's feedback named this, and run 22 met it again.

`driver.py jev --kind cell` writes its round beside the cell's batch folder,
under `~/.saffron/batches/v0/SA-NNNN/`. Every other kind writes under
`~/.saffron/batches/spec-loop/`. The labelling step then put run 22's three
cell labels under `spec-loop/SA-NNNN/cell/round-1/`, away from the
`findings.json` they label. `driver.py labels` reads spec-review and
pr-review rounds only, so nothing checks those three files.

## Done looks like

A cell round lives under `spec-loop/` like the rest, and `driver.py labels`
exits 1 on a scored cell round with no `labels.json`.

## Record

- 2026-09-29: filed from the spec loop's run 22.
