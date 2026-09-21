---
id: b-7d3810
title: Adding a spec edits four other files by hand, and the queue smoke test's paragraph is rewritten every time
status: open
tier: 2
filed: 2026-09-20
specs: [SA-0116]
prs: [416]
commits: []
cites: []
related: [b-b69bb6, b-281f0a]
---

## Problem

Filed 2026-09-20 from `SA-0113`, one spec drafted outside a loop run.

`docs/agents/issue-tracker.md` asks the commit that adds a spec to carry four
edits beyond the spec file. The origin item gains the spec in its `specs:`
list. Any record the spec's author files gains a line in `PRIORITY.md`, because
the tier check fails without one. The queue smoke test at
`tests/test_scheduler.py::test_saffron_queue_smoke_reproduces_this_repos_measured_queue`
gains a paragraph saying what is queued and why, and its pinned candidate list
gains the new id.

`SA-0113`'s draft took 35.7 minutes of agent time, and this tail is the part of
it that needs no judgement. The smoke test's paragraph records its forty-ninth
re-measurement in that commit. Every one of the forty-nine was written by hand
from a queue the author had to compute anyway.

Each edit is derivable. `build_queue` over the working tree returns the
candidate list and the refusals. The origin item is the one the spec's
`## Context` cites first. The `PRIORITY.md` question is whether each new record
id appears in the file at all.

## Done looks like

A command takes a spec id and prints the four edits. The origin item's
`specs:` line. Any new record id that `PRIORITY.md` does not name. The smoke
test's new paragraph and its pinned list, computed from `build_queue` over the
working tree rather than from the author's reading. The author pastes what it
prints.

## Record

- 2026-09-20: filed from `SA-0113`. The same shape as `SA-0092` and `SA-0112`,
  where a cell built a command and the prompt that calls it was a hand edit.
- 2026-09-20: `SA-0116` is queued for the command. It goes in the spec loop's
  `.claude/skills/run-saffron-spec-loop/driver.py` beside `check`, `cite` and
  `enumerators`, as `driver.py bookkeeping SA-NNNN`. It edits the same two
  files as `SA-0114` and `SA-0115`, so it
  declares `depends_on: [SA-0115]`, the later of the two. Three findings came
  out of writing it. Two of the four edits are judged already, by
  `check_specs_name_their_items` and `check_priority` in `tests/records/check.py`,
  so the command imports rather than re-derives. There is no
  `--base`: all four edits are about the working tree, and `check_priority` over
  that tree already reports the records left unplaced. And the smoke test's
  ordinal cannot be counted. Measured at this base, the docstring says "a
  fifty-first time" and holds 37 lines beginning `Re-measured`. So the ordinal
  comes from the topmost one plus one.
- 2026-09-20: the first review of `SA-0116` put the four-block shape at 555
  changed lines against a `feature` ceiling of 600. So the spec was cut to
  three blocks. It now prints the `specs:` line, the smoke test's
  paragraph and its two pinned `assert` lines. `PRIORITY.md` is the block that
  came out. `check_priority` already names the record and its tier on
  every `make check`, leaving only the `### Tier <n>` heading to find. That
  quarter of this item stays open, and it is a small spec of its own: a filter
  over `check_priority` plus a heading lookup.
- 2026-09-20: the prose half stays open here, as item b-281f0a left its own.
  Running the command from `.claude/agents/spec-writer.md`, and naming it in
  the spec loop's `SKILL.md`, are by-hand edits after the cell lands.
- 2026-09-21: `SA-0116` ran in the spec loop's run 11 after its spec was revised
  for its parent branch (#407). Its cell was cut by the turn wall with no commit
  and ended `NOT_IMPLEMENTED`, so nothing landed. Item b-36b551 holds the cause.
  The spec is reviewed and merged, and a later loop can run it again.
- 2026-09-21: `SA-0116` ran again in the spec loop's run 12, after #413 added a
  commit-before-verify note. It reached `READY_FOR_REVIEW` as #416 at $13.53 of
  $26. The review seats found the headings' order unwitnessed, among other
  findings, and the review commit fixed them. The operator accepted 636 changed
  lines against the ceiling of 600.
