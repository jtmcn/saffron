# Spec chain feedback, 2026-09-26: splitting SA-0147 after its plan was refused

The spec loop's run 19 started `SA-0147`'s cell. The cell ended
`PLAN_REJECTED` after $2.84 and 41 turns. Its plan priced 5800 changed
tokens against the `feature` ceiling of 3000. `saffron/ledger.py` and
`saffron/cell/session.py` are in `elevate_on`, so `size` blocked the plan.
The spec declared no `estimated_lines`, so `driver.py check` had nothing to
price before the cell.

The operator chose a split. The writer and reviewer agents then produced four
specs in one chain: `SA-0178`, `SA-0179`, `SA-0180` and a rescoped `SA-0147`.
`SA-0147` keeps its id last, so the thirteen queued specs that cite it need
no edit.

## Rounds and cost

| Step | Wall time | Result |
|---|---|---|
| Writer, first split | 23 min | three specs, `SA-0147` still at 93% |
| Writer, join split off | 17 min | `SA-0180` at 84% |
| Writer, in-cell concerns moved | 25 min | `SA-0180` 79%, `SA-0147` 33%, measured |
| Review round 1, four in parallel | 2 to 8 min each | no blocker, nine concerns |
| Writer, round 1 answered | 9 min | every concern applied and measured |
| Review round 2, four in parallel | 2 to 4 min each | no blocker, four concerns |
| Writer and delegate, round 2 answered | 7 min | applied, the grouping case measured |

The operator answered two size questions on the way. Each split was priced
from a prototype built at the base with `size_gate`'s own counter, times
1.4 for the sibling overrun.

## Findings by class

| Class | Round | Spec | Check that should have caught it |
|---|---|---|---|
| A wrong build passes the arrangement | 1 | `SA-0178` x1, `SA-0179` fold, `SA-0147` unreached layer | pre-flight 1 |
| A comment the change makes false | 1 | `SA-0178` `session.py:1327` | pre-flight 6 |
| A helper one spec defines and the next reshapes | 1, 2 | `SA-0180` run parameter, then grouping | none |
| Placeholders a dataclass requires | 1 | `SA-0180` `CellSpec` | pre-flight 3 |
| A delegate edit that broke a neighbour | 2 | `SA-0178` mutant, `SA-0147` TE-0 | none |

Two classes are new to the split.

- **The seam between split specs.** The writer's prototype shared one
  helper across `SA-0180` and `SA-0147`, so it never saw that `SA-0180`'s
  text described the helper too narrowly for `SA-0147`'s join. Round 1 found
  the missing run parameter. Round 2 found that grouping per call would give
  two groups for one file. A split should name each seam's parameters and
  return value in the earlier spec.
- **A mutant in a forbidden file.** Round 1 suggested declaring a mutant on
  `review.adequacy_probes`. Round 2 found that `revert` exempts a witness
  whose mutant's file the diff never touches. The mutant then trades
  `revert`'s verdict for `witness`'s. The delegate removed it.

## Not settled

- `SA-0180` prices at 79% at 1.4 times and 90% at 1.6 times. It runs at
  `standard`, where `size` only advises.
- Round 2's fixes were not reviewed a third time. The stop rule is two
  rounds, and each fix was measured in the prototype.
