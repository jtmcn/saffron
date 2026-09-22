# Feedback on run-saffron-spec-loop (fourteenth run after the rework, 2026-09-22)

Two specs: `SA-0123` (item b-fd1468, the writer half) and `SA-0124` (item 171),
a child of `SA-0123`. Run 13's feedback is checked below.

**Outcome:** `SA-0123` ended `EXHAUSTED`, and the operator had #451 opened by
hand, reviewed and merged. `SA-0124` then ran from `main` and reached
`READY_FOR_REVIEW` as #459. Two cells cost **$48.59** against $56 of budgets.

| Spec | PR | Spent | Outcome | Step 1b rounds |
|---|---|---|---|---|
| `SA-0123` | #451 | $38.20 of $32 | `EXHAUSTED`, opened by hand | 2 |
| `SA-0124` | #459 | $10.39 of $24 | `READY_FOR_REVIEW` | 2, one at the parent branch |

## What happened, in order

1. **Step 1b found the production path unwitnessed.** `SA-0123`'s criteria 1
   and 6 drove only a ledger with a record attached, and no production caller
   builds one. The delegate added a no-record half to each.
2. **The delegate's own edit carried a finding again.** Round 2 found that a
   note the delegate wrote asked criterion 13 to fail a case its witness could
   not see. Runs 7, 10, 11 and 13 showed the same pattern.
3. **A git claim was settled in a minute.** `SA-0124` claimed an empty-file
   patch applies on the host's git. One `container run` in
   `saffron/cell-base:python` showed git 2.39.5 applies it too.
4. **The turn bound cut two of `SA-0123`'s turns.** IMPLEMENT and the first
   REPAIR each hit the fifteen-minute bound. IMPLEMENT spent its turn running
   the spec's list of wrong versions. Item b-2dea1c.
5. **Step 1b's size concern was right.** The review warned the prototype sat at
   865 of 1000 lines, and `SA-0117` had landed at 979. The delegate cut 90
   lines from the spec. The cell still landed at 1001 and ended `EXHAUSTED`.
6. **An `EXHAUSTED` branch was kept by hand again.** `size` and `stack` refuse
   one, as run 13 found. The delegate opened #451 and measured `size` with the
   gate's own `_changed_lines`.
7. **A hand merge left the child refused.** After #451 merged, `next` and
   `saffron queue` still refused `SA-0124` on its `EXHAUSTED` parent. The
   delegate started the cell by spec path. Item b-111c56.
8. **Both clean-looking results hid witness holes.** `SA-0124`'s three lenses
   raised nothing. The Spec seat then found two witnesses a wrong writer
   passed. One was criterion 4, whose spec text the delegate had tightened to
   "the integers 3 and 4". The witness compared with `==`, so 3.0 passed.
9. **Every Standards seat found prose the `prose` gate misses in Python.** It
   happened in both pull requests. Item b-440f17 carries the counts.
10. **Jev refused the second two-seat review.** It answered
    `max_tokens_exceeded` for `SA-0124`'s pull request review, so that round
    has no score.
11. **DNS failed for about four minutes.** A push failed and was retried in a loop.
    The first retry printed exit 0 from `tail` while the push had failed.

## Run 13's items, checked

- b-4a63b7, REBUT's witness and `revert`: did not recur. No REBUT ran.
- A deferred step 1b concern that changes the build: not deferred this time.
  The size concern was acted on, and it still cost a cell.
- The driver taking an `EXHAUSTED` branch: recurred, point 6.
- b-66e82d: did not arise.
- Saving the reviewer's whole report: done for every round.

## Summary: what to change first

1. **A spec whose estimate is within 20% of its ceiling is split before its
   cell.** `SA-0117` and `SA-0123` both landed within 25 lines of 1000.
2. **b-2dea1c.** The host runs the wrong versions a spec names, and the cell
   is not asked to.
3. **The driver takes an `EXHAUSTED` branch the operator keeps**, and counts a
   hand-merged parent as merged (b-111c56).
4. **A spec edit that tightens a witness names the wrong version it must kill.**
   "The integers 3 and 4" named none, and the cell wrote `==`.
5. **b-440f17**, which recurred in every pull request of runs 11 to 14.
