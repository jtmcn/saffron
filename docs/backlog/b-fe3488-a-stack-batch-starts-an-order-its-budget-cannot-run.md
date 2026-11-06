---
id: b-fe3488
title: "`saffron batch --stack` starts an order its budget cannot run, and prints no admission line"
status: open
tier: 2
filed: 2026-11-06
specs: []
prs: []
commits: []
cites: [§7.1]
related: [b-2f4746]
---

## Problem

Found in the spec loop's run 54.

The delegate proposed `--budget 230` for four specs carrying $185. A stack
batch holds 25% for its reserve and 25% for the writer, so $115 reached
cells. `saffron queue --stack` prints a $434 total for that order. `saffron
batch` printed no admission line. It ran two specs and stopped with
`batch: BUDGET`, and a second batch at $172 ran the rest.

## Done looks like

`saffron batch --stack` prints the admission lines `saffron queue --stack`
prints. It refuses to start when its budget admits fewer candidates than the
order holds, unless told to run a prefix.

## Record

- 2026-11-06: filed from the spec loop's run 54.
