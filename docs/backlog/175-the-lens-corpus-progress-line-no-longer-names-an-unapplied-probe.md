---
id: 175
title: The lens corpus's progress line no longer says which probe did not apply
status: done
tier: 3
filed: 2026-09-17
closed: 2026-11-07
specs: [SA-0096]
prs: []
commits: ["58ecf478"]
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

## Record

- 2026-11-07: closed in grooming. The progress line already names the probe's
  file, which this item's done condition accepts. `SA-0096`'s own commit
  `58ecf478` took only the find text out of the reason and kept the file:
  `source_mutated` yields `{mutant.file}: find text not found`
  (`saffron/cell/worktree.py:741`). `check_probe` returns that refusal verbatim
  as the reason (`saffron/probe.py:206-210`), and the driver prints it at
  `docs/evidence/scripts/2026-09-08-lens-corpus.py:199`. Every other refusal
  `source_mutated` and `probe_refusal` yield names the file too. The item read
  the reason as a bare `find text not found`, which it never was.
