# Feedback on run-saffron-spec-loop (run 31, 2026-10-07 to 2026-10-08)

Run 31 took three queued specs: `SA-0226`, `SA-0225` and `SA-0228`. The
operator asked for a batch with no spec review at the start, and for the
loop's own step 1b review to be removed from the skill. Then they left the
delegate to finish. This file ranks what the delegate still did by hand.

## What happened, in order

1. **`snapshot` was typed as a `saffron` command.** The status hook said
   "run `snapshot`" with no path, and `saffron snapshot` does not exist. The
   driver's message now names the whole command.
2. **The order and the batch disagreed.** `snapshot` ordered three specs and
   refused `SA-0227` and `SA-0229`. `queue --stack` planned all five. The
   operator chose a `--stack` batch over the five, which runs core's own
   spec review on each layer.
3. **The budget was worked out from the code.** `--stack` holds back a
   quarter for the end review and a quarter for the writer. The delegate
   read `cli.py` to choose $320 for $157 of spec budgets (b-0a08bf).
4. **Step 1b left the skill.** It is now a ceilings check alone. A spec is
   reviewed by `create-saffron-spec` and again by the stack batch.
5. **A green cell lost its PACKAGE.** `SA-0226` went `READY_FOR_REVIEW` at
   $13.29. PACKAGE's re-verify seed then got "Permission denied" on two loose
   objects. The batch refused `SA-0227` and `SA-0229`, and `SA-0225`'s seed
   failed the same way. The batch exited 2.
6. **Three batches to find the cause.** The delegate hand-packaged `SA-0226`
   as #745. A re-run exited 0 as `DRAINED` with no cell run (b-a04cc8). A
   rebuilt mirror failed on the same inodes, because a local
   `clone --mirror` hard-links the checkout's objects (b-6cd3c2). A
   `git repack -d` in the checkout cleared it.
7. **The fourth batch ran clean.** `SA-0225` became #746 at $34.95 of $35.
   `SA-0228` became #747 at $11.22 of $28, cut from #746's packaged head.
   The stack finish escalated on three failures it recorded nowhere
   (b-fe82d9).
8. **Seats found a witness hole on every layer.** Each was the same class:
   a pair or a set of values driven so that a mix-up between them could not
   show. Facts against rows on #745, added against removed on #746, and the
   three unknown counts on #747.
9. **The delegate chained the stack.** `SA-0225` moved onto `SA-0226`, and
   `SA-0228` onto `SA-0225`, after the review commits. Both rebases were
   clean.

## Run 30's items, checked

1. **A batch that runs the loop's order, records each task and restacks
   review commits (b-cab612, b-e0e1cf)**: partly absorbed. A `--stack` batch
   ran, and nothing refused it, since no parent was open. `record` still ran
   by hand, the restack was by hand, and the driver's order still differs
   from the batch's.
2. **A check that each witness drives every part of its claim (b-20043f)**:
   not absorbed. Four of this run's nine rejection lines are this class, and
   all three layers had one.
3. **Price a measured estimate against what measured specs landed
   (b-fbd181)**: not absorbed. All three specs measured their estimates and
   landed at 1.6x to 1.7x of them. `SA-0225` ended 119 tokens under its
   ceiling.
4. **Run `terms` and `prose` over the tree when a rule widens (b-1e106d)**:
   not exercised. `main`'s baseline showed only `prose=fail`, which is by
   design.
5. **Check that a spec's named symbols exist at base (b-cd41ac)**: not
   absorbed. The batch's spec review noted stale line citations in
   `SA-0226` and routed it `run`.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-08 are the
evidence.

1. **A mirror that shares no inode with the checkout (b-6cd3c2).** A cell
   runtime change. It cost three batches, a hand-packaged PR, and the
   refusal of two specs.
2. **A check that each witness drives every part of its claim (b-20043f).**
   A lens change. Every layer's Spec seat found a pair the witness drove on
   one side only, after the adequacy lens and REBUT had closed.
3. **Re-run PACKAGE alone, and call an infrastructure stop by its name
   (b-883f74, b-a04cc8).** A phase change and a batch change. A green cell
   needed a hand-written PR, and a night that ran nothing read `DRAINED`.
4. **A `prose` hit that survives a rename (b-8acb05).** A gate change. The
   cell's reflow got past it, and three reviewers caught it.
5. **An escalated finish that names its failures (b-fe82d9).** A phase
   change. The end review's commit broke three tests that nobody can read.

## The loop's own gaps

- **Seats stay.** All three layers' Spec seats found a witness blocker
  after the in-cell critic and REBUT had passed them.
- **The driver lags the batch.** `snapshot`'s order, `record`, `size` and
  `stack` all assume attended cells or a recorded PR. A hand-packaged task
  is invisible to `size` and `stack` (b-2247dd).
- **The watch saw no spec review.** It followed the last loop's task until
  the first cell started (b-4e1b6d).
- **Jev did not run.** No key file was made this run, so no review round was
  scored.
