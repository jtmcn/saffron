# The same diff, with the gate summary naming its tools: the gap did not move

Backlog item **88**, the second pass of Track A's harness. Measured 2026-09-08
on branch `joel/lens-gates-tool`. **$4.84, three runs of three lenses** over
`docs/evidence/fixtures/SA-0062`. Raw JSON, one file per run, in
`docs/evidence/passes/2026-09-08-lens-scoring-second-pass/`. Tests re-compute
every number below from those three files.

The question: the first pass
(`docs/evidence/2026-09-07-lens-scoring-first-pass.md`) filed anchored blockers
1, 2, 1 over PR #154's range, where the production run of the same range filed
**zero** and reached `READY_FOR_REVIEW`. Every harness run would have routed to
REBUT (§5.5); production's did not. Item 88 named the frozen `gates.txt` the
leading suspect — it was rebuilt from `gate_results` rows that carried no
`tool`, so every line read `no tool reported`, and §5.4 makes `tool` exactly
what separates a gate that ran from one that never did. A lens with structural
reason to distrust fourteen gates digs harder, which is a bias in the direction
observed.

**One input changed.** The tools are back in `gates.txt`, spliced from the same
run's `baseline.json` in the batch tree. Budget, turns, lens prompts, diff, spec
body and `context.md` are the first pass's, unchanged, so this pass reads as a
difference and not as a second absolute.

## The table

| Defect | Owner declared | Seen | Graded | Where it landed |
|---|---|---|---|---|
| `dirty-restore` | correctness | **1/3** | 1/3 | `correctness` worktree.py:422 |
| `truncating-write` | contract | **2/3** | 2/3 | `contract` worktree.py:418 |

Per run, beside the first pass's:

| Run | `dirty-restore` | `truncating-write` | Anchored blockers | Cost |
|---|---|---|---|---|
| 1 | missed | missed | 1 | $1.55 |
| 2 | missed | `blocker` | 1 | $1.60 |
| 3 | `blocker` | `blocker` | 2 | $1.68 |

| Pass | Anchored blockers per run | Total | Cost |
|---|---|---|---|
| First (no tools) | 1, 2, 1 | 4 | $5.70 |
| Second (tools) | 1, 1, 2 | 4 | $4.84 |
| Production | 0 | 0 | — |

## Three readings

**The suspect is eliminated, and it explains nothing.** Four anchored blockers
across three runs, both passes; every run of both would have routed to REBUT.
Naming the tools moved the count by zero. Whatever produces 3-of-3 blocking here
against 0-of-1 in production, it is not the gate summary — which is worth having
paid for, because it was the cheapest candidate and the one the fixture's own
provenance flagged as a live confound rather than a footnote.

**The per-defect scores moved and the blocker count did not, which is the more
useful finding.** `dirty-restore` went 2/3 → 1/3 and `truncating-write` 3/3 →
2/3 seen, on an input change with no mechanism to make either defect harder to
see. That is the spread of the measurement, read directly: at n=3, per-defect
scores swing by a third on a fixture where nothing relevant changed, while the
aggregate a pull request actually turns on — did any lens file an anchored
blocker — was identical. **Item 79's exit criterion is written on the noisier of
the two numbers.** Requiring both defects in 3 of 3 runs is a threshold this
pass would fail and the previous one would also fail, and neither failure would
mean a lens got worse. Track C should either raise n or read the criterion as a
difference across passes of equal n, never as a count met once.

**What is left.** Two candidates from item 88 survive, and the pass narrows
neither. Budget and turns are still not production's — production gave $3.30 and
90 turns, both passes gave $4.00 and 30 — though no lens came near either
ceiling in either pass ($0.43–$0.68 here against a $4.00 lens budget), so this
remains the unlikely one. That leaves genuine run-to-run variance against a
production sample of **one**. A single production run that filed zero is not
evidence that production filed zero reliably; the harness has n=3 twice and
production has n=1, and the honest comparison is not available until production
runs the range again.

**So item 88 closes where it said it would.** The harness's absolute numbers
steer nothing. Its *differences* between two prompts over the same fixture do,
and this pass is the first evidence that those differences are readable at all:
one input changed, and the number Track C would read moved by zero while the
number it should not read moved by a third.

## Deviations

- `gates.txt`'s tools are spliced from the same run's `baseline.json` rather
  than recorded at review time: `gate_results` gained a `tool` column on
  2026-09-08, but the 14 rows predate it and a nullable column is null for every
  one. Base and head ran the same binaries from the same cell image in the same
  run, so a version string in the baseline suite is the version string at head.
  Recorded in `fixture.toml`; the splice is
  `docs/evidence/scripts/2026-09-08-sa0062-gate-tools.py`, which refuses to write
  if regeneration moves anything but a tool.
- Seven of the fourteen lines still read `no tool reported`. They are host-side
  core gates that execute nothing, and they read that way in production too —
  the first pass's record and item 88 both overstated the deviation as all
  fourteen, and both are corrected.
- Budget and turns are the first pass's ($4.00, 30), not production's ($3.30,
  90). Held constant across the two passes deliberately: matching production
  would have changed two inputs at once and made this pass unreadable.
- The cell image is built from the working copy's `.saffron/Dockerfile`, which
  is byte-identical to the first pass's and to `head_sha`'s. `uv.lock` is
  unchanged too, so the gate tool versions the fixture now names are the ones a
  cell here would still produce.
