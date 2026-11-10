---
id: b-fe3488
title: "`saffron batch --stack` starts an order its budget cannot run, and prints no admission line"
status: open
tier: 2
filed: 2026-11-06
specs: [SA-0361]
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
- 2026-11-09: recurred in the spec loop's run 57. Batch 74 ran `--budget 120` for `SA-0343` ($52) and `SA-0356` ($30), so tasks got $60. `SA-0343` spent $52.44, and the batch ended `BUDGET` before `SA-0356`. A second batch, with its own reserve and finish, ran `SA-0356`. Specced as `SA-0361`.
- 2026-11-09: `SA-0361` refuses below the queue's printed total, not below the last layer's threshold. Between the two every layer starts, and the last spec review spends into the reserve and the writer's share. Whether those shares are a floor is b-2f4746's open question. So the delegate took the arm that keeps them whole, and `--partial` overrides it.
