# The lens corpus's baseline pass — 2026-09-09

The first pass whose numbers are kept. Pass 1 (2026-09-08) was declared disposable and its
only job was correcting the predicates; this is the pass the exit criterion in
`docs/superpowers/plans/2026-09-07-trusting-the-queue.md` is written against.

Raw runs are in `docs/evidence/passes/2026-09-09-lens-corpus-baseline/`, one directory per
fixture, so every number below is re-derivable without a cell. The aggregate is pinned by
`tests/test_corpus.py::test_the_baseline_pass_s_published_aggregate_is_re_derivable`, and
every dollar figure by `test_every_dollar_figure_in_the_baseline_record_is_one_a_run_produced`.

## What was run

`docs/evidence/scripts/2026-09-08-lens-corpus.py` over `docs/evidence/fixtures`, eight
fixtures, `--runs 1`, `--max-turns 30`, `--budget-usd 4.0`, `--max-spend-usd 20.0`.

**In two invocations, not one** — see Deviations 1. The second was a `--skip-existing`
resume of one fixture at identical settings.

## The corpus table

**3/12 declared defects graded** (3/12 seen) across 8 fixture(s).

| Fixture | Defect | Seen | Graded | Anchored blockers |
|---|---|---|---|---|
| SA-0045 | `reflow-defeats-guard` | 0/1 | 0/1 | 0 |
| SA-0046 | `reflow-defeats-guard` | 0/1 | 0/1 | 0 |
| SA-0048 | `refusal-codes-unpinned` | 1/1 | 1/1 | 1 |
| SA-0050 | `breaker-reset-unguarded` | 1/1 | 1/1 | 1 |
| SA-0054 | `parent-branch-unpinned` | 0/1 | 0/1 | 0 |
| SA-0054 | `stop-line-unwitnessed` | 0/1 | 0/1 | 0 |
| SA-0055 | `pinned-base-unwitnessed` | 0/1 | 0/1 | 0 |
| SA-0055 | `readiness-guard-unwitnessed` | 0/1 | 0/1 | 0 |
| SA-0062 | `dirty-restore` | 0/1 | 0/1 | 2 |
| SA-0062 | `truncating-write` | 1/1 | 1/1 | 2 |
| SA-0063 | `notes-neutralization-unwitnessed` | 0/1 | 0/1 | 1 |
| SA-0063 | `empty-notes-heading-unwitnessed` | 0/1 | 0/1 | 1 |

No fixture dropped. Drop rate is `0%` at every fixture: 21 findings, none unanchored.

## The aggregate

**`B = 3`.** That is the number the criterion takes, and the paragraph below is why it is not
the number pass 1 would suggest.

**Pass 1 re-scored graded 4/12, and the two are not comparable.** This branch changed
`saffron/agents/prompts/review-adequacy.md`, adding a required `probe` field. The ownership of
the corpus is lopsided:

| Owner | Declared defects | Graded here |
|---|---|---|
| adequacy | **10 of 12** | 2 — SA-0048, SA-0050 |
| contract | 1 | 1 — SA-0062 `truncating-write` |
| correctness | 1 | 0 |

Both SA-0063 defects — the whole of the `4 → 3` difference — are adequacy-owned, and adequacy
is the lens whose prompt changed. So the two passes are one sample each of two configurations,
not two samples of one. `4 → 3` is neither noise nor a measured regression: it is confounded,
and this record claims neither reading. What it does claim is that **`3` is the count under the
prompt that runs from here on**, which is the only configuration a forward-looking criterion
can be written against.

The same fact bars the opposite claim: **this work cannot be said to have left adequacy's
recall unchanged.** Adequacy went 3/10 to 2/10 across the prompt change, n=1 each side.
Answering that needs a controlled measurement, and is filed rather than guessed.

**SA-0063's `notes-neutralization-unwitnessed` scored 0/1, and it is a lens miss, not a
predicate failure.** The `locations` predicate landed for this defect specifically. Every
finding SA-0063 produced here anchored in `saffron/cell/session.py` and
`saffron/phases/package.py`; none in `saffron/report/pr_body.py` or `tests/test_report.py`,
where both defects are declared. Nothing reached the corrected predicate to be matched by it,
so the correction is untested in a pass rather than refuted by one.

### Vacuity probes

**8 verified vacuities** — 8 of 10 probes that answered survived, 2 `killed`, 0 `unproven`,
over 8 fixtures probed. Hand-aggregated across the eight `probes.json` files (Deviation 3).

