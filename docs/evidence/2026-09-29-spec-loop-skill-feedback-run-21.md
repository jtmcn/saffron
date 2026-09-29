# Feedback on run-saffron-spec-loop (run 21, 2026-09-28 to 29)

Six specs ran as attended cells in one chain, from `SA-0187` to `SA-0192`.
The previous session wrote them to move three seats' work into the cell:
b-7e69d0, b-ab4b33 and b-abeb74. All six reached `READY_FOR_REVIEW`. Run 20's
feedback is checked below.

**Outcome:** six pull requests, linked and marked ready. The cells cost
**$81.25** against $148 of budget.

| Spec | PR | Spent | Attempts | In-cell blockers | Seat blockers the critic passed | Size after review |
|---|---|---|---|---|---|---|
| `SA-0187` | #574 | $9.79 of $22 | 2 | 0 | 1 | 2425 of 3000 |
| `SA-0190` | #576 | $14.74 of $26 | 2 | 0 | 1 | 2175 of 3000 |
| `SA-0188` | #577 | $18.36 of $26 | 1 | 1, fixed in REBUT | 0 | 2732 of 3000 |
| `SA-0189` | #579 | $11.41 of $24 | 1 | 0 | 1 | 456 of 3000 |
| `SA-0191` | #580 | $19.79 of $24 | 1 | 0 | 2 | 1939 of 3000 |
| `SA-0192` | #581 | $7.16 of $26 | 1 | 1, withdrawn in REBUT | 1, plus the withdrawn one | 1128 of 3000 |

`SA-0190` ran at `elevated` and landed at 72.5% of its ceiling. `SA-0188`
landed at 91% at `standard`. Its review rewrote three stale docstrings, and
the `prose` ratchet judges an edited docstring as new text.

## What happened, in order

1. **The operator scoped the loop to this chain.** `snapshot --new` took
   seventeen specs. The eleven from `SA-0161` on took eleven `drop` calls,
   as in run 20 (b-c07b92).
2. **The operator skipped step 1b's spec review.** `check` still ran, and it
   cleared all six. `SA-0188` priced at 92%, which the operator had accepted.
3. **The unmeasured arrangements were run, not reviewed.** A forked agent
   measured each item the handoff listed at `095e9fef`. Four held. One
   needed a decision: `revert` checks no witness on `SA-0191`, because
   pytest exits 4 on a `[conventions]` id absent at base.
4. **Spec PR #573 gave `SA-0191`'s criterion 3 a mutant.** A mutant cut from
   the new prompt would be refused as disclosed, since the body spells the
   remit. The mutant points the `LENSES` entry at the adequacy prompt. In
   the cell, `witness` passed with five of five mutants killed.
5. **`revert` skipped on `SA-0187` too.** `tests/test_context.py` reads a
   constant at import that base lacks, so the whole file failed to collect.
   The Spec seat ran every witness at base by hand.
6. **The host's probes filed two blockers in-cell.** `SA-0188`'s was fixed in
   REBUT. `SA-0192`'s was argued away as "outside my diff", and both seats
   found the hole real. A `preserves` criterion is a whole-file property.
7. **Lenses run from `main`, not from the branch.** `SA-0191` and `SA-0192`
   each ran three lenses, so the conventions lens has no live run yet. The
   handoff raised `SA-0192`'s budget for a four-lens REVIEW that never ran.
8. **The seats found blockers the critic passed on five of six pull
   requests.** Four were witnesses that could not fail: a condition keyed on
   the wrong field, a container name that outlives teardown, a `TypeError`
   standing in for an assertion, and an expected value built from the
   constant under test.
9. **The operator decided three things in review.** `calibrate` refuses an
   empty recorded run. `SA-0192`'s block says a blank `CLAUDE.md` also counts
   as none. Step 5 carries the hand edits the specs could not make.
10. **The auto mode classifier gave no verdict on four calls** during
    `SA-0191`'s cell. Reading the log with the Read tool needed no verdict.

## Run 20's items, checked

1. **Probe every wrong version the spec lists** (b-7e69d0): landed as
   `SA-0187` and `SA-0190`. No spec in this run declared `wrong_versions`,
   so the session has not yet run live.
