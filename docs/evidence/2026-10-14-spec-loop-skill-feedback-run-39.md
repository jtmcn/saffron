# Feedback on run-saffron-spec-loop (run 39, 2026-10-14)

Run 39 ran `SA-0272` alone. The 16 specs behind it form one chain, and each
waits on the one before it.

`SA-0272` ended `EXHAUSTED` at $41.29 of $36, or $44.97 with its spec review.
PACKAGE still opened draft #875. The operator chose to review it as it stood.
Batch 31 drained under the $72 the operator approved.

## What happened, in order

1. **IMPLEMENT ran out of turns.** It reached its ceiling of 190 turns at
   $21.53 with nothing committed. SALVAGE recovered one commit, and the gates
   passed on it. The ceilings check had compared 190 turns with a past peak
   of 131.
2. **The host's criterion probes found seven blockers.** The four lenses
   found none. Every blocker was a wrong version the witness let through.
3. **REBUT fixed six and argued one.** Its argument was wrong: it said
   nothing passes `history` to a `CellSpec`, and #872 had done exactly that.
   The gates re-ran with no new failures.
4. **The verdict ran out of money.** The fixes and their record took $9.49 of
   REBUT's $10. The verdict started with $0.56 and stopped. The task ended
   `EXHAUSTED` (b-4901d2).
5. **The driver refused the PR.** `size` and `stack` take reviewable tasks
   only. The delegate measured the size through the driver's own function,
   and marked the PR ready by hand (b-d5db52).
6. **Review took #875 over its size ceiling.** It measured 2969 tokens as
   packaged and 3251 after review, against 3000. The operator accepted it, and
   said the delegate should usually accept an overrun itself.
7. **Step 5's branch was first cut from `main`.** The `dead` gate then called
   `Ledger.snapshot` unused, since its caller is in #875. The branch was
   moved onto #875's head.

## What the reviews found

The seats found these defects that the critic missed. The delegate verified
each by a probe or by reading the line.

- The History run heading was glued to the last acceptance line in every
  lens prompt.
- A patch refused in the history Gate-only cell was reported as refused in
  the critic cell.
- Nine mutants survived the witnesses: the workdirs, the timeout, a mount's
  kind and `readonly`, `thread_env`, each exec once, `history.json`'s
  command, a timed-out copy, and a history cell for a spec with no `history`.
- Three _Avoid_ terms in tests and comments, and two comments that misstated
  or restated.

## Run 38's items, checked

1. **The spec writer's revision passes `prose` before the batch accepts it
   (b-703e64)**: pending. It did not recur. The finish had no layer.
2. **The adequacy lens names a witness that drives only some cases**:
   recurred. The witness drove a failed copy but no timed-out one, and never
   checked that a spec with no `history` gets no history cell.
3. **A fake's signature is compared with its target's (b-7c8bc4)**: pending.
   It did not recur.
4. **PACKAGE renders a spec's deferred checks (b-a12047)**: pending. It did
   not recur.
5. **cell-watch with a spec follows that spec**: not tested. The delegate
   called it with no spec this run, and it picked up `SA-0272`.
6. **The ceilings check counts the batch's spec review**: recurred in a new
   form. `SA-0272` was over budget before its spec review was counted.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-14 are the
evidence.

1. **REBUT holds back the verdict's money before the fixes start
   (b-4901d2).** A phase change. A task whose gates were green ended
   `EXHAUSTED`, and the operator decided its fate by hand.
2. **The adequacy lens names a witness that drives only some of the cases
   its criterion lists.** A lens change, now seen in two runs in a row.
3. **The `terms` gate's table carries each _Avoid_ line in `CONTEXT.md`.**
   A gate change. "History check" and "suite cell" passed `terms` here, and
   "the history check" passed on #872.
4. **Every spec a batch's writer returns passes `prose` and the queue's
   checks (b-703e64).** A gate change, carried over.

## The loop's own gaps

- **A size overrun is the delegate's call.** The operator said on 2026-10-14
  that the delegate should usually accept one. Step 2c says so now, in this PR.
- **The driver takes an `EXHAUSTED` task with an open PR as a layer once the
  operator says so (b-d5db52).**
- **Step 5's branch is cut from the top layer, not from `main`.** The `dead`
  gate caught this here. Step 5 now says where to cut it, in this PR.
- **The ceilings check compares turns with the past peak, and the peak was
  too low.** `SA-0272` used all 190 turns in IMPLEMENT alone.
