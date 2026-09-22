---
id: b-149df3
title: A bound cut with nothing committed ends `ORPHANED` once SA-0126 lands, and the glossary, §4.5 and the spec loop's gotchas still say otherwise
status: open
tier: 1
by_hand: true
filed: 2026-09-22
specs: [SA-0126]
prs: []
commits: []
cites: [§4.2.1, §4.5]
related: [b-36b551, b-cafacd]
---

## Problem

Found 2026-09-22, writing `SA-0126`.

`SA-0126` gives a wall-clock cut the salvage turn a turn-ceiling cut gets.
The first implement turn at a `spec_sha` that either bound cuts with nothing
committed then ends `ORPHANED`, so the next scan re-queues the spec. A second
such cut at the same `spec_sha` ends `NOT_IMPLEMENTED`, so a spec retries
once. A task `ORPHANED` by a kill or by a scan does not count toward that
retry. Five passages no cell can edit become incomplete, and none names the
retry.

- `CONTEXT.md` §6 says each `TerminalEvent` reason ends the task in
  `PLAN_REJECTED` or `NOT_IMPLEMENTED`. The two cut-off reasons now end in
  `ORPHANED` on a first cut.
- `CONTEXT.md` §6 defines `ORPHANED` as a task whose cell was killed or
  crashed. A turn ceiling ends a turn without killing anything.
- `DESIGN.md` §4.5 says the supervisor stamps `ORPHANED` on kill, on crash,
  and on `--until`. It does not name a bound cut with nothing committed.
- `.claude/skills/run-saffron-spec-loop/GOTCHAS.md:57-59` says a cut followed
  by `budget: … no room left to salvage` ends `NOT_IMPLEMENTED`.
- `.claude/skills/run-saffron-spec-loop/GOTCHAS.md:65` lists that same
  `NOT_IMPLEMENTED` as one shape of a cell that halts at a ceiling.

`DESIGN.md` and `CONTEXT.md` are `protected`, and `SA-0126` forbids
`.claude/**`, so the cell changes none of them.

The cap also rests on each cell minting its own task row
(`saffron/cell/session.py:1640`). `DESIGN.md` §4.2.1 says a re-queued spec
resumes its task row (`DESIGN.md:384`), and `saffron/scheduler.py:779-780`
computes which row. Nothing passes that row to a cell yet. The day a re-queue
resumes it, the cap's "an earlier task" excludes the first cut's own row, and
the cap stops firing with no error. The resumption change must re-key the cap.
It must also revisit the rule that every attempt is in `IMPLEMENTING`. A
resumed row that went through REBUT and was then cut ends on an `IMPLEMENTING`
attempt after a `REBUTTING` one. That row is a cut, and the rule misses it.

## Done looks like

The `ORPHANED` entry and the `TerminalEvent` paragraph in `CONTEXT.md` name a
turn cut by its turn ceiling or its wall clock with nothing committed. They
say the first such cut at a `spec_sha` ends `ORPHANED` and the second ends
`NOT_IMPLEMENTED`. `DESIGN.md` §4.5 names the same case beside kill, crash
and `--until`, with the one retry, and says a resumed task row must re-key the
cap. `GOTCHAS.md` says a first cut with no room to salvage ends `ORPHANED` and
re-queues, and a second at the same `spec_sha` ends `NOT_IMPLEMENTED`. All
land after `SA-0126` merges, not before.
