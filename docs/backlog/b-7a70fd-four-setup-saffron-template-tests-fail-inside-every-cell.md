---
id: b-7a70fd
title: Four setup-saffron template tests fail inside every cell and pass on the host
status: done
tier: 2
filed: 2026-09-29
closed: 2026-09-30
specs: []
prs: []
commits: []
cites: []
related: [b-bf970a, 173]
---

## Problem

Found in the spec loop's run 22, 2026-09-29. The tests came from #552.

Four tests in `tests/test_setup_saffron.py` fail in a cell and pass on the
host.

- `test_the_templates_filled_in_pass_the_check`
- `test_the_gate_template_reads_an_unparsed_nonzero_exit_as_error`
- `test_the_tests_template_keys_a_failure_on_its_collected_name`
- `test_the_tests_template_reports_a_name_it_cannot_find`

Every run 22 cell's baseline read `tests=fail` with exactly these four.
Baseline subtraction spares each cell. It also hides the four from every
later cell.

## Cause

Diagnosed 2026-09-30 by running the four in `saffron/cell:saffron` with no
network. Every gate there reported `env: 'python3': No such file or directory`.

The helper `_onboarded_from_templates` set `PATH` to a tmp `bin`, the directory
of `sys.executable`, `/usr/bin` and `/bin`. In a cell that directory is
`/opt/venv/bin`. The runner's `_gate_env` removes `sys.prefix/bin` from a
gate's `PATH` when Saffron runs in a venv. That leaves `/usr/bin:/bin`. The cell
image's only `python3` is `/usr/local/bin/python3`. So the templates'
`#!/usr/bin/env python3` finds nothing. On the host, macOS ships
`/usr/bin/python3`, so the four passed on the system interpreter by accident.

The runner is right, and the test was wrong. The helper now puts the resolved
interpreter's directory on `PATH`, which `_gate_env` keeps.

## Done looks like

The cause is found and written here. All four pass in a cell started the way
production starts one. A cell's baseline then reads `tests` without them.

## Record

- 2026-09-29: filed from the spec loop's run 22.
- 2026-09-30: diagnosed and fixed in the test helper. All 24 tests in the
  file pass inside the cell image.
