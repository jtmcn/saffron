# Feedback on run-saffron-spec-loop (run 68, 2026-11-13)

Run 68 kept the goal of runs 55 to 67: implement every backlog item. It
queued the three specs the spec chain wrote beside run 67.

| Spec | PR | Outcome | Spend of budget | Turns of ceiling |
|---|---|---|---|---|
| `SA-0384` | #1188 | `READY_FOR_REVIEW` | $17.74 of $30 | 242 of 150 |
| `SA-0385` | #1189 | `READY_FOR_REVIEW` | $8.79 of $26 | 153 of 160 |
| `SA-0386` | #1190 | `READY_FOR_REVIEW` | $20.37 of $22 | 525 of 180 |

Batch 86 ran at `--budget 204` with `--stack --defer-end-review`. The batch
refused $110 and printed the $204 it needed. Turns count every phase, the
spec review included. Finish 86's end review spent $0.60, wrote no follow-up
and committed a finishing layer, #1191. The loop spent $47.50 of $204.

## What the run found

1. **The batch's spec review sent `SA-0386` back twice.** Its writer and
   reviewer spent $12.95 of the task's $20.37. The first blocker was a
   section the spec chain added on seeding a mutant. That section quoted
   the mutant's `find` text in the body, so `refuse_disclosed_mutants` would
   refuse the task once the mutant was seeded. The second was a
   `wrong_versions` entry neither witness could kill. No pre-flight check
   reads a spec's body for a mutant's `find` text.
2. **REBUT's withdrawal on `SA-0384` held.** The implementer added one
   assertion to kill the host's probe. The Spec seat flipped each
   comparison alone and in pairs, and every flip but the equivalent ones
   died. This is the case b-7f6ce2 needs to tell apart from run 67's.
3. **Two cells raised no finding at all.** `SA-0385` and `SA-0386` each had
   four lenses and no finding. The seats then found no blocker either. Their
   probes killed 25 of 27 and every declared wrong version.
4. **`SA-0384`'s witness left its own claim's order unwitnessed.** Its only
   construct defect came last, so a version that returned every new defect
   first passed. Its in-cell adequacy lens drove one probe and missed this.
5. **`SA-0384` made `cite` refuse one of `SA-0385`'s own citations.** The
   batch's spec review uses the old rule, so the cell ran. The spec retires
   here, so no re-cite is owed.

## What the reviews found

- **#1188:** 1 Spec blocker, the text order above. 1 concern, that the
  witness compared defects by line only. Six notes on docstrings, a
  duplicated span line and a test name. All were fixed, with the finish's
  note on the duplicated join, in a review commit and this PR.
- **#1189:** 1 Standards concern, filed as b-e11fb7. One note asked to
  rename a test that a done spec, `SA-0148`, names as its witness. It was
  kept.
- **#1190:** 1 note on the new constant's comment, fixed. One note on a
  prefix-only mutant that criterion 2's witness kills, kept.

`.saffron/rejections.md` holds six lines for this run.

## Run 67's items, checked

- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.
  This run's withdrawal held, so it is no new evidence for or against.
- [x] **`cite` refuses a citation no single construct holds:** `SA-0384`
  (#1188). b-b664d1 stays partial for a bare citation into a parent's file.
- [x] **A reset past six hours waits six hours:** `SA-0385` (#1189).
- [ ] **Specs that edit code put a mutant on the ref:** open, on item 080, with a Record line from this run.
  `SA-0386`'s criterion 3 ran with no mutant, and the chain's advice on
  seeding one refuses the task.
- [ ] **`census` reads a renamed parametrize id as a rename:** open, on
  b-f30189.

## Summary: what Saffron should absorb next

1. **`driver.py check` refuses a spec body that quotes a mutant's `find`.**
   A gate change. The batch's spec review caught it at $12.95, and a
   pre-flight check catches it for free.
2. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.
3. **Specs that edit code put a mutant on the ref.** A gate change, on item
   080.
4. **`cite` flags a bare citation into a parent's changed file.** A tool
   change, the open half of b-b664d1.
5. **`census` reads a renamed parametrize id as a rename.** A gate change,
   on b-f30189.

This PR changes two lines of skill text. `cmd_cite`'s docstring and
pre-flight check 5 now state `SA-0384`'s rule.

## Next run

Run 69 takes the next items from `PRIORITY.md` through the spec chain.
