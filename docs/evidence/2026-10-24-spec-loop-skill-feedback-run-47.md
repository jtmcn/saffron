# Feedback on run-saffron-spec-loop (run 47, 2026-10-23 to 2026-10-24)

Run 47's order was six specs: `SA-0312`, `SA-0313`, `SA-0315`, `SA-0311`,
`SA-0314` and `SA-0316`. Their budgets came to $230. One batch and its finish
spent $140.87 of a $600 cap. Three specs reached a reviewed pull request. The
other three wait on `SA-0312`.

| Spec | PR | Spend of budget | Outcome |
|---|---|---|---|
| `SA-0311` | #955 | $29.11 of $52 | stack #958, bottom |
| `SA-0312` | #957 | $71.76 of $52 | `EXHAUSTED`, fixed by hand and adopted, stack #958, middle |
| `SA-0314` | #956 | $19.34 of $30 | stack #958, top |
| `SA-0313` | none | $0 | refused, reaches `SA-0312` |
| `SA-0315` | none | $0 | refused, reaches `SA-0312` |
| `SA-0316` | none | $0 | refused, reaches `SA-0312` |

Batch 51 ran with `--stack --defer-end-review`. `saffron finish 51` then
spent $20.66 and committed nothing.

## What the run found

1. **A witness gate passes a mutant it never ran (b-a68b24).** `SA-0312`'s
   cell copied a fetch tail, so criterion 5's find matched three lines. The
   gate counts such a find toward nothing. The Standards seat counted the
   matches. The operator chose to fold the copy in review.
2. **An adopted layer still reads `EXHAUSTED` (b-619b7d).** `SA-0312` was
   adopted as #957. The finish then reviewed `SA-0314` against `SA-0311` and
   charged `SA-0312`'s diff to it. `driver.py size` read the same wrong
   parent, so the delegate measured each layer by hand.
3. **The finish filed nothing (b-781ea4).** Two follow-up drafts failed to
   parse at a YAML list item that opens with a backtick. The third declared
   `type: test`. All three findings were pooled.
4. **The batch ran in id order (b-0c5afc).** The snapshot put `SA-0312`
   first, as the parent with most descendants. The batch started `SA-0311`.
5. **A cell spent 138% of its budget.** `SA-0312` spent $71.76 of $52 over
   two attempts and the batch's spec revision. Attempt 1 had 122 new
   failures and attempt 2 had one.
6. **The cell-watch mod followed the wrong task (b-2d2014).** Before
   `SA-0311` wrote its log, the watch followed run 46's `SA-0305`. A stop did
   not end it.

## What the reviews found

Six seats reviewed three pull requests and raised 33 findings. Review
commits fixed 29. Three went to new items and one needed no change. The
in-cell critic raised 3 findings over the two cells that ran a REVIEW. `SA-0312` ran no
REVIEW, so every finding on it was the seats' alone. `.saffron/rejections.md`
holds 18 lines for the fixed or kept findings the critic missed, plus two
run gaps, dated 2026-10-24. Five of the 18 are adequacy gaps.

Three hand commits rode the stack. `49e4ebca` declares `format`, `lint` and
`prose` as form gates, so `SA-0311`'s repair turn can fire here. `9e00bee1`
gave `SA-0312`'s last surviving witness an arrangement that kills its mutant.
`011c3618` points `driver.py cite` at the core checker `SA-0314` built.

Ten new items carry what the stack left: b-a68b24, b-781ea4, b-0c5afc,
b-fa014a, b-22ed54, b-c3688d, b-7fa522, b-54c8b4, b-7655f9 and b-2d2014.

## Run 46's items, checked

1. **REBUT earns one repair turn (b-0bd346):** done in #955.
2. **A batch stacks on the deepest open parent (b-1572e7):** done in #957,
   by hand after the cell ended `EXHAUSTED`.
3. **`adopt` and `package` accept a review-commit layer (b-066901,
   b-619b7d):** open. `SA-0313` and `SA-0315` carry them and wait on #957.
   The gap recurred in this run's finish.
4. **The citation check stops refusing correct ranges (b-2da959):** done in
   #956. Both copies now share one rule.
5. **Qualification drops a finding a queued spec owns (b-cc87b1):** open.
   It did not recur, since the finish drafted nothing it kept.
6. **The adequacy lens probes the way the Spec seat does:** open. Five
   adequacy gaps passed REVIEW or had no REVIEW, and each seat found its gap
   with a probe.

## Summary: what Saffron should absorb next

1. **`adopt` promotes the task it names (b-619b7d).** A phase change, queued
   as `SA-0313`. It refused three children, misgraded one finish layer and
   broke `driver.py size`.
2. **The witness gate fails a find that matches other than once
   (b-a68b24).** A gate change. A copied line let a criterion pass with no
   mutant run.
3. **A follow-up draft that does not parse goes back to the writer once
   (b-781ea4).** A phase change. It cost $20.66 and filed nothing.
4. **The adequacy lens probes the way the Spec seat does.** A lens change,
   carried from run 46. Five adequacy gaps this run.
5. **A stack batch takes the queue's order (b-0c5afc).** A scheduler
   change. It delayed the chain's root by one cell.

This PR changes no skill text. `#956` carries the one skill edit, to
`preflight.md`, beside the driver change it describes.

## Next run

`SA-0313`, `SA-0315` and `SA-0316` stay queued as a chain on `SA-0312`. They
can run once stack #958 merges. Each needs a citation check at its parent's
branch first.
