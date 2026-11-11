# Feedback on run-saffron-spec-loop (run 60, 2026-11-10)

Run 60 kept the goal of runs 55 to 59: implement every backlog item. It ran
three specs the chain wrote this session: `SA-0363` (#1132), `SA-0364`
(#1133) and `SA-0365` (#1134).

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0363` | #1135 | `READY_FOR_REVIEW` | $43.98 of $64 |
| `SA-0364` | #1136 | `MERGE_FAILED`, then opened by hand | $25.02 of $30 |
| `SA-0365` | #1137 | `ORPHANED`, then rebuilt by hand | $49.80 of $60 |

Batch 78 ran at `--budget 356` with `--stack --defer-end-review`. It spent
$118.80 of the $154 its three specs carried, and it held an $89 reserve.
Finish 78 reviewed `SA-0363`, the one layer PACKAGE opened. It raised two
concerns and a note, and ended `INFRASTRUCTURE` with both follow-ups unrun.

## What the run found

1. **One flaky pair cost two of three tasks.** The two commit-id tests
   #1112 fixes failed in `SA-0364`'s PACKAGE re-verify, so a green cell
   ended `MERGE_FAILED`. `SA-0365`'s second repair then chased the same
   pair and looped the suite inside the cell. #1112 is green and mergeable.
   The delegate's merge was refused as a merge without review, so it waits
   on the operator.
2. **A second cell lost its patch to the cell runtime.** `SA-0365`'s agent
   died with exit -6, and the runtime then failed to start any process ("no
   PID data from sync pipe"). The patch export ran in that container, so no
   `patch.diff` was written. This is run 59's failure again, on b-f582ee.
3. **PACKAGE counts its new failures and names none.** `SA-0364`'s log said
   "2 new failures" and nothing more. A local suite on the same commit named
   them. This is b-fe82d9's shape, now in PACKAGE as well as in a finish.
4. **`adopt` cannot re-gate a stack batch's task.** `regate` declines any
   task that ran a recorded spec text. A `--stack` batch records one for each
   layer its own spec review revised, so `SA-0364` stayed `MERGE_FAILED`.
   b-619b7d has the Record line.
5. **The loop's tools again read the ledger alone.** The delegate wrote
   #1136 and #1137 into `.saffron-loop/order.json` by hand, as run 59 did
   for #1127.
6. **The cell's stored probes graded the hand rebuild again.** All 28
   criterion probes and 31 wrong versions ran against #1137. Each was
   killed, two through an equivalent edit.
7. **Every PR's review strengthened a witness.** Each Spec seat found a
   listed wrong version that survived, after the in-cell critic withdrew
   its own blockers. `SA-0365`'s seats also found a git read with no bound.
8. **The finish drafted specs for two one-line docstrings.** `SA-0366`'s
   draft failed `prose`. `SA-0367`'s witness passed at its base, because
   review commit `80f41af0` had fixed its line. The finish pushed both
   drafts as #1138. The delegate fixed the one live line in this PR and
   closed #1138. b-4a9207 has the Record line.

## What the reviews found

- **#1135:** the Spec seat raised 3 blockers and 2 notes. The Standards seat
  raised 1 concern and 2 notes. Review commit `80f41af0` fixed every one.
- **#1136:** the Spec seat raised 2 blockers and 1 note. The Standards seat
  raised 3 notes. Review commit `b5c6f011` fixed all but a nested test
  helper, which follows the file's own pattern.
- **#1137:** each seat raised 1 concern and 3 notes. Review commit
  `efa95a11` bounded the git read, reordered the timeout check and fixed
  the wording. The `Popen` workaround is kept and filed as b-16c819.

`.saffron/rejections.md` holds six lines for this run. Two new items were
filed, b-96508a and b-16c819, and Record lines went to b-fe82d9, b-619b7d,
b-f582ee and b-4a9207.

## Run 59's items, checked

- [ ] **The patch is exported from the host's view of the worktree:** open.
  It cost a second task this run, on b-f582ee.
- [ ] **`adopt` takes an `ORPHANED` task:** held for the operator. #1137 is
  no task's pull request either.
- [ ] **The loop reads a pull request adopt could not name:** open. Two hand
  edits of `order.json` this run.
- [ ] **Any gate REBUT turns red gets one repair turn (b-0bd346):** held
  for the operator.

## Summary: what Saffron should absorb next

1. **Merge #1112.** It is a test fix, not a gate change, and it removes the
   flake behind two of this run's three losses.
2. **The patch is exported from the host's view of the worktree.** A phase
   change, on b-f582ee. Two runs in a row lost a green or near-green patch.
3. **PACKAGE and finish write each new failure they count.** A phase
   change, on b-fe82d9. It would have named this run's flake at once.
4. **`regate` reads a recorded spec text.** A command change, on
   b-619b7d. It lets `adopt` rescue a stack batch's task.
5. **The loop reads a pull request adopt could not name.** A driver change.
6. **A finish fixes a one-line finding in its finishing layer.** A phase
   change, on b-4a9207. Four runs drafted a spec for one line.

This PR changes no skill text.

## Next run

The queue is empty. New specs come from the backlog through
`create-saffron-spec`.
