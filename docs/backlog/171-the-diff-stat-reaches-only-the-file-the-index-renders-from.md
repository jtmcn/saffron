---
id: 171
title: The diff stat reaches only the file the index renders from, so no authoritative record holds it
status: open
tier: 2
filed: 2026-09-17
specs: [SA-0124]
prs: []
commits: []
cites: [§5.7, §6]
related: [165, 170]
---

## Problem

§6's own mock of the morning queue renders a diff stat on every line, as
`+180/−22`, and the section names the defect itself: the stat "is stored in no
column at all".

It is computed once, at PACKAGE. `saffron/phases/package.py:792` reads
`added, removed = mirror_ops.diff_stat(mirror, target_head, pushed)`. The pair
lands on `PackageResult` at `saffron/phases/package.py:585-586`, and `_finish`
passes it into the queue row at `:975-976`. `QueueLine` declares both fields at
`saffron/report/index.py:60-61`, and `:175` renders them as
`f"+{line.added}/−{line.removed}"`. The pull request body carries them too,
guarded by `tests/test_report.py:175`.

**It is not discarded, and the plan that called it discarded was wrong.**
`docs/superpowers/plans/2026-08-31-operator-visibility.md` titles its Task 5 "the
diff stat is computed and discarded". Measured 2026-09-17, the stat reaches
`queue.json` and `pr_body.md`. Nothing throws it away.

**What it never reaches is any store the index could be rebuilt from.** No
table has a column for it, `tasks` included. So `queue.json` is
both the store and the only source of these two numbers, and the page cannot be
regenerated from anything but itself. Delete the file and the counts are gone
even though every commit that produced them survives.

This is the narrow half of item 170, and it is the half a cell can land. Item 170
edits `DESIGN.md` and `CONTEXT.md`, so it is by hand. This is a write beside an
existing write.

**It is direction-independent.** Item 170 offers two arms, and both need these
two numbers in whatever the authoritative record turns out to be. Only the
representation follows from that decision.

**Nothing is broken for an operator today**, which is why this is filed rather
than ranked. The stat renders on the page and in the pull request body. It
becomes load-bearing when the index stops being its own source.

## Done looks like

The authoritative record carries the added and removed counts for every task that
produced a diff, written where they are measured rather than derived later. The
index renders them from that record rather than from a store only it writes, so
deleting the rendered page loses nothing.

A task that never packaged carries no counts rather than two zeros.
`PackageResult` defaults both to `0` (`saffron/phases/package.py:585-586`), and a
stored zero is indistinguishable from a measured empty diff. That is §4.1's
warning about a column named for a measurement it cannot make. Item 165 adds rows
for exactly the tasks with no stat to give.

Whether that record is two ledger columns or two fields in a state commit follows
item 170, and this item does not decide it.

## Record

**Filed 2026-09-17**, from an inventory of what one execution can be seen
through. It was the last gap that inventory found with no item behind it.

Carved out of item 170 rather than left inside it, for the reason item 160 was
carved out of item 141: the two halves have different owners. A sentence inside a
by-hand architectural item lands when that architecture lands, and this one needs
a cell and a few lines.
