# Feedback on run-saffron-spec-loop (run 32, 2026-10-08 to 2026-10-09)

Run 32 took every queued spec. Twenty-six had been written and reviewed in
the spec chain of 2026-10-07, and none had run. The operator chose one
`--stack` batch over all 26 at $1200, with no deadline. The batch spent
$295.91. Thirteen pull requests reached the stack as #791. Thirteen specs did
not run, and two follow-ups the batch wrote did not join the stack.

## What happened, in order

1. **The operator read the queue as already merged.** `saffron queue` names
   an unmet `depends_on` as "has no task at its current spec_sha". The
   refusal never says that the spec merged and its task never ran.
2. **`snapshot` stranded six specs again (b-fab381).** `SA-0229` and
   `SA-0246` name a parent that merged but whose spec file is still queued.
   `snapshot --force --add` refused them as "not new". The delegate wrote the
   six rows into `order.json` by hand with the driver's own `OrderRow`.
3. **The order and the batch disagreed again.** `queue --stack` planned all
   26. `saffron batch` takes no order, so the operator's first answer could
   not be run.
4. **The budget split was read from the code again (b-0a08bf).** A `--stack`
   batch holds back a quarter for the end review and a quarter for the
   writer.
5. **A stack batch chains every layer.** The batch cut each cell from the
   previous layer's packaged head, `depends_on` or not. PACKAGE then applied
   the patch onto that branch's current head, review commits included. The
   delegate held each layer's review commits until the next layer packaged.
6. **A PACKAGE seed failed after a green cell (b-6cd3c2, b-f582ee).**
   `SA-0233` went `READY_FOR_REVIEW` at $8.36. Its re-verify seed read
   "Permission denied" on mirror object `6c8cc03b`, which four seeds had read
   before it. The batch counted the layer missed and refused its nine
   dependents. The delegate hand-packaged it as #780.
7. **The watch's wake-ups queued while the delegate reviewed.** Seven layers
   packaged during one long review. The delegate then reviewed seven pull
   requests at once, with seat prompts generated from a template and reports
   written to files.
8. **`SA-0245` ran out of REBUT budget.** Main lacks `SA-0231`'s REBUT cap,
   so REBUT inherited the remainder and was cut. Four test blockers stood.
   The operator dropped it and its two dependents.
9. **`SA-0251`'s first seed failed on the same object.** It never ran.
10. **`SA-0255` could not write a path in its own `touches`.** The in-cell
    agent was refused every write to `.pre-commit-config.yaml`. The cell left
    the hook block in its notes. The delegate added it as #790.
11. **The end review graded the wrong heads.** It ran over the packaged
    heads, before the loop's review commits. Most of what it pooled was
    already fixed. It wrote two follow-ups. `SA-0256` (#789) made a test read
    the table it checks, and the operator closed it. `SA-0257` ended
    `EXHAUSTED`. The finish escalated with 7 new failures (b-fe82d9).
12. **No second batch could run.** The queue refuses a spec whose `touches`
    overlaps an open pull request. This stack covers `review.py`,
    `worktree.py` and `ledger.py`, so a plain batch would run two specs and
    `--stack` none. The operator deferred the ten to the next loop.
13. **The driver could not stack the chain.** `driver.py stack` ordered by
    `depends_on` alone, left out #780 and #790, and said a reordered child's
    diff was unaffected. The delegate wrote a restack script. It rebased all
    twelve layers onto their parents' reviewed heads and moved #780 to the
    top. `make check` passed at the top, and `gh stack link` made #791.

## Run 31's items, checked

1. **A mirror that shares no inode with the checkout (b-6cd3c2)**: not
   absorbed. It cost two specs their runs and nine their place in the batch.
2. **A check that each witness drives every part of its claim (b-20043f)**:
   not absorbed. Seats found this class on #777, #779, #780, #781, #782 and
   #787, each after the in-cell critic.
3. **Re-run PACKAGE alone, and call an infrastructure stop by its name
   (b-883f74, b-a04cc8)**: not absorbed. `SA-0233` was hand-packaged again.
   `SA-0234` (#783) now re-offers a cell runtime failure, which re-runs a
   whole green cell when PACKAGE raises.
4. **A `prose` hit that survives a rename (b-8acb05)**: not exercised. The
   gate instead forced two review fixes down to two-line comments.
5. **An escalated finish that names its failures (b-fe82d9)**: not absorbed.
   Batch 20's finish escalated on 7 failures it recorded nowhere.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-09 are the
evidence.

1. **Run PACKAGE alone on an exported patch (b-883f74).** A phase change.
   One PACKAGE failure cost nine specs their run, and #783 now makes the same
   failure re-pay a whole cell.
2. **A mirror that shares no inode with the checkout (b-6cd3c2).** A cell
   runtime change. It struck twice in one batch.
3. **A batch that takes the loop's order (b-910cef).** A batch change. The queue's
   open-PR conflict set refuses every child of an open stack, so the loop
   cannot run a second batch until the first merges.
4. **A check that each witness drives every part of its claim (b-20043f).**
   A lens change. It was the seats' most common blocker again.
5. **An end review over the reviewed heads (b-8a0c9a).** A phase change. Grading the
   packaged heads re-raised findings the seats had already fixed, and its
   follow-up made a test weaker.
6. **A cell that can write every path in its `touches` (b-f8fa24).** A
   cell runtime change. `SA-0255` lost its run to one refused path.

## The loop's own gaps

- **Seats stay.** The in-cell critic missed a real defect on 11 of 13
  layers. It was clean on #777, #780, #784, #786 and #787, and seats found
  blockers on three of those.
- **The driver lags the batch (b-f10412, b-25f2b2).** `snapshot`,
  `record`, `stack` and `size` assume an order of `depends_on` and a ledger pull request. A stack batch
  chains by predecessor, and a hand-packaged layer has no ledger pull
  request.
- **Seat prompts must spell the findings block.** Seats wrote YAML and string
  criteria until the prompt gave the JSON shape.
- **A spec review that routes `run` prints nothing (b-5abe53).** The
  delegate told
  seats no spec review ran. The ledger's `spec_reviews` table showed one per
  layer.
