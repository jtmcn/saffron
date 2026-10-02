# Spec chain feedback, 2026-10-01: SA-0177 revised in loop run 25

Run 24 handed `SA-0177` over with a parent-branch review at `fcc37bed`, the
head of #630. That review found two blockers. Run 25 revised the spec after
#630 merged, so the base is `main` at `4e8dd982`.

## What the operator settled

- The write stamps the fact's `batch_key` from the selected layer, with
  `dataclasses.replace`. It adds no `_apply` refusal of a `None` batch key.
- The declared wrong versions stay near seven. Other wrong builds go to a
  step 1b list in the notes.

## Rounds

| Round | Base | Blockers | Concerns | Notes | Fixed by |
|---|---|---|---|---|---|
| 2, parent branch | `fcc37bed` | 1 build, 1 witness | 2 | 3 | writer |
| 3 | `a2c9b2c6` | 1 witness | 1 | 2 | delegate |
| 4 | `c1cac147` | 0 | 1, the planned step 1b run | 3 | delegate |

## Each finding by class

- **Build: the fact's batch came from the task's run.** This is a data-flow
  finding, and pre-flight check 4 should catch it. The source is
  `_build_fact`'s run, and a fold can re-hang that run. No pre-flight ran on
  the parent's merged code, because the parent had not merged.
- **Witness: the top of two layers was also the first by id and recording.**
  This is a set member left undriven, so pre-flight check 1 applies. The spec
  argued the arrangement and did not work it.
- **Witness: no step read the record after the last write.** This is check 1
  again. The claim spans two sets, the row and the fact. The last step drove
  only the row.
- **Concern: a sentence said every ledger test shares one `base_sha`.** This
  is a claim about the tree, so check 5 applies. One grep refutes it.
- **Notes: the fact's order, each task's key and the third path were left
  to the cell.** No check covers these. Each one costs a repair turn and
  never a wrong build.

## Measured

`measure-177/picks.py` ran at `4e8dd982`. Only `ORDER BY sl.position DESC`
reaches the top layer. A plain scan reads `stack_layers` and picks the first
recorded layer. The re-fold hangs all four tasks on run 1, which belongs to
`b1`. The output is in the run 25 summary.

## SA-0167, revised in the same run

`SA-0167` had no review in run 24. Its first round ran at `main`, before its
parent existed. The second ran at the parent's pushed branch.

| Round | Base | Blockers | Concerns | Notes | Fixed by |
|---|---|---|---|---|---|
| 1, at `main` | `4e8dd982` | 1 witness | 4 | 5 | writer (#635) |
| 2, parent branch | `61231745` | 1 witness | 1 | 2 | delegate (#637) |
| 3 | `61231745` | 0 | 1 | 1 | delegate (#637) |
| 4 | `4e66195d` | 0 | 0 | 0 | none |

Every finding that changed the spec was one class, a set the witness drove
one member of. That is pre-flight check 1, the largest class in the corpus:

- the commit line matched as a substring, which passes the old line;
- the publish raise driven with only the two types a narrow catch names;
- the policy checked on `protected` alone, which passes a build that keeps
  the suppression scan.

One concern rested on a false premise. It said the cell image runs git
2.39.5. The image runs 2.47.3. Both that git and the host's reject an
empty-expect lease on an existing branch with `stale info`
(`measure-167/lease.sh`).
