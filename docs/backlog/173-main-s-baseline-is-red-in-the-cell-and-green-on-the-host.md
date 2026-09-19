---
id: 173
title: Main's baseline is red in the cell, so every cell subtracts a failure the host never sees
status: done
closed: 2026-09-18
tier: 1
filed: 2026-09-17
specs: []
prs: [354]
commits: ["cecdb1b"]
cites: [§5.4]
related: []
---

## Problem

Found in the spec loop's run 6, 2026-09-17. All three cells, at `4a6750f` and
at `e980c8b`, printed `baseline: … tests=fail … prose=fail …`.

- `tests` fails one test,
  `tests/test_saffron_gates.py::test_structure_errors_when_its_tool_is_present_but_not_runnable`
  (`~/.saffron/batches/v0/SA-0098/baseline.json`: `1 failed, 2277 passed`). It
  passes on the host (`uv run pytest` on that node id, `1 passed`), and
  `make check` on every review branch was green. Unverified cause: the test
  sets `PATH` to `<stub>:/usr/bin:/bin`, and the cell image puts its toolchain
  in `/opt/venv/bin` (`.saffron/Dockerfile:29`).
- `prose` flags `.claude/agents/spec-reviewer.md` for sentence length and
  semicolons ("this file gained …"), on a baseline with no diff. Unverified
  which base the cell's `prose` compares against.

Baseline subtraction charges neither to the cell, which is right. But until
main is green in a cell, every cell subtracts a regression in that test. The
same holds for a new prose defect in that file. Nothing in the loop reads the baseline
line, so a gate red on `main` reaches nobody.

## Done looks like

The test passes whatever directory the image installs its toolchain in. The
prose gate's base in a cell is found and fixed. The loop's step 2 says to read
the `baseline:` line and take a red gate on `main` to the operator.

## Record

- 2026-09-18: still red in every run-7 cell (`tests` and `prose`, same two failures), at
  `1549f41`, `0188327`, `666d21f` and `9db478d`.
- 2026-09-18: done by hand. The cell image has no `/usr/bin/python3`, so under
  the test's `PATH` the `structure` gate's `exec python3` found nothing and
  printed no contract. Reproduced in `saffron/cell:saffron`. The test now puts a
  `python3` link in its stub directory, and passes in the image and on the host.
  `prose` has no base to find: it fails at base by design, and subtraction
  counts its hits per file (`.saffron/policy.yaml`). The loop's step 2 and
  `GOTCHAS.md` now say so.
