---
id: 175
title: The lens corpus's progress line no longer says which probe did not apply
status: open
tier: 3
filed: 2026-09-17
specs: []
prs: []
commits: []
cites: []
related: [114]
---

## Problem

Found reviewing `SA-0096` (PR #320), 2026-09-17. `SA-0096` took the find text
out of an unapplied mutant's reason, which is right for anything a cell or a
lens reads. `docs/evidence/scripts/2026-09-08-lens-corpus.py` also uses
`source_mutated` as its `mutate` callable, and `:200` prints
`probe {result.verdict}: {result.reason}`. After #320 that line reads
`find text not found` with nothing naming the probe. `probes.json` still
records the whole probe (`:153-158`), so nothing is lost from the record, only
from the console.

## Done looks like

The progress line names the probe's file or index. The harness is
operator-facing, so printing the find text there is allowed.
