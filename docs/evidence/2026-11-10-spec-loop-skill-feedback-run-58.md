# Feedback on run-saffron-spec-loop (run 58, 2026-11-10)

Run 58 kept the goal of runs 55 to 57: implement every backlog item. It ran
the two specs the chain wrote this session, in one batch, as one stack of two.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0360` | #1117 | `EXHAUSTED`, then adopted to `READY_FOR_REVIEW` | $43.27 of $60 |
| `SA-0361` | #1118 | `READY_FOR_REVIEW` | $20.79 of $30 |

The two cells spent $64.06 against $90 of spec budgets. Batch 76 ran at
`--budget 212`, the total `saffron queue --stack` printed. It drained, and
deferred its end review with a $53 reserve. Finish 76 runs after this stack
merges.

Before the batch, the delegate closed four items by hand: b-d1c277 (#1110),
b-d39d9a (#1111), b-2d2014 (#1114) and b-60d804 (#1116). Run 57's stack
closed b-f73cd0.

## What the run found

1. **REBUT turned a green cell red, and nothing repaired it.** `SA-0360`
   passed every gate on attempt 1. REVIEW filed seven host criterion probes.
   REBUT killed all seven, then wrapped a call missing a required argument
   in `pytest.raises`. `types` and `tests` failed, and the task ended
   `EXHAUSTED`. `SA-0311` gave a repair turn to the form gates alone, so
   b-0bd346 is reopened.
2. **The hand path cost two re-gates.** The delegate fixed the test, opened
   #1117 and ran `saffron adopt`. Its first re-gate failed on the two
   commit-id tests #1112 fixes, while a `make check` ran beside it. The
   retry, run alone, passed.
3. **The seats found five witness blockers after every probe was killed.**
   On #1117 three witnesses let a probe survive, one per criterion. On
   #1118 `_format_budget` rounded past six digits, and the default-budget
   case passed the flag. Run 54's finding 5 recurs.
4. **Every standing concern recurred in both seats.** Three concerns stood
   across the two cells, and both seats raised each one again. `SA-0360`
   is the fix, so run 59's cells are its first test.
5. **`record` read a branch it had not fetched.** It printed "the branch's
   copy is unreadable" for `SA-0361`, as it did for `SA-0356`. Run 57's
   finding 7 recurs.
6. **The budget refusal and the concern table had no `DESIGN.md` line.**
   Both specs held `DESIGN.md` in `forbidden`. This PR adds a sentence to
   §4.2.1 and one to §5.7.

## What the reviews found

- **#1117:** the seats raised 3 blockers, 3 concerns and 3 notes. Two
  concerns were one finding. Review commit `1a02a5be` fixed all of them.
  `1dd3e5a5` fixed the `types` failure first.
- **#1118:** the seats raised 2 blockers, 2 concerns and 6 notes, with
  three findings raised twice. Review commit `6ca6b1b8` fixed every one but
  the §4.2.1 sentence, which this PR adds.

`.saffron/rejections.md` holds seven lines for this run.

## Run 57's items, checked

- [x] **REBUT answers each concern as it answers a blocker (b-31e3c8):**
  landed in #1117.
- [x] **REBUT draws from REVIEW's pool (b-d39d9a):** closed by #1111.
- [x] **A batch refuses an order its task share cannot hold (b-fe3488):**
  landed in #1118. Run 57 said no item held it. b-fe3488 did.
- [ ] **A form-gate failure after REBUT gets one repair turn (b-8826cf):**
  open. Finding 1 is the same gap for a gate that is not a form gate.
- [ ] **A stack batch's citation rewrite maps lines through the parent's
  diff (b-c7858c):** open. No layer of this run had a parent.

## Summary: what Saffron should absorb next

1. **Any gate REBUT turns red gets one repair turn (b-0bd346).** A phase
   change. It cost this run a $43 cell and a hand adoption.
2. **The adequacy lens drives each member of a set a claim names.** A lens
   change. Five witness blockers reached the seats after every host probe
   was killed.
3. **A finish grades each layer's reviewed head (b-4a9207).** A phase
   change. Finish 74 and finish 75 pooled concerns already fixed.
4. **`record` fetches the branch before it reads the spec copy.** A driver
   change. It recurred in runs 57 and 58.

This PR changes no skill text.

## Next run

The queue is empty. Finish 76 runs once this stack merges. New
specs come from the backlog through `create-saffron-spec`.
