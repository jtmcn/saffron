---
id: b-8fb227
title: The `size` ceiling lookup is written out in three modules and four tests, with no `ceiling_for` to give it one source
status: open
tier: 3
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-a90136]
---

## Problem

Found in the review of #502 (`SA-0129`), 2026-09-24.

`_CEILINGS.get(spec_type, _DEFAULT_CEILING)` is spelled out in
`saffron/gates/core/size.py:259`, `saffron/agents/artifacts.py:314` and
`.claude/skills/run-saffron-spec-loop/driver.py:1967`. Four tests repeat it:
`tests/test_spec_size_estimate.py:60` and `:146`,
`tests/test_session.py:338` and `tests/test_artifacts.py:257`.

A change to the default, or a new fallback, has seven places to land.

## Done looks like

`size.py` exports `ceiling_for(spec_type)`, and every caller reads it.

## Record

- 2026-09-25: filed from the spec loop's run 16.
