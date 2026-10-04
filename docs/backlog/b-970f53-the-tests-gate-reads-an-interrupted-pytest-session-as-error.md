---
id: b-970f53
title: The `tests` gate reads an interrupted pytest session as `error`, so a test that lets `KeyboardInterrupt` escape charges wrong code to the gate
status: open
tier: 2
filed: 2026-10-03
specs: [SA-0197]
prs: [657]
commits: []
cites: [§5.4]
related: [96]
---

## Problem

Found at step 1b of the spec loop's run 27, reviewing `SA-0197`.

A test that raises `KeyboardInterrupt` stops pytest's whole session. Measured
on 2026-10-03, pytest exits 2. It prints no `FAILED` line, and its trailer reads
`test_kbi.py:9: KeyboardInterrupt`. Every test after it goes unrun.

`.saffron/gates/tests.py` parses failures with
`^(\S+?):(\d+): (\w+): (.*)$`. The trailer has no fourth field, so nothing
matches, and no `FAILED` line exists to fall back on. The gate then emits
`error` with "pytest exited 2 with no parsed failures".

So a cell whose code lets Ctrl-C escape a call under test gets `error`, which
means the gate broke and is charged to nobody. The code is what is wrong. That
collapses `error` and `fail`, which `CLAUDE.md` forbids. `SA-0197`'s witness
now catches the interrupt itself, but no other test is protected.

## Done looks like

An interrupted session whose trailer names a test file and line reads as
`fail`, with that test as the failure. A test in `tests/` drives a fixture
that raises `KeyboardInterrupt` and asserts the gate's status.

## Record

- 2026-10-03: filed from the spec loop's run 27.
