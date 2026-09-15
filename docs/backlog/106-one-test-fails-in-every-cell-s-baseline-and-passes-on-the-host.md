---
id: 106
title: One test fails in every cell's baseline and passes on the host
status: open
tier: 3
specs: [SA-0062, SA-0066]
prs: []
commits: []
cites: []
related: []
---

## Problem

**Tier 3.** Measured running stack #222, 2026-09-12.
`tests/test_saffron_gates.py::test_structure_errors_when_its_tool_is_present_but_not_runnable`
is the one failure in every cell baseline the batch took — `SA-0066`'s
`baseline.json` records 1 failed of 1778 collected, and every cell's
`baseline:` line read `tests=fail` — and passes on the host in 0.26s. The
2026-09-11 lens-corpus probes record it too
(`docs/evidence/passes/2026-09-11-lens-corpus-spread/SA-0062/probes.json`). The
test puts an `ast-grep` stub of mode `0644` first on `PATH` and expects the
`structure` gate to report `error`.

Baseline subtraction cancels it, so it blocks nothing. What it costs: every
cell's `tests` baseline is `fail`, and a spec that changes the `structure` gate
would find its own witness already failing. The cause is not measured. No image
under `images/` or `.saffron/Dockerfile` sets `USER`, so cells run as root — but
root still cannot execute a file with no execute bit, so that alone does not
explain it.

**Done looks like** the failure reproduced in a cell and its cause named, then
the test or the cell fixed — not the test skipped in a cell, which is a `pass`
nobody checked.
