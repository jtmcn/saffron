# The lens corpus after `CLAUDE.md` reaches every lens — 2026-09-11

`docs/evidence/2026-09-11-lens-corpus-spread.md` measured the metric's spread under lenses
that did not receive the repo's `CLAUDE.md`. This pass re-ran the identical corpus after
`fix(review): no lens was shown the invariants it judged a diff against`, which put
`CLAUDE.md` in front of the three review lenses and the verdict lenses too. This record
answers whether that change moved the score, under the decision rule Task 10 Step 3 of
`docs/superpowers/plans/2026-09-10-claude-md-reaches-every-phase.md` fixed before either
number existed.

Raw runs are in `docs/evidence/passes/2026-09-11-lens-corpus-claude-md/`, one directory per
fixture (`run-1.json`…`run-3.json`, `probes.json`) plus the rendered `table.md` at the root, so
every number below is re-derivable without a cell. The per-run line is pinned by
`tests/test_corpus.py::test_the_claude_md_pass_s_per_run_totals_are_re_derivable`.

## What was run

From branch `joel/claude-md-reaches-lenses`, when it sat on the pre-rebase base — the lens
code is identical to HEAD now:

```
env SAFFRON_ALLOW_HOST_PROCESS=rapportd CLAUDE_CODE_OAUTH_TOKEN=… uv run python \
    docs/evidence/scripts/2026-09-08-lens-corpus.py \
    --fixtures docs/evidence/fixtures --out ~/.saffron/lens-corpus-claude-md \
    --runs 3 --max-spend-usd 70
```

with the defaults `--budget-usd 4.0` and `--max-turns 30`. The ceiling was raised from the
spread pass's 60 to 70 because every lens prompt now also carries `CLAUDE.md`.

**One invocation**, run from about 10:42 to 14:13 on 2026-09-11 (file mtimes in the archive
this was copied from). No `--max-spend-usd` trip and no `--skip-existing` resume.

## The corpus table

Pasted verbatim from `table.md`:

**6/12 declared defects graded** (6/12 seen) across 8 fixture(s).

Per run, each scored alone: 1/10 · 4/12 · 4/12 graded. The headline counts a defect graded in any run, so it rises with `--runs`; these are the spread.

| Fixture | Defect | Seen | Graded | Anchored blockers |
|---|---|---|---|---|
| SA-0045 | `reflow-defeats-guard` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0046 | `reflow-defeats-guard` | 0/3 | 0/3 | 0, 0, 1 |
| SA-0048 | `refusal-codes-unpinned` | 3/3 | 3/3 | 1, 1, 1 |
| SA-0050 | `breaker-reset-unguarded` | 2/3 | 1/3 | 0, 1, 0 |
| SA-0054 | `parent-branch-unpinned` | 2/2 | 2/2 | 2, 1, 1 |
| SA-0054 | `stop-line-unwitnessed` | 0/2 | 0/2 | 2, 1, 1 |
| SA-0055 | `pinned-base-unwitnessed` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0055 | `readiness-guard-unwitnessed` | 0/3 | 0/3 | 0, 0, 0 |
| SA-0062 | `dirty-restore` | 1/3 | 1/3 | 2, 1, 2 |
| SA-0062 | `truncating-write` | 2/3 | 1/3 | 2, 1, 2 |
| SA-0063 | `notes-neutralization-unwitnessed` | 1/3 | 1/3 | 3, 2, 1 |
| SA-0063 | `empty-notes-heading-unwitnessed` | 0/3 | 0/3 | 3, 2, 1 |

**14 verified vacuities** — adequacy-lens findings whose named edit left the fixture's suite green. 14 of 20 probe(s) that answered survived; 0 unproven and in no denominator, over 8 fixture(s) probed this invocation at 3 run(s) each — which need not be every fixture in the table, since recall is re-derived from every run JSON on disk and a resumed pass probes only what it ran. A total over those runs, not a rate over them, so it does not compare with a pass at a different `--runs`. Not comparable with the recall line above either: one lens, and a lower bound — a killed probe may have broken the program rather than been noticed, which is adjudicated per probe and not computed.

