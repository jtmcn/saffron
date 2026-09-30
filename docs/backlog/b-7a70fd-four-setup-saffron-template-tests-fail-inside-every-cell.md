---
id: b-7a70fd
title: Four setup-saffron template tests fail inside every cell and pass on the host
status: open
tier: 2
filed: 2026-09-29
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

The cause is not diagnosed. The operator chose to file it. The helper
`_onboarded_from_templates` sets `PATH` to a tmp `bin`, the directory of
`sys.executable`, `/usr/bin` and `/bin` (`tests/test_setup_saffron.py:209`).
The `gate` and `tests` templates start `#!/usr/bin/env python3`.

## Done looks like

The cause is found and written here. All four pass in a cell started the way
production starts one. A cell's baseline then reads `tests` without them.

## Record

- 2026-09-29: filed from the spec loop's run 22.
