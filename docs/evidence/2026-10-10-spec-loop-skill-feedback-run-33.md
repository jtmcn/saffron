# Feedback on run-saffron-spec-loop (run 33, 2026-10-10)

Run 33 took the ten specs run 32 deferred. The operator chose one `--stack`
batch at $500, with no deadline. The batch spent $200.33. The ten cells spent
$163.29 against $253 of spec budgets. All ten ended `READY_FOR_REVIEW`, and the
stack is #793 to #802, linked as #803. `SA-0253` and `SA-0254` were refused,
because their parent `SA-0245` is outside the order. The operator chose to
rewrite `SA-0245` in a later session.

## What happened, in order

1. **The snapshot left out two layers (b-fab381).** `SA-0248` names `SA-0244`,
   in the order, and `SA-0237`, merged. The snapshot held eight specs, and
   `queue --stack` admitted ten. `--force --add` refused both as not new.
2. **The batch ran all ten anyway.** `saffron batch` takes no order, so the
   batch ran the two specs the driver had left out. `driver.py record` then
   refused both as not in the order. The delegate read their outcomes from
   the ledger.
3. **Each layer's review commits waited for the next layer.** The batch cuts
   each cell from the previous layer's packaged head. The delegate held every
   fix as a local commit until the layer above packaged, then pushed it.
4. **Three cells overran their budgets and still finished.** `SA-0242` spent
   $22.60 of $21, `SA-0243` $22.47 of $20 and `SA-0244` $20.06 of $20.
5. **Two criterion blockers stood after REBUT (b-c9a913).** On `SA-0242` and
   `SA-0248` the host's probe survived the declared witness. Another test
   killed it each time. The delegate settled both by re-running the probe.
6. **The seats found a blocker the critic missed on eight of ten layers.**
   The critic was clean on #793 and #799, and the seats found blockers on
   both.
7. **One layer went over its `size` ceiling.** `SA-0243`'s fixes reached
   1376 of 1300. The operator chose to drop two note fixes, which became
   b-97357c, and the layer landed at 1296.
8. **The end review graded the packaged heads again (b-8a0c9a).** Seven of
   its eight findings were already fixed on the branches. The eighth is
   b-55186d.
9. **No follow-up became a spec (b-27bacc).** The writer drafted one per
   group. `follow_up._validate` refuses a `depends_on` entry, and in a stack
   each draft named one. Two more drafts had no frontmatter, and one declared
   type `test`.
10. **The driver could not stack the chain again (b-f10412).** The delegate
    rebased all nine layers with run 32's restack script. `make check` passed
    at the top, and `gh stack link` made #803.

## Run 32's items, checked

1. **Run PACKAGE alone on an exported patch (b-883f74)**: not exercised.
   Every PACKAGE in this batch succeeded.
2. **A mirror that shares no inode with the checkout (b-6cd3c2)**: not
   absorbed. The delegate deleted the old mirror, and no seed failed.
3. **A batch that takes the loop's order (b-910cef)**: not absorbed. The
   batch and the snapshot disagreed on two specs (step 2).
4. **A check that each witness drives every part of its claim (b-20043f)**:
   not absorbed. It was the seats' most common blocker again.
5. **An end review over the reviewed heads (b-8a0c9a)**: not absorbed. The
   reviews and the writer cost $37.04 beyond the cells. The end review found
   one new defect.
6. **A cell that can write every path in its `touches` (b-f8fa24)**: not
   exercised. No spec this run touched the hook config.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-10 are the
evidence.

1. **Judge a criterion probe against the whole `tests` gate (b-c9a913).**
   A gate change. Two argued blockers stood on a misnamed witness, and the
   delegate settled each by hand.
2. **A check that each witness drives every part of its claim (b-20043f).**
   A lens change. Eleven of the twenty rejection lines are `witness` lines.
3. **An end review over the reviewed heads, with follow-ups it can admit
   (b-8a0c9a, b-27bacc).** A phase change. The end review paid for findings
   the seats had fixed, and its writer drafted specs the validator refused.
4. **A batch that takes the loop's order (b-910cef, b-fab381).** A batch
   change. The snapshot and the batch disagreed, and the driver refused to
   record two layers the batch ran.
5. **A driver that stacks a stack batch's chain (b-f10412).** A skill change,
   ranked last. The restack script ran a second time without a conflict.

## The loop's own gaps

- **Seats stay.** The critic missed a blocker on eight of ten layers.
- **Held pushes are a hand step (b-cab612).** Each layer's fix waited for the
  next layer to package. A batch that reads the review commits would end it.
- **A spend overrun reads as a pass.** Three cells passed their budgets and
  ended `READY_FOR_REVIEW`. No line in the batch log names the overrun.
