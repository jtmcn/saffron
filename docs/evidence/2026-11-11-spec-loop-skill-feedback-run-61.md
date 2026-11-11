# Feedback on run-saffron-spec-loop (run 61, 2026-11-11)

Run 61 kept the goal of runs 55 to 60: implement every backlog item. It ran
one spec the chain wrote this session, `SA-0368` (#1144), for b-fe82d9.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0368` | #1145 | `EXHAUSTED`, then adopted as `READY_FOR_REVIEW` | $39.92 of $52 |

Batch 79 ran at `--budget 120` with `--stack --defer-end-review`. It held a
$30 reserve. `saffron finish 79` refused, so no end review ran and the
reserve was not spent.

## What the run found

1. **A runtime death after green read as `EXHAUSTED`.** The gates went green
   on attempt 2. The critic raised five blockers. REBUT's agent died with
   exit -6 before any result event, so nothing answered them. A crash is an
   `error`, yet the task was charged as one that could not pass. This is the
   third cell in three runs lost to the runtime. b-f582ee has the Record line.
2. **The crash line named a cap.** The log said REBUT's extraction "ran out
   of its $4.00 reserve". No turn spent it. b-6a101f has the Record line.
3. **The patch survived this time.** Teardown exported 35249 bytes, and
   PACKAGE opened #1145 on an `EXHAUSTED` task. No hand rebuild was needed.
4. **`adopt` rescued the task.** Its re-gate ran green at the reviewed head
   and set `READY_FOR_REVIEW`. No spec text was recorded for this layer, so
   b-619b7d's block did not apply.
5. **An adopted task is no stack layer.** `saffron finish 79` refused with
   "batch 79 holds no layer". The end review never ran on #1145. b-619b7d
   has the Record line.
6. **The critic found every witness gap, and nothing answered it.** All five
   adequacy blockers were real. Both seats confirmed them, and one review
   commit closed all five. A REBUT that had run would have fixed them in the
   cell.
7. **The pinned base predated #1112.** The cell cut from 2b39b61b, and
   PACKAGE re-verified at 3e92e854. Neither suite hit the clock flake.

## What the reviews found

- **Spec seat:** 3 blockers, 1 concern and 1 note. The three blockers are the
  critic's own. The concern, an `OSError` while writing `verify.json`, is
  kept as is: a failed write in the batch tree is an infrastructure failure.
- **Standards seat:** 3 notes. Two docstring and comment wordings were fixed.
  The private imports the spec requires were kept.
- Review commit `cab81f10` fixed the witness and the wording.

`.saffron/rejections.md` holds two lines for this run. No item was filed.
`CONTEXT.md` gains a `verify.json` entry, and the escalation line entry names
the new per-failure lines. Record lines went to b-f582ee, b-6a101f and
b-619b7d.

## Run 60's items, checked

- [x] **Merge #1112:** merged at 3e92e854 by the peer session.
- [ ] **The patch is exported from the host's view of the worktree:** open.
  This run's patch was exported, but the cell still died in REBUT.
- [x] **PACKAGE and finish write each new failure they count:** done by
  #1145, b-fe82d9.
- [ ] **`regate` reads a recorded spec text:** open. This run's adopt
  needed no recorded text.
- [ ] **The loop reads a pull request adopt could not name:** open. Not hit
  this run, since adopt named #1145.
- [ ] **A finish fixes a one-line finding in its finishing layer:** open.
  No finish ran.

## Summary: what Saffron should absorb next

1. **A cell that dies after green is an `error`, not `EXHAUSTED`.** A phase
   change, on b-f582ee. REBUT should retry once on a runtime death, or end
   the task in a state that says the runtime failed.
2. **An adopted task joins its batch's stack.** A command change, on
   b-619b7d. Then `saffron finish` reviews it and spends the held reserve.
3. **REBUT names a crash as a crash.** A message change, on b-6a101f.
4. **`regate` reads a recorded spec text.** A command change, on b-619b7d.
5. **A finish fixes a one-line finding in its finishing layer.** A phase
   change, on b-4a9207.

This PR changes no skill text.

## Next run

The queue is empty. New specs come from the backlog through
`create-saffron-spec`.
