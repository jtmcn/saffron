---
id: 156
title: "`session.py`, its tests and `suite.py` still use words `CONTEXT.md` tells them to avoid"
status: open
tier: 3
filed: 2026-09-16
by_hand: false
specs: []
prs: []
commits: []
cites: []
related: [142]
---

## Problem

**Tier 3.** Found by the Standards seats on #303, #305 and #307, 2026-09-16.

`CONTEXT.md` defines **Gate-only cell** with "_Avoid_: 'the gate cell'", and
says **Run** is a repo's slice of a batch, never a gate suite and never a task.
The code predating this loop does not follow either:

- `saffron/cell/session.py` says "gate cell" in comments and in one message an
  operator reads on the exit-2 path: "the exported patch did not apply in the
  gate cell". `tests/test_session.py` says it a dozen times, including in test
  names that specs cite as witnesses.
- `session.py` says "a SIGKILLed run" where it means a task.
- `saffron/gates/suite.py` names a gate suite's results `SuiteRun`, and the
  comparison's field `run`.

Each seat marked the new lines in its own diff and left these, because the
message is pinned by `tests/fixtures/watch-golden.txt`, `suite.py` is under
`saffron/gates/**`, and a renamed test breaks every spec that names it.

## Done looks like

The message and comments say "Gate-only cell", "run" means a run everywhere in
`saffron/`, and `SuiteRun` has a name `CONTEXT.md` allows — with the golden
fixture and any witness ids renamed in the same change.

## Record

**Filed 2026-09-16** from the spec loop's run 5 (stack #308).
