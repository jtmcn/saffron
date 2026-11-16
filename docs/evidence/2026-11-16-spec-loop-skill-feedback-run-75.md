# Feedback on run-saffron-spec-loop (run 75, 2026-11-16)

Run 75 kept the goal of runs 55 to 74: implement every backlog item. It took
`SA-0401` and `SA-0402`, the two halves of b-9efbe2 that run 73 wrote.

| Spec | PR | Outcome | Spend of budget | Turns of ceiling |
|---|---|---|---|---|
| `SA-0401` | #1232 | `READY_FOR_REVIEW` | $15.47 of $30 | 164 of 150 |
| `SA-0402` | #1233 | `READY_FOR_REVIEW` | $30.20 of $48 | 387 of 200 |

Batch 93 ran at `--budget 188` with `--stack --defer-end-review`. It held a
$47 reserve. Finish 93 spent $4.47 on the end review, committed nothing and
ran no follow-up. The run spent about $50.14 of $188. Turns count every
phase.

## What the run found

1. **Both cells passed REBUT, and both PRs still held a blocker.** Each Spec
   seat found a witness that reads only part of what its claim names.
   `SA-0401`'s witness let a copied recorded reason pass, and it named an
   entry witness without its file. `SA-0402`'s witness read the record field
   by field, so dropped fields and a reversed order passed. This is the class
   runs 13 to 74 keep naming.
2. **REBUT's fixes held up under the seats.** The host filed three blockers
   on `SA-0401` and two on `SA-0402`. REBUT fixed four and argued one. The
   `SA-0402` seat checked that the new outcome assertion kills every wrong
   mapping, not only the one probed.
3. **Finish 93 graded three findings REBUT had already fixed.** All three
   read `unverified`, since their lines moved. The end review gets the
   cell's own concerns again and cannot tell them from open ones.
4. **`cite` found two stale citations before the batch.** The refresh needed
   its own spec PR, #1231. The classifier denied that push until the operator
   approved it in chat. A refresh `cite` can compute still needs a person.
5. **Batch admission refused $140.** It wanted its own printed total of $188,
   which carries the reserve. The skill text does not say to read that total.
6. **`SA-0402` built on `SA-0401`'s cell head.** `SA-0401`'s review commit
   waited for that cell to exit, then `SA-0402` rebased onto it cleanly. The
   `SA-0402` seat flagged an unguarded call that only the rebase closed.
7. **Seat prompts and report saving stayed hand steps.** The helpers from run
   74 survived, since no reboot hit this run.

## What the reviews found

- **#1232:** the witness let a copied reason and a bare entry witness pass.
  `names_file` read a non-ASCII letter as a path's end. A refused diff raised
  out of the module. Notes covered a stale comment, an _Avoid_ word and a
  wrong `§3.2` cite. All were fixed.
- **#1233:** the witness read the record field by field. Four notes covered a
  stale docstring, "errored", a comment pointing up and a split name. All
  were fixed, and each surviving edit now fails the witness.

`.saffron/rejections.md` holds five lines for this run. b-9efbe2 closes. Its
review-commit half is filed as b-d9a027.

## Run 74's items, checked

- [ ] **A wrong version's edit changes only the case it names:** open, on
  b-f06097.
- [x] **A later commit reruns recorded wrong versions:** the cell half landed
  in `SA-0401` and `SA-0402`. The review-commit half moved to b-d9a027.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.
- [ ] **A finish prices a follow-up's ceilings from past follow-ups:** open,
  with no item. Finish 93 ran no follow-up.
- [ ] **`driver.py check` refuses a spec body that quotes a mutant's
  `find`:** open, on item 080.
- [ ] **The driver fills the seat prompts and saves the reports:** open,
  with no item. Item 7 did both by hand.
- [ ] **`cite` flags a bare citation into a parent's changed file:** open,
  the other half of b-b664d1.
- [ ] **`driver.py stack` links a finish's layer:** open, with no item.
  Finish 93 had no layer.
- [ ] **`bookkeeping` runs the smoke test's flat corpus:** open, with no
  item. This run's retirement needed no change, so it went unexercised.

## Summary: what Saffron should absorb next

1. **A wrong version's edit changes only the case it names.** A phase
   change, on b-f06097.
2. **`regate` asks the recorded wrong versions of a review commit.** A gate
   change, on b-d9a027. Both layers took review commits no host probe reran.
3. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.
4. **A finish drops a finding REBUT fixed.** A phase change, with no item
   yet. Item 3 is all three of finish 93's findings.
5. **A finish prices a follow-up's ceilings from past follow-ups.** A phase
   change, with no item yet.
6. **`driver.py check` refuses a spec body that quotes a mutant's
   `find`.** A gate change, on item 080.
7. **The driver fills the seat prompts and saves the reports.** A tool
   change, with no item yet.
8. **`cite` writes the refresh it flags.** A tool change, with no item yet.
   Item 4 cost a spec PR and an operator prompt.
9. **`cite` flags a bare citation into a parent's changed file.** A tool
   change, the open half of b-b664d1.
10. **`driver.py stack` links a finish's layer.** A tool change, with no
    item yet.
11. **`bookkeeping` runs the smoke test's flat corpus.** A tool change, with
    no item yet.

This PR changes no skill text.

## Next run

Run 76 takes the next backlog items through the spec chain, starting with
b-f06097.
