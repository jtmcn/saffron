---
id: b-946f03
title: N5's derivation chain never ran over a merged change, so a chain a later task overwrote reads as whole
status: open
filed: 2026-09-18
specs: [SA-0107]
prs: []
commits: []
cites: [§1, §4.1, §4.6, §9]
related: [118]
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

A projection of the whole ledger is rebuilt at every batch end. Each derivation
edge in it is stated only when the stored file matches its task's record. A
report lists the merged pull requests Q4 drops that the checked walk calls whole.
Appendix T's decision rule is then run over the merged history and its answer
recorded, whichever way it lands.

## Record

**Filed 2026-09-18** with `SA-0107`, as the origin item Appendix T had stood in
for.
