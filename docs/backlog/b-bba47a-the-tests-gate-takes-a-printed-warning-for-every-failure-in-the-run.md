---
id: b-bba47a
title: The `tests` gate takes an unindented warning a test prints for every failure in the run, and two comments say that is its common path
status: open
tier: 2
filed: 2026-10-15
specs: [SA-0273]
prs: [881]
commits: []
cites: [§5.4]
related: [b-4a63b7]
---

## Problem

Found in the spec loop's run 40, reviewing #881.

`.saffron/gates/tests.py` parses failures with
`^(\S+?):(\d+): (\w+): (.*)$`, and reads `FAILED` lines only when that finds
nothing. A failing test whose captured output holds an unindented
`file:line: Type: msg` line matches it. A subprocess's warning is one. Every
failure in the run then carries that type as its `code`, and no node id
survives.

Measured by the Spec seat: two failing tests, one of which ran a subprocess
that printed a `UserWarning`, gave `[('<string>', 'UserWarning', 1)]` in place
of both node ids. A plain assert, a raise and a warning in the test's own
process gave node ids.

`revert`, `criteria` and the probe all read node ids from `code`. When the
regex fires, a probe reads `unproven` and `revert` degrades to `skip`.

The comment at `saffron/gates/core/revert.py:309-313` says the gate keys
`code` on the exception type "on its common path", as a measured reason. The
delegate and the Spec seat each measured the opposite. `criteria._side`
carries the same claim.

## Done looks like

The gate keys `failures[].code` on node ids from `FAILED` and `ERROR` lines
whatever else the output holds. The two comments say what was measured.

## Record

- 2026-10-15: filed from the spec loop's run 40.
