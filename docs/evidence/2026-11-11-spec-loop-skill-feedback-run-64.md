# Feedback on run-saffron-spec-loop (run 64, 2026-11-11)

Run 64 kept the goal of runs 55 to 63: implement every backlog item. It ran
three specs the chain wrote this session, and finish 82 ran one follow-up.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0372` | #1162 | `READY_FOR_REVIEW` | $20.91 of $45 |
| `SA-0373` | #1164 | `READY_FOR_REVIEW` | $17.65 of $32 |
| `SA-0374` | #1166 | `READY_FOR_REVIEW` | $11.76 of $30 |
| `SA-0379` | #1167 | `READY_FOR_REVIEW` | $5.78 of $45 |

Batch 82 ran at `--budget 262` with `--stack --defer-end-review`. The first
start at $260 was refused, since $107 of specs needs $262 with both shares
whole. `saffron finish 82` then ran the end review and drafted `SA-0379`.

## What the run found

1. **Every task reached `READY_FOR_REVIEW` on its first attempt.** Each
   IMPLEMENT made one commit. REBUT withdrew every adequacy blocker.
2. **The finish's re-verify went red on `census` for a rename.**
   `test_dead_gate.py` named each case by a spec's whole text. The finishing
   commit wrote revised texts, so two cases read as removed. This PR names the
   cases by file. b-703e64 and b-f30189 have Record lines.
3. **Finish 82's follow-up ran green.** `SA-0379` came from `SA-0372`'s
   symlink concern. It passed the batch's citation check and reached #1167.
   b-4a9207 has the Record line.
4. **Two of four PRs restated a helper the code base already had.**
   `run_task` split an entry by hand beside the scheduler's
   `_entry_subject`. `_tracked_symlinks` wrote out `_git`'s argv and exit
   check.
5. **Two of four PRs left a guard no witness drove.** `SA-0373`'s orphan
   guard and `SA-0379`'s empty-entries guard each survived deletion.
6. **The b-6dd608 flake hit a fifth time,** in `test_batch`. It passed alone.
7. **One concern was not a defect.** `SA-0373`'s seat asked whether a
   concurrent `saffron draft` run could join a batch. `draft` holds the home
   lock, so it cannot run beside a batch. Nothing was filed.

## What the reviews found

- **#1162:** 1 Spec seat blocker and 3 Standards notes. The witness drove one
  entry order. A missing stdout check, a restated helper and docstring words
  were fixed in `9334b97a`.
- **#1164:** 1 Spec seat blocker and 3 notes. The orphan task had no spec
  review row, so the guard never ran. Fixed in `41f0f975`.
- **#1166:** 1 note, a copied comment. Fixed in `335684ea`.
- **#1167:** 1 Spec seat blocker and 4 Standards notes, all fixed in the
  review commit on #1167.

`.saffron/rejections.md` holds nine lines for this run. No item was filed.

## Run 63's items, checked

- [ ] **A wrong version's edit changes only the case it names:** open, on
  b-f06097.
- [x] **REVIEW records the tree the critic read:** specced as `SA-0375`,
  merged in #1160. `SA-0378` reads it.
- [ ] **`terms` reads every `_Avoid_` line:** open, on b-8220e6.
- [x] **An adopted task joins its batch's stack:** done, by #1164.
- [ ] **A cell that dies after green is an `error`:** open, on b-f582ee.

## Summary: what Saffron should absorb next

1. **`census` reads a renamed parametrize id as a removed test.** A gate
   change, on b-f30189. It turned finish 82 red with no defect.
2. **REVIEW probes each guard the diff adds.** A lens change. Two of four
   PRs left a guard no witness drove, and adequacy filed neither.
3. **A lens reads for a helper the diff restates.** A lens change. Two of
   four PRs copied a helper's body.
4. **A wrong version's edit changes only the case it names.** A phase
   change, on b-f06097.
5. **A cell that dies after green is an `error`.** A phase change, on
   b-f582ee.

This PR changes no skill text.

## Next run

`SA-0375` to `SA-0378` are queued for run 65.
