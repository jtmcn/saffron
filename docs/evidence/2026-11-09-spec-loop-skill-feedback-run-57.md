# Feedback on run-saffron-spec-loop (run 57, 2026-11-09)

Run 57 kept the goal of runs 55 and 56: implement every backlog item. It ran
the two specs run 56 left queued, in two batches, as one stack of two.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0343` | #1106 | `READY_FOR_REVIEW`, batch 74 | $52.44 of $52 |
| `SA-0356` | #1107 | `READY_FOR_REVIEW`, batch 75 | $21.35 of $30 |

The two cells spent $73.79 against $82 of spec budgets. Batch 74 ran at
`--budget 120` and batch 75 at `--budget 80`. Both deferred their end
review. Finish 74 holds a $30 reserve and finish 75 holds $20. Each finish
runs after this stack merges, so it runs the stack's own engine (b-4a9207).

Before the batches, #1103 refreshed six citations in the two specs by hand.

## What the run found

1. **The spec that caps REVIEW's spend overran its own budget.** `SA-0343`
   spent $52.44 of $52. REVIEW raised five adequacy blockers, and REBUT
   answered all five. #1106 caps REVIEW alone, so REBUT's half of b-d39d9a
   stays open.
2. **The delegate sized batch 74 below its order.** `--stack
   --defer-end-review` gives tasks half of `--budget`. At $120 that left $60,
   so `SA-0356` met $10.35 and the batch ended `BUDGET`. The batch printed
   the split before its first cell. Nothing refused an order the task share
   could not hold. A second batch cost a second reserve and a second finish.
3. **REBUT still answers no concern.** Each cell left one conventions
   concern standing. #1106 wrote a bare "pool", and #1107 called a miss a
   "missed layer". Both seats raised each one again. b-31e3c8 recurs.
4. **The seats found witness blockers after every lens withdrew.** `SA-0343`'s
   criterion 1 witness never read `wrong-versions.json`. Its criterion 2
   witness checked three caps of thirteen. Five wrong versions survived.
   Run 54's item 5 recurs.
5. **An adequacy probe that changes nothing cost a REBUT turn.** The probe
   at `saffron/batch.py:1042` filtered an id `_drive` had already excluded.
   It stayed green because it was inert. REBUT spent $4.74 answering it and
   one other blocker.
6. **The spec carried a word `CONTEXT.md` rules out.** `SA-0356`'s criterion
   2 said "missed layer". The cell copied it, and `terms` passed it.
7. **`record` read a branch it had not fetched.** It printed "the branch's
   copy is unreadable" for `SA-0356` and recorded the outcome anyway.
8. **cell-watch ignores `stop: true`.** It answered "Watching the newest
   task" after batch 75 drained. b-2d2014 recurs.

## What the reviews found

- **#1106:** the seats raised 2 blockers, 2 concerns and 4 notes. Review commit `0fabc377` fixed all 8. One test name in
  a `forbidden` file still names the deleted `critic_budget`. It went to
  b-d39d9a.
- **#1107:** the seats raised 1 concern and 4 notes. Review commit
  `8e2d4d02` fixed the 3 on the "missed layer" phrase. The 2 on
  `_print_stack_admission` went to b-d1c277, since `saffron/cli.py` was
  `forbidden`. Every wrong version was killed.

`.saffron/rejections.md` holds three lines for this run.

## Run 56's items, checked

- [ ] **A form-gate failure after REBUT gets one repair turn (b-8826cf):**
  open. It did not recur.
- [ ] **REBUT answers each concern as it answers a blocker (b-31e3c8):**
  open, and it recurs as finding 3.
- [ ] **A gate result names each new failure (b-66e82d):** open. No red
  gate needed a suite run to find this run.
- [ ] **`adopt` re-gates the spec text the task ran (b-619b7d):** open. No
  task was adopted this run.
- [ ] **A stack batch's citation rewrite maps lines through the parent's
  diff (b-c7858c):** open. `SA-0343` waited a run for it, and #1103 moved
  its citations by hand.
- [ ] **`prose` judges a long docstring by what changed in it (b-ec607a):**
  open. It did not recur.
- [x] **A batch passes over a candidate its budget cannot cover
  (b-f73cd0):** landed in #1107.

## Summary: what Saffron should absorb next

1. **REBUT answers each concern as it answers a blocker (b-31e3c8).** A
   phase change. It recurred on both pull requests this run.
2. **REBUT draws from REVIEW's pool (b-d39d9a).** A phase change. `SA-0343`
   overran its budget during REBUT, and #1106 left that half open.
3. **A batch refuses an order its task share cannot hold.** A command
   change. Batch 74 printed the split and then ran into it.
4. **A form-gate failure after REBUT gets one repair turn (b-8826cf).** A
   phase change. It ended a task in each of runs 55 and 56.
5. **A stack batch's citation rewrite maps lines through the parent's diff
   (b-c7858c).** A phase change. It cost `SA-0343` a run.

This PR changes no skill text.

## Next run

The queue is empty. Finish 74 and finish 75 run once this stack merges. New
specs come from the backlog through `create-saffron-spec`, under #1104's
chain.
