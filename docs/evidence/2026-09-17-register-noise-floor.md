# The register metric's noise floor — 2026-09-17

Task 1 of `docs/superpowers/plans/2026-09-17-prompt-change-measurement.md` (the spike): before
building anything that scores a prompt edit by how the `prose` gate reads REVIEW's claims, this
measures whether that score is stable enough to see a prompt edit at all. It writes no committed
code — a throwaway script, run against an existing pass, and this record.

## What was run

The three runs of `docs/evidence/passes/2026-09-11-lens-corpus-spread/` (8 fixture directories —
`SA-0045`, `SA-0046`, `SA-0048`, `SA-0050`, `SA-0054`, `SA-0055`, `SA-0062`, `SA-0063` — each
with `run-1.json`, `run-2.json`, `run-3.json`) are three samples of the **same** prompt: nothing
in REVIEW's prompt changed between them, only sampling did. For each run, every lens finding's
`claim` text across all 8 fixtures was pooled and scored with the `prose` gate:

```python
gate.check(text, "claim.md", "prose", root=REPO)
```

`root=REPO` so `protected_words` reads `CONTEXT.md` and Saffron's own vocabulary is not scored
as filler. `"claim.md"` is neither a spec (which would enable the spec-only
`trailing-condition` rule) nor a root document (which would enable rendered-span logic) — a
plain prose file, scored on the same rules a claim's prose would draw regardless of which
fixture or lens produced it.

The script (not committed, per this task's brief) lived at
`<scratchpad>/noise_floor.py` for the run and no longer exists on disk:

```python
import importlib.util, json, sys, pathlib
from collections import Counter

REPO = pathlib.Path(".")
PASS = REPO / "docs/evidence/passes/2026-09-11-lens-corpus-spread"

spec = importlib.util.spec_from_file_location("pg", REPO / ".saffron/gates/prose.py")
gate = importlib.util.module_from_spec(spec); sys.modules["pg"] = gate
spec.loader.exec_module(gate)

per_run = {}
for fixture in sorted(p for p in PASS.iterdir() if p.is_dir()):
    for f in sorted(fixture.glob("run-*.json")):
        run = int(f.stem.split("-")[1])
        claims, words, hits = per_run.setdefault(run, [0, 0, Counter()])
        for lens in json.loads(f.read_text()):
            for finding in lens.get("findings") or []:
                text = finding.get("claim")
                if not text:
                    continue
                per_run[run][0] += 1
                per_run[run][1] += len(text.split())
                per_run[run][2].update(h.code for h in gate.check(text, "claim.md", "prose", root=REPO))

for run in sorted(per_run):
    claims, words, hits = per_run[run]
    total = sum(hits.values())
    print(f"run {run}: {claims} claims, {words} words, {total} hits, "
          f"{1000*total/words:.1f} per 1k  {dict(hits.most_common())}")
```

Run with:

```
uv run python <scratchpad>/noise_floor.py
```

Every number below re-derives by writing the snippet above into a scratch file and running it
against the same pass — the pass itself is on disk, unchanged, at
`docs/evidence/passes/2026-09-11-lens-corpus-spread/`.

## The three runs

Verbatim output:

```
run 1: 21 claims, 2602 words, 100 hits, 38.4 per 1k  {'sentence-length': 48, 'em-dash': 30, 'filler': 13, 'semicolon': 9}
run 2: 22 claims, 2757 words, 115 hits, 41.7 per 1k  {'sentence-length': 52, 'em-dash': 36, 'filler': 19, 'semicolon': 5, 'hedge': 2, 'contraction': 1}
run 3: 21 claims, 2651 words, 108 hits, 40.7 per 1k  {'sentence-length': 52, 'em-dash': 31, 'filler': 13, 'semicolon': 7, 'contraction': 4, 'perfect-tense': 1}
```

Total claims across all three runs: **64** (21 + 22 + 21) — matching the prior probe's count
named in this task's brief. Nothing about the pass or the gate has changed since.

Per-rule breakdown, the three runs side by side:

| Rule | run 1 | run 2 | run 3 |
|---|---|---|---|
| `sentence-length` | 48 | 52 | 52 |
| `em-dash` | 30 | 36 | 31 |
| `filler` | 13 | 19 | 13 |
| `semicolon` | 9 | 5 | 7 |
| `hedge` | 0 | 2 | 0 |
| `contraction` | 0 | 1 | 4 |
| `perfect-tense` | 0 | 0 | 1 |
| **Total hits** | **100** | **115** | **108** |
| **Per 1k words** | **38.4** | **41.7** | **40.7** |

## The spread

Highest per-1k: **41.7** (run 2). Lowest: **38.4** (run 1). Spread: **3.3 per 1k**, about 8.6% of
the lowest value and about 8.2% of the three-run mean (40.3).

`sentence-length` and `em-dash` dominate every run's total (78–88 of each run's hits) and move
together with claim/word count, which tracks: more or longer claims draw more of both rules
mechanically. The smaller-count rules move relatively more between runs — `contraction` is 0, 1,
4; `hedge` is 0, 2, 0; `perfect-tense` is 0, 0, 1 — but they are a small enough share of the
total (at most 4 of 100+ hits) that they do not drive the per-1k figure's spread on their own.
`filler` moved from 13 to 19 to 13, a real jump in run 2 not mirrored in run 3.

## What was surprising

- Claim count and word count both moved slightly between runs despite an identical prompt (21,
  22, 21 claims; 2602, 2757, 2651 words) — REVIEW's own sampling varies which findings surface
  and how each claim is phrased, before the `prose` gate ever runs. The metric measured here
  inherits that upstream variance; it is not itself the source of it.
- Run 1 and run 3 have the same claim count (21) but different word counts (2602 vs. 2651) and
  different per-1k figures (38.4 vs. 40.7) — the metric is sensitive to phrasing, not just to how
  many claims a run produced.
- The rarest rules (`hedge`, `contraction`, `perfect-tense`) are the ones that appear in only one
  or two of the three runs at all, which is consistent with them being low-count, high-variance
  categories rather than a broken rule.

## Reasoning for the controller

Three identical-prompt runs land at 38.4, 40.7, and 41.7 per 1k — a range of 3.3, centered
around a mean of about 40.3. Whether a real prompt edit (the kind Task 2 would introduce number
targets or register instructions to fix) is expected to move the per-1k figure by more or less
than 3.3 is the judgment call this record hands to the controller, not one this task makes.
Points relevant to that call:

- The spread is about 8% of the mean, all attributable to sampling noise, not to a code change of
  any kind — the gate, the fixtures, and the prompt were held fixed.
- The two rules that carry most of the signal (`sentence-length`, `em-dash`) also carry most of
  the spread in absolute hit counts, so the metric's noise is concentrated in the same rules it
  would need a prompt edit to move.
- n=3 is a range, not a distribution — as `docs/evidence/2026-09-11-lens-corpus-spread.md` notes
  for a different metric under the same pass, three points support a range statement and nothing
  about how the samples are shaped between the endpoints.

DECISION: <pending controller ruling>
