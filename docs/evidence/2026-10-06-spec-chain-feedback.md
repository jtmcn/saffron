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

## The migration, `SA-0220` to `SA-0224`

Item 170's design step 3 moves the stored tasks into the record. One writer
read the item and stopped at its step 1. Two fact shapes the migration
writes were not built, so the step became four specs. A revision then pushed
the migration core past the size line, and it split again into five.

### Cost

Times are each agent's wall clock.

| Spec | Draft | Review 1 | Revise 1 | Review 2 | Fixes after round 2 |
|---|---|---|---|---|---|
| `SA-0220` | 5.0 min split, 22.0 min draft | 4.6 min | 12.6 min | 5.7 min | by hand |
| `SA-0221` | 2.5 min stop, 12.9 min draft | 3.1 min | none | none | none |
| `SA-0222` | 28.1 min | 6.5 min | 5.0 min stop, 13.1 min split | 5.4 min | 6.8 min |
| `SA-0223` | 26.3 min | 3.7 min | 15.9 min | 3.4 min | 7.0 min |
| `SA-0224` | 35.3 min | 9.3 min | 12.4 min | 5.3 min | 8.4 min |

Every spec was measured on a prototype, from 205 to 434 lines. Every listed
wrong version was applied to its prototype and killed: 33, 16, 29, 37 and 39.
The two-round stop held on every spec. Fixes after round 2 were run on the
prototype, with no third review.

### Rounds

| Spec | Round 1 | Round 2 |
|---|---|---|
| `SA-0220` | 1 blocker, 2 concerns, 3 notes | 0, 3, 3 |
| `SA-0221` | 0, 2, 3 | none |
| `SA-0222` | 2, 5, 6 | 1, 6, 3 |
| `SA-0223` | 1, 2, 4 | 1, 2, 3 |
| `SA-0224` | 2, 3, 7 | 1, 2, 6 |

### Each finding by class

- **A claim over a set whose witness drives one member.** Seven of the nine
  blockers were this class. The unread members were all reachable on the
  real ledger. They were a stack rerun's
  second baseline, a fact differing after its first position, the
  `revert` and `witness` shape of drift, a doubled attempt with counted
  results, numbering that never skips, and output streamed within one repo.
- **A claim wider than the spec's own scope.** `SA-0222`'s round-2
  blocker said it writes every task fact kind, and seven belong to `SA-0224`.
- **A claim about the documents that a same-day hand edit made false.**
  `SA-0222`'s first blocker contradicted a `DESIGN.md` sentence added by hand
  for `SA-0220` after `SA-0222`'s brief went out.
- **A design argument the code does not support.** The design put the
  earned tier on the attempt's close. The attempt closes before the suite
  computes the tier, so the operator moved the tier to the gate-result fact.
- **A data flow the base cannot carry.** A null `tasks.risk` drops the task
  from the view, the projection and a shape. The operator kept the null in
  the record only.
- **An arrangement argued rather than run.** A mirror cannot push to its
  own remote, and the live mirror's remote is a scratch checkout. Both came
  from the writer's prototype. Neither came from a review.

### What the next run changes

- A brief that reaches a later spec must carry every hand edit made to
  `DESIGN.md` since the chain started.
- The set check is still prose, and it found seven blockers here. The next
  check to make a command is one that lists each claim's quantified set
  and asks which witness member drives each element.
- A full trial migration of a ledger copy ran in 17 min, and a rerun took
  2.7 min with nothing duplicated. Five measured specs, run as one chain
  through one writer per spec, cost about four hours of agent time.
