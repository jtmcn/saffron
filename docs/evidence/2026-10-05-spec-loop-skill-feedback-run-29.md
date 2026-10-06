# Feedback on run-saffron-spec-loop (run 29, 2026-10-05)

Run 29 is stage 2 of the delegate-loop plan. It wrote three specs by hand and
ran four through two `saffron batch --stack` batches. No attended cell ran.
`docs/evidence/2026-10-05-first-stack-batch.md` holds the batch facts and the
seat table. This file ranks what the delegate still did by hand.

## What happened, in order

1. **The specs took one hand review each.** The operator said "the spec write
   and review process takes too long". The delegate then applied each
   review's findings itself, with no second round. Drafts took 18 to 27
   minutes and reviews 4 to 7.
2. **The budget rule was stale.** `--stack` holds back two quarters of
   `--budget`, not one. The delegate found it in `saffron/cli.py`. The queue
   printed nothing that showed it (b-0a08bf).
3. **`saffron watch` showed nothing for the first quarter hour.** A spec
   review logs no events (b-4e1b6d). The operator asked for it filed at once.
4. **Batch 13 lost its third layer to a seed error.** `SA-0206` failed to
   seed (b-6ac0cd), and `SA-0207` was refused as its descendant (b-60a399).
5. **Both finishes escalated.** Each retired its specs and closed no item, so
   the records test went red (b-3c7ce9). The delegate linked both stacks.
6. **Batch 14 waited for a merge.** It could not stack on batch 13's unmerged
   layers (b-e0e1cf). The operator merged #692 first.
7. **The seats found five witness holes the end review passed.** The end
   review raised nothing on any layer.

## Run 28's items, checked

1. **Run a wrong version against a test file (b-34d743)**: not absorbed. No
   spec this run had a test as its subject.
2. **Let `reconcile` read an `EXHAUSTED` row (b-8e30bd)**: not absorbed. No
   layer ended `EXHAUSTED`.
3. **A check that each witness drives every part of its claim (b-20043f)**:
   not absorbed. The seats found five more holes of this class.
4. **Print no stopping line before a REBUT that runs (b-444bed)**: not
   absorbed. Not seen this run.
5. **One re-prompt helper for REVIEW (b-708c8a)**: not absorbed.
6. **Find why git in a cell is refused a loose object (b-6ac0cd)**: not
   absorbed. It hit again, in a spec-review cell, and is narrowed to a
   transient read through the mirror's bind mount.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` are the evidence.

1. **Close each retired spec's item in the finishing commit (b-3c7ce9).** A
   finish change. Both finishes went red, and the delegate linked by hand.
2. **A check that each witness drives every part of its claim (b-20043f).** A
   lens change. Five of this run's ten rejection lines are bucket 1
   `witness`, each a seat probe the critic passed.
3. **Retry a failed seed, and never refuse descendants for infrastructure
   (b-6ac0cd, b-60a399).** A batch change. One seed error cost two layers.
4. **Stack on a reviewable layer from an earlier batch (b-e0e1cf).** A queue
   change. It cost a merge wait between batches.
5. **Print the admission arithmetic (b-0a08bf).** A queue change. It moves the
   delegate's budget arithmetic into the plan the operator already reads.
6. **Log spec sessions where `watch` reads (b-4e1b6d).** A batch change.

## The loop's own gaps

- **The hand spec review duplicates the batch's.** The in-batch review sent
  all four specs to run, with two concerns and no blocker. The hand reviews
  had already removed the two blockers it would have met. One more batch
  measures whether the hand review can go.
- **Seats stay.** Both batches fail the retirement test.
- **Jev scored nothing.** The worktree guard still refuses its key.
