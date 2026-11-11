---
id: b-6dd608
title: A record push to a test's bare origin fails to write an object, and fails one test per full suite
status: open
tier: 3
filed: 2026-11-11
closed:
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found running `make check` for #1152, 2026-11-11.

Two full suites on the same branch each failed one test, and each test
passed alone. Each failure was a record push to a bare origin in pytest's
temp dir:

```
RecordError("git push failed (1): error: unable to write file ./objects/b2/056759...
  .../pytest-of-jm/pytest-7888/test_a_stack_batchs_layer_and_0/record-origin.git'")
```

- `tests/test_qualify.py::test_a_qualification_fact_reaches_the_origin_at_exit`
  failed in the first suite. A spec writer ran tests during it.
- `tests/test_batch.py::test_a_stack_batchs_layer_and_spec_review_facts_reach_the_origin_at_exit`
  failed in the second suite, which ran alone.

The disk was 47% full. The cause is unknown.

## Done looks like

The failing write is reproduced or explained. No full suite fails a record
push on an unchanged branch.

## Record

- 2026-11-11: filed from #1152's two suites.
