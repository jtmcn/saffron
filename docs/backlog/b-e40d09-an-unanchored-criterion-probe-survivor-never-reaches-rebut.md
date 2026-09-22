---
id: b-e40d09
title: A criterion-probe survivor that does not anchor never reaches REBUT, so a claim the host found unguarded blocks nothing
status: open
tier: 3
filed: 2026-09-22
specs: []
prs: []
commits: []
cites: [§5.4.1, §5.5]
related: [b-b431c1, b-2750d5]
---

## Problem

Found reviewing ADR 4, 2026-09-22.

The host files a surviving criterion probe as an adequacy finding, then passes
it through `anchor` like a lens finding (`saffron/cell/session.py`,
`_apply_criterion_probes`). A survivor whose line is not in a diff hunk, and
names no identifier the diff changed, is recorded with `anchored = false`. It
never reaches REBUT.

Anchoring exists to drop a lens's hallucinated or off-diff finding. A survivor
is neither. The host ran the edit and watched the witness stay green. A
`preserves` criterion is probed too, and its edit is the likeliest to target
code the diff did not touch. No run has shown one drop yet. That is reasoned,
not measured.

The ledger then counts it against the adequacy lens's drop rate, which
b-b431c1 owns.

## Done looks like

A surviving criterion probe reaches the operator whether or not it anchors,
or §5.4.1 states why an unanchored one is dropped. A witness covers the
chosen behaviour.

## Record

- 2026-09-22: filed from ADR 4's review. ADR 4's principle 28 records it.
