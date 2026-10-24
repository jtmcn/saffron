# Feedback on run-saffron-spec-loop (run 46, 2026-10-20 to 2026-10-23)

Run 46's order was nine specs: `SA-0299`, `SA-0298`, `SA-0300`, `SA-0301`,
`SA-0302`, `SA-0303`, `SA-0304`, `SA-0306` and `SA-0305`. Their budgets
came to $299. Six of them build b-8a0c9a as one chain. Eleven batches spent
$258.15 of a $600 cap. All nine reached a reviewed pull request.

| Spec | PR | Spend of budget | Outcome |
|---|---|---|---|
| `SA-0299` | #928 | $19.04 of $25 | merged |
| `SA-0298` | #929 | $12.50 of $24 | `EXHAUSTED` after REBUT, fixed by hand and adopted, merged |
| `SA-0300` | #930 | $8.06 of $22 | merged |
| `SA-0301` | #932 | $14.10 of $29 | merged |
| `SA-0302` | #937 | $51.02 of $32 | PACKAGE raised, pushed by hand and adopted, merged |
| `SA-0304` | #934 | $21.15 of $30 | merged |
| `SA-0303` | #939 | $37.14 of $34 | stack #945, bottom |
| `SA-0306` | #941 | $31.30 of $58 | stack #945, middle |
| `SA-0305` | #944 | $31.68 of $45 | stack #945, top |

The operator merged the bottom six as the chain went. Each child then had
its citations refreshed in a spec PR the delegate merged, and ran alone in
a one-spec `--stack` batch.

## What the run found

1. **REBUT ended a fixed task `EXHAUSTED` (b-0bd346).** `SA-0298`'s REBUT
   fixed all five blockers and killed each probe. Its own test comments then
   failed `prose`. No repair turn follows REBUT, so the delegate fixed three
   comments and adopted the branch.
2. **A layer cut from a review commit cannot be packaged again (b-066901).**
   `SA-0302`'s PACKAGE raised when the container service failed. The batch
   still exited 0. `saffron package` then refused, since the tree base was a
   review commit and no task's `pushed_sha`.
3. **An adopted task blocks its child (b-619b7d, b-066901).** The adopted
   `SA-0302` recorded no pushed sha, so batch 44 refused `SA-0303` at $0.
4. **The stack base is the lowest open parent (b-1572e7).** Batch 49
   refused `SA-0305` for overlapping #941, its own parent. #943 reordered
   `depends_on` by hand.
5. **The citation check costs a spec PR per layer (b-2da959).** Each child
   needed its citations refreshed at its parent's reviewed branch. Four PRs
   did so (#931, #933, #940, #942). `SA-0304` drew 20 refusals, and 19 were
   correct citations.
6. **The end review's writer redid a queued spec (b-cc87b1).** Batch 47
   drafted `SA-0310`, which restates `SA-0306`. The finish then escalated
   on "13 new failures" where the suite showed one (b-fe82d9).
7. **One refused /24 stopped every cell (b-7c1c99).** `10.200.0.0/24` failed
   in every mode after a `brew upgrade` and a second user's container
   service. The loop waited a day for a reboot.
8. **Re-gating after REBUT prints nothing (b-30cbb8).** `SA-0305`'s five
   rebuttals took forty silent minutes, and the operator read it as a stall.
9. **The stack graded the right heads at last.** Batches 48 and 50 ran with
   `SA-0302` and `SA-0303` in place. Their end reviews raised nothing a
   review commit already held, and neither finish committed anything.

## What the reviews found

Eighteen seats reviewed nine pull requests and raised 74 findings. Review
commits fixed 62. Four went to new items and eight needed no change. The
in-cell critic missed 29 of the fixed or kept ones. `.saffron/rejections.md`
holds those and four run gaps, dated 2026-10-23. Twelve of the 29 are
adequacy gaps, each a witness a seat's probe broke after REVIEW passed it.

Ten new items carry what the stack left: b-0bd346, b-066901, b-1572e7,
b-cc87b1, b-7c1c99, b-30cbb8, b-d038df, b-25634b, b-19dbc9 and b-1fc93b.

## Run 45's items, checked

1. **The end review drafts from the head the delegate will push
   (b-8a0c9a):** done. Stack #945 and the four merged layers close it. The
   loop now defers the end review and runs `saffron finish` after the push.
2. **The `comment-block` rule joins a comment split by blank lines
   (b-998bb7):** done by hand in #924, before this run.
3. **A host-filed survivor holds its task wherever its edit lands
   (b-e40d09):** done in #928.
4. **`make check` reads the working tree for `prose` (b-08a36a):** done in
   #929.
5. **A refused follow-up is written to the tree (b-589cf6, b-703e64):**
   half. #930 makes `saffron next-id` read the ledger. `SA-0307` to
   `SA-0310` still live only there.

## Summary: what Saffron should absorb next

1. **REBUT earns one repair turn on a gate its fix turned red (b-0bd346).**
   A phase change. It cost a reviewable task its pull request.
2. **A batch stacks on the deepest open parent and exempts every parent's
   branch (b-1572e7).** A scheduler change. It cost one batch and one spec
   PR.
3. **`adopt` and `package` accept a layer cut from a review commit
   (b-066901, b-619b7d).** A phase change. Two hand pushes and one refused
   batch came from it.
4. **The citation check stops refusing correct ranges (b-2da959).** A gate
   change. It drove four spec PRs, and two of them only reshaped sentences.
5. **Qualification drops a finding a queued spec owns (b-cc87b1).** A phase
   change. It cost $1.11 and a red finish.
6. **The adequacy lens probes the way the Spec seat does.** A lens change.
   Twelve witness gaps passed REVIEW this run, and each seat found its gap
   with a two-line probe.

This PR changes skill text twice. Step 2 now runs the batch with
`--defer-end-review` and finishes after the push, as `SA-0305` allows.
`spec-writer.md` names `saffron next-id` for a child's spec id.

## Next run

Nothing is queued. Stack #945 waits on the operator.
