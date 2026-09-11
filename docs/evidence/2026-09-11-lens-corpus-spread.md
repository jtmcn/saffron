# The lens corpus's spread — 2026-09-11

The baseline (`docs/evidence/2026-09-09-lens-corpus-baseline.md`) was one run per fixture: one
sample of the corpus aggregate under the current lenses. `docs/BACKLOG.md` item 93 asked for
the metric's resolution — how much that aggregate moves between runs of *unchanged* lenses,
before any prompt change is read off it. This is the `--runs 3` pass that answers the cheap
half of item 93; the confound half (a pass under the pre-probe prompt) stays open.

Raw runs are in `docs/evidence/passes/2026-09-11-lens-corpus-spread/`, one directory per
fixture (`run-1.json`…`run-3.json`, `probes.json`) plus the rendered `table.md` at the root, so
every number below is re-derivable without a cell. The per-run line is pinned by
`tests/test_corpus.py::test_the_spread_pass_s_per_run_totals_are_re_derivable`.

## What was run

From branch `joel/corpus-per-run-spread` at `b0e7431` (`graded_per_run`, which makes
`render_corpus_table` print each run's own total):

```
env SAFFRON_ALLOW_HOST_PROCESS=rapportd CLAUDE_CODE_OAUTH_TOKEN=… uv run python \
    docs/evidence/scripts/2026-09-08-lens-corpus.py \
    --fixtures docs/evidence/fixtures --out ~/.saffron/lens-corpus-spread \
    --runs 3 --max-spend-usd 60
```

with the defaults `--budget-usd 4.0` and `--max-turns 30`.

**One scored invocation**, not two — see Deviations 1. It ran from about 22:12 on 2026-09-10 to
01:46 on 2026-09-11 (file mtimes). No `--max-spend-usd` trip and no `--skip-existing` resume.

## The corpus table

Pasted verbatim from `table.md`:

**3/12 declared defects graded** (5/12 seen) across 8 fixture(s).

Per run, each scored alone: 1/12 · 2/12 · 3/12 graded. The headline counts a defect graded in any run, so it rises with `--runs`; these are the spread.

| Fixture | Defect | Seen | Graded | Anchored blockers |
|---|---|---|---|---|
| SA-0045 | `reflow-defeats-guard` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0046 | `reflow-defeats-guard` | 0/3 | 0/3 | 2, 1, 0 |
| SA-0048 | `refusal-codes-unpinned` | 3/3 | 3/3 | 1, 2, 2 |
| SA-0050 | `breaker-reset-unguarded` | 3/3 | 2/3 | 0, 1, 1 |
| SA-0054 | `parent-branch-unpinned` | 0/3 | 0/3 | 0, 0, 1 |
| SA-0054 | `stop-line-unwitnessed` | 0/3 | 0/3 | 0, 0, 1 |
| SA-0055 | `pinned-base-unwitnessed` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0055 | `readiness-guard-unwitnessed` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0062 | `dirty-restore` | 1/3 | 0/3 | 1, 1, 0 |
| SA-0062 | `truncating-write` | 1/3 | 0/3 | 1, 1, 0 |
| SA-0063 | `notes-neutralization-unwitnessed` | 1/3 | 1/3 | 2, 1, 2 |
| SA-0063 | `empty-notes-heading-unwitnessed` | 0/3 | 0/3 | 2, 1, 2 |

**16 verified vacuities** — adequacy-lens findings whose named edit left the fixture's suite green. 16 of 22 probe(s) that answered survived; 0 unproven and in no denominator, over 8 fixture(s) probed this invocation at 3 run(s) each — which need not be every fixture in the table, since recall is re-derived from every run JSON on disk and a resumed pass probes only what it ran. A total over those runs, not a rate over them, so it does not compare with a pass at a different `--runs`. Not comparable with the recall line above either: one lens, and a lower bound — a killed probe may have broken the program rather than been noticed, which is adjudicated per probe and not computed.

**Two comparisons this record does not make**, because `table.md` itself says not to: the
16-verified-vacuities line is a total over three runs against the baseline's total over one, and
the best-of-3 headline (`3/12`, `5/12` seen) is best-of-*n* against the baseline's best-of-1 —
neither pair is comparable. The per-run totals are.

## The spread

Four samples of the same lens configuration — the three per-run totals here, plus the
baseline's single-run pass, all under the prompt with the required `probe` field:

| Sample | Graded/Declared |
|---|---|
| Baseline (`2026-09-09`, `--runs 1`) | 3/12 |
| This pass, run 1 | 1/12 |
| This pass, run 2 | 2/12 |
| This pass, run 3 | 3/12 |

**Range: 1/12 to 3/12** — a spread of 2 defects out of 12, over n=4.

**What that means for exit criterion 3** (`docs/superpowers/plans/2026-09-07-trusting-the-queue.md`,
"REVIEW grades at least **3** of the corpus's twelve declared defects … over two consecutive
passes"): n=4 gives a range, not a distribution — nothing here is a mean, a standard deviation,
or a claim about how the four samples are shaped between the endpoints. What the range does
support: a pass reporting `3` is not distinguishable from this pass's ordinary spread, since `3`
is both the baseline's value and this pass's own run-3 value. And a pass reporting as low as `1`
is also within the spread already measured here, under lenses nobody changed. The criterion's
own margin clause — "at least 3 … over two consecutive passes" — is what a range this wide
argues for: one pass at `3` proves nothing on its own, which this pass's run 1 (`1/12`) and run 2
(`2/12`) demonstrate directly, both scored under the identical lenses that produced the
baseline's `3`.

**Which per-defect rows moved, read off the table's `k/3` columns.** Of the twelve rows, one
defect's `Graded` count is not unanimous across the three runs: `SA-0050`'s
`breaker-reset-unguarded` graded `2/3` — missed in exactly one run. The other eleven rows are
unanimous in `Graded` within this pass: ten always `0/3`, one (`SA-0048`'s
`refusal-codes-unpinned`) always `3/3`. `Seen` — the weaker bar — moved on three more rows:
`SA-0062`'s `dirty-restore` and `truncating-write` (`1/3` seen, never graded) and `SA-0063`'s
`notes-neutralization-unwitnessed` (`1/3` seen, `1/3` graded — the one run that saw it also
graded it). No row went from graded-every-run to graded-never, or the reverse; the movement
that exists is at the margin, not a reversal.

## Cost

Per fixture, summed over the three runs' own `cost_usd` fields (sum over lenses and runs, never
derived by subtraction):

| Fixture | Total | correctness | contract | adequacy |
|---|---|---|---|---|
| SA-0045 | $4.14 | $0.66 | $2.31 | $1.16 |
| SA-0046 | $5.36 | $1.38 | $2.33 | $1.64 |
| SA-0048 | $4.15 | $1.24 | $1.58 | $1.32 |
| SA-0050 | $4.76 | $1.41 | $2.25 | $1.09 |
| SA-0054 | $7.80 | $3.04 | $3.24 | $1.53 |
| SA-0055 | $4.56 | $1.09 | $1.12 | $2.36 |
| SA-0062 | $5.16 | $1.14 | $2.06 | $1.96 |
| SA-0063 | $7.05 | $3.38 | $1.93 | $1.74 |
| **Published total** | **$42.97** | **$13.33** | **$16.82** | **$12.82** |

**$60 held.** One scored invocation spent $42.97 against a $60 ceiling — no trip, no resume, and
$17.03 of headroom left. The driver printed this total only to the operator's terminal; every
figure above is summed from each run JSON's own `cost_usd` field, over lenses and runs, by a
one-off script (not committed — its command and output are in this task's report).

## Deviations

1. **The invocation that ran is the second attempt.** The first stopped at preflight before any
   cell or lens ran, so nothing was spent. The worktree had no `.env`, so
   `SAFFRON_ALLOW_HOST_PROCESS=rapportd` — this dev laptop's tolerated `rapportd` listener, per
   `docs/HOST-HARDENING.md` — was unset, and preflight refused host port 50671. The rerun put the
   variable on the invocation itself, as the command above shows, and is the only scored run.
