# Feedback on run-saffron-spec-loop (run 51, 2026-10-30)

Run 51's order was `SA-0328` alone, with a budget of $52. Batch 62 ran it at
$120. It reached a reviewed pull request, #1000.

| Spec | PR | Spend of budget | Peak turns of ceiling |
|---|---|---|---|
| `SA-0328` | #1000 | $34.92 of $52 | 197 of 220 |

The spend includes the spec review, at $2.96. REBUT spent $4.65. Finish 62
spent about $3.25, drained, and committed nothing. The run spent about $38.

## What the run found

1. **No witness read the prompt this spec exists to change.** The change is
   an instruction in `criterion-probe.md`. Every test passed with that
   instruction removed, since each witness scripts its answers. No claim
   named the instruction. A pre-flight or a gate could ask for one.
2. **The critic's probes ran the old prompt.** The host ran `main`'s code,
   so the two blockers they filed say nothing about this change. The first
   cell after #1000 merges is the first measurement.
3. **Two spend figures name one task.** The watch said $31.96, and `record`
   said $34.92. `record` adds the spec review, and only the ledger shows it.
4. **A spec review's text sits in its event log.** The batch log cuts each
   finding, and `record` prints none. The delegate read four notes out of
   `events.jsonl` by hand, and first took its last session's $0.71 for the
   whole review's cost.
5. **`cite` passed citations a spec review called off.** It resolved all 96,
   and a note reported drift of one to a few lines. This repeats run 50's
   finding 10.

## What the reviews found

Two seats raised seven findings on #1000. A review commit fixed six, and one
needed no action, since neighbouring tests pin its line. Two were blockers,
both witness gaps the critic missed, and both were real. Finish 62 raised
nothing. `.saffron/rejections.md` holds five lines for this run.

The Standards seat also named `review.py:717`, which says "retry" on the base.
The `terms` gate does not list that word. This run filed no item for it.

## Run 50's items, checked

- [ ] **A spec review keeps its findings when extraction fails (b-298b1c):**
  open. It did not recur.
- [ ] **REBUT knows a suppression fails (b-8826cf):** open. It did not recur.
- [x] **The adequacy lens probes the way the Spec seat does (b-78a590):** done
  in #1000, and not yet measured.
- [ ] **An adopted task is a layer of its batch (b-323c97):** open. It did not
  recur.
- [ ] **A stack batch exempts an earlier batch's lower layers (b-0bd8c9):**
  open. It did not recur, since one spec ran.
- [ ] **`cite` reads every open layer and what a sentence names:** open. Half
  of it recurred, as finding 5 says.
- [ ] **`check` compares ceilings with the closest shape:** open. It did not
  recur. `check` set 220 turns against 169, and the cell used 197.
- [ ] **The skill says to read `saffron queue --stack` for the budget:** open.
  The delegate read it unprompted this run.

## Summary: what Saffron should absorb next

1. **A spec review keeps its findings when extraction fails (b-298b1c).** A
   phase change, unchanged from run 50.
2. **REBUT gets a repair turn, or knows a suppression fails (b-8826cf).** A
   phase change, unchanged from run 50.
3. **An adopted task is a layer of its batch (b-323c97).** A phase change.
4. **A stack batch exempts an earlier batch's lower layers (b-0bd8c9).** A
   gate change.
5. **A change to a prompt file needs a claim that reads the changed text.** A
   gate or pre-flight change. It cost one blocker in this run. One run is
   thin evidence, so it ranks below the items with a measured cost.
6. **`record` prints the spec review's findings and spend.** A driver change.
   It cost the delegate a hand read of `events.jsonl`.
7. **`cite` reads every open layer's lines, and checks what a sentence
   names.** A driver change.
8. **`check` compares ceilings with the closest shape.** A driver change.
9. **The skill says to read `saffron queue --stack` for the budget.** A skill
   text change, ranked last.

This PR changes no skill text.

## Next run

The queue is empty once #1000 and this PR merge. Compare the seats' witness
gaps on the first cell that runs the new prompt against this run's two.
