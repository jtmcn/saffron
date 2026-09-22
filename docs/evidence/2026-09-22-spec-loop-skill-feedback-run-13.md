# Feedback on run-saffron-spec-loop (thirteenth run after the rework, 2026-09-22)

Five specs: `SA-0119` (item b-461729, with b-a70ec1 folded in), `SA-0120` (the
child half of item b-2750d5), `SA-0122` (item b-e403c1), `SA-0118` (item 103)
and `SA-0121` (item 89's remainder). Run 12's feedback is checked below.

**Outcome:** five pull requests, stacked #431, #434, #436, #433 and #435 in that
order and marked ready. Four reached `READY_FOR_REVIEW`. `SA-0118` ended
`EXHAUSTED` with a correct diff, and the operator opened #433 by hand. Five
cells cost **$45.76** against $93 of budgets.

| Spec | PR | Spent | Outcome | Step 1b rounds |
|---|---|---|---|---|
| `SA-0119` | #431 | $8.59 of $20 | `READY_FOR_REVIEW` | 1 |
| `SA-0120` | #434 | $16.40 of $24 | `READY_FOR_REVIEW` | 4 |
| `SA-0122` | #436 | $5.78 of $17 | `READY_FOR_REVIEW` | 3, one at the parent branch |
| `SA-0118` | #433 | $10.45 of $20 | `EXHAUSTED`, opened by hand | 2 |
| `SA-0121` | #435 | $4.54 of $12 | `READY_FOR_REVIEW` | 1 |

## What happened, in order

1. **`driver.py jev` refused a review saved as prose.** It printed "the report
   has no fenced json block of findings". The first `SA-0122` review was saved
   without that block and had to be saved again.
2. **A deferred concern cost a whole cell.** Step 1b flagged `SA-0118`'s sha1
   literal in round 1, not as a blocker, and the delegate deferred it. The
   in-cell adequacy lens caught it. REBUT's fix passed at base, and `revert`
   refused it. Item b-4a63b7.
3. **No record named the gate that failed after REBUT.** The log said
   `gates: 1 new failures after the rebuttal`. Finding `revert` took running
   every gate by hand. Item b-66e82d.
4. **No driver command takes an `EXHAUSTED` branch.** `size` says "not
   reviewable, so it has no stack to sit in", and `stack` leaves it out. The
   operator linked it with `gh stack link 431 434 436 433 435` and marked it
   ready by hand. GOTCHAS covers a `REBUTTING` branch taken by hand, and not an
   `EXHAUSTED` one.
5. **The round-4 split cost what it predicted on `SA-0120`.** Both witness-only
   findings deferred to `{KNOWN}` came back as Spec-seat blockers, and each took
   one assertion to fix.
6. **The delegate's own edits carried findings again.** Three of `SA-0120`'s
   four step 1b blockers came from its edits: the drop-rate witness, the single
   strip, then the identical-finding gap. Runs 7, 10 and 11 showed the same
   pattern.
7. **The seats used the "Already raised" list.** Both deferred `SA-0120`
   witness gaps and the `SA-0118` move-aside hole were confirmed and fixed from
   it.
8. **Every Standards seat found prose the `prose` gate misses in Python.** It
   happened in all five pull requests. Item b-440f17 carries the counts.

## Run 12's items, checked

- b-36b551, the wall cut: did not recur. No cell logged a cut turn.
- b-2750d5, the in-cell half: done by #434. The seats still found witness holes
  in #433, #434 and #436, and all three cells ran before #434 merged.
- b-440f17, `prose` reaching Python: recurred in all five pull requests.
- b-0de0b3, the loop's history collected by hand: still true. This record was
  written from a scratch file again.
- b-89ec93 and b-e8027b: no instance is in this run's notes.

## Summary: what to change first

1. **b-4a63b7**. It turned a sound fix into `EXHAUSTED`, and it will recur
   wherever REBUT answers a surviving probe with a new test.
2. **A deferred step 1b concern that changes what the cell builds is a
   blocker.** The round-4 split holds for witness-only findings, which cost one
   assertion each. The sha1 literal changed the build, and it cost a cell.
3. **The driver takes an `EXHAUSTED` branch the operator keeps.** `size` and
   `stack` accept it, and GOTCHAS names the steps.
4. **b-66e82d**. A red rebuttal names its gate.
5. **A saved review keeps the reviewer's whole report.** The reviewer ends on a
   fenced json block (`.claude/agents/spec-reviewer.md:144`), and a prose
   summary saved in its place loses it.
