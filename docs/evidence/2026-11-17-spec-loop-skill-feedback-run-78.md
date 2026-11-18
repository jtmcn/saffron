# Feedback on run-saffron-spec-loop (run 78, 2026-11-17)

Run 78 kept the goal of runs 55 to 76: implement every backlog item. It took
`SA-0406` and `SA-0407`, the two specs the chain wrote for b-f7a591. Batch
95's finish then ran two follow-ups.

| Spec | PR | Outcome | Spend of budget | Turns of ceiling |
|---|---|---|---|---|
| `SA-0406` | #1247 | `READY_FOR_REVIEW` | $23.00 of $50 | 369 of 240 |
| `SA-0407` | #1250 | `READY_FOR_REVIEW` | $48.46 of $54 | 605 of 240 |
| `SA-0412` | #1252 | `READY_FOR_REVIEW` | $3.59 of $10 | 87 of 40 |
| `SA-0413` | #1254 | dropped, PR closed | $5.23 of $10 | 121 of 60 |

Batch 95 ran at `--budget 280` with `--stack --defer-end-review`. It held a
$70 reserve. The four tasks spent $80.28. Turns count every phase.

While the batch ran, the spec chain wrote and merged five specs: `SA-0408`
(#1246), `SA-0409` (#1248), `SA-0410` (#1249), `SA-0411` (#1251) and
`SA-0414` (#1253).

## What the run found

1. **REBUT withdrew every blocker, and both PRs still held blockers.** The
   seats found six blockers on two PRs. `SA-0406`'s REBUT fixed a witness
   with a spy on a private helper, and the implementer said the two forms
   were equal through the public result. `SA-0407`'s REBUT fixes asserted a
   state where the claims name a line or a record. Each surviving probe was
   measured.
2. **A finish follow-up undid a review decision.** Finish 95's end review
   read `SA-0406` at its reviewed head. It held that the witness could not
   tell the filter form from the full list. That form is equivalent by
   behaviour, and the review had removed the spy on purpose. The follow-up
   `SA-0413` put the spy back. I dropped it and closed #1254.
3. **A spec id was taken twice.** The `b-cafacd` writer took `SA-0412`, and
   the finish minted a follow-up there. It moved to `SA-0413`, and the
   finish minted a second follow-up there. The spec landed as `SA-0414`.
4. **Every spec chain hit check 65's class.** Five chains ran two rounds
   each. Eight of the ten rounds found a blocker, and seven of those were a
   set whose deciding member sat at an edge, or a step after the decisive
   one that no witness observed.
5. **A seat's patch failed lint.** The `SA-0407` Spec seat's diff used `l`
   as a name, and `make check` refused it.

## What the reviews found

- `SA-0406`: one Spec blocker, a renumbered guard that survived but for the
  spy. Three Standards concerns: a restated `probe_key`, three wrong
  criterion numbers, and the same spy. All fixed.
- `SA-0407`: five Spec blockers, each a state asserted where the claim names
  a line, a record or a lens. One Standards concern, a docstring that
  contradicted criterion 2. All fixed. A suggested refactor of `cut` was
  rejected, since it changed which end a cut takes.
- `SA-0412`: no blocker. The witness copies the `prose` rule, kept until
  b-6b8896 lands.

## Run 76's items, checked

- [ ] **A wrong version's edit changes only the case it names:** open, on
  b-f06097, parked on the operator.
- [ ] **A finish drops a finding REBUT fixed:** open, and it recurred in a
  new shape. Finish 95 graded a finding the review had settled, and its
  follow-up undid the review (item 2 above).
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2,
  parked.
- [ ] **A declared wrong version dies on its own criterion's witness:**
  open, a question for the operator.
- [ ] **`integrity` reads a fixture's spec id as data:** open, on b-988eb9.
- [ ] **A finish prices a follow-up's ceilings from past follow-ups:** open.
  Both follow-ups fit their $10 this time.
- [ ] **`driver.py check` refuses a spec body that quotes a mutant's
  `find`:** open. The `SA-0411` reviewer caught one by hand.
- [ ] **The driver fills the seat prompts and saves the reports:** open.
  `mkseat.py` and `save_report.py` still run from the scratchpad.
- [ ] **`cite` flags a bare citation into a parent's changed file:** open.
- [ ] **`driver.py stack` links a finish's layer:** open. Finish 95
  committed nothing, so it did not arise.
- [ ] **`bookkeeping` runs the smoke test's flat corpus:** open.

## Summary: what Saffron should absorb next

1. **A lens judges whether REBUT's fix observes behaviour.** A lens change,
   with no item yet. Item 1 is the evidence: six blockers passed a REBUT
   that withdrew everything.
2. **A finish reads a review commit's rationale before it grades.** A phase
   change, with no item yet. Items 2 here and 2 of run 76 are the evidence.
3. **`next-id` reserves an id for a draft.** A tool change, on b-90c8fa.
4. **A wrong version's edit changes only the case it names.** A phase
   change, on b-f06097, once the operator picks its arm.
5. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.
6. **The `prose` gate reads an irregular participle.** A gate change, on
   b-6b8896.
7. **`integrity` reads a fixture's spec id as data.** A gate change, on
   b-988eb9.
8. **`driver.py check` refuses a spec body that quotes a mutant's
   `find`.** A gate change, on item 080.
9. **The driver fills the seat prompts and lints a seat's patch.** A tool
   change, with no item yet.
10. **`cite` flags a bare citation into a parent's changed file.** A tool
    change, the open half of b-b664d1.
11. **`driver.py stack` links a finish's layer.** A tool change, with no
    item yet.
12. **`bookkeeping` runs the smoke test's flat corpus.** A tool change, with
    no item yet.

This PR changes no skill text.

## Next run

Run 79 runs `SA-0408`, `SA-0409`, `SA-0410`, `SA-0411` and `SA-0414` in one
`--stack` batch.
