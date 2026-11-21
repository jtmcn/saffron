---
id: 20
title: No cell-marked test exercises the `shacl` gate
status: done
closed: 2026-11-21
tier: 3
specs: []
prs: [46]
commits: []
cites: []
related: [19]
---

## Problem

**Status:** open. Same PR.

`tests/test_saffron_gates.py` runs the gate through a bare `subprocess.run` that
inherits pytest's environment, so it finds `pyshacl` in Saffron's own venv.
Through the real `LocalExecutor` it reports `error: pyshacl not on PATH`, because
`_gate_env` strips that venv — which is correct and is what `tests` already does,
since gates target the cell. The in-cell evidence is one line in
`.saffron/Dockerfile` asserting `pyshacl --version` at build time.

That is the same class of gap Appendix I is about: every mechanism reported green
and the thing under test was somewhere else. It is thinner here — the build-time
assertion is real, and `python3` and the `pyshacl` console script both resolve to
`/opt/venv` — but nothing proves the gate produces a contract-shaped result from
inside a cell.

## Done looks like

a `@pytest.mark.cell` test that starts a cell the way
production does and runs `shacl` through `CellExecutor`, asserting `pass` and a
`tool` obtained in the cell rather than on the host.

## Record

- 2026-11-21: closed. `tests/test_shacl_cell.py` starts a cell from the repo's
  own image, runs `shacl` through `CellExecutor` and asserts `pass` on a
  conforming graph and `fail` on one missing a required property. Its `tool`
  is the cell's own `pyshacl --version`. A gate edited to pass everything
  fails it.
