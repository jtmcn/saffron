---
id: 92
title: Three things the corpus's probe path ships knowing, recorded only in scratch
status: open
tier: 3
specs: []
prs: []
commits: []
cites: []
related: [91]
---

## Problem

**Tier 3 — real, not urgent.** All three were found by review on the branch that
built the vacuity-probe path, judged not to block it, and written down in that
branch's SDD workspace — which is git-ignored session scratch. Item 91's own
body makes the argument: a thing recorded only inside the document that depends
on it is a claim, not a record. This is that argument applied to itself.

1. **No test drives the real `CellExecutor` path.** Every driver test replaces
   `run_gate`, so the contract is pinned but the exec is not. One fixture has
   since run end to end against a real cell, which is evidence rather than
   coverage; a `-m cell` test is the durable version.
2. **`tests/test_corpus.py` covers two things** — `harness/corpus.py`'s
   predicate and a dated evidence driver — at ~750 lines. A
   `tests/test_lens_corpus_driver.py` split is mechanical.
3. **`TEST_PATHS = ("tests/",)` is this repo's layout, hardcoded in the
   driver.** `check_probe` requires the argument so it cannot be silently
   absent, and the prefixes are normalised, so the guard holds for the eight
   shipped fixtures. But `--fixtures` points wherever it is told, and
   `src/tests/test_x.py` would pass it. `policy.integrity.test_paths` is the
   right source and is globs (`tests/**`) where this compares prefixes, so it
   is a translation rather than a substitution.

Also open and *not* in this list because it is already in the design spec: the
in-cell suite runs 5.5x faster than the same tree on the host, and nobody has
explained it. `probes.json` now records the gate's tool, collected count and
summary per verdict, so the next pass can say whether the suite that answered
was the whole one.
