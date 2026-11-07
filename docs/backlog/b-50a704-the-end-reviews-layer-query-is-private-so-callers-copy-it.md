---
id: b-50a704
title: "`saffron-cells` is a bare literal in `session.py` and `end_review.py`, where one public name would do"
status: open
tier: 3
filed: 2026-09-26
specs: []
prs: []
commits: []
cites: [§2.1]
related: [b-792ab2, b-115f9b, b-65dbbd]
---

## Problem

Found in the spec loop's run 18, 2026-09-26, reviewing #528 and #529.

- `SA-0154` restated `end_review._BATCH_LAYERS` as `_BATCH_LAYER_KEYS`, and
  `SA-0157` restated it in `cli.py`. Review replaced both with the private
  name. The two seats disagreed on whether a copy or a private import is worse.
- `_SAFFRON_ROOT` has copies in `saffron/cell/session.py` and
  `saffron/repos/image.py`. `cli.py` now imports the private one.
- `"saffron-cells"` is a bare literal in `session.py` and `end_review.py`.
- Each module reads `ledger._db` for the layers. `Ledger` has no method for it.

## Done looks like

One public cell network name, which `session.py` and `end_review.py` both import.

## Record

- 2026-09-26: filed from the spec loop's run 18 (stack #531).
- 2026-11-07: trimmed in grooming on the operator's ruling of 2026-11-07 to its one unique part. b-115f9b holds the layer query, and `Ledger.stack_layers` now exists. b-65dbbd holds the two copies of `_SAFFRON_ROOT`.
