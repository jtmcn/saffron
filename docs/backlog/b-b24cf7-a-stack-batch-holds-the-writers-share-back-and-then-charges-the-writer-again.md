---
id: b-b24cf7
title: A stack batch holds the spec writer's share back, then charges the writer again, so a spec can only be revised under a budget twice its cost
status: done
tier: 1
filed: 2026-10-15
closed: 2026-10-16
specs: [SA-0273]
prs: [880, 886]
commits: []
cites: [§4.2.1]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 40.

Batch 32 ran at $134 with `--stack`. The spec review found a blocker in
`SA-0273` and asked for a revision. The batch refused it:
`SA-0273 unrevised needs 71.500, 64.680 left`. No cell ran.

The check is in `saffron/batch.py`. A revision needs the writer session, a
review session and the spec's own budget, which is $71.50 for a $45 spec. The
money left is the budget minus `reserve_usd`, minus `writer_usd`, minus what
the batch spent. Each share is a quarter of `--budget`
(`_stack_admission_shares`). So the writer's share is held back from the
check that pays the writer.

A spec costing `B` can be revised only when the budget is at least
`2B + 53` plus twice the spend. At $134 a $45 spec could never be revised.
Run 39 at $72 had the same shape for its $36 spec. The delegate fixed the
spec by hand in #880 and reran at $148.

## Done looks like

The revision check draws on the writer's share it holds back, not on top of
it. A batch sized at twice its specs' budgets can revise any one of them.

## Record

- 2026-10-15: filed from the spec loop's run 40.
- 2026-10-16: closed by hand. The operator chose that a revision draws on the
  writer's share. Spec writing now leaves the share as it spends, so a later
  cell and the follow-up writer see only what is left.
