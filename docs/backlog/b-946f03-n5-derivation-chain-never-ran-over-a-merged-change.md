---
id: b-946f03
title: N5's derivation chain never ran over a merged change, so a chain a later task overwrote reads as whole
status: done
closed: 2026-09-19
filed: 2026-09-18
specs: [SA-0107, SA-0108]
prs: [355, 366]
commits: []
cites: [§1, §4.1, §4.6, §9]
related: [118, 170]
---

## Problem

Found 2026-09-18, reviewing `DESIGN.md` Appendix T.

Q4 encodes N5 and has only ever run over a hand-authored graph
(`tests/ontology/fixtures/lifecycle.ttl`, loaded at
`tests/ontology/conftest.py:12-17`). No merged pull request was ever its subject.

The batch tree is keyed by spec (`saffron/cell/session.py:1285`), so a later
task of the same spec writes over the earlier task's `plan.json` and
`patch.diff` (`saffron/cell/session.py:751,1582`). A walk over §4.1's foreign
keys that checks each file exists calls the earlier chain whole. The event log
still holds what each task recorded at extraction: the plan's sha256 prefix and
the diff's byte count (`saffron/cell/session.py:768,1583-1587`).

## Done looks like

A projection of the whole ledger is built on demand. Each derivation edge in
it is stated only when the stored file matches its task's record. A
report lists the merged pull requests Q4 drops that the checked walk calls whole.
Appendix T's decision rule is then run over the merged history and its answer
recorded, whichever way it lands. Item 170 closes the overwrite case for
later history, so this answer bears on its choice to migrate or abandon the
tasks already recorded.

## Record

**Filed 2026-09-18** with `SA-0107`, as the origin item Appendix T had stood in
for.

- 2026-09-19: open as PR #355 (`SA-0107`, the projection) and PR #366
  (`SA-0108`, the checked walk). Spec loop run 8 stacked them in #351 ← #360 ← #355
  ← #366 ← #353. Over a copy of the real ledger, #366 compared 38 of 76 merged
  tasks and found 0 breaks. The one real overwrite is among those left out (item
  b-952c34).
- 2026-09-19: #355 and #366 merged. `saffron chains` materializes the
  projection over the real ledger and compares Q4 with the checked walk. Half
  the merged tasks never reach the comparison, and that is item b-952c34.