## The dropped run

SA-0054's run 1 was dropped: its `contract` lens hit the 30-turn ceiling
(`error_max_turns/max_turns` after 31 turns, no output), and `score_pass` drops an errored
run rather than scoring it as a miss. That leaves SA-0054's two declared defects at `k/2` in
the Seen and Graded columns of the table above — its Anchored blockers column still lists all
three runs (`2, 1, 1`), since run 1's surviving lenses are counted there — and run 1's own
per-run total at a denominator of 10, not 12 — `SA-0054` contributes nothing to that slice.

This is not the first time this exact fixture has hit this exact ceiling.
`docs/evidence/2026-09-09-lens-corpus-baseline.md`'s Deviations §1 records the baseline's
first invocation losing SA-0054's `contract` lens to the same `error_max_turns` at the same
`--max-turns 30`, under the prompt *before* `CLAUDE.md` reached any lens. That earlier drop
was re-run at identical settings rather than by raising the ceiling. Two trips at the same
ceiling under two different prompt lengths is consistent with SA-0054's `contract` lens
being close to the 30-turn ceiling on its own merits — it does not, by itself, implicate the
longer `CLAUDE.md`-carrying prompt as the cause of this drop. It also does not clear the
longer prompt: one more turn either way decides a trip this close to the line, and n=2 does
not separate "this fixture is just slow" from "the added prompt cost a turn." The ceiling
was already raised for this pass (item above); it was not raised further after this drop,
matching the spread pass's own precedent of not changing settings mid-comparison.

## The spread comparison

The old configuration's four samples (`docs/evidence/2026-09-11-lens-corpus-spread.md`) against
this pass's three:

| Sample | Graded/Declared |
|---|---|
| Old — baseline (`2026-09-09`, `--runs 1`) | 3/12 |
| Old — spread pass, run 1 | 1/12 |
| Old — spread pass, run 2 | 2/12 |
| Old — spread pass, run 3 | 3/12 |
| New — this pass, run 1 (partial: 10 of 12 declared) | 1/10 |
| New — this pass, run 2 | 4/12 |
| New — this pass, run 3 | 4/12 |

**Old range: 1/12 to 3/12. New range: 1/10 to 4/12.** The ranges overlap: `1/10` (0.10) falls
inside the old range (`1/12` ≈ 0.083 to `3/12` = 0.25).

**Decision rule** (`docs/superpowers/plans/2026-09-10-claude-md-reaches-every-phase.md`, Task
10 Step 3, quoted verbatim):

> - **ranges do not overlap, new above** — the change helped at this resolution; say so.
> - **ranges overlap** — no measurable difference at n=3; say that, not "no effect".
> - **ranges do not overlap, new below** — stop. Do not submit layer 3; bring the record to
>   the operator. `CLAUDE.md` may be crowding out the lens remit, which is the cost §5.3's
>   per-phase slicing names. Layers 1 and 2 stand on their own and can merge without it.

The ranges overlap, so the verdict is **no measurable difference at n=3**.

**Observations the rule does not turn into a verdict:**

- Both complete runs of this pass (`4/12` each) sit above every old sample (baseline `3/12`
  and all three spread-pass runs). Run 1 is the only new sample inside the old range, which is
  why the ranges overlap. Run 1 is also the partial sample: 10 of 12 declared defects, not 12,
  because SA-0054 dropped out of that slice (see above), so it is not directly comparable to
  the other five samples on a raw count, only as a rate — which is how it is treated above.
