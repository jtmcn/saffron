---
id: b-6d43da
title: A fixture declares no recorded lens set, so `calibrate` cannot tell a truncated recorded run from an older one
status: partial
tier: 3
filed: 2026-09-29
closed:
specs: []
prs: [1075]
commits: []
cites: []
related: [b-abeb74, b-d5d290, b-cd4de2]
---

## Problem

Found in the spec loop's run 21, 2026-09-29, by both seats on #579
(`SA-0189`).

`SA-0189` lets `calibrate` accept a recorded run made before a lens existed.
A fixture never says which lenses its recorded run held. So an older
three-lens run and a `recorded-findings.json` that lost a lens read the same.
At #579's head an adequacy-only recorded run calibrates to `None` and passes.
Review added a guard for an empty recorded run. The partial case needs a field
under `docs/**`, which the cell could not write.

Harness prose also uses bare "run" and "pass" (`harness/lens_scoring.py:19`,
`harness/corpus.py:5`). `CONTEXT.md` lists them under `_Avoid_` for Scoring
run and Scoring pass. The `terms` gate does not read those lists.

## Done looks like

Each `docs/evidence/fixtures/*/fixture.toml` declares `recorded_lenses`.
`calibrate` refuses a recorded run whose lens set differs from it. A test drives
an adequacy-only run against a three-lens declaration and reads the refusal.
The harness says Scoring run and Scoring pass, and `terms` covers both.

## Record

- 2026-09-29: filed from the spec loop's run 21.
- 2026-11-08: partial, by hand. All 13 shipped fixtures declare `recorded_lenses`, and `calibrate` refuses a recorded run that holds another set. `harness/corpus.py`'s module docstring says scoring run and scoring pass. Three parts are left. `load_fixture` still reads a fixture with no `recorded_lenses`, because `tests/test_lens_scoring.py` builds such fixtures and a queued spec holds that file. The recovery script does not write the field. The `terms` gate does not cover bare "run" or "pass", which a phrase map cannot tell from the qualified terms (b-d5d290).
