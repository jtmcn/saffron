---
id: b-bf970a
title: Two unreadable-file tests skip on uid 0 in every cell, where the read they test would fail
status: open
tier: 3
filed: 2026-09-29
specs: []
prs: []
commits: []
cites: [§5.1]
related: [94, 106, 173]
---

## Problem

Found closing item 94, 2026-09-29.

Every cell's `tests` baseline reads `2 skipped`, and the host reads none. The
two skips are these tests.

- `tests/test_intake.py:153`, an unreadable spec raising `SpecError`.
- `tests/test_policy.py:109`, an unreadable `policy.yaml` raising `PolicyError`.

Each skips when `os.geteuid() == 0`. No image sets `USER`, so a cell runs as
root and both skip. The premise is "root reads everything", and a production
cell makes it false. Measured in `saffron/cell:saffron`: uid 0 reads a mode
`000` file by default. Under `--cap-drop ALL` the same read raises
`PermissionError`. Every cell starts with `--cap-drop ALL`
(`saffron/cell/runtime.py`, §5.1).

So a probe that breaks either error path survives in a cell and dies on the
host. No `survived` verdict so far touches either path (item 94).

## Done looks like

Each test skips only when the read succeeds. It chmods the file `000`, tries
to open it, and skips if the open works. A cell then runs both, and the
host still runs both. The baseline reads `0 skipped` in a cell started the
way production starts one.

A non-root `USER` in the image would also close it. That changes what the
agent can write under `/work`, so it is the larger change.

## Record

- 2026-09-29: filed from closing item 94.
