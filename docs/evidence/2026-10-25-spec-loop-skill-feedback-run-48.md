# Feedback on run-saffron-spec-loop (run 48, 2026-10-24 to 2026-10-25)

Run 48's order was the chain `SA-0313`, `SA-0315` and `SA-0316`. Their
budgets came to $96. Three batches and three finishes spent about $116.79
of a $300 cap. All three specs reached a reviewed pull request, stacked as
#961, #964 and #966.

| Spec | PR | Batch | Spend of budget | Peak turns of ceiling |
|---|---|---|---|---|
| `SA-0313` | #961 | 53 | $34.29 of $30 | 151 of 150 |
| `SA-0315` | #964 | 54 | $20.46 of $30 | 121 of 180 |
| `SA-0316` | #966 | 55 | $32.27 of $36 | 169 of 180 |

The cells spent $87.02. The three deferred finishes spent about $7.13,
$7.98 and $14.66, which is $29.77 in all.

## What the run found

1. **Each finish re-raised what review had fixed (b-1b05be).** The three
   finishes reported eight findings. Five named PACKAGE's head, below the
   reviewed one. Four of those five were fixed, and the spec answered the
   fifth. Their follow-up drafts were all pooled.
2. **Each child waited on a citation refresh (b-009d51).** `SA-0315` was
   refused with four stale citations, and `SA-0316` with seven. Each one
   cost a spec PR (#962, #965) and one more batch. `cite` printed every new
   line, and the delegate copied them by hand.
3. **A host-filed probe ran the wrong witness (b-b9365d).** `SA-0313`'s
   adequacy blocker at `cli.py:2884` ran a `preserves` witness that never
   calls `_adopt`. Re-run against the adopt tests, the same edit failed
   three assertions.
4. **The writer drafted a spec for a comment (b-01c53d).** `saffron finish
   55` spent three revisions on `SA-0317`, a two-line comment fix, and
   withheld it. The delegate fixed the comment in this PR.
5. **A cell cited a spec that does not exist (b-9c5b11).** `SA-0315` wrote
   `SA-0320` three times. The conventions lens caught it. No gate checks it.
6. **`record` read a task mid-PACKAGE (b-92fdbe).** The delegate's wait
   matched the batch's header line, and `record` printed a halt at
   `REBUTTING`. A second `record` after the exit read #966.
7. **A stale rebase state blocked the stack link (b-d3f977).** Run 19 left
   `.git/gh-stack-rebase-state`. The delegate moved it aside rather than
   abort, since an abort would reset 13 old branches.
8. **The cell-watch mod reported stale hand-overs (b-2d2014).** It did so
   three times, once each time it attached to a new task.

## What the reviews found

Six seats reviewed three pull requests and raised 21 findings. Review
commits fixed 20, and one needed no action. Two were blockers, and both
were real. The in-cell critic raised 4 blockers, and 3 of them were real.
REBUT fixed all three.
`.saffron/rejections.md` holds 13 lines for this run, dated 2026-10-25.
Two of them are adequacy gaps.

This PR carries one hand commit. `0fc29a37` fixes three comments the
finishes found after the layers below it were reviewed.

Nine new items carry what the stack left: b-1b05be, b-009d51, b-b9365d,
b-9c5b11, b-01c53d, b-92fdbe, b-d3f977, b-f0e351 and b-87001a.

## Run 47's items, checked

- [x] **`adopt` promotes the task it names (b-619b7d):** done in #961.
- [ ] **The witness gate fails a find that matches other than once
  (b-a68b24):** open. It did not recur.
- [ ] **A follow-up draft that does not parse goes back once (b-781ea4):**
  open. It recurred in finish 55, with a draft that had no frontmatter.
- [ ] **The adequacy lens probes the way the Spec seat does:** open. Both
  adequacy gaps this run were found by a seat's probe.
- [ ] **A stack batch takes the queue's order (b-0c5afc):** open. It did
  not matter here, since each batch ran one spec.
- [x] **`package` accepts a review-commit layer (b-066901):** done in #964,
  and #966 makes a raised PACKAGE exit 2.

## Summary: what Saffron should absorb next

1. **The finish reads findings at the layer's pushed head (b-1b05be).** A
   phase change. Five of eight finish findings were stale this run.
2. **`cite` rewrites a construct it finds at one new place (b-009d51).** A
   gate change. It cost two spec PRs and two batches this run.
3. **A host-filed probe runs the tests that reach its file (b-b9365d).** A
   gate change. It filed one false blocker this run.
4. **A comment-only finding becomes a finishing-layer edit (b-01c53d).** A
   phase change. It cost about $7 and filed nothing.
5. **A gate checks every cited spec id (b-9c5b11).** A gate change. A lens
   caught it this time.
6. **`record` refuses while its batch still runs (b-92fdbe).** A driver
   change.

This PR changes no skill text.

## Next run

The order is empty. Stack #966 waits on the operator.
