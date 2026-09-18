---
id: b-d6bff7
title: A batch scans its queue once, so a child waits a night for a parent that packaged hours earlier
status: open
tier: 3
filed: 2026-09-17
specs: [SA-0106]
prs: []
commits: []
cites: [§4.2, §4.2.1]
related: [67, 70, 177]
---

## Problem

Found 2026-09-17, asking why the spec loop runs attended cells rather than
`saffron batch`.

`saffron batch` resolves its queue once, before the first task
(`saffron/cli.py:766`), and `_drive` loops over that fixed list
(`saffron/batch.py:160`). A spec whose `depends_on` parent has no task yet is
refused in that scan: "has no task at its current spec_sha"
(`saffron/scheduler.py:595`). If the parent then packages `READY_FOR_REVIEW`
during the night, nothing rescans, so the child waits for the next night. A scan
at that point would admit it (`DEPENDENCY_WAITING_STATES`,
`saffron/scheduler.py:91`) and stack it on the parent's branch.

§4.2's footnote to the dependency gate names a 3-node chain taking three nights
as the cost stacking removes. With one scan per night, it still takes three.

## Done looks like

`saffron batch` rescans the queue after each task, against the same pinned base,
and starts the first spec not yet attempted that night. A child whose parent
packaged earlier in the night runs the same night, cut from the parent's branch.

The spec loop still runs attended cells, because it pushes review commits to a
parent before its child is cut (`.claude/skills/run-saffron-spec-loop/GOTCHAS.md`).
Once this lands, update by hand the prose it makes false, none of which a cell
can edit:

- The first half of that `GOTCHAS.md` section's reason.
- `DESIGN.md:385`: nothing is in flight at a scan.
- `DESIGN.md:400`: "sorted once in memory".
- `DESIGN.md:404`: the next scan stamps a task left in flight.
- `DESIGN.md:408`: priority is "read exactly once, at scan".
- `saffron/task.py:130-133`: a grandchild out of reach by design.

## Record

**Filed 2026-09-17** with `SA-0106`.
