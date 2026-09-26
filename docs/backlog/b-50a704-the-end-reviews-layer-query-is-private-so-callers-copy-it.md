---
id: b-50a704
title: The end review's layer query and Saffron's root path are private, so callers copy them or import a private name
status: open
tier: 3
filed: 2026-09-26
specs: []
prs: []
commits: []
cites: [§2.1]
related: [b-792ab2]
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

- A public `Ledger.stack_layers(batch_key)`, or a public name in `end_review`.
- One public Saffron root and one cell network name, each imported.

## Record

- 2026-09-26: filed from the spec loop's run 18 (stack #531).
