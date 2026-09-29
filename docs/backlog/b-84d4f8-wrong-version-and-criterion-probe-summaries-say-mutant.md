---
id: b-84d4f8
title: Wrong-version and criterion-probe summaries say "mutant", and wrong versions run under the criterion-probe helper's name
status: open
tier: 3
filed: 2026-09-29
closed:
specs: []
prs: []
commits: []
cites: [§5.4.1, §5.5]
related: [b-7e69d0, b-37924b, b-a5d4af]
---

## Problem

Found in the spec loop's run 21, 2026-09-29, by the Standards seat on #576
(`SA-0190`).

`wrong-versions.json` and `criterion-probes.json` carry summaries that
`witness_gate` writes (`saffron/gates/core/witness.py:228-296`). One reads
"1 of 1 witness(es) survived their own mutant". `CONTEXT.md`
lists "mutant" under `_Avoid_` for a criterion probe (`:397`) and for a wrong
version (`:409`).

`_apply_criterion_probes` (`saffron/cell/session.py:1561`) now applies wrong
versions too, under the criterion-probe name and outcome helper. The file it
writes is `wrong-versions.json` (`:2815`).

## Done looks like

`witness_gate` takes the name of the edit it applies, and each file's
summaries use that name. The helper's name covers both kinds of edit, or each
kind gets its own. A test reads a wrong-version summary and finds no
"mutant".

## Record

- 2026-09-29: filed from the spec loop's run 21.
