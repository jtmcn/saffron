---
id: b-60f950
title: 'No vocabulary owns the run statuses `SA-0419` closes, so `ABORTED` means whatever its writer needed'
status: done
tier: 3
outside_cell: true
filed: 2026-11-20
specs: []
prs: [1297]
closed: 2026-11-22
commits: []
cites: [§4.1]
related: [b-7431a2, 164]
---

## Problem

Found 2026-11-20, writing `SA-0419` for b-7431a2.

`SA-0419` gives `runs.status` a closed set. A row is minted `RUNNING`, and
`finish_run` writes `COMPLETE` or `ABORTED` (`saffron/ledger.py:1364-1366`,
`saffron/cell/session.py:4163`). None of the three sits in `CONTEXT.md` or
in `ontology/factory.ttl`. The Standards seat on #811 (`SA-0245`) found the
same gap for `ABORTED` on 2026-10-11.

The preflight outcomes beside it are owned. `factory:PreflightOutcome`
declares `PASSED` and `FAILED` (`ontology/factory.ttl:188-189`).
`tests/ontology/test_vocabulary_agrees_with_code.py:161-166` holds the
ledger's tuple to that class. The run statuses have neither half.

`SA-0419` forbids `ontology/**`, `CONTEXT.md` and `tests/ontology/**`. A cell
cannot land the entry, since `CONTEXT.md` is `protected` and is rendered
from the vocabulary. So the entry lands by hand.

`ABORTED` is the term that needs care. Item 164 measured that it folds a
machine that never started together with Ctrl-C and every other exception
in a long task (`saffron/cell/session.py:4147-4150`). The entry says so,
and defines no narrower word than the code writes.

## Done looks like

- `ontology/factory.ttl` declares a class for the run statuses, with
  `RUNNING`, `COMPLETE` and `ABORTED` as its members.
- `uv run python -m ontology.render` writes the `CONTEXT.md` entry.
- A test in `tests/ontology/test_vocabulary_agrees_with_code.py` holds the
  class to the statuses `saffron/ledger.py` declares, in the shape of the
  preflight test.
- `DESIGN.md` §4.1 names the set beside its sentence on `runs.preflight`.

Land it after `SA-0419` merges, since the test reads the set it declares.

## Record

- 2026-11-20: filed beside `SA-0419`.
- 2026-11-22: done by hand. `factory:RunStatus` declares the three statuses,
  with a shape, a negative fixture and a `CONTEXT.md` entry. A test holds it to
  the ledger's tuple, and `DESIGN.md` §4.1 names the set.
