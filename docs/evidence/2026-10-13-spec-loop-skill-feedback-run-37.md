# Feedback on run-saffron-spec-loop (run 37, 2026-10-13)

Run 37 ran `SA-0286` and `SA-0271` in one stack batch. The 19 specs behind
them wait on specs that have not run yet.

Both became a stack, #867 and #868. `SA-0286` spent $17.06 of $24, and $5.21
of that was its cell. `SA-0271` spent $52.51 of $52. Batch 29 spent $77.40 of
the $168 the operator approved, and stopped on `BUDGET`.

## What happened, in order

1. **The delegate priced the batch from the two shares alone.** At $156 the
   batch held back $78 and left $78 for cells. `saffron queue --stack` showed
   a spec review of $8 per spec on top, so `SA-0271` needed $168. Run 36's
   item was applied: the delegate ran the command before the batch. The
   operator approved $168.
2. **The batch's spec review cost more than the cell.** It ran three rounds on
   `SA-0286`, and its writer revised the spec twice. That spent about $11.85
   against a cell of $5.21. The revision lives only in the ledger, and the
   cell's worktree carried the queued text. The delegate read the revision out
   of `spec_texts` to brief the seats.
3. **`SA-0271`'s agent ran out of turns.** It used all 230 with no output and
   spent $28.27. Gates found 7 new failures, and repair cleared them. REVIEW
   raised three `adequacy` blockers, each a probe the witness missed. REBUT
   fixed all three and the lens withdrew them.
4. **The finish wrote the spec writer's revision back and went red.** Commit
   `55c118b3` held `SA-0286`'s revised text alone. Re-verification reported 13
   new failures, and the finish escalated and linked nothing. The host suite
   passed at that commit. The revision carried 12 new `prose` hits.
5. **The end review found one stale docstring the seats also found.** It read
   the packaged heads again (b-8a0c9a).
6. **A sentence the delegate wrote went stale under the next layer.** #865
   said re-verification creates on `DEFAULT_SUBNET` until `SA-0271`. #868
   deletes the name. This pull request fixes the sentence by hand.

## What the reviews found

The seats found six defects the critic missed. The delegate verified each.

- #867: the body named no measured pass for a prompt change.
- #867: a witness recomputed what its helper returns.
- #868: two `cell` fixtures discarded the subnet they claimed.
- #868: three fakes kept a reordered function's old signature. A positional
  revert survived before the fix and failed after it.
- #868: an evidence script warned of a collision the change removed.
- #868: new comments said a bare "pool" and lost a reason.

## Run 36's items, checked

1. **The queue refuses a spec that leaves a reader of a removed name outside
   its `touches` (b-1c59c3)**: pending. It did not recur. `SA-0271` listed two
   files it never needed.
2. **A child's edit to a parent's witness re-runs the parent's wrong versions
   (b-9efbe2)**: pending. It did not recur. The Spec seat checked the parents'
   witnesses by hand.
3. **Preflight asks whether the cell runtime is up (b-1c20da)**: pending. It
   did not recur.
4. **The adequacy lens names a witness that passes on an empty recorder
   (b-20043f)**: pending. A near shape recurred as the fakes on #868.
5. **An end review over the reviewed heads (b-8a0c9a, b-27bacc)**: pending.
   It recurred as item 5 above.
6. **Price the batch with `saffron queue --stack`**: done. It caught the
   delegate's own mispricing before the batch started.
7. **A review commit's text is part of the stack**: recurred as item 6 above.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-13 are the
evidence.

1. **The spec writer's revision passes `prose` before the batch accepts it
   (b-703e64).** A gate change. It cost a finish and its re-verification.
2. **A fake's signature is compared with its target's (b-7c8bc4).** A gate
   change, with the dropped-value fixture left to the adequacy lens.
3. **PACKAGE renders a spec's deferred checks (b-a12047).** A phase change.
4. **The queue refuses a spec that leaves a reader of a removed name outside
   its `touches` (b-1c59c3).** Carried over from run 36.
5. **A child's edit to a parent's witness re-runs the parent's wrong versions
   (b-9efbe2).** Carried over from run 36.

## The loop's own gaps

- **Name where a batch keeps a revised spec.** The skill should tell the
  delegate to brief the seats from `spec_texts`, not the tree.
- **The ceilings check leaves out the batch's spec review.** It cost two
  thirds of `SA-0286`'s spend, and it put `SA-0271` over its budget.
- **Colima is now tolerated on this host.** `limactl` joins `rapportd` and
  `RAATServe` for every run.
