# A corpus for the lens harness: eight fixtures, twelve defects, one number

Track A of `docs/superpowers/plans/2026-09-07-trusting-the-queue.md`, closing the
half item 79 left open. Written 2026-09-08, after backlog item **88**.

## Why

Item 88's second pass measured the harness against itself: one input changed,
and the per-defect scores moved by a third — `dirty-restore` 2/3 → 1/3,
`truncating-write` 3/3 → 2/3 seen — while the aggregate a pull request turns on,
did any lens file an anchored blocker, was identical at four. Nothing about that
input could make either defect harder to see. That spread is the harness's
resolution at n=3 over one fixture, and it is wider than any prompt change Track
C would make.

So Track C cannot currently read its own work. A lens edit that moved a defect
from 1/3 to 2/3 would be indistinguishable from the noise two unmodified passes
already produce. The fix is not more repeats of one diff — repeats measure that
diff's variance. It is more diffs.

`load_fixture` takes a single root and `score_pass` scores a single fixture, so
aggregating across fixtures is unbuilt. That is what this design adds.

## Decisions taken before the design

**Wide and shallow: eight fixtures at n=1, not one fixture at n=3.** Twelve
independent defect-observations for ~$13 a pass, against six for ~$5. Per
dollar it buys more, and the aggregate over twelve defects has a far tighter
error bar than any single k/3 — which is the whole complaint above.

**Two passes to a trustworthy baseline, ~$26 once.** Pass 1's only job is to fix
predicates: every miss read by hand, each one judged miss-or-mis-declared, the
`must_mention` phrases corrected, and the corrections recorded as having been
made after seeing runs. Its numbers are then discarded. Pass 2 is Track C's
baseline, graded by predicates frozen before it ran. Every later iteration is
~$13 against that baseline.

This is the safeguard the SA-0062 fixture had to improvise. Its phrases were
corrected twice after seeing runs, and what ended up guarding those corrections
was a pair of regression tests carrying verbatim claim text from runs 1 and 2.
The twelve new defects have no such text: item 69's rows were found by the
operator running mutations, not by a lens writing a finding. At n=1 a wrong
phrase and a lens miss are the same observation, so the tuning has to happen in
a pass that is declared disposable rather than in the one Track C reads.

**A corpus module beside the predicate, not inside it.** `lens_scoring` keeps
answering one question — did this run see this defect — and stays the linted,
tested predicate it is. `harness/corpus.py` composes it and owns the arithmetic
Track C reads.

## The corpus

Eight fixtures, twelve declared defects. Two are shipped; ten are recovered.

| Spec | PR | base..head | Defects | Source |
|---|---|---|---|---|
| SA-0045 | 115 | `2e563cf0..f9f007c4` | 1 | item 69 — `SCHEMA` reflow defeats the migration guard |
| SA-0046 | 116 | `a79b680b..c71eeca9` | 1 | item 69 — the same, second occurrence |
| SA-0048 | 117 | `c71eeca9..64c71614` | 1 | item 69 — `exc.code not in (401, 403)` neutered, 89 tests green |
| SA-0050 | 121 | `5c103860..91f56c69` | 1 | item 69 — breaker reset deleted, suite green |
| SA-0054 | 123 | `fe39b41a..70091cd8` | 2 | item 69 — `parent_branch=None`; a `print` reduced to `pass` |
| SA-0055 | 131 | `aa8dfd17..e5a7cbe9` | 2 | item 69 — `pinned=derived` invisible to an `ast.Constant` match; the `readiness.ok` guard deleted |
| SA-0062 | 154 | `91b6eda8..78a25a23` | 2 | item 78, shipped |
| SA-0064 | 160 | `3ba55621..2544fc05` | 2 | item 86 — neutralization on the notes path; criterion 4's witness |

Item 69's ninth row, the SHACL `sh:in` deletion, is **excluded**: it is attached
to backlog item 65 rather than to a spec, so it has no batch tree and no
recorded findings to calibrate against. Recovering it is hand archaeology and it
would add one defect to twelve.

Every declared defect is one a lens *should* have raised and did not: each
fixture's `recorded_seen` and `recorded_graded` are therefore `0`, and
`calibrate` asserts exactly that before any money is spent.

### Recovery, and why it is verifiable

Every `head_sha` recorded in `patch.json` is gone from live history — the branch
was deleted after merge — so each fixture's range is recovered rather than read
off. The rule is uniform:

- **head** is the ledger's `pushed_sha` for the task.
- **base** is the first ancestor of that head where `git diff base..head` is
  **byte-identical** to the batch tree's recorded `patch.diff`.

Byte-identity is the acceptance test, not a heuristic: a fixture whose range
cannot be reproduced exactly fails recovery loudly instead of shipping an
approximate diff that would grade a lens against a tree it never saw.

Four of the eight need the walk because `patch.json`'s recorded `tree_base` is
not an ancestor of their head at all. The reason is worth recording: **SA-0048's
true base is SA-0046's head**. These were stacked pull requests, and the batch
tree recorded the base the task was cut against rather than the branch it was
built on — backlog item **33**'s disagreement, visible in the archive. The walk
is indifferent to the cause; the byte-identity check is what makes it safe.

## Modules

### `harness/corpus.py` — new

```
load_corpus(root)            -> list[Fixture]     every subdirectory with a fixture.toml
calibrate_corpus(fixtures)   -> None              raises on the first that fails
score_corpus(fixtures, runs) -> CorpusScore       runs keyed by spec_id
anchored_blockers(runs)      -> dict[str, list[int]]
render_corpus_table(score)   -> str
```

