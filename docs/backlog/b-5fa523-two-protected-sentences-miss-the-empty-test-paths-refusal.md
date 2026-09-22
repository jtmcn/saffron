---
id: b-5fa523
title: Two protected sentences say every probe off a test path reaches a cell, and `SA-0119` refuses them all on an empty `test_paths`
status: open
tier: 3
filed: 2026-09-21
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.5.1]
related: [b-461729]
---

## Problem

Found by the first review of `SA-0119`, 2026-09-21. Once `SA-0119` lands, a
repo that declares no `test_paths` has every probe refused `unproven` before
any cell starts. Two protected sentences still say the rest reach a cell.

- `DESIGN.md:1071` reads "A probe that edits a declared test path is
  `unproven` and never applied. For the rest, the host runs the repo's `tests`
  gate over the probed tree."
- `CONTEXT.md:355`, the *vacuity probe* entry, reads "in a gate-only cell,
  unless the probe edits a declared test path."

Both files are `protected`, so no cell can edit them.

## Done looks like

Both sentences name the empty `test_paths` refusal beside the test-path one.
`CONTEXT.md` changes through `ontology/factory.ttl` if the entry is generated
from it.

## Record

- 2026-09-21: filed by hand with `SA-0119`. It waits on that spec's merge.
