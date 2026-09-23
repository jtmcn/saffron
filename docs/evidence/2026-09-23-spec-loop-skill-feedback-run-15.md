# Feedback on run-saffron-spec-loop (fifteenth run after the rework, 2026-09-22 to 23)

Eight specs were snapshotted, and six ran. `SA-0129` and `SA-0133` were dropped
to the next loop when their parent `SA-0128` halted. Run 14's feedback is
checked below.

**Outcome:** stack #484 is six pull requests, all marked ready. Six cells cost
**$81.97** against $118 of their budgets. The order's total budget was $160.

| Spec | PR | Spent | Outcome | Step 1b rounds |
|---|---|---|---|---|
| `SA-0127` | #476 | $10.28 of $18 | `READY_FOR_REVIEW` | 2 |
| `SA-0125` | #473 | $12.36 of $22 | `READY_FOR_REVIEW` | 1 |
| `SA-0126` | #478 | $22.12 of $24 | `READY_FOR_REVIEW` | 2, one at the parent branch |
| `SA-0128` | #483 | $19.75 of $24 | halted at `REBUTTING`, opened by hand | 3, two at the parent branch |
| `SA-0130` | #480 | $3.13 of $12 | `READY_FOR_REVIEW` | 1 |
| `SA-0131` | #481 | $14.33 of $18 | `READY_FOR_REVIEW` | 2 |

## What happened, in order

1. **The snapshot took in eight specs when the operator asked for four.**
   Four children became runnable once `SA-0125` joined the order. The
   delegate asked, and the operator chose all eight.
2. **Step 1b found two scope blockers.** `SA-0127` contradicted `DESIGN.md`
   §5.4's rule that partial results are not results. The operator had the
   exception written into §5.4 before the cell ran (#471). `SA-0131` read
   every nonzero git exit as "not landed". The delegate measured that a
   missing commit and an unreadable mirror both exit 128. The operator had
   the callable raise instead.
3. **The delegate's own edits carried findings again.** `SA-0131`'s round 2
   found a blocker in the round-1 edit. `SA-0128`'s round 3 found a count and
   a number the round-2 edit left wrong. Runs 7, 10, 11, 13 and 14 showed the
   same pattern.
4. **Deferred step 1b concerns came back.** `SA-0126`'s concern about the
   re-queue cap's key was sent to the Spec seat. The in-cell adequacy lens
   found the spec-id half, which cost a REBUT of about $4.80. The Spec seat
   found the repo and state halves. `SA-0130`'s concern about the new
   paragraph's sense came back as a Standards blocker.
5. **A probe was counted killed by the format test.** On `SA-0127`, the
   adequacy lens's probe lengthened a line past the formatter's width. The
   format test failed, and `probes.json` recorded a kill. The witnesses never
   failed, and the Spec seat showed the probe survives. Item b-19b255.
6. **A verdict session too large for argv halted a cell.** `SA-0128`'s REBUT
   fixed a real hole. The lens's re-judge then failed with `Argument list too
   long`, and the task stopped at `REBUTTING` with no PR. The operator took it
   by hand as #483, and the Spec seat judged the rebuttal sound. Item
   b-8487de.
7. **Baseline subtraction hid a `preserves` witness's mutant.** `SA-0127`'s
   base had `witness=fail`, so a cell that never strengthened the witness
   would still pass. This cell did strengthen it. The delegate checked by hand.
   Item b-6377cf.
8. **Every pull request needed a review commit.** The seats found eleven
   blockers the critic missed, all witness or build holes. Each was verified
   with `driver.py probe` before and after the fix.
9. **`terms` failed at base in every cell.** It fails on `Never a ticket` at
   `saffron/intake.py:133`, which names avoided words to exclude them. Item
   b-f4eb52.
10. **Two branches ended within 16 lines of their ceilings.** `SA-0131` landed
    at 299 of 300 lines. `SA-0128` landed at 584 of 600.
11. **The event log held counts and no identities.** `SA-0128`'s attempt 1
    failed `census` on three ids that `events.jsonl` did not name. Item
    b-66e82d.

## Run 14's items, checked

- A spec estimated within 20% of its ceiling is split: `SA-0129` builds the
  check and moved to the next loop. The shape recurred (point 10).
- b-2dea1c: `SA-0130` delivered it (#480). Review narrowed the paragraph, so
  the one run of a new test against unfixed code stays with the cell.
- The driver taking a hand-merged parent: `SA-0131` delivered b-111c56 (#481).
  A halted task still needed a hand-opened PR and a hand-linked stack.
- A tightening edit names the wrong version it must kill: done for every edit
  this run. The edits still carried findings (point 3).
- b-440f17: recurred in every pull request, with three new shapes.

## Summary: what to change first

1. **b-19b255.** A probe counts as killed only when a criterion's witness or
   a new test fails by assertion. Today REVIEW can report a hole as covered.
2. **b-8487de.** The verdict prompt goes by stdin, and a verdict session that
   cannot start is `error`. Today a large diff halts the task for the operator.
3. **b-6377cf.** A mutant that survives at base is not subtracted.
4. **Step 1b fixes a concern about a witness's selection in the spec.** Sending
   it to the Spec seat cost a REBUT and a review commit on `SA-0126`. This is
   a skill change, until check 3 can measure an arrangement that needs code
   the spec has not built.
5. **b-440f17**, now with the net-count and attribute-docstring shapes.
