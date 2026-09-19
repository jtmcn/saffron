---
id: b-4589be
title: Six spec-loop driver defects that run 8 worked around by hand
status: open
tier: 2
filed: 2026-09-19
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [157, 158, b-36b551, b-65e7e2]
---

## Problem

Found in the spec loop's run 8, 2026-09-18 and 2026-09-19. By hand:
`.claude/skills/run-saffron-spec-loop/driver.py` is the skill's, not a cell's.

- **`probe` shares its verdict line with uv's warning.** `cmd_probe` merges
  stdout and stderr and prints `verdict: <last line>` (`driver.py:1162` and
  `:1174`). Under `uv run` with another `VIRTUAL_ENV` set, the last line is uv's
  warning. The delegate filtered it with `grep -v VIRTUAL_ENV` and hid a
  `survived` on #351.
- **`history` reads the spec in the checkout it runs from** (`driver.py:1641`).
  A reviewer running it from `main` saw `SA-0102`'s old ceilings, 90 turns and
  $14, for a spec edited on a branch. Item 157 is the same defect for
  `status`, `next` and `snapshot`.
- **`next` names a child too early.** It named `SA-0102` before its review at
  `origin/saffron/SA-0101` was done. The delegate ran `SA-0106` first by hand.
- **`record` settles a wall-cut `NOT_IMPLEMENTED`.** `cmd_record` treats every
  `DONE_STATES` member as decided (`driver.py:1072`). `SA-0107`'s first cell was
  cut by the wall with nothing committed, and `record` settled the spec and held
  `SA-0108`. Item b-36b551 is the core half.
- **`hold` takes one spec id** (`driver.py:1180`). Every step 1b round edited
  all five specs, so each round took five commands.
- **The watch pattern still misses the CLI's error line** (item 158). Users add
  `Error` by hand, and it matches agent lines too.

## Done looks like

`probe` prints its verdict on its own line, with uv's output apart from it.
`history --spec <path>` reads the spec from a path or ref. `next` skips a child
with no recorded parent-branch review. `record` calls a `NOT_IMPLEMENTED` with
no commits and a bound in its terminal a halt. `hold` takes several ids or
`--all`. Item 158 closes.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
