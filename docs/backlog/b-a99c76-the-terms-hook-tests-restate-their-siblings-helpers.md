---
id: b-a99c76
title: "`tests/test_terms_hook.py` restates four helpers and a reason from its two sibling hook tests"
status: open
tier: 3
filed: 2026-10-09
specs: []
prs: [790]
commits: []
cites: []
related: [b-262df1]
---

## Problem

Found by #790's Standards seat in the spec loop's run 32.

`_hook_config`, `_git_in`, `_prose` and `_tracked` in
`tests/test_terms_hook.py` restate helpers in `tests/test_dead_gate.py` and
`tests/test_prose_gate.py`. The spec directed it, so the seat left it.

The three files also copied one module docstring reason. It says the `revert`
gate re-runs a new witness with its script deleted. That held only for the
pull request that added each script. #790's review removed it from
`tests/test_terms_hook.py`. It is still in `tests/test_prose_gate.py:3-4` and
`tests/test_dead_gate.py:3-4`, where it is now stale.

## Done looks like

The hook tests import one shared helper module, and no module docstring
carries the stale `revert` reason.

## Record

- 2026-10-09: filed from the spec loop's run 32.
