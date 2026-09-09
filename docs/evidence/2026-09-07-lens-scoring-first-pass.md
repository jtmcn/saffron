# The lenses, scored against a diff whose defects are already written down

Backlog item **79**, Track A of `docs/superpowers/plans/2026-09-07-trusting-the-queue.md`.
Measured 2026-09-07, on branch `joel/lens-scoring-harness` at `654330a` —
not on `main`, which does not contain it. **$5.70, three runs of three lenses**
over one fixture. Raw JSON, one file per run, in
`docs/evidence/passes/2026-09-07-lens-scoring-first-pass/` — kept in the repo
rather than left under `~/.saffron/`, because a table nobody but its author can
re-derive is item 79's own complaint one level up. Tests re-compute every number
below from those three files: the table, and — since the per-lens range was
first published as run 1's maximum rather than the pass's — the costs beside
it.

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
lens spent itself on a UTF-8 concern instead.

**All three runs would have blocked the pull request**, against zero blockers on
the production run of the same range. Anchored blockers per run are 1, 2, 1 —
every finding in this pass anchored — and §5.5 routes any single anchored blocker
to REBUT. *(Corrected 2026-09-08: this paragraph first read "two of the three",
taking the number from `dirty-restore`'s 2/3 and applying a per-defect score to a
per-pull-request claim, two lines under a per-run table that already said run 1
filed the truncating write as a blocker. A test named for the count now pins it
to the data.)*

That gap — 3/3 here against 0/1 in production, on the same diff — is larger than
this pass can explain, and it is the reason the `gates.txt` deviation below is a
confound and not a footnote.

**The owner in item 79 is wrong, and it changes Track C.** The item proposes
widening the *correctness* lens's remit, or giving the question to a fourth
lens. Measured: the **contract** lens raised the truncating write 3/3, reaching
it through `witness.Mutated`'s written contract — *"a raise from `__enter__`
must mean nothing was changed"* — which is squarely its own remit, not a stretch
of it. The correctness lens owns the other defect, 2/3. Neither question is
homeless. Track C should be re-aimed at the variance, not at the remit — and
the variance that is left, once every run turns out to have blocked, is narrower
than "run 1 was green" made it sound: it is *which* defect a run raises and at
what grade. Run 1 missed the undo entirely; run 3 filed the truncating write as
a concern. Both are one lens-session away from run 2, which filed both as
blockers. A fourth lens would not have changed either.

**The budget confound is absent; the gate-summary one is not.** Neither budget
nor turns bound either run. The original had $3.30 and 90 turns and spent
$0.52–$0.73 per lens; this pass gave $4.00 and 30 turns and spent $0.36–$1.01.
The parameters were not identical, and are reported rather than smoothed, but no
lens came near either ceiling. *(Corrected 2026-09-08: the range read
$0.36–$0.92, which is run 1's maximum, not the pass's — run 3's adequacy lens
spent $1.01. The table beside this paragraph was pinned to the run JSON and the
paragraph was not; both are now.)*

The frozen `gates.txt` is a different matter. All 14 lines read `no tool
reported`, because `gate_results` has no `tool` column to rebuild them from —
and §5.4 makes `tool` precisely what separates a gate that ran from one that
never did. A lens told that fourteen gates ran and not one of them named a tool
has structural reason to distrust the gates and dig harder. That biases toward
*more* findings, which is the direction of every conclusion here, including the
3/3-versus-0 gap above. It is the leading candidate for that gap and this pass
cannot separate it from lens variance. A second pass over a fixture whose gate
summary names its tools would.

*(Corrected 2026-09-08: "where the original named tools", below, overstated what
the deviation was. Production named **7 of 14** — `scope`, `integrity`, `size`,
`committed`, `census` and `criteria` are host-side core gates that execute
nothing and report no tool, in production as here, and `witness` inherits the
`tests` tool but skipped a spec that declares no mutants. The gap this pass
could not separate from variance is 7 named against 0, not 14 against 0. The
tools are restored in the fixture and the second pass measures what that moves:
`docs/evidence/2026-09-08-lens-scoring-second-pass.md`.)*

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
assumed — and one of them was first stated too broadly.

**Calibration does not reach either correction, and this record originally
claimed it did.** The calibration case is unchanged and still holds: the
predicate scores the fixture's own recorded `findings.json` at 0 seen / 0
graded, and the driver refuses to score a pass when it does not. But its reach
is exactly the lines those three recorded findings landed on — `worktree.py:358`,
`worktree.py:379`, `runner.py:308` — so it asserts one thing: that the adequacy
concern at 379 does not match `truncating-write`'s phrases. **Nothing recorded
lands in `dirty-restore`'s range at all**, so dropping `dirty` could not have
moved calibration, and neither could widening `truncating-write` past 382.
Measured, not reasoned: calibration passes on the pre-correction fixture, on the
shipped one, and on the shipped one with `dirty` put back. A fixture built from a
run that missed both defects can only be calibrated where that run happened to
look.

**What actually guards the corrections is the regression tests**, which carry
verbatim claim text from runs 1 and 2 and assert each defect is credited to
itself and not the other; re-introducing `dirty` fails one of them. Beside them,
a test re-derives this record's whole table from the committed run JSONs, so a
predicate change that silently moves a published number fails in `make check`.
Those are authored from the same runs that motivated the correction, which is
worth saying plainly rather than dressing up as independent.

The arithmetic the corrections claim does hold: `dirty-restore` went **stricter**
(3/3 → 2/3), and `truncating-write` moved only because all three runs had in fact
raised it — scored against the pre-correction fixture the pass reads 3/3 and 0/3,
close to the exact inverse.

## Deviations

- The frozen `gates.txt` is rebuilt from the ledger's `gate_results` rows, which
  have no `tool` column, so all 14 lines read `no tool reported` where the
  original named 7. Recorded in `fixture.toml`, and treated as a confound
  above rather than only listed here. *(Corrected 2026-09-08: read "named
  tools", which reads as all 14.)*
- `context.md` is `CONTEXT.md` at base. `session.py` reads the host's working
  copy at run time, which is not recoverable after the fact.
- The driver's first two attempts failed and cost nothing: `run_review` needs an
  `agent` already bound with `spec_id`, and the first teardown forgot
  `proxy.stop_proxy()`, which left the proxy container attached and made
  `remove_network` fail by a return code nobody read. Both are fixed; the second
  is now a comment in the teardown, because the failure it produces lands on the
  *next* run as "network saffron-cells already exists".