2. **A REBUT from a spec contradiction escalates** (b-ab4b33): landed as
   `SA-0188`. Its own REBUT accepted the optional-field schema. The verdict
   was `withdrawn`, so no live `contradicted` answer ran.
3. **A standards lens in REVIEW** (b-abeb74): landed as `SA-0189`, `SA-0191`
   and `SA-0192`, and still partial. ADR 8's measured pass is hand work, and
   the lens runs live only once the stack merges.
4. **`prose` stops rewarding a split sentence** (b-ad1285): not started.
5. **`check` knows a measured estimate** (b-b0a187): not started. `SA-0188`
   landed at 91% against a 92% forecast.
6. **`terms` reads a negation** (b-f4eb52): not started. Every baseline in
   this run reported `terms=fail`.
7. **A loop can be scoped without `drop`** (b-c07b92): not started. It cost
   eleven calls again.
8. **`stack` checks the merge the operator will make** (b-2e7c4d): not
   started. This chain was linear, so pairwise merges matched the real one.

## ADR 8's evidence: what the seats found that a conventions lens would miss

The lens never ran live, so this comes from the Standards seat reading its
prompt against its own findings on #580 and #581.

- **Text made false outside any hunk.** `SA-0191` left two comments counting
  three lenses and seven turns, 2,600 lines from the nearest hunk. The lens
  asks its questions of each hunk.
- **The spec's own directives.** The spec said to update each comment that
  counts three lenses. The lens judges against the standing instructions,
  not the spec.
- **Message and prompt strings.** `SA-0192`'s constant said no `CLAUDE.md`
  stood while serving a blank one. The remit names comments, docstrings and
  citations only.
- **Test adequacy.** Both of #581's blockers were witnesses that could not
  fail, which the prompt hands to the adequacy lens. That lens reported
  none.
- **`_Avoid_` lists.** They are stripped from the lens's vocabulary (item
  162).

## Summary: what to change first

Each item moves part of a seat's work into a gate, a lens or a phase.

1. **`revert` judges each new witness on its own** (b-cf832a). One
   uncollectable id skips the whole subset. It hit two of six cells, and
   step 1b predicted one of them.
2. **A host-filed probe blocker on a `preserves` criterion cannot be
   argued away as out of scope** (b-cd5fd2). The lens withdrew a real
   hole on `SA-0192`.
3. **Anchoring needs an identifier, not a stopword** (b-38d45f). The
   probe that found `SA-0192`'s hole anchored through words like "the".
4. **A stack exercises its own new lens or phase** (b-66d1c3). Until
   then a chain that adds a lens cannot test it, and budgets assume it runs.
5. **The conventions lens reads beyond the hunk** (b-78ccc7). This covers
   the four gaps above, before ADR 8 retires the Standards seat.
6. **A witness whose expected value is the code under test is refused.**
   `SA-0192`'s criterion 2 compared the constant with itself. The adequacy
   lens passed it, and a structure rule could name the pattern (b-5b1f8a).

## Filed from the reviews

Kept findings became b-cf832a (`revert` skips a subset on one uncollectable
id), b-5b1f8a (a witness comparing a constant with itself), b-cd5fd2 (a
`preserves` probe blocker argued out of scope), b-66d1c3 (a stack never runs
its own new lens), b-78ccc7 (the conventions lens's gaps), b-47659f (the
criterion-probe witness and teardown, unverified), b-38d45f (anchoring on
stopwords), b-84d4f8 ("mutant" in wrong-version summaries) and b-6d43da (a
fixture's recorded lens set).

Step 5 also carries the edits the specs could not make, on the operator's
call. `implement.md` now forbids running the versions listed under a
criterion. `DESIGN.md` and ADR 4 give the verdict its third value and count
four lenses. The issue tracker and the spec writer name `wrong_versions:`.

## The loop's own gaps

- `driver.py bookkeeping` reads the checkout its own file sits in. Run from
  the main checkout, it drafted the old queue for a worktree's step 5.
- `driver.py labels` reads spec-review and pr-review rounds only. The six
  cell rounds' labels go unchecked.
- `driver.py jev --kind cell` writes beside the cell's batch folder, not
  under `spec-loop/`, so a cell round's labels have no `findings.json`
  beside them.
