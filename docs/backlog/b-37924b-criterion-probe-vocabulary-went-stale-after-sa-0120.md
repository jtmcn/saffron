---
id: b-37924b
title: '`witness_gate`''s summaries call a criterion probe a mutant, and two protected files say no gate applies one'
status: open
tier: 3
filed: 2026-09-22
by_hand: true
specs: [SA-0120]
prs: [434]
commits: []
cites: [§5.4.1]
related: [b-2750d5, b-0c1d69]
---

## Problem

Found reviewing `SA-0120` (#434), 2026-09-22.

- `witness_gate`'s summaries say "mutant"
  (`saffron/gates/core/witness.py:213,237,252-253,280,290`). `SA-0120` records
  that summary for a criterion probe, and `CONTEXT.md:371` avoids "mutant" for
  one.
- `Finding.probe`'s docstring (`saffron/agents/findings.py`) and `CONTEXT.md`'s
  **Vacuity probe** entry do not say that a host-filed criterion-probe survivor
  is filed under `adequacy`.
- `DESIGN.md:989` and `CONTEXT.md:369-370` still say "No gate applies one yet
  (backlog item b-2750d5)". The host applies one now.

## Done looks like

The summary names a criterion probe as one, and each sentence says what the
host does today. By hand, since `DESIGN.md` and `CONTEXT.md` are protected.

## Record

- 2026-09-22: filed from the spec loop's run 13.
