# Feedback on run-saffron-spec-loop (run 50, 2026-10-27 to 2026-10-29)

Run 50's order was `SA-0325`, `SA-0326` and `SA-0327`, with budgets of $98.
Two stack batches ran it, 59 at $250 and 60 at $190. Two specs reached a
reviewed pull request, stacked as #989 and #990. `SA-0327` waits for that
stack to merge, by the operator's call. The run spent about $68.

| Spec | PR | Spend of budget | Peak turns of ceiling |
|---|---|---|---|
| `SA-0325` | #989 | $20.73 of $20 | 70 of 120 |
| `SA-0326` | #990 | $38.17 of $48 | 119 of 240 |
| `SA-0327` | none | $0 of $30 | not run |

Batch 59's spec review of `SA-0326` spent $4.90 and ran no cell. Finish 60
spent $4.14. Peak turns are the largest turn count per attempt in the
ledger.

## What the run found

1. **A rebuttal's suppressions ended a green task (b-8826cf).** `SA-0325`
   passed every gate on attempt 1. REBUT then wrote ten `noqa` comments,
   and `integrity` ended it `EXHAUSTED`. The delegate moved one closure,
   and `saffron adopt` re-gated it green as #989.
2. **A spec review's findings were lost (b-298b1c).** Batch 59's review
   of `SA-0326` found a blocker, then its extraction ran past $1. The batch
   raised and ran no cell. Batch 60's review of the same spec passed.
3. **An adopted task got no end review (b-323c97).** `saffron finish 59`
   refused with "batch 59 holds no layer", so #989 was read by no end review.
4. **A child's citations named `main` (no item).** `SA-0327` cites
   `follow_up.py` at `main`, and its cell cuts from #989's head. Batch 60
   refused it, and #991 refreshed six citations.
5. **A stack batch refused a sibling overlap (b-0bd8c9).** With #991 in, a
   new batch refused `SA-0327` for touching `cli.py`, which #990 changes.
6. **CI on `main` was red from git 2.56 (b-d0baf7, closed).** All 12 runs on
   the new runner image failed one finish test, and all 8 on the old one
   passed. Git 2.56 writes a URL push's ref into the matching mirror. #992
   fixed the test.
7. **The finish still pooled a draft that did not parse.** Finish 60 ran
   `main`'s code, without `SA-0325`, so one finding filed nothing.
8. **The token file in the scratchpad vanished overnight.** Batch 60's
   first start failed on a missing env file.

## What the reviews found

Four seats reviewed two pull requests and raised 19 findings. Review commits
fixed 10. Eight needed no action, and one was not a defect. Four were
blockers, all witness gaps the critic missed, and all four were real.
Finish 60's end review raised one new concern, fixed on #990.
`.saffron/rejections.md` holds 6 lines for this run, dated 2026-10-29.

Five new items carry what the stack left: b-8826cf, b-298b1c, b-323c97,
b-0bd8c9 and b-8971e6.

## Run 49's items, checked

- [ ] **The finishing layer retires a follow-up whose cell ran
  (b-e0044f):** open. `SA-0327` is queued for it.
- [x] **A lens reads each review commit (b-549012):** done in #990. This
  run could not use it, since #990 is not merged.
- [ ] **The adequacy lens probes the way the Spec seat does:** open. Four
  witness gaps this run came from a seat's probe.
- [x] **A follow-up draft that does not parse goes back once (b-781ea4):**
  done in #989. It recurred once in finish 60, which ran `main`.
- [ ] **`snapshot` takes in a finish's follow-up (b-719346):** open. It did
  not recur.
- [ ] **A held blocker marks its pull request (b-92c92a):** open. It did not
  recur.
- [ ] **The skill states the batch's holds:** open. It recurred. The
  delegate quoted $160 for batch 60, and `saffron queue --stack` said $188.

## Summary: what Saffron should absorb next

1. **A spec review keeps its findings when extraction fails (b-298b1c).** A
   phase change. It cost one layer and lost one blocker.
2. **REBUT gets a repair turn, or knows a suppression fails (b-8826cf).** A
   phase change. It cost a $20 task and a hand fix.
3. **The adequacy lens probes the way the Spec seat does.** A lens change.
   It missed four witness gaps this run.
4. **An adopted task is a layer of its batch (b-323c97).** A phase change.
   #989 merges with no end review.
5. **A stack batch exempts an earlier batch's lower layers (b-0bd8c9).** A
   gate change. It cost a merge before `SA-0327` can run.
6. **`check` re-runs `cite` on a child once its parent packages.** A driver
   change. Step 1b printed "cite not run" for `SA-0327`, and nothing ran it
   again before the batch refused it.
7. **The skill says to read `saffron queue --stack` for the budget.** A
   skill text change, ranked last. It cost one question to the operator.

This PR changes no skill text.

## Next run

`SA-0327` is the order, once #989, #990 and this PR merge. Batch 60's
reserve is spent, and batch 59's was never used.
