# Feedback on run-saffron-spec-loop (run 53, 2026-11-03 to 2026-11-04)

Run 53's order was `SA-0333`, then `SA-0330` stacked on it. The specs carried
$84 of budget. Neither cell landed its spec.

- The delegate built `SA-0333` by hand as #1014.
- `SA-0330`'s cell ended `EXHAUSTED`, and the operator chose to adopt it as
  #1016.
- #1014 merged during the run. #1016 is reviewed and marked ready.

| Spec | PR | Outcome | Spend of budget | Peak turns of ceiling |
|---|---|---|---|---|
| `SA-0333`, first cell | none | `NOT_IMPLEMENTED` | $4.81 of $44 | 42 of 240 |
| `SA-0333`, rerun | none | `PLAN_REJECTED` | $1.57 of $44 | 44 of 240 |
| `SA-0333`, by hand | #1014 | merged | no cell spend | none |
| `SA-0330` | #1016 | `EXHAUSTED`, adopted | $41.67 of $40 | 201 of 200 |

Batch 65 ran at a $200 ceiling and batch 66 at $190. Finish 65 had nothing to
finish, and finish 66 refused. The run spent about $48.05 in cells.

## What the run found

1. **A connection lost after a completed turn ended `NOT_IMPLEMENTED`.**
   `SA-0333`'s first cell lost the API mid-IMPLEMENT, after the plan was
   accepted. The batch then refused `SA-0330` for its parent. b-031ac2 covered
   only a session with no completed turn. Filed as b-f011f3.
2. **A fix to the plan checkpoint could not pass the checkpoint it fixed.** The
   rerun priced its 380-line plan at 1520 tokens against 1300, since tests
   still counted. Filed as b-0ac661.
3. **A by-hand merge left its child refused.** `adopt` refused the
   `PLAN_REJECTED` row. After #1014 merged, the queue still read `SA-0333` as
   `PLAN_REJECTED`. #1015 retired the spec, at the cost of a merge. Filed as
   b-bece8b.
4. **REPAIR could not find the cases its survived mutants named.** `SA-0330`
   passed every gate but `witness` from attempt 2 on. Each failure named a
   claim of about a dozen sentences. The repair turns hunted mutants of their
   own, and the cell hit its turn ceiling. Each missing case took the delegate
   one test block. Filed as b-fa4a83.
5. **A cell cited the wrong spec at 20 sites.** Every new comment in #1016
   said `SA-0332`, and no gate read it. Both seats found it. Filed as b-249808.
6. **An adopted task is still no layer.** `saffron finish 66` refused with
   "batch 66 holds no layer". b-323c97 recurs.
7. **The Spec seat still found six witness blockers.** No in-cell critic ran
   on either PR. On #1016, five named claims and one column witness let a
   named wrong version pass. Each was a member of a set the claim named and
   the witness never drove.
8. **The delegate told the seats that no batch spec review ran for `SA-0330`.**
   One did, at $4.12, with two notes. The delegate read the log, which never
   prints it, and not the ledger.

## What the reviews found

- **#1014:** the seats raised 6 findings. Review commit `814a66fd` fixed 3,
  one needed no action, and 2 are b-8c6696.
- **#1016:** the seats raised 17. Review commits `cf2e73fe` and `215cd6f5`
  fixed 14. One needed no action, and 2 are b-9bb8b7. `37089b1c` fixed the two
  gaps the `witness` gate found.

`.saffron/rejections.md` holds ten lines for this run. The Standards seat's
out-of-scope finding on #1014 is b-a19ffd.

## Run 52's items, checked

- [x] **The plan checkpoint prices what `size` counts (b-15db6e):** done, #1014.
- [ ] **A citation's construct is checked at the spec's own base (b-b664d1):**
  open. It did not recur, since `SA-0330`'s 54 citations resolved at `main`.
- [ ] **A finish fixes a one-line finding in its layer (b-4a9207):** open. No
  finish ran.
- [ ] **The adequacy lens probes each member of a set:** open, and it recurs.
  Finding 7 is the same class, with no lens run at all.
- [ ] **A spec review keeps its findings when extraction fails (b-298b1c):**
  open. It did not recur.
- [ ] **`check` leaves a citation the batch can move as a note:** open. It did
  not recur.
- [ ] **`record` and the ledger agree on a task's spend:** open, and it
  recurs. The watch said $37.54 at `EXHAUSTED`, and `record` said $41.67.

## Summary: what Saffron should absorb next

1. **A survived mutant tells REPAIR which part of its claim went untested
   (b-fa4a83).** A gate change in `saffron/gates/core/witness.py`. It cost a
   whole cell this run.
2. **A by-hand merge satisfies a child's `depends_on` (b-bece8b).** A queue
   change. It cost a PR and a merge.
3. **A lost connection never decides a task (b-f011f3).** A phase change. It
   cost a cell and the batch's second spec.
4. **A gate checks the spec ids a diff cites (b-249808).** A gate change.
5. **An adopted task is a layer of its batch (b-323c97).** A phase change,
   unchanged from run 51.
6. **The adequacy lens runs on a diff the cell could not finish.** A phase
   change. Six blockers reached the seats with no lens run.
7. **`record` prints the spec review's findings.** A driver change. It would
   have kept finding 8 from the seats' brief.

This PR changes no skill text.

## Next run

Nothing is queued. The operator asked for specs for the next three tier-1
items in `PRIORITY.md`.
