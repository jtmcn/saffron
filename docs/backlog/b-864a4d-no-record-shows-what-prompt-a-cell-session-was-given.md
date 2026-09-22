---
id: b-864a4d
title: No record shows what prompt a cell session was given, so CLAUDE.md reaching a live cell is unverifiable
status: open
filed: 2026-09-22
specs: [SA-0129]
prs: []
commits: []
cites: [§5.3, §8]
related: []
---

## Problem

Found 2026-09-22 while checking that `CLAUDE.md` reaches cells.

Commits `fdbbe072` and `0d5f8e63` put the base commit's `CLAUDE.md` into
every agent prompt, under the heading `This repository's standing
instructions`. Unit tests assert it. No live run can show it.

`events.jsonl` records no prompt text and no prompt digest. A search of it for
SA-0121 to SA-0124 finds the heading zero times.

`tasks.prompt_sha` does not fill the gap. `context.prompt_sha()` hashes the
prompt templates as authored, and its docstring excludes the assembled prompt.
Every recent task carries the same value, `1747509ede66`, whatever its
`CLAUDE.md` said.

## Done looks like

- Each agent session a task starts records a SHA-256 of the prompt it sent.
  This covers IMPLEMENT, the criterion probe, each lens and the rebut verdict.
- Each task records a SHA-256 of the `CLAUDE.md` text read at `base_sha`, or
  says it found none.
- A test changes only `CLAUDE.md` at the base commit and shows both values
  change.

## Record

- 2026-09-22: filed.
