---
id: b-89ec93
title: The `size` gate counts physical lines, so a cell near its ceiling packs code onto long lines to pass
status: open
tier: 1
filed: 2026-09-21
specs: [SA-0128]
prs: []
commits: []
cites: [§5.4]
related: [40, b-408cf5]
---

## Problem

`size` counts changed physical lines (`saffron/gates/core/size.py:36`). A line
break inside a string costs a line, and joining two lines saves one. So a cell
near its ceiling can pass by reformatting, and nothing else changes.

`SA-0117` did this in the spec loop's run 12 (#418). Its attempt 2 failed `size`
at `elevated`, where the gate blocks. Attempt 3 passed at 979 of 1000. Its SQL
in `saffron/ledger.py` sits on single lines up to 193 characters. The rest of
that file writes SQL as triple-quoted strings over several lines. Base had one
line over 88 characters, and head has twelve.

No gate objects. Ruff ignores `E501` (`pyproject.toml:85`), and the formatter
cannot wrap a string. Restoring the file's style would take the diff past 1000.
Both review seats flagged it, and the operator accepted it for now and asked
for a fix soon.

The measure rewards the wrong thing. A cell that writes readable SQL pays for
it in `size`, and one that packs it does not.

## Done looks like

`size` measures a diff in a unit that line wrapping does not move. One option
is tokens or logical lines. Another is counting after a normalising pass that
joins a string split across lines. Reformatting a file changes its count by
nothing. The ceilings in `size.py` are re-measured in the new unit against
past cells.

## Record

- 2026-09-21: filed from the spec loop's run 12 (#418). The operator suggested
  a line size that depends on content.
