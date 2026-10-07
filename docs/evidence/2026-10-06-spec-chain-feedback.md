# Spec chain feedback, 2026-10-06

## The task page, `SA-0219`

Item b-cf50dc came from the run record view's final whole-branch review. That
review read the merged view against the plan on the real ledger. It found the
task page never says how a task ended, puts every row in one unlabelled
table, and sorts ids as text. The operator split the review's findings. The
small ones landed by hand as review commits on #708, and this one became a
spec.

### Cost

| Step | Time |
|---|---|
| Draft | 25.4 min |
| Review 1 | 4.2 min |
| Revise 1 | 9.2 min |
| Review 2 | 4.8 min |
| Revise 2 | 7.0 min |

The draft did not split. A prototype measured 2125 tokens, then 2211 after
both revisions, against a split line of 2400. Round 2 was settled by running
every listed wrong version, 50 of 50 killed, with no third review.

### Rounds

| Round | Blockers | Concerns | Notes |
|---|---|---|---|
| 1 | 2 | 3 | 3 |
| 2 | 0 | 4 | 5 |

### Each finding by class

- **A fixture that makes a wrong build right by coincidence.** All six
  concerns of substance were this class again, and four were the same
  shape as yesterday's. One batch per task left the batch page's order
  untested. A single unbatched task let a query run unbound. An uncosted
  attempt holding three gate results let a sum over the wrong rows land on
  the right total. A batch id could equal a task id.
- **A claim over a set whose witness drives one member.** The unbatched
  task carried no cost, so a total read from the batched query passed.
- **Two criteria answering one input differently.** One criterion gave
  every task page four tables, and another gave a page with no attempts
  none.

### What the next run changes

- The fixture-coincidence check proposed yesterday would have caught every
  round-1 finding here. It is still prose, and it is the next check to
  make a command.
- A writer that has met a hole once repeats it in the next spec of the
  same shape. Give the brief yesterday's exact holes by name, not only
  their class.

## The run record view's final review

The plan's whole-branch review ran on the most capable model over the
feature's own paths, and it served the real ledger read-only. It found no
critical issue and four important ones. Three were page design, and the
fourth was a missing `Host` check that let a DNS-rebinding page read the
record. Each spec's two review rounds and each cell's critic had passed all
four. They were found by using the page on real data, which no spec review
or lens does.
