---
id: b-1c7019
title: The guard against a column nothing reads asserts two names and claims the whole schema
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [18, 97]
---

## Problem

Found by the spec loop's Standards and Spec seats reviewing #381, 2026-09-19,
and verified by the delegate.

`tests/test_ledger.py:802-826` is named
`test_the_schema_adds_no_column_that_nothing_reads` and its docstring calls
itself "§4.2.1's two explicit cuts". Its assertions are that `batches` has no
`concurrency` and `tasks` no `priority`. It reaches nothing else.

`DESIGN.md:408` is the rule it is named for: "A column written at scan and read
by nobody would be item 18's pattern wearing a schema instead of a dataclass".
#381 adds exactly such a column, `tasks.merged_head_sha`, written by
`reconcile`'s scan and read by no production code. The test passed without
noticing. `SA-0111` knew, and routed the fact to the pull request body, where
it is prose that outlives nothing.

A rename is barred while a spec is in flight: `census` compares collected test
names between base and head and reads a rename as a removal.

## Done looks like

Either the name narrows to what it asserts, or the test grows into the guard
its name claims: `PRAGMA table_info(tasks)` against a declared allowlist, with
a named carve-out per column that is written and not yet read. The next such
column then argues for itself in the tree rather than in a body.

## Record

- 2026-09-19: filed from the spec loop's run 10 (#381). The column it failed to
  notice is `SA-0111`'s, and the carve-out for it is argued in #381's body.
