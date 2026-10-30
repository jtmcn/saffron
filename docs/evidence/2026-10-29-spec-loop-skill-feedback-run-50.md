# Feedback on run-saffron-spec-loop (run 50, 2026-10-27 to 2026-10-29)

Run 50's order was `SA-0325`, `SA-0326` and `SA-0327`, with budgets of $98.
Three stack batches ran it, 59 at $250, 60 at $190 and 61 at $76. Each
spec reached a reviewed pull request: #989 and #990 in one stack, then #996
after that stack merged. The run spent about $116.

| Spec | PR | Spend of budget | Peak turns of ceiling |
|---|---|---|---|
| `SA-0325` | #989 | $20.73 of $20 | 70 of 120 |
| `SA-0326` | #990 | $38.17 of $48 | 119 of 240 |
| `SA-0327` | #996 | $41.43 of $30 | 170 of 170 |

Batch 59's spec review of `SA-0326` spent $4.90 and ran no cell. Finish 60
spent $4.14. Batch 61's spec review spent $0.82, and finish 61 spent $5.36. Peak turns are the largest turn count per attempt in the
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
9. **A sibling layer moved a child's citations (#995).** Once #990 merged,
   `check` found four `cli.py` citations 13 lines off. `cite` ran at #989's
   head, which never held #990's lines.
10. **`cite` passed two citations that name the wrong code.** Batch 61's
    spec review found `cli.py:1106-1113` and `:1638-1640` off by about 13
    lines. `cite` reported all 52 resolved.
11. **`SA-0327`'s IMPLEMENT ran out of turns.** It used 170 of 170, and the
    gates were green anyway. `check` said the ceilings clear this shape's
    history, against `SA-0201`'s 121. The batch's spec review called them
    tight against `SA-0326`'s 240.
12. **Finish 61 pooled its one follow-up for a `depends_on` (b-27bacc).**
    The finding was real, and b-25b7ba carries it instead.

## What the reviews found

Six seats reviewed three pull requests and raised 30 findings. Review commits
fixed 20. Nine needed no action, and one was not a defect. Nine were
blockers, all witness gaps the critic missed, and all nine were real.
Finish 60's end review raised one new concern, fixed on #990. Finish 61's
raised one, filed as b-25b7ba. `.saffron/rejections.md` holds 10 lines for
this run, under 2026-10-29 and 2026-10-30.

On #996 the in-cell critic raised six adequacy blockers, and REBUT fixed all
six. The Spec seat then ran 43 probes and five survived. The Standards seat
raised four notes, and the critic had raised one of them.

Six new items carry what the run left: b-8826cf, b-298b1c, b-323c97,
b-0bd8c9, b-8971e6 and b-25b7ba.

## Run 49's items, checked

- [x] **The finishing layer retires a follow-up whose cell ran
  (b-e0044f):** done in #996.
- [x] **A lens reads each review commit (b-549012):** done in #990. This
  run could not use it, since #990 is not merged.
- [ ] **The adequacy lens probes the way the Spec seat does:** open. Nine
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
   It missed nine witness gaps this run, five of them after REBUT.
4. **An adopted task is a layer of its batch (b-323c97).** A phase change.
   #989 merges with no end review.
5. **A stack batch exempts an earlier batch's lower layers (b-0bd8c9).** A
   gate change. It cost a merge before `SA-0327` can run.
6. **`cite` reads every open layer's lines, and checks what a sentence
   names.** A driver change. It ran at one parent and missed a sibling's
   shift, so #991 and #995 each refreshed citations. It also passed two
   citations a spec review then found.
7. **`check` compares ceilings with the closest shape.** A driver change.
   It cleared 170 turns against a 121-turn floor, and the cell used all 170.
8. **The skill says to read `saffron queue --stack` for the budget.** A
   skill text change, ranked last. It cost one question to the operator.

This PR changes no skill text.

## Next run

The queue is empty once #996 and this PR merge. Batch 59's reserve was
never used.
