# Feedback on run-saffron-spec-loop (twelfth run after the rework, 2026-09-21)

Two specs: `SA-0117` (item b-fd1468, the fold's reading half) and `SA-0116`
(item b-7d3810, rerun after run 11's wall cut). Run 11's feedback went into
backlog items through #410, and those are checked below.

**Outcome:** two pull requests, #418 and #416, stacked in that order and
marked ready. Two cells cost **$44.23** against $52 of budgets.

| Spec | PR | Spent | Attempts | Changed lines | Step 1b rounds |
|---|---|---|---|---|---|
| `SA-0117` | #418 | $30.70 of $26 | 3, two wall cuts | 979, then 993 | 3 |
| `SA-0116` | #416 | $13.53 of $26 | 2 | 619, then 636 | 2 after the edit |

## What happened, in order

1. **`snapshot --new` left `SA-0116` out and said nothing.** Run 11's
   `NOT_IMPLEMENTED` settled its `spec_sha`, and `queue` lists no refusal for a
   settled spec. The operator asked where it went. Item b-36b551 holds the
   cause, and its record now carries this run.
2. **A spec edit re-queued it.** #413 told the cell to commit as soon as a
   witness passes and to skip the full suite. The rerun committed twice in
   IMPLEMENT and reached `READY_FOR_REVIEW`.
3. **A re-snapshot released a hold on an unmerged edit.** #413 merged before
   #414. The re-snapshot that added `SA-0116` released `SA-0117`'s hold as well,
   and `next` named `SA-0117` at its old text. Item b-e8027b.
4. **Step 1b's second round found a blocker the authoring reviews missed.**
   `SA-0117` told its cell to delete three tests, and `census` fails any removed
   test on every attempt. The cell would have ended `EXHAUSTED`.
5. **The delegate's edits carried findings again.** Round 1's edit to criterion
   1 left a note two paragraphs down saying "fresh ledger". Round 2 found it.
   The same edit garbled a sentence in a third paragraph. This is the fourth run
   in a row with this pattern.
6. **A blocker the delegate declined came back after the cell.** Round 1 asked
   to pin attempt 2's phase. The delegate declined, since the fact carries `n`.
   The cell chose a second phase, so both attempts had `n=1`, and a fold fixing
   `n` at 1 passed. The Spec seat found it and the review commit fixed it.
7. **The turn wall cut `SA-0117` twice.** IMPLEMENT had one commit when cut,
   and REPAIR was checkpointed by the host. A 1000-line refactor does not fit
   in 900 seconds per turn. Item b-36b551.
8. **`SA-0117` packed SQL to pass `size`.** The operator accepted it and asked
   for a fix soon. Item b-89ec93.
9. **The seats found five witness holes in #418 after a clean lens pass.** Each
   was found by a probe, not by reading. Item b-2750d5 is the in-cell half.

## Run 11's items, checked

- b-440f17, `prose` reaching Python: recurred in both pull requests.
- b-0de0b3, the loop's history collected by hand: still true. This run's
  summary was assembled from a scratch file again.
- b-36b551, the wall cut: recurred twice, above.

## Summary: what to change first

1. **b-36b551**. It cost a whole cell in run 11 and two cut turns here.
2. **b-2750d5**. Five holes in one pull request after the adequacy lens.
3. **b-89ec93**. A blocking gate that a reformat passes.
4. **b-e8027b**. A driver fix, small.
