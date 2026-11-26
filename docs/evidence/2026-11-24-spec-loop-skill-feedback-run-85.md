# Feedback on run-saffron-spec-loop (run 85, 2026-11-24)

Run 85 kept the goal of runs 55 to 84: implement every backlog item. It ran
one spec in one batch.

| Batch | Spec | PR | Outcome | Spend of budget |
|---|---|---|---|---|
| 106 | `SA-0425` | #1315 | `ORPHANED`, taken by hand | $26.77 of $30 |

The batch ran at $80 with `--stack --defer-end-review` and ended `BUDGET`.
Its $13 left could not re-queue the orphaned spec. Its deferred finish holds
no adopted layer, so it did not run.

Beside the loop, the spec chain merged `SA-0429` (#1314) and drafted
`SA-0430`.

## What the run found

1. **The container refused an exec after REBUT a third time.** `SA-0425`
   ended `ORPHANED` on "no PID data from sync pipe", as `SA-0423` did twice
   in run 84. In both specs the REBUT agent ran the whole suite in
   the cell. `SA-0426`'s and `SA-0428`'s REBUTs ran few tests or none, and
   both survived. Recorded on b-f582ee.
2. **REVIEW's one blocker was an equivalent mutant.** The witness let
   `and not self.emptied_by_death` survive on the budget-signal branch. A
   marked REBUT stage has spent its whole pool, so a later call is refused
   before any agent runs. REBUT argued it, and nobody judged it.
3. **Two queued specs contradicted each other.** `SA-0429`, merged as a
   spec, said a kept `ORPHANED` parent is offered again. `SA-0430`, being
   written, refuses it. Each passed alone, and together they turn
   `tests/test_cli.py` red. The `SA-0430` writer found it by applying both
   prototypes. No gate compares two queued specs' claims.
4. **The delegate ran `make check` on a tree it was editing.** The run was
   stopped and redone after the commit.

## What the reviews found

- `SA-0425`: the Spec seat ran 22 wrong versions, and one survived. A death
  row's REBUT line could lose its own error. The Standards seat found a bare
  "stage" and "pool" in new comments. Both were fixed. Jev scored 6 answers
  on the cell review and 15 on the PR review.

## Run 84's items, checked

- [ ] **`saffron adopt` takes an `ORPHANED` or `REBUTTAL_UNJUDGED` task:**
  specified as `SA-0429` (#1314). It waits on `SA-0430`.
- [ ] **REBUT retries an agent that exited with no result event:** open, on
  b-53354f.
- [ ] **The host checks each declared wrong version against its own witness
  before the cell:** open, on b-216235. It recurred as item 2.
- [ ] **The adequacy lens drives each member a claim names:** open. The seat
  blocker this run was one more member no witness pinned.
- [ ] **The `prose` gate reads attribute docstrings:** open, on b-e0e720.

## Summary: what Saffron should absorb next

1. **A cell runs no full suite during REBUT.** A phase change, on b-f582ee.
   Item 1 is the evidence. The host already re-gates after REBUT.
2. **`saffron adopt` takes an `ORPHANED` or `REBUTTAL_UNJUDGED` task.** A
   tool change, `SA-0430` then `SA-0429`.
3. **The queue checks two queued specs' claims against each other.** A gate
   change. Item 3 is the evidence.
4. **REBUT retries an agent that exited with no result event.** A phase
   change, on b-53354f.
5. **The `terms` gate reads `CONTEXT.md`'s _Avoid_ words in Python.** A gate
   change, on item 174.

This PR changes no skill text.

## Next run

Run 86 runs `SA-0430`, then `SA-0429`, once `SA-0430`'s spec merges.
