# Feedback on run-saffron-spec-loop (run 56, 2026-11-08 to 2026-11-09)

Run 56 kept run 55's goal: implement every backlog item. Batch 73 ran the
queued chain at `--budget 550` as one stack, with its end review deferred.
Six specs reached a pull request, and the delegate adopted one of them.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0341` | #1094 | `READY_FOR_REVIEW` | $28.64 of $42 |
| `SA-0342` | #1095 | `READY_FOR_REVIEW` | $51.21 of $92 |
| `SA-0351` | #1096 | `READY_FOR_REVIEW` | $52.05 of $60 |
| `SA-0355` | #1097 | `READY_FOR_REVIEW` | $17.78 of $36 |
| `SA-0353` | #1099 | `EXHAUSTED`, adopted | $53.80 of $60 |
| `SA-0354` | #1098 | `READY_FOR_REVIEW` | $13.11 of $28 |
| `SA-0359` | #1101 | `READY_FOR_REVIEW`, a finish follow-up | $4.52 of $10 |

The six cells spent $216.59 against $318 of spec budgets. Finish 73 spent
$11.23 on its end review and $4.52 on `SA-0359`'s cell, from a $137.50
reserve. Its writer sessions record no spend. It ran for five hours and ten
minutes, and the writer's send-backs took most of that.

Batch 73 refused two specs before a cell. `SA-0343` held a citation the
batch could not move. `SA-0356` reaches `SA-0353`.

## What the run found

1. **One line from REBUT ended a $53.80 task.** `SA-0353`'s REBUT fixed
   twelve adequacy blockers. Its new witness wrote `import pytest as
   _pytest`, which failed `structure` and the test that runs `structure`
   over the tree. The task ended `EXHAUSTED`, and `SA-0356` was refused by
   reach. A one-line review commit turned both gates green. b-8826cf
   recurs, in a second run running.
2. **REBUT still answers no concern.** `SA-0341`, `SA-0342` and `SA-0351`
   each reached both PR seats with a concern REBUT left standing. One sat
   in a `forbidden` ADR. b-31e3c8 recurs.
3. **The batch refused a citation its own rewrite could not place.**
   `SA-0341` added one line to `saffron/cell/session.py`. `SA-0343`'s
   citation moved by one, and the rewrite guessed a construct that held
   nothing. The refusal names a count, not the citation. b-c7858c recurs.
4. **The seats still found witness blockers the adequacy lens passed.**
   Seven of `SA-0342`'s wrong versions survived their own criterion's
   witness. `SA-0353`'s criterion 2 witness drove the reverse of its claim,
   and REBUT argued the inversion as a fix. Run 54's item 5 recurs.
5. **`prose` held three stale docstrings out of reach.** A rewrite inside a
   docstring over ten lines reads as new hits. `SA-0351`'s cell and its
   review commit both put the correction in a comment. b-ec607a reopens.
6. **A spec asked for a rename `census` refuses.** `SA-0353`'s notes named
   the new test name, and its cell kept the old one. b-f30189 recurs.
7. **`adopt` cannot re-gate a spec text the batch rewrote.** It kept
   `SA-0353` `EXHAUSTED`, and `driver.py stack` and `size` misread the
   chain. The delegate linked the stack by hand. b-619b7d and b-f10412
   recur.
8. **A gate result after REBUT names a count, not a test.** Finding
   `SA-0353`'s one red test took a suite run at the cell's head. b-66e82d
   reopens.
9. **A deferred finish ran `main`'s engine, not the stack's.** Finish 73's
   writer lacked #1099's own validation. Its drafts failed to parse three
   times and failed `prose` four times. `SA-0357` and `SA-0358` were refused
   for overlapping #1099. The finishing layer went red with one unnamed
   failure and pushed nothing. b-4a9207 and b-703e64 recur.
10. **The finish graded an adopted layer's diff as its child's.** It read
   `SA-0354` against `SA-0355`, so `SA-0353`'s diff raised eight false
   blockers. b-323c97 recurs.
11. **cell-watch ignores `stop: true`.** It answered "Watching the newest
   task" three times after the batch drained. b-2d2014 reopens.

## What the reviews found

- **#1094:** the seats raised 10 findings. Review commit `f261309e` and
  this PR's amendment to ADR 0004 fixed 8. Two needed no action.
- **#1095:** the seats raised 14. Review commit `6266888a` fixed 12. Two
  needed no action.
- **#1096:** the seats raised 9. Review commit `dc1052fa` fixed 7, some
  in comments, and three docstrings stay stale (b-ec607a). Two needed no
  action.
- **#1097:** the seats raised 2 notes. Review commit `5b00641c` fixed both.
- **#1099:** the seats raised 19. Review commits `ef7adc09` and `b360ff34`
  fixed 16. Both seats' test-name findings went to b-f30189, and one
  needed no action.
- **#1098:** the seats raised 2 notes, and neither needed a change.
- **#1101:** the seats raised 1 blocker and 4 notes. Review commit
  `e5854814` fixed all five. The witness passed a second count beside the
  right one, and the in-cell critic raised nothing.

`.saffron/rejections.md` holds eleven lines for this run.

## Run 55's items, checked

- [ ] **REBUT answers each concern as it answers a blocker (b-31e3c8):**
  open, and it recurs as finding 2.
- [ ] **A stack batch maps a child's citations through its parent's diff
  (b-c7858c):** open. The batch now moves most citations itself, and one
  still refused `SA-0343` (finding 3).
- [ ] **A form-gate failure after REBUT gets one repair turn (b-8826cf):**
  open, and it recurs as finding 1.
- [ ] **A finish mints follow-up ids against `origin/main` (b-cbb6e7):**
  open. It did not recur. Finish 73 minted `SA-0357` to `SA-0359`, and none
  was taken on `main`.
- [ ] **The suite runs once in a cell before a by-hand merge:** open. No
  by-hand merge reached a cell this run.
- [ ] **cell-watch reads a fact for a hand-over (b-86d716):** open, and it
  recurs. Finish 73's end review woke the delegate with "`SA-0354` has
  packaged, and `SA-0355` started", from a watch the delegate stopped three times.
- [x] **The follow-up writer validates its own spec (b-ffb930):** landed in
  #1099.

## Summary: what Saffron should absorb next

1. **A form-gate failure after REBUT gets one repair turn (b-8826cf).** A
   phase change. It ended a task in each of the last two runs, and each
   time the fix was one line.
2. **REBUT answers each concern as it answers a blocker (b-31e3c8).** A
   phase change. It removes the class of fix the seats made on three pull
   requests.
3. **A gate result names each new failure (b-66e82d).** A gate contract
   change. With it, `SA-0353`'s red test needs no suite run to find.
4. **`adopt` re-gates the spec text the task ran (b-619b7d).** A command
   change. An adopted layer would then join the stack as reviewable.
5. **A stack batch's citation rewrite maps lines through the parent's diff
   (b-c7858c).** A phase change. It refused `SA-0343` this run.
6. **`prose` judges a long docstring by what changed in it (b-ec607a).** A
   gate change. Stale docstrings stay stale while it holds.

This PR changes no skill text.

## Next run

`SA-0357` and `SA-0358` stay unrun, refused for overlapping #1099. Their
ids are taken in the ledger. `SA-0343` and `SA-0356` are queued. `SA-0343` needs its `session.py`
citation refreshed against `main` once this stack merges. `SA-0356` can run
once `SA-0353` merges.
