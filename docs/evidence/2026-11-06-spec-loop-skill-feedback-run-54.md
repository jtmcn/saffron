# Feedback on run-saffron-spec-loop (run 54, 2026-11-05 to 2026-11-06)

Run 54's order was `SA-0334`, then `SA-0335` and `SA-0336` stacked on it,
then `SA-0337` with no parent. The specs carried $185 of budget. All four
cells reached `READY_FOR_REVIEW`, and the four pull requests are one linked
stack, reviewed and marked ready.

| Spec | PR | Outcome | Spend of budget | Peak turns of ceiling |
|---|---|---|---|---|
| `SA-0334` | #1024 | `READY_FOR_REVIEW` | $28.43 of $46 | 134 of 235 |
| `SA-0335` | #1025 | `READY_FOR_REVIEW` | $80.11 of $69 | 338 of 360 |
| `SA-0336` | #1026 | `READY_FOR_REVIEW` | $21.66 of $40 | 131 of 200 |
| `SA-0337` | #1027 | `READY_FOR_REVIEW` | $27.07 of $30 | 70 of 150 |

Batch 67 ran at $230 and stopped on `BUDGET` after two specs. Batch 68 ran at
$172, finished `SA-0336`, and refused `SA-0337` on a citation. `SA-0337` then
ran as a single cell from `main`. The two finishes spent about $9.86 on end
review lenses and the follow-up writer. The run spent about $167 in all.

The ledger charges finish 67's writer ($2.24) to `SA-0334`, so `record` reads
$28.43 and the ledger's attempts sum to $30.67.

## What the run found

1. **A cell spent past its own budget, and the overrun stopped the batch.**
   `SA-0335` reached $76.77 against $69 during REVIEW and REBUT. Nothing
   checked its ceiling once IMPLEMENT ended. Filed as b-d39d9a.
2. **The delegate proposed a budget the order could not use.** A stack batch
   holds half of `--budget` for the reserve and the writer. $230 gave cells
   $115 for an order that needed $434. `saffron batch` printed no admission
   line and started anyway. Filed as b-fe3488, beside b-2f4746.
3. **A batch refused a spec whose citations `check` passed.** `check` ran
   `cite` at `origin/main`. Batch 68 cut `SA-0337` from `SA-0336`'s head,
   where two `ledger.py` citations had moved. b-b664d1 recurs.
4. **The finish's follow-up never landed a one-line fix.** Finish 67 found a
   stale docstring line on #1024. The writer's first draft emitted
   `wrong_versions` as objects and did not parse. The second failed `prose`
   and was pooled. The delegate fixed the line by hand. Filed as b-ffb930, and
   b-4a9207 and b-01c53d recur.
5. **The Spec seat still found a witness blocker on two of four pull
   requests.** On #1024 the witness for "no argv names the origin" checked
   only for `fetch`. On #1027 the live ref held no `task_state`, so a top-up
   refusing every multi-state ref passed. Each is a member of a set the claim
   named and the witness never drove. The in-cell adequacy lens ran on both.
6. **A cell's proxy denied 16 CONNECTs to github.com.** Both seats showed that
   no git call in the suite made them. Their source is unknown. Filed as
   b-71f95f.
7. **The Spec seat measured `SA-0337` against the live record.** Against
   copies of the ledger and the mirror, #1027's `migrate` takes all 376 refs
   and refuses none, and the fold succeeds. The operator still owes the rerun
   of `saffron migrate` after #1027 merges.

## What the reviews found

- **#1024:** the seats raised 9 findings. Review commits `b0faa32f` and
  `4321ba68` fixed 6. One needed no action, and 2 are b-0add4c and b-25c0f5.
- **#1025:** the seats raised 7. Review commit `fecc61f0` fixed 3. One was an
  equivalent mutant, one needed no action, and 2 are b-25c0f5.
- **#1026:** the seats raised 5. Review commit `b9071998` fixed 4. One is
  b-980fbd.
- **#1027:** the seats raised 7. Review commit `535dc706` fixed 6, and one copy
  stays as an independent oracle.

`.saffron/rejections.md` holds twelve lines for this run.

## Run 53's items, checked

- [ ] **A survived mutant tells REPAIR which part of its claim went untested
  (b-fa4a83):** open. It did not recur, since every cell passed `witness`.
- [ ] **A by-hand merge satisfies a child's `depends_on` (b-bece8b):** open.
  It did not recur.
- [ ] **A lost connection never decides a task (b-f011f3):** open. It did not
  recur.
- [ ] **A gate checks the spec ids a diff cites (b-249808):** open. No cell
  cited a wrong spec id.
- [ ] **An adopted task is a layer of its batch (b-323c97):** open. Nothing
  was adopted.
- [ ] **The adequacy lens runs on a diff the cell could not finish:** open.
  Every cell finished, so every lens ran. Finding 5 shows the lens misses the
  set-member class even when it runs.
- [ ] **`record` prints the spec review's findings:** open. The seats' briefs
  again carried no batch spec review.
- [ ] **`record` and the ledger agree on a task's spend:** open, and it
  recurs. The finish's writer spend lands on a layer's task.

## Summary: what Saffron should absorb next

1. **A cell's own `budget_usd` binds every phase (b-d39d9a).** A phase change.
   It cost two of four specs their batch and a second batch.
2. **A stack batch refuses an order its budget cannot run (b-fe3488).** A gate
   change at batch start. With 1, it would have let one batch run all four.
3. **`check` resolves citations at the branch a batch will cut from
   (b-b664d1).** A driver change today and a gate later. It cost a single
   cell and left `SA-0337` a sibling of the stack.
4. **The follow-up writer validates its own spec (b-ffb930).** A phase change
   inside the writer's session. The finish has now landed no follow-up in
   four runs.
5. **The adequacy lens drives each member of a set a claim names.** A lens
   change. It is the class behind finding 5 and run 53's six blockers.
6. **A finish charges its writer to the batch, not to a layer's task.** A
   ledger change. It keeps `record` and the ledger in agreement.

This PR changes no skill text.

## Next run

Nothing is queued. After #1027 merges, the operator reruns
`saffron migrate --from ~/.saffron/ledger.db` to repair the 35 refs the last
run refused. Nothing rebuilds the ledger from the record before then.
