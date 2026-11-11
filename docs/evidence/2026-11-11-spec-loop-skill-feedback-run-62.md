# Feedback on run-saffron-spec-loop (run 62, 2026-11-11)

Run 62 kept the goal of runs 55 to 61: implement every backlog item. It ran
one spec the chain wrote this session, `SA-0369` (#1148), for b-f582ee.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0369` | #1150 | `READY_FOR_REVIEW` | $48.12 of $60 |

Batch 80 ran at `--budget 140` with `--stack --defer-end-review`. The first
start at `--budget 130` was refused, since one $60 spec needs $136. The cell
spent $35.96 and the batch's spec review the rest. `saffron finish 80` ran
after the review commit was pushed.

## What the run found

1. **The cell went green with no runtime death.** Runs 59, 60 and 61 each lost
   a cell to the runtime. This one reached PACKAGE, and teardown exported
   39206 bytes.
2. **REVIEW asked none of its 37 wrong versions.** The gate-only cell stopped
   after the 26th criterion probe. Every later probe and every wrong version
   was filed `unproven`. No file names the error that stopped it. The task
   still reached `READY_FOR_REVIEW`. b-7c88f8 has the Record line.
3. **The seats found what that check would have asked.** Four of the Spec
   seat's blockers are wrong versions the spec declared. Each survived its
   criterion's named witness. Two lived in separately named tests, and two
   were never asserted.
4. **REBUT answered every blocker.** The adequacy lens filed 11. REBUT moved
   the head, and its re-run killed 8 and left 3 `unproven` on a stale find
   text. The Spec seat killed all 3 at the head.
5. **The finish graded fixed findings.** Finish 80 read the in-cell critic's
   two concerns at PACKAGE's head. REBUT had fixed one before PACKAGE, and
   review commit `12e8c6a6` the other. One was pooled. The other became
   `SA-0370`, refused for 11 citations. The finishing layer edited `SA-0369`'s
   spec, went red on `prose` and `census`, and pushed nothing. b-4a9207 has
   the Record line.

## What the reviews found

- **Spec seat:** 4 blockers, 1 concern and 2 notes. The blockers were witness
  gaps on criteria 1 and 2. The concern was the critic's own: a failed
  file-list read left `patch.diff` with no `patch.json`.
- **Standards seat:** 1 concern and 1 note. Both export paths wrote their own
  `patch.json`. A docstring cited "see the spec".
- Review commit `12e8c6a6` fixed all of them. The volume path now reads every
  fact before it writes either file. Every seat probe now fails its
  criterion's witness.

`.saffron/rejections.md` holds six lines for this run. No item was filed.
Record lines went to b-f582ee, b-323c97, b-4a9207 and b-7c88f8.

## Run 61's items, checked

- [ ] **A cell that dies after green is an `error`, not `EXHAUSTED`:** open.
  `SA-0369` exports a dead cell's patch from its volume, which is part of
  b-f582ee. The state a runtime death ends in is unchanged.
- [ ] **An adopted task joins its batch's stack:** open. Not hit this run.
- [x] **REBUT names a crash as a crash:** done by #1147, b-6a101f.
- [ ] **`regate` reads a recorded spec text:** open. Not hit this run.
- [ ] **A finish fixes a one-line finding in its finishing layer:** open, and
  recurred in finish 80.

## Summary: what Saffron should absorb next

1. **REVIEW does not reach `READY_FOR_REVIEW` on a probe set it never
   asked.** A gate change, on b-7c88f8. A stopped probe cell earns one fresh
   cell for the rest, and its error is written to `criterion-probes.json`.
   This run's four witness blockers were all declared wrong versions.
2. **The finish drops a critic finding that REBUT or a review commit
   changed.** A phase change, on b-4a9207. Finish 80 graded two fixed
   concerns.
3. **A cell that dies after green is an `error`, not `EXHAUSTED`.** A phase
   change, on b-f582ee.
4. **An adopted task joins its batch's stack.** A command change, on
   b-323c97.
5. **A finish fixes a one-line finding in its finishing layer.** A phase
   change, on b-4a9207.

This PR changes no skill text.

## Next run

The queue is empty. New specs come from the backlog through
`create-saffron-spec`.