SA-0046 and SA-0055 filed no probe and paid no baseline suite for it, which is
`docs/BACKLOG.md` item 92.1 working in a pass for the first time. Both are still counted among
the eight: an empty `probes.json` is coverage, an absent one is not.

**Amended 2026-09-09: none of these ten verdicts records the baseline it was subtracted from,
and none ever will.** `probes.json` kept only what survived the subtraction, so a `survived`
computed against a baseline that was already red reads identically to one over a green suite.
Measured on `SA-0063`'s head (`f76931df`): `1502 passed` on the host, `1 failed, 1499 passed,
2 skipped` in the cell at the same 1502 collected. The subtraction cancels that failure
correctly — no *new* failure — but whether it is the very test that would have caught the
mutation is undecidable from this record, and if it is, the cancellation masks a kill. That is
**2 of the 8 above**, and `docs/BACKLOG.md` item 94 is why no re-run can settle them: a probe
is authored by the lens per run, so re-running yields different probes rather than an audit of
these.

Item 94 landed the same day and is entirely forward-looking. `ProbeResult` now carries the
baseline's failure identities, tool, collected count and summary line, and `probes.json` writes
them — from the *next* pass onward. The ten verdicts above carry no such key, which reads back
as `None` rather than as a baseline that was green; a test pins that, so the distinction cannot
quietly close. Read the `8` accordingly: it is a lower bound with two entries whose baseline
nobody can inspect, not eight equally-evidenced vacuities.

### Cost

Per fixture, read from each run's own JSON rather than derived by subtraction:

| Fixture | Total | correctness | contract | adequacy |
|---|---|---|---|---|
| SA-0045 | $1.68 | $0.30 | $0.93 | $0.44 |
| SA-0046 | $1.74 | $0.52 | $0.57 | $0.66 |
| SA-0048 | $1.88 | $0.53 | $0.94 | $0.41 |
| SA-0050 | $2.15 | $0.73 | $0.85 | $0.57 |
| SA-0054 | $2.92 | $1.22 | $1.00 | $0.70 |
| SA-0055 | $1.54 | $0.34 | $0.55 | $0.64 |
| SA-0062 | $2.26 | $0.99 | $0.60 | $0.67 |
| SA-0063 | $2.37 | $1.32 | $0.41 | $0.63 |
| **Published baseline** | **$16.53** | | | |

The two invocations printed $17.31 and $2.92, and $20.23 was spent to produce a $16.53
baseline: the difference is SA-0054's discarded run at $3.70. That reconciles exactly
($13.61 for the seven kept fixtures of invocation 1, plus $3.70, is $17.31), and the
reconciliation is a check rather than a derivation — the per-fixture figures were read from
the JSONs first and the invocation totals matched them afterwards.

**The driver's projection was low.** `--max-spend-usd`'s help extrapolates `~$12.90` from
$1.61 per fixture-run measured on one fixture, and says plainly that nobody had run the corpus
driver itself. Measured: **$16.53**, 28% over. The help is corrected in the same commit as this
record.

## Per-fixture anchored blockers

Five, all anchored, none dropped.

| Fixture | Lens | Anchor | Claim |
|---|---|---|---|
| SA-0048 | correctness | `saffron/preflight.py:315` | `validate_claude_token`'s own docstring against what it checks |
| SA-0050 | adequacy | `saffron/batch.py:178` | no test attaches a run to its batch on that outcome |
| SA-0062 | contract | `saffron/cell/worktree.py:418` | `_write_file` outside any handler that can undo it |
| SA-0062 | contract | `saffron/cell/worktree.py:418` | `_write_file` before the generator's first `yield` |
| SA-0063 | contract | `saffron/phases/package.py:834` | `render_pr_body` called without `notes=outcome.notes` |

SA-0055 produced **zero findings** from all three lenses, which is a real answer and is
distinguishable in the JSON from a lens that emitted nothing.

## The 5.5x, narrowed by measurement

The in-cell suite runs the *whole* suite, and that kills the leading explanation.

| Fixture | collected | in-cell elapsed |
|---|---|---|
| SA-0045 | 1250 | 13.04s, 13.28s |
| SA-0048 | 1266 | 13.12s |
| SA-0050 | 1292 | 13.43s, 14.19s |
| SA-0054 | 1309 | 13.65s, 14.02s |
| SA-0062 | 1484 | 19.00s |
| SA-0063 | 1502 | 18.88s, 20.41s |

`survived` means "no new failure against the baseline", and a suite that collected almost
nothing is green too — that was the open worry, and it is answered: 1250 to 1502 tests
collected and run.

**Measured on one tree, both ends, 2026-09-09.** The table above compares eight heads against
host figures taken at one, which is not a controlled comparison. So `SA-0063`'s head
(`f76931df`) was run on the host directly, in a detached worktree of its own:

| | collected | elapsed |
|---|---|---|
| Host, `f76931df` | 1502 | **107.31s** |
| Cell, `f76931df` | 1502 | **18.88s**, **20.41s** |

**5.7x on the same tree at the same collection count**, and the gap is **still unexplained** —
this record does not explain it. What it does retire is the two ways out that were still open:
the suite is whole, and the comparison no longer rests on different heads.

**The same run found a second symptom, and it is not about speed.** That tree is **green on the
host — `1502 passed`** — while the cell reports `1 failed, 1499 passed, 2 skipped` at the same
1502 collected. So one failure and two skips exist only in the cell. The failure's identity is
recorded nowhere (Deviation 5), and the skips are unexplained. Every `survived` verdict in this
corpus is computed against a baseline that may be red for reasons like that one.

## Deviations

1. **The baseline is two invocations.** In invocation 1, SA-0054's `contract` lens reached its
   ceiling of 30 turns (`error_max_turns`); `LensReview.error` drops all three lenses' findings
   for that run, so the fixture produced no scored run and its two declared defects left the
   denominator — the pass reported `3/10` across 7 fixtures. SA-0054 was re-run through
   `--skip-existing` at **identical settings**: `--max-turns` was deliberately not raised,
   because a fixture scored under different settings than the other seven is a worse deviation
   than the drop was. The re-run's `contract` lens finished with 0 findings and no error.
2. **The discarded run is archived, not deleted** —
   `~/.saffron/lens-scoring/corpus-baseline-pass2-archive/SA-0054-contract-max-turns/`, moved
   out of the scored tree so a `run-*.json` glob cannot score one fixture on two runs while
   the others have one. It is outside the repo; this record is its only in-repo mention, which
   is the item-91 hazard and is accepted here because the run it holds is one nothing is
   claimed from.
3. **The vacuity number is hand-aggregated.** No invocation printed it: invocation 1 printed
   8 over 8 fixtures with SA-0054's errored run still in the recall denominator, and the resume
   printed 2 over 1 fixture. Nothing re-aggregates probes across invocations — the driver's own
   `ponytail` says so. The eight `probes.json` files in this pass directory are the source.
4. **`table.md` here is `--score-only` output**, which renders no second number by design, so
   the recall table and the vacuity number in this record come from different renderings. The
   two invocation tables are kept beside it as
   `table-invocation-1-sa0054-dropped.md` and `table-resume-sa0054.md`.
5. **Two of the eight survivals cannot be checked, by any means.** SA-0063's `tests` gate
   fails **in the cell** at its own head — `docs/evidence/fixtures/SA-0063/gates.txt` records
   `tests: fail (pytest 9.1.1) — 1 failed, 1499 passed, 2 skipped, 21 deselected`, the same
   shape both probe summaries report. Baseline subtraction cancels it and both probes record
   `failures: []`, which is correct: no *new* failure. But `probes.json` persists only
   post-subtraction failures, so whether that failure is in the very test that would have
   caught the mutation is undecidable. If it is, the cancellation masks a kill and those two
   are not vacuities.

   **It is not a property of the tree.** An earlier draft of this line said it was, on the
   strength of `gates.txt` alone. Measured instead: the same tree runs **`1502 passed`** on the
   host. The failure exists only in the cell, which makes it a worse problem than a known-bad
   head would have been, not a bounded one.

   **And no re-run can settle it.** A probe is authored by the lens per run — `SA-0054`'s
   re-run named two *different* edits — so re-running SA-0063 yields different probes rather
   than an audit of these. `docs/BACKLOG.md` item 94 is therefore worth landing for the passes
   that come after, and these two stay unauditable permanently.
6. **Dated by production.** `docs/superpowers/plans/2026-09-08-lens-corpus.md` Task 9 names
   `2026-09-08-lens-corpus-baseline`; this is `2026-09-09`, the day it ran, matching how every
   other file under `docs/evidence/` is dated.
