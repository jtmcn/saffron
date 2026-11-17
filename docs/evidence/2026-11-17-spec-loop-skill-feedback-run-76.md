# Feedback on run-saffron-spec-loop (run 76, 2026-11-17)

Run 76 kept the goal of runs 55 to 75: implement every backlog item. It took
`SA-0403`, `SA-0404` and `SA-0405`, the three specs the chain wrote for
b-d9a027.

| Spec | PR | Outcome | Spend of budget | Turns of ceiling |
|---|---|---|---|---|
| `SA-0403` | #1239 | `READY_FOR_REVIEW` | $30.02 of $46 | 302 of 200 |
| `SA-0404` | #1240 | `READY_FOR_REVIEW` | $41.07 of $46 | 387 of 200 |
| `SA-0405` | #1241 | `READY_FOR_REVIEW` | $16.58 of $30 | 200 of 170 |

Batch 94 ran at `--budget 300` with `--stack --defer-end-review`. It held a
$75 reserve. Finish 94 spent $8.61 on the end review and committed a
citation refresh as #1242. It ran no follow-up. The run spent about $96 of
$300. Turns count every phase.

## What the run found

1. **All three cells passed REBUT, and two PRs still held a blocker.** The
   `SA-0403` witness compared one of three pairs whole. The `SA-0404` witness
   never collected its canary's witness, and its moved policy changed only
   the env. This is the class runs 13 to 75 keep naming.
2. **REBUT's re-run accepts a kill by any test.** `SA-0404`'s REBUT fixed ten
   blockers by fixture changes. Two of its re-run probes were killed by
   criterion 2's witness, not criterion 1's (`rebut-probes.json`). The
   lens withdrew both. b-c9a913 made that rule: another test's kill names a
   misnamed witness, not a blocker. The Spec seat held each declared wrong
   version to its own criterion's witness, and the fix cost one line.
3. **REBUT confirmed two blockers for the host to judge.** On `SA-0403` the
   empty-head witness checked only that a diff was non-empty. A review
   commit fixed it. On `SA-0405` a `preserves` witness never moves HEAD, and
   the file was `forbidden`. Both seats agreed with the implementer's
   argument, and it is filed as b-c1259f.
4. **Finish 94 graded two findings REBUT had already fixed.** Both read
   `unverified`, since their lines moved. Run 75 saw three.
5. **The finish refreshed its own citations.** Its layer, #1242, rewrote four
   stale line ranges in `SA-0404`'s spec. Run 75 needed a spec PR and an
   operator prompt for the same kind of refresh.
6. **A cell split a literal to pass `integrity`.** `SA-1` in a fixture string
   read as a citation of an unknown spec. The operator kept the split, and
   the gate's false positive is b-988eb9.
7. **Every layer took its review commit after the batch drained.** Each
   restack replayed cleanly, and no hold blocked a push for long.

## What the reviews found

- **#1239:** the own-pairs witness checked two pairs in part, and the
  empty-head witness only that a diff was non-empty. Three notes covered a
  wrong field name, an unread field and a docstring count. All were fixed.
- **#1240:** two declared wrong versions and three policy reads passed the
  main witness. Notes covered loose output asserts, an unannotated stub, an
  inert flag and a misplaced credit. All were fixed. REBUT's extra survivor
  makes the witness expect 4 failures where the spec says 3, and that stays.
- **#1241:** a docstring dropped the witness from the guard text, a comment
  cited a missing file, and a docstring used perfect tense. All were fixed.
  The split literal and the unmoved `preserves` witness were filed.

`.saffron/rejections.md` holds seven lines for this run. b-d9a027 closes.

## Run 75's items, checked

- [ ] **A wrong version's edit changes only the case it names:** open, on
  b-f06097. Its record now holds the backtest and the operator's question.
- [x] **`regate` asks the recorded wrong versions of a review commit:**
  landed in `SA-0403` and `SA-0404`. `SA-0405` closed the REBUT half.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.
- [ ] **A finish drops a finding REBUT fixed:** open, with no item. Item 4
  is both of finish 94's findings.
- [ ] **A finish prices a follow-up's ceilings from past follow-ups:** open,
  with no item. Finish 94 ran no follow-up.
- [ ] **`driver.py check` refuses a spec body that quotes a mutant's
  `find`:** open, on item 080.
- [ ] **The driver fills the seat prompts and saves the reports:** open,
  with no item. The scratch helpers did both again.
- [x] **`cite` writes the refresh it flags:** the finish layer wrote one
  for `SA-0404` with no prompt. Before a batch it is still a spec PR.
- [ ] **`cite` flags a bare citation into a parent's changed file:** open,
  the other half of b-b664d1.
- [ ] **`driver.py stack` links a finish's layer:** open. The finish linked
  its own layer this run, and step 5's PR still goes on top by hand.
- [ ] **`bookkeeping` runs the smoke test's flat corpus:** open. No
  retirement this run owed a change.

## Summary: what Saffron should absorb next

1. **A wrong version's edit changes only the case it names.** A phase
   change, on b-f06097, once the operator picks its arm.
2. **A finish drops a finding REBUT fixed.** A phase change, with no item
   yet. Five findings across two finishes were graded and dropped.
3. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.
4. **A declared wrong version dies on its own criterion's witness.** A gate
   question for the operator. b-c9a913 settled the other way, and item 2
   is the evidence for asking again.
5. **`integrity` reads a fixture's spec id as data.** A gate change, on
   b-988eb9.
6. **A finish prices a follow-up's ceilings from past follow-ups.** A phase
   change, with no item yet.
7. **`driver.py check` refuses a spec body that quotes a mutant's
   `find`.** A gate change, on item 080.
8. **The driver fills the seat prompts and saves the reports.** A tool
   change, with no item yet.
9. **`cite` flags a bare citation into a parent's changed file.** A tool
   change, the open half of b-b664d1.
10. **`driver.py stack` links a finish's layer.** A tool change, with no
    item yet.
11. **`bookkeeping` runs the smoke test's flat corpus.** A tool change, with
    no item yet.

This PR changes no skill text.

## Next run

Run 77 takes the next backlog items through the spec chain, starting with
b-7f6ce2.
