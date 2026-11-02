# Feedback on run-saffron-spec-loop (run 52, 2026-11-01 to 2026-11-02)

Run 52's order was `SA-0329`, then `SA-0331` and `SA-0330` stacked above it.
The specs carried $116 of budget. It took two batches, a spec PR and two
finishes. It reached two reviewed pull requests, #1008 and #1010, stacked and
marked ready.

| Spec | PR | Outcome | Spend of budget | Peak turns of ceiling |
|---|---|---|---|---|
| `SA-0329` | #1008 | `READY_FOR_REVIEW` | $32.52 of $38 | 142 of 210 |
| `SA-0331` | #1010 | `READY_FOR_REVIEW` | $34.12 of $38 | 130 of 210 |
| `SA-0330` | none | `PLAN_REJECTED` | $7.50 of $40 | 80 of 200 |

Batch 63 ran at a $280 ceiling and batch 64 at $188. Finish 63 spent $1.85
and finish 64 spent $5.58. The run spent about $81.57 in all.

## What the run found

1. **The plan checkpoint priced tests that `size` never counts.**
   - `SA-0330`'s plan estimated 480 lines, priced at 1920 tokens.
   - Its touch of `saffron/ledger.py` made it `elevated`, where `size` blocks
     at 1300. It ended `PLAN_REJECTED` before any code.
   - Its spec measured 120 lines outside tests. b-15db6e named this on
     2026-10-11, and this run moves it to tier 1.
2. **A child's citations met their parent's diff only inside the batch.**
   - Batch 63 refused `SA-0331`, and `SA-0330` with it.
   - One citation named `_finish` beside lines that held `_state`, so the batch
     could not move it once `SA-0329` shifted the file.
   - `cite` passed it at `main`, and `check` could not run on a child whose
     parent had no branch. The fix cost a spec PR (#1009), a merge and a
     second batch. Filed as b-b664d1.
3. **Bare citations drift with nothing to catch them.** The batch's spec review
   found about ten `:NNNN` citations in `SA-0331`, each 49 lines stale. The
   batch moves only a citation whose sentence names its construct. Run 50's
   finding 10 recurs. b-b664d1 carries it.
4. **`check` blocks on citations the batch moves itself.** After #1009 merged,
   `check` still printed `blocker: 2 of 70 citation(s) do not resolve`. Batch 64
   moved both and ran the spec.
5. **Finish 64 drafted a follow-up its own batch refused.** It drafted
   `SA-0332` for a one-line comment. The draft failed `prose`, then its batch
   refused it for two citations, and the layer stayed red. The delegate fixed
   the line by hand. Filed as b-4a9207.
6. **The new probe prompt found more, and the seats still found two per PR.**
   - `SA-0329`'s REVIEW named 34 criterion probes over 7 criteria and filed 7
     real blockers.
   - `SA-0331`'s named 32 over 9 and filed 5. REBUT closed each one.
   - Each PR's Spec seat still found two witness blockers. Each was a claim over
     a set or a sequence whose witness drove one member, such as the outcome's
     states or a second scan.
7. **Two spend figures name `SA-0331` again.** `record` said $34.12. The
   ledger's attempts sum to $36.56. This repeats run 51's finding 3.

## What the reviews found

The seats raised 15 findings on #1008 and 10 on #1010.
- **#1008:** all 15 were real, and review commit `1bab00be` fixed them.
- **#1010:** two needed no action, since other witnesses kill those mutants.
  `c6a99459` and `42a773d1` fixed the rest, `42a773d1` closing the one finish
  64 raised.

Five blockers in all were witness gaps the critic missed.
`.saffron/rejections.md` holds seven lines for this run. The Standards seat's
out-of-scope finding is b-e4cb58.

## Run 51's items, checked

- [ ] **A spec review keeps its findings when extraction fails (b-298b1c):**
  open. It did not recur.
- [ ] **REBUT knows a suppression fails (b-8826cf):** open. It did not recur.
- [ ] **An adopted task is a layer of its batch (b-323c97):** open. It did not
  recur.
- [ ] **A stack batch exempts an earlier batch's lower layers (b-0bd8c9):**
  open. It did not recur. Batch 64 stacked `SA-0331` on #1008, its ancestor.
- [ ] **A change to a prompt file needs a claim that reads the changed text:**
  open. No spec this run changed a prompt.
- [ ] **`record` prints the spec review's findings and spend:** open. The
  delegate read them from the ledger's `spec_reviews` table by hand.
- [ ] **`cite` reads every open layer's lines and checks what a sentence
  names:** open, and it cost this run the most. Findings 2 and 3 recur it.
- [ ] **`check` compares ceilings with the closest shape:** open. Both cells
  ended well under 210 turns.
- [ ] **The skill says to read `saffron queue --stack` for the budget:** open.
  The delegate read it unprompted again.

## Summary: what Saffron should absorb next

1. **The plan checkpoint prices what `size` counts (b-15db6e).** A phase
   change. It cost a whole spec this run, and a rerun would fail the same way.
2. **A citation's named construct is checked at the spec's own base, and a
   bare citation into a file a parent changes is flagged (b-b664d1).** A gate
   change in `saffron/spec_citations.py`. It cost a spec PR, a merge and a
   batch.
3. **A finish fixes a one-line finding in its layer rather than drafting
   (b-4a9207).** A phase change.
4. **The adequacy lens probes each member of a set a claim quantifies over.**
   A lens change. It cost four blockers across two PRs.
5. **A spec review keeps its findings when extraction fails (b-298b1c).**
   A phase change, unchanged from run 51.
6. **`check` leaves a citation the batch can move as a note.** A driver change.
7. **`record` and the ledger agree on a task's spend.** A driver change.

This PR changes no skill text.

## Next run

`SA-0330` stays queued until b-15db6e lands. Once its spec merges, rerun
`SA-0330` on `main` after #1008 and #1010 merge.
