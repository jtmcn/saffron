# The lenses, scored against a diff whose defects are already written down

Backlog item **79**, Track A of `docs/superpowers/plans/2026-09-07-trusting-the-queue.md`.
Measured 2026-09-07, `main` at `654330a`. **$5.70, three runs of three lenses**
over one fixture. Raw JSON, one file per run, under
`~/.saffron/lens-scoring/SA-0062-20260907T225001/`.

The question: item 79 says nobody knows what REVIEW would say about a diff with
a known defect in it, because no such diff was kept. PR #154's range is now kept
(`docs/evidence/fixtures/SA-0062/`), with item **78**'s two defects declared
over it and the four prompt inputs frozen beside them. This is the first pass.

## What was run

`docs/evidence/scripts/2026-09-07-lens-scoring.py` builds a cell at `78a25a2` —
PR #154's own first commit, before the two human fix commits, so both defects
are still in the tree — through `session.cell_up`, the same function
`_drive_cell` uses. It then drives `phases.review.run_review` three times over
the frozen diff and scores each run with `harness/lens_scoring.py`.

The reviewed head recorded in `patch.json` (`87baeae`) no longer exists. It was
recovered by comparing the recorded `patch.diff` against live history: the diff
is byte-identical to `git diff 91b6eda..78a25a2`, which identifies the tree.

## The table

| Defect | Owner declared | Seen | Graded | Where it landed |
|---|---|---|---|---|
| `dirty-restore` | correctness | **2/3** | 2/3 | `correctness` worktree.py:422 |
| `truncating-write` | contract | **3/3** | 2/3 | `contract` worktree.py:418 |

Per run, and this is the part the aggregate hides:

| Run | `dirty-restore` | `truncating-write` | Cost |
|---|---|---|---|
| 1 | missed — correctness filed the UTF-8 concern instead | `blocker` | $1.87 |
| 2 | `blocker` | `blocker` | $1.50 |
| 3 | `blocker` | `concern` | $2.33 |

## Three readings

**Item 79's central observation is a sample, not a constant.** It records that
neither defect "was filed at any severity" and reasons from there to a remit
gap: *what does the failure path leave behind* is a question no lens owns. Run 2
of this pass filed **both** defects as blockers, and the truncating write was
raised in all three runs. The lenses as they stand today do own the question.
What they do not do is answer it reliably, and the original run — the single
sample item 79 was written from — happens to be the one where the correctness
lens spent itself on a UTF-8 concern instead. Two of the three runs here would
have produced a REVIEW that blocked the pull request.

**The owner in item 79 is wrong, and it changes Track C.** The item proposes
widening the *correctness* lens's remit, or giving the question to a fourth
lens. Measured: the **contract** lens raised the truncating write 3/3, reaching
it through `witness.Mutated`'s written contract — *"a raise from `__enter__`
must mean nothing was changed"* — which is squarely its own remit, not a stretch
of it. The correctness lens owns the other defect, 2/3. Neither question is
homeless. Track C should be re-aimed at the variance, not at the remit: the
cheap intervention is whatever makes run 1 look like run 2, and adding a fourth
lens would not have changed run 1.

**A `preserves`-style confound is absent here and worth noting.** Neither budget
nor turns bound either run. The original had $3.30 and 90 turns and spent
$0.52–$0.73 per lens; this pass gave $4.00 and 30 turns and spent $0.36–$0.92.
The parameters were not identical, and are reported rather than smoothed, but
no lens came near either ceiling.

## The fixture was wrong twice, and the pass is what found it

Both errors were in the predicate's declaration, not in its code, and both would
have reported this pass backwards. They are corrected in `fixture.toml`, each
with the reason recorded beside it.

**A range that stopped at the callee.** `truncating-write` was declared over
`_write_file`'s own lines, 366-382. All three runs filed it at **418** — the
call site inside `source_mutated`, which is where the missing `try/finally` is,
and therefore where a lens reasoning about what a failed write leaves behind
naturally anchors. The range now runs 366-426.

**A phrase generic enough to match the other defect.** `dirty-restore` listed
`dirty`, and run 1's contract lens — describing the *truncating write* — quoted
`witness.py`'s phrase "understate a dirty tree". That scored the undo. Before
correction the pass read `dirty-restore` 3/3 and `truncating-write` 0/3, which
is close to the exact inverse of what the lenses did. The phrases now name what
is specific to each defect: whose work the undo discards, and that the write
truncates.

Both corrections were made **after** seeing the runs, which is the tuning risk
the harness was designed around, so the safeguards are stated rather than
assumed. The calibration case is unchanged and still holds: the predicate scores
the fixture's own recorded `findings.json` at 0 seen / 0 graded, the answer item
79 already wrote down, and the driver refuses to score a pass when it does not.
The correction made `dirty-restore` **stricter** (3/3 → 2/3) and moved
`truncating-write` only because all three runs had in fact raised it. Two
regression tests now carry the real claim text from runs 1 and 2 and assert each
defect is credited to itself and not the other; re-introducing the `dirty`
phrase fails one of them.

## Deviations

- The frozen `gates.txt` is rebuilt from the ledger's `gate_results` rows, which
  have no `tool` column, so all 14 lines read `no tool reported` where the
  original named tools. Recorded in `fixture.toml`.
- `context.md` is `CONTEXT.md` at base. `session.py:1133` reads the host's
  working copy at run time, which is not recoverable after the fact.
- The driver's first two attempts failed and cost nothing: `run_review` needs an
  `agent` already bound with `spec_id`, and the first teardown forgot
  `proxy.stop_proxy()`, which left the proxy container attached and made
  `remove_network` fail by a return code nobody read. Both are fixed; the second
  is now a comment in the teardown, because the failure it produces lands on the
  *next* run as "network saffron-cells already exists".
