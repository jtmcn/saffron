# Spec chain feedback, 2026-09-22: SA-0123 and SA-0124

Two specs through `create-saffron-spec`, stacked. `SA-0123` is the writer
side of item b-fd1468. `SA-0124` is item 171, stacked on it because both
touch `saffron/ledger.py`. Item 177 was weighed the same day. The operator
chose to redefine **Run** as one task's pin, which edits protected documents,
so it gets no spec.

## Cost

| Step | Agent | Time | Tokens |
|---|---|---|---|
| SA-0123 draft, with a prototype | `spec-writer` | 34.9 min | 293k |
| SA-0123 first review | `spec-reviewer` | 8.0 min | 169k |
| SA-0123 revise, prototype rebuilt | `spec-writer` | 8.0 min | 38k |
| SA-0123 second review | `spec-reviewer` | 6.9 min | 142k |
| SA-0124 draft, with a prototype | `spec-writer` | 21.3 min | 218k |
| SA-0124 first review | `spec-reviewer` | 5.0 min | 111k |
| SA-0124 revise, one new run | `spec-writer` | 5.9 min | 18k |
| SA-0124 second review | `spec-reviewer` | 4.6 min | 102k |

Both revisions resumed the writer that drafted the spec. Each cost under a
fifth of a fresh draft, because the prototype and its context were still
held. The SA-0124 draft ran in a separate worktree while SA-0123 was
under review.

## First reviews: no blocker on either spec

| Spec | Finding | Class | Check that should have caught it |
|---|---|---|---|
| SA-0123 | Criterion 3's full ledger held no run or gate result of its own | A witness drives one member of a set | Pre-flight 1 |
| SA-0123 | The wrong implementations criteria 1 to 3 exclude were claimed, not run | An arrangement argued rather than run | Pre-flight 10 |
| SA-0123 | Size near 940 against 1000 after SA-0117's growth | Size or ceilings | Pre-flight 7 |
| SA-0123 | A dropped payload assert removed the only `error` status check in its file | A change breaking a live check or test | Pre-flight 6 |
| SA-0123 | An old-record exit code was stated and not measured | An arrangement argued rather than run | Pre-flight 10 |
| SA-0123 | One citation one line early | A claim about the tree | Pre-flight 5 |
| SA-0124 | `replay.py` was said to write no task row | A claim about the tree | Pre-flight 5 |
| SA-0124 | A `_finish` storing NULL for a measured 0 passed every witness | A witness drives one member of a set | Pre-flight 1 |
| SA-0124 | `DESIGN.md:1221` becomes false in a forbidden file | A design argument the documents do not support | Pre-flight 8 |
| SA-0124 | Test line numbers move under the parent too | A claim about the tree | Pre-flight 5 |

The measured-zero finding is the set class again. The set was the values a
stat can take, and the witness drove one of them. The run settled it in six
minutes. A mode-only patch never reaches `diff_stat`. An empty-file patch
does, and the counterfeit passed four witnesses until that run was added.

## Second reviews: one concern

| Spec | Finding | Class | Check that should have caught it |
|---|---|---|---|
| SA-0124 | The widened claim said a measured 0 on four paths, and the new run drives one | A witness drives one member of a set | Pre-flight 1, on the revision |
| SA-0123 | A counterfactual exit code named the wrong missing key | A claim about the tree | Pre-flight 5, on the revision |
| SA-0123 | §4.6 rule 1 was cited for the record, and it governs the graph | A design argument the documents do not support | Pre-flight 8 |
| SA-0124 | The empty-file run named no git version | A claim about the tree | Pre-flight 5 |

Every second-round finding came from text the revision added. The delegate
applied them by hand and did not re-review, under the two-round stop.

## What the next run should change

1. **Re-run pre-flight 1 on each revision.** A fix that widens a claim to a
   new member is itself a set claim. Both second-round set findings were
   revisions that closed one member and named more.
2. **Say where a tool behaviour was measured.** The host runs git 2.54.0 and
   the cell runs 2.39.5. A spec that quotes git output should name the host.
3. **Keep one scratch directory per writer.** The SA-0124 writer synced into
   a `proto` directory an earlier writer had left. It lost nothing that
   mattered, since SA-0123 was committed first.
