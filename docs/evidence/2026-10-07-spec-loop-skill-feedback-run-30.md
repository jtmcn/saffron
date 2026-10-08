# Feedback on run-saffron-spec-loop (run 30, 2026-10-07)

Run 30 took the record migration's five specs, `SA-0220` to `SA-0224`. They
form one chain, each spec depending on the one before. The first ran as an
attended cell. The operator then asked for the rest as a batch: "Run the
remaining using batch. It should be the default now." This file ranks what
the delegate still did by hand.

## What happened, in order

1. **Step 1b was skipped.** The spec chain had reviewed all five the day
   before, in two rounds each, and killed every listed wrong version on a
   prototype. `driver.py check` passed all five.
2. **`main` was red.** The first cell's baseline line read `terms=fail` on
   `main`. The `Spec` docstring named "ticket" to forbid it. #720 fixed it at
   the operator's request (b-1e106d).
3. **`SA-0220` ran attended.** It cost $24.57 of $32 and became #722. Its
   seats killed all 38 probes, and the review commit fixed three comments.
4. **The stack batch was refused.** `saffron batch --stack` would not take
   `SA-0221`, whose parent was an open pull request outside the order
   (b-e0e1cf). The queue also refused `SA-0221` until #720 merged, because
   #720 touched a file in its `touches`.
5. **A plain batch ran the other four.** It drained for $86.19 of $130 and
   cut each child at its parent's packaged head. The seats reviewed each
   pull request while the next cell ran.
6. **The review commits came after the chain.** Each child had already been
   cut, so the delegate held every fix as a local commit. After the batch it
   rebased four layers by hand, resolved docstring conflicts twice, and
   pushed all four with leases.
7. **Two layers landed over the size ceiling.** `size` failed every attempt
   of `SA-0223` and `SA-0224`, and only advised at `standard`. The operator
   kept both (b-fbd181).
8. **`stack` saw one pull request.** No batch task had a `record` call. The
   delegate recorded all four by hand (b-cab612).

## Run 29's items, checked

1. **Close each retired spec's item in the finishing commit (b-3c7ce9)**: not
   absorbed. No stack finish ran this run.
2. **A check that each witness drives every part of its claim (b-20043f)**:
   not absorbed. Every batch layer's seats found more of this class. Two
   layers compared `migrated` sorted, and three left a field undriven.
3. **Retry a failed seed (b-6ac0cd, b-60a399)**: not absorbed. No seed failed.
4. **Stack on a reviewable layer from an earlier batch (b-e0e1cf)**: not
   absorbed. It refused this run's chain, and the run fell back to a plain
   batch.
5. **Print the admission arithmetic (b-0a08bf)**: not absorbed. The plain
   batch held back no reserve, so it did not bite.
6. **Log spec sessions where `watch` reads (b-4e1b6d)**: not absorbed, and not
   met. No spec session ran.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-07 are the evidence.

1. **A batch that runs the loop's order, records each task and restacks
   review commits (b-cab612, b-e0e1cf).** A batch and driver change. The
   whole hand-rebase step, and the four `record` calls, came from it.
2. **A check that each witness drives every part of its claim (b-20043f).** A
   lens change. Ten of this run's twenty rejection lines are bucket 1
   `witness`, each a seat probe the critic passed. Two repeated a hole the
   layer below had just had fixed.
3. **Price a measured estimate against what measured specs landed
   (b-fbd181).** A `check` change. Both overruns read as clear before the
   cells ran.
4. **Run `terms` and `prose` over the tree when a rule widens (b-1e106d).** A
   gate change. It cost a hand pull request mid-loop.
5. **Check that a spec's named symbols exist at base (b-cd41ac).** A spec
   review change.

## The loop's own gaps

- **Seats stay.** Every batch layer's seats found a blocker the in-cell
  critic passed, and on #722 the Standards seat found three comment defects
  no lens raised. The critic's citation checks miss a wrong section.
- **Seats ran during the batch.** Reviewing layer N while cell N+1 ran saved
  wall clock. Holding fixes as local commits made the restack a hand step.
- **The real ledger is a witness.** The Spec seats migrated a backup of the
  live ledger on three layers. They checked 239 tasks and 5,320 gate results
  with none refused and no row differing, which no fixture covered.
- **Jev scored every round.** The worktree guard's allow rule for the key
  worked. Ten rounds were scored and labelled.
- **`labels` reads no cell round.** It walks `spec-review` and `pr-review`
  only. The five cell rounds were scored and labelled by hand under
  `~/.saffron/batches/v0/`, and nothing checks or reads those labels.
