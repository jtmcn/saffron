# Feedback on run-saffron-spec-loop (run 55, 2026-11-07 to 2026-11-08)

The operator set run 55 a goal: implement every backlog item. The loop ran
the queued chain in four stack batches at `--budget 550`. It also wrote seven
specs through the writer and reviewer chain. The delegate closed items by hand
in about thirty pull requests beside the batches. Five specs merged.

| Spec | PR | Outcome | Spend of budget | Peak turns of ceiling |
|---|---|---|---|---|
| `SA-0338` | #1055 | `EXHAUSTED`, adopted | $66.28 of $62 | IMPLEMENT cut at its ceiling |
| `SA-0339` | #1068 | `READY_FOR_REVIEW` | $30.80 of $58 | 98 of 300 |
| `SA-0340` | #1084 | `READY_FOR_REVIEW` | $59.82 of $72 | 280 of 330 |
| `SA-0350` | #1089 | `READY_FOR_REVIEW` | $36.43 of $52 | 163 of 230 |
| `SA-0352` | #1090 | `READY_FOR_REVIEW` | $21.06 of $56 | 124 of 230 |

Batches 69 to 72 spent $226.16 against $550 each. Finish 72's end review
lenses spent $7.13. The ledger charges finish 72's follow-up writer ($2.37)
to `SA-0352`.

Batch 72 refused seven specs before a cell. `SA-0341`, `SA-0353` and
`SA-0354` cited lines a layer below them moved. `SA-0342`, `SA-0343`,
`SA-0351` and `SA-0355` reach `SA-0341`.

## What the run found

1. **REBUT never answers a concern.** All five in-cell concerns and notes of
   batch 72 reached both PR seats unfixed. Each was a one-line comment fix
   inside `touches`. Filed as b-31e3c8.
2. **A layer's own diff moves its child's citations.** Batches 71 and 72
   refused six specs on citations that a parent layer moved. `cite` reads a
   plain line citation as ok whatever moved. A line map over the parent's
   diff found all 13 of `SA-0341`'s. Filed as b-c7858c, and b-b664d1 recurs.
3. **A form-gate failure after REBUT ends the task.** `SA-0338`'s REBUT
   fixed nine blockers and added one prose hit, and the task ended
   `EXHAUSTED`. Its five children were refused by reach. The delegate fixed
   the word and adopted the pull request.
4. **The finish minted a follow-up id `main` already held.** Finish 72's
   writer named its spec `SA-0356`, which #1085 had merged by hand. Its
   re-verify went red, and the finish pushed nothing. Filed as b-cbb6e7.
5. **The Spec seat still found witness blockers.** On #1089 one assertion
   read `done/` from a suffix and none counted the rows. On #1084 the
   tiebreak had no witness. The adequacy lens ran on both. Run 54's item 5
   recurs.
6. **By-hand merges turned two tests red only inside a cell.** #1076 and
   #1061 passed `make check` on the host and CI. A cell's PID 1 reaps
   nothing, and its checkout has no `origin`. Baseline subtraction hid both
   from every later cell until #1086.
7. **cell-watch woke the delegate falsely five times.** An orphan reap, a
   refused spec and each end review layer read as a hand-over. Filed as
   b-86d716.
8. **A stack merges only through `gh stack merge`.** `gh pr merge` and
   `gh pr edit --base` are refused for a linked stack.

## What the reviews found

- **#1084:** the seats raised 9 findings. Review commits `aea665b3` and
  `bc7d0bff` fixed 8. One needed no action. b-3df181 is kept.
- **#1089:** the seats raised 7. Review commits `a6038469` and `0ea7ff8f`
  fixed all 7. b-840763 is kept.
- **#1090:** the seats raised 5. Review commits `06dad7af` and `0f7ebb43`
  fixed all 5. b-879e72 is kept. The end review found the first fix still
  wrong.

`.saffron/rejections.md` holds fourteen lines for this run.

## Run 54's items, checked

- [ ] **A cell's own `budget_usd` binds every phase (b-d39d9a):** open, and it
  did not recur. `SA-0338` ended $4.28 over its budget.
- [ ] **A stack batch refuses an order its budget cannot run (b-fe3488):**
  open. $550 covered every order this run.
- [ ] **`check` resolves citations at the branch a batch will cut from
  (b-b664d1):** open, and it recurs as finding 2.
- [ ] **The follow-up writer validates its own spec (b-ffb930):** open. It is
  specced as `SA-0353`, which batch 72 refused. Finding 4 shows a new way the
  finish lands nothing.
- [ ] **The adequacy lens drives each member of a set a claim names:** open,
  and it recurs as finding 5.
- [ ] **A finish charges its writer to the batch, not to a layer's task:**
  open, and it recurs.

## Summary: what Saffron should absorb next

1. **REBUT answers each concern as it answers a blocker (b-31e3c8).** A phase
   change. It removes the class of fix the seats made on all three pull
   requests.
2. **A stack batch maps a child's citations through its parent's diff
   (b-c7858c).** A phase change at a layer's start, and a driver change first.
   It refused six specs this run.
3. **A form-gate failure after REBUT gets one repair turn.** A phase change.
   One word cost a five-spec chain its batch.
4. **A finish mints follow-up ids against `origin/main` (b-cbb6e7).** A phase
   change in the finish.
5. **The suite runs once in a cell before a by-hand merge.** A gate change in
   CI, or in the delegate's own check.
6. **cell-watch reads a fact for a hand-over, never a directory (b-86d716).**
   A mod change.

This PR changes no skill text.

## Next run

`SA-0341`, `SA-0342`, `SA-0343`, `SA-0351`, `SA-0353`, `SA-0354`, `SA-0355`
and `SA-0356` are queued. `SA-0353` and `SA-0354` need their `saffron/cli.py`
citations refreshed against `main` before the next batch.
