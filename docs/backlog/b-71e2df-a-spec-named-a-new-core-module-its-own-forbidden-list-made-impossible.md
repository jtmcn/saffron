---
id: b-71e2df
title: A spec named a new module under `saffron/gates/core/` that its own `forbidden` list made impossible, and no review or check saw it
status: partial
tier: 2
filed: 2026-10-19
specs: [SA-0410]
prs: [1260]
commits: []
cites: [§3.2, §5.4]
related: [b-281f0a]
---

## Problem

Found by the Spec seat on #908, in the spec loop's run 44.

`SA-0280` asked for `saffron/gates/core/constant_mutants.py` and listed it in
`touches`. It also forbade `ontology/**` and `tests/ontology/**`.
`tests/ontology/test_vocabulary_agrees_with_code.py` reads every module under
`saffron/gates/core/` as a core gate, which needs a vocabulary entry. So the
module could not be added without an edit the spec forbade. The cell put the
code in `witness.py` instead, and the file in `touches` was never created.

Neither the spec writer, the spec review nor the batch's spec review caught
it. No gate reports a `touches` entry the diff never created.

## Done looks like

The spec review, or a check before a cell, refuses a new module under
`saffron/gates/core/` that is not a gate. A diff that leaves a new file in
`touches` uncreated is reported to the reviewer.

## Record

- 2026-10-19: filed from the spec loop's run 44.
- 2026-11-17: `SA-0410` queued for the second arm. A passing `scope` result
  at head names each literal `touches` entry absent at base that the diff
  never created. It is reported, never failed. The item stays partial on the
  first arm, a refusal of a new module under `saffron/gates/core/` that is not
  a gate. That is this repo's own rule, read by
  `tests/ontology/test_vocabulary_agrees_with_code.py`, so core cannot hold it
  (§2.1).
- 2026-11-18: the second arm landed in #1260 (`SA-0410`). The review added a
  witness for a `touches` path that starts with `:`. The first arm stays
  open as recorded above.
