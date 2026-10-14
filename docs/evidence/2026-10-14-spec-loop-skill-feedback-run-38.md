# Feedback on run-saffron-spec-loop (run 38, 2026-10-14)

Run 38 ran `SA-0289` and `SA-0285` in one stack batch. Both waited on
`SA-0271`, which run 37 landed. The 17 specs behind them wait on specs that
have not run.

Both became a stack, #871 and #872. `SA-0289` spent $24.98 of $24, and
`SA-0285` spent $14.01 of $28. Batch 30 spent $52.47 of the $120 the operator
approved, and stopped on `BUDGET`.

## What happened, in order

1. **The delegate priced the batch first.** `saffron queue --stack` showed
   that $120 admits both specs. Run 37's item held.
2. **cell-watch followed the last run's task.** With no spec it picked
   `SA-0271`, and with `SA-0289` it did the same. The delegate fell back to a
   Monitor on the log. The tool moved on once `SA-0289` started.
3. **A lens answered outside its schema.** The conventions lens on `SA-0289`
   added a `claim_detail` field. REVIEW re-prompted it once and it answered.
4. **The finish went red again.** The end review raised a concern on
   `SA-0285`, and the follow-up writer turned it into `SA-0292`. That spec
   carried 21 `prose` hits and failed two of the queue's own checks.
   Re-verification reported 24 new failures and the finish escalated. A
   comment fixed the concern on #872.
5. **Review took `SA-0289` over its size ceiling.** The cell's diff measured
   1065 tokens. The strengthened witness took it to 1319 against 1300. The
   operator accepted the overrun.

## What the reviews found

The seats found these defects that the critic missed. The delegate verified
each by a probe or by reading the line.

- #871: the `images` witness asserted the runtime calls on one store only.
- #871: it never drove the proxy-alone miss, or each store on both runtimes.
- #871: its raise case never named the tag.
- #871: a docstring had its guard backwards and a test copied a helper.
- #872: the history field was called a check, an _Avoid_ term.
- #872: a test parameter went unannotated, and a docstring did not say its
  claim was documented.

## Run 37's items, checked

1. **The spec writer's revision passes `prose` before the batch accepts it
   (b-703e64)**: pending. It recurred as item 4 above, from the follow-up
   writer this time.
2. **A fake's signature is compared with its target's (b-7c8bc4)**: pending.
   It did not recur. The Spec seat checked the fakes by hand.
3. **PACKAGE renders a spec's deferred checks (b-a12047)**: pending. It did
   not recur.
4. **The queue refuses a reader of a removed name outside `touches`
   (b-1c59c3)**: pending. It did not recur.
5. **A child's edit to a parent's witness re-runs the parent's wrong versions
   (b-9efbe2)**: pending. It did not recur.
6. **Name where a batch keeps a revised spec**: neither spec was revised.
7. **The ceilings check leaves out the batch's spec review**: recurred.
   `SA-0289` went $0.98 over once its spec review was counted.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-14 are the
evidence.

1. **Every spec a batch's writer returns passes `prose` and the queue's
   checks before the finish commits it (b-703e64).** A gate change. Two
   finishes in a row went red on it.
2. **The adequacy lens names a witness that drives only some of the cases its
   criterion lists.** A lens change. #871's three gaps were this one shape.
3. **A fake's signature is compared with its target's (b-7c8bc4).** A gate
   change, carried over from run 37.
4. **PACKAGE renders a spec's deferred checks (b-a12047).** A phase change,
   carried over from run 37.

## The loop's own gaps

- **cell-watch with a spec should follow that spec.** It followed the last
  run's task until the batch started the next one.
- **The ceilings check should count the batch's spec review.** It put two
  specs in two runs over budget.
- **A review commit that adds test cases can cross `size`.** The skill could
  say to run `size` before the witness commit, not only after the push.