`CorpusScore` carries the per-fixture `dict[str, Score]` unchanged — so every
existing per-fixture table still renders — plus `declared`, `seen` and `graded`
counted over defects rather than over fixtures.

**The aggregate is `graded / declared`, weighted per defect.** Twelve defects,
each contributing 0 or 1 at n=1. Per defect rather than per fixture because a
fixture carrying two defects is two independent observations, and averaging
within it first would throw one of them away.

Reported beside it, per fixture: the count of anchored blockers. That is the
number item 88 showed is stable across passes, and the only number production
can be compared against at all.

**n=1 has no redundancy, and the denominator has to say so.** `score_pass` drops
a run whose lens errored and raises when nothing survives — at n=3 that costs a
third of a fixture, at n=1 it costs the fixture entirely. So `declared` counts
only the defects of fixtures that produced a scored run, and `CorpusScore`
carries the dropped fixtures by name. A pass that silently reported `7/12` where
two fixtures never ran would be reporting a lens miss for an error, which is the
distinction `LensErrored` exists to keep. The driver's `--skip-existing` re-run
is the repair: rerun the dropped fixture alone and score the pass again.

### `harness/lens_scoring.py` — two changes

`load_fixture` refuses a fixture declaring zero defects. Today a `defects = []`
would load and score `0/0`, which reads like a measurement — the same failure
`score_pass` already refuses for zero surviving runs.

Nothing else moves. `score_pass`, `score_run`, `match`, `calibrate` and
`render_table` are unchanged, so both recorded passes stay re-derivable by the
tests that pin them.

### `docs/evidence/scripts/2026-09-08-recover-fixture.py` — new

Given a spec id, writes `docs/evidence/fixtures/<SPEC>/`: `diff.patch` from the
batch tree's `patch.diff`, `recorded-findings.json` from its `findings.json`,
`gates.txt` from the ledger's rows with tools spliced from `baseline.json`,
`spec_body.md` as the spec at base plus its criteria section, `context.md` as
`CONTEXT.md` at base, and a `fixture.toml` carrying the recovered range and
`recorded_seen = recorded_graded = 0`.

It generalises `2026-09-08-sa0062-gate-tools.py`, which already reads both of
those records for one spec. That script **stays**: `fixture.toml` and the
second-pass record both cite it by name as the provenance of SA-0062's restored
tools, and a deleted script makes those citations unfollowable. The splice moves
into a function both import.

The `[[defects]]` blocks are **not** generated. They are declared by hand from
each backlog row, because the row is the only place the mutation that proves the
defect is written down, and a generated guess would be a predicate nobody chose.

### `docs/evidence/scripts/2026-09-08-lens-corpus.py` — new

Walks the corpus: calibrate every fixture first, then per fixture bring up a
cell at its head, run the lenses, write `run-1.json` under that fixture's name,
tear the cell down. The existing single-fixture driver stays exactly as it is,
so both recorded passes remain reproducible by the file that produced them.

Two properties it needs that the single-fixture driver does not:

**Resumable.** Each fixture's JSON is written the moment it lands, and a
`--skip-existing` re-run continues rather than restarting. A failure at fixture
six must not cost the first five.

**One image, eight cells.** `image.cell_tag` keys off the repo path, not the
tree, so the image builds once and each fixture pays only for a worktree at its
own head. Budget ~80 minutes of wall-clock for a pass, mostly cell starts.

## What replaces the exit criterion

The plan's criterion 3 reads *"REVIEW grades both of PR #154's defects in 3 of 3
runs"*. Item 88 showed that number is the noisiest the harness prints. It
becomes:

> REVIEW grades at least **B** of the corpus's twelve declared defects, where
> **B** is pass 2's measured baseline, and no fixture that graded a defect at
> baseline grades none.

**B is deliberately blank until pass 2 runs.** Choosing a threshold before
measuring the baseline is how criterion 3 came to be written against an absolute
in the first place.

## Testing

- Recovery is exact: a test asserts each shipped fixture's `diff.patch` is
  byte-identical to `git diff base..head` at the range its `fixture.toml`
  declares. This is what makes the archaeology above auditable rather than
  claimed.
- `calibrate_corpus` passes over the corpus as shipped — the same guard
  `calibrate` gives one fixture, over all eight, run in `make check`.
- A fixture declaring no defects is refused, proven against a fixture with its
  `defects` emptied.
- The aggregate counts defects and not fixtures, proven on a corpus where one
  fixture carries two defects and another carries one.
- Pass 2's published numbers are re-derived from its committed run JSONs, and
  every dollar figure its record prints must be one the data or a declared
  budget produces — the stronger form written for the second pass, not the
  weaker one the first pass used.

## What this does not do

**It does not close item 69.** That item's "done looks like" is a spec-guided
mutation check — break the property a claim names and require *that* witness to
fail. This borrows item 69's table as evidence and leaves the mechanism to item
71's seam and `SA-0059`.

**It does not settle item 88.** Production's side of that comparison is n=1, and
no work on the harness changes it. The corpus makes the harness's own numbers
readable; it does not make production's readable.

**It does not widen the corpus past twelve defects.** Item 65's `sh:in` row and
any future range stay out until something needs them, and `load_corpus` reading
a directory means adding one is a fixture directory rather than a code change.
