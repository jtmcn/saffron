---
id: b-7e69d0
title: The host probes no wrong version a spec lists, so the seats kill 20 to 70 mutants the cell never ran
status: open
tier: 1
filed: 2026-09-28
closed:
specs: [SA-0187, SA-0190]
prs: []
commits: []
cites: [§5.4.1, §5.5]
related: [b-2750d5, b-2dea1c, b-9ed36d]
---

## Problem

Found in the spec loop's run 20, 2026-09-28. The operator ranked it first.

In the cell, `witness` runs each criterion's declared mutant. A criterion probe
session names one more edit from the claim alone (`saffron/phases/review.py:376`).
It never sees the spec body. Many specs list the wrong versions each witness
must kill, and nothing in the cell applies them.

The PR seats ran 20 to 70 probes a pull request, mostly from those lists. They
found witness blockers the critic passed on #560 (1), #561 (2), #564 (4), #565
(1) and #566 (4). On #564 the critic's two criterion probes were the declared
mutants.

## Done looks like

A spec's wrong versions are declared per criterion in a form the host reads.
After GATE the host applies each in a Gate-only cell and runs that criterion's
witness. A survivor is a blocker for REBUT, like a surviving criterion probe.

## Record

- 2026-09-28: filed from the spec loop's run 20.
