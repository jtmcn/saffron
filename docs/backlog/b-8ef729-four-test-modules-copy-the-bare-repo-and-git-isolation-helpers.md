---
id: b-8ef729
title: "Four test modules each define `_bare`, and four define a git isolation helper, where one shared helper would do"
status: superseded
tier: 3
filed: 2026-10-19
closed: 2026-11-07
specs: []
prs: [1029]
commits: []
cites: []
related: [170, b-25c0f5]
superseded_by: b-25c0f5
---

## Problem

Found by the Standards seats on #907 and #909, in the spec loop's run 44.

`_bare` is defined in `tests/test_cli.py:2014`, `tests/test_record_migrate.py:76`,
`tests/test_record_routed.py:11` and `tests/test_task_record.py:24`.
`_isolated_git` or `_isolate_git` is defined in `tests/test_record_routed.py:28`,
`tests/test_task_record.py:31`, `tests/test_setup_saffron.py:60` and
`tests/test_finish.py:31`. Review of `SA-0281` (#909) removed a fifth copy
in `tests/test_engine.py`, which now imports `tests/test_finish.py`'s. A fix
to how a test isolates git otherwise lands in one copy.

## Done looks like

One helper module under `tests/` holds each, and every test imports it.

## Record

- 2026-10-19: filed from the spec loop's run 44.
- 2026-11-07: partial in grooming. `tests/conftest.py` now holds `bare_repo`, one shared bare-repo helper (fecc61f0, merged in #1029). Five test modules import it. The four `_bare` copies remain, at `tests/test_cli.py:3581`, `tests/test_record_routed.py:13`, `tests/test_record_migrate.py:77` and `tests/test_task_record.py:24`. b-25c0f5 asks for those four too. The four git isolation helpers remain, and no shared one exists.
- 2026-11-07: superseded in grooming by b-25c0f5, on the operator's ruling of 2026-11-07. Both ask for the four `_bare` copies to go. b-25c0f5 takes this item's other half, the four git isolation helpers, into its Record.
