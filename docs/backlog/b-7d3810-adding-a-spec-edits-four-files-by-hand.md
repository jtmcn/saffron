---
id: b-7d3810
title: Adding a spec edits four other files by hand, and the queue smoke test's paragraph is rewritten every time
status: open
filed: 2026-09-20
specs: []
prs: []
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
