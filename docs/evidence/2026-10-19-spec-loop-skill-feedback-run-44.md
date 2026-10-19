# Feedback on run-saffron-spec-loop (run 44, 2026-10-17 to 2026-10-19)

Run 44's order was the chain from `SA-0276`, thirteen specs. Two `--stack`
batches ran it. Batch 37 spent $50.15 of $1170 and stopped after one
layer. Batch 38 spent $275.35 of $1100 and drained. The stack is eleven pull
requests, #903 to #915, linked as stack #916. Ten ended `READY_FOR_REVIEW`.
`SA-0279` ended `EXHAUSTED`, and the delegate finished it by hand as #912.
`SA-0290`, `SA-0291` and `SA-0295` wait on #912 to merge.

## Before the run

- **`snapshot --new` admitted 2 of 13 specs.** The driver needed every
  `depends_on` parent in the order, so two merged parents stranded the chain.
  This PR carries the fix and its red-first test.
- **`check` blocked four specs on ceilings and one on citations.** #902
  raised the ceilings and refreshed 24 of `SA-0276`'s citations.

## What the run found

1. **PACKAGE refused `SA-0277`'s push.** A test spelled a whole private key
   header, so the task ended `MERGE_FAILED` and nine children were refused.
   Neither `adopt` nor `package` takes that state. The operator chose a
   re-run after #905 (b-619b7d).
2. **`SA-0279`'s own refusal failed the specs below it.** Its new `.claude`
   check refused the `touches` of `SA-0280`, `SA-0282` and `SA-0283`, which
   sat queued as open layers. No in-cell edit could fix that, and the cell
   spent its turns proving it (b-e7898b).
3. **An adopted `EXHAUSTED` task stays outside the driver.** `size` and
   `stack` refused #912, so the delegate measured and linked it by hand
   (b-619b7d).
4. **A host-filed survivor outside the diff was dropped.** `SA-0288`'s
   critic filed a blocker at `runner.py:330`, which the diff never touches.
   It was unanchored, so no REBUT ran and the task went
   `READY_FOR_REVIEW`. Both seats then proved the witness could not fail
   (b-e40d09).
5. **The end review ran a follow-up spec with no file.** `SA-0296` lived
   only in the ledger, so `record`, `jev` and `bookkeeping` could not find
   it. It also redid a fix held as a review commit on #911 (b-703e64,
   b-8a0c9a).
6. **Both finishes escalated a red suite.** The end review committed a fix
   that failed 2 tests in batch 37 and 10 in batch 38. Of its 13 follow-up
   drafts, 12 were pooled (b-fe82d9, b-27bacc).
7. **`driver.py stack` ordered the stack wrongly again.** It put #914 below
   #913 and left out #915 and #912. `size` measured #913 from the wrong
   base. The delegate linked by hand (b-3a79a0).
8. **The delegate pushed a review commit on a red suite.** One shell line
   ran `make check`, the commit and the push. Closing b-0569f7 turned it
   green.

## What the reviews found

Twenty-two seats reviewed eleven pull requests. The Spec seats ran about
270 probes. Survivors became review commits on #906, #907, #908, #909,
#910, #912, #914 and #915. The in-cell critic missed most of them, and
`.saffron/rejections.md` holds 45 lines dated 2026-10-19. Fourteen new
items carry what the reviews kept.

## Run 43's items, checked

1. **A batch runs the loop's order (b-f73cd0):** did not recur. The chain
   was the whole order.
2. **A stack records the base each layer was cut from (b-3a79a0):**
   recurred, with a third symptom in `size`.
3. **The `adequacy` lens asks whether a witness runs the spec's seams:**
   recurred on #914. The lens raised it this time, and anchoring dropped it.
4. **A fixture head is reachable from a ref a clone fetches (b-055fa3):**
   recurred. The item named the wrong hop. The seed fetch takes only
   `+refs/heads/*`, and the mirror holds every object.

## Summary: what Saffron should absorb next

1. **A host-filed survivor holds its task wherever its edit lands
   (b-e40d09).** A phase change. Anchoring is for a lens's claim, and this
   probe ran on the host.
2. **A spec that adds a refusal is checked against the specs queued below
   it (b-e7898b).** A spec review change. It cost `SA-0279` its whole
   budget.
3. **A stack records each layer's base (b-3a79a0).** A phase change. It has
   recurred in three runs.
4. **A finish leaves no red commit and writes every follow-up spec to the
   tree (b-fe82d9, b-703e64).** A phase change.
5. **The cell's seed fetches the fixture heads (b-055fa3).** A cell change.
   Four local branches stand in for it.
6. **`adopt` takes a fixed task back to a waiting state (b-619b7d).** A
   phase change.
7. **The `prose` gate reads `.yaml` and `docs/agents/` (b-e9cd43). A gate
   catches a test writing outside `tmp_path` (b-524b1a).** Gate changes.

One skill-text change shipped here. `REVIEW-PROMPT.md` now inlines the
findings block's shape, since a seat wrote a list Jev refused.

## Next run

Merge stack #916 first. `SA-0290`, `SA-0291` and `SA-0295` then queue on
`SA-0279`. `SA-0290` has 12 of 22 citations stale at `main`.
