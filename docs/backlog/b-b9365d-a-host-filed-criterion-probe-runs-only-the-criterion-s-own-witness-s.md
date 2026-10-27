---
id: b-b9365d
title: "A host-filed criterion probe runs only the criterion's own witness, so a preserves witness that never runs the mutated file files a false blocker"
status: done
tier: 2
filed: 2026-10-25
closed: 2026-10-27
specs: [SA-0322]
prs: [978]
commits: []
cites: [§5.5]
related: [b-a68b24]
---

## Problem

Found in the spec loop's run 48.

`SA-0313`'s REVIEW filed an adequacy blocker at `saffron/cli.py:2884`. The
host applied a wrong version to `cli.py` and ran only criterion 7's
`preserves` witness, which lives in `tests/test_reconcile.py` and never
calls `_adopt`. The implementer argued it. The delegate re-ran the same
edit against `tests/test_cli.py -k adopt`, and three assertions failed.

`SA-0316`'s two host-filed blockers were real, and REBUT fixed both.

## Done looks like

A host-filed probe runs the tests that reach the mutated file, or says
that the criterion's witness never imports it.

## Record

- 2026-10-25: filed from the spec loop's run 48.
- 2026-10-27: done by `SA-0322` in #978, from the spec loop's run 49.
