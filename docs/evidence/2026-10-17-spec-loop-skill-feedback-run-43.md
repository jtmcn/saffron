# Feedback on run-saffron-spec-loop (run 43, 2026-10-17)

Run 43's order was `SA-0284` and `SA-0294`. The operator added `SA-0284`
once #893 merged. Thirteen more queued specs wait on a chain that starts at
`SA-0284`.

`SA-0294` ran as one attended cell and ended `READY_FOR_REVIEW` at $16.97 of
$25. PACKAGE opened #898. Batch 36 then ran with `--stack` at $90 and spent
$37.29. `SA-0284` ended `READY_FOR_REVIEW` at $32.11 of $42, its spec review
included, and PACKAGE opened #899. The batch stopped at `BUDGET` before
`SA-0276`. The loop spent $54.26 against $67 of spec budgets.

## Before the run

- **`check` blocked both specs on citations.** `SA-0284` had 9 of 27 that
  no longer resolved, and `SA-0294` had 3 of 35. #897 refreshed all 12 by
  hand. Two `ledger.py` quotes matched many lines and needed a narrower
  range. The batch's spec review found nothing to revise.
- **No batch could run this order.** A plain batch rescans after each task,
  so `SA-0276` would follow `SA-0284`. A `--stack` batch puts `SA-0294`
  behind 13 chained specs. The operator chose an attended cell for
  `SA-0294` first, then a `--stack` batch (b-f73cd0).

## What the run found

1. **`main` was red at `SA-0294`'s base.** Four `tests/test_corpus.py`
   fixture witnesses failed in the cell and passed on the host. The local
   branches that carried five fixture heads were deleted after run 42. The
   checkout held 10 of origin's 26 `refs/fixtures/*`, and the mirror copies
   refs from the checkout. A host-side fetch restored them (b-055fa3).
2. **The batch stacked `SA-0284` on #898.** A `--stack` batch took the open
   pull request as its stack base, though neither spec names the other.
3. **The delegate pushed to that stack base mid-batch.** The skill says to
   hold review commits until the batch drains. The delegate reverted the
   remote within a minute, while `SA-0284` sat in IMPLEMENT (b-3a79a0).
4. **`driver.py stack` ordered the layers backwards.** It reads only
   `depends_on`, so it put #899 below #898. The delegate linked them by hand
   with `gh stack link 898 899` (b-3a79a0).
5. **Retiring `SA-0294` turned `dead` red.** Its `pending_symbols` deferred
   `citation_defects` until a caller lands. The step 5 PR moves the entry to
   `SA-0295`, as commit `2cd7b9ae` did for `record_regate`.
6. **A seat wrote its findings block as bullets.** Jev refused it. The seat
   emitted JSON on a second request.

## What the reviews found

On #898 the Spec seat ran 34 probes over five criteria and killed all but
one. The surviving probe changed how a follow-up's `cite` raise is recorded,
and a review commit added its witness. Both seats confirmed two of the
critic's concerns and refuted its note.

- `citation_defects`'s docstring contradicted criterion 3. Fixed.
- `run_stack_batch`'s docstring kept ten lines with two overlong lines.
  Fixed.
- A citation at line `0` resolves, in core and in the driver. The operator
  sent both copies to b-2da959.
- `CONTEXT.md`'s Refusal entry lacks the citation cause. Kept as b-74a122.

On #899 the Spec seat found four mutants its witnesses missed. Review
commits killed each one.

- The decline witness passed with each reason dropped.
- A token read passed with the token set in the shell.
- The green witness could not see the probe run before `reverify`.
- A deleted task branch reported itself as a parent branch.
- `regate` loses PACKAGE's `revert` exemption. The critic, the end review
  and both seats raised it. Kept on b-6b06e1.

## Run 42's items, checked

1. **A batch runs the loop's order (b-f73cd0)**: recurred. The loop ran
   one spec by hand to work around it.
2. **`cite` judges a citation by its construct (b-2da959)**: not started.
   Run 43 adds a third fault to it.
3. **A test that reads the host's own repository fails on the host too**:
   recurred in a new shape. The corpus witnesses read host refs a cell
   lacks.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-17 are the
evidence.

1. **A batch runs the loop's order (b-f73cd0).** A phase change. It cost
   an attended cell this run and a skipped spec in run 42.
2. **A stack records the base each layer was cut from (b-3a79a0).** A phase
   change. The driver then orders the stack from the record, and refuses a
   push to a running batch's stack base.
3. **The `adequacy` lens asks whether a witness runs with the spec's named
   seams.** A lens change. Four of #899's survivors were witnesses that never
   pinned the environment or the order the spec named.
4. **A fixture head is reachable from a ref a clone fetches (b-055fa3).** A
   gate change. The baseline should not depend on the host's branches.

## Next run

`SA-0276` heads the chain once #899 merges. A `--stack` batch over the chain
needs each spec's ceiling plus the reserve and writer shares, half of
`--budget` together. Nothing else is queued outside the chain.