- **Which per-defect rows moved**, read off the two tables' `k/n` columns: `SA-0054`'s
  `parent-branch-unpinned` was `0/3` in the spread pass and is now `2/2` (both surviving
  runs graded it — recall its denominator changed too, from the dropped run). `SA-0062`'s two
  defects, both graded `0/3` in the spread pass, are now graded `1/3` each. Against that,
  `SA-0050`'s `breaker-reset-unguarded` moved the other way on both columns: `3/3` seen and
  `2/3` graded in the spread pass down to `2/3` seen and `1/3` graded here. `SA-0062`'s
  `truncating-write` also moved on `Seen`, `1/3` to `2/3`, one run ahead of where it moved on
  `Graded`. `SA-0054`'s `stop-line-unwitnessed` reads `0/3` in the spread pass and `0/2` here —
  the same denominator shift as `parent-branch-unpinned`, from the same dropped run, with the
  same `0` numerator both times, so it is not counted as a content move here. Every other
  row — seven of twelve — is unchanged in both `Seen` and `Graded` between the two tables.
- The best-of-3 headlines (`3/12` graded, `5/12` seen, in the spread pass's table; `6/12`
  graded and seen here) are the same depth, `--runs 3` on both sides, so they compare like for
  like as a pair. They are still best-of-*n*, though, and the decision rule above is written on
  the per-run totals, not the headline — the headline moving is not itself evidence for the
  rule's verdict.
- The two passes' vacuity-probe totals — 16 of 22 surviving in the spread pass, 14 of 20 here
  — count different probe sets: a probe is authored by the adequacy lens fresh on every run,
  so `--runs 3` twice files two different sets of edits, not the same 22 replayed. These two
  totals are not presented as a change for that reason, matching how `table.md` itself
  declines to compare a pass's probe total across `--runs`.

## Cost

Per fixture, summed over the three runs' own `cost_usd` fields (sum over lenses and runs,
never derived by subtraction), by a one-off script (not committed; command and output are in
this task's report):

| Fixture | Total | correctness | contract | adequacy |
|---|---|---|---|---|
| SA-0045 | $3.93 | $0.98 | $2.05 | $0.91 |
| SA-0046 | $5.24 | $1.72 | $1.75 | $1.77 |
| SA-0048 | $4.58 | $1.58 | $1.94 | $1.06 |
| SA-0050 | $4.95 | $2.00 | $1.31 | $1.63 |
| SA-0054 | $8.56 | $3.02 | $3.90 | $1.63 |
| SA-0055 | $5.27 | $1.07 | $1.45 | $2.75 |
| SA-0062 | $6.97 | $2.75 | $1.39 | $2.83 |
| SA-0063 | $4.54 | $1.68 | $1.10 | $1.77 |
| **Published total** | **$44.04** | **$14.80** | **$14.88** | **$14.35** |

**$70 held.** One invocation spent $44.04 against the $70 ceiling raised for this pass — no
trip, no resume, and $25.96 of headroom left.

## The comparison isolates the prompt change

`main` gained other merged work while this branch's pass ran, but none of it touched the lens
prompts, `saffron/phases/review.py`, `saffron/phases/rebut.py`, or `saffron/agents/context.py`:

```
git diff --stat a92571d d1d3aae -- saffron/agents/prompts saffron/phases/review.py \
    saffron/phases/rebut.py saffron/agents/context.py
```

produces no output — no lines changed in any of those paths between the two commits. What
moved on `main` in that window did not touch what this pass is scoring.

That is `main`'s window, not the one that matters for comparing against the spread pass, which
is from the spread pass's code to this pass's code. #199 (`fix(session): a hook refusing the
repair checkpoint orphaned a task the next suite should have judged`) is the one non-prompt
change in that narrower window, and it touches only `_repair`'s host checkpoint in
`saffron/cell/session.py` — REPAIR, which the corpus never runs.

## Next

n=3 on each side is not enough to place `1/10` cleanly inside or outside the old spread; the
two ranges overlapping is itself a statement about resolution, not about the effect being
absent. What would settle it is more samples of the same configuration — another pass at
`--runs 3`, or a single pass at a higher `--runs`, either one adding to this pass's three
per-run totals rather than to the old four. This record does not recommend spending on that
pass; it names what would answer the question if one is run.
