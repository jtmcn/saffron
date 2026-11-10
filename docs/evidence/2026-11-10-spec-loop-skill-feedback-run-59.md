# Feedback on run-saffron-spec-loop (run 59, 2026-11-10)

Run 59 kept the goal of runs 55 to 58: implement every backlog item. It ran
one spec, `SA-0362`, which the chain wrote this session (#1122).

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0362` | #1127 | `ORPHANED`, then rebuilt by hand | $31.46 of $32 |

Batch 77 ran at `--budget 80`. It stopped at `BUDGET` and deferred its end
review with a $20 reserve. `saffron finish 77` refused, since the batch
holds no layer.

Before the batch, the delegate closed b-c7858c (#1123), b-3df181 (#1125)
and b-cbb6e7 (#1126) by hand. It also fixed the snapshot's follow-up rows
(#1124) and the record fetch (#1121).

## What the run found

1. **A green, rebutted cell lost its whole patch in teardown.** `SA-0362`
   went green on attempt 2, and REBUT moved its head. Then the cell runtime
   failed to start any process in the container ("no PID data from sync
   pipe"). The commit log, the patch export and the status call all ran in
   that container, and all failed. No `patch.diff` was written, and the
   task ended `ORPHANED`. b-f582ee has a Record line for it.
2. **`saffron adopt` refuses an `ORPHANED` task.** The delegate rebuilt the
   branch from the writer's `proto.diff` and opened #1127. Adopt takes four
   states, and `ORPHANED` is not one. Widening that set changes how §4.2.1
   re-queues a spec, so it goes to the operator.
3. **The cell's stored probes graded the hand rebuild.** All 41 criterion
   probes and wrong versions ran against #1127's witnesses. 40 killed their
   own witness. The 41st was filed under the wrong witness: it edits the
   `Attempt`, and two `Attempt` witnesses kill it.
4. **The loop's tools read the ledger alone.** `record`, `size`, `reviewed`
   and `stack` know a pull request only from the ledger. The delegate wrote
   #1127 into `.saffron-loop/order.json` by hand. Jev's `--kind cell`
   refused, as it needs `patch.json`.
5. **The seat prompt carried a commit from the last PR.** Its worktree line
   kept run 58's `20729cb6`. The Spec seat saw that the commit was no
   ancestor and probed at the head. The fill script is the delegate's own.
6. **The seats found one helper restated and two aliased imports.** The
   Spec seat walked five criteria and found nothing.
7. **A new flake hit `make check`.** `test_a_qualification_fact_reaches_the_origin_at_exit`
   failed once on "unable to write file" in its temp origin. It passed alone
   three times, and the full suite then passed.

## What the reviews found

- **#1127:** the Standards seat raised 1 concern and 1 note, both real.
  Review commit `760a4bd1` fixed both. The Spec seat raised none.

`.saffron/rejections.md` holds one line for this run.

## Run 58's items, checked

- [ ] **Any gate REBUT turns red gets one repair turn (b-0bd346):** held
  for the operator. It reverses §5.6.
- [ ] **The adequacy lens drives each member of a set a claim names:** not
  tested. #1127 was a hand rebuild, not a cell's work.
- [ ] **A finish grades each layer's reviewed head (b-4a9207):** open.
  Finish 77 refused, so no finish ran this run.
- [x] **`record` fetches the branch before it reads the spec copy:** landed
  in #1121.
- [x] **A snapshot takes in a settled follow-up:** landed in #1124.

## Summary: what Saffron should absorb next

1. **The patch is exported from the host's view of the worktree.** A phase
   change, on b-f582ee. A dead container cost a $31 cell's whole result.
2. **`adopt` takes an `ORPHANED` task whose cell left no patch.** A command
   change, and the operator's call under §4.2.1.
3. **The loop reads a pull request adopt could not name.** A driver change.
   It removes the hand edit of `order.json`.
4. **Any gate REBUT turns red gets one repair turn (b-0bd346).** A phase
   change, held for the operator.

This PR changes no skill text.

## Next run

The queue is empty. New specs come from the backlog through
`create-saffron-spec`.
