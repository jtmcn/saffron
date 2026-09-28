---
id: b-30bbd7
title: The library's hour, 3600, has no name, and the 60-turn default is spelled twice
status: open
tier: 3
filed: 2026-09-28
closed:
specs: []
prs: []
commits: []
cites: [§4.3]
related: [b-bf0c91, 18]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, by #560's Standards seat
(`SA-0184`).

- The one-hour transport ceiling is a bare `3600` in
  `saffron/cell/runtime.py:486` and `saffron/phases/implement.py:216`, at
  `18ecd9ef`. `WALL_CAP_S = 3600.0` restates it a third time
  (`saffron/cell/session.py:68`). `runtime.py` was forbidden to `SA-0184`.
- `CellSpec` spells `max_turns: int = 60` (`saffron/cell/session.py:279`).
  `intake.Spec` spells `Field(default=60, gt=0)` on its own
  (`saffron/intake.py:167`). The first version of criterion 4's witness passed
  vacuously because the two agree by coincidence.

## Done looks like

The hour has one name in `runtime.py`, and `implement.py` and `WALL_CAP_S` read
it. One `max_turns` default derives from the other, and a test changes one and
reads the change in both.

## Record

- 2026-09-28: filed from the spec loop's run 20.
