# The first live stack batches, 2026-10-05

Stage 2 of `docs/superpowers/plans/2026-10-03-delegate-loop-onto-the-stack-batch.md`.
Two `saffron batch --stack` runs took four specs, attended. Batch 13 ran
`SA-0208` and `SA-0205`. Batch 14 ran `SA-0206` and `SA-0207`, after the
operator merged batch 13's stack.

## The batches

| Batch | Window | Budget | Spent | Exit |
|---|---|---|---|---|
| 13 | 13:02 to 16:06 | $270 | $51.96 | 0, `DRAINED` |
| 14 | 17:23 to 20:06 | $142 | $43.45 | 0, `DRAINED` |

| Spec | Batch | Outcome | PR | Spent / budget |
|---|---|---|---|---|
| `SA-0208` | 13 | `READY_FOR_REVIEW` | #687 | $11.61 / $14 |
| `SA-0205` | 13 | `READY_FOR_REVIEW` | #689 | $37.08 / $34 |
| `SA-0206` | 13 | `GATE_ERROR` at seeding | none | $0.00 |
| `SA-0207` | 13 | refused, its parent missed | none | none |
| `SA-0206` | 14 | `READY_FOR_REVIEW` | #696 | $27.31 / $34 |
| `SA-0207` | 14 | `READY_FOR_REVIEW` | #697 | $12.23 / $21 |

Each task's spend includes its in-batch spec review. `SA-0208`'s took 84
turns and $3.77. `SA-0205` ran past its budget in REBUT, which `SA-0203` allows.

The end reviews cost $3.27 and $3.91. One lens in batch 13 was cut by the
900-second wall with no output and recorded $0.00, which is b-209696 live.

## ADR 7's two measures

Neither has a value. Both end reviews produced no qualified finding, so no
follow-up was written. The share of follow-ups that reach `READY_FOR_REVIEW`
with a clean critic, and the spend per follow-up, have nothing to count.

The ledger's stack tables after both batches:

| Table | Rows |
|---|---|
| `spec_reviews` | 5 |
| `spec_texts` | 0 |
| `stack_layers` | 4 |
| `end_reviews` | 10 |
| `qualifications` | 0 |
| `stack_finishes` | 0 |

`stack_finishes` stayed empty because both finishes escalated.

## Steps that needed a hand

1. **The budget.** The settled rule was total over 0.75. `--stack` holds back
   two quarters, the end review's and the follow-up writers'. The delegate
   read that in `saffron/cli.py`, and the operator chose total plus spec
   review, over 0.5.
2. **Both finishes.** Each finishing commit moved the layers' specs to
   `done/` and closed no origin item. The records test turned red, so each
   finish linked nothing and pushed nothing. The delegate linked both stacks.
3. **Batch 13's third layer.** `SA-0206`'s spec-review cell failed to seed
   (b-6ac0cd), and `SA-0207` was refused as its descendant.
4. **The second batch.** It could not stack on batch 13's unmerged layers.
   The operator merged #692 first.
5. **Watching.** `saffron watch` showed nothing during a spec review (b-4e1b6d).

## Seats beside the end review

The end review raised nothing on any layer. The seats ran on every layer PR,
as stage 3 says. Each blocker was verified with `driver.py probe`.

| PR | Seat blockers | End review raised it | Fixed |
|---|---|---|---|
| #687 | 0, one concern a fixture could not see | no | yes |
| #689 | 2 witness holes | no | yes |
| #696 | 1 witness hole | no | yes |
| #697 | 1 witness hole | no | yes |

The seats found four blockers and one concern the end review missed. So the
retirement test fails for both batches, and the seats stay.

## Defects the batches found

Each is a backlog record in this pull request. b-6ac0cd gained a second
measured case.
