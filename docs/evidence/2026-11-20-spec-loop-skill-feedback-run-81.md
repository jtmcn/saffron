# Feedback on run-saffron-spec-loop (run 81, 2026-11-20)

Run 81 kept the goal of runs 55 to 80: implement every backlog item. It ran
`SA-0416` and `SA-0417` in batch 99, and `SA-0418` in batch 100. Finish 99
ran one follow-up, `SA-0420`.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0416` | #1278 | `READY_FOR_REVIEW` | $32.68 of $62 |
| `SA-0417` | #1279 | `READY_FOR_REVIEW` | $38.14 of $56 |
| `SA-0418` | #1281 | `READY_FOR_REVIEW` | $29.09 of $24 |
| `SA-0420` | #1284 | `READY_FOR_REVIEW` | $15.39 of $20 |

Both batches ran with `--stack --defer-end-review`. `SA-0418` overran its
budget within the one-attempt allowance. The `SA-0420` figure is the
finish's whole charge to that task, its end review and its cell together.

The spec chain ran beside the batches. It merged `SA-0418` (#1276) and
`SA-0419` (#1280). By hand, the run closed item 20 (#1282), item 128
(#1283) and b-63ac52 (#1277).

## What the run found

1. **A witness that errored passed as one that asserted.** Three `SA-0418`
   witnesses looked a task up before they asserted. Fifteen wrong versions
   died by `KeyError`, and the cell's REVIEW counted each as caught. Only
   the driver's `probe` read the difference. Filed as b-c2f264.
2. **A set's members were still found one review at a time.** The
   `SA-0419` chain's two reviews each named one more member of the same
   refused set. That is the fourth run with this class. The chain added
   checks 76 to 79 for it.
3. **A finish pooled a real finding because its draft failed `prose`.**
   Finish 99 drafted `SA-0421` for a stale `DESIGN.md` sentence. The draft
   held one sentence over 25 words, so the suite refused it. A review commit
   on #1278 fixed the sentence by hand. Recorded on b-703e64.
4. **A finish marked a finding unresolvable on a moved line.** Its
   `_REGULAR_MODES` concern cited a line that had moved. The concern is real
   and belongs to b-385eba. Run 80 saw the same shape.
5. **A filtered commit hid a failed hook.** The `SA-0417` review commit
   failed `ruff`, and a `grep` over the output hid it. `make check` then ran
   on an uncommitted tree. Checking the commit's own exit caught it.
6. **A witness's fixture left its edit unstaged.** `SA-0416`'s `head_text`
   witness could not tell the index from `HEAD`. Staging the edit made the
   wrong version die.

## What the reviews found

- `SA-0416`: one Spec blocker (item 6) and four Standards notes, all fixed.
  The end review's `DESIGN.md` concern was fixed after the finish.
- `SA-0417`: two Spec blockers, both witness gaps in the findings check,
  and one Standards concern on a comment's order. All fixed.
- `SA-0418`: three Spec blockers (item 1), one concern on the repair and
  rebuttal phases, and one Standards concern on a docstring. All fixed.
- `SA-0420`: one comment and a test that reads it. Accepted as it stands.

## Run 80's items, checked

- [ ] **The adequacy lens moves a claim's deciding case off each edge:**
  open. Item 2 is the fourth run of evidence.
- [ ] **A rate-limited task resumes its cell instead of starting over:**
  open. No cell was rate-limited this run.
- [ ] **The driver fills the seat prompts:** open. A script in the
  scratchpad still holds the step.
- [ ] **The spec writer's tree checks run `saffron mutant` on each drafted
  mutant:** open. The `SA-0419` writer ran it by hand, and both mutants
  wrote.
- [ ] **A host probe asks what the code it edits is for:** open.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.

## Summary: what Saffron should absorb next

1. **The `witness` gate reads an exception-only kill as a survivor.** A
   gate change, on b-c2f264. Item 1 is the evidence.
2. **The adequacy lens moves a claim's deciding case off each edge.** A
   lens change, with no item yet, now on its fourth run.
3. **The follow-up writer's draft meets `prose` before the suite.** A phase
   change, on b-703e64. Item 3 is the evidence.
4. **A rate-limited task resumes its cell instead of starting over.** A
   phase change, with no item yet, carried from run 80.
5. **The driver fills the seat prompts.** A tool change, with no item yet.
6. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.

This PR changes no skill text.

## Next run

Run 82 runs `SA-0419`. Specs for b-0f5493, b-d9ed45, b-bc54d1 and b-9eceda
wait on this stack, since they touch the files it changes.
