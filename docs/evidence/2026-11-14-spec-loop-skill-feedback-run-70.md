# Feedback on run-saffron-spec-loop (run 70, 2026-11-14)

Run 70 kept the goal of runs 55 to 69: implement every backlog item. It
queued `SA-0389` and `SA-0390`, written after run 69.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0389` | #1202 | `READY_FOR_REVIEW` | $22.39 of $48 |
| `SA-0390` | #1203 | `READY_FOR_REVIEW` | $19.08 of $36 |
| `SA-0391` | #1204 | `READY_FOR_REVIEW` | $7.67 of $15 |
| `SA-0392` | #1205 | `READY_FOR_REVIEW` | $5.30 of $10 |

Batch 88 ran at `--budget 200` with `--stack --defer-end-review`. It spent
$41.47. Finish 88 spent $22.60, and $12.97 of that went to two follow-ups.
The run spent $64.07 of $200. `SA-0389` used 271 turns, 82 in IMPLEMENT,
against 200. `SA-0390` used 342, 72 in IMPLEMENT, against 180.

## What the run found

1. **A review commit of mine made a wrong version observable, and finish
   88 caught it.** I reduced `SA-0389`'s rename clause to
   `accepted_renames - declared`. It is equal on every real input. But the
   clause no longer passed through `new_only`, so the spec's wrong version 8
   now named a name head never collected. No witness read that name. Finish
   88's spec lens found it, and `SA-0391` pinned it. No host probe runs on a
   review commit, so nothing reruns the wrong versions after one. Recorded on b-9efbe2.
2. **A wrong version's edit removed nothing, and REVIEW filed it as a
   blocker.** `SA-0390` declared "`risk` is left out". The expression's
   reason named the deletion, but its edit kept the whole `find` and
   appended an unused function. The witness passed, and the host kept the
   blocker as recorded disagreement. The Spec seat ran the real deletion,
   and three witnesses killed it. Filed as b-7fc792.
3. **REBUT withdrew ten host probes on `SA-0389`, and both seats agreed.**
   Seven were fixed by folding calls from separate tests into the named
   witness. Three were equivalent under the cell's code, since its clause
   derived from `new_only`. Item 1 shows that equivalence held for that
   one shape of the code alone.
4. **The batch's spec review revised nothing again.** Each spec review
   returned one note, at $2.29 and $2.10.
5. **Both cells ran past their turn ceilings again.** REVIEW took 166 turns
   on `SA-0390`, which has six adequacy probes and nine criteria.
6. **A comment-only follow-up still owes a witness.** `SA-0392` fixed a
   stale comment and added a test that reads the comment's text.
7. **Jev scores one findings block per report.** One seat reviewed both
   follow-ups in one report, and both rounds scored #1204's block. #1205's
   findings went to `run-70-unscored.json`. A combined seat writes one
   report per pull request.

## What the reviews found

- **#1202:** no blocker. One concern, a wrong spec id in the witness
  docstring. Three notes, a cited line range, a restated formula and a
  `fail` call that asserted files alone. All four were fixed. Both seats and
  the critic named a stale `session.py` comment outside `touches`. Finish
  88's `SA-0392` fixed it.
- **#1203:** one blocker. The criterion 2 witness read the `EXHAUSTED` note
  by substring, so the spec's own wrong version passed. Fixed. A review-round
  tag in a comment was dropped. A duplicated test set-up was kept.
- **#1204, #1205:** finish 88's follow-ups, reviewed by one seat holding
  both remits. #1204's one line kills both widenings of the new-name match.
  #1205's test pins the comment's wording, not its reader set. So the
  spec's claim that dropping a reader fails a test overstates it.
  `tests/test_contract.py` pins a comment the same way, and the test was
  kept.

`.saffron/rejections.md` holds six lines for this run.

## Run 69's items, checked

- [ ] **`driver.py check` refuses a spec body that quotes a mutant's
  `find`:** open, on item 080.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.
  This run's ten withdrawals all held.
- [x] **`revert` reads a declared rename:** `SA-0389` (#1202). The
  `FINISH-0` half of b-d2b6b3 stays open.
- [ ] **Specs that edit code put a mutant on the ref:** open, on item 080.
- [ ] **`cite` flags a bare citation into a parent's changed file:** open,
  the other half of b-b664d1.

## Summary: what Saffron should absorb next

1. **A later commit reruns a task's recorded wrong versions.** A gate
   change, on b-9efbe2. This run's one regression came from a review commit,
   and only the end review caught it.
2. **REVIEW refuses a wrong version's edit that removes nothing.** A phase
   change, on b-7fc792.
3. **`driver.py check` refuses a spec body that quotes a mutant's
   `find`.** A gate change, on item 080.
4. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.
5. **`cite` flags a bare citation into a parent's changed file.** A tool
   change, the open half of b-b664d1.

This PR changes no skill text. It records `SA-0391` and `SA-0392` from
finish 88's ran texts.

## Next run

Run 71 takes the next items from `PRIORITY.md` through the spec chain.
