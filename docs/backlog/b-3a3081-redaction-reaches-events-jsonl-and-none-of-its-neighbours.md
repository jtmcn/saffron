---
id: b-3a3081
title: "Redaction reaches `events.jsonl` and none of the cell-authored files beside it, and §5.7 still names the remote alone"
status: open
tier: 2
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§5.4, §5.7]
related: [46, 11]
---

## Problem

Found by both seats on #906, in the spec loop's run 44.

`SA-0277` (#906) redacts a credential an `Agent` event carries before
`EventLog.append` writes it. The files the cell's output lands in beside the
log are written as they came.

- `patch.diff` (`saffron/cell/session.py:976`), `plan.json` (`:2545`),
  `notes.json` (`:3017`) and `findings.json` (`:3364`).
- PACKAGE builds `EventLog(outcome.task_dir)` with no token
  (`saffron/phases/package.py:640`, `:1089`). PACKAGE emits no `Agent`
  event today, so nothing it writes is lost to this yet.

Two texts lag. `DESIGN.md` §5.7 states the residual risk for the remote
alone (`DESIGN.md:1359`). A shape the list misses now also reaches
`events.jsonl`, as `saffron/credentials.py` says. Item 11 still names
`_CREDENTIAL_SHAPES` under a `ponytail:` comment (`docs/backlog/011-what-package-left-and-the-one-design-question-it-raised.md:83`).
The tuple is `saffron/credentials.py`'s `CREDENTIAL_SHAPES` now.

## Done looks like

Each cell-authored file in the task directory is redacted with the same
module before it is written, or `DESIGN.md` §5.7 names it as accepted risk.
PACKAGE's log takes the token it holds. §5.7 names `events.jsonl` in its
residual risk.

## Record

- 2026-10-19: filed from the spec loop's run 44.
